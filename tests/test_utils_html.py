# tests/test_utils_html.py
from truth_mirror.utils import clean_html_payload

def test_clean_html_payload_strips_scripts_and_styles():
    raw_html = b"""
    <html>
      <head>
        <script>alert('spam');</script>
        <style>body { color: red; }</style>
      </head>
      <body>
        <h1>Hello World</h1>
      </body>
    </html>
    """
    cleaned = clean_html_payload(raw_html)
    cleaned_str = cleaned.decode("utf-8")
    
    assert "alert('spam')" not in cleaned_str
    assert "color: red" not in cleaned_str
    assert "Hello World" in cleaned_str


def test_utils_imports_with_selectolax_v1_deprecation(monkeypatch):
    import sys
    import importlib

    # Simulate selectolax 1.0 where importing selectolax.parser raises the deprecation ImportError
    class BrokenParserModule:
        def __getattr__(self, name):
            raise ImportError(
                "Modest backend is deprecated since selectolax 1.0. It's outdated, not maintained, contains bugs and does not follow modern HTML5 standards. Please use lexbor backend instead: `from selectolax.lexbor import LexborHTMLParser`."
            )

    monkeypatch.setitem(sys.modules, "selectolax.parser", BrokenParserModule())
    if "truth_mirror.utils" in sys.modules:
        monkeypatch.delitem(sys.modules, "truth_mirror.utils")

    import truth_mirror.utils

    assert hasattr(truth_mirror.utils, "HTMLParser")
    cleaned = truth_mirror.utils.clean_html_payload(b"<div><script>remove_me</script><p>keep_me</p></div>")
    assert b"remove_me" not in cleaned
    assert b"keep_me" in cleaned

