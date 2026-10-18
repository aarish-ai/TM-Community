import unittest
from unittest.mock import patch, MagicMock

from truth_mirror.retrieval_news import GoogleNewsRSSConnector
from truth_mirror.models import EvidenceItem

class TestScrapersFallback(unittest.TestCase):
    @patch('truth_mirror.retrieval_news.extract_article_text')
    @patch('truth_mirror.retrieval_news.get_session')
    def test_scraper_uses_extract_article_text(self, mock_get_session, mock_extract):
        connector = GoogleNewsRSSConnector()
        
        mock_rss_response = MagicMock()
        mock_rss_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Title</title>
                    <link>https://www.example.com</link>
                    <pubDate>Wed, 01 Jan 2025 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""
        
        mock_get_session.return_value.get.return_value = mock_rss_response
        mock_extract.return_value = "Extracted article content that is long enough for the excerpt field."
        
        results = connector.retrieve("test")
        
        self.assertEqual(len(results), 1)
        self.assertIn("Extracted article content", results[0].excerpt)

if __name__ == '__main__':
    unittest.main()
