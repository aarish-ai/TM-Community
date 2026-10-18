"""SQLite database persistence layer for Truth Mirror authentication."""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_db(db_path: str = "truth_mirror.db") -> sqlite3.Connection:
    """Connect to SQLite database and ensure auth schema exists."""
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Initialize database tables for authentication."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                code TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_user(
    conn: sqlite3.Connection, email: str, password_hash: str
) -> int:
    """Create a new user and return the generated user ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, is_verified) VALUES (?, ?, 0)",
        (email, password_hash),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_user_by_email(
    conn: sqlite3.Connection, email: str
) -> Optional[sqlite3.Row]:
    """Retrieve user record by email."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()


def mark_user_verified(conn: sqlite3.Connection, email: str) -> None:
    """Mark user as email-verified."""
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    conn.commit()


def update_user_password(
    conn: sqlite3.Connection, email: str, password_hash: str
) -> bool:
    """Update password hash for an existing user. Returns True if updated, False if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (password_hash, email.strip()),
    )
    conn.commit()
    return cursor.rowcount > 0



def store_verification_code(
    conn: sqlite3.Connection, email: str, code: str, expires_at: float
) -> None:
    """Store or update verification code for an email address."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO verification_codes (email, code, expires_at, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET
            code = excluded.code,
            expires_at = excluded.expires_at,
            created_at = CURRENT_TIMESTAMP
        """,
        (email, code, expires_at),
    )
    conn.commit()


def get_verification_code(
    conn: sqlite3.Connection, email: str
) -> Optional[sqlite3.Row]:
    """Retrieve stored verification code record for an email address."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verification_codes WHERE email = ?", (email,))
    return cursor.fetchone()


def delete_verification_code(conn: sqlite3.Connection, email: str) -> None:
    """Delete verification code record for an email address."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM verification_codes WHERE email = ?", (email,))
    conn.commit()
