import sqlite3
import pytest
from truth_mirror.db import (
    get_db,
    create_user,
    get_user_by_email,
    mark_user_verified,
    store_verification_code,
    get_verification_code,
    delete_verification_code,
)


def test_get_db_creates_schema(tmp_path):
    db_file = str(tmp_path / "test_schema.db")
    conn = get_db(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "users" in tables
    assert "verification_codes" in tables
    conn.close()


def test_create_user_returns_id(tmp_path):
    db_file = str(tmp_path / "test_user.db")
    conn = get_db(db_file)
    user_id = create_user(
        conn,
        email="test@example.com",
        password_hash="hashed_pw_123",
    )
    assert isinstance(user_id, int)
    assert user_id > 0
    conn.close()


def test_create_user_duplicate_email_raises(tmp_path):
    db_file = str(tmp_path / "test_dup_email.db")
    conn = get_db(db_file)
    create_user(
        conn,
        email="dup@example.com",
        password_hash="pw1",
    )
    with pytest.raises(sqlite3.IntegrityError):
        create_user(
            conn,
            email="dup@example.com",
            password_hash="pw2",
        )
    conn.close()


def test_get_user_by_email_returns_row(tmp_path):
    db_file = str(tmp_path / "test_get_email.db")
    conn = get_db(db_file)
    create_user(
        conn,
        email="findme@example.com",
        password_hash="secret_hash",
    )
    row = get_user_by_email(conn, "findme@example.com")
    assert row is not None
    assert row["email"] == "findme@example.com"
    assert row["password_hash"] == "secret_hash"
    assert row["is_verified"] == 0
    conn.close()


def test_get_user_by_email_missing_returns_none(tmp_path):
    db_file = str(tmp_path / "test_missing_email.db")
    conn = get_db(db_file)
    row = get_user_by_email(conn, "missing@example.com")
    assert row is None
    conn.close()


def test_mark_user_verified(tmp_path):
    db_file = str(tmp_path / "test_verify.db")
    conn = get_db(db_file)
    create_user(
        conn,
        email="verify_me@example.com",
        password_hash="pw",
    )
    row = get_user_by_email(conn, "verify_me@example.com")
    assert row["is_verified"] == 0

    mark_user_verified(conn, "verify_me@example.com")
    row_updated = get_user_by_email(conn, "verify_me@example.com")
    assert row_updated["is_verified"] == 1
    conn.close()


def test_store_and_get_verification_code(tmp_path):
    db_file = str(tmp_path / "test_code.db")
    conn = get_db(db_file)
    store_verification_code(conn, "code_user@example.com", "123456", 1700000000.0)
    row = get_verification_code(conn, "code_user@example.com")
    assert row is not None
    assert row["email"] == "code_user@example.com"
    assert row["code"] == "123456"
    assert row["expires_at"] == 1700000000.0
    conn.close()


def test_store_verification_code_replaces_existing(tmp_path):
    db_file = str(tmp_path / "test_code_replace.db")
    conn = get_db(db_file)
    store_verification_code(conn, "replace@example.com", "111111", 1700000000.0)
    store_verification_code(conn, "replace@example.com", "999999", 1700005000.0)
    row = get_verification_code(conn, "replace@example.com")
    assert row is not None
    assert row["code"] == "999999"
    assert row["expires_at"] == 1700005000.0
    conn.close()


def test_delete_verification_code(tmp_path):
    db_file = str(tmp_path / "test_delete_code.db")
    conn = get_db(db_file)
    store_verification_code(conn, "delete_me@example.com", "654321", 1700000000.0)
    assert get_verification_code(conn, "delete_me@example.com") is not None

    delete_verification_code(conn, "delete_me@example.com")
    assert get_verification_code(conn, "delete_me@example.com") is None
    conn.close()
