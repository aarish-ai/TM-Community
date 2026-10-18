import concurrent.futures
from typing import List
from dataclasses import asdict

from truth_mirror.models import EvidenceItem
from truth_mirror.retrieval import RetrievalConfig, EvidenceRetriever
NEWS_FIRST_CLAIM_TYPES = ["geopolitical", "breaking_news", "event", "biographical", "policy"]

try:
    from truth_mirror.retrieval_news import GDELTConnector, GoogleNewsRSSConnector, NewsDataIOConnector
except ImportError:
    GDELTConnector = None
    GoogleNewsRSSConnector = None
    NewsDataIOConnector = None


class FreeSourceRetrieval(EvidenceRetriever):
    """
    Unified orchestrator for retrieving evidence from free academic, news, and
    fact-checking sources.

    For biographical, political, and current-event claims the connector order is
    rearranged so that news/fact-check sources run first and arXiv is skipped
    entirely.  For all other claim types the original order is preserved.
    """

    def __init__(self, cache_path: str = ".tm_cache.json", config: RetrievalConfig | None = None, disable_academic: bool = False):
        super().__init__(cache_path=cache_path, config=config)

        self.disable_academic = disable_academic

        # Build typed connector pools so we can reorder on demand.
        self._news_connectors: list = []
        self._acad_connectors: list = []

        if GDELTConnector:
            self._news_connectors.append(GDELTConnector(self.config))
        if GoogleNewsRSSConnector:
            self._news_connectors.append(GoogleNewsRSSConnector(self.config))
        if NewsDataIOConnector:
            self._news_connectors.append(NewsDataIOConnector(self.config))

    def _ordered_connectors(self, claim_type: str) -> list:
        """Return connectors in the correct priority order for *claim_type*."""
        return self._news_connectors

    def retrieve(self, query: str, claim_type: str = "mixed or ambiguous claim", include_wikinews: bool = True) -> List[EvidenceItem]:
        cache_key = f"{self.CACHE_VERSION}:{claim_type}::{query.strip().lower()}"
        if cache_key in self._cache:
            return [self._normalize_cached_item(EvidenceItem(**item)) for item in self._cache[cache_key]]

        results = []
        connectors = self._ordered_connectors(claim_type)

        def fetch_wiki():
            return self._query_wikipedia(query)[:4]
            
        def fetch_wikinews():
            return self._query_wikinews(query)[:1] if include_wikinews else []
            
        def fetch_crossref():
            return self._query_crossref(query)[:2] if not (claim_type in NEWS_FIRST_CLAIM_TYPES or self.disable_academic) else []

        def fetch(connector):
            try:
                if hasattr(connector, "search"):
                    return connector.search(query)
                elif hasattr(connector, "retrieve"):
                    return connector.retrieve(query)
                return []
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"[FreeSourceRetrieval] Connector {connector.__class__.__name__} failed: {e}")
                return []

        # Execute everything in parallel (throttled to avoid connection floods)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(connectors) + 3, 5)) as executor:
            futures = [
                executor.submit(fetch_wiki),
                executor.submit(fetch_wikinews),
                executor.submit(fetch_crossref)
            ]
            
            for c in connectors:
                futures.append(executor.submit(fetch, c))
                
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

        results = self._dedupe(results)
        self._cache[cache_key] = [asdict(item) for item in results]
        self._save_cache()
        return results
