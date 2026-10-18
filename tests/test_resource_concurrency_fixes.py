"""
Unit tests for Resource, Network & Concurrency fixes: C3, C4, C10, C11, C14.
"""

import asyncio
import concurrent.futures
import threading
import time
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import aiohttp
import requests

from truth_mirror.source_analyzer import SourceAnalyzer, _call_gemini_async, _call_openrouter_async

from truth_mirror.geo_orchestrator import GeopoliticalPipeline
from truth_mirror.gemini_analyzer import GeminiAnalyzer
from truth_mirror.models import EvidenceItem
from app import TruthMirrorHandler


# ---------------------------------------------------------------------------
# C3: aiohttp Connection Pooling Tests
# ---------------------------------------------------------------------------
def test_aiohttp_session_reuse_in_async_helpers():
    """Verify async API calls accept and reuse an external aiohttp.ClientSession."""
    async def _test():
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"candidates": [{"content": {"parts": [{"text": '{"stance": "SUPPORTS"}'}]}}]}
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockPostContext:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session.post = MagicMock(return_value=MockPostContext())

        with patch("truth_mirror.key_rotator.get_current_key", return_value="fake_key"):
            result = await _call_gemini_async("test prompt", "gemini-2.5-flash", session=mock_session)

        assert result == '{"stance": "SUPPORTS"}'
        assert mock_session.post.called
        assert not mock_session.close.called

    asyncio.run(_test())


def test_source_analyzer_analyze_all_session_reuse():
    """Verify SourceAnalyzer.analyze_all accepts and passes session."""
    async def _test():
        analyzer = SourceAnalyzer()
        mock_article = EvidenceItem(
            source_title="Test title",
            source_type="journalism",
            publisher="Test publisher",
            date="2026-01-01",
            url_or_id="https://example.com/test",
            excerpt="Test claim snippet text long enough",
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)

        with patch.object(analyzer, "_call_groq_batch", return_value=[]):
            res = await analyzer.analyze_all([mock_article], "Test claim snippet", session=mock_session)
            assert isinstance(res, list)

    asyncio.run(_test())


# ---------------------------------------------------------------------------
# C4: Requests Timeout Parameters Tests
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# C10: Catch Unhandled Exceptions in HTTP Handler Tests
# ---------------------------------------------------------------------------
def test_app_do_post_catches_general_exception(monkeypatch):
    """Verify TruthMirrorHandler.do_POST handles general pipeline exception gracefully with HTTP 500."""
    handler = TruthMirrorHandler.__new__(TruthMirrorHandler)
    handler.headers = {"Content-Length": "35"}
    
    req_body = b'{"claim": "Simulated error claim"}'
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = req_body
    handler.path = "/api/verify"

    monkeypatch.setattr("app._check_session", MagicMock(return_value=True))

    written_payloads = []
    def mock_write_json(payload, status=200):
        written_payloads.append((payload, status))

    handler._write_json = mock_write_json

    # Mock executor to raise an exception during submit
    monkeypatch.setattr("app._executor.submit", MagicMock(side_effect=RuntimeError("Simulated pipeline crash")))
    handler.pipeline = MagicMock()

    handler.do_POST()

    assert len(written_payloads) == 1
    payload, status = written_payloads[0]
    assert status == 500
    assert payload["error"] == "Failed to start analysis"
    assert "Simulated pipeline crash" in payload["details"]


# ---------------------------------------------------------------------------
# C11: Relevance Ordering Preservation Tests
# ---------------------------------------------------------------------------


def test_geo_orchestrator_parallel_retrieve_relevance_ordering():
    """Verify GeopoliticalPipeline._parallel_retrieve preserves query order."""
    pipeline = GeopoliticalPipeline.__new__(GeopoliticalPipeline)
    mock_retriever = MagicMock()

    def mock_retrieve(query, claim_subtype, use_wikinews):
        if query == "q_first":
            time.sleep(0.05)
            return [EvidenceItem(source_title="First", source_type="journalism", publisher="P", date="2026-01-01", url_or_id="http://first.com", excerpt="E")]
        else:
            return [EvidenceItem(source_title="Second", source_type="journalism", publisher="P", date="2026-01-01", url_or_id="http://second.com", excerpt="E")]

    mock_retriever.retrieve.side_effect = mock_retrieve
    pipeline.retriever = mock_retriever
    pipeline.targeted_connectors = []

    results = pipeline._parallel_retrieve(["q_first", "q_second"], "conflict", "dummy claim")
    assert len(results) == 2
    assert results[0].url_or_id == "http://first.com"
    assert results[1].url_or_id == "http://second.com"


# ---------------------------------------------------------------------------
# C14: Thread-Safe Counter Increment Tests
# ---------------------------------------------------------------------------
def test_gemini_analyzer_thread_safe_counter():
    """Verify GeminiAnalyzer._call_count increments safely across concurrent threads."""
    GeminiAnalyzer.reset_call_count()
    assert GeminiAnalyzer._call_count == 0

    with patch.dict("os.environ", {"MAX_GEMINI_CALLS_PER_QUERY": "10"}):
        analyzer = GeminiAnalyzer()
        analyzer.enabled = False  # Disabled so synthesize returns None early after incrementing count

        def call_synthesize():
            analyzer.synthesize("claim", [EvidenceItem(source_title="Title", source_type="journalism", publisher="Pub", date="2026-01-01", url_or_id="http://url.com", excerpt="Snippet")])

        threads = [threading.Thread(target=call_synthesize) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 10 calls should have been allowed and recorded
        assert GeminiAnalyzer._call_count == 10

    GeminiAnalyzer.reset_call_count()
    assert GeminiAnalyzer._call_count == 0
