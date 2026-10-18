"""
TDD tests for the enhanced article extraction fallback chain.
All tests MUST fail before implementation begins (Task 2+).
Run with: pytest tests/test_extraction_fallback.py -v
"""
import pytest
import threading
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from truth_mirror.retrieval_news import (
    extract_article_text,
    EXTRACTION_CACHE,
    _fetch_via_scraperapi,
    _fetch_via_zenrows,
    _fetch_via_commoncrawl,
    _fetch_via_selenium,
    _fetch_via_rss_discovery,
)
from truth_mirror import retrieval_news as rn


def test_blocked_domain_skips_direct_fetch():
    """extract_article_text must NOT call get_session().get() for always-blocked domains."""
    EXTRACTION_CACHE.clear()
    with patch.object(rn, 'get_session') as mock_sess:
        mock_sess.return_value.get.return_value = MagicMock(
            status_code=200,
            content=b"<html>article text that is definitely longer than 50 chars of content</html>",
            headers={"Content-Type": "text/html"}
        )
        with patch.object(rn, '_fetch_via_google_translate', return_value=""):
          with patch.object(rn, '_fetch_via_amp_cache', return_value=""):
            with patch.object(rn, '_fetch_via_wayback', return_value=""):
              with patch.object(rn, '_fetch_via_scraperapi', return_value=""):
                with patch.object(rn, '_fetch_via_zenrows', return_value=""):
                  with patch.object(rn, '_fetch_via_commoncrawl', return_value=""):
                    with patch.object(rn, '_fetch_via_selenium', return_value=""):
                      with patch.object(rn, '_fetch_via_rss_discovery', return_value=""):
                        extract_article_text("https://www.reuters.com/article/some-article")
    mock_sess.return_value.get.assert_not_called()


def test_wayback_semaphore_limits_concurrency():
    """The global _wayback_semaphore must be a threading.Semaphore with value 2."""
    assert hasattr(rn, '_wayback_semaphore'), "rn._wayback_semaphore not found"
    sem = rn._wayback_semaphore
    assert sem.acquire(blocking=False), "First acquire failed"
    assert sem.acquire(blocking=False), "Second acquire failed"
    assert not sem.acquire(blocking=False), "Third acquire should fail (value is 2)"
    sem.release()
    sem.release()


def test_fetch_via_scraperapi_returns_text():
    """_fetch_via_scraperapi must return non-empty text when ScraperAPI responds 200."""
    with patch('truth_mirror.retrieval_news.get_session') as mock_session_getter:
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b"<html><body>" + b"x" * 500 + b"</body></html>"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_session.get.return_value = mock_resp
        mock_session_getter.return_value = mock_session
        with patch('truth_mirror.retrieval_news._parse_content',
                   return_value="article body text here that is definitely well over fifty characters long for test purposes"):
            with patch.dict(os.environ, {"SCRAPERAPI_KEY": "test_key"}):
                result = _fetch_via_scraperapi("https://www.nytimes.com/article/test")
    assert result and len(result) > 50


def test_fetch_via_zenrows_returns_text():
    """_fetch_via_zenrows must return non-empty text when ZenRows API responds 200."""
    with patch('truth_mirror.retrieval_news.get_session') as mock_session_getter:
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b"<html><body>full article text goes here long</body></html>"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_session.get.return_value = mock_resp
        mock_session_getter.return_value = mock_session
        with patch('truth_mirror.retrieval_news._parse_content',
                   return_value="article body text here that is definitely well over fifty characters long for test purposes"):
            with patch.dict(os.environ, {"ZENROWS_API_KEY": "test_key"}):
                result = _fetch_via_zenrows("https://www.forbes.com/article/test")
    assert result and len(result) > 50


