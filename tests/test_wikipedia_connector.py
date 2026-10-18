import unittest
from unittest.mock import patch, MagicMock
import time
import concurrent.futures

from truth_mirror.retrieval import EvidenceRetriever, RetrievalConfig
from truth_mirror.models import EvidenceItem

class TestWikipediaConnector(unittest.TestCase):
    def setUp(self):
        self.config = RetrievalConfig(max_results=2)
        self.connector = EvidenceRetriever(config=self.config)

    @patch('truth_mirror.retrieval.requests.get')
    def test_concurrent_requests_are_rate_limited(self, mock_get):
        # We simulate a successful search but no extracts to simplify
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "search": [{"title": "Test Title", "snippet": "Test snippet"}]
            }
        }
        mock_get.return_value = mock_response

        # We will record the exact time when requests.get is called
        call_times = []
        def side_effect(*args, **kwargs):
            call_times.append(time.time())
            return mock_response
        
        mock_get.side_effect = side_effect

        def run_query(q):
            return self.connector._query_wikipedia(q)
            
        start_time = time.time()
        # Fire 5 queries concurrently
        queries = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_query, q) for q in queries]
            concurrent.futures.wait(futures)
            
        self.assertEqual(len(call_times), 10) # 5 for search, 5 for extracts
        
        # Verify that calls are spaced by at least 1.0 seconds
        # Sort call times just in case, though the lock should enforce strict ordering
        call_times.sort()
        for i in range(1, len(call_times)):
            diff = call_times[i] - call_times[i-1]
            self.assertGreaterEqual(diff, 0.9, f"Rate limit failed! Interval between requests was only {diff}s")

if __name__ == '__main__':
    unittest.main()
