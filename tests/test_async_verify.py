import json
import pytest
from unittest.mock import MagicMock
from app import TruthMirrorHandler
import truth_mirror.pipeline_status as pipeline_status

def test_async_verify_endpoint_returns_202(monkeypatch):
    """Test that /api/verify returns 202 Accepted and a request_id immediately."""
    handler = TruthMirrorHandler.__new__(TruthMirrorHandler)
    
    req_body = b'{"claim": "Is the sky blue?"}'
    handler.headers = {"Content-Length": str(len(req_body))}
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = req_body
    handler.path = "/api/verify"

    monkeypatch.setattr("app._check_session", MagicMock(return_value=True))

    written_payloads = []
    def mock_write_json(payload, status=200):
        written_payloads.append((payload, status))
    handler._write_json = mock_write_json

    mock_pipeline = MagicMock()
    mock_pipeline.verify.return_value = {"verdict": "Real"}
    # We don't want the mock pipeline to actually block if called synchronously.
    # But we want to ensure do_POST finishes without waiting for the pipeline to finish if it's async.
    handler.pipeline = mock_pipeline

    handler.do_POST()

    assert len(written_payloads) == 1
    payload, status = written_payloads[0]
    assert status == 202
    assert payload.get("status") == "Started"
    assert "request_id" in payload

def test_status_endpoint_returns_result(monkeypatch):
    """Test that /api/status returns the final result once available."""
    # First set a mock result in pipeline_status
    req_id = "test-12345"
    expected_result = {"verdict": "Real", "confidence": 0.95}
    
    # We expect set_result to be implemented and available
    pipeline_status.set_result(req_id, expected_result)
    
    # Now simulate a GET to /api/status
    handler = TruthMirrorHandler.__new__(TruthMirrorHandler)
    handler.path = f"/api/status?request_id={req_id}"
    from urllib.parse import urlparse
    parsed_path = urlparse(handler.path)
    
    monkeypatch.setattr("app._check_session", MagicMock(return_value=True))
    
    written_payloads = []
    def mock_write_json(payload, status=200):
        written_payloads.append((payload, status))
    handler._write_json = mock_write_json
    
    # Mock do_GET using the inner logic of do_GET (which is not easily callable since it relies on actual server stuff, wait, we can just call do_GET)
    # But wait, app.py uses `parsed_path = urlparse(self.path)` in do_GET.
    handler.do_GET()
    
    assert len(written_payloads) == 1
    payload, status = written_payloads[0]
    assert status == 200
    assert payload.get("stage") == "completed"
    assert payload.get("result") == expected_result
