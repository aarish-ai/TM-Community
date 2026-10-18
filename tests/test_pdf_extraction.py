import io
import pytest
import requests
import truth_mirror.retrieval_news
import PyPDF2

def test_pdf_extraction_graceful_handling(monkeypatch):
    class MockResponse:
        content = b"%PDF-1.4\n\x00\x01\x02\x03\x04" # Raw binary invalid PDF content
        headers = {"Content-Type": "application/pdf"}
        text = ""
        def raise_for_status(self): pass

    class MockSession:
        def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(truth_mirror.retrieval_news, "get_session", lambda: MockSession())
    
    # Disable fallbacks by mocking requests.get to raise an exception
    def mock_requests_get(*args, **kwargs):
        raise Exception("Should not fallback for PDFs")
    monkeypatch.setattr(requests, "get", mock_requests_get)

    result = truth_mirror.retrieval_news.extract_article_text("http://fake.com/test.pdf")
    # Verify that extract_article_text safely handles PyPDF2 exceptions without crashing
    # the application when given invalid PDF bytes, falling back to return an empty string.
    assert result == ""
