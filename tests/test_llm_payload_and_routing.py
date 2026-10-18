import pytest
from unittest.mock import patch, MagicMock
from truth_mirror.model_config import (
    GROQ_ANALYSIS_FALLBACK_1,
    GROQ_ANALYSIS_FALLBACK_2,
    GROQ_ANALYSIS_PRIMARY,
    GROQ_SIMPLE_MODEL,
)
from truth_mirror.source_analyzer import SourceAnalyzer
from truth_mirror.verdict_engine import VerdictEngine
from truth_mirror.geo_query_generator import GeoQueryGenerator

def test_model_config_valid_model_names():
    assert GROQ_ANALYSIS_FALLBACK_2 == "qwen/qwen3.6-27b", f"Expected 'qwen/qwen3.6-27b' but got {GROQ_ANALYSIS_FALLBACK_2}"
    assert GROQ_ANALYSIS_FALLBACK_1 == "qwen/qwen3.8-27b"
    assert "qwen-2.5-32b" not in GROQ_ANALYSIS_FALLBACK_2
    assert "qwen/qwen-3.6-27b" != GROQ_ANALYSIS_FALLBACK_2

@patch("truth_mirror.source_analyzer.call_groq_with_key_rotation")
def test_source_analyzer_payload_max_tokens_budget(mock_call):
    mock_call.return_value = ('{"analyses": []}', "success")
    analyzer = SourceAnalyzer()
    
    analyzer._call_groq_batch("test claim", [], "test prompt", model="openai/gpt-oss-120b")
    
    assert mock_call.called
    called_payload = mock_call.call_args[1]["payload"]
    assert called_payload["max_tokens"] <= 2048, f"max_tokens should be <= 2048 to stay under TPM limit, got {called_payload['max_tokens']}"

@patch("truth_mirror.groq_router.call_groq_with_key_rotation")
@pytest.mark.anyio
async def test_verdict_engine_groq_max_tokens_budget(mock_call):
    mock_call.return_value = ('{"verdict": "SUPPORTED"}', "success")
    engine = VerdictEngine()
    
    with patch.object(engine, "_call_gemini_sync_sdk", return_value=None):
        verdict = await engine.generate([], [], "test claim", None)
        
    assert mock_call.called
    called_payload = mock_call.call_args[1]["payload"]
    assert called_payload["max_tokens"] <= 2048, f"VerdictEngine max_tokens should be <= 2048, got {called_payload['max_tokens']}"

@patch("truth_mirror.geo_query_generator.call_groq_with_key_rotation")
def test_geo_query_generator_json_object_schema(mock_call):
    mock_call.return_value = ('{"queries": ["q1", "q2", "q3", "q4"]}', "success")
    gen = GeoQueryGenerator()
    
    queries = gen.generate("test sub-claim", ["Party A"], "dispute")
    
    assert mock_call.called
    called_payload = mock_call.call_args[1]["payload"]
    assert called_payload.get("response_format") == {"type": "json_object"}, "GeoQueryGenerator must use json_object response format"
    assert len(queries) == 4
    assert queries == ["q1", "q2", "q3", "q4"]
