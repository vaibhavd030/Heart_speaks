"""
Authentication module for SAGE.

Handles user registration, login, JWT tokens, and admin approval.
"""

import os
import smtplib
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from heart_speaks.config import settings

# --- Password Hashing ---
# Using pbkdf2_sha256 to avoid compatibility issues between passlib and bcrypt 4.0+
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# --- JWT Config ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", settings.jwt_secret_key)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72  # 3 days for spiritual seekers, not a banking app

security = HTTPBearer(auto_error=False)

# --- Pydantic Models ---
class RegisterRequest(BaseModel):
    """Registration request from a new user."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    abhyasi_id: str = Field(..., min_length=3, max_length=50)


class LoginRequest(BaseModel):
    """Login request. Username is email, password is abhyasi_id."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response after successful login."""

    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class ApproveRequest(BaseModel):
    """Admin request to approve or reject a user."""

    email: str
    action: str = Field(..., description="'approve' or 'reject'")


# --- Database Setup ---
# Use the root-relative data directory from settings
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, settings.data_dir.replace("./", ""), "messages.db")

def get_db() -> sqlite3.Connection:
    """Returns a configured SQLite connection."""

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_table() -> None:
    """Creates the users table if it does not exist."""

    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                abhyasi_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    # Create admin user if not exists (you)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE email = ?", ("vaibhav030@gmail.com",)
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO users (user_id, first_name, last_name, email, abhyasi_id, password_hash, status, is_admin)
                VALUES (?, ?, ?, ?, ?, ?, 'approved', 1)
            """,
                (
                    str(uuid.uuid4()),
                    "Vaibhav",
                    "Dhanani",
                    "vaibhav030@gmail.com",
                    "admin",
                    pwd_context.hash("admin"),  # Change this after first login
                    ),
            )
            conn.commit()
            logger.info("Admin user created: vaibhav030@gmail.com")


# --- Core Auth Functions ---
def register_user(req: RegisterRequest) -> dict[str, str]:
    """Registers a new user with status 'pending'. Sends notification email to admin."""

    init_users_table()

    # Check if email already exists
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE email = ?", (req.email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400, detail="An account with this email already exists."
            )

    # Hash the abhyasi_id as the default password
    password_hash = pwd_context.hash(req.abhyasi_id)

    user_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, first_name, last_name, email, abhyasi_id, password_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
            (user_id, req.first_name, req.last_name, req.email, req.abhyasi_id, password_hash),
        )
        conn.commit()

    # Send notification email to admin
    _send_admin_notification(req)

    return {"message": "Registration submitted. You will be notified once approved."}


def login_user(req: LoginRequest) -> TokenResponse:
    """Authenticates a user and returns a JWT token."""

    init_users_table()

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (req.email,)
        ).fetchone()

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
        raise HTTPException(
            status_code=403, detail="Your registration request was not approved."
        )

    # Create JWT token
    token_data = {
        "sub": user["email"],
        "user_id": user["user_id"],
        "is_admin": bool(user["is_admin"]),
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
            "is_admin": bool(user["is_admin"]),
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token."
        )

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )

    return dict(user)


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

    new_status = "approved" if req.action == "approve" else "rejected"

    with get_db() as conn:
        result = conn.execute(
            "UPDATE users SET status = ? WHERE email = ? AND status = 'pending'",
            (new_status, req.email),
        )
        conn.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404, detail="No pending user found with that email."
        )

    return {"message": f"User {req.email} has been {new_status}."}


def list_pending_users() -> list[dict[str, Any]]:
    """Returns all users with status 'pending'."""

    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id, first_name, last_name, email, abhyasi_id, created_at FROM users WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]

def list_all_users() -> list[dict[str, Any]]:
    """Returns all registered users with full metadata."""

    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id, first_name, last_name, email, abhyasi_id, status, is_admin, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]

# --- Email Notification ---
def _send_admin_notification(req: RegisterRequest) -> None:
    """Sends a notification email to the admin about a new registration.

    Uses Gmail SMTP. Requires GMAIL_APP_PASSWORD in env.
    If not configured, logs the notification instead.
    """

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

Or use the admin API:
POST /admin/users/approve
{{"email": "{req.email}", "action": "approve"}}

Or reject:
{{"email": "{req.email}", "action": "reject"}}
"""

    if not gmail_password:
        logger.warning(
            f"GMAIL_APP_PASSWORD not set. Registration notification NOT emailed. Details:\\n{body}"
        )
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
