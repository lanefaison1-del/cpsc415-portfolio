"""The spoken interface for my portfolio chatbot: the browser records, the server transcribes,
answers from the profile, and speaks the answer.

    cd voice && ../.venv/bin/python server.py      # needs OPENROUTER_API_KEY; then http://localhost:8000

GET  /            the page
POST /api/voice   body = the recording, Content-Type = its format. Transcribe, answer, speak.
POST /api/ask     body = a typed question. The same answer function, without transcription or speech.

The key is read once at startup and never sent to the browser. Nothing a visitor sends or
receives is written to disk or logged: the log line for a turn holds only seconds and costs.
Spec behaviors 28 to 31 and 34 to 40.
"""
import base64
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from answer import EmptyAnswer, answer
from check import words
from speak import DEFAULT_MODEL as TTS_MODEL
from speak import DEFAULT_VOICE as TTS_VOICE
from speak import synthesize
from transcribe import DEFAULT_MODEL as STT_MODEL
from transcribe import transcribe

PAGE = (Path(__file__).resolve().parent / "index.html").read_bytes()
MAX_BYTES = 10_000_000                 # behavior 39: refused with 413, never cut short
MAX_AUDIO_SECONDS = 35                 # behavior 39: past this, no answer or speech call
MAX_QUESTION_CHARS = 2000
FORMATS = {"audio/webm": "webm", "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
           "audio/x-wav": "wav", "audio/wave": "wav", "audio/ogg": "ogg", "audio/mp4": "m4a",
           "audio/x-m4a": "m4a", "audio/m4a": "m4a", "audio/flac": "flac", "audio/aac": "aac"}
CLIENT = None                          # the OpenRouter client, made at startup; the tests put a fake here
_KEY = re.compile(r"sk-or-v1-[A-Za-z0-9]+")


def _scrub(message: str) -> str:
    """Provider messages go back to the page, so anything shaped like a key is removed first."""
    return _KEY.sub("[key removed]", message)[:300]


def voice_turn(client, audio: bytes, fmt: str) -> dict:
    """Hear, think, speak, once. Each step can stop the turn without the steps after it being billed."""
    heard = transcribe(client, audio, fmt, STT_MODEL)
    question = (heard["text"] or "").strip()
    reply = {"transcript": question, "answer": None, "audio_b64": None, "error": None, "trace": [],
             "cost": {"stt": heard["cost"], "chat": 0, "tts": 0},
             "seconds": {"stt": heard["seconds"], "chat": 0, "tts": 0}}
    if not words(question):                                        # behavior 29
        reply["answer"] = "I didn't catch that."
        return reply
    if (heard["audio_seconds"] or 0) > MAX_AUDIO_SECONDS:          # behavior 39
        reply["error"] = f"That recording runs past {MAX_AUDIO_SECONDS} seconds. Please ask a shorter question."
        return reply
    try:
        said = answer(client, question)                            # behavior 37: the typed path's function
    except EmptyAnswer as e:                                       # behavior 35
        reply["error"] = f"I couldn't put an answer together: {e}. Please ask again."
        return reply
    reply["answer"], reply["trace"] = said["text"], said["trace"]                # behavior 51
    reply["cost"]["chat"], reply["seconds"]["chat"] = said["cost"], said["seconds"]
    try:
        spoken, info = synthesize(client, said["text"], TTS_MODEL, TTS_VOICE)
    except Exception as e:  # noqa: BLE001  behavior 31: any failure, and the visitor can still read it
        reply["error"] = "The answer could not be spoken: " + _scrub(str(e))
        return reply
    reply["audio_b64"] = base64.b64encode(spoken).decode()
    reply["cost"]["tts"], reply["seconds"]["tts"] = info["cost"], info["seconds"]
    return reply


def typed_turn(client, question: str) -> dict:
    reply = {"transcript": question, "answer": None, "audio_b64": None, "error": None, "trace": [],
             "cost": {"stt": 0, "chat": 0, "tts": 0}, "seconds": {"stt": 0, "chat": 0, "tts": 0}}
    try:
        said = answer(client, question)
    except EmptyAnswer as e:
        reply["error"] = f"I couldn't put an answer together: {e}. Please ask again."
        return reply
    reply["answer"], reply["trace"] = said["text"], said["trace"]                # behavior 51
    reply["cost"]["chat"], reply["seconds"]["chat"] = said["cost"], said["seconds"]
    return reply


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            return self.reply(404, {"error": "not found"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BYTES:
            self.close_connection = True
            return self.reply(413, {"error": f"recordings over {MAX_BYTES // 1_000_000} MB are refused"})
        body = self.rfile.read(length)
        try:
            if self.path == "/api/voice":
                ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                fmt = FORMATS.get(ctype)
                if not fmt:                                        # behavior 28, before any billed call
                    return self.reply(415, {"error": f"unsupported audio type {ctype!r}"})
                result = voice_turn(CLIENT, body, fmt)
                print(f"voice turn: seconds {result['seconds']}  cost {result['cost']}", flush=True)
                return self.reply(200, result)
            if self.path == "/api/ask":
                question = body.decode("utf-8", "replace").strip()[:MAX_QUESTION_CHARS]
                if not words(question):
                    return self.reply(400, {"error": "empty question"})
                return self.reply(200, typed_turn(CLIENT, question))
            return self.reply(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001  the provider's message goes back, never the key
            return self.reply(502, {"error": _scrub(str(e))})

    def reply(self, status: int, data: dict):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    from openrouter import OpenRouter
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set; the server did not start.")
    CLIENT = OpenRouter(api_key=key)
    print(f"http://localhost:8000  (stt {STT_MODEL}, chat {os.environ.get('CHAT_MODEL', 'xiaomi/mimo-v2.6-flash')}, "
          f"tts {TTS_MODEL} / {TTS_VOICE})", flush=True)
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
