from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from truth_mirror.geo_orchestrator import GeopoliticalPipeline
from truth_mirror.models import EvidenceItem
from truth_mirror.source_analyzer import SourceAnalyzer
from truth_mirror.verdict_engine import VerdictEngine

@patch("truth_mirror.geo_orchestrator.set_stage")
def test_geo_orchestrator_emits_expanded_stages(mock_set_stage):
    pipeline = GeopoliticalPipeline()
    pipeline._check_cache = MagicMock(return_value=None)
    pipeline.decomposer.decompose = MagicMock(return_value=[])
    pipeline.query_generator.generate = MagicMock(return_value=["test query"])
    pipeline.targeted_connectors = []
    
    def fake_retrieve(*args, **kwargs):
        return [EvidenceItem(
            url_or_id="http://test.com",
            source_title="Test",
            excerpt="Test",
            source_type="journalism",
            publisher="Test",
            date="2026-01-01"
        )]
    pipeline.retriever.retrieve = MagicMock(side_effect=fake_retrieve)
    
    with patch("truth_mirror.keyword_extractor.extract_search_queries", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = ["test query"]
        with patch.object(pipeline, '_deduplicate_evidence', return_value=[]) as mock_dedup:
            try:
                asyncio.run(pipeline.run_async("Test claim", request_id="req-123"))
            except Exception:
                pass

    emitted_stages = [call[0][0] for call in mock_set_stage.call_args_list]
    assert "classifying_temporal" not in emitted_stages # Should be replaced
    assert "decomposing_temporal" in emitted_stages
    assert "generating_queries" in emitted_stages
    assert "fetching_primary" in emitted_stages
    assert "fetching_regional" in emitted_stages
    assert "deduplicating" in emitted_stages

@patch("truth_mirror.source_analyzer.tracker")
@patch("truth_mirror.source_analyzer.set_stage")
def test_source_analyzer_emits_batches(mock_set_stage, mock_tracker):
    analyzer = SourceAnalyzer()
    analyzer._call_groq_batch = MagicMock(return_value=[MagicMock(summary="Test")])
    articles = [
        EvidenceItem(
            url_or_id=f"http://test{i}.com",
            source_title="Test claim",
            excerpt="Test claim",
            source_type="journalism",
            publisher="Test",
            date="2026-01-01"
        ) for i in range(8)
    ]
    asyncio.run(analyzer.analyze_all(articles, "Test claim", request_id="req-123"))
    emitted_stages = [call[0][0] for call in mock_set_stage.call_args_list]
    assert "analyzing_primary" in emitted_stages
    assert "cross_referencing" in emitted_stages

@patch("truth_mirror.verdict_engine.set_stage")
def test_verdict_engine_emits_stages(mock_set_stage):
    engine = VerdictEngine()
    engine._call_gemini_sync_sdk = MagicMock(return_value='{"verdict": "SUPPORTED"}')
    asyncio.run(engine.generate([], [], "Test claim", None, request_id="req-123"))
    emitted_stages = [call[0][0] for call in mock_set_stage.call_args_list]
    assert "weighing_contradictions" in emitted_stages
    assert "synthesizing_verdict" in emitted_stages
