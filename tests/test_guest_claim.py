import pytest
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def app_instance(tmp_path):
    db_file = str(tmp_path / "test_guest.db")
    with patch("app.send_verification_email", return_value=True):
        test_app = create_app(db_path=db_file)
        test_app.config["TESTING"] = True
        test_app.config["RATELIMIT_ENABLED"] = False
        return test_app


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


def test_guest_verify_accepts_unauthenticated_request(client):
    with patch("app._executor.submit") as mock_submit:
        mock_future = MagicMock()
        mock_submit.return_value = mock_future
        
        resp = client.post(
            "/api/guest-verify",
            json={"claim": "Global trade increased in 2024", "request_id": "guest-req-101"},
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert data.get("status") == "Started"
        assert data.get("request_id") == "guest-req-101"
        assert mock_submit.called


def test_guest_status_accessible_with_guest_flag(client):
    # Without auth or guest -> 401
    resp_unauth = client.get("/api/status?request_id=guest-req-101")
    assert resp_unauth.status_code == 401

    # With guest=1 -> 200
    resp_guest = client.get("/api/status?request_id=guest-req-101&guest=1")
    assert resp_guest.status_code == 200
    data = resp_guest.get_json()
    assert isinstance(data, dict)


def test_guest_verify_empty_claim_rejected(client):
    resp_empty = client.post(
        "/api/guest-verify",
        json={"claim": "", "request_id": "guest-req-empty"},
    )
    assert resp_empty.status_code == 400
    data_empty = resp_empty.get_json()
    assert "error" in data_empty

    resp_spaces = client.post(
        "/api/guest-verify",
        json={"claim": "   ", "request_id": "guest-req-spaces"},
    )
    assert resp_spaces.status_code == 400
    data_spaces = resp_spaces.get_json()
    assert "error" in data_spaces


def test_authenticated_verify_still_works(client):
    # Unauthenticated /api/verify -> 401
    resp_unauth = client.post(
        "/api/verify",
        json={"claim": "Geopolitical claim requiring authentication"},
    )
    assert resp_unauth.status_code == 401

    # Authenticate as seeded test user
    login_resp = client.post(
        "/api/login",
        json={"email": "test@truthmirror.ai", "password": "truthmirror26"},
    )
    assert login_resp.status_code == 200
    token = login_resp.get_json()["token"]

    with patch("app._executor.submit") as mock_submit:
        mock_future = MagicMock()
        mock_submit.return_value = mock_future
        
        resp_auth = client.post(
            "/api/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"claim": "Geopolitical claim requiring authentication", "request_id": "auth-req-202"},
        )
        assert resp_auth.status_code == 202
        data = resp_auth.get_json()
        assert data.get("status") == "Started"
        assert data.get("request_id") == "auth-req-202"
