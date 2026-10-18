import subprocess
import sys
import pytest
from truth_mirror.db import get_db, get_user_by_email
from truth_mirror.auth_service import check_password


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "cli_test.db")


def test_cli_create_admin_success(test_db_path):
    cmd = [
        sys.executable,
        "scripts/manage_users.py",
        "create-admin",
        "--email",
        "admin@domain.com",
        "--password",
        "StrongPass2026",
        "--db-path",
        test_db_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "created and verified successfully" in res.stdout

    conn = get_db(test_db_path)
    try:
        user = get_user_by_email(conn, "admin@domain.com")
        assert user is not None
        assert user["is_verified"] == 1
        assert check_password("StrongPass2026", user["password_hash"]) is True
    finally:
        conn.close()


def test_cli_reset_password_success(test_db_path):
    # First create
    subprocess.run(
        [
            sys.executable,
            "scripts/manage_users.py",
            "create-admin",
            "--email",
            "admin@domain.com",
            "--password",
            "OldPass123",
            "--db-path",
            test_db_path,
        ],
        check=True,
    )

    # Then reset
    cmd = [
        sys.executable,
        "scripts/manage_users.py",
        "reset-password",
        "--email",
        "admin@domain.com",
        "--password",
        "NewPass456",
        "--db-path",
        test_db_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "updated successfully" in res.stdout

    conn = get_db(test_db_path)
    try:
        user = get_user_by_email(conn, "admin@domain.com")
        assert check_password("NewPass456", user["password_hash"]) is True
    finally:
        conn.close()


def test_cli_invalid_email_fails(test_db_path):
    cmd = [
        sys.executable,
        "scripts/manage_users.py",
        "create-admin",
        "--email",
        "invalid-email",
        "--password",
        "ValidPass123",
        "--db-path",
        test_db_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Invalid email" in res.stderr
