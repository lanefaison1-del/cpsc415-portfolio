# Plan

Builds what [`spec.md`](spec.md) describes, one feature per branch and pull request. Each pull request is reviewed against [`REVIEW.md`](REVIEW.md) before I merge it. The file names below confirm the spec's planned layout; nothing in the spec changes.

## Files to create or change

| File | Purpose | Pull request |
|---|---|---|
| `plan.md` | This plan | 1 |
| `profile/profile.json` | The profile, drafted from the approved seed. The single source of truth. | 1, then 2 for the last annotations |
| `CLAUDE.md` | Working rules updated for branches and pull requests; commands filled in as they exist | 1, then each PR that adds a command |
| `prompt/grounding.md` | The grounding rules, started from `evidence/grounding-draft.md` | 3 |
| `build.py` | Checks the profile, then writes the page and the instructions | 3 |
| `tests/test_build.py` | Build tests on small broken profiles in `tests/fixtures/` | 3 |
| `.private/denylist.txt` | Client names, deal names and post-graduation plans. Git-ignored; only on my Mac. | 3 (not committed) |
| `site/index.html` | Generated page | 3 |
| `functions/api/_prompt.js` | Generated instructions | 3 |
| `functions/api/_lib.js` | Input checks, CORS, stream conversion | 4 |
| `functions/api/ask.js` | `POST /api/ask` | 4 |
| `tests/lib.test.js`, `tests/ask.test.js` | Function tests on `node --test`, with OpenRouter replaced by a fake | 4 |
| `site/chat.js`, `site/style.css` | Chat widget and styles | 5 |
| `tests/render.test.js` | Escape-first markdown and injection tests for the widget | 5 |
| `tests/adversarial.json` | At least 14 cases covering every category in spec behavior 25 | 6 |
| `eval.py` | Runs the cases on both models and the judge | 6 |
| `CHECKS.md`, `evidence/runs/` | Recorded results, failures kept | 6, then every later run |
| `README.md` | How to run, test and deploy; results table | 7, finished in 8 |
| `ANNOTATION.md` | The four questions for the finished site | 8 |

## Order of work

Each step is one branch and one pull request, merged before the next starts.

1. **`plan-and-profile`** (October 19 milestone). This plan, the drafted profile, and CLAUDE.md working rules for branches. No code.
2. **`profile-annotations`** (before November 2). Every project's four annotations filled in my words, plus any profile corrections.
3. **`build-script`.** `prompt/grounding.md`, `build.py` and its tests. The build stops on every rule the spec lists. Until step 2 merges, `--draft` allows empty annotation fields; without it, the build fails on any empty field. Generates `site/index.html` and `functions/api/_prompt.js`.
4. **`chat-function`** (November 2: chatbot answering from the profile). `_lib.js` and `ask.js`, ported from Kousen's function to call OpenRouter, pinned to Xiaomi's endpoint. Tests first, then one real question through `wrangler pages dev` on my Mac.
5. **`chat-widget`.** `chat.js` and `style.css`, ported from Kousen's widget, with keyboard, screen-reader and no-JavaScript behavior from spec behaviors 22–24.
6. **`adversarial-eval`** (November 30). `tests/adversarial.json`, `eval.py`, the first two-model run recorded in `CHECKS.md`, and my review of every FAIL, every judge/check disagreement, and one PASS in five.
7. **`deploy`** (November 30). I create the Cloudflare account; then the Pages project, the `OPENROUTER_API_KEY` secret, the rate-limit rule, and an eval run against the deployed `/api/ask` with `--url`.
8. **`final`** (December 14). README, ANNOTATION.md, current CLAUDE.md, a last eval on both models, tag `portfolio-final`.

The Week 7 voice interface and the Week 8 chatbot tools each get their own intent first, as the intent says, and fit between steps 5 and 8.

## Risks

