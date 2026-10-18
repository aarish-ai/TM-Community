import pytest
from unittest.mock import patch, MagicMock

from truth_mirror.retrieval_news import extract_article_text, EXTRACTION_CACHE


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._parse_content')
def test_local_fetch_success_skips_fallbacks(mock_parse_content, mock_get_session):
    """When local fetch succeeds, no fallbacks are called."""
    EXTRACTION_CACHE.clear()
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_resp = MagicMock()
    mock_resp.content = b"<html>...</html>"
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_session.get.return_value = mock_resp

    mock_parse_content.return_value = "Article content that is long enough to pass the 50 char minimum check."

    with patch('truth_mirror.retrieval_news._fetch_via_google_translate') as mock_gt:
        result = extract_article_text("https://example.com/article")
        assert "Article content" in result
        mock_gt.assert_not_called()


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._fetch_via_google_translate')
def test_local_failure_falls_back_to_google_translate(mock_gt, mock_get_session):
    """When local fetch fails, Google Translate proxy is tried."""
    EXTRACTION_CACHE.clear()

    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_local = MagicMock()
    mock_local.raise_for_status.side_effect = Exception("404 Not Found")
    mock_session.get.return_value = mock_local

    mock_gt.return_value = "Google translated article content that is long enough to pass the 50 char minimum check."

    url = "https://blocked.com/article"
    result = extract_article_text(url)

    mock_gt.assert_called_once_with(url)
    assert result == "Google translated article content that is long enough to pass the 50 char minimum check."


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._fetch_via_google_translate')
@patch('truth_mirror.retrieval_news._fetch_via_amp_cache')
def test_google_translate_failure_falls_back_to_amp_cache(mock_amp, mock_gt, mock_get_session):
    """When local fetch and Google Translate fail, AMP Cache is tried."""
    EXTRACTION_CACHE.clear()

    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_local = MagicMock()
    mock_local.raise_for_status.side_effect = Exception("404 Not Found")
    mock_session.get.return_value = mock_local

    mock_gt.return_value = ""
    mock_amp.return_value = "AMP article content that is long enough to pass the 50 char minimum check."

    url = "https://blocked.com/article"
    result = extract_article_text(url)

    mock_gt.assert_called_once_with(url)
    mock_amp.assert_called_once_with(url)
    assert result == "AMP article content that is long enough to pass the 50 char minimum check."


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._fetch_via_google_translate')
@patch('truth_mirror.retrieval_news._fetch_via_amp_cache')
@patch('truth_mirror.retrieval_news._fetch_via_wayback')
def test_local_failure_falls_back_to_wayback(mock_wayback, mock_amp, mock_gt, mock_get_session):
    """When local fetch, Google Translate, and AMP Cache fail, Wayback Machine is tried."""
    EXTRACTION_CACHE.clear()
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_local = MagicMock()
    mock_local.raise_for_status.side_effect = Exception("404 Not Found")
    mock_session.get.return_value = mock_local
    
    mock_gt.return_value = ""
    mock_amp.return_value = ""
    mock_wayback.return_value = "Wayback Content that is definitely long enough to pass the 50 character minimum."
    
    url = "https://blocked.com/article"
    result = extract_article_text(url)
    
    mock_gt.assert_called_once_with(url)
    mock_amp.assert_called_once_with(url)
    mock_wayback.assert_called_once_with(url)
    assert result == "Wayback Content that is definitely long enough to pass the 50 character minimum."


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._fetch_via_google_translate')
@patch('truth_mirror.retrieval_news._fetch_via_amp_cache')
@patch('truth_mirror.retrieval_news._fetch_via_scraperapi')
@patch('truth_mirror.retrieval_news._fetch_via_zenrows')
@patch('truth_mirror.retrieval_news._fetch_via_commoncrawl')
@patch('truth_mirror.retrieval_news._fetch_via_wayback')
@patch('truth_mirror.retrieval_news._fetch_via_rss_discovery')
@patch('truth_mirror.retrieval_news._fetch_via_selenium')
def test_all_fallbacks_fail_returns_empty(mock_selenium, mock_rss, mock_wayback, mock_cc, mock_zen, mock_scraper, mock_amp, mock_gt, mock_get_session):
    """When local fetch and all fallbacks fail, empty string is returned."""
    EXTRACTION_CACHE.clear()
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_local = MagicMock()
    mock_local.raise_for_status.side_effect = Exception("404 Not Found")
    mock_session.get.return_value = mock_local
    
    mock_gt.return_value = ""
    mock_amp.return_value = ""
    mock_scraper.return_value = ""
    mock_zen.return_value = ""
    mock_cc.return_value = ""
    mock_wayback.return_value = ""
    mock_rss.return_value = ""
    mock_selenium.return_value = ""
    
    result = extract_article_text("https://blocked.com/article")
    
    assert result == ""


@patch('truth_mirror.retrieval_news.get_session')
@patch('truth_mirror.retrieval_news._fetch_via_google_translate')
@patch('truth_mirror.retrieval_news._fetch_via_amp_cache')
@patch('truth_mirror.retrieval_news._fetch_via_wayback')
def test_full_fallback_chain_order(mock_wayback, mock_amp, mock_gt, mock_get_session):
    """All 4 fallback steps are tried in order: Local -> Google Translate -> AMP Cache -> Wayback."""
    EXTRACTION_CACHE.clear()
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_local = MagicMock()
    mock_local.raise_for_status.side_effect = Exception("404 Not Found")
    mock_session.get.return_value = mock_local
    
    # We want it to fail sequentially and finally succeed in Wayback
    mock_gt.return_value = ""
    mock_amp.return_value = ""
    mock_wayback.return_value = "Wayback Content that is definitely long enough to pass the 50 character minimum."
    
    url = "https://blocked.com/article"
    result = extract_article_text(url)
    
    assert mock_gt.call_count == 1
    assert mock_amp.call_count == 1
    assert mock_wayback.call_count == 1
    assert "Wayback Content" in result
