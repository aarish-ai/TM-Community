# scripts/reproduce_dns_error.py
import concurrent.futures
import time
import logging
from truth_mirror.retrieval_news import extract_article_text

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

URLS = [
    "https://www.aljazeera.com/",
    "https://www.dw.com/",
    "https://www.thehindu.com/",
    "https://www.bbc.com/",
    "https://www.reuters.com/",
] * 10  # 50 concurrent requests to simulate heavy load

def fetch_url(url):
    logger.info(f"Starting fetch for {url}")
    extract_article_text(url)

if __name__ == "__main__":
    logger.info(f"Starting load test with {len(URLS)} concurrent requests...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(fetch_url, URLS))
        
    duration = time.time() - start_time
    logger.info(f"Load test complete in {duration:.2f} seconds.")
    logger.info("Check the logs above for [DNS_PROBE] messages.")
    logger.info("If you see 'native socket RESOLVED', it's a thread-safety issue with SHARED_SESSION.")
    logger.info("If you see 'native socket FAILED', your local/datacenter DNS is dropping packets.")
