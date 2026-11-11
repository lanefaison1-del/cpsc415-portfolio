"""A browser-driven check of the voice page, the Week 5 way. Start server.py first: it holds the key,
and the browser must never see it.

    cd voice && ../.venv/bin/python server.py &               # with OPENROUTER_API_KEY set
    ../.venv/bin/python -m pytest test_browser.py -v           # three billed calls on the server

It uploads my clip 1 through the page's file picker (a microphone cannot be scripted reliably),
waits for the spoken answer, then checks what the browser was allowed to see. The last three
assertions are the point. Set URL to run it against another address, such as the deployed site.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("URL", "http://localhost:8000")
CLIP = Path(__file__).parent / "clips" / "lane-01.wav"     # "What did Lane Faison's capstone team build ..."


def test_voice_page_answers_and_the_key_never_reaches_the_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not os.environ.get("HEADED"))
        page = browser.new_page()
        requests = []
        page.on("request", lambda r: requests.append((r.url, r.headers.get("authorization"))))
        page.goto(URL)
        assert "sk-or" not in page.content()
        page.set_input_files("#file", str(CLIP))
        page.click("#send")
        page.wait_for_function("document.querySelector('#out').textContent.includes('[cost')", timeout=120_000)
        out = page.inner_text("#out")
        has_audio = page.evaluate("!!document.querySelector('#player').src")
        browser.close()
    assert "Answer:" in out, out
    heard, answer = out.split("Answer:", 1)
    assert "lane" in heard.lower(), out                               # the transcript kept my name
    assert len(answer.split("[cost")[0].strip()) > 20, out             # an answer came back
    assert "could not be spoken" not in out, out
    assert has_audio                                                   # audio came back to play
    assert all(auth is None for _, auth in requests)                   # no Authorization header left the browser
    assert all("openrouter" not in url for url, _ in requests)         # the browser never called the provider
    assert any(url.endswith("/api/voice") for url, _ in requests)      # it called my server
