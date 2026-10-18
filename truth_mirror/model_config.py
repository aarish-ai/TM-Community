"""
Centralized AI Model Configuration
This file stores all model IDs used across the application. 
Change these values to update the models used by the engine.
"""

# ── Groq Models ────────────────────────────────────────────────────────

# Used in: geo_query_generator.py, local_decomposer.py, temporal_classifier.py
# Purpose: Primary model for simple structured tasks like generating search queries and extracting dates.
# Intelligence: Low/Medium (fast, cheap models work best).
GROQ_SIMPLE_MODEL = "openai/gpt-oss-20b"

# Used in: geo_query_generator.py, local_decomposer.py, temporal_classifier.py
# Purpose: Fallback model for simple structured tasks when primary fails.
# Intelligence: Low/Medium (fast, cheap models work best).
GROQ_SIMPLE_FALLBACK = "openai/gpt-oss-20b"

# Used in: verdict_engine.py, source_analyzer.py
# Purpose: Primary model for complex analysis tasks requiring nuance, deep context understanding, and reasoning.
# Intelligence: High (Flagship models required).
GROQ_ANALYSIS_PRIMARY = "openai/gpt-oss-120b"

# Used in: verdict_engine.py, source_analyzer.py
# Purpose: First fallback for complex analysis tasks.
# Intelligence: High.
GROQ_ANALYSIS_FALLBACK_1 = "qwen/qwen3.8-27b"

# Used in: verdict_engine.py, source_analyzer.py
# Purpose: Second fallback for complex analysis tasks.
# Intelligence: High.
GROQ_ANALYSIS_FALLBACK_2 = "qwen/qwen3.6-27b"

# Used in: verdict_engine.py, source_analyzer.py
# Purpose: Final fallback for complex analysis tasks.
# Intelligence: Low/Medium.
GROQ_ANALYSIS_FALLBACK_3 = "openai/gpt-oss-20b"

# ── OpenRouter Models ──────────────────────────────────────────────────

# Used in: geo_query_generator.py
# Purpose: Final fallback for search query generation when Groq fails.
# Intelligence: Low/Medium.
OPENROUTER_QUERY_FALLBACK = "nvidia/nemotron-3-super-120b-a12b:free"

# Used in: source_analyzer.py
# Purpose: Final fallback for analyzing source credibility and extracting claims when Groq fails.
# Intelligence: High (Needs strong reasoning).
OPENROUTER_ANALYSIS_FALLBACK = "google/gemma-4-31b-it:free"

# Used in: verdict_engine.py
# Purpose: Final fallback for rendering the final truth verdict when Groq fails.
# Intelligence: High (Needs strong reasoning).
OPENROUTER_VERDICT_FALLBACK = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Used in: geo_classifier.py
# Purpose: Final fallback for classifying claims when Groq fails.
# Intelligence: High (Needs strong reasoning).
OPENROUTER_CLASSIFIER_FALLBACK = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Used in: geo_synthesizer.py
# Purpose: Final fallback for synthesizing final reports when Groq fails.
# Intelligence: High (Needs strong reasoning).
OPENROUTER_SYNTHESIZER_FALLBACK = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Used in: hidden_story_extractor.py
# Purpose: Final fallback for extracting hidden stories when Groq fails.
# Intelligence: High (Needs strong reasoning).
OPENROUTER_HIDDEN_STORY_FALLBACK = "google/gemma-4-31b-it:free"
