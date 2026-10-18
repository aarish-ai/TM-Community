import time
import re
import trafilatura

def test_preprocessing():
    file_path = "scripts/eval/sample_large.html"
    with open(file_path, "rb") as f:
        content = f.read()
    
    orig_size_mb = len(content) / (1024 * 1024)
    print(f"Original HTML size: {orig_size_mb:.2f} MB")
    
    start_clean = time.time()
    
    # Decode to string for regex
    html_str = content.decode("utf-8", errors="ignore")
    
    # Strip script and style tags completely
    html_str = re.sub(r'<script.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    html_str = re.sub(r'<style.*?</style>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    
    # Re-encode
    cleaned_content = html_str.encode("utf-8")
    clean_duration = time.time() - start_clean
    
    clean_size_mb = len(cleaned_content) / (1024 * 1024)
    print(f"Cleaned HTML size: {clean_size_mb:.2f} MB")
    print(f"Cleaning time: {clean_duration:.4f} seconds")
    
    start_extract = time.time()
    text = trafilatura.extract(cleaned_content)
    extract_duration = time.time() - start_extract
    
    text_len = len(text) if text else 0
    print(f"Extracted text length: {text_len} chars")
    print(f"Extraction time: {extract_duration:.4f} seconds")
    print(f"Total time (clean + extract): {clean_duration + extract_duration:.4f} seconds")

if __name__ == "__main__":
    test_preprocessing()
