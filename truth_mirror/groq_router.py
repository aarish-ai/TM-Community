"""
Centralized Groq model routing configuration.
All Groq model strings are defined here — never hardcoded in other files.
Fallback Chain for Analysis: 70b-versatile -> 70b-specdec -> qwen-2.5-32b -> 8b-instant
"""

import os
import logging
import requests
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Connection pooling for synchronous requests
_session = requests.Session()

from truth_mirror.model_config import (
    GROQ_SIMPLE_MODEL,
    GROQ_SIMPLE_FALLBACK,
    GROQ_ANALYSIS_PRIMARY,
    GROQ_ANALYSIS_FALLBACK_1,
    GROQ_ANALYSIS_FALLBACK_2,
    GROQ_ANALYSIS_FALLBACK_3,
)

# Model metadata for logging
GROQ_MODEL_LABELS = {
    GROQ_SIMPLE_MODEL:        "gpt-oss-20b (simple tasks)",
    GROQ_SIMPLE_FALLBACK:     "gpt-oss-20b (simple fallback)",
    GROQ_ANALYSIS_PRIMARY:    "gpt-oss-120b (analysis)",
    GROQ_ANALYSIS_FALLBACK_1: "qwen3.8-27b (analysis fallback 1)",
    GROQ_ANALYSIS_FALLBACK_2: "qwen3.6-27b (analysis fallback 2)",
    GROQ_ANALYSIS_FALLBACK_3: "gpt-oss-20b (analysis fallback 3 — quality reduced)",
}

def get_model_label(model_id: str) -> str:
    return GROQ_MODEL_LABELS.get(model_id, model_id)

# ── GROQ KEY MANAGEMENT ───────────────────────────────────────────────

_key_cooldowns = {}
from truth_mirror.rate_limiter import llm_sync_limiter
import time

def get_groq_keys() -> list[str]:
    """
    Returns ordered list of Groq API keys.
    Key 1 (GROQ_API_KEY_1) is always checked first.
    Key 2 (GROQ_API_KEY_2) is the backup.
    Deduplicates — if both env vars point to same key, returns only one.
    """
    key1 = os.getenv("GROQ_API_KEY_1", "").strip()
    key2 = os.getenv("GROQ_API_KEY_2", "").strip()

    keys = []
    seen = set()
    for k in [key1, key2]:
        if k and k not in seen:
            keys.append(k)
            seen.add(k)

    if not keys:
        # Final fallback: try the original single-key env var
        fallback = os.getenv("GROQ_API_KEY", "").strip()
        if fallback:
            keys.append(fallback)

    return keys

def call_groq_with_key_rotation(
    payload: dict,
    timeout: int = 60,
    log_prefix: str = "[GroqRouter]"
) -> tuple[str | None, str]:
    """
    Makes a Groq API call, trying each key in order before giving up.
    Returns (response_content, status) where status is one of:
      "success"       — call succeeded
      "rate_limited"  — all keys returned 429 for this model
      "failed"        — all keys returned non-429 errors

    The caller is responsible for deciding what to do with each status.
    This function handles ONLY key rotation within a single model.
    Model fallback is handled by the caller (source_analyzer.py etc.).

    payload must be a complete Groq chat completion payload dict
    with "model" already set.
    """
    import json

    keys = get_groq_keys()
    if not keys:
        logger.error(f"{log_prefix} No Groq API keys available.")
        return None, "failed"

    model_name = payload.get("model", "unknown")

    while True:
        current_time = time.time()
        available_keys = [k for k in keys if _key_cooldowns.get(k, 0) < current_time]
        
        if not available_keys:
            # All keys on cooldown. Check graceful backoff.
            wait_times = [_key_cooldowns[k] - current_time for k in keys]
            min_wait = min(wait_times)
            if min_wait <= 60:
                logger.info(f"{log_prefix} All keys on cooldown. Graceful backoff for {min_wait:.1f}s.")
                time.sleep(min_wait + 0.1)
                continue # Retry after sleep
            else:
                logger.warning(
                    f"{log_prefix} All {len(keys)} keys rate limited for >60s "
                    f"for model {get_model_label(model_name)}. Model exhausted."
                )
                return None, "rate_limited"

        all_rate_limited = True
        for key_index, api_key in enumerate(available_keys, 1):
            try:
                logger.info(
                    f"{log_prefix} Trying model={get_model_label(model_name)} "
                    f"key={key_index}/{len(available_keys)}"
                )
                
                llm_sync_limiter.wait()
                
                response = _session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        cooldown_sec = float(retry_after) if retry_after else 60.0
                    except ValueError:
                        cooldown_sec = 60.0
                        
                    _key_cooldowns[api_key] = time.time() + cooldown_sec
                    logger.warning(
                        f"{log_prefix} Key rate limited (429) "
                        f"for model {get_model_label(model_name)}. Cooldown: {cooldown_sec}s."
                    )
                    continue

                if response.status_code != 200:
                    logger.warning(
                        f"{log_prefix} Key returned HTTP "
                        f"{response.status_code} for model {model_name}: {response.text}"
                    )
                    all_rate_limited = False
                    continue

                content = response.json()["choices"][0]["message"]["content"]
                logger.info(
                    f"{log_prefix} Success with key, "
                    f"model={get_model_label(model_name)}"
                )
                return content, "success"

            except Exception as e:
                logger.warning(
                    f"{log_prefix} Key exception for model "
                    f"{model_name}: {e}"
                )
                all_rate_limited = False
                
        # If we broke out of the loop and all were 429s, loop again to trigger backoff check
        if all_rate_limited:
            continue
            
        logger.error(
            f"{log_prefix} All keys failed (non-rate-limit errors) "
            f"for model {model_name}."
        )
        return None, "failed"
