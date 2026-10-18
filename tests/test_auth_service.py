import time
import pytest
from truth_mirror.db import get_db, get_user_by_email, store_verification_code
from truth_mirror.auth_service import (
    hash_password,
    check_password,
    generate_code,
    register_user,
    verify_email_code,
    authenticate_user,
    login_user,
    seed_test_user,
)


@pytest.fixture
def db_conn(tmp_path):
    db_file = str(tmp_path / "test_auth.db")
    conn = get_db(db_file)
    try:
        yield conn
    finally:
        conn.close()


def test_hash_password_returns_string():
    hashed = hash_password("secret123")
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != "secret123"


def test_check_password_correct():
    hashed = hash_password("my_secure_password")
    assert check_password("my_secure_password", hashed) is True


def test_check_password_wrong():
    hashed = hash_password("my_secure_password")
    assert check_password("wrong_password", hashed) is False


def test_generate_code_is_six_digits():
    code = generate_code()
    assert isinstance(code, str)
    assert len(code) == 6
    assert code.isdigit()


def test_generate_code_is_random():
    codes = {generate_code() for _ in range(50)}
    assert len(codes) > 1


def test_register_user_success(db_conn):
    res = register_user(db_conn, "new@example.com", "password123")
    assert res.get("success") is True
    assert "user_id" in res
    assert res["user_id"] > 0
    assert "code" in res or "verification_code" in res


def test_register_user_duplicate_email(db_conn):
    register_user(db_conn, "dup@example.com", "password123")
    res = register_user(db_conn, "dup@example.com", "password123")
    assert res.get("success") is False
    assert "error" in res
    assert "email" in res["error"].lower()


def test_register_user_invalid_email(db_conn):
    res = register_user(db_conn, "not-an-email", "password123")
    assert res.get("success") is False
    assert "error" in res


def test_register_user_short_password(db_conn):
    res = register_user(db_conn, "user@example.com", "123")
    assert res.get("success") is False
    assert "error" in res


def test_verify_email_code_success(db_conn):
    reg = register_user(db_conn, "verify@example.com", "password123")
    code = reg.get("verification_code") or reg.get("code")
    res = verify_email_code(db_conn, "verify@example.com", code)
    assert res.get("success") is True


def test_verify_email_code_wrong_code(db_conn):
    register_user(db_conn, "wrongcode@example.com", "password123")
    res = verify_email_code(db_conn, "wrongcode@example.com", "000000")
    assert res.get("success") is False
    assert "error" in res


def test_verify_email_code_expired(db_conn):
    register_user(db_conn, "expired@example.com", "password123")
    store_verification_code(db_conn, "expired@example.com", "123456", time.time() - 100.0)
    res = verify_email_code(db_conn, "expired@example.com", "123456")
    assert res.get("success") is False
    assert "error" in res
    assert "expired" in res["error"].lower()


def test_verify_email_marks_user_verified(db_conn):
    reg = register_user(db_conn, "markverified@example.com", "password123")
    code = reg.get("verification_code") or reg.get("code")
    user_before = get_user_by_email(db_conn, "markverified@example.com")
    assert user_before["is_verified"] == 0

    verify_email_code(db_conn, "markverified@example.com", code)

    user_after = get_user_by_email(db_conn, "markverified@example.com")
    assert user_after["is_verified"] == 1


def test_login_user_by_email(db_conn):
    reg = register_user(db_conn, "login_email@example.com", "password123")
    code = reg.get("verification_code") or reg.get("code")
    verify_email_code(db_conn, "login_email@example.com", code)

    res = login_user(db_conn, "login_email@example.com", "password123")
    assert res.get("success") is True
    assert "user" in res
    assert res["user"]["email"] == "login_email@example.com"


def test_authenticate_user_success(db_conn):
    reg = register_user(db_conn, "auth@example.com", "password123")
    code = reg.get("verification_code") or reg.get("code")
    verify_email_code(db_conn, "auth@example.com", code)

    res = authenticate_user(db_conn, "auth@example.com", "password123")
    assert res.get("success") is True
    assert res["user"]["email"] == "auth@example.com"


