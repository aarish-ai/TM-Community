import pytest
import re
import base64
from unittest.mock import MagicMock



# 2. C5 XXE Vulnerability Fix Test
import defusedxml.ElementTree as DefusedET
import truth_mirror.retrieval_news as r_news
import truth_mirror.retrieval_nonwestern as r_nonwestern
import truth_mirror.retrieval as r_retrieval

def test_c5_defusedxml_imports():
    assert r_news.ET is DefusedET
    assert r_nonwestern.ET is DefusedET
    assert r_retrieval.ET is DefusedET


# 3. C7 Auth Bypass Fix Test
from app import TruthMirrorHandler
import app

def test_c7_auth_bypass_rejection():
    handler = MagicMock(spec=TruthMirrorHandler)
    handler.headers = {}
    handler.wfile = MagicMock()
    
    # Execute _check_session with mock headers (no Authorization header)
    result = app._check_session(handler)
    assert result is False
    handler.send_response.assert_called_with(401)

def test_c7_auth_valid_credentials():
    handler = MagicMock(spec=TruthMirrorHandler)
    handler.wfile = MagicMock()
    
    token = app._create_session("admin")
    handler.headers = {"Authorization": f"Bearer {token}"}
    
    result = app._check_session(handler)
    assert result is True


# 4. C9 Prompt Injection Sanitization Test
from truth_mirror.source_analyzer import _build_single_prompt
from truth_mirror.models import EvidenceItem

def test_c9_prompt_injection_sanitization():
    article = EvidenceItem(
        source_title="Title with ``` injection",
        source_type="journalism",
        publisher="TestNews",
        date="2026-07-24",
        url_or_id="https://test.com/news",
        excerpt="Excerpt with ``` and harmful instructions"
    )
    claim = "Claim with ``` and injection instructions"
    
    prompt = _build_single_prompt(article, claim)
    
    # Check that triple backticks are escaped
    assert "```" not in prompt
    assert "` ` `" in prompt
    
    # Check untrusted content wrappers
    assert "<untrusted_content>Claim with ` ` ` and injection instructions</untrusted_content>" in prompt
    assert "<untrusted_content>Title with ` ` ` injection</untrusted_content>" in prompt
    assert "<untrusted_content>Excerpt with ` ` ` and harmful instructions</untrusted_content>" in prompt
