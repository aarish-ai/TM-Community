import pytest
from unittest.mock import patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError
from truth_mirror.retrieval_news import GDELTConnector

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_timeout_retry(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    # Mock to raise Timeout on attempt 0, then succeed on attempt 1 (max 2 attempts)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"articles": []}
    
    mock_get_session.return_value.get.side_effect = [
        requests.exceptions.Timeout("Timeout 1"),
        mock_response
    ]
    
    result = connector.retrieve("test query")
    
    assert mock_get_session.return_value.get.call_count == 2
    assert result == []
    
    # Verify exponential backoff: 2**1 on retry (attempt 1)
    sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
    assert 2 in sleep_args

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_ip_ban_retries(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_403 = MagicMock()
    mock_403.status_code = 403
    mock_403.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden", response=mock_403)
    
    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.headers = {"Content-Type": "application/json"}
    mock_200.json.return_value = {"articles": []}
    
    mock_get_session.return_value.get.side_effect = [mock_403, mock_200]
    
    result = connector.retrieve("test query")
    
    assert mock_get_session.return_value.get.call_count == 2
    # Both calls were to original URL
    assert "api.gdeltproject.org" in mock_get_session.return_value.get.call_args_list[0][0][0]
    assert "api.gdeltproject.org" in mock_get_session.return_value.get.call_args_list[1][0][0]
    assert result == []

def test_gdelt_connector_timeout_is_7_seconds():
    connector = GDELTConnector()
    assert getattr(connector, "timeout_seconds", 0) == 7

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_primary_url_uses_http(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"articles": []}
    mock_get_session.return_value.get.return_value = mock_response
    
    connector.retrieve("test query")
    
    called_url = mock_get_session.return_value.get.call_args[0][0]
    assert called_url.startswith("http://api.gdeltproject.org")
    assert not called_url.startswith("https://")

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_invokes_rate_limiter(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"articles": []}
    mock_get_session.return_value.get.return_value = mock_response
    
    connector.retrieve("test query")
    
    assert mock_limiter.call_count >= 1

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_html_error_response_returns_empty_without_retrying(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_html = MagicMock()
    mock_html.status_code = 200
    mock_html.headers = {"Content-Type": "text/html; charset=UTF-8"}
    mock_html.text = "<html><body><h1>Your search contained too many keywords</h1></body></html>"
    
    mock_get_session.return_value.get.return_value = mock_html
    
    result = connector.retrieve("test query")
    
    # Should not retry; return [] immediately
    assert result == []
    assert mock_get_session.return_value.get.call_count == 1

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_max_retries_is_2_on_failure(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_get_session.return_value.get.side_effect = [
        requests.exceptions.Timeout("Timeout 1"),
        requests.exceptions.Timeout("Timeout 2"),
        requests.exceptions.Timeout("Timeout 3 (should not be called)")
    ]
    
    result = connector.retrieve("test query")
    
    assert result == []
    assert mock_get_session.return_value.get.call_count == 2

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_connection_reset_retries(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_reset = ConnectionError("Connection reset by peer")
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.headers = {"Content-Type": "application/json"}
    mock_success.json.return_value = {"articles": [{"url": "http://test.com"}]}
    
    mock_get_session.return_value.get.side_effect = [mock_reset, mock_success]
    
    with patch('truth_mirror.retrieval_news.extract_article_text', return_value="Sample text"):
        result = connector.retrieve("test query")
    
    # Retry happened and succeeded on attempt 2
    assert mock_get_session.return_value.get.call_count == 2
    assert len(result) == 1

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_unexpected_content_type(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    # Simulate an API gateway returning an XML error instead of JSON
    mock_xml = MagicMock()
    mock_xml.status_code = 200
    mock_xml.headers = {"Content-Type": "application/xml"}
    mock_xml.text = "<error>Gateway Timeout</error>"
    
    mock_get_session.return_value.get.return_value = mock_xml
    
    result = connector.retrieve("test query")
    
    # Non-JSON content type returns empty list immediately without wasting retries
    assert result == []
    assert mock_get_session.return_value.get.call_count == 1

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_malformed_article_payloads(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.headers = {"Content-Type": "application/json"}
    
    # Payload with missing URL, malformed seendate, and missing title
    mock_success.json.return_value = {
        "articles": [
            {"title": "Missing URL"}, # Should be skipped
            {"url": "http://test.com/1", "seendate": "invalid_date_format"}, # Date fallback
            {"url": "http://test.com/2", "seendate": 20230501120000} # Int date instead of string
        ]
    }
    
    mock_get_session.return_value.get.return_value = mock_success
    
    with patch('truth_mirror.retrieval_news.extract_article_text', return_value="Sample article content"):
        result = connector.retrieve("test query")
    
    # One article skipped, two processed with fallback dates
    assert len(result) == 2
    result_urls = {r.url_or_id for r in result}
    assert result_urls == {"http://test.com/1", "http://test.com/2"}

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_extraction_timeout_and_exceptions(mock_sleep, mock_get_session, mock_limiter):
    connector = GDELTConnector()
    
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.headers = {"Content-Type": "application/json"}
    mock_success.json.return_value = {
        "articles": [
            {"url": "http://test.com/exception", "title": "Will Fail"},
        ]
    }
    
    mock_get_session.return_value.get.return_value = mock_success
    
    with patch('truth_mirror.retrieval_news.extract_article_text') as mock_extract:
        # Simulate extraction throwing a generic exception
        mock_extract.side_effect = Exception("Browser crashed")
        
        result = connector.retrieve("test query")
        
        # The connector should swallow the extraction error and fallback to the title
        assert len(result) == 1
        assert result[0].excerpt == "Will Fail"

@patch('truth_mirror.retrieval_news.gdelt_limiter.wait')
@patch('truth_mirror.retrieval_news.get_session')
@patch('time.sleep')
def test_gdelt_maintains_original_ranking(mock_sleep, mock_get_session, mock_limiter):
    import time
    connector = GDELTConnector()
    
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.headers = {"Content-Type": "application/json"}
    
    mock_success.json.return_value = {
        "articles": [
            {"url": "http://test.com/1", "title": "Article 1", "domain": "test.com", "seendate": "20230501T120000Z"},
            {"url": "http://test.com/2", "title": "Article 2", "domain": "test.com", "seendate": "20230501T120000Z"},
            {"url": "http://test.com/3", "title": "Article 3", "domain": "test.com", "seendate": "20230501T120000Z"}
        ]
    }
    
    mock_get_session.return_value.get.return_value = mock_success
    
    def mock_extract(url):
        if url.endswith("1"):
            time.sleep(0.2)
        elif url.endswith("2"):
            time.sleep(0.05)
        elif url.endswith("3"):
            time.sleep(0.1)
        return "Sample article content"
        
    with patch('truth_mirror.retrieval_news.extract_article_text') as mock_extract_fn:
        mock_extract_fn.side_effect = mock_extract
        result = connector.retrieve("test query")
    
    assert len(result) == 3
    assert result[0].url_or_id == "http://test.com/1"
    assert result[1].url_or_id == "http://test.com/2"
    assert result[2].url_or_id == "http://test.com/3"
