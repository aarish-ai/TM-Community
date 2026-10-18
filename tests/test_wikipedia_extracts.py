"""Test that WikipediaConnector fetches actual article content, not just search snippets."""

import unittest
from truth_mirror.retrieval import EvidenceRetriever, RetrievalConfig


class TestWikipediaExtracts(unittest.TestCase):
    
    def setUp(self):
        """Create a retriever with a temp cache path to avoid polluting real cache."""
        self.retriever = EvidenceRetriever(
            cache_path=".tm_test_cache.json",
            config=RetrievalConfig(max_results=3, timeout_seconds=10)
        )
    
    def test_excerpt_length_exceeds_snippet(self):
        """Wikipedia results should have excerpts much longer than search snippets."""
        results = self.retriever._query_wikipedia("Iran Israel conflict 2024")
        self.assertGreater(len(results), 0, "Should return at least 1 result")
        
        # Search snippets are typically 100-200 chars.
        # With extracts, we expect at least 500+ chars for most articles.
        long_excerpts = [r for r in results if len(r.excerpt) > 400]
        self.assertGreater(
            len(long_excerpts), 0,
            f"At least one excerpt should be >400 chars. "
            f"Got lengths: {[len(r.excerpt) for r in results]}"
        )
    
    def test_excerpt_contains_substantive_content(self):
        """Excerpts should contain actual factual content, not just title repetition."""
        results = self.retriever._query_wikipedia("2024 Iran Israel conflict")
        self.assertGreater(len(results), 0)
        
        # Check that at least one excerpt contains substantive words
        # that would only appear in article body, not a search snippet
        substantive_markers = ["military", "attack", "missile", "conflict", "April", "October"]
        found_substantive = False
        for r in results:
            if any(marker.lower() in r.excerpt.lower() for marker in substantive_markers):
                found_substantive = True
                break
        
        self.assertTrue(
            found_substantive,
            f"No excerpt contained substantive conflict details. "
            f"Excerpts: {[r.excerpt[:100] for r in results]}"
        )
    
    def test_excerpt_max_length(self):
        """Excerpts should be truncated to 2000 chars max."""
        results = self.retriever._query_wikipedia("United States")
        for r in results:
            self.assertLessEqual(
                len(r.excerpt), 2000,
                f"Excerpt for '{r.source_title}' exceeds 2000 chars: {len(r.excerpt)}"
            )
    
    def test_fallback_to_snippet_on_failure(self):
        """If extracts API fails, should still return results with search snippets."""
        # Query for something obscure that should still return search results
        results = self.retriever._query_wikipedia("Wikipedia test page sandbox")
        # Even if extracts fail, we should still get results (with snippet fallback)
        self.assertGreater(len(results), 0, "Should return results even if extracts fail")
    
    def test_fetch_wikipedia_extracts_method(self):
        """The _fetch_wikipedia_extracts helper should return title->text mapping."""
        extracts = self.retriever._fetch_wikipedia_extracts(["Iran", "Israel"])
        self.assertIsInstance(extracts, dict)
        # At least one should have content
        if extracts:
            for title, text in extracts.items():
                self.assertIsInstance(text, str)
                self.assertGreater(len(text), 50, f"Extract for '{title}' is too short")
    
    def tearDown(self):
        """Clean up test cache."""
        import os
        if os.path.exists(".tm_test_cache.json"):
            os.remove(".tm_test_cache.json")


if __name__ == "__main__":
    unittest.main()
