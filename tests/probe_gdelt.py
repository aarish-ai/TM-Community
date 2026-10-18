import time
import os
import sys

# Ensure truth_mirror package is importable when script is run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from truth_mirror.retrieval_news import get_session

def run_probe():
    print(f"\n=== Running Probe ===")
    session = get_session()
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc?query=test&mode=artlist&maxrecords=5&format=json"
    target_url = base_url

    for i in range(1, 11):
        print(f"Attempt {i}...")
        try:
            resp = session.get(target_url, headers={"User-Agent": "TruthMirror/1.0"}, timeout=15, impersonate="chrome120")
            content_type = resp.headers.get("Content-Type", "MISSING")
            print(f"  Status: {resp.status_code}")
            print(f"  Content-Type: {content_type}")
            
            if "application/json" not in content_type.lower():
                print(f"  [!] NON-JSON BODY DETECTED:")
                print(f"  {resp.text[:300]}")
            else:
                print("  [OK] JSON received successfully.")
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {str(e)}")
        time.sleep(0.5) # Hammer it fast to trigger limits

if __name__ == "__main__":
    run_probe()

