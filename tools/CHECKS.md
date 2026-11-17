# Week 8 checks: one real tool

The chatbot's tool is `recent_commits(repo, count)`: the latest commits in one of my public GitHub repositories. Spec component 10, behaviors 41 to 52. Every run below went through `voice/answer.py`, the same answer function `/api/ask` and `/api/voice` use, with the profile in the prompt and the tool alongside it.

## No-key tests

`.venv/bin/python -m pytest voice/tests tools/tests`: 58 passed, 6 skipped (the billed tests, with no key), well under a second for `tools/tests`. The tests were committed failing before the code in both steps (`Tools: misuse-case tests, before the loop exists`, then `Tools: chatbot tests, before the tool is wired in`).

## Before the billed run

The real `openrouter` client was pointed at a fake OpenAI-compatible server on my Mac, no key and no cost, to check the request and reply shapes the scripted tests cannot see:

| Scripted reply | What the program did |
|---|---|
| A tool request, then an answer | The second request carried `system, user, assistant, tool`, with the tool message's `tool_call_id` matching the request; `tools` and the pinned Xiaomi provider went with every request |
| A misnamed argument, then a good call | Error result, the loop went on, answered |
| A tool that does not exist | Error result, answered |
| A model that asks forever | Stopped at four steps with the program's sentence |
| An answer in a code fence with markdown | Cleaned to plain text |
| An empty reply | Refused as an empty answer, nothing to speak |
| An answer naming commit `9fe01ab` with no tool call | Held back |
| A not-found repo, then "There's no repository called cpsc415-week09" | Passed: the name is in a negative sentence |
| HTTP 500 | The client **retried the request once on its own** before failing. That breaks the no-automatic-retries rule (behavior 38) for every billed call in `voice/`, not only this tool. Recorded here; the fix (`retry_config` on the client) belongs with the hosting decision before November 30. |

## The eval: five questions on two models

`tools/tests/test_eval.py`, November 17, 2026. Each question went through the answer function once per model; the tool calls, the words in the answer, and the claim check were checked in code. Every run, with its full trace, is in [`eval-results.json`](eval-results.json).

The eval ran three times, not once: the first two were started by calls that timed out on my side before the runs finished, and both kept running. The table is run 3; all three are summarized after it.

| # | Question | Model | Tools called | Steps | Result | Cost | Seconds |
|---|---|---|---|---|---|---|---|
| 1 | What has Lane committed lately to his portfolio? | MiMo | `recent_commits(cpsc415-portfolio)` | 2 | pass | $0.000130 | 10.2 |
| 1 | | M3 | `recent_commits(cpsc415-portfolio)` | 2 | pass | $0.000809 | 3.7 |
| 2 | What's in Lane's cpsc415-week09 repository? | MiMo | `recent_commits(cpsc415-week09)`: not found | 2 | pass | $0.000115 | 9.7 |
| 2 | | M3 | `cpsc415-week09` (not found), then `cpsc415-portfolio` and `cpsc415-week05` | 3 | pass | $0.002564 | 5.2 |
| 3 | What did Lane's capstone team build? | MiMo | none | 1 | pass | $0.000043 | 3.8 |
| 3 | | M3 | none | 1 | pass | $0.000516 | 2.6 |
| 4 | What did Lane commit yesterday? | MiMo | `recent_commits(cpsc415-portfolio)` | 2 | pass | $0.000155 | 13.6 |
| 4 | | M3 | 9 calls: `cpsc415-portfolio`, `week01` to `week05`, and two names that do not exist, `lane-faison` and `portfolio` | 4 | **fail: hit the step cap** | $0.003240 | 30.8 |
| 5 | What were the latest commits in Lane's week 5 lab and in his portfolio? | MiMo | `cpsc415-portfolio` and `cpsc415-week05`, in parallel | 2 | pass | $0.000186 | 5.3 |
| 5 | | M3 | `cpsc415-week05` and `cpsc415-portfolio`, in parallel | 2 | pass | $0.001287 | 3.7 |

MiMo is `xiaomi/mimo-v2.6-flash` (pinned to Xiaomi, reasoning effort low); M3 is `minimax/minimax-m3`.

### All three runs

| # | MiMo steps, runs 1 / 2 / 3 | M3 steps, runs 1 / 2 / 3 | Failures |
|---|---|---|---|
| 1 | 2 / 2 / 2 | 2 / 2 / 2 | none |
| 2 | 2 / 2 / 2 | 3 / 2 / 3 | none |
| 3 | 1 / 1 / 1 | 1 / 1 / 1 | none: neither model ever called the tool for a profile question |
| 4 | 2 / 2 / 2 | 2 / 4 / 4 (cap) | M3, run 3 |
| 5 | 2 / 2 / 2 | 2 / 2 / 2 | none |

29 of 30 runs passed. No answer was held back by the claim check in any run.

### Totals

| | MiMo | M3 |
|---|---|---|
| Cost per question with a tool call (mean of 12) | $0.00029 | $0.0020 |
| Cost per question without one (mean of 3) | $0.00005 | $0.00084 |
| Most steps any question took | 2 | 4 (question 4, runs 2 and 3) |

All 30 runs together cost $0.030, three times the $0.01 planned, because the eval ran three times. GitHub cost nothing and its rate limit was never reached.

## Linter

`ruff check .` while building: two findings in my new code (`Optional[str]` where the 3.11 code should say `str | None`, in `tools/loop.py` and `voice/answer.py`, and an unused `noqa` comment in `voice/answer.py`), all fixed before the commits. Now: no findings in `tools/` or the files this week changed. Two remain in files from earlier weeks, an import-order note in `voice/transcribe.py` and a style note in a local hook script, left as they are.
