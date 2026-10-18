import os
import json
import logging
from dataclasses import dataclass
from typing import List
import asyncio

from truth_mirror.source_analyzer import SourceAnalysis
from truth_mirror.run_tracker import tracker
from truth_mirror.llm_fallback import LLMFallbackChain
from truth_mirror.groq_router import GROQ_ANALYSIS_PRIMARY
from truth_mirror.model_config import OPENROUTER_HIDDEN_STORY_FALLBACK
from truth_mirror.utils import parse_llm_json

logger = logging.getLogger(__name__)

@dataclass
class HiddenStory:
    title: str
    explanation: str
    supporting_facts: list[str]
    which_sources_hint_at_this: list[str]
    which_sources_suppress_this: list[str]
    significance: str

class HiddenStoryExtractor:
    async def extract(
        self,
        source_analyses: List[SourceAnalysis],
        claim: str,
        gemini_client,
        temporal_context=None
    ) -> List[HiddenStory]:
        if not source_analyses:
            return []
            
        sources_parts = []
        for s in source_analyses:
            sources_parts.append(f"[{s.source_name}] Stance: {s.stance} | Key Claims: {', '.join(s.key_claims)}")
        formatted_all_sources = "\n".join(sources_parts)
        
        claim_with_context = claim
        if temporal_context and hasattr(temporal_context, 'date_qualifier') and temporal_context.date_qualifier:
            claim_with_context = f"{claim} (Timeframe: {temporal_context.date_qualifier})"
            
        prompt = f"""You are an experienced investigative journalist and geopolitical analyst with deep knowledge of how media narratives are constructed, what states and media organisations have incentives to hide, and what patterns of omission reveal about real events.

You have been given a full analysis of {len(source_analyses)} news sources regarding the following claim:

CLAIM: {claim_with_context}

ALL SOURCE SUMMARIES:
{formatted_all_sources}

Your task is to identify 2-5 hidden stories, patterns, or angles that:
- Are NOT the main narrative any source is pushing
- Emerge from CONNECTING facts that individual sources report separately
- Explain WHY certain facts are being emphasized or suppressed
- Represent what an experienced intelligence analyst or senior journalist would conclude by reading between the lines
- May involve: economic incentives, military strategy, domestic political pressures, diplomatic back-channels, historical patterns being repeated, or facts that contradict the official narrative of multiple parties simultaneously

For each hidden story, respond in this JSON format:
{{
  "title": "Short headline",
  "explanation": "3-5 sentence explanation of the hidden story or pattern.",
  "supporting_facts": ["Specific fact from sources that supports this", "..."],
  "which_sources_hint_at_this": ["source name", "..."],
  "which_sources_suppress_this": ["source name", "..."],
  "significance": "Why this matters and what it changes about understanding the claim."
}}

Return ONLY a valid JSON array. The array must contain ONLY JSON objects. Do NOT include any strings, explanations, or preamble text as array elements. Do NOT wrap the array in an object. The first character of your response must be '[' and the last must be ']'. Any non-object element will cause a system failure. Be intellectually rigorous. Do not speculate wildly - ground every hidden story in specific observable facts from the sources. But do not be timid: if the facts point somewhere the mainstream narrative ignores, say so clearly.
"""
        def run_sync():
            chain = LLMFallbackChain(
                sequence=["gemini", "groq", "openrouter"],
                models={
                    "gemini": "gemini-3.5-flash",
                    "groq": GROQ_ANALYSIS_PRIMARY,
                    "openrouter": OPENROUTER_HIDDEN_STORY_FALLBACK
                },
                tracker_module="hidden_story_extraction",
                temperature=0.2,
                max_tokens=4096
            )
            data = chain.execute(prompt)
            if data is None:
                logger.error("All API fallbacks failed for hidden story extraction.")
            return data

        try:
            data = await asyncio.to_thread(run_sync)
            result = []
            if data:
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    if not isinstance(item, dict):
                        logger.warning(f"[HiddenStoryExtractor] Skipping non-dict item in response: {type(item)}")
                        continue
                    result.append(HiddenStory(
                        title=item.get("title", ""),
                        explanation=item.get("explanation", ""),
                        supporting_facts=item.get("supporting_facts", []),
                        which_sources_hint_at_this=item.get("which_sources_hint_at_this", []),
                        which_sources_suppress_this=item.get("which_sources_suppress_this", []),
                        significance=item.get("significance", "")
                    ))
            return result
        except Exception as e:
            logger.error(f"Hidden story extraction failed entirely: {e}")
            return []

