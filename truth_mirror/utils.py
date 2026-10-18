import re
import json
import requests
from urllib.parse import quote, urlparse
try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    from selectolax.parser import HTMLParser

def strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from JSON output."""
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback to brace matching if no fences
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# Fallback session if none provided
_DEFAULT_GOOGLE_NEWS_SESSION = None

def get_google_news_session():
    global _DEFAULT_GOOGLE_NEWS_SESSION
    if _DEFAULT_GOOGLE_NEWS_SESSION is None:
        _DEFAULT_GOOGLE_NEWS_SESSION = requests.Session()
        _DEFAULT_GOOGLE_NEWS_SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        })
    return _DEFAULT_GOOGLE_NEWS_SESSION

def decode_google_news_url_fast(source_url: str, session: requests.Session = None) -> dict:
    """
    Decodes a Google News article URL into its original source URL,
    using a persistent session to avoid TLS handshake CPU spikes.
    """
    if session is None:
        session = get_google_news_session()
        
    try:
        url = urlparse(source_url)
        path = url.path.split("/")
        if not (url.hostname in ("news.google.com", "news.url.google.com") and len(path) > 1 and path[-2] in ["articles", "read"]):
            return {"status": False, "message": "Invalid Google News URL format."}
            
        base64_str = path[-1]
        
        # 1. Get decoding params
        req_url = f"https://news.google.com/rss/articles/{base64_str}"
        response = session.get(req_url, timeout=10)
        response.raise_for_status()
        
        parser = HTMLParser(response.text)
        data_element = parser.css_first("c-wiz > div[jscontroller]")
        if data_element is None:
            return {"status": False, "message": "Failed to fetch data attributes."}
            
        signature = data_element.attributes.get("data-n-a-sg")
        timestamp = data_element.attributes.get("data-n-a-ts")
        
        # 2. Decode URL via batchexecute
        batch_url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        payload = [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{base64_str}",{timestamp},"{signature}"]',
        ]
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}
        
        batch_resp = session.post(batch_url, headers=headers, data=f"f.req={quote(json.dumps([[payload]]))}", timeout=10)
        batch_resp.raise_for_status()
        
        parsed_data = json.loads(batch_resp.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed_data[0][2])[1]
        
        return {"status": True, "decoded_url": decoded_url}
    except Exception as e:
        return {"status": False, "message": f"Error in decode_google_news_url_fast: {str(e)}"}

def parse_llm_json(text: str):
    """
    Robustly parse LLM JSON output, handling markdown fences, conversational filler, 
    and common syntax errors. Returns None if the input is empty or unparseable.
    """
    if not text or not text.strip():
        return None
        
    # Fast path: Try native json after stripping markdown
    clean_text = strip_markdown_json(text)
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        pass
        
    # Slow path: Use json_repair for structurally malformed JSON
    try:
        import json_repair
        return json_repair.loads(text)
    except Exception:
        return None

def clean_html_payload(content: bytes) -> bytes:
    """Strips <script>, <style>, <noscript>, and <svg> tags to reduce parsing overhead."""
    try:
        # We rely on selectolax for extremely fast tag removal
        tree = HTMLParser(content)
        for tag in tree.css("script, style, noscript, svg"):
            tag.decompose()
        return tree.html.encode("utf-8")
    except Exception:
        # Fallback to original content on severe parsing failure
        return content
