"""Text in, MP3 out, through OpenRouter's speech endpoint (POST /api/v1/audio/speech).

    python3 speak.py "Hello from CPSC 415." --out hello.mp3                 # needs OPENROUTER_API_KEY
    python3 speak.py "Hello from CPSC 415." --voice en-GB-Emily:MAI-Voice-2.1-Flash --out hello-gb.wav   # .wav asks for PCM
    python3 speak.py "Hello from CPSC 415." --model elevenlabs/eleven-v4-turbo --voice george --out hello-11.mp3

The reply is raw audio bytes, not JSON, so there is no usage object in it. The bill is
in the generation record (X-Generation-Id header), which appears about a minute after the call;
until then the cost is estimated from the catalog price per character.

The course example's file, with one change for my server: synthesize() returns the audio
in memory, so a visitor's spoken answer is never written to disk (spec behavior 40).
speak() calls it and writes the file, as before.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import wave
from pathlib import Path

from openrouter import OpenRouter

DEFAULT_MODEL = "microsoft/mai-voice-2.1-flash"       # priced per character; 23 languages; a voice per locale; under a second
DEFAULT_VOICE = "en-US-Harper:MAI-Voice-2.1-Flash"    # the model's voice ids carry the locale: en-GB-Emily, en-IN-Priya, es-MX-Valeria, ...
_PRICES: dict[str, float] = {}


def synthesize(client: OpenRouter, text: str, model: str = DEFAULT_MODEL, voice: str = DEFAULT_VOICE,
               fmt: str = "mp3") -> tuple[bytes, dict]:
    """One TTS call, kept in memory. Returns the audio bytes and what is recorded: characters,
    bytes, seconds, cost. A reply that is not audio raises, so an error body is never used as audio."""
    t0 = time.time()
    r = client.tts.create_speech(model=model, input=text, voice=voice, response_format=fmt)
    data = r.read()                                  # the SDK hands back a streaming httpx response
    seconds = round(time.time() - t0, 1)
    ctype = r.headers.get("content-type", "")
    if not ctype.startswith("audio/"):               # an error body is JSON; never treat JSON as audio
        raise RuntimeError(f"expected audio, got {ctype}: {data[:300]!r}")
    gen_id = r.headers.get("x-generation-id")
    billed = cost_of(client, gen_id)
    return data, {"model": model, "voice": voice, "chars": len(text), "bytes": len(data), "seconds": seconds,
                  "content_type": ctype, "generation_id": gen_id,
                  "cost": billed if billed is not None else estimate(model, len(text)),
                  "cost_is_estimate": billed is None}


def speak(client: OpenRouter, text: str, out: Path, model: str = DEFAULT_MODEL, voice: str = DEFAULT_VOICE) -> dict:
    """One TTS call written to a file (MP3, or WAV when `out` ends in .wav).

    Why WAV exists here: on October 26 the MP3s from two per-character models carried a wrong length
    in their header, and Whisper's host trusted it and transcribed only the first half of each clip,
    while Scribe read the whole thing. Raw PCM has no header to be wrong; `wave` writes a correct one."""
    fmt = "pcm" if out.suffix.lower() == ".wav" else "mp3"
    data, info = synthesize(client, text, model, voice, fmt)
    if fmt == "pcm":                                 # "audio/pcm;rate=24000;channels=1" says how to frame it
        ctype = info["content_type"]
        rate = int((re.search(r"rate=(\d+)", ctype) or ["", "24000"])[1])
        channels = int((re.search(r"channels=(\d+)", ctype) or ["", "1"])[1])
        with wave.open(str(out), "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(data)
    else:
        out.write_bytes(data)
    return {"file": str(out), **info}


def cost_of(client: OpenRouter, gen_id: str | None) -> float | None:
    """The generation record carries the bill. On October 26 it took about a minute to appear
    (NotFound until then), so this is one try; the estimate covers the gap."""
    if not gen_id:
        return None
    try:
        return client.generations.get_generation(id=gen_id).data.total_cost
    except Exception:  # noqa: BLE001  # not there yet, or the lookup failed; the audio is already saved
        return None


def estimate(model: str, chars: int) -> float | None:
    """Catalog price per character times characters. Right for per-character models (most of them);
    token-priced ones (Gemini TTS) are billed differently, and the record is the truth."""
    if not _PRICES:
        with urllib.request.urlopen("https://openrouter.ai/api/v1/models?output_modalities=speech", timeout=20) as resp:
            for m in json.load(resp)["data"]:
                _PRICES[m["id"]] = float(m["pricing"].get("prompt") or 0)
    return round(_PRICES[model] * chars, 6) if model in _PRICES else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--out", type=Path, default=Path("speech.mp3"))
    ap.add_argument("--model", default=os.environ.get("TTS_MODEL", DEFAULT_MODEL))
    ap.add_argument("--voice", default=os.environ.get("TTS_VOICE", DEFAULT_VOICE))
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set; nothing was billed.")
    info = speak(OpenRouter(api_key=key), a.text, a.out, a.model, a.voice)
    print(f"{info['file']}  {info['bytes']} bytes  {info['chars']} chars  {info['seconds']}s  "
          f"cost ${info['cost']}{' (estimated)' if info['cost_is_estimate'] else ''}  [{info['model']} / {info['voice']}]")
