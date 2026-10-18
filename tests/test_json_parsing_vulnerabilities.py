import unittest
from unittest.mock import patch, AsyncMock
from truth_mirror.geo_query_generator import GeoQueryGenerator

class TestJSONParsingVulnerabilities(unittest.TestCase):
    
    @patch('truth_mirror.geo_query_generator.call_groq_with_key_rotation')
    def test_geo_query_generator_markdown_fence_crash(self, mock_call_groq):
        mock_call_groq.return_value = ("```json\n[\"query 1\"]\n```", "success")
        generator = GeoQueryGenerator()
        
        result = generator.generate("Test claim", [], "")
        self.assertIn("query 1", result)

    @patch('truth_mirror.local_decomposer.OPENROUTER_API_KEY', None)
    @patch('truth_mirror.local_decomposer.call_groq_with_key_rotation')
    def test_local_decomposer_conversational_filler_crash(self, mock_call_groq):
        from truth_mirror.local_decomposer import LocalDecomposer
        mock_call_groq.return_value = ("Here is your JSON:\n[\"subclaim 1\"]", "success")
        decomposer = LocalDecomposer()
        
        result = decomposer.decompose("Test claim")
        self.assertIn("subclaim 1", result)

    @patch('truth_mirror.temporal_classifier.call_groq_with_key_rotation')
    def test_temporal_classifier_empty_string_crash(self, mock_call_groq):
        from truth_mirror.temporal_classifier import TemporalClassifier
        mock_call_groq.return_value = ("", "success")
        classifier = TemporalClassifier()
        
        result = classifier.classify("Test claim")
        
        # When Groq returns an empty string, json.loads fails with "Expecting value: line 1 column 1 (char 0)"
        # Confirm it returns the fallback TemporalContext and assert that fallback reasoning is present.
        expected_fallback = classifier._fallback("Test claim")
        self.assertEqual(result, expected_fallback)
        self.assertIn("Fallback", result.reasoning, "Vulnerability missing: Fallback reasoning not present!")

    @patch('truth_mirror.temporal_classifier.call_groq_with_key_rotation')
    def test_temporal_classifier_markdown_fence(self, mock_call_groq):
        from truth_mirror.temporal_classifier import TemporalClassifier
        mock_call_groq.return_value = ("```json\n{\"temporal_type\": \"historical_completed\", \"reasoning\": \"It's old\"}\n```", "success")
        classifier = TemporalClassifier()
        
        result = classifier.classify("Test claim")
        
        self.assertEqual(result.temporal_type, "historical_completed")
        self.assertEqual(result.reasoning, "It's old")

    @patch('truth_mirror.keyword_extractor.asyncio.sleep', new_callable=AsyncMock)
    @patch('truth_mirror.keyword_extractor.get_current_key', return_value='fake_key')
    @patch('truth_mirror.keyword_extractor.aiohttp.ClientSession.post')
    def test_keyword_extractor_conversational_crash(self, mock_post, mock_get_key, mock_sleep):
        import asyncio
        from truth_mirror.keyword_extractor import extract_search_queries
        
        mock_resp = AsyncMock()
        mock_resp.status = 200
        # Inject conversational preamble which breaks its weak strip
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Here is it:\n```json\n{\"queries\": [\"keyword\"]}\n```"}]}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        result = asyncio.run(extract_search_queries("Test claim"))
        
        self.assertIn("keyword", result)

    def test_source_analyzer_parse_batch_conversational_markdown_fence(self):
        from truth_mirror.source_analyzer import _parse_batch_response
        from truth_mirror.models import EvidenceItem
        
        # Raw text with markdown fence, conversational preamble, and trailing comma
        raw_text = """Here is your JSON response:
```json
{
  "analyses": [
    {
      "article_index": 1,
      "source_name": "Test Source",
      "summary": "This is a summary",
      "stance": "SUPPORTS",
      "stance_confidence": 0.9,
      "key_claims": ["claim1",],
    }
  ]
}
```
"""
        batch = [EvidenceItem(source_title="Test Source", source_type="journalism", publisher="Test Publisher", date="2025-01-01", url_or_id="https://test.com", excerpt="Test excerpt")]
        results = _parse_batch_response(raw_text, batch)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].stance, "SUPPORTS")

    def test_source_analyzer_parse_single_conversational_markdown_fence(self):
        from truth_mirror.source_analyzer import _parse_single_response
        from truth_mirror.models import EvidenceItem
        
        # Raw text with markdown fence, conversational preamble, and trailing comma
        raw_text = """Here is your JSON response:
```json
{
  "summary": "Single source summary",
  "stance": "CONTRADICTS",
  "stance_confidence": 0.85,
  "key_claims": ["claim1",],
}
```
"""
        article = EvidenceItem(source_title="Test Article", source_type="journalism", publisher="Test Publisher", date="2025-01-01", url_or_id="https://test.com", excerpt="Test excerpt")
        result = _parse_single_response(raw_text, article)
        self.assertIsNotNone(result)
        self.assertEqual(result.stance, "CONTRADICTS")

    def test_gemini_analyzer_conversational_markdown_fence(self):
        from truth_mirror.gemini_analyzer import GeminiAnalyzer
        from truth_mirror.models import EvidenceItem
        from unittest.mock import MagicMock
        
        analyzer = GeminiAnalyzer()
        analyzer.enabled = True
        analyzer.model_name = "gemini-3.5-flash"
        
        # Mock response text with conversational text, markdown fences, and trailing comma
        mock_response = MagicMock()
        mock_response.text = """Here is the fact check:
```json
{
  "verdict": "Supported",
  "confidence": 0.95,
  "reasoning": "Strong evidence",
  "evidence_summary": "All sources agree",
}
```
"""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('truth_mirror.gemini_analyzer.genai.Client', return_value=mock_client), \
             patch('truth_mirror.key_rotator.get_current_key', return_value='fake_key'):
            GeminiAnalyzer.reset_call_count()
            evidence = [EvidenceItem(source_title="Title", source_type="journalism", publisher="Pub", date="2025-01-01", url_or_id="https://test.com", excerpt="Excerpt")]
            result = analyzer.synthesize("Test claim", evidence)
            self.assertIsNotNone(result)
            self.assertEqual(result["verdict"], "Supported")
            self.assertEqual(result["confidence"], 0.95)

    @patch('truth_mirror.geo_synthesizer.GeopoliticalResult')
    def test_geo_synthesizer_conversational_markdown_fence(self, mock_geo_result):
        from truth_mirror.geo_synthesizer import GeoSynthesizer
        from unittest.mock import MagicMock
        
        # Mock response text with conversational preamble, markdown fence, and trailing comma
        mock_response = MagicMock()
        mock_response.text = """Here is the analysis:
```json
{
  "verdict": "Supported",
  "confidence": 0.9,
  "verdict_reasoning": "Evidence is clear",
  "source_agreement_level": "high",
  "story": {
    "headline": "Headline",
    "background": "Background",
    "current_situation": "Current situation",
    "key_actors": [],
    "timeline_hints": [],
    "sources_agreeing_on": "Agreement",
  },
  "has_dispute": false,
  "key_sources": [],
  "missing_evidence": [],
}
```
"""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('truth_mirror.geo_synthesizer.genai.Client', return_value=mock_client), \
             patch('truth_mirror.key_rotator.get_current_key', return_value='fake_key'), \
             patch('truth_mirror.geo_synthesizer.GENAI_AVAILABLE', True):
            synthesizer = GeoSynthesizer(client=mock_client)
            synthesizer.synthesize("Claim", "subtype", "parties", "evidence")
            mock_geo_result.assert_called_once()
            _, kwargs = mock_geo_result.call_args
            self.assertEqual(kwargs.get("verdict"), "Supported")
            self.assertEqual(kwargs.get("confidence"), 0.9)

    @patch('truth_mirror.stance.requests.post')
    @patch('truth_mirror.stance.get_current_key', return_value='fake_key')
    def test_stance_analyzer_conversational_markdown_trailing_comma(self, mock_key, mock_post):
        from truth_mirror.stance import StanceAnalyzer
        from truth_mirror.models import EvidenceItem
        from unittest.mock import MagicMock
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": 'Sure, here is the analysis:\n```json\n{"stance": "contradicts",}\n```'}]}}]
        }
        mock_post.return_value = mock_resp
        
        analyzer = StanceAnalyzer()
        evidence = EvidenceItem(
            source_title="A detailed title supporting the claim fully with facts",
            source_type="journalism",
            publisher="Pub",
            date="2025-01-01",
            url_or_id="https://test.com",
            excerpt="This is a sufficiently long excerpt supporting the claim fully with facts and details."
        )
        result = analyzer.detect("A detailed title supporting the claim", evidence)
        self.assertEqual(result, "contradicts")

    def test_llm_fallback_chain_robust_parsing(self):
        from truth_mirror.llm_fallback import LLMFallbackChain
        chain = LLMFallbackChain(sequence=["groq"], models={"groq": "test-model"}, tracker_module="test")
        
        # Test conversational filler + trailing comma
        res1 = chain._parse_json('Here is the data:\n```json\n{"key": "value",}\n```')
        self.assertEqual(res1, {"key": "value"})
        
        # Test empty string returns None
        res2 = chain._parse_json("")
        self.assertIsNone(res2)

    @patch('truth_mirror.verdict_engine.VerdictEngine._call_gemini_sync_sdk', return_value=None)
    @patch('truth_mirror.groq_router.call_groq_with_key_rotation')
    def test_verdict_engine_groq_conversational_markdown_trailing_comma(self, mock_groq, mock_gemini):
        import asyncio
        from truth_mirror.verdict_engine import VerdictEngine
        
        mock_groq.return_value = (
            'Here is your verdict:\n```json\n{"verdict": "CONTRADICTED", "confidence": 0.9, "full_reasoning": "Reason",}\n```',
            "success"
        )
        engine = VerdictEngine()
        result = asyncio.run(engine.generate([], [], "Claim", None))
        self.assertEqual(result.verdict, "CONTRADICTED")
        self.assertEqual(result.confidence, 0.9)

    @patch('truth_mirror.hidden_story_extractor.LLMFallbackChain.execute')
    def test_hidden_story_extractor_none_or_malformed(self, mock_execute):
        import asyncio
        from truth_mirror.hidden_story_extractor import HiddenStoryExtractor
        from truth_mirror.source_analyzer import SourceAnalysis
        
        mock_execute.return_value = None
        extractor = HiddenStoryExtractor()
        source = SourceAnalysis(
            url="https://test.com",
            title="Title",
            source_name="Source 1",
            source_category="news",
            source_country="US",
            alignment="Center",
            reliability_tier=1,
            snippet="Snippet",
            summary="Summary",
            stance="SUPPORTS",
            stance_confidence=0.9,
            stance_reasoning="Reason",
            key_claims=["Claim 1"],
            what_emphasized="Emphasized",
            what_omitted="Omitted",
            hidden_implication="Implication"
        )
        result = asyncio.run(extractor.extract([source], "Claim", None))
        self.assertEqual(result, [])




