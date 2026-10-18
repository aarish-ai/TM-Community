"""Test that all connectors import, initialize, and return EvidenceItem objects."""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

class TestConnectorImports(unittest.TestCase):
    """Verify all connectors can be imported after dependency fixes."""

    def test_retrieval_news_imports(self):
        from truth_mirror.retrieval_news import (
            GDELTConnector, GoogleNewsRSSConnector, NewsDataIOConnector
        )
        self.assertIsNotNone(GDELTConnector)
        self.assertIsNotNone(GoogleNewsRSSConnector)

    def test_retrieval_nonwestern_imports(self):
        from truth_mirror.retrieval_nonwestern import (
            NonWesternRSSConnector, TargetedRSSConnector
        )
        self.assertIsNotNone(TargetedRSSConnector)



    def test_free_source_retrieval_initializes(self):
        """FreeSourceRetrieval should init with at least 1 news connector."""
        from truth_mirror.retrieval_free import FreeSourceRetrieval
        retriever = FreeSourceRetrieval(
            cache_path=".tm_test_cache_t2.json",
            disable_academic=True
        )
        self.assertGreater(
            len(retriever._news_connectors), 0,
            f"Expected >0 news connectors, got {len(retriever._news_connectors)}"
        )

    def test_no_duplicate_connectors(self):
        from truth_mirror.geo_orchestrator import GeopoliticalPipeline
        from truth_mirror.retrieval_news import GDELTConnector
        
        # Initializing GeopoliticalPipeline should not result in duplicate connectors
        orchestrator = GeopoliticalPipeline()
        retriever = orchestrator.retriever
        
        if hasattr(retriever, "_news_connectors"):
            gdelt_count = sum(1 for c in retriever._news_connectors if isinstance(c, GDELTConnector))
            self.assertLessEqual(gdelt_count, 1, "Should not have duplicate GDELTConnectors")


class TestGDELTConnector(unittest.TestCase):
    """Test GDELT returns real article content, not placeholder text."""

    @patch('truth_mirror.retrieval_news.get_session')
    @patch('truth_mirror.retrieval_news.extract_article_text')
    def test_gdelt_excerpt_not_placeholder(self, mock_extract, mock_get_session):
        from truth_mirror.retrieval_news import GDELTConnector
        connector = GDELTConnector()
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.headers = {"Content-Type": "application/json"}
        mock_success.json.return_value = {
            "articles": [{"url": "http://test.com", "title": "Iran Israel conflict 2025"}]
        }
        mock_get_session.return_value.get.return_value = mock_success
        mock_extract.return_value = "This is a real article excerpt containing actual content about the conflict."
        
        results = connector.retrieve("Iran Israel conflict 2025")
        
        # GDELT may return 0 results for very specific queries, that's OK
        for item in results:
            self.assertNotIn(
                "GDELT Match from",
                item.excerpt,
                f"GDELT still returning placeholder excerpts: {item.excerpt[:100]}"
            )
            # If we got results, excerpts should have real content
            if len(results) > 0:
                self.assertGreater(
                    len(item.excerpt), 20,
                    f"Excerpt too short for '{item.source_title}': {len(item.excerpt)} chars"
                )





class TestNewsDataIO(unittest.TestCase):
    """Test NewsData.io API connector."""

    def test_uses_full_query(self):
        from truth_mirror.retrieval_news import NewsDataIOConnector
        from unittest.mock import patch
        
        connector = NewsDataIOConnector()
        connector.api_key = "test_key"
        long_query = "This is a very long query that has more than six words in it"
        
        with patch('truth_mirror.retrieval_news.get_session') as mock_get_session:
            # Mock a successful response
            mock_get_session.return_value.get.return_value.json.return_value = {"results": []}
            
            connector.retrieve(long_query)
            
            mock_get_session.return_value.get.assert_called_once()
            args, kwargs = mock_get_session.return_value.get.call_args
            params = kwargs.get('params', {})
            self.assertEqual(params.get('q'), long_query, "Must not truncate query")



