"""
Repository Layer for Heart Speaks.

Stores full-text representations and rich metadata of spiritual messages.
This enables the frontend to fetch complete contexts for citations,
rather than just chunks returned by the vector store.
"""
import os
import sqlite3
import uuid

from loguru import logger

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "messages.db")

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
        cursor.execute('''
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
        ''')
        conn.commit()

def clear_db() -> None:
    """Drops the messages table to allow fresh ingestion."""
    logger.warning("Clearing message repository...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS messages')
        conn.commit()
    init_db()

def upsert_message(source_file: str, full_text: str, author: str = "Unknown", date: str = "", page_count: int = 1, topics: list[str] | None = None) -> None:
    """
    Inserts or updates a full spiritual message in the repository.
    """
    if topics is None:
        topics = []
        
    topics_str = ",".join(topics)
    # Generate a preview: first ~150 chars, up to the last word boundary
    preview = full_text[:150].rsplit(' ', 1)[0] + "..." if len(full_text) > 150 else full_text
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (message_id, source_file, author, date, full_text, preview, page_count, topics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_file) DO UPDATE SET
                full_text=excluded.full_text,
                author=excluded.author,
                date=excluded.date,
                preview=excluded.preview,
                page_count=excluded.page_count,
                topics=excluded.topics
        ''', (str(uuid.uuid4()), source_file, author, date, full_text, preview, page_count, topics_str))
        conn.commit()

from typing import Any

def get_message_by_source(source_file: str) -> dict[str, Any] | None:
    """Retrieves a message based on its original PDF filename."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages WHERE source_file = ?', (source_file,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
