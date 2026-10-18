import time
import tracemalloc
import trafilatura

def profile_extraction():
    file_path = "scripts/eval/sample_large.html"
    with open(file_path, "rb") as f:
        content = f.read()
    
    print(f"Loaded HTML: {len(content) / (1024 * 1024):.2f} MB")
    
    tracemalloc.start()
    start_time = time.time()
    
    # Run extraction bypassing any 1MB limit
    text = trafilatura.extract(content)
    
    duration = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    text_len = len(text) if text else 0
    print(f"Extraction successful: {text is not None and text_len > 0}")
    print(f"Extracted text length: {text_len} chars")
    print(f"Time taken: {duration:.4f} seconds")
    print(f"Peak memory: {peak / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    profile_extraction()
