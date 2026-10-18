# tests/integration/test_dns_load.py
import concurrent.futures
import pytest
from truth_mirror.retrieval_news import extract_article_text

URLS = [
    "https://www.aljazeera.com/",
    "https://www.dw.com/",
    "https://www.thehindu.com/",
    "https://www.bbc.com/",
    "https://www.reuters.com/",
] * 10  # 50 concurrent requests

@pytest.mark.integration
def test_concurrent_dns_resolution():
    """Replicates the production load to ensure no DNS drops occur."""
    success_count = 0
    failure_count = 0
    
    def fetch(url):
        try:
            # Import dynamically to test current architecture
            import truth_mirror.retrieval_news as rn
            session = getattr(rn, "get_session", lambda: getattr(rn, "SHARED_SESSION"))()
            resp = session.get(url, timeout=10, impersonate="chrome120")
            resp.raise_for_status()
            return True
        except Exception as e:
            if "curl: (6)" in str(e) or "Could not resolve host" in str(e):
                return False
            return True # Failed for other reasons (403, timeout), which is fine for this test

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch, URLS))
        
    failures = [r for r in results if r is False]
    
    # Assert there are ZERO DNS failures
    assert len(failures) == 0, f"Failed with {len(failures)} DNS resolution drops under load"
