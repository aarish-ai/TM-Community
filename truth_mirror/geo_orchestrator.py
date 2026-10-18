"""Orchestrator for the Geopolitical Intelligence Engine."""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from typing import List
import logging
import asyncio
from datetime import datetime
import time
import json
import re
import random
import aiohttp

logger = logging.getLogger(__name__)


from truth_mirror.local_decomposer import LocalDecomposer
from truth_mirror.geo_query_generator import GeoQueryGenerator
from truth_mirror.retrieval_free import FreeSourceRetrieval
from truth_mirror.geo_synthesizer import GeoSynthesizer
from truth_mirror.models import GeopoliticalResult, EvidenceItem
from truth_mirror.retrieval import RetrievalConfig
from truth_mirror.caching import EvidenceCache
from dataclasses import asdict
from truth_mirror.rate_limiter import rate_limiter
from truth_mirror.pipeline_status import set_stage

def _dict_to_geo_result(d: dict) -> "GeopoliticalResult":
    """Reconstruct a GeopoliticalResult from a cached dictionary."""
    from truth_mirror.models import GeopoliticalResult
    d.pop("_from_cache", None)
    try:
        return GeopoliticalResult(**{
            k: v for k, v in d.items()
            if k in GeopoliticalResult.__dataclass_fields__
        })
    except Exception as e:
        logger.warning(f"Cache reconstruction failed: {e}. Returning raw dict.")
        # Fallback: create minimal GeopoliticalResult
        return GeopoliticalResult(
            original_claim=d.get("original_claim", ""),
            is_geopolitical=d.get("is_geopolitical", True),
            verdict=d.get("verdict", "Unclear"),
            **{k: d[k] for k in [
                "source_analyses", "hidden_stories",
                "verdict_data", "total_sources", "confidence"
            ] if k in d}
        )

