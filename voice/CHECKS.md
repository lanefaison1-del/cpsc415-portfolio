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

## The answer, typed and spoken (November 10)

**Typed answer to clip 1's question** through `answer.py` (the function the server uses for both routes): two sentences, 446 characters, finish reason `stop`, $0.00051, 6.2 s. The text is in `answers/answer-clip1.json`:

> Lane's capstone team designed a reusable LN2-cooled conical reentry heat shield to replace the single-use ablative AVCOAT standard, choosing liquid nitrogen flowing through radial pipes over a transpiration-cooled lattice, and built a serpentine cooling-channel rig with a thermocouple grid to validate the thermal models. Lane led the problem framing, the design alternatives and down-select, the final-design justification, and the conclusions.

Every fact in it is in the profile.

**My name misheard.** The same question typed with "Lane Faisan" instead of "Lane Faison": the chatbot answered about me as usual and did not mention the spelling. $0.00052, 5.6 s. A misheard surname does not stop or change an answer, so on a live turn the only place the error shows is "I heard: ..." on the page.

**Spoken twice** with `speak.py`:

| Voice | Model | Characters | Bytes | Length of audio | Cost | Call seconds |
|---|---|---|---|---|---|---|
| `en-US-Harper:MAI-Voice-2.1-Flash` (class, default) | `microsoft/mai-voice-2.1-flash` | 446 | 607,680 | 30.4 s | $0.00669 (billed, from the generation record) | 1.6 |
| `george` (comparison) | `elevenlabs/eleven-v4-turbo` | 446 | 465,649 | 29.0 s | $0.01784 (estimated from the catalog price) | 5.0 |

The files are `answers/answer-harper.mp3` and `answers/answer-george.mp3`. ElevenLabs cost about 2.7 times as much for the same text.

**What each voice did with my name, the course number and the abbreviations.** The answer has no course number in it. My note after listening to both: "Yes, got my name right and answered correctly." I kept Harper as the default. As a machine check, each spoken answer was transcribed back once with `elevenlabs/scribe-v2` ($0.0019 and $0.0018):

| Voice | "Lane" | "LN2" | "AVCOAT" | Word error rate against the text |
|---|---|---|---|---|
| Harper | kept, both times | came back as "LN two" | came back as "AV coat", which still counts | 0.091 |
| George | kept, both times | kept | came back as "AVCO" | 0.015 |

**Finding: three sentences is not short.** The model kept to the sentence limit with two long sentences, which run about 30 seconds aloud. Speech is priced per character, so the answer's length, not the sentence count, sets most of the cost of a turn.

## Lint, with the course files copied in

`transcribe.py` and `speak.py` are the course example's files, copied unchanged. `ruff check .` finds one import-order issue (I001) in `transcribe.py`, left as copied, alongside the PIE810 in `guard.py`. The new files `answer.py` and `tests/test_answer.py` are clean.

## Answer tests (`voice/tests/test_answer.py`, no key, a fake model)

| Run | Result |
|---|---|
| Before `answer.py` existed | Collection error: `ModuleNotFoundError: No module named 'answer'` |
| After `answer.py` | 18 passed with the checker tests, 0.01 s |

## The loop: `/api/voice` and the page (November 10)

`server.py` serves the page, `POST /api/voice` and `POST /api/ask`, and both routes call the same `answer()` from `answer.py`. `speak.py` is the course file with one change: `synthesize()` returns the spoken answer in memory, so the server never writes a visitor's audio to disk.

**Server tests** (`voice/tests/test_server.py`, no key, fake models):

| Run | Result |
|---|---|
| Before `server.py` existed | Collection error: `ModuleNotFoundError: No module named 'server'` |
| After `server.py` | 28 passed with the checker and answer tests, 6 billed tests skipped with no key, 5.0 s |

They cover 415 before any billed call, 413 over the size cap, a full turn, the empty transcript, the 35-second stop, the empty answer, a speech reply that is not audio, a provider error carrying a key-shaped string, one answer function for both routes, and no file left behind after a turn.

**Browser check** (`voice/test_browser.py`, Playwright with Chromium, my clip 1 through the page's file picker): 1 passed in 17.9 s. Its last three assertions: no request from the browser carried an `Authorization` header; no request went to OpenRouter; the page called `/api/voice`. That turn cost $0.0000718 to transcribe, $0.0000734 to answer and $0.00873 to speak, $0.0089 in all.

## One turn (November 10)

I used the microphone on the page three times. The server keeps no record of what was said, only seconds and costs, so the first two are known only from those:

| Turn | What happened | Transcription | Answer | Speech |
|---|---|---|---|---|
| 1 | A full turn | $0.0000493 | $0.0000835 | $0.00213 |
| 2 | An empty transcript: no answer or speech call was made (behavior 29) | $0.0000004 | none | none |
| 3 | The turn recorded below | $0.0000202 | $0.0000631 | $0.005895 |

**The question**, from my test set (seed question q01): "We need someone to write SQL against our deal database from day one. Can Lane do that?"

**I heard:** "We need something to write a SQL. Deal database from day one. Can Lane do that?" Against the question as written, the word error rate is 0.235, and both "Lane" and "SQL" survived. Whisper turned "someone" into "something" and lost "against our", but the words that carry the question came through.

**Answer**, three sentences, spoken by Harper:

> Lane lists SQL as "not yet" — he says his analysis has lived in spreadsheet models and agent-written Python so far, and SQL is the next skill he plans to learn. So he would not write that query by hand today, though he does build software by specifying it and verifying what a coding agent produces. If you want to talk through how he'd approach the schema, email him at lanefaison1@gmail.com.

Every claim in it is in the profile: SQL and writing code by hand are both on the "not yet" list, and the answer gives those reasons rather than claiming the skill. The refuse-to-fabricate rule held aloud.

| Step | Model | Cost | Seconds |
|---|---|---|---|
| Transcription | `openai/whisper-large-v3-turbo` | $0.0000202 | 2.5 |
| Answer | `xiaomi/mimo-v2.6-flash` | $0.0000631 | 4.1 |
| Speech | `microsoft/mai-voice-2.1-flash`, Harper | $0.005895 | 1.0 |
| **Total** | | **$0.005978** | **7.6** |

One spoken question costs about six-tenths of a cent, 99% of it speech. This figure goes into the hosting decision in `spec.md` before November 30.

## Lint, final

`ruff check .` finds 2 issues, both in course files left as copied: PIE810 in `.claude/hooks/guard.py` and I001 in `voice/transcribe.py`. Every file written for this lab is clean.
