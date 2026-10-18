from unittest.mock import patch, MagicMock
from truth_mirror.retrieval_nonwestern import NonWesternRSSConnector

@patch('truth_mirror.retrieval_nonwestern.get_session')
@patch('urllib.request.urlopen')
def test_nonwestern_connector_handles_4mb_file(mock_urlopen, mock_get_session):
    connector = NonWesternRSSConnector("Mock", "mock.com", "Unknown")
    
    # Mock Google News RSS response
    mock_rss = MagicMock()
    mock_rss.read.return_value = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss><channel><item>
        <title>Test Title</title>
        <link>http://mock.com/article</link>
        <pubDate>Thu, 27 Aug 2026 12:00:00 GMT</pubDate>
    </item></channel></rss>"""
    mock_urlopen.return_value.__enter__.return_value = mock_rss
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_resp = MagicMock()
    
    large_padding = b"<!-- " + b"X" * (4 * 1024 * 1024) + b" -->"
    article_content = b"<p>Nonwestern Article Text Nonwestern Article Text Nonwestern Article Text Nonwestern Article Text</p>" * 10
    raw_html = b"<html><body><article>" + article_content + large_padding + b"</article></body></html>"
    mock_resp.content = raw_html
    mock_resp.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_resp
    
    articles = connector.search("test query")
    
    assert len(articles) == 1
    assert "Nonwestern Article Text" in articles[0].excerpt