class GeopoliticalPipeline:
    """Pipeline orchestrator for the Geopolitical Intelligence Engine."""

    def __init__(self) -> None:

        self.decomposer = LocalDecomposer()
        self.query_generator = GeoQueryGenerator()
        
        # Configure the retriever (max_results per connector is also set to 8 by default)
        self.retriever = FreeSourceRetrieval(config=RetrievalConfig(max_results=8), disable_academic=True)
        
        self.synthesizer = GeoSynthesizer()

        self._result_cache = EvidenceCache()
        # Cleanup expired entries on startup (non-blocking, cheap)
        try:
            deleted = self._result_cache.cleanup_expired_results()
            if deleted > 0:
                logger.info(f"[GeoOrchestrator] Cleaned up {deleted} expired result cache entries.")
        except Exception as e:
            logger.warning(f"[GeoOrchestrator] Cache cleanup failed: {e}")


        self.targeted_connectors = []
        try:
            from truth_mirror.retrieval_nonwestern import TargetedRSSConnector
            from truth_mirror.source_registry import SOURCE_REGISTRY
            
            targeted_domains = [
                "aljazeera.com", "cgtn.com", "tass.com", "xinhuanet.com", "dawn.com",
                "middleeasteye.net", "presstv.ir", "tehrantimes.com", "reuters.com",
                "bbc.com", "apnews.com", "nytimes.com", 
                "asia.nikkei.com", "thehindu.com", "scmp.com",
                "africanews.com", "thejakartapost.com", "al-monitor.com",
                "kyivindependent.com", "meduza.io", "dailymaverick.co.za",
                "mercopress.com", "insightcrime.org", "balkaninsight.com"
            ]
            
            for domain in targeted_domains:
                meta = SOURCE_REGISTRY.get(domain, {})
                name = meta.get("name", domain)
                alignment = meta.get("alignment", "Unknown")
                try:
                    self.targeted_connectors.append(TargetedRSSConnector(name, domain, alignment))
                except Exception as e:
                    logger.warning(f"Failed to load connector for {domain}: {e}")
        except ImportError as e:
            logger.warning(f"Failed to import non-western connectors: {e}")
            
        logger.info(f"[GeopoliticalPipeline] Initialized with {len(self.retriever._news_connectors)} news connectors and {len(self.retriever._acad_connectors)} academic connectors.")

    def _parallel_retrieve(self, queries: List[str], claim_subtype: str, base_claim: str, request_id: str = None) -> List[EvidenceItem]:
        """
        Fetches evidence for all generated queries in parallel.
        Ensures that the retrieval pulls up to 8 items per query.
        Preserves query order for relevance ranking.
        """
        all_results = []
        max_results_per_query = 8
        
        set_stage("fetching_primary", request_id=request_id)
        # We cap workers at 4 to avoid connection limits
        with ThreadPoolExecutor(max_workers=min(len(queries) + 1, 4)) as executor:
            futures = []
            for idx, q in enumerate(queries):
                # Only use Wikipedia/Academic engines for the very first query (the broad entity query)
                use_wikinews = (idx == 0)
                future = executor.submit(
                    self.retriever.retrieve, q, claim_subtype, use_wikinews
                )
                futures.append(future)

            for future in futures:
                try:
                    results = future.result()
                    # Up to 8 items per query
                    all_results.extend(results[:max_results_per_query])
                except Exception as e:
                    logger.warning(f"[GeoOrchestrator] Error fetching query results: {e}")

        # Also run targeted connectors on the base claim
        def fetch_targeted(connector):
            try:
                return connector.search(base_claim)
            except Exception as e:
                logger.warning(f"[GeoOrchestrator] Targeted connector {connector.source_name} failed: {e}")
                return []
                
        set_stage("fetching_regional", request_id=request_id)
        with ThreadPoolExecutor(max_workers=min(len(self.targeted_connectors)+1, 4)) as tgt_executor:
            tgt_futures = []
            for c in self.targeted_connectors:
                tgt_futures.append(tgt_executor.submit(fetch_targeted, c))

            for future in tgt_futures:
                try:
                    results = future.result()
                    all_results.extend(results[:max_results_per_query])
                except Exception as e:
                    logger.warning(f"[GeoOrchestrator] Error fetching targeted query results: {e}")
                    
        return all_results

    def verify(self, claim: str, scope_gate=None, request_id: str = '__global__') -> GeopoliticalResult:
        return asyncio.run(self.run_async(claim, scope_gate, request_id=request_id))

    def _check_cache(self, claim: str) -> GeopoliticalResult | None:
        cache_key = EvidenceCache.normalize_claim_key(claim)
        cached_result = self._result_cache.get_result(cache_key)
        if cached_result:
            logger.info(f"[GeoOrchestrator] Cache HIT for claim: '{claim[:60]}...'")
            cached_result["_from_cache"] = True
            return _dict_to_geo_result(cached_result)
        logger.info(f"[GeoOrchestrator] Cache MISS for claim: '{claim[:60]}...'")
        return None

    def _generate_queries(self, claim: str, sub_claims: list[str], involved_parties: list[str], claim_subtype: str, temporal_context) -> list[str]:
        all_queries = []
        for sub_claim in sub_claims:
            if sub_claim.lower().startswith("the period in question") or sub_claim.lower().startswith("the action is currently"):
                continue
            queries = self.query_generator.generate(
                sub_claim, 
                involved_parties, 
                claim_subtype,
                temporal_context=temporal_context
            )
            all_queries.extend(queries)

        if temporal_context.needs_date and temporal_context.date_qualifier:
            dq = temporal_context.date_qualifier
            dq_suffix = "" if dq.lower() in claim.lower() else f" {dq}"
            clean_claim = claim.rstrip('.')
        else:
            dq_suffix = ""
            clean_claim = claim.rstrip('.')
            
        base_search = " ".join(involved_parties) if involved_parties else clean_claim
        
        perspective_queries = [
            f"{base_search}{dq_suffix} Western media Reuters AP",
            f"{base_search}{dq_suffix} Russian Chinese media TASS CGTN",
            f"{base_search}{dq_suffix} Middle East Al Jazeera",
            f"{base_search}{dq_suffix} official government statement"
        ]
        
        # Geographic Query Routing (Basic)
        middle_east_keywords = ['israel', 'gaza', 'palestine', 'iran', 'syria', 'lebanon', 'yemen', 'saudi', 'iraq']
        if any(kw in claim.lower() for kw in middle_east_keywords):
            perspective_queries.append(f"{base_search}{dq_suffix} Middle East Eye Dawn SCMP")
            
        all_queries.extend(perspective_queries)
        return all_queries

    def _get_infra_failure_result(self, claim: str) -> GeopoliticalResult:
        _INFRA_FAILURE_VERDICT = (
            "All available AI models (Groq 70b, 70b-specdec, Qwen-32b, 8b) "
            "were simultaneously rate-limited or unreachable during source "
            "analysis, and the Gemini fallback also failed. This is a "
            "temporary infrastructure capacity issue, not an analytical "
            "finding about the claim itself."
        )
        return GeopoliticalResult(
            claim=claim,
            original_claim=claim,
            is_geopolitical=True,
            source_analyses=[],
            total_sources=0,
            hidden_stories=[],
            verdict_data={
                "verdict": "ANALYSIS_FAILED",
                "confidence": 0.0,
                "confidence_label": "N/A",
                "one_line_verdict": (
                    "Analysis could not be completed — API limits exhausted. "
                    "Please wait a few minutes and try again."
                ),
                "full_reasoning": _INFRA_FAILURE_VERDICT,
                "what_is_true": "N/A — source analysis could not be completed.",
                "what_is_false": "N/A — source analysis could not be completed.",
                "what_is_unclear": "N/A — source analysis could not be completed.",
                "strongest_evidence_for": "N/A",
                "strongest_evidence_against": "N/A",
                "source_quality_note": (
                    "No sources were analyzed. Please retry your claim in "
                    "a few minutes when API capacity is restored."
                ),
            },
            verdict="ANALYSIS_FAILED",
            final_verdict="ANALYSIS_FAILED",
            confidence=0.0,
        )

    def _deduplicate_evidence(self, all_evidence: list) -> list:
        seen = set()
        deduped_evidence = []
        for item in all_evidence:
            key = (item.url_or_id or item.source_title).strip().lower()
            if key not in seen:
                seen.add(key)
                deduped_evidence.append(item)
        return deduped_evidence

    def _cache_store(self, result: GeopoliticalResult, temporal_context) -> None:
        cache_key = EvidenceCache.normalize_claim_key(result.claim)
        temporal_type = getattr(temporal_context, "temporal_type", "current_state")
        try:
            if (not result.source_analyses or
                not result.verdict_data or
                result.verdict in ["Unclear", "UNVERIFIABLE"]):
                logger.info("[GeoOrchestrator] Skipping cache for incomplete/unclear result.")
            else:
                result_dict = asdict(result)
                self._result_cache.set_result(cache_key, result_dict, temporal_type)
                logger.info(f"[GeoOrchestrator] Result cached for {temporal_type} claim (TTL based on type).")
        except Exception as e:
            logger.warning(f"[GeoOrchestrator] Failed to cache result: {e}")

    async def run_async(self, claim: str, scope_gate=None, request_id: str = '__global__') -> GeopoliticalResult:
        from truth_mirror.source_analyzer import SourceAnalyzer
        from truth_mirror.hidden_story_extractor import HiddenStoryExtractor
        from truth_mirror.verdict_engine import VerdictEngine
        from truth_mirror.temporal_classifier import TemporalClassifier
        from truth_mirror.run_tracker import tracker
        from truth_mirror.testing_logger import TestingLogger
        from truth_mirror.gemini_analyzer import GeminiAnalyzer
        
        GeminiAnalyzer.reset_call_count()
        tracker.set_current(request_id)
        try:
            tracker.reset(claim)
            start_time = time.time()

            cached_res = self._check_cache(claim)
            if cached_res:
                tracker.record("cache", "cache", "local", "success")
                events = tracker.get_stage_summary()
                test_logger = TestingLogger()
                test_logger.log_run(claim, cached_res, events, time.time() - start_time)
                tracker.reset("")
                return cached_res

            # 1. Classification
            involved_parties = scope_gate.involved_parties if scope_gate else []
            claim_subtype = scope_gate.claim_subtype if scope_gate else ""
            
            # 2. Decomposition
            set_stage("decomposing_temporal", request_id=request_id)
            sub_claims = self.decomposer.decompose(claim)

            # Classify temporal intent
            temporal_classifier = TemporalClassifier()
            temporal_context = temporal_classifier.classify(claim)

            # 3. Query Generation
            set_stage("generating_queries", request_id=request_id)
            from truth_mirror.keyword_extractor import extract_search_queries
            optimized_queries = await extract_search_queries(claim)
            all_queries = self._generate_queries(claim, sub_claims, involved_parties, claim_subtype, temporal_context)
            all_queries.extend(optimized_queries)

            # Parallel Retrieval
            all_evidence = self._parallel_retrieve(all_queries, claim_subtype, claim, request_id=request_id)
            set_stage("deduplicating", request_id=request_id)
            deduped_evidence = self._deduplicate_evidence(all_evidence)
            
            # Pre-filter for relevancy using LLM removed in favor of KeywordExtractor
            # deduped_evidence = await filter_relevant_evidence(deduped_evidence, claim)
            
            # Enforce Source Diversity Quota
            non_western_count = sum(1 for e in deduped_evidence if e.perspective_label and e.perspective_label.lower() != "western")
            if non_western_count < 2:
                logger.info(f"[GeoOrchestrator] Diversity quota not met (only {non_western_count} non-Western). Triggering targeted fallback...")
                try:
                    from truth_mirror.retrieval_news import NewsDataIOConnector
                    fallback_results = NewsDataIOConnector().search(claim)
                    if fallback_results:
                        deduped_evidence.extend(fallback_results)
                        deduped_evidence = self._deduplicate_evidence(deduped_evidence)
                except Exception as e:
                    logger.warning(f"Fallback retrieval failed: {e}")

            # Stage 2: Per-source stance analysis
            analyzer = SourceAnalyzer()
            async with aiohttp.ClientSession() as session:
                source_analyses = await analyzer.analyze_all(deduped_evidence, claim, max_concurrent=3, temporal_context=temporal_context, session=session, request_id=request_id)
                source_analyses = [s for s in source_analyses if s.summary]

                await rate_limiter.wait_if_needed("gemini")

                if not source_analyses:
                    res = self._get_infra_failure_result(claim)
                    events = tracker.get_stage_summary()
                    test_logger = TestingLogger()
                    test_logger.log_run(claim, res, events, time.time() - start_time)
                    tracker.reset("")
                    return res

                gemini_client = getattr(self.synthesizer, "client", None)

                # Stage 4: Hidden story extraction
                set_stage("extracting_stories", request_id=request_id)
                extractor = HiddenStoryExtractor()
                hidden_stories = await extractor.extract(source_analyses, claim, gemini_client, temporal_context=temporal_context)
                await rate_limiter.wait_if_needed("gemini")

                # Stage 5: Verdict generation
                engine = VerdictEngine()
                verdict = await engine.generate(source_analyses, hidden_stories, claim, gemini_client, temporal_context=temporal_context, request_id=request_id)
                await rate_limiter.wait_if_needed("gemini")

                result = GeopoliticalResult(
                    claim=claim,
                    original_claim=claim,
                    is_geopolitical=True,
                    source_analyses=[s.__dict__ for s in source_analyses],
                    total_sources=len(source_analyses),
                    hidden_stories=[h.__dict__ for h in hidden_stories],
                    verdict_data=verdict.__dict__,
                    verdict=verdict.verdict,
                    final_verdict=verdict.verdict,
                    confidence=verdict.confidence,
                    temporal_type=temporal_context.temporal_type if temporal_context else "",
                    temporal_qualifier=temporal_context.date_qualifier if temporal_context else ""
                )

                self._cache_store(result, temporal_context)

                elapsed = time.time() - start_time
                events = tracker.get_stage_summary()
                test_logger = TestingLogger()
                test_logger.log_run(claim, result, events, elapsed)
                tracker.reset("")

                return result
        finally:
            tracker.clear_current()
            tracker.remove(request_id)


    @staticmethod
    def to_json(result) -> dict:
        """Serialise a VerificationResult or GeopoliticalResult to a dict guaranteed to include all
        frontend-required fields."""
        from truth_mirror.models import GeopoliticalResult
        from dataclasses import asdict
        
        try:
            from truth_mirror.models import VerificationResult
            if isinstance(result, VerificationResult):
                base = asdict(result)
                required_fields = {
                    "final_verdict": base.get("final_verdict", "Unclear"),
                    "confidence": base.get("confidence", 0.0),
                    "confidence_interval": base.get("confidence_interval", (0.0, 1.0)),
                    "reasoning": base.get("reasoning", ""),
                    "evidence_summary": base.get("evidence_summary", "No evidence summary available."),
                    "key_sources": base.get("key_sources", []),
                    "warnings": base.get("warnings", []),
                    "missing_information": base.get("missing_information", []),
                    "claim_type": base.get("claim_type", ""),
                    "original_claim": base.get("original_claim", ""),
                    "normalized_claim": base.get("normalized_claim", ""),
                    "sub_claims": base.get("sub_claims", []),
                    "hidden_story_items": base.get("hidden_story_items", []),
                    "evidence_by_region": base.get("evidence_by_region", {}),
                    "geo_divergence_detected": base.get("geo_divergence_detected", False),
                    "narrative_coherence_score": base.get("narrative_coherence_score", 0.0),
                    "source_diversity_score": base.get("source_diversity_score", 0.0),
                    "human_review_recommended": base.get("human_review_recommended", False),
                    "generated_at": base.get("generated_at", ""),
                }
                return {**base, **required_fields}
        except ImportError:
            pass

        if isinstance(result, GeopoliticalResult):
            base = asdict(result)
            # Ensure required fields for GeopoliticalResult if any missing logic is expected
            return base
            
        return asdict(result) if hasattr(result, '__dataclass_fields__') else result
