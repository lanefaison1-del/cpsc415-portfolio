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
