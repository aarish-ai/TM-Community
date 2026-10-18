"""News and Current Events retrieval connectors."""

from __future__ import annotations

import json
import re
import urllib.parse
import defusedxml.ElementTree as ET
import requests
from curl_cffi import requests as curl_requests
from datetime import datetime, timezone
import dateutil.parser

import threading
_thread_local = threading.local()

def get_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = curl_requests.Session(
            impersonate="chrome120",
            doh_url="https://cloudflare-dns.com/dns-query"
        )
    return _thread_local.session

from truth_mirror.models import EvidenceItem
from truth_mirror.caching import EvidenceCache
import os
import logging
import trafilatura
import concurrent.futures
from truth_mirror.retrieval import RetrievalConfig
from truth_mirror.rate_limiter import gdelt_limiter
from truth_mirror.extraction_config import (
    ALWAYS_BLOCKED_DOMAINS,
    EXTRACTION_TIMEOUT,
    MAX_WAYBACK_CONCURRENT,
    WAYBACK_MIN_INTERVAL,
)

import os
import logging
import time
import random
import io
import PyPDF2
from requests.exceptions import Timeout, ConnectionError
from curl_cffi.requests.errors import RequestsError

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

EXTRACTION_CACHE = {}

_wayback_lock = threading.Lock()
_wayback_last_request = 0.0
_wayback_semaphore = threading.Semaphore(MAX_WAYBACK_CONCURRENT)
_WAYBACK_MIN_INTERVAL = 2.0  # seconds between Wayback requests

def _wayback_rate_limit():
    """Enforce minimum interval between Wayback Machine requests."""
    global _wayback_last_request
    wait = 0.0
    with _wayback_lock:
        now = time.time()
        wait = _WAYBACK_MIN_INTERVAL - (now - _wayback_last_request)
        if wait > 0:
            _wayback_last_request = now + wait
        else:
            wait = 0.0
            _wayback_last_request = now
            
    if wait > 0:
        time.sleep(wait)

logger = logging.getLogger(__name__)

