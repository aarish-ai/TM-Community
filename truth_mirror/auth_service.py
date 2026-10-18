"""Authentication and user management business logic for Truth Mirror."""

from __future__ import annotations

import re
import secrets
import sqlite3
import time
from typing import Any, Dict, Optional

import bcrypt

try:
    from truth_mirror.db import (
        create_user,
        get_user_by_email,
        mark_user_verified,
        update_user_password,
        store_verification_code,
        get_verification_code,
        delete_verification_code,
    )
except ImportError:
    from db import (  # type: ignore
        create_user,
        get_user_by_email,
        mark_user_verified,
        update_user_password,
        store_verification_code,
        get_verification_code,
        delete_verification_code,
    )

TEST_USER_EMAIL = "test@truthmirror.ai"
TEST_USER_PASSWORD = "truthmirror26"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def generate_code() -> str:
    """Generate a cryptographically secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def register_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Register a new user, hash password, and store a verification code."""
    email = email.strip()

    if not email or not EMAIL_REGEX.match(email):
        return {"success": False, "error": "Invalid email address format."}

    if not password or len(password) < 6:
        return {
            "success": False,
            "error": "Password must be at least 6 characters long.",
        }

    if get_user_by_email(conn, email) is not None:
        return {"success": False, "error": "Email is already registered."}

    pw_hash = hash_password(password)
    user_id = create_user(conn, email, pw_hash)

    code = generate_code()
    expires_at = time.time() + 900.0  # 15 minutes
    store_verification_code(conn, email, code, expires_at)

    return {
        "success": True,
        "user_id": user_id,
        "user": {"id": user_id, "email": email},
        "verification_code": code,
        "message": "User registered successfully. Verification code generated.",
    }


def verify_email_code(
    conn: sqlite3.Connection,
    email: str,
    code: str,
) -> Dict[str, Any]:
    """Verify an email code and activate the user's account."""
    email = email.strip()
    code = code.strip()

    record = get_verification_code(conn, email)
    if record is None:
        return {
            "success": False,
            "error": "Verification code not found or already verified.",
        }

    if record["code"] != code:
        return {"success": False, "error": "Invalid verification code."}

    if record["expires_at"] < time.time():
        return {"success": False, "error": "Verification code has expired."}

    mark_user_verified(conn, email)
    delete_verification_code(conn, email)

    return {"success": True, "message": "Email verified successfully."}


def authenticate_user(
    conn: sqlite3.Connection,
    identifier: str,
    password: str,
) -> Dict[str, Any]:
    """Authenticate a user by email."""
    identifier = identifier.strip()
    if not identifier or not password:
        return {"success": False, "error": "Email and password required."}

    user = get_user_by_email(conn, identifier)
    if user is None:
        return {"success": False, "error": "User not found."}

    if not check_password(password, user["password_hash"]):
        return {"success": False, "error": "Invalid password."}

    if not user["is_verified"]:
        return {
            "success": False,
            "error": "Email is not verified. Please verify your email.",
            "is_verified": False,
        }

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "is_verified": bool(user["is_verified"]),
        },
    }


login_user = authenticate_user


def seed_test_user(conn: sqlite3.Connection) -> None:
    """Ensure standard test users exist and are verified for automated tests."""
    users_to_seed = [
        (TEST_USER_EMAIL, TEST_USER_PASSWORD),
        ("test@truth-mirror.net", TEST_USER_PASSWORD),
    ]
    for email, pwd in users_to_seed:
        existing = get_user_by_email(conn, email)
        if existing is None:
            pw_hash = hash_password(pwd)
            create_user(conn, email, pw_hash)
            mark_user_verified(conn, email)
        elif not existing["is_verified"]:
            mark_user_verified(conn, email)


def create_or_update_admin(
    conn: sqlite3.Connection,
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Create a verified admin user or update an existing user's password."""
    email = email.strip()
    if not email or not EMAIL_REGEX.match(email):
        return {"success": False, "error": "Invalid email address format."}

    if not password or len(password) < 6:
        return {
            "success": False,
            "error": "Password must be at least 6 characters long.",
        }

    pw_hash = hash_password(password)
    existing = get_user_by_email(conn, email)
    if existing is None:
        user_id = create_user(conn, email, pw_hash)
        mark_user_verified(conn, email)
        return {
            "success": True,
            "action": "created",
            "user_id": user_id,
            "email": email,
            "message": f"Admin account {email} created and verified successfully.",
        }
    else:
        update_user_password(conn, email, pw_hash)
        if not existing["is_verified"]:
            mark_user_verified(conn, email)
        return {
            "success": True,
            "action": "updated",
            "user_id": existing["id"],
            "email": email,
            "message": f"Password for {email} updated successfully.",
        }