| Risk | Assumption it rests on | Blast radius | Guard |
|---|---|---|---|
| A confidential name reaches the public repo | Every client, deal and post-graduation term is in the denylist | High: the repo is public, and git history keeps it | The build fails on any denylisted term in the profile, the grounding rules or a generated file. The eval fails any answer that contains one. I add a term the moment it comes up. |
| The profile claims more than I have done | Every entry comes from something I stated | High: the whole grade rests on honesty | Shipped, learning and not-yet stay separate keys; every skill needs an evidence id; I review each profile diff in its pull request. |
| The cheap model behaves differently from the October 5 test | 14 single-turn questions predict the full set | Medium: wrong answers on the live site | Pin Xiaomi's endpoint; run both models at every milestone from November 2; switch `CHAT_MODEL` to Sonnet if MiMo fails a case Sonnet passes. |
| The judge passes a bad answer | Sonnet grades fairly, including its own answers | Medium: a failure goes unrecorded | Automatic checks run first and can't be overruled; I review every FAIL, every disagreement and one PASS in five, and record overrides. |
| `build.py` and the eval drift apart | Both use the one assembly function in `build.py` | Medium: a test result wouldn't mean what the site does | The eval imports that function; a build test compares the generated `_prompt.js` with the function's output. |
| Kousen's code doesn't port cleanly to OpenRouter | OpenRouter's endpoint matches OpenAI's for streaming | Low: confined to `ask.js` | Function tests run against a fake upstream that sends the OpenRouter stream format. |
| `wrangler` can't run locally | `npx wrangler` works with Node 24 on my Mac without Homebrew | Low: blocks the local check only | Fall back to the function tests plus a check on Cloudflare's preview deployment. |
| Cost runs over | About $0.56 per eval run, about $10 for the semester | Low: the lab key has a spending limit | No automatic retries; eval runs only at milestones and after prompt, model or host changes. |

## Proof

**Without an API key** (run on every pull request, cost $0):

| Check | Command | What it proves |
|---|---|---|
| Profile rules | `python3 build.py --draft`, then `python3 build.py` after step 2 | The profile meets every schema rule; the page and the instructions come only from the profile and the grounding rules (behaviors 20–21) |
| Build tests | `python3 -m unittest tests/test_build.py` | Each broken fixture (missing evidence id, missing reason, duplicate id, `http` URL, denylisted term) stops the build with a message naming the entry |
| Function tests | `node --test tests/` | Input checks, the 12-message and 4,000-character limits, role handling, the missing-key 500, the upstream 502 and 25-second timeout, CORS, and that the key never appears in a response (behaviors 15–19) |
| Widget tests | `node --test tests/render.test.js` | HTML in model output is escaped before markdown renders (behavior 24) |
| Page check | Open `site/index.html` with JavaScript off; tab through the widget; screen-reader check in Safari | Behaviors 22–23 |

**With the key** (only when the plan says so; cost noted):

| Check | Command | What it proves | Cost |
|---|---|---|---|
| Local answer | `npx wrangler pages dev site`, one question | The function, the key and the model work together on my Mac | about $0.0003 |
| Adversarial eval | `python3 eval.py` | Behaviors 1–14 and 25–26 on both models, results in `CHECKS.md` | about $0.56 per run |
| Deployed eval | `python3 eval.py --url https://<project>.pages.dev/api/ask` | The live site answers the way the local run did | about $0.56 per run |

## Subagents and parallel work

None. The steps depend on each other (the build comes before the function, and both come before the eval), so each one is built and merged in order on its own branch.

**Approved by:** Lane Faison, 2026-10-21

## Week 7

Builds the "Week 7: spoken interface" section of [`spec.md`](spec.md). The course assigns this lab to `main`, and it runs ahead of steps 2 to 5 above, which stay open.

### Files under `voice/`

| File | Purpose |
|---|---|
| `check.py`, `tests/test_check.py` | The checker and its no-key tests |
| `transcribe.py`, `speak.py` | The two billed request shapes |
| `answer.py`, `tests/test_answer.py` | The shared answer function and its no-key tests |
| `server.py`, `index.html`, `tests/test_server.py` | `/api/voice`, `/api/ask`, the recorder page, and the server's no-key tests |
| `test_browser.py` | The browser check, with the server running |
| `tests/test_eval.py` | The billed eval, skipped with no key |
| `clips/` | Three course clips, two of mine, and `expected.json` |
| `transcripts.json`, `transcripts-scribe.json` | The output of both transcribers |
| `answers/` | The two spoken answers |
| `CHECKS.md` | Every measured result |

### Order of work

Tests are committed failing before the code that passes them.

