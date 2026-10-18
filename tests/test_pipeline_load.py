import os
import concurrent.futures
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError

from truth_mirror.llm_fallback import LLMFallbackChain

def test_concurrent_llm_fallback_chain():
    sequence = ["groq", "gemini", "openrouter"]
    models = {"groq": "llama3-8b-8192", "gemini": "gemini-2.5-flash"}
    chain = LLMFallbackChain(sequence=sequence, models=models, tracker_module="test_load")

    with patch('truth_mirror.llm_fallback.call_groq_with_key_rotation') as mock_groq, \
         patch('truth_mirror.llm_fallback.requests.post') as mock_post, \
         patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test_key'}):
        
        # Mock Groq failure
        mock_groq.return_value = (None, "failed")
        
        # Mock requests.post to raise 400 error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError("400 Client Error")
        mock_post.return_value = mock_response

        # Execute 20 concurrent requests
        num_requests = 20
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(chain.execute, "mock prompt") for _ in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results.append(res)
                    
        assert len(results) == 20
        for res in results:
            assert res is None