def _build_browser_headers() -> dict:
    """Build headers that closely mimic a real Chrome browser request."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

def _is_blocked_domain(url: str) -> bool:
    """Return True if the URL's domain is in the always-blocked list.
    
    Matches both exact domains and subdomains (e.g. blogs.nytimes.com).
    """
    try:
        hostname = urllib.parse.urlparse(url).hostname or ""
        domain = hostname.removeprefix("www.")
        return (
            domain in ALWAYS_BLOCKED_DOMAINS
            or any(domain.endswith(f".{blocked}") for blocked in ALWAYS_BLOCKED_DOMAINS)
        )
    except Exception:
        return False

def _parse_content(content: bytes, content_type: str, url: str) -> str:
    if "application/pdf" in content_type:
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        pdf_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pdf_text.append(page_text)
        return "\n".join(pdf_text)
    else:
        from truth_mirror.utils import clean_html_payload
        
        if len(content) > 5 * 1024 * 1024:
            logger.warning(f"Document too large for trafilatura ({len(content)} bytes), skipping extraction.")
            return ""
            
        content = clean_html_payload(content)
        extracted = trafilatura.extract(content)
        if not extracted or len(extracted.strip()) <= 50:
            import newspaper
            article = newspaper.Article(url)
            article.set_html(content)
            article.parse()
            if article.text and len(article.text.strip()) > 50:
                extracted = article.text
        return extracted or ""

def _fetch_via_google_translate(url: str) -> str:
    """Fetch article content via Google Translate proxy with TLS spoofing.
    
    Uses curl_cffi instead of plain requests to bypass Google's bot detection.
    Falls back to Google Web Cache if Google Translate fails.
    """
    # Attempt 1: Google Translate with TLS spoofing
    try:
        gt_url = f"https://translate.google.com/translate?sl=auto&tl=en&u={urllib.parse.quote(url, safe='')}"
        headers = _build_browser_headers()
        resp = get_session().get(gt_url, headers=headers, timeout=20, impersonate="chrome120")
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, gt_url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] Google Translate proxy successfully extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.debug(f"[extract_article_text] Google Translate attempt failed for {url}: {e}")
    
    # Attempt 2: Google Web Cache
    try:
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{urllib.parse.quote(url, safe='')}"
        headers = _build_browser_headers()
        resp = get_session().get(cache_url, headers=headers, timeout=20, impersonate="chrome120")
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, cache_url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] Google Cache successfully extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] Google Translate proxy failed for {url}: {e}")
    
    return ""

def _fetch_via_amp_cache(url: str) -> str:
    """Fetch article content via Google AMP Cache.
    
    Google AMP Cache stores cached versions of web pages.
    URL format: https://cdn.ampproject.org/c/s/<domain>/<path>
    Falls back to trying the page's /amp version directly.
    """
    # Attempt 1: Google AMP Cache
    try:
        parsed = urllib.parse.urlparse(url)
        query_part = f"?{parsed.query}" if parsed.query else ""
        amp_url = f"https://cdn.ampproject.org/c/s/{parsed.netloc}{parsed.path}{query_part}"
        headers = _build_browser_headers()
        resp = get_session().get(amp_url, headers=headers, timeout=20, impersonate="chrome120")
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, amp_url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] AMP Cache successfully extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.debug(f"[extract_article_text] AMP Cache attempt failed for {url}: {e}")
    
    # Attempt 2: Direct /amp version of the URL
    try:
        parsed = urllib.parse.urlparse(url)
        new_path = parsed.path.rstrip("/") + "/amp"
        amp_direct_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))
        headers = _build_browser_headers()
        resp = get_session().get(amp_direct_url, headers=headers, timeout=15, impersonate="chrome120")
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, amp_direct_url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] AMP direct successfully extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] AMP Cache fallback failed for {url}: {e}")
    
    return ""

def _fetch_via_scraperapi(url: str) -> str:
    """Fetch article text via ScraperAPI free tier (1,000 req/month).
    
    Requires SCRAPERAPI_KEY in environment. Returns '' if key is absent or call fails.
    Docs: https://www.scraperapi.com/documentation/
    """
    api_key = os.getenv("SCRAPERAPI_KEY", "").strip()
    if not api_key:
        logger.debug("[extract_article_text] SCRAPERAPI_KEY not set — skipping ScraperAPI.")
        return ""
    try:
        session = get_session()
        resp = session.get(
            "https://api.scraperapi.com/",
            params={"api_key": api_key, "url": url, "render": "false"},
            timeout=EXTRACTION_TIMEOUT,
            impersonate="chrome120",
        )
        if not resp.ok:
            logger.warning(f"[extract_article_text] ScraperAPI returned {resp.status_code} for {url}: {resp.text[:200]}")
            return ""
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] ScraperAPI extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] ScraperAPI fallback failed for {url}: {e}")
    return ""

def _fetch_via_zenrows(url: str) -> str:
    """Fetch article text via ZenRows free tier (1,000 req/month).
    
    Requires ZENROWS_API_KEY in environment. Returns '' if key is absent or call fails.
    Docs: https://www.zenrows.com/documentation
    """
    api_key = os.getenv("ZENROWS_API_KEY", "").strip()
    if not api_key:
        logger.debug("[extract_article_text] ZENROWS_API_KEY not set — skipping ZenRows.")
        return ""
    try:
        session = get_session()
        params = {"apikey": api_key, "url": url, "js_render": "false", "antibot": "true"}
        resp = session.get(
            "https://api.zenrows.com/v1/",
            params=params,
            timeout=EXTRACTION_TIMEOUT,
            impersonate="chrome120",
        )
        # If ZenRows returns 400 (e.g. REQS002 requiring js_render/premium_proxy for Reuters/Bloomberg/Cloudflare)
        if resp.status_code == 400 and ("js_render" in resp.text or "premium_proxy" in resp.text or "REQS" in resp.text):
            logger.info(f"[extract_article_text] ZenRows retrying with js_render & premium_proxy for {url}")
            params["js_render"] = "true"
            params["premium_proxy"] = "true"
            resp = session.get(
                "https://api.zenrows.com/v1/",
                params=params,
                timeout=30,
                impersonate="chrome120",
            )
        if not resp.ok:
            logger.warning(f"[extract_article_text] ZenRows returned {resp.status_code} for {url}: {resp.text[:200]}")
            return ""
        content_type = resp.headers.get("Content-Type", "").lower()
        extracted = _parse_content(resp.content, content_type, url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] ZenRows extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] ZenRows fallback failed for {url}: {e}")
    return ""

def _fetch_via_commoncrawl(url: str) -> str:
    """Fetch article text from CommonCrawl archive (free, no rate limits).
    
    Queries the CC Index CDX API to find the most recent crawl record,
    then fetches the raw WARC byte range from S3.
    Content may be up to ~1 month old.
    Docs: https://index.commoncrawl.org/
    """
    try:
        session = get_session()
        # Step 1: Query the CC Index to find the most recent crawl record
        cdx_url = (
            f"https://index.commoncrawl.org/CC-MAIN-2026-06-index?"
            f"url={urllib.parse.quote(url, safe='')}&output=json&limit=1&filter=status:200"
        )
        cdx_resp = session.get(cdx_url, timeout=15, impersonate="chrome120")
        cdx_resp.raise_for_status()
        lines = [ln.strip() for ln in cdx_resp.text.strip().splitlines() if ln.strip()]
        if not lines:
            logger.debug(f"[extract_article_text] CommonCrawl: no record found for {url}")
            return ""

        record = json.loads(lines[0])
        filename = record.get("filename", "")
        offset = int(record.get("offset", 0))
        length = int(record.get("length", 0))
        if not filename or not length:
            return ""

        # Step 2: Fetch the specific WARC byte range from S3
        s3_url = f"https://data.commoncrawl.org/{filename}"
        byte_range = f"bytes={offset}-{offset + length - 1}"
        warc_resp = session.get(
            s3_url,
            headers={"Range": byte_range},
            timeout=EXTRACTION_TIMEOUT,
            impersonate="chrome120",
        )
        warc_resp.raise_for_status()
        content_type = warc_resp.headers.get("Content-Type", "text/html").lower()
        extracted = _parse_content(warc_resp.content, content_type, url)
        if extracted and len(extracted.strip()) > 50:
            logger.info(f"[extract_article_text] CommonCrawl extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] CommonCrawl fallback failed for {url}: {e}")
    return ""

_selenium_driver_lock = threading.Lock()

def _get_selenium_driver():
    """Create a headless Chrome WebDriver. Caller is responsible for driver.quit()."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

