import os
from pathlib import Path

def test_requirements_encoding_and_content():
    req_path = Path("requirements.txt")
    assert req_path.exists(), "requirements.txt does not exist"
    
    raw_bytes = req_path.read_bytes()
    # Ensure no UTF-16 null bytes
    assert b"\x00" not in raw_bytes, "requirements.txt contains UTF-16 null bytes (\\x00)"
    
    # Ensure it decodes cleanly to utf-8
    text = raw_bytes.decode("utf-8")
    assert "gunicorn" in text, "gunicorn not found in requirements.txt"
    assert "gunicorn>=21.2.0" in text, "gunicorn version specifier missing"

def test_dockerfile_production_server():
    df_path = Path("Dockerfile")
    assert df_path.exists(), "Dockerfile does not exist"
    
    content = df_path.read_text(encoding="utf-8")
    expected_cmd = 'CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8080", "app:app"]'
    assert expected_cmd in content, f"Dockerfile CMD does not match expected production command: {expected_cmd}"
