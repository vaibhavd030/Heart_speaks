"""
Tests for Firestore-backed repository functions.

Uses unittest.mock to patch the Firestore client — no emulator or network needed.
All tests run fully offline.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(data: dict, exists: bool = True):
    """Creates a mock Firestore DocumentSnapshot."""
    doc = MagicMock()
    doc.exists = exists
    doc.to_dict.return_value = data
    doc.id = data.get("id", "mock-doc-id")
    return doc


def _make_stream(items: list[dict]):
    """Creates a mock Firestore stream (iterator of DocumentSnapshots)."""
    return iter([_make_doc(item) for item in items])


# ---------------------------------------------------------------------------
# user_progress
# ---------------------------------------------------------------------------

class TestUserProgress:
    def test_update_progress(self):
        """update_progress calls Firestore set() with correct data."""
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_doc = MagicMock()
            mock_client.return_value.collection.return_value.document.return_value = mock_doc

            from heart_speaks.repository import update_progress
            update_progress("user-123", "1991/August/msg.pdf", 5)

            mock_client.return_value.collection.assert_called_with("user_progress")
            mock_client.return_value.collection.return_value.document.assert_called_with("user-123")
            mock_doc.set.assert_called_once_with({
                "user_id": "user-123",
                "last_read_source_file": "1991/August/msg.pdf",
                "messages_read": 5,
            })

    def test_get_progress_found(self):
        """get_progress returns dict when document exists."""
        expected = {"user_id": "user-123", "last_read_source_file": "1991/msg.pdf", "messages_read": 5}
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_doc = _make_doc(expected)
            mock_client.return_value.collection.return_value.document.return_value.get.return_value = mock_doc

            from heart_speaks.repository import get_progress
            result = get_progress("user-123")

        assert result == expected

    def test_get_progress_not_found(self):
        """get_progress returns None when document doesn't exist."""
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_client.return_value.collection.return_value.document.return_value.get.return_value = mock_doc

            from heart_speaks.repository import get_progress
            result = get_progress("nonexistent-user")

        assert result is None


# ---------------------------------------------------------------------------
# bookmarks
# ---------------------------------------------------------------------------

class TestBookmarks:
    def test_upsert_bookmark(self):
        """upsert_bookmark sets a Firestore document with correct fields."""
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_doc_ref = MagicMock()
            mock_client.return_value.collection.return_value.document.return_value = mock_doc_ref

            from heart_speaks.repository import upsert_bookmark
            upsert_bookmark("user-123", "1991/August/msg.pdf", "Beautiful passage")

            mock_client.return_value.collection.assert_called_with("bookmarks")
            call_args = mock_doc_ref.set.call_args[0][0]
            assert call_args["user_id"] == "user-123"
            assert call_args["source_file"] == "1991/August/msg.pdf"
            assert call_args["notes"] == "Beautiful passage"
            assert "created_at" in call_args

    def test_delete_bookmark(self):
        """delete_bookmark deletes the correct Firestore document."""
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_doc_ref = MagicMock()
            mock_client.return_value.collection.return_value.document.return_value = mock_doc_ref

            from heart_speaks.repository import delete_bookmark
            delete_bookmark("user-123", "1991/August/msg.pdf")

            mock_doc_ref.delete.assert_called_once()

    def test_get_bookmarks_enriched(self):
        """get_bookmarks returns bookmarks enriched with SQLite message metadata."""
        bm_data = {"user_id": "user-123", "source_file": "1991/August/msg.pdf", "notes": "Lovely", "created_at": "2024-01-01T00:00:00Z"}

        with patch("heart_speaks.repository.get_firestore_client") as mock_client, \
             patch("heart_speaks.repository.get_db_connection") as mock_db:

            # Firestore stream
            mock_client.return_value.collection.return_value.where.return_value.stream.return_value = _make_stream([bm_data])

            # SQLite cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            sqlite_row = MagicMock()
            sqlite_row.__getitem__ = lambda self, key: {"date": "1991-08-15", "preview": "Dear Soul...", "author": "Babuji", "page_count": 3}[key]
            mock_cursor.fetchone.return_value = sqlite_row
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn

            from heart_speaks.repository import get_bookmarks
            result = get_bookmarks("user-123")

        assert len(result) == 1
        assert result[0]["source_file"] == "1991/August/msg.pdf"
        assert result[0]["notes"] == "Lovely"
        assert result[0]["author"] == "Babuji"
        assert result[0]["date"] == "1991-08-15"


# ---------------------------------------------------------------------------
# chat_logs
# ---------------------------------------------------------------------------

class TestChatLogs:
    def test_save_chat_log(self):
        """save_chat_log adds a Firestore document with all fields."""
        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_collection = MagicMock()
            mock_client.return_value.collection.return_value = mock_collection

            from heart_speaks.repository import save_chat_log
            save_chat_log(
                user_id="user-123",
                session_id="sess-abc",
                question="What is love?",
                response="Love is the path...",
                metadata='{"sources_count": 3}',
                first_name="Vaibhav",
                last_name="Dikshit",
                email="v@example.com",
                abhyasi_id="B123",
            )

            mock_client.return_value.collection.assert_called_with("chat_logs")
            added_data = mock_collection.add.call_args[0][0]
            assert added_data["user_id"] == "user-123"
            assert added_data["question"] == "What is love?"
            assert added_data["first_name"] == "Vaibhav"
            assert added_data["last_name"] == "Dikshit"
            assert "created_at" in added_data

    def test_get_all_chat_logs(self):
        """get_all_chat_logs returns list from ordered Firestore query."""
        log_data = {"user_id": "u1", "question": "Q1", "response": "A1", "created_at": "2024-01-01T10:00:00Z", "id": "log-1"}

        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            mock_query = MagicMock()
            mock_client.return_value.collection.return_value.order_by.return_value.limit.return_value.offset.return_value = mock_query
            mock_query.stream.return_value = _make_stream([log_data])

            from heart_speaks.repository import get_all_chat_logs
            result = get_all_chat_logs(limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["question"] == "Q1"


# ---------------------------------------------------------------------------
# delete_user_data
# ---------------------------------------------------------------------------

class TestDeleteUserData:
    def test_delete_cascades(self):
        """delete_user_data removes progress, bookmarks, and chat logs."""
        bm_doc = MagicMock()
        log_doc = MagicMock()

        with patch("heart_speaks.repository.get_firestore_client") as mock_client:
            db = mock_client.return_value

            # Progress delete
            progress_ref = MagicMock()
            db.collection.return_value.document.return_value = progress_ref

            # Bookmarks stream
            bm_stream = [bm_doc]
            log_stream = [log_doc]

            def collection_side_effect(name):
                mock_col = MagicMock()
                if name == "bookmarks":
                    mock_col.where.return_value.stream.return_value = iter(bm_stream)
                elif name == "chat_logs":
                    mock_col.where.return_value.stream.return_value = iter(log_stream)
                elif name == "user_progress":
                    mock_col.document.return_value = progress_ref
                return mock_col

            db.collection.side_effect = collection_side_effect

            from heart_speaks.repository import delete_user_data
            delete_user_data("user-123")

        bm_doc.reference.delete.assert_called_once()
        log_doc.reference.delete.assert_called_once()
