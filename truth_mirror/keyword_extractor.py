import logging
import json
import asyncio
import aiohttp
from typing import List
from truth_mirror.key_rotator import get_current_key, rotate_gemini_key
from truth_mirror.utils import parse_llm_json

logger = logging.getLogger(__name__)

async def extract_search_queries(claim: str) -> List[str]:
    """
    Uses Gemini 2.5 Flash to convert a raw user claim into optimized
    Google News search queries.
    """
    prompt = f"""You are an expert open-source intelligence (OSINT) researcher.
Your task is to take the following raw claim and generate 3 highly optimized, punchy search queries that will yield the best results on Google News.

RAW CLAIM: {claim}

Rules:
1. Return exactly 3 queries.
2. Make them concise and focused on the core entities and actions (e.g., instead of "Did Iran strike Israel with ballistic missiles in August", use "Iran Israel ballistic missiles attack").
3. Omit filler words.
4. Respond in strict JSON format.

Respond in JSON format only:
{{
  "queries": [
    "query 1",
    "query 2",
    "query 3"
  ]
}}
"""
    
    model = "gemini-2.5-flash"
    for attempt in range(4):
        api_key = get_current_key()
        if not api_key:
            return [claim] # fallback to raw claim if no key

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=15) as resp:
                    if resp.status in (429, 403):
                        logger.warning(f"[KeywordExtractor] Gemini 429. Rotating key.")
                        rotate_gemini_key()
                        await asyncio.sleep(2)
                        continue
                    if resp.status != 200:
                        logger.warning(f"[KeywordExtractor] Gemini HTTP {resp.status}")
                        return [claim]

                    data = await resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = parse_llm_json(raw_text)
                    if parsed is None:
                        raise ValueError("Failed to parse LLM JSON")
                    queries = parsed.get("queries", [])
                    if queries and isinstance(queries, list):
                        logger.info(f"[KeywordExtractor] Generated queries: {queries}")
                        return queries
                    return [claim]

        except Exception as e:
            logger.warning(f"[KeywordExtractor] Attempt {attempt+1} failed: {e}")
            await asyncio.sleep(1)

    logger.warning("[KeywordExtractor] All attempts failed, falling back to raw claim.")
    return [claim]