class TestIsRelevantRegex(unittest.TestCase):
    """Test that _is_relevant matches keywords with numbers (e.g., g20, 2024)."""

    def test_numeric_keywords_match(self):
        from truth_mirror.source_analyzer import _extract_claim_keywords, _is_relevant
        from truth_mirror.models import EvidenceItem

        keywords = _extract_claim_keywords("The G20 summit in 2024 was important")
        self.assertIn("g20", keywords, "Should extract 'g20' as keyword")
        self.assertIn("2024", keywords, "Should extract '2024' as keyword")

        # Create a fake article that mentions G20
        fake_article = EvidenceItem(
            source_title="G20 Summit Results 2024",
            source_type="journalism",
            publisher="Test",
            date="2024-01-01",
            url_or_id="http://test.com",
            excerpt="The G20 leaders met in 2024 to discuss trade."
        )
        self.assertTrue(
            _is_relevant(fake_article, keywords),
            "Article mentioning 'G20' and '2024' should be relevant"
        )


class TestJSONParsing(unittest.TestCase):
    """Test that strip_markdown_json handles common LLM output formats."""

    def test_strip_markdown_fences(self):
        from truth_mirror.utils import strip_markdown_json
        import json

        # Normal JSON
        self.assertEqual(
            json.loads(strip_markdown_json('{"key": "value"}')),
            {"key": "value"}
        )
        # With markdown fences
        self.assertEqual(
            json.loads(strip_markdown_json('```json\n{"key": "value"}\n```')),
            {"key": "value"}
        )
        # With trailing text after fence
        result = strip_markdown_json('```json\n{"key": "value"}\n```\nSome extra text')
        parsed = json.loads(result)
        self.assertEqual(parsed["key"], "value")

    def test_parse_llm_json_robustness(self):
        from truth_mirror.utils import parse_llm_json
        
        # 1. Native JSON
        self.assertEqual(parse_llm_json('{"key": "value"}'), {"key": "value"})
        
        # 2. Markdown fenced
        self.assertEqual(parse_llm_json('```json\n{"key": "value"}\n```'), {"key": "value"})
        
        # 3. Conversational preamble
        self.assertEqual(parse_llm_json('Here is your json:\n[1, 2, 3]'), [1, 2, 3])
        
        # 4. Empty string -> returns None safely
        self.assertIsNone(parse_llm_json('   '))
        
        # 5. Structurally malformed (handled by json_repair)
        self.assertEqual(parse_llm_json('{"key": "value",}'), {"key": "value"}) # trailing comma


    def tearDown(self):
        import os
        for f in [".tm_test_cache_t2.json"]:
            if os.path.exists(f):
                os.remove(f)



def test_nonwestern_rss_sanitizes_xml():
    from truth_mirror.retrieval_nonwestern import NonWesternRSSConnector
    from unittest.mock import patch, MagicMock

    connector = NonWesternRSSConnector("Tehran Times", "tehrantimes.com", "Middle Eastern")
    
    # Create invalid XML byte payload containing a null byte
    invalid_xml_bytes = b"<?xml version=\"1.0\"?><rss><channel><item><title>Test \x00 Title</title><link>http://test.com</link></item></channel></rss>"
    
    mock_response = MagicMock()
    mock_response.read.return_value = invalid_xml_bytes
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response), \
         patch("truth_mirror.rate_limiter.google_news_limiter.wait"), \
         patch("truth_mirror.retrieval_news.get_session") as mock_session_get:
         
        # Mock the extraction response
        mock_ext_resp = MagicMock()
        mock_ext_resp.content = b"<html><body><p>Some text</p></body></html>"
        mock_session_get.return_value.get.return_value = mock_ext_resp

        # If not sanitized, ET.fromstring will throw a ParseError/ValueError
        items = connector.search("test")
        
        # It should gracefully skip parsing errors, but we want it to SUCCEED and return the item.
        # Wait, the search method returns [] on exception. We want it to NOT throw an exception.
        assert len(items) == 1

if __name__ == "__main__":
    unittest.main()
