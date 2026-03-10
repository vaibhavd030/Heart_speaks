"""
Repository Layer for Heart Speaks.

Stores full-text representations and rich metadata of spiritual messages.
This enables the frontend to fetch complete contexts for citations,
rather than just chunks returned by the vector store.
"""

import os
import sqlite3
import uuid
from typing import Any

from loguru import logger

from heart_speaks.config import settings

DB_PATH = os.path.join(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", settings.data_dir.replace("./", "")
        )
    ),
    "messages.db",
)


def get_db_connection() -> sqlite3.Connection:
    """Returns a configured SQLite connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the SQLite database schema."""
    logger.info(f"Initializing message repository at {DB_PATH}")
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id TEXT PRIMARY KEY,
                last_read_source_file TEXT,
                messages_read INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                source_file TEXT PRIMARY KEY,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_file) REFERENCES messages(source_file)
            )
        """)
        conn.commit()


def clear_db() -> None:
    """Drops the messages table to allow fresh ingestion."""
    logger.warning("Clearing message repository...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS messages")
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
    """
    Inserts or updates a full spiritual message in the repository.
    """
    if topics is None:
        topics = []

    topics_str = ",".join(topics)
    # Generate a preview: first ~150 chars, up to the last word boundary
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
            (
                str(uuid.uuid4()),
                source_file,
                author,
                date,
                full_text,
                preview,
                page_count,
                topics_str,
            ),
        )
        conn.commit()


def get_message_by_source(source_file: str) -> dict[str, Any] | None:
    """Retrieves a message based on its original PDF filename."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE source_file = ?", (source_file,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_stats() -> dict[str, Any]:
    """Retrieves basic EDA statistics from the repository."""
    stats = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) as total_messages, SUM(page_count) as total_pages FROM messages"
        )
        totals = cursor.fetchone()
        stats["total_messages"] = totals["total_messages"] if totals else 0
        stats["total_pages"] = totals["total_pages"] if totals else 0

        # Messages by Year (extracted from YYYY-MM-DD date string)
        cursor.execute("""
            SELECT substr(date, 1, 4) as year, COUNT(*) as count 
            FROM messages 
            WHERE date IS NOT NULL AND date != '' AND date != 'Unknown'
            GROUP BY year ORDER BY year
        """)
        stats["by_year"] = [dict(row) for row in cursor.fetchall()]

        # Messages by Month
        cursor.execute("""
            SELECT substr(date, 6, 2) as month, COUNT(*) as count 
            FROM messages 
            WHERE date IS NOT NULL AND date != '' AND date != 'Unknown'
            GROUP BY month ORDER BY month
        """)
        stats["by_month"] = [dict(row) for row in cursor.fetchall()]

        # Messages by Author
        cursor.execute("""
            SELECT author, COUNT(*) as count 
            FROM messages 
            GROUP BY author ORDER BY count DESC
        """)
        stats["by_author"] = [dict(row) for row in cursor.fetchall()]

    return stats


def search_messages(query: str = "", page: int = 1, limit: int = 50) -> dict[str, Any]:
    """Retrieves a paginated list of messages, optionally filtered by a text query."""
    offset = (page - 1) * limit
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if query:
            search_pattern = f"%{query}%"
            # Count total matching
            cursor.execute(
                """
                SELECT COUNT(*) as total FROM messages 
                WHERE full_text LIKE ? OR author LIKE ? OR source_file LIKE ?
            """,
                (search_pattern, search_pattern, search_pattern),
            )
            total = cursor.fetchone()["total"]

            # Get paginated data
            cursor.execute(
                """
                SELECT message_id, source_file, author, date, preview, page_count 
                FROM messages 
                WHERE full_text LIKE ? OR author LIKE ? OR source_file LIKE ?
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """,
                (search_pattern, search_pattern, search_pattern, limit, offset),
            )
        else:
            # Count total
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total = cursor.fetchone()["total"]

            # Get paginated data
            cursor.execute(
                """
                SELECT message_id, source_file, author, date, preview, page_count 
                FROM messages 
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

        rows = cursor.fetchall()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "messages": [dict(row) for row in rows],
    }


def get_reader_sequence() -> list[dict[str, Any]]:
    """Returns a sequence of all messages ordered by date (oldest first)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Order by date ASC. Note: 'Unknown' or missing dates will be handled by SQLite sorting.
        cursor.execute("""
            SELECT source_file, date, preview, page_count, author 
            FROM messages 
            ORDER BY date ASC, source_file ASC
        """)
        return [dict(row) for row in cursor.fetchall()]


def update_progress(user_id: str, source_file: str, messages_read: int) -> None:
    """Updates the user's reading progress."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_progress (user_id, last_read_source_file, messages_read)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_read_source_file=excluded.last_read_source_file,
                messages_read=excluded.messages_read
        """,
            (user_id, source_file, messages_read),
        )
        conn.commit()


def get_progress(user_id: str) -> dict[str, Any] | None:
    """Retrieves the user's reading progress."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def upsert_bookmark(source_file: str, notes: str) -> None:
    """Saves or updates a bookmark and associated notes for a message."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bookmarks (source_file, notes)
            VALUES (?, ?)
            ON CONFLICT(source_file) DO UPDATE SET
                notes=excluded.notes,
                created_at=CURRENT_TIMESTAMP
        """,
            (source_file, notes),
        )
        conn.commit()


def delete_bookmark(source_file: str) -> None:
    """Removes a bookmark."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookmarks WHERE source_file = ?", (source_file,))
        conn.commit()


def get_bookmarks() -> list[dict[str, Any]]:
    """Retrieves all bookmarks with message context, ordered by message date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.source_file, b.notes, b.created_at, m.date, m.preview, m.author, m.page_count
            FROM bookmarks b
            JOIN messages m ON b.source_file = m.source_file
            ORDER BY m.date ASC, b.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
