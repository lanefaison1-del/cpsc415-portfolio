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
