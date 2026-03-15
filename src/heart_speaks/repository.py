"""
Repository Layer for Heart Speaks.

Architecture:
- messages table → SQLite (read-only, bundled in Docker image, 5000+ records)
- user_progress, bookmarks, chat_logs → Firestore (persistent, cross-device)
"""

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    from google.cloud.firestore import FieldFilter
except ImportError:
    from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger

from heart_speaks.config import settings
from heart_speaks.firestore_db import get_firestore_client

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, settings.data_dir.replace("./", ""), "messages.db")


# ---------------------------------------------------------------------------
# SQLite helpers (messages only – read-only)
# ---------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """Returns a configured SQLite connection for the read-only messages DB."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialises the SQLite messages table (no user tables — those live in Firestore)."""
    logger.info(f"Initialising message repository at {DB_PATH}")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                source_file TEXT UNIQUE NOT NULL,
                author TEXT,
                date TEXT,
                full_text TEXT NOT NULL,
                preview TEXT,
                page_count INTEGER,
                topics TEXT
            )
        """)
        conn.commit()


def clear_db() -> None:
    """Drops the messages table to allow fresh ingestion."""
    logger.warning("Clearing message repository...")
    with get_db_connection() as conn:
        conn.cursor().execute("DROP TABLE IF EXISTS messages")
        conn.commit()
    init_db()


def upsert_message(
    source_file: str,
    full_text: str,
    author: str = "Unknown",
    date: str = "",
    page_count: int = 1,
    topics: list[str] | None = None,
) -> None:
    """Inserts or updates a full spiritual message in the repository."""
    if topics is None:
        topics = []
    topics_str = ",".join(topics)
    preview = (
        full_text[:150].rsplit(" ", 1)[0] + "..." if len(full_text) > 150 else full_text
    )
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (message_id, source_file, author, date, full_text, preview, page_count, topics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_file) DO UPDATE SET
                full_text=excluded.full_text,
                author=excluded.author,
                date=excluded.date,
                preview=excluded.preview,
                page_count=excluded.page_count,
                topics=excluded.topics
        """,
            (str(uuid.uuid4()), source_file, author, date, full_text, preview, page_count, topics_str),
        )
        conn.commit()