def _fetch_via_selenium(url: str) -> str:
    """Fetch article text using a headless Selenium Chrome browser.
    
    Nuclear last resort — ~15-30s per URL. Renders JS, bypasses most WAF bot detection.
    Only use after all faster fallbacks have failed.
    """
    driver = None
    try:
        driver = _get_selenium_driver()
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(3)
        title = (driver.title or "").lower()
        if any(err in title for err in ["privacy error", "certificate error", "site can't be reached", "access denied", "403 forbidden", "404 not found"]):
            return ""
        html = driver.page_source
        if not html or "Your connection is not private" in html:
            return ""
        html_bytes = html.encode("utf-8", errors="replace")
        extracted = _parse_content(html_bytes, "text/html", url)
        if extracted and len(extracted.strip()) > 50:
            if "Your connection is not private" in extracted or "Attackers might be trying to steal" in extracted:
                return ""
            logger.info(f"[extract_article_text] Selenium extracted {len(extracted)} chars for {url}")
            return extracted.strip()
    except Exception as e:
        logger.warning(f"[extract_article_text] Selenium fallback failed for {url}: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    return ""

def _fetch_rss_articles_for_url(url: str) -> str:
    """Find alternative coverage of the same story via Google News RSS.
    
    When a specific article URL is blocked, searches Google News for articles
    from the same domain about the same topic and attempts to extract one of them.
    Returns the first successfully-extracted article body (may not be the exact article).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        domain = (parsed.hostname or "").removeprefix("www.")
        path_parts = [p for p in parsed.path.split("/") if len(p) > 4 and not p.isdigit()]
        keywords = " ".join(path_parts[-3:])
        if not keywords:
            return ""

        query = f"site:{domain} {keywords}"
        rss_url = (
            f"https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}&hl=en&gl=US&ceid=US:en"
        )
        resp = get_session().get(rss_url, headers=_build_browser_headers(), timeout=10, impersonate="chrome120")
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for node in root.findall("./channel/item")[:3]:
            link = (node.findtext("link") or "").strip()
            if not link:
                continue
            try:
                from truth_mirror.utils import decode_google_news_url_fast
                decoded = decode_google_news_url_fast(link)
                if decoded and decoded.get("status"):
                    link = decoded.get("decoded_url", link)
            except Exception:
                pass

            try:
                alt_resp = get_session().get(
                    link, headers=_build_browser_headers(), timeout=15, impersonate="chrome120"
                )
                alt_resp.raise_for_status()
                content_type = alt_resp.headers.get("Content-Type", "").lower()
                extracted = _parse_content(alt_resp.content, content_type, link)
                if extracted and len(extracted.strip()) > 50:
                    logger.info(
                        f"[extract_article_text] RSS discovery found alternative for {url} at {link}"
                    )
                    return extracted.strip()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[extract_article_text] RSS discovery failed for {url}: {e}")
    return ""

def _fetch_via_rss_discovery(url: str) -> str:
    """Wrapper for _fetch_rss_articles_for_url (thin layer for testability)."""
    return _fetch_rss_articles_for_url(url)

def _fetch_via_wayback(url: str) -> str:
    """Fetch article content from Wayback Machine with rate limiting and CDX API."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            _wayback_rate_limit()
            headers = _build_browser_headers()
            
            # Use CDX API for more reliable snapshot lookup
            cdx_url = (
                f"https://web.archive.org/cdx/search/cdx?"
                f"url={urllib.parse.quote(url, safe='')}"
                f"&output=json&limit=1&fl=timestamp,original"
                f"&filter=statuscode:200&sort=reverse"
            )
            cdx_resp = get_session().get(cdx_url, headers=headers, timeout=15, impersonate="chrome120")
            cdx_resp.raise_for_status()
            
            cdx_data = cdx_resp.json()
            if len(cdx_data) < 2:  # First row is header
                logger.debug(f"[extract_article_text] No Wayback snapshot found for {url}")
                return ""
            
            timestamp = cdx_data[1][0]
            original_url = cdx_data[1][1]
            # id_ suffix tells Wayback to return original content without toolbar
            snapshot_url = f"https://web.archive.org/web/{timestamp}id_/{original_url}"
            
            _wayback_rate_limit()
            snapshot_resp = get_session().get(snapshot_url, headers=headers, timeout=20, impersonate="chrome120")
            snapshot_resp.raise_for_status()
            
            content_type = snapshot_resp.headers.get("Content-Type", "").lower()
            extracted = _parse_content(snapshot_resp.content, content_type, snapshot_url)
            if extracted and len(extracted.strip()) > 50:
                logger.info(f"[extract_article_text] Wayback Machine successfully extracted {len(extracted)} chars for {url}")
                return extracted.strip()
            return ""
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                wait = (2 ** (attempt + 1)) + random.uniform(0.5, 2.0)
                logger.warning(f"[extract_article_text] Wayback rate limited (attempt {attempt+1}/{max_retries}), waiting {wait:.1f}s")
                time.sleep(wait)
                continue
            logger.warning(f"[extract_article_text] Wayback fallback failed for {url}: {e}")
            return ""
    return ""

def extract_article_text(url: str) -> str:
    """Robust 9-step fallback chain for extracting article text.

    Fallback order (cheapest/fastest first):
      1. Cache hit (instant)
      2. Direct fetch via curl_cffi — SKIPPED for always-blocked domains
      3. Google Translate proxy
      4. Google AMP Cache
      5. ScraperAPI (free tier — requires SCRAPERAPI_KEY)
      6. ZenRows (free tier — requires ZENROWS_API_KEY)
      7. CommonCrawl archive (free, no rate limits, ~1 month old content)
      8. Wayback Machine (rate-limited via global semaphore, max 2 concurrent)
      9. RSS Discovery (finds alternative coverage of the same story)
     10. Selenium headless browser (last resort — slow but highly effective)

    On total failure, returns '' silently. Never raises.
    """
    if url in EXTRACTION_CACHE:
        return EXTRACTION_CACHE[url]

    text: str = ""

    # --- Step 1: Direct fetch (skipped for always-blocked domains) ---
    if not _is_blocked_domain(url):
        for fetch_attempt in range(2):
            try:
                headers = _build_browser_headers()
                if fetch_attempt > 0:
                    current_ua = headers.get("User-Agent", "")
                    try:
                        current_idx = USER_AGENTS.index(current_ua)
                    except ValueError:
                        current_idx = 0
                    headers["User-Agent"] = USER_AGENTS[(current_idx + 1) % len(USER_AGENTS)]
                    time.sleep(random.uniform(1.0, 3.0))

                resp = get_session().get(url, headers=headers, timeout=15, impersonate="chrome120")
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "").lower()
                extracted = _parse_content(resp.content, content_type, url)
                if extracted and len(extracted.strip()) > 50:
                    text = extracted.strip()
                    logger.info(f"[extract_article_text] Direct fetch: {len(text)} chars from {url}")
                    break
            except Exception as e:
                error_msg = str(e)
                if fetch_attempt == 0 and ("403" in error_msg or "401" in error_msg):
                    logger.debug(f"[extract_article_text] Direct fetch got {error_msg}, retrying...")
                    continue
                logger.warning(f"[extract_article_text] Direct fetch failed for {url}: {error_msg}")
                if "curl: (6)" in error_msg or "Could not resolve host" in error_msg:
                    try:
                        import socket
                        hostname = urllib.parse.urlparse(url).hostname
                        if hostname:
                            ip = socket.gethostbyname(hostname)
                            logger.error(f"[DNS_PROBE] curl_cffi failed, native socket RESOLVED {hostname} to {ip}")
                    except Exception as se:
                        logger.error(f"[DNS_PROBE] Both curl_cffi and native socket FAILED: {se}")
                break

    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 2: Google Translate proxy ---
    logger.warning(f"[extract_article_text] Trying Google Translate proxy for {url}")
    text = _fetch_via_google_translate(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 3: Google AMP Cache ---
    logger.warning(f"[extract_article_text] Trying AMP Cache for {url}")
    text = _fetch_via_amp_cache(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 4: ScraperAPI ---
    logger.warning(f"[extract_article_text] Trying ScraperAPI for {url}")
    text = _fetch_via_scraperapi(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 5: ZenRows ---
    logger.warning(f"[extract_article_text] Trying ZenRows for {url}")
    text = _fetch_via_zenrows(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 6: CommonCrawl ---
    logger.warning(f"[extract_article_text] Trying CommonCrawl for {url}")
    text = _fetch_via_commoncrawl(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 7: Wayback Machine (global semaphore: max 2 concurrent) ---
    logger.warning(f"[extract_article_text] Trying Wayback Machine for {url}")
    with _wayback_semaphore:
        text = _fetch_via_wayback(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 8: RSS Discovery ---
    logger.warning(f"[extract_article_text] Trying RSS discovery for {url}")
    text = _fetch_via_rss_discovery(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    # --- Step 9: Selenium (nuclear last resort) ---
    logger.warning(f"[extract_article_text] Trying Selenium headless browser for {url}")
    text = _fetch_via_selenium(url)
    if text:
        EXTRACTION_CACHE[url] = text
        return text

    logger.error(f"[extract_article_text] ALL FALLBACKS EXHAUSTED for {url} — returning empty string")
    return ""

RSS_FEEDS_PATH = os.path.join(os.path.dirname(__file__), "rss_feeds.json")
try:
    with open(RSS_FEEDS_PATH, "r", encoding="utf-8") as _f:
        RSS_FEEDS = json.load(_f)
except Exception as e:
    logger.warning(f"Could not load RSS feeds from {RSS_FEEDS_PATH}: {e}")
    RSS_FEEDS = []

GDELT_ACRONYM_MAP = {
    "us": "United States",
    "uk": "United Kingdom",
    "eu": "European Union",
    "un": "United Nations",
    "ap": "Associated Press",
    "ai": "Artificial Intelligence",
}

def sanitize_gdelt_query(query: str) -> str:
    """Sanitize and normalize query strings specifically for the GDELT DOC API.
    
    - Expands key geopolitical and common acronyms (e.g. 'us' -> 'United States').
    - Strips URLs and special punctuation/colons/quotes that break GDELT syntax.
    - Filters out short noise tokens (< 3 chars) that are not recognized acronyms.
    - Safely truncates queries longer than 250 characters.
    - Returns an empty string '' if input is empty or has < 3 characters after cleaning.
    """
    if not query or not isinstance(query, str):
        return ""
        
    # Strip URLs
    text = re.sub(r'https?://\S+', ' ', query)
    
    # Strip punctuation / non-alphanumeric characters (replace with space)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    tokens = text.split()
    if not tokens:
        return ""
        
    processed_tokens: list[str] = []
    for token in tokens:
        token_lower = token.lower()
        if token_lower in GDELT_ACRONYM_MAP:
            processed_tokens.append(GDELT_ACRONYM_MAP[token_lower])
        elif len(token) >= 3:
            processed_tokens.append(token)
            
    if not processed_tokens:
        return ""
        
    sanitized = " ".join(processed_tokens).strip()
    
    if len(sanitized) > 250:
        truncated = sanitized[:250]
        if " " in truncated:
            sanitized = truncated.rsplit(" ", 1)[0].strip()
        else:
            sanitized = truncated.strip()
            
    if len(sanitized) < 3:
        return ""
        
    return sanitized

class GDELTConnector:
    """Connects to the GDELT DOC 2.0 API to find global news coverage."""

    def __init__(self, config: RetrievalConfig | None = None):
        self.cache = getattr(config, 'cache', None) if config else None
        self.max_results = config.max_results if config else 5
        self.timeout_seconds = 7

    def retrieve(self, query: str) -> list[EvidenceItem]:
        clean_query = sanitize_gdelt_query(query)
        if not clean_query:
            logger.warning(f"[GDELTConnector] Query '{query}' became empty after sanitization. Skipping.")
            return []

        cache_key = f"gdelt:{clean_query.lower()}"

        base_api_url = (
            "http://api.gdeltproject.org/api/v2/doc/doc?"
            + urllib.parse.urlencode({
                "query": clean_query,
                "mode": "artlist",
                "maxrecords": self.max_results,
                "format": "json"
            })
        )

        payload = {}
        for attempt in range(2):
            if attempt > 0:
                time.sleep(2 ** attempt)
            api_url = base_api_url
            try:
                if attempt == 0:
                    logger.info(f"[GDELTConnector] Querying: {query}")
                gdelt_limiter.wait()
                time.sleep(random.uniform(0.1, 0.5))
                # Do not use proxy for GDELT initially. Rely on TLS spoofing.
                response = get_session().get(api_url, headers={"User-Agent": "TruthMirror/1.0"}, timeout=self.timeout_seconds, impersonate="chrome120")
                if response.status_code == 429:
                    logger.warning(f"[GDELTConnector] Rate limited (429) for '{query}'. Retrying...")
                    continue
                if response.status_code == 403:
                    logger.warning(f"[GDELTConnector] 403 IP Ban detected for '{query}'. Retrying...")
                    continue
                response.raise_for_status()
                
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/json" not in content_type:
                    raw_text = response.text[:200].lower() if hasattr(response, "text") and response.text else ""
                    logger.warning(f"[GDELTConnector] Non-JSON response received (Content-Type: '{content_type}'). Body: {raw_text}")
                    return []

                try:
                    payload = response.json()
                except Exception as json_e:
                    logger.warning(f"[GDELTConnector] JSON Parse Error. Raw body snippet: {response.text[:200]}")
                    return []
                
                break
            except (Timeout, ConnectionError, RequestsError) as e:
                logger.warning(f"[GDELTConnector] Network error on attempt {attempt+1} for '{query}': {e}")
                if 'reset' in str(e).lower():
                    logger.warning(f"[GDELTConnector] Connection Reset detected for '{query}'. Retrying...")
                if attempt == 1:
                    return []
            except Exception as e:
                logger.warning(f"[GDELTConnector] Failed attempt {attempt+1} for query '{query}': {e}")
                if attempt == 1:
                    return []

        raw_items = []
        for article in payload.get("articles", []):
            url = article.get("url", "")
            if not url:
                continue
            title = article.get("title", "")
            domain = article.get("domain", "unknown")
            date_str = str(article.get("seendate", ""))
            try:
                dt = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                formatted_date = dt.date().isoformat()
            except ValueError:
                formatted_date = datetime.now(timezone.utc).date().isoformat()
            raw_items.append((title, url, domain, formatted_date, article.get("language", "en")))

        def fetch_text(item_data):
            title, url, domain, formatted_date, language = item_data
            excerpt = title  # fallback

            try:
                extracted_text = extract_article_text(url)
                if extracted_text:
                    excerpt = extracted_text[:1000]
            except Exception as exc:
                logger.warning(f"[GDELTConnector] fetch_text exception for {url}: {exc}")

            return EvidenceItem(
                source_title=title,
                source_type="journalism",
                publisher=domain,
                date=formatted_date,
                url_or_id=url,
                excerpt=excerpt,
                language=language,
                independence_key=f"news:{domain}",
            )

        items: list[EvidenceItem] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(raw_items) or 1, 2)) as executor:
            futures = [executor.submit(fetch_text, item) for item in raw_items]
            for future in futures:
                try:
                    items.append(future.result(timeout=30))
                except Exception as exc:
                    logger.warning(f"[GDELTConnector] Fetch generated an exception: {exc}")

        logger.info(f"[GDELTConnector] Retrieved {len(items)} items for: {query}")
        return items




class BaseConnector:
    """Base interface for all connectors."""
    pass

class GoogleNewsRSSConnector(BaseConnector):
    """Fetches real-time news from Google News RSS feed."""
    def __init__(self, config: RetrievalConfig | None = None):
        self.cache = getattr(config, 'cache', None) if config else None
        self.max_results = config.max_results if config else 8
        self.timeout_seconds = 10

    def search(self, query: str) -> list[EvidenceItem]:
        return self.retrieve(query)

    def retrieve(self, query: str) -> list[EvidenceItem]:
        import urllib.request
        from truth_mirror.rate_limiter import google_news_limiter
        
        google_news_limiter.wait()

        api_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}"
        try:
            logger.info(f"[GoogleNewsRSSConnector] Querying: {query}")
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            # Bypass proxy for Google News, rely on curl_cffi TLS spoofing from our server IP
            response = get_session().get(api_url, headers=headers, timeout=self.timeout_seconds, impersonate="chrome120")
            response.raise_for_status()
            xml_bytes = response.content
        except Exception as e:
            logger.warning(f"[GoogleNewsRSSConnector] get_session() failed for query '{query}': {e}. Falling back to standard requests.")
            try:
                response = requests.get(api_url, headers=headers, timeout=self.timeout_seconds)
                response.raise_for_status()
                xml_bytes = response.content
            except Exception as fallback_e:
                logger.warning(f"[GoogleNewsRSSConnector] Fallback requests.get failed for query '{query}': {fallback_e}")
                return []

        try:
            root = ET.fromstring(xml_bytes)
        except Exception as parse_e:
            logger.warning(f"[GoogleNewsRSSConnector] XML parsing failed for query '{query}': {parse_e}")
            return []

        items: list[EvidenceItem] = []
        raw_items = []
        for node in root.findall("./channel/item")[:self.max_results]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            pub_date = (node.findtext("pubDate") or datetime.now(timezone.utc).date().isoformat()).strip()
            try:
                pub_date = dateutil.parser.parse(pub_date).date().isoformat()
            except Exception:
                pass
            
            if not title or not link:
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
                logger.warning(f"[GoogleNewsRSSConnector] Failed to decode URL {link}: {e}")

            extracted_text = extract_article_text(link)
            if extracted_text:
                excerpt = extracted_text[:1000]

            return EvidenceItem(
                source_title=title,
                source_type="journalism",
                publisher="Google News",
                date=pub_date,
                url_or_id=link,
                excerpt=excerpt,
                language="en",
                independence_key=f"news:{urllib.parse.urlparse(link).netloc.replace('www.', '')}",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(raw_items) or 1, 2)) as executor:
            futures = [executor.submit(fetch_text, item) for item in raw_items]
            for future in futures:
                try:
                    items.append(future.result(timeout=30))
                except Exception as exc:
                    logger.warning(f"[GoogleNewsRSSConnector] Fetch generated an exception: {exc}")
            
        logger.info(f"[GoogleNewsRSSConnector] Retrieved {len(items)} items for: {query}")
        return items



class NewsDataIOConnector(BaseConnector):
    """Fetches global news from NewsData.io API for non-Western / global coverage."""
    def __init__(self, config: RetrievalConfig | None = None):
        self.cache = getattr(config, 'cache', None) if config else None
        self.max_results = config.max_results if config else 5
        self.timeout_seconds = 10
        self.api_key = os.getenv("NEWSDATA_API_KEY")

    def search(self, query: str) -> list[EvidenceItem]:
        return self.retrieve(query)

    def retrieve(self, query: str) -> list[EvidenceItem]:
        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("[NewsDataIOConnector] API key not found. Skipping.")
            return []
            
        api_url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": self.api_key,
            "q": query,
            "language": "en",
        }
        
        try:
            logger.info(f"[NewsDataIOConnector] Querying: {query}")
            response = get_session().get(api_url, params=params, headers={"User-Agent": "TruthMirror/1.0"}, timeout=self.timeout_seconds, impersonate="chrome120")
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            logger.warning(f"[NewsDataIOConnector] Failed for query '{query}': {e}")
            return []
            
        items = []
        for result in payload.get("results", [])[:self.max_results]:
            url = result.get("link", "")
            title = result.get("title", "")
            body = result.get("content", result.get("description", ""))
            pub_date = result.get("pubDate", datetime.now(timezone.utc).isoformat())
            try:
                pub_date = dateutil.parser.parse(pub_date).date().isoformat()
            except:
                pass
            publisher = result.get("source_id", "NewsData Source")
                
            items.append(EvidenceItem(
                source_title=title,
                source_type="journalism",
                publisher=publisher,
                date=pub_date,
                url_or_id=url,
                excerpt=body[:1000] if body else title,
                language="en",
                independence_key=f"news:{publisher.lower()}"
            ))
            
        logger.info(f"[NewsDataIOConnector] Retrieved {len(items)} items for: {query}")
        return items

