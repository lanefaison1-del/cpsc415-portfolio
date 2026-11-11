# Week 7 checks: spoken interface

The typed Cloudflare chatbot in `plan.md` (steps 2 to 5) does not exist yet. Every answer recorded here comes from the local server in `voice/`, which answers from `profile/profile.json` with the October 5 grounding rules (`evidence/grounding-draft.md`). The voice route moves to the Cloudflare function before November 30.

## Setup checkpoints (November 9)

| Checkpoint | Result |
|---|---|
| A: one speech call | 52 characters, 99,840 bytes, 0.9 s, $0.00078 (estimated); `microsoft/mai-voice-2.1-flash`, `en-US-Harper:MAI-Voice-2.1-Flash` |
| B: one transcription | Course `clip-01.wav`: word error rate 0.0, 6.38 s of audio, $0.0000212, 1.4 s; `openai/whisper-large-v3-turbo` |
| Guard | Did not refuse `pip install openrouter` before the Week 7 spec named it. The guard looks for the word anywhere in `spec.md`, and the October 5 spec already says OpenRouter. |

## Answer model, before the spec chose its settings (November 9)

My two clip questions went once each to `xiaomi/mimo-v2.6-flash` on Xiaomi's endpoint, at reasoning low and at reasoning none. All four answers came back complete, with no empty replies: $0.000036 to $0.00053 each, 2.9 to 6.3 seconds. The spec keeps reasoning low, the setting the October 5 questions were tested on.

## Checker tests (`voice/tests/test_check.py`, no key)

| Run | Result |
|---|---|
| Before `check.py` existed | Collection error: `ModuleNotFoundError: No module named 'check'` |
| After `check.py` | 10 passed in 0.01 s |

## Lint (`ruff check .`, ruff 0.17.3)

| Run | Findings |
|---|---|
| First run | 13: twelve in the new `voice/` files (older `typing.List`/`Dict`/`Optional` style where Python 3.10+ allows `list`, `dict` and `X \| None`; one slice that `str.removesuffix()` replaces; one unneeded `noqa`), and one in `.claude/hooks/guard.py` (PIE810: two `startswith` calls that could be one) |
| After fixing the `voice/` files | 1: the PIE810 in `guard.py`, left as copied from the course example |

## My clips, transcribed on two models (November 10)

My two clips were recorded in iPhone Voice Memos (`.m4a`, 48 kHz) and converted to 24 kHz mono 16-bit WAV. `expected.json` was committed before either was recorded. Clip 1 is a question the profile can answer (close to seed question q14); clip 2 is one it cannot, because Tableau is not in the profile (close to q02). In clip 2 I said the course number as "C P S C four fifteen". The three course clips, spoken by a speech model, are the baseline. Each clip was transcribed once on each model with `transcribe.py --set clips/expected.json`; the full output is in `transcripts.json` and `transcripts-scribe.json`.

**`openai/whisper-large-v3-turbo`** (class model), $0.00029 for all five:

| Clip | Verdict | Word error rate | Missing words | Audio seconds | Cost | Call seconds | What came back |
|---|---|---|---|---|---|---|---|
| `lane-01.wav` (me) | FAIL | 0.059 | capstone | 6.464 | $0.0000215 | 3.1 | "What did Lane Faison's **Capzone** team build at Trinity, and what was his part of the project?" |
| `lane-02.wav` (me) | FAIL | 0.188 | Lane, Faison | 10.0 | $0.000111 | 1.1 | "Did **Lanefason** use Tableau **and** CPSC 415 and how good is he at building dashboards?" |
| `clip-01.wav` (course) | ok | 0.0 | none | 6.38 | $0.0000212 | 1.4 | exact |
| `clip-02.wav` (course) | ok | 0.0 | none | 10.0 | $0.000111 | 0.8 | exact |
| `clip-03.wav` (course) | ok | 0.0 | none | 7.708 | $0.0000257 | 4.8 | exact |

**`elevenlabs/scribe-v2`** (comparison), $0.00230 for all five, about eight times Whisper:

| Clip | Verdict | Word error rate | Missing words | Audio seconds | Cost | Call seconds |
|---|---|---|---|---|---|---|
| `lane-01.wav` (me) | ok | 0.0 | none | 6.464 | $0.000395 | 1.3 |
| `lane-02.wav` (me) | ok | 0.0 | none | 9.067 | $0.000554 | 1.1 |
| `clip-01.wav` (course) | ok | 0.0 | none | 6.38 | $0.000390 | 1.1 |
| `clip-02.wav` (course) | ok | 0.0 | none | 8.062 | $0.000493 | 0.7 |
| `clip-03.wav` (course) | ok | 0.0 | none | 7.708 | $0.000471 | 0.9 |

**Which model got my name right.** By the checker: Scribe on both of my clips; Whisper on clip 1 only. On clip 2 Whisper fused my name into one word, "Lanefason". The course example's check looks for the name anywhere inside the transcript, so it would have counted "Lane" as present in "Lanefason"; the whole-word rule in spec behavior 33 marks it missing. Whisper also lost "capstone" on clip 1. Both models brought the course number back as "415", so "four fifteen" said aloud was not a problem.

**My note after playing both clips and reading both transcripts aloud:** "Yes, got my name right and answered correctly."

**Whisper's audio seconds.** Whisper reported 10.0 seconds for both clips that run between 8 and 10 seconds (my clip 2 is 9.07 s, course clip 2 is 8.06 s) and charged them $0.0000111 per reported second. The three shorter clips came back with their real lengths at $0.0000033 per second. Scribe reported the real length every time.
