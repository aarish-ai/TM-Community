import os
import requests

def fetch_large_article():
    url = "https://en.wikipedia.org/wiki/World_War_II"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    print(f"Fetching {url}...")
    
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    
    content = resp.content
    size_mb = len(content) / (1024 * 1024)
    print(f"Fetched size: {size_mb:.2f} MB")
    
    os.makedirs("scripts/eval", exist_ok=True)
    with open("scripts/eval/sample_large.html", "wb") as f:
        f.write(content)
        
    print("Saved to scripts/eval/sample_large.html")

if __name__ == "__main__":
    fetch_large_article()
