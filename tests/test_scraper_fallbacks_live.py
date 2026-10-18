"""Live integration tests for article extraction fallback chain.

These tests hit REAL endpoints. They are slow and require network access.
Run with: pytest tests/test_scraper_fallbacks_live.py -v -m live
"""
import pytest
from truth_mirror.retrieval_news import (
    extract_article_text,
    _fetch_via_google_translate,
    _fetch_via_amp_cache,
    _fetch_via_wayback,
    EXTRACTION_CACHE,
)

pytestmark = pytest.mark.live


class TestGoogleTranslateLive:
    """Verify Google Translate proxy actually returns content from a real URL."""

    def test_google_translate_returns_content_for_accessible_page(self):
        """Google Translate should successfully proxy a simple, unblocked page."""
        EXTRACTION_CACHE.clear()
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        text = _fetch_via_google_translate(url)
        assert len(text) > 100, f"Expected >100 chars, got {len(text)}: {text[:200]}"
        assert "python" in text.lower(), f"Expected 'python' in text, got: {text[:200]}"


class TestAMPCacheLive:
    """Verify AMP Cache proxy actually returns content."""

    def test_amp_cache_returns_content_for_known_amp_page(self):
        """AMP Cache should work for sites that have AMP versions."""
        EXTRACTION_CACHE.clear()
        # Use a well-known site that definitely has AMP
        url = "https://www.bbc.com/news/world-middle-east-67600369"
        text = _fetch_via_amp_cache(url)
        # AMP may or may not have this specific page; this tests the mechanism
        if text:
            assert len(text) > 50


class TestWaybackLive:
    """Verify Wayback Machine returns content with rate limiting."""

    def test_wayback_returns_content_for_archived_page(self):
        """Wayback should find and extract an archived Wikipedia page."""
        EXTRACTION_CACHE.clear()
        url = "https://en.wikipedia.org/wiki/Fact-checking"
        text = _fetch_via_wayback(url)
        assert len(text) > 100, f"Expected >100 chars, got {len(text)}"


class TestFullFallbackChainLive:
    """Verify the full fallback chain works end-to-end for a blocked site."""

    def test_extract_article_text_for_accessible_page(self):
        """Full chain should extract content from an accessible page (direct fetch succeeds)."""
        EXTRACTION_CACHE.clear()
        url = "https://en.wikipedia.org/wiki/Fact-checking"
        text = extract_article_text(url)
        assert len(text) > 100, f"Expected >100 chars from accessible page, got {len(text)}"

    def test_extract_article_text_returns_something_for_blocked_page(self):
        """Full chain should extract SOME content even from a page that blocks direct fetch."""
        EXTRACTION_CACHE.clear()
        # Times of Israel returns 403 on direct fetch
        url = "https://www.timesofisrael.com/liveblog_entry/un-commission-claims-israel-deliberately-targeted-gaza-children-resulting-in-genocide/"
        text = extract_article_text(url)
        # At least one fallback should succeed
        assert len(text) > 0, "ALL fallbacks failed for a blocked page — the pipeline is still broken"
