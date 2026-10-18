"""
Non-western source retrieval connectors for Truth Mirror.
"""
import logging
import re
from typing import List
import urllib.parse
import urllib.request
import defusedxml.ElementTree as ET
from truth_mirror.retrieval_news import extract_article_text
from datetime import datetime, timezone
from truth_mirror.models import EvidenceItem
import concurrent.futures
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

EXTRACTION_CACHE = {}

class NonWesternRSSConnector:
    def __init__(self, source_name: str, domain: str, perspective_label: str):
        self.source_name = source_name
        self.domain = domain
        self.perspective_label = perspective_label
        self.max_results = 8
        self.timeout_seconds = 10

    def search(self, query: str) -> list[EvidenceItem]:
        site_query = f"{query} site:{self.domain}"
        api_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(site_query)}"
        
        from truth_mirror.rate_limiter import google_news_limiter
        
        google_news_limiter.wait()
        
        try:
            logger.info(f"[{self.source_name}Connector] Querying: {api_url}")
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                xml_bytes = response.read()
            xml_text = xml_bytes.decode('utf-8', errors='replace')
            # Remove illegal XML characters (e.g. \x00 to \x08, \x0B, \x0C, \x0E-\x1F)
            xml_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_text)
            root = ET.fromstring(xml_text)
        except Exception as e:
            logger.warning(f"[{self.source_name}Connector] Failed for query '{query}': {e}")
            return []

        items = []
        raw_items = []
        for node in root.findall("./channel/item")[:self.max_results]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            pub_date = (node.findtext("pubDate") or datetime.now(timezone.utc).date().isoformat()).strip()
            
            if not title or not link:
                continue
                
            source_text = node.findtext("source") or ""
            if source_text and self.source_name.lower() not in source_text.lower() and self.domain not in source_text.lower():
                continue
            
            raw_items.append((title, link, pub_date))

        def fetch_text(item_data):
            title, link, pub_date = item_data
            excerpt = title
            try:
                from truth_mirror.utils import decode_google_news_url_fast
                decoded_res = decode_google_news_url_fast(link)
                if decoded_res and decoded_res.get("status"):
                    link = decoded_res.get("decoded_url")
            except Exception as e:
                logger.warning(f"[{self.source_name}Connector] Failed to decode URL {link}: {e}")

            if link in EXTRACTION_CACHE:
                excerpt = EXTRACTION_CACHE[link][:1000]
            else:
                text = extract_article_text(link)
                if text and len(text.strip()) > 50:
                    EXTRACTION_CACHE[link] = text.strip()
                    excerpt = text.strip()[:1000]

            return EvidenceItem(
                source_title=title,
                source_type="journalism",
                publisher=self.source_name,
                date=pub_date,
                url_or_id=link,
                excerpt=excerpt,
                language="en",
                independence_key=f"news:{self.domain.replace('.', '_')}",
                perspective_label=self.perspective_label
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(raw_items) or 1, 2)) as executor:
            future_to_url = {executor.submit(fetch_text, item): item for item in raw_items}
            done, not_done = concurrent.futures.wait(future_to_url.keys(), timeout=30)
            for future in done:
                try:
                    items.append(future.result())
                except Exception as exc:
                    logger.warning(f"[{self.source_name}Connector] Fetch generated an exception: {exc}")
            for future in not_done:
                logger.warning(f"[{self.source_name}Connector] Fetch timed out for one of the items.")
                future.cancel()
            
        logger.info(f"[{self.source_name}Connector] Retrieved {len(items)} items for: {query}")
        return items

    def retrieve(self, query: str) -> list[EvidenceItem]:
        return self.search(query)

class TargetedRSSConnector(NonWesternRSSConnector):
    def __init__(self, source_name: str, domain: str, perspective_label: str = "Unknown"):
        super().__init__(source_name, domain, perspective_label)

