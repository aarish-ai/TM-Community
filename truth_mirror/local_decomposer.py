import os
import json
import logging
from truth_mirror.groq_router import GROQ_SIMPLE_MODEL, GROQ_SIMPLE_FALLBACK, get_model_label, call_groq_with_key_rotation
from truth_mirror.run_tracker import tracker
from truth_mirror.utils import parse_llm_json
import requests
import re
import time
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

logger = logging.getLogger(__name__)

class LocalDecomposer:
    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def decompose(self, claim: str) -> list[str]:
        prompt = f"""Break this claim into simple sub-claims, separating temporal elements from core factual elements.
Return ONLY a JSON object with a "sub_claims" key containing an array of strings. Do not include markdown formatting or conversational text.
CRITICAL: Output valid JSON only, starting with '{{' and ending with '}}'.

Ensure the decomposition is timeline-agnostic and does not contain specific dates, months, or years. Keep queries broad and neutral.

Example input: "Donald Trump is president of USA in the current era"
Example output: {{"sub_claims": ["Donald Trump is president of the USA", "The period in question is the current era"]}}

Example input: "Donald Trump was president in a past term"
Example output: {{"sub_claims": ["Donald Trump is president of the USA", "The period in question is a past term"]}}

Example input: "A war is happening today"
Example output: {{"sub_claims": ["A war is happening", "The action is currently ongoing"]}}

Claim: "{claim}"

Output JSON:"""
        
        def _call_groq(prompt_str: str) -> list | None:
            payload = {
                "model": GROQ_SIMPLE_MODEL,
                "messages": [{"role": "user", "content": prompt_str}],
                "temperature": 0.1,
                "max_tokens": 1024,
                "response_format": {"type": "json_object"}
            }

            content, status = call_groq_with_key_rotation(
                payload=payload,
                timeout=25,
                log_prefix="[LocalDecomposer]"
            )

            if status != "success" or content is None:
                record_status = "rate_limited" if status == "rate_limited" else "failed"
                tracker.record("decomposer", GROQ_SIMPLE_MODEL, "groq", record_status)

                # Try GROQ_SIMPLE_FALLBACK before giving up on Groq
                logger.info(f"[LocalDecomposer] Primary 8b failed. Trying fallback 8b "
                            f"({GROQ_SIMPLE_FALLBACK}).")
                fallback_payload = payload.copy()
                fallback_payload["model"] = GROQ_SIMPLE_FALLBACK

                content, status = call_groq_with_key_rotation(
                    payload=fallback_payload,
                    timeout=25,
                    log_prefix="[LocalDecomposer-fallback]"
                )

                if status != "success" or content is None:
                    tracker.record("decomposer", GROQ_SIMPLE_FALLBACK, "groq",
                                   "rate_limited" if status == "rate_limited" else "failed")
                    return None

                try:
                    parsed = parse_llm_json(content)
                    if parsed is None:
                        raise ValueError("Failed to parse LLM JSON")
                    tracker.record("decomposer", GROQ_SIMPLE_FALLBACK, "groq", "fallback_used")
                    if isinstance(parsed, dict) and "sub_claims" in parsed and isinstance(parsed["sub_claims"], list):
                        return parsed["sub_claims"]
                    if isinstance(parsed, list):
                        return parsed
                    for key in parsed:
                        if isinstance(parsed[key], list):
                            return parsed[key]
                    return None
                except Exception as e:
                    logger.warning(f"[LocalDecomposer] Fallback 8b parse failed: {e}")
                    tracker.record("decomposer", GROQ_SIMPLE_FALLBACK, "groq", "failed")
                    return None

            try:
                parsed = parse_llm_json(content)
                if parsed is None:
                    raise ValueError("Failed to parse LLM JSON")
                logger.info("[LocalDecomposer] Groq call succeeded.")
                tracker.record("decomposer", GROQ_SIMPLE_MODEL, "groq", "success")
                if isinstance(parsed, dict) and "sub_claims" in parsed and isinstance(parsed["sub_claims"], list):
                    return parsed["sub_claims"]
                if isinstance(parsed, list):
                    return parsed
                for key in parsed:
                    if isinstance(parsed[key], list):
                        return parsed[key]
                return None
            except Exception as e:
                logger.warning(f"[LocalDecomposer] Failed to parse Groq response: {e}")
                tracker.record("decomposer", GROQ_SIMPLE_MODEL, "groq", "failed")
                return None

        try:
            response_text = None
            openrouter_failed = False
            
            logger.info(f"[LocalDecomposer] Attempting Groq ({get_model_label(GROQ_SIMPLE_MODEL)}) for claim decomposition.")
            groq_result = _call_groq(prompt)
            if groq_result is not None:
                # Format to JSON string so the rest of the parsing logic handles it uniformly
                response_text = json.dumps(groq_result)
            elif OPENROUTER_API_KEY:
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://truthmirror.app",
                    "X-Title": "Truth Mirror"
                }
                payload = {
                    "models": [
                        "nvidia/nemotron-3-ultra-550b-a55b:free", 
                        "google/gemma-4-26b-a4b-it:free", 
                        "nvidia/nemotron-3.5-lightning:free"
                    ],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
                        if response.status_code == 429:
                            wait_time = (2 ** attempt) + 1
                            logger.warning(f"[LocalDecomposer] Rate limited on attempt {attempt+1}. Waiting {wait_time}s before retry.")
                            time.sleep(wait_time)
                            if attempt == max_retries - 1:
                                openrouter_failed = True
                            continue
                        response.raise_for_status()
                        response_text = response.json()["choices"][0]["message"]["content"]
                        model_used = response.json().get("model", "unknown_openrouter_model")
                        openrouter_failed = False
                        tracker.record("decomposer", model_used, "openrouter", "success")
                        break
                    except Exception as e:
                        logger.warning(f"OpenRouter failed ({e}).")
                        openrouter_failed = True
                        break
            if openrouter_failed:
                raise ValueError("OpenRouter API failed for decomposition.")
            
            subclaims = []
            try:
                parsed = parse_llm_json(response_text)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            subclaims = v
                            break
                elif isinstance(parsed, list):
                    subclaims = parsed
            except Exception:
                start = response_text.find('[')
                end = response_text.rfind(']')
                if start != -1 and end != -1 and end > start:
                    try:
                        subclaims = parse_llm_json(response_text[start:end+1])
                    except Exception:
                        pass
            
            if not subclaims:
                raise ValueError("Response is not a valid JSON array or could not be parsed")
            
            # Validation
            if not isinstance(subclaims, list):
                raise ValueError("Response is not a JSON array")
                
            if not subclaims:
                raise ValueError("Empty list")
                
            if len(subclaims) > 6:
                raise ValueError("List length exceeds 6")
                
            valid_subclaims = []
            for item in subclaims:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError("Element is not a non-empty string")
                
                item = item.strip()
                # Condition: Relaxed length validation
                if len(claim) > 15 and len(item) >= len(claim) * 2 and len(subclaims) <= 1:
                    raise ValueError("Single element is significantly longer than the original claim")
                    
                valid_subclaims.append(item)
                
            return valid_subclaims
            
        except Exception as e:
            logger.info(f"Fallback to original claim (decomposition failed): {e}")
            tracker.record("decomposer", "identity_fallback", "heuristic_fallback", "success")
            return [claim]