def test_fetch_via_zenrows_retries_on_400():
    """_fetch_via_zenrows retries with js_render and premium_proxy if 400 REQS002 is returned."""
    with patch('truth_mirror.retrieval_news.get_session') as mock_session_getter:
        mock_session = MagicMock()
        resp_400 = MagicMock()
        resp_400.status_code = 400
        resp_400.text = '{"code":"REQS002","detail":"needs JavaScript rendering and/or Premium Proxies"}'
        resp_200 = MagicMock()
        resp_200.ok = True
        resp_200.status_code = 200
        resp_200.content = b"<html><body>full reuters text goes here</body></html>"
        resp_200.headers = {"Content-Type": "text/html"}
        mock_session.get.side_effect = [resp_400, resp_200]
        mock_session_getter.return_value = mock_session
        with patch('truth_mirror.retrieval_news._parse_content',
                   return_value="full reuters text goes here and is definitely long enough to pass 50 chars threshold"):
            with patch.dict(os.environ, {"ZENROWS_API_KEY": "test_key"}):
                result = _fetch_via_zenrows("https://www.reuters.com/article/test")
    assert result and len(result) > 50
    assert mock_session.get.call_count == 2


def test_fetch_via_commoncrawl_returns_text():
    """_fetch_via_commoncrawl must query CDX and return text from the WARC record."""
    cdx_response = MagicMock()
    cdx_response.raise_for_status = MagicMock()
    cdx_response.text = '{"urlkey":"com,aljazeera)/news","timestamp":"20260901120000","original":"https://www.aljazeera.com/news/test","mimetype":"text/html","statuscode":"200","digest":"ABC123","length":"12345","filename":"crawl-data/CC-MAIN-2026-06/segments/x/warc/CC-MAIN-20260901.warc.gz","offset":"1000"}'
    cdx_response.text += "\n"
    warc_response = MagicMock()
    warc_response.raise_for_status = MagicMock()
    warc_response.content = b"<html><body>full article body text that is definitely more than fifty characters long here</body></html>"
    warc_response.headers = {"Content-Type": "text/html"}
    with patch('truth_mirror.retrieval_news.get_session') as mock_session_getter:
        mock_session = MagicMock()
        mock_session.get.side_effect = [cdx_response, warc_response]
        mock_session_getter.return_value = mock_session
        with patch('truth_mirror.retrieval_news._parse_content',
                   return_value="full article body text that is definitely well over fifty characters long for test purposes"):
            result = _fetch_via_commoncrawl("https://www.aljazeera.com/news/test")
    assert result and len(result) > 50


def test_fetch_via_selenium_returns_text():
    """_fetch_via_selenium must use a headless browser and return trafilatura-extracted text."""
    with patch('truth_mirror.retrieval_news._get_selenium_driver') as mock_driver_factory:
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>" + "Article content. " * 100 + "</body></html>"
        mock_driver_factory.return_value = mock_driver
        with patch('truth_mirror.retrieval_news._parse_content',
                   return_value="Article content. " * 10):
            result = _fetch_via_selenium("https://www.economist.com/article/test")
    assert result and len(result) > 50


def test_fetch_via_rss_discovery_returns_text():
    """_fetch_via_rss_discovery must search Google News RSS and return text."""
    with patch('truth_mirror.retrieval_news._fetch_rss_articles_for_url',
               return_value="This is the full article found via RSS and it is more than 50 chars long for sure"):
        result = _fetch_via_rss_discovery("https://www.reuters.com/article/ukraine-war-12345")
    assert result and len(result) > 50


def test_scraperapi_skips_when_no_key():
    """_fetch_via_scraperapi must return '' immediately when SCRAPERAPI_KEY is not set."""
    env_without_key = {k: v for k, v in os.environ.items() if k != "SCRAPERAPI_KEY"}
    with patch.dict(os.environ, env_without_key, clear=True):
        result = _fetch_via_scraperapi("https://www.nytimes.com/article/test")
    assert result == ""


def test_zenrows_skips_when_no_key():
    """_fetch_via_zenrows must return '' immediately when ZENROWS_API_KEY is not set."""
    env_without_key = {k: v for k, v in os.environ.items() if k != "ZENROWS_API_KEY"}
    with patch.dict(os.environ, env_without_key, clear=True):
        result = _fetch_via_zenrows("https://www.forbes.com/article/test")
    assert result == ""
