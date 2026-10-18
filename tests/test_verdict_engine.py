import unittest
from unittest.mock import patch, MagicMock

from truth_mirror.verdict_engine import VerdictEngine
from truth_mirror.models import VerificationResult

class TestVerdictEngine(unittest.IsolatedAsyncioTestCase):
    @patch('google.genai.Client')
    async def test_verdict_engine_recovers_from_missing_comma(self, mock_client_class):
        # We need an async test because VerdictEngine.generate is async.
        # It calls gemini and parses the JSON.
        
        # This is a sample json response but with a MISSING comma after "final_verdict"
        malformed_json_response = """
        ```json
        {
            "original_claim": "Test",
            "normalized_claim": "Test",
            "claim_type": "factual",
            "sub_claims": [],
            "verdict": "Supported"
            "confidence": 0.9,
            "confidence_label": "High",
            "one_line_verdict": "Summary",
            "full_reasoning": "Because",
            "what_is_true": "None",
            "what_is_false": "None",
            "what_is_unclear": "None",
            "strongest_evidence_for": "None",
            "strongest_evidence_against": "None",
            "source_quality_note": "None"
        }
        ```
        """
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = malformed_json_response
        mock_client.models.generate_content.return_value = mock_response

        engine = VerdictEngine()
        
        # If it uses strict json.loads, this will raise a JSONDecodeError
        result = await engine.generate(
            source_analyses=[],
            hidden_stories=[],
            claim="Test",
            gemini_client=None
        )
        
        # Wait, if it fails, it returns a fallback UNVERIFIABLE verdict.
        # So it shouldn't raise, but it will return the fallback!
        # If json_repair is working, it will return the parsed 'Supported'.
        self.assertEqual(result.verdict, "Supported")
        self.assertEqual(result.confidence, 0.9)

if __name__ == '__main__':
    unittest.main()