1. **Checker.** Failing tests, commit. Code, green run, `ruff check .`, commit `Voice: transcript checker with tests`.
2. **My clips.** Commit `clips/expected.json` by itself before any model hears the clips. Transcribe each clip once on each model, listen, record, commit `Voice: own clips transcribed on two models`.
3. **The answer, spoken.** Failing tests for the answer function, then the code. Send the misheard-name question. Speak the answer to clip 1 in two voices, listen, record, commit `Voice: the answer spoken, two voices`.
4. **The loop.** Failing server tests, then `/api/voice` and the page, then the browser check, then one real microphone turn recorded as **One turn**. Commit `Voice: the loop, with the browser check`.
5. **Submit.** Tag `week07-submitted` and push, only after my approval.

### Questions I asked before approving

1. **"If the transcriber turns my name into a different word, what does the chatbot do with the question, and which test notices?"** It answers the question it heard. During a visit, the only signal is "I heard: ..." on the page. No test notices a live misheard name; the must-survive check catches it only on recorded clips. **Correction:** the billed proof now sends one typed question with my name misheard as "Faisan", and `CHECKS.md` records whether the chatbot answers about me, asks, or says the profile does not cover it.
2. **"What does one voice turn cost on the class models, and what happens if a visitor holds the button down for a minute?"** About half a cent, most of it the spoken answer. The recorder stops at 30 seconds, but an uploaded file can run longer, and the course example cuts a body over 10 MB short without saying so. **Correction:** the server refuses a body over 10 MB with status 413, and it stops after transcription when the audio runs past 35 seconds. Both get no-key tests.

### Risks

| Risk | Blast radius | Guard |
|---|---|---|
| The transcriber changes my name | Medium: the chatbot answers a different question | "I heard: ..." on every turn; must-survive check on recorded clips; a second transcriber; the misheard-name question in Proof |
| A wrong spoken claim about me | High: the portfolio's honesty is the grade | Same grounding rules and answer function as typed; I listen to the spoken answers |
| A confidential term reaches the public repo through a saved answer | High | `.private/denylist.txt` does not exist yet, so I read every answer before it is committed. Only answers to my own clip questions are saved. |
| A long or oversized upload | Low: about half a cent a turn, but repeatable | 30-second recorder; 413 over 10 MB; no answer or speech past 35 seconds of audio |
| A visitor's recording or question ends up stored | Medium: privacy | Nothing is written to disk; a no-key server test checks that a turn leaves no file behind |
| Three-sentence cut drops the end of an answer | Low | The page shows exactly what was spoken; the prompt asks for three sentences first |
| An MP3 with a wrong length header cuts a transcript short | Low | Clips are WAV |
| The Python server does not port to Cloudflare | Medium, and only by November 30 | The request shapes are small; the port is part of the hosting decision |

### Proof

**Without an API key** (cost $0):

| Check | What it proves |
|---|---|
| `tests/test_check.py` | A perfect transcript scores zero; one word in thirteen scores one thirteenth; an empty reply scores one and is reported, not raised; a name that must survive is reported within tolerance; a number read as words is a miss; spacing and case do not count; whole words only ("plane" is not "Lane"); a possessive still counts |
| `tests/test_answer.py` | The answer is cut to three sentences with markdown removed; an empty answer is a failure and is not spoken |
| `tests/test_server.py` | With the model calls replaced by fakes: 415 for an unknown type, 413 over 10 MB, no answer or speech past 35 seconds, "I didn't catch that." on an empty transcript, no key in any response, no file left behind |
| `ruff check .` | Lint findings, recorded in `CHECKS.md` |

**With the key** (billed):

| Check | What it proves | Cost |
|---|---|---|
| Five clips, once on each of two transcribers | Word error rate, missing words, audio seconds and cost per clip; which model got my name right | about $0.003 |
| One typed question with my name misheard as "Faisan" | What the chatbot does with a misheard name | about $0.0005 |
| The answer to clip 1 in two voices | Characters, bytes and cost per voice; what each did with my name and the course number | about $0.02 |
| The browser check: one clip through the page | The browser never saw the key or the provider | about $0.005 |
| One microphone turn | What one visitor's question costs | about $0.005 |

Total billed: about $0.04.

**Approved by:** Lane Faison, 2026-11-10