def get_message_by_source(source_file: str) -> dict[str, Any] | None:
    """Retrieves a message based on its original PDF filename."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE source_file = ?", (source_file,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_stats() -> dict[str, Any]:
    """Retrieves basic EDA statistics from the repository."""
    stats: dict[str, Any] = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_messages, SUM(page_count) as total_pages FROM messages")
        totals = cursor.fetchone()
        stats["total_messages"] = totals["total_messages"] if totals else 0
        stats["total_pages"] = totals["total_pages"] if totals else 0

        cursor.execute("""
            SELECT substr(date, 1, 4) as year, COUNT(*) as count
            FROM messages
            WHERE date IS NOT NULL AND date != '' AND date != 'Unknown'
            GROUP BY year ORDER BY year
        """)
        stats["by_year"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT substr(date, 6, 2) as month, COUNT(*) as count
            FROM messages
            WHERE date IS NOT NULL AND date != '' AND date != 'Unknown'
            GROUP BY month ORDER BY month
        """)
        stats["by_month"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT author, COUNT(*) as count
            FROM messages
            GROUP BY author ORDER BY count DESC
        """)
        stats["by_author"] = [dict(row) for row in cursor.fetchall()]

    return stats


def search_messages(query: str = "", page: int = 1, limit: int = 50) -> dict[str, Any]:
    """Retrieves a paginated list of messages, optionally filtered by text query."""
    offset = (page - 1) * limit
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if query:
            pattern = f"%{query}%"
            cursor.execute(
                "SELECT COUNT(*) as total FROM messages WHERE full_text LIKE ? OR author LIKE ? OR source_file LIKE ?",
                (pattern, pattern, pattern),
            )
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT message_id, source_file, author, date, preview, page_count FROM messages WHERE full_text LIKE ? OR author LIKE ? OR source_file LIKE ? ORDER BY date DESC LIMIT ? OFFSET ?",
                (pattern, pattern, pattern, limit, offset),
            )
        else:
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT message_id, source_file, author, date, preview, page_count FROM messages ORDER BY date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = cursor.fetchall()

    return {"total": total, "page": page, "limit": limit, "messages": [dict(row) for row in rows]}


def get_reader_sequence() -> list[dict[str, Any]]:
    """Returns a filtered sequence of all messages where the PDF file exists on disk."""
    base_data_dir = os.path.dirname(DB_PATH)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_file, date, preview, page_count, author FROM messages ORDER BY date ASC, source_file ASC")
        all_messages = [dict(row) for row in cursor.fetchall()]

    filtered = []
    skipped = 0
    for msg in all_messages:
        if os.path.exists(os.path.join(base_data_dir, msg["source_file"])):
            filtered.append(msg)
        else:
            skipped += 1

    print(f"READER SEQUENCE: Base dir: {base_data_dir}, Found: {len(filtered)}, Skipped: {skipped}")
    return filtered


# ---------------------------------------------------------------------------
# Firestore helpers (mutable user data)
# ---------------------------------------------------------------------------

def _bookmark_doc_id(user_id: str, source_file: str) -> str:
    """Stable document ID for a bookmark: hash of user_id+source_file."""
    return hashlib.md5(f"{user_id}::{source_file}".encode()).hexdigest()


def update_progress(user_id: str, source_file: str, messages_read: int) -> None:
    """Updates the user's reading progress in Firestore."""
    db = get_firestore_client()
    db.collection("user_progress").document(user_id).set({
        "user_id": user_id,
        "last_read_source_file": source_file,
        "messages_read": messages_read,
    })


def get_progress(user_id: str) -> dict[str, Any] | None:
    """Retrieves the user's reading progress from Firestore."""
    db = get_firestore_client()
    doc = db.collection("user_progress").document(user_id).get()
    return doc.to_dict() if doc.exists else None


def upsert_bookmark(user_id: str, source_file: str, notes: str) -> None:
    """Saves or updates a bookmark in Firestore."""
    db = get_firestore_client()
    doc_id = _bookmark_doc_id(user_id, source_file)
    db.collection("bookmarks").document(doc_id).set({
        "user_id": user_id,
        "source_file": source_file,
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def delete_bookmark(user_id: str, source_file: str) -> None:
    """Removes a bookmark from Firestore."""
    db = get_firestore_client()
    doc_id = _bookmark_doc_id(user_id, source_file)
    db.collection("bookmarks").document(doc_id).delete()


def get_bookmarks(user_id: str) -> list[dict[str, Any]]:
    """Retrieves all bookmarks for a user, enriched with message metadata from SQLite."""
    db = get_firestore_client()
    docs = db.collection("bookmarks").where(filter=FieldFilter("user_id", "==", user_id)).stream()
    bookmarks = [doc.to_dict() for doc in docs]

    # Enrich with message metadata from SQLite (read-only)
    result = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for bm in bookmarks:
            cursor.execute(
                "SELECT date, preview, author, page_count FROM messages WHERE source_file = ?",
                (bm["source_file"],),
            )
            msg = cursor.fetchone()
            if msg:
                result.append({
                    "source_file": bm["source_file"],
                    "notes": bm.get("notes", ""),
                    "created_at": bm.get("created_at", ""),
                    "date": msg["date"],
                    "preview": msg["preview"],
                    "author": msg["author"],
                    "page_count": msg["page_count"],
                })

    # Sort by message date ascending
    result.sort(key=lambda x: x.get("date", ""))
    return result


def save_chat_log(
    user_id: str,
    session_id: str,
    question: str,
    response: str,
    metadata: str | None = None,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    abhyasi_id: str = "",
) -> None:
    """Persists a chat interaction to Firestore (denormalized with user info)."""
    db = get_firestore_client()
    db.collection("chat_logs").add({
        "user_id": user_id,
        "session_id": session_id,
        "question": question,
        "response": response,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "abhyasi_id": abhyasi_id,
    })


def get_all_chat_logs(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieves all chat logs from Firestore for admin auditing."""
    db = get_firestore_client()
    query = (
        db.collection("chat_logs")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .offset(offset)
    )
    docs = query.stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def get_user_chat_logs(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Retrieves chat logs for a specific user from Firestore.
    Sorts in-memory to avoid requiring a composite index on (user_id, created_at).
    """
    db = get_firestore_client()
    logger.info(f"Fetching chat logs for user_id: {user_id}")
    
    # Simple query only requires a single-field index (automatic)
    try:
        query = (
            db.collection("chat_logs")
            .where(filter=FieldFilter("user_id", "==", user_id))
            .limit(200) # Fetch more than limit to allow sorting then slicing
        )
        docs = query.stream()
        logs = [{**doc.to_dict(), "id": doc.id} for doc in docs]
        
        logger.info(f"Retrieved {len(logs)} logs from Firestore for user {user_id}")
        
        # Sort in-memory: most recent first
        logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return logs[:limit]
    except Exception as e:
        logger.error(f"Error fetching logs for user {user_id}: {str(e)}")
        return []


def delete_chat_log(log_id: str, user_id: str | None = None) -> bool:
    """
    Removes a specific chat log from Firestore.
    If user_id is provided, ensures the log belongs to that user.
    """
    db = get_firestore_client()
    doc_ref = db.collection("chat_logs").document(log_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False
        
    data = doc.to_dict()
    if user_id and data.get("user_id") != user_id:
        return False
        
    doc_ref.delete()
    return True


def delete_user_data(user_id: str) -> None:
    """Cascades deletion of all Firestore data for a user (bookmarks, progress, chat_logs)."""
    db = get_firestore_client()

    # Delete progress
    db.collection("user_progress").document(user_id).delete()

    # Delete bookmarks
    bm_docs = db.collection("bookmarks").where(filter=FieldFilter("user_id", "==", user_id)).stream()
    for doc in bm_docs:
        doc.reference.delete()

    # Delete chat logs
    log_docs = db.collection("chat_logs").where(filter=FieldFilter("user_id", "==", user_id)).stream()
    for doc in log_docs:
        doc.reference.delete()
