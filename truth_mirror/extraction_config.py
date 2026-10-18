"""Static configuration for the article extraction fallback chain."""

# Publishers confirmed to block with 401, 403, curl(35), or curl(28) on every run.
# Keep sorted alphabetically.
ALWAYS_BLOCKED_DOMAINS: frozenset[str] = frozenset({
    "aljazeera.com",
    "criticalthreats.org",
    "economist.com",
    "forbes.com",
    "news.un.org",
    "nytimes.com",
    "pravda.com.ua",
    "reuters.com",
    "texaspolicy.com",
    "wired-gov.net",
})

# Seconds to wait per HTTP request in each fallback layer.
EXTRACTION_TIMEOUT: int = 20

# Maximum threads that may be inside the Wayback Machine fallback simultaneously.
MAX_WAYBACK_CONCURRENT: int = 2

# Minimum seconds between consecutive Wayback Machine HTTP calls (per-thread).
WAYBACK_MIN_INTERVAL: float = 2.0
