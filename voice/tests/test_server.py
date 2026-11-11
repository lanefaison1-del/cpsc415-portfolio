"""No-key tests for the voice server (spec behaviors 28 to 31 and 35 to 40). Every model call is a fake.

    .venv/bin/python -m pytest voice/tests/test_server.py -v     # from the repository root
"""
import base64
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

VOICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VOICE))

import server

FAKE_KEY = "sk-or-v1-thisisnotarealkey0000"
AUDIO = b"ID3" + b"\x00" * 3000


class FakeClient:
    """Stands in for the OpenRouter client and records which billed calls were made, in order."""

    def __init__(self, heard="What did Lane build?", audio_seconds=4.0,
                 said="Lane built a heat shield. He led the framing.",
                 speech=(AUDIO, "audio/mpeg"), speech_error=None):
        self.calls = []

        def create_transcription(**kwargs):
            self.calls.append("stt")
            return SimpleNamespace(text=heard, usage=SimpleNamespace(seconds=audio_seconds, cost=0.00002))

        def send(**kwargs):
            self.calls.append("chat")
            message = SimpleNamespace(content=said)
            return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")],
                                   usage=SimpleNamespace(cost=0.0005))

        def create_speech(**kwargs):
            self.calls.append("tts")
            if speech_error:
                raise RuntimeError(speech_error)
            data, ctype = speech
            return SimpleNamespace(read=lambda: data, headers={"content-type": ctype, "x-generation-id": "gen-1"})

        def get_generation(id):
            return SimpleNamespace(data=SimpleNamespace(total_cost=0.006))

        self.stt = SimpleNamespace(create_transcription=create_transcription)
        self.chat = SimpleNamespace(send=send)
        self.tts = SimpleNamespace(create_speech=create_speech)
        self.generations = SimpleNamespace(get_generation=get_generation)


@pytest.fixture
def run(monkeypatch, tmp_path):
    """Start the real handler on a free port with a fake client; return a function that posts to it."""
    monkeypatch.chdir(tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def post(client, path, body, ctype):
        monkeypatch.setattr(server, "CLIENT", client)
        request = urllib.request.Request(base + path, data=body, headers={"Content-Type": ctype}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as resp:
                text = resp.read().decode()
                status = resp.status
        except urllib.error.HTTPError as e:
            text, status = e.read().decode(), e.code
        assert FAKE_KEY not in text                       # behavior 36, on every response
        return status, json.loads(text)

    yield post
    httpd.shutdown()


def test_an_unknown_type_is_refused_before_any_billed_call(run):
    client = FakeClient()
    status, reply = run(client, "/api/voice", b"not audio", "text/plain")
    assert status == 415 and "unsupported" in reply["error"]
    assert client.calls == []


def test_a_body_over_the_cap_is_refused_not_cut_short(run, monkeypatch):
    monkeypatch.setattr(server, "MAX_BYTES", 1000)
    client = FakeClient()
    status, _ = run(client, "/api/voice", b"\x00" * 1001, "audio/wav")
    assert status == 413
    assert client.calls == []


def test_a_turn_transcribes_answers_and_speaks(run):
    client = FakeClient()
    status, reply = run(client, "/api/voice", b"RIFF....", "audio/webm;codecs=opus")
    assert status == 200 and client.calls == ["stt", "chat", "tts"]
    assert reply["transcript"] == "What did Lane build?"
    assert reply["answer"] == "Lane built a heat shield. He led the framing."
    assert base64.b64decode(reply["audio_b64"]) == AUDIO
    assert reply["cost"] == {"stt": 0.00002, "chat": 0.0005, "tts": 0.006}
    assert reply["error"] is None


def test_an_empty_transcript_is_a_failed_transcript(run):
    client = FakeClient(heard="  ")
    status, reply = run(client, "/api/voice", b"RIFF....", "audio/wav")
    assert status == 200 and reply["answer"] == "I didn't catch that."
    assert client.calls == ["stt"] and reply["audio_b64"] is None


def test_past_35_seconds_of_audio_stops_after_transcription(run):
    client = FakeClient(audio_seconds=36.0)
    _, reply = run(client, "/api/voice", b"RIFF....", "audio/wav")
    assert "35 seconds" in reply["error"] and reply["answer"] is None
    assert client.calls == ["stt"]


def test_an_empty_answer_is_reported_and_not_spoken(run):
    client = FakeClient(said="")
    _, reply = run(client, "/api/voice", b"RIFF....", "audio/wav")
    assert reply["answer"] is None and "no answer" in reply["error"]
    assert client.calls == ["stt", "chat"] and reply["audio_b64"] is None


def test_a_reply_that_is_not_audio_is_never_returned_as_audio(run):
    client = FakeClient(speech=(b'{"error": "unknown voice"}', "application/json"))
    _, reply = run(client, "/api/voice", b"RIFF....", "audio/wav")
    assert reply["audio_b64"] is None and "expected audio" in reply["error"]
    assert reply["transcript"] and reply["answer"]        # the visitor can still read what they could not hear


def test_a_provider_error_never_carries_the_key_back(run):
    client = FakeClient(speech_error=f"401 invalid key {FAKE_KEY}")
    _, reply = run(client, "/api/voice", b"RIFF....", "audio/wav")
    assert "[key removed]" in reply["error"]


def test_typed_and_spoken_questions_share_one_answer_function(run, monkeypatch):
    asked = []
    real = server.answer

    def spy(client, question):
        asked.append(question)
        return real(client, question)

    monkeypatch.setattr(server, "answer", spy)
    run(FakeClient(), "/api/ask", b"What did Lane build?", "text/plain")
    run(FakeClient(heard="And his part?"), "/api/voice", b"RIFF....", "audio/wav")
    assert asked == ["What did Lane build?", "And his part?"]


def test_a_turn_leaves_no_file_behind(run, tmp_path):
    before = sorted(p for p in VOICE.rglob("*") if "__pycache__" not in p.parts and ".pytest_cache" not in p.parts)
    run(FakeClient(), "/api/voice", b"RIFF....", "audio/wav")
    after = sorted(p for p in VOICE.rglob("*") if "__pycache__" not in p.parts and ".pytest_cache" not in p.parts)
    assert after == before
    assert list(tmp_path.iterdir()) == []
