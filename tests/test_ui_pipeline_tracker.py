import time
import threading
from http.server import ThreadingHTTPServer
from app import TruthMirrorHandler
from playwright.sync_api import sync_playwright

TEST_PORT = 8091

import app

def start_server():
    # Patch _check_session to always return True for the test
    app._check_session = lambda handler: True
    
    # Patch pipeline to not finish instantly so we can observe the "processing" state
    original_verify = app.GeopoliticalPipeline.verify
    def slow_verify(*args, **kwargs):
        time.sleep(5)
        return original_verify(*args, **kwargs)
    app.GeopoliticalPipeline.verify = slow_verify
    
    server = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), TruthMirrorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def test_pipeline_tracker_visibility():
    server = start_server()
    time.sleep(1) # Wait for server to start
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"http://localhost:{TEST_PORT}/")
            
            # Ensure we have a valid token to bypass auth redirects
            page.evaluate("sessionStorage.setItem('tm_token', 'test-token');")
            page.reload()
            
            # Enter claim and submit
            page.evaluate("document.getElementById('termsOverlay').style.display = 'none';")
            page.fill("input#claimInput", "This is a test claim.")
            page.click("button#verifyBtn", force=True)
            
            # Wait for the initial /api/verify request to finish (HTTP 202 is fast)
            page.wait_for_timeout(1500) 
            
            # Verify the pipeline tracker has not been hidden prematurely
            display_style = page.evaluate("document.getElementById('pipelineTracker').style.display")
            assert display_style != "none", "Pipeline tracker was hidden prematurely!"
            
            browser.close()
    finally:
        server.shutdown()
