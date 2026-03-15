"""
Authentication module for Heart Speaks.

All user data is stored in Firestore (persistent, cross-device, survives deployments).
Uses JWT tokens (python-jose) and bcrypt password hashing (passlib).
"""

import os
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.cloud.firestore_v1.base_query import FieldFilter
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from heart_speaks.config import settings
from heart_speaks.firestore_db import get_firestore_client
from heart_speaks.repository import delete_user_data

# --- Config ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", settings.jwt_secret_key)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

security = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ADMIN_EMAIL = "vaibhav030@gmail.com"
ADMIN_FIRST = "Vaibhav"
ADMIN_LAST = "Dikshit"


# --- Pydantic Models ---
class RegisterRequest(BaseModel):
    """User registration request."""
    first_name: str
    last_name: str
    email: str
    abhyasi_id: str


class LoginRequest(BaseModel):
    """User login request."""
    email: str
    password: str


class ApproveRequest(BaseModel):
    """Admin request to approve or reject a user."""
    email: str
    action: str = Field(..., description="'approve' or 'reject'")


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


# --- Firestore helpers ---
def _users_collection():
    return get_firestore_client().collection("users")


def _get_user_by_email(email: str) -> dict[str, Any] | None:
    """Fetches a user document by email."""
    docs = _users_collection().where(filter=FieldFilter("email", "==", email)).limit(1).stream()
    for doc in docs:
        return {**doc.to_dict(), "_doc_id": doc.id}
    return None


def _get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetches a user document by user_id field."""
    doc = _users_collection().document(user_id).get()
    if doc.exists:
        return {**doc.to_dict(), "_doc_id": doc.id}
    return None


# --- Admin bootstrap ---
def ensure_admin_exists() -> None:
    """
    Ensures the admin account exists in Firestore with correct privileges.
    Called once on startup. Safe to call multiple times.
    """
    db = get_firestore_client()
    admin_ref = db.collection("users").document("admin")
    doc = admin_ref.get()

    if doc.exists:
        # Always enforce correct admin flags and name
        admin_ref.update({
            "is_admin": True,
            "status": "approved",
            "first_name": ADMIN_FIRST,
            "last_name": ADMIN_LAST,
        })
        logger.info("Admin privileges enforced for: vaibhav030@gmail.com")
    else:
        admin_ref.set({
            "user_id": "admin",
            "first_name": ADMIN_FIRST,
            "last_name": ADMIN_LAST,
            "email": ADMIN_EMAIL,
            "abhyasi_id": "admin",
            "password_hash": pwd_context.hash("admin"),
            "status": "approved",
            "is_admin": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin user created: vaibhav030@gmail.com")


# --- Core Auth Functions ---
def register_user(req: RegisterRequest) -> dict[str, str]:
    """Registers a new user with status 'pending'. Sends notification email to admin."""

    # Check if email already exists
    if _get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Hash the abhyasi_id as the default password
    password_hash = pwd_context.hash(req.abhyasi_id)
    user_id = str(uuid.uuid4())

    _users_collection().document(user_id).set({
        "user_id": user_id,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "email": req.email,
        "abhyasi_id": req.abhyasi_id,
        "password_hash": password_hash,
        "status": "pending",
        "is_admin": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    _send_admin_notification(req)
    return {"message": "Registration submitted. You will be notified once approved."}


def login_user(req: LoginRequest) -> TokenResponse:
    """Authenticates a user and returns a JWT token."""
    user = _get_user_by_email(req.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if user["status"] == "pending":
        raise HTTPException(
            status_code=403,
            detail="Your account is pending approval. Please wait for the admin to approve your request.",
        )

    if user["status"] == "rejected":
        raise HTTPException(status_code=403, detail="Your registration request was not approved.")

    if user["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended. Contact the admin.")

    token_data = {
        "sub": user["email"],
        "user_id": user["user_id"],
        "is_admin": bool(user.get("is_admin", False)),
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return TokenResponse(
        access_token=access_token,
        user={
            "user_id": user["user_id"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "email": user["email"],
            "is_admin": bool(user.get("is_admin", False)),
        },
    )


def get_current_user(
    credentials: Any = Depends(security),
) -> dict[str, Any]:
    """FastAPI dependency: extracts and validates the current user from the JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return user


def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """FastAPI dependency: ensures the current user is an admin."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def approve_or_reject_user(req: ApproveRequest) -> dict[str, str]:
    """Admin action: approve or reject a pending user."""
    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    user = _get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="No user found with that email.")

    if user["status"] != "pending":
        raise HTTPException(status_code=400, detail="User is not in pending status.")

    new_status = "approved" if req.action == "approve" else "rejected"
    _users_collection().document(user["user_id"]).update({"status": new_status})

    return {"message": f"User {req.email} has been {new_status}."}


def suspend_user(user_id: str) -> dict[str, str]:
    """Admin action: suspend a user account."""
    doc = _users_collection().document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found.")

    _users_collection().document(user_id).update({"status": "suspended"})
    return {"message": f"User {user_id} has been suspended."}


def delete_user(user_id: str) -> dict[str, str]:
    """Admin action: permanently delete a user and all their data."""
    doc = _users_collection().document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found.")

    # Cascade delete all user data from Firestore
    delete_user_data(user_id)

    # Delete the user document itself
    _users_collection().document(user_id).delete()

    return {"message": f"User {user_id} and all their data have been deleted."}


def list_pending_users() -> list[dict[str, Any]]:
    """Returns all users with status 'pending', newest first."""
    docs = _users_collection().where(filter=FieldFilter("status", "==", "pending")).stream()
    users = []
    for doc in docs:
        d = doc.to_dict()
        users.append({
            "user_id": d.get("user_id"),
            "first_name": d.get("first_name"),
            "last_name": d.get("last_name"),
            "email": d.get("email"),
            "abhyasi_id": d.get("abhyasi_id"),
            "created_at": d.get("created_at"),
        })
    users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
    return users


def list_all_users() -> list[dict[str, Any]]:
    """Returns all registered users with full metadata, newest first."""
    docs = _users_collection().stream()
    users = []
    for doc in docs:
        d = doc.to_dict()
        users.append({
            "user_id": d.get("user_id"),
            "first_name": d.get("first_name"),
            "last_name": d.get("last_name"),
            "email": d.get("email"),
            "abhyasi_id": d.get("abhyasi_id"),
            "status": d.get("status"),
            "is_admin": d.get("is_admin", False),
            "created_at": d.get("created_at"),
        })
    users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
    return users


# --- Email Notification ---
def _send_admin_notification(req: RegisterRequest) -> None:
    """Sends a notification email to the admin about a new registration."""
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", settings.gmail_app_password)
    admin_email = settings.admin_email

    subject = f"[SAGE] New Registration Request: {req.first_name} {req.last_name}"
    body = f"""New user registration request for SAGE:

Name: {req.first_name} {req.last_name}
Email: {req.email}
Abhyasi ID: {req.abhyasi_id}
Time: {datetime.now(timezone.utc).isoformat()}

To approve or reject, visit the Archive Dashboard:
https://sage-frontend-34833003999.europe-west2.run.app/dashboard
"""

    if not gmail_password:
        logger.warning(f"GMAIL_APP_PASSWORD not set. Registration notification NOT emailed. Details:\n{body}")
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = admin_email
        msg["To"] = admin_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(admin_email, gmail_password)
            server.send_message(msg)

        logger.info(f"Admin notification sent for registration: {req.email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification email: {e}")
