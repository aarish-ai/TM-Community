import pytest
import requests
from truth_mirror.utils import decode_google_news_url_fast

def test_decode_google_news_url_fast_success():
    # A known Google News URL format
    test_url = "https://news.google.com/rss/articles/CBMiVkFVX3lxTE4zaGU2bTY2ZGkzdTRkSkJ0cFpsTGlDUjkxU2FBRURaTWU0c3QzVWZ1MHZZNkZ5Vzk1ZVBnTDFHY2R6ZmdCUkpUTUJsS1pqQTlCRzlzbHV3?oc=5"
    
    # We create a persistent session
    session = requests.Session()
    
    result = decode_google_news_url_fast(test_url, session=session)
    
    assert isinstance(result, dict)
    assert result.get("status") is True
    assert "decoded_url" in result
    assert result["decoded_url"].startswith("http")
    assert "news.google.com" not in result["decoded_url"]
