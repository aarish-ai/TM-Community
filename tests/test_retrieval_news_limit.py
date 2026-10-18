from truth_mirror.retrieval_news import _parse_content

def test_parse_content_handles_4mb_file():
    # Simulate a 4MB payload, which used to be aggressively skipped by the 1MB limit
    large_padding = b"<!-- " + b"X" * (4 * 1024 * 1024) + b" -->"
    raw_html = b"<html><body><p>Actual Article Text</p>" + large_padding + b"</body></html>"
    
    result = _parse_content(raw_html, "text/html", "http://example.com")
    
    assert "Actual Article Text" in result
