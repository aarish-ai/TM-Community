import json
import pytest
from unittest.mock import patch, MagicMock
from truth_mirror.db import get_db, get_verification_code


@pytest.fixture
def mock_send_email():
    with patch("app.send_verification_email", return_value=True) as mock_send:
        yield mock_send


@pytest.fixture
def app_instance(tmp_path, mock_send_email):
    from app import create_app
    db_file = str(tmp_path / "test_routes.db")
    test_app = create_app(
        db_path=db_file,
        test_config={"TESTING": True, "RATELIMIT_ENABLED": False},
    )
    return test_app


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


def test_register_success(client, mock_send_email):
    payload = {
        "email": "alice@example.com",
        "password": "securepassword123",
    }
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert "verification_sent" in (data.get("status") or "")
    assert mock_send_email.called


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "password": "securepassword123",
    }
    resp1 = client.post("/api/register", json=payload)
    assert resp1.status_code == 201

    payload2 = {
        "email": "dup@example.com",
        "password": "securepassword123",
    }
    resp2 = client.post("/api/register", json=payload2)
    assert resp2.status_code == 409
    data = resp2.get_json()
    assert data.get("code") == "email_taken" or "email" in data.get("error", "").lower()


def test_register_invalid_password(client):
    payload = {
        "email": "shortpw@example.com",
        "password": "123",
    }
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("code") == "invalid_password" or "password" in data.get("error", "").lower()


def test_register_invalid_email(client):
    payload = {
        "email": "not-a-valid-email",
        "password": "securepassword123",
    }
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("code") == "invalid_email" or "email" in data.get("error", "").lower()


def test_register_missing_fields(client):
    resp = client.post("/api/register", json={"email": "missing@example.com"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_verify_email_success(client, app_instance):
    # First register
    client.post(
        "/api/register",
        json={
            "email": "bob@example.com",
            "password": "securepassword123",
        },
    )
    # Fetch code from DB
    db_path = app_instance.config["AUTH_DB_PATH"]
    conn = get_db(db_path)
    record = get_verification_code(conn, "bob@example.com")
    conn.close()
    assert record is not None
    code = record["code"]

    resp = client.post(
        "/api/verify-email",
        json={"email": "bob@example.com", "code": code},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert data.get("email") == "bob@example.com"


def test_verify_email_wrong_code(client):
    client.post(
        "/api/register",
        json={
            "email": "charlie@example.com",
            "password": "securepassword123",
        },
    )
    resp = client.post(
        "/api/verify-email",
        json={"email": "charlie@example.com", "code": "000000"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("code") == "invalid" or "invalid" in data.get("error", "").lower()


def test_login_seeded_test_user(client):
    resp = client.post(
        "/api/login",
        json={"email": "test@truthmirror.ai", "password": "truthmirror26"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert data.get("email") == "test@truthmirror.ai"


def test_login_wrong_password(client):
    resp = client.post(
        "/api/login",
        json={"email": "test@truthmirror.ai", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


def test_login_not_found(client):
    resp = client.post(
        "/api/login",
        json={"email": "nonexistent_user@example.com", "password": "somepassword"},
    )
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


def test_status_requires_auth_unless_guest(client):
    # Without auth or guest -> 401
    resp = client.get("/api/status")
    assert resp.status_code == 401

    # With guest=1 -> 200
    resp_guest = client.get("/api/status?guest=1")
    assert resp_guest.status_code == 200


def test_status_with_valid_bearer_token(client):
    # Log in as seeded user to get token
    login_resp = client.post(
        "/api/login",
        json={"email": "test@truthmirror.ai", "password": "truthmirror26"},
    )
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_get_root_serves_landing(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")


def test_get_app_serves_index(client):
    resp = client.get("/app")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")


def test_validate_session_unauthorized_without_header(client):
    resp = client.get("/api/validate")
    assert resp.status_code == 401
    data = resp.get_json()
    assert data.get("error") == "Unauthorized"


def test_validate_session_unauthorized_with_invalid_token(client):
    resp = client.get("/api/validate", headers={"Authorization": "Bearer invalid_token"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data.get("error") == "Unauthorized"


def test_validate_session_authorized(client):
    login_resp = client.post(
        "/api/login",
        json={"email": "test@truthmirror.ai", "password": "truthmirror26"},
    )
    token = login_resp.get_json()["token"]

    resp = client.get("/api/validate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("valid") is True
    assert data.get("email") == "test@truthmirror.ai"


def test_app_does_not_seed_in_production_mode(tmp_path, monkeypatch):
    from app import create_app
    from truth_mirror.db import get_db, get_user_by_email

    monkeypatch.delenv("SEED_TEST_USERS", raising=False)
    db_file = str(tmp_path / "prod_test.db")
    create_app(db_path=db_file, test_config={"TESTING": False})

    conn = get_db(db_file)
    try:
        test_user = get_user_by_email(conn, "test@truthmirror.ai")
        assert test_user is None
    finally:
        conn.close()


def test_app_seeds_when_env_flag_set(tmp_path, monkeypatch):
    from app import create_app
    from truth_mirror.db import get_db, get_user_by_email

    monkeypatch.setenv("SEED_TEST_USERS", "true")
    db_file = str(tmp_path / "flag_test.db")
    create_app(db_path=db_file, test_config={"TESTING": False})

    conn = get_db(db_file)
    try:
        test_user = get_user_by_email(conn, "test@truthmirror.ai")
        assert test_user is not None
    finally:
        conn.close()