def test_login_user_not_found(db_conn):
    res = login_user(db_conn, "nonexistent@example.com", "password123")
    assert res.get("success") is False
    assert "error" in res


def test_login_user_wrong_password(db_conn):
    reg = register_user(db_conn, "wrongpw@example.com", "password123")
    code = reg.get("verification_code") or reg.get("code")
    verify_email_code(db_conn, "wrongpw@example.com", code)

    res = login_user(db_conn, "wrongpw@example.com", "wrong_pass")
    assert res.get("success") is False
    assert "error" in res


def test_login_user_not_verified(db_conn):
    register_user(db_conn, "unverified@example.com", "password123")
    res = login_user(db_conn, "unverified@example.com", "password123")
    assert res.get("success") is False
    assert "error" in res
    assert "verified" in res["error"].lower()


def test_seed_test_user_creates_verified_user(db_conn):
    seed_test_user(db_conn)
    user = get_user_by_email(db_conn, "test@truthmirror.ai")
    assert user is not None
    assert user["is_verified"] == 1

    res = login_user(db_conn, "test@truthmirror.ai", "truthmirror26")
    assert res.get("success") is True
    assert res["user"]["email"] == "test@truthmirror.ai"


def test_seed_test_user_idempotent(db_conn):
    seed_test_user(db_conn)
    seed_test_user(db_conn)
    user = get_user_by_email(db_conn, "test@truthmirror.ai")
    assert user is not None
    assert user["is_verified"] == 1


def test_update_user_password(db_conn):
    from truth_mirror.db import create_user, update_user_password, get_user_by_email
    create_user(db_conn, "admin@example.com", "old_hash")

    updated = update_user_password(db_conn, "admin@example.com", "new_hash")
    assert updated is True

    user = get_user_by_email(db_conn, "admin@example.com")
    assert user["password_hash"] == "new_hash"


def test_update_user_password_nonexistent_user(db_conn):
    from truth_mirror.db import update_user_password
    updated = update_user_password(db_conn, "nobody@example.com", "new_hash")
    assert updated is False


def test_create_or_update_admin_new_user(db_conn):
    from truth_mirror.auth_service import create_or_update_admin
    res = create_or_update_admin(db_conn, "admin@truthmirror.ai", "StrongPassword123")
    assert res["success"] is True
    assert res["action"] == "created"

    user = get_user_by_email(db_conn, "admin@truthmirror.ai")
    assert user is not None
    assert user["is_verified"] == 1
    assert check_password("StrongPassword123", user["password_hash"]) is True


def test_create_or_update_admin_existing_user(db_conn):
    from truth_mirror.auth_service import create_or_update_admin
    create_or_update_admin(db_conn, "admin@truthmirror.ai", "InitialPassword123")

    res = create_or_update_admin(db_conn, "admin@truthmirror.ai", "UpdatedPassword456")
    assert res["success"] is True
    assert res["action"] == "updated"

    user = get_user_by_email(db_conn, "admin@truthmirror.ai")
    assert check_password("UpdatedPassword456", user["password_hash"]) is True


def test_create_or_update_admin_invalid_inputs(db_conn):
    from truth_mirror.auth_service import create_or_update_admin
    res_bad_email = create_or_update_admin(db_conn, "not-an-email", "ValidPass123")
    assert res_bad_email["success"] is False
    assert "Invalid email" in res_bad_email["error"]

    res_short_pw = create_or_update_admin(db_conn, "admin@truthmirror.ai", "123")
    assert res_short_pw["success"] is False
    assert "Password must be at least 6 characters" in res_short_pw["error"]


def test_seed_test_user_contains_no_personal_emails(db_conn):
    seed_test_user(db_conn)
    cursor = db_conn.cursor()
    cursor.execute("SELECT email FROM users")
    emails = [row["email"] for row in cursor.fetchall()]
    # Ensure ONLY generic test domains are seeded, never personal Gmail/personal addresses
    for email in emails:
        assert email.endswith("@truthmirror.ai") or email.endswith("@truth-mirror.net")
        assert not email.endswith("@gmail.com")




