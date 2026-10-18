import pytest
import os
import json
from unittest.mock import patch, MagicMock

# Create mock for ThreadingHTTPServer so we don't bind to port
with patch('http.server.ThreadingHTTPServer'):
    from app import TruthMirrorHandler

class DummyHandler:
    def __init__(self, method, path, headers=None, body=b""):
        self.command = method
        self.path = path
        self.headers = headers or {}
        self.rfile = MagicMock()
        self.rfile.read.return_value = body
        self.wfile = MagicMock()
        self.response_status = None
        self.response_body = b""
        self.ended = False

    def send_response(self, code):
        self.response_status = code

    def send_header(self, keyword, value):
        pass

    def end_headers(self):
        self.ended = True
        
    def _write_json(self, payload, status=200):
        self.response_status = status
        self.response_body = json.dumps(payload).encode("utf-8")

def test_auth_empty_password_rejection():
    handler = object.__new__(TruthMirrorHandler)
    # Override wfile
    handler.wfile = MagicMock()
    
    # Mock send_response and _write_json behavior
    response_data = {}
    def mock_write_json(payload, status=200):
        response_data['status'] = status
        response_data['payload'] = payload
    
    handler._write_json = mock_write_json
    handler.path = "/api/login"
    handler.headers = {"Content-Length": "100"}
    
    # Payload with valid user but empty password
    body = json.dumps({"email": "test@truthmirror.ai", "password": ""}).encode("utf-8")
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = body

    handler.do_POST()
        
    assert response_data['status'] == 401
    assert "Invalid" in response_data['payload']['error']

def test_dos_payload_too_large():
    handler = object.__new__(TruthMirrorHandler)
    handler.requestline = "POST /api/login HTTP/1.1"
    
    response_data = {}
    def mock_write_json(payload, status=200):
        response_data['status'] = status
        response_data['payload'] = payload
    
    handler._write_json = mock_write_json
    handler.path = "/api/login"
    handler.headers = {"Content-Length": str(10 * 1024 * 1024)} # 10MB
    
    handler.do_POST()
    
    assert response_data['status'] == 413
    assert "Payload too large" in response_data['payload']['error']


def test_flask_auth_empty_password_rejection(tmp_path):
    from app import create_app
    db_file = str(tmp_path / "test_sec.db")
    app_instance = create_app(db_path=db_file)
    app_instance.config["TESTING"] = True
    client = app_instance.test_client()

    resp = client.post("/api/login", json={"email": "test@truthmirror.ai", "password": ""})
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


def test_flask_payload_too_large_rejection(tmp_path):
    from app import create_app
    db_file = str(tmp_path / "test_sec.db")
    app_instance = create_app(db_path=db_file)
    app_instance.config["TESTING"] = True
    client = app_instance.test_client()

    large_body = "x" * (6 * 1024 * 1024)  # 6MB > 5MB limit
    resp = client.post("/api/login", data=large_body, content_type="application/json")
    assert resp.status_code == 413
    data = resp.get_json()
    assert "Payload too large" in data.get("error", "")

