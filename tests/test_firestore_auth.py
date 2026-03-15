"""
Tests for Firestore-backed auth functions.

Uses unittest.mock to patch the Firestore client — no emulator or network needed.
All tests run fully offline.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(data: dict, exists: bool = True):
    doc = MagicMock()
    doc.exists = exists
    doc.to_dict.return_value = data
    doc.id = data.get("user_id", "mock-id")
    return doc


def _stream_with(*items):
    return iter([_make_doc(item) for item in items])


def _empty_stream():
    return iter([])


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------

class TestRegisterUser:
    def test_register_new_user(self):
        """Registers a new user; Firestore set() is called."""
        with patch("heart_speaks.auth.get_firestore_client") as mock_client, \
             patch("heart_speaks.auth._send_admin_notification") as mock_email:

            db = mock_client.return_value
            # No existing user
            db.collection.return_value.where.return_value.limit.return_value.stream.return_value = _empty_stream()
            doc_ref = MagicMock()
            db.collection.return_value.document.return_value = doc_ref

            from heart_speaks.auth import register_user, RegisterRequest
            req = RegisterRequest(first_name="Test", last_name="User", email="test@example.com", abhyasi_id="B999")
            result = register_user(req)

        assert "submitted" in result["message"].lower()
        doc_ref.set.assert_called_once()
        stored = doc_ref.set.call_args[0][0]
        assert stored["email"] == "test@example.com"
        assert stored["status"] == "pending"
        assert stored["is_admin"] == False
        mock_email.assert_called_once_with(req)

    def test_register_duplicate_email_raises(self):
        """Raises 400 if email already exists."""
        with patch("heart_speaks.auth.get_firestore_client") as mock_client, \
             patch("heart_speaks.auth._send_admin_notification"):

            existing = {"user_id": "existing-id", "email": "dupe@example.com"}
            db = mock_client.return_value
            db.collection.return_value.where.return_value.limit.return_value.stream.return_value = _stream_with(existing)

            from heart_speaks.auth import register_user, RegisterRequest
            req = RegisterRequest(first_name="Dup", last_name="User", email="dupe@example.com", abhyasi_id="B001")

            with pytest.raises(HTTPException) as exc:
                register_user(req)
            assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# login_user
# ---------------------------------------------------------------------------

class TestLoginUser:
    def _setup_user(self, mock_client, user_data: dict):
        db = mock_client.return_value
        db.collection.return_value.where.return_value.limit.return_value.stream.return_value = _stream_with(user_data)
        return db

    def test_login_success(self):
        """Valid credentials return a JWT token and user object."""
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = {
            "user_id": "u1", "first_name": "Vaibhav", "last_name": "Dikshit",
            "email": "vaibhav030@gmail.com",
            "password_hash": pwd.hash("admin"),
            "status": "approved", "is_admin": True, "abhyasi_id": "admin",
        }

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            self._setup_user(mock_client, user)
            from heart_speaks.auth import login_user, LoginRequest
            result = login_user(LoginRequest(email="vaibhav030@gmail.com", password="admin"))

        assert result.access_token
        assert result.user["is_admin"] is True
        assert result.user["first_name"] == "Vaibhav"
        assert result.token_type == "bearer"

    def test_login_wrong_password(self):
        """Wrong password raises 401."""
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = {"user_id": "u1", "email": "test@example.com", "password_hash": pwd.hash("correct"), "status": "approved", "is_admin": False}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            self._setup_user(mock_client, user)
            from heart_speaks.auth import login_user, LoginRequest
            with pytest.raises(HTTPException) as exc:
                login_user(LoginRequest(email="test@example.com", password="wrong"))
            assert exc.value.status_code == 401

    def test_login_pending_user(self):
        """Pending user gets 403."""
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = {"user_id": "u2", "email": "pending@example.com", "password_hash": pwd.hash("pass"), "status": "pending", "is_admin": False}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            self._setup_user(mock_client, user)
            from heart_speaks.auth import login_user, LoginRequest
            with pytest.raises(HTTPException) as exc:
                login_user(LoginRequest(email="pending@example.com", password="pass"))
            assert exc.value.status_code == 403

    def test_login_suspended_user(self):
        """Suspended user gets 403."""
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = {"user_id": "u3", "email": "sus@example.com", "password_hash": pwd.hash("pass"), "status": "suspended", "is_admin": False}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            self._setup_user(mock_client, user)
            from heart_speaks.auth import login_user, LoginRequest
            with pytest.raises(HTTPException) as exc:
                login_user(LoginRequest(email="sus@example.com", password="pass"))
            assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# approve_or_reject_user
# ---------------------------------------------------------------------------

class TestApproveRejectUser:
    def test_approve_pending_user(self):
        """Approving a pending user updates Firestore status to approved."""
        user = {"user_id": "u1", "email": "seeker@example.com", "status": "pending"}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            db = mock_client.return_value
            db.collection.return_value.where.return_value.limit.return_value.stream.return_value = _stream_with(user)
            doc_ref = MagicMock()
            db.collection.return_value.document.return_value = doc_ref

            from heart_speaks.auth import approve_or_reject_user, ApproveRequest
            result = approve_or_reject_user(ApproveRequest(email="seeker@example.com", action="approve"))

        assert "approved" in result["message"].lower()
        doc_ref.update.assert_called_once_with({"status": "approved"})

    def test_reject_pending_user(self):
        """Rejecting a pending user updates Firestore status to rejected."""
        user = {"user_id": "u1", "email": "seeker@example.com", "status": "pending"}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            db = mock_client.return_value
            db.collection.return_value.where.return_value.limit.return_value.stream.return_value = _stream_with(user)
            doc_ref = MagicMock()
            db.collection.return_value.document.return_value = doc_ref

            from heart_speaks.auth import approve_or_reject_user, ApproveRequest
            result = approve_or_reject_user(ApproveRequest(email="seeker@example.com", action="reject"))

        assert "rejected" in result["message"].lower()
        doc_ref.update.assert_called_once_with({"status": "rejected"})

    def test_invalid_action_raises(self):
        """Invalid action raises 400."""
        with patch("heart_speaks.auth.get_firestore_client"):
            from heart_speaks.auth import approve_or_reject_user, ApproveRequest
            with pytest.raises(HTTPException) as exc:
                approve_or_reject_user(ApproveRequest(email="test@example.com", action="ban"))
            assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# suspend_user / delete_user
# ---------------------------------------------------------------------------

class TestSuspendDeleteUser:
    def test_suspend_user(self):
        """Suspending a user updates Firestore status to suspended."""
        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            doc = MagicMock()
            doc.exists = True
            mock_client.return_value.collection.return_value.document.return_value.get.return_value = doc
            doc_ref = MagicMock()
            mock_client.return_value.collection.return_value.document.return_value = doc_ref
            doc_ref.get.return_value = doc

            from heart_speaks.auth import suspend_user
            result = suspend_user("user-123")

        assert "suspended" in result["message"].lower()
        doc_ref.update.assert_called_once_with({"status": "suspended"})

    def test_suspend_nonexistent_user(self):
        """Suspending a non-existent user raises 404."""
        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            doc = MagicMock()
            doc.exists = False
            mock_client.return_value.collection.return_value.document.return_value.get.return_value = doc

            from heart_speaks.auth import suspend_user
            with pytest.raises(HTTPException) as exc:
                suspend_user("ghost-user")
            assert exc.value.status_code == 404

    def test_delete_user_calls_cascade(self):
        """delete_user calls delete_user_data and then deletes the user doc."""
        with patch("heart_speaks.auth.get_firestore_client") as mock_client, \
             patch("heart_speaks.auth.delete_user_data") as mock_cascade:

            doc = MagicMock()
            doc.exists = True
            doc_ref = MagicMock()
            doc_ref.get.return_value = doc
            mock_client.return_value.collection.return_value.document.return_value = doc_ref

            from heart_speaks.auth import delete_user
            result = delete_user("user-123")

        mock_cascade.assert_called_once_with("user-123")
        doc_ref.delete.assert_called_once()
        assert "deleted" in result["message"].lower()


# ---------------------------------------------------------------------------
# list_all_users / list_pending_users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_list_all_users(self):
        """list_all_users returns all users sorted by created_at descending."""
        users_data = [
            {"user_id": "u1", "first_name": "A", "last_name": "B", "email": "a@x.com", "abhyasi_id": "1", "status": "approved", "is_admin": False, "created_at": "2024-01-01"},
            {"user_id": "u2", "first_name": "C", "last_name": "D", "email": "c@x.com", "abhyasi_id": "2", "status": "pending", "is_admin": False, "created_at": "2024-02-01"},
        ]

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            mock_client.return_value.collection.return_value.stream.return_value = _stream_with(*users_data)
            from heart_speaks.auth import list_all_users
            result = list_all_users()

        assert len(result) == 2
        # Should be sorted newest first
        assert result[0]["created_at"] == "2024-02-01"

    def test_list_pending_users(self):
        """list_pending_users filters to only pending status."""
        pending = {"user_id": "u1", "first_name": "P", "last_name": "Q", "email": "p@x.com", "abhyasi_id": "3", "created_at": "2024-01-01"}

        with patch("heart_speaks.auth.get_firestore_client") as mock_client:
            mock_client.return_value.collection.return_value.where.return_value.stream.return_value = _stream_with(pending)
            from heart_speaks.auth import list_pending_users
            result = list_pending_users()

        assert len(result) == 1
        assert result[0]["email"] == "p@x.com"
