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
| 4 | | M3 | 9 calls: `cpsc415-portfolio`, `week01` to `week05`, two names that do not exist, `lane-faison` and `portfolio`, and one refused for a misspelled owner, `lanefanity1-del` | 4 | **fail: hit the step cap** | $0.003240 | 30.8 |
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

## Misuse cases

The six from the lab, each with the no-key test in `tools/tests/test_loop.py` that covers it, and whether a real model produced it in the 30 billed runs.

| # | Misuse case | Test | From a real model? |
|---|---|---|---|
| 1 | The single-shot call: the result goes back as a `tool` message with the request's `tool_call_id` | `test_single_shot_call_goes_back_as_a_tool_message_with_its_id` | Yes, the normal path: 24 of 30 runs called the tool and 23 answered from its results |
| 2 | Bad arguments get an error result and the loop goes on | `test_wrong_argument_name_gets_an_error_that_says_what_to_do_and_the_loop_continues`, `test_bad_arguments_are_error_results_not_exceptions`, `test_someone_elses_repo_is_refused_without_a_request` | Once: step 3 of the trace below |
| 3 | A tool that does not exist gets an error result | `test_unknown_tool_gets_an_error_naming_the_real_one` | No. Both models only ever asked for `recent_commits` |
| 4 | A model that asks forever is stopped by the cap, and the answer is the program's | `test_endless_caller_stops_at_the_cap_and_the_answer_is_the_programs`, `test_an_identical_repeat_gets_the_earlier_result_without_calling_github_again` | Once: the trace below |
| 5 | A side-effect tool is held as pending and its effect does not happen | `test_a_side_effect_tool_is_held_as_pending_and_never_runs` | Cannot happen in the eval: `recent_commits` has no side effect, so the test registers a scripted outbox tool of its own |
| 6 | An answer naming something no tool returned is flagged | `test_an_answer_naming_a_commit_no_tool_returned_is_held_back`, `test_the_claim_check_looks_at_repos_commit_ids_and_dates`, `test_a_not_found_name_is_supported_only_in_a_negative_sentence` | No. Nothing was held back in 30 runs, including the six runs of question 4, which invites an invented commit |

**The trace: question 4 ("What did Lane commit yesterday?") on M3, run 3.**

| Step | The model asked for | What came back |
|---|---|---|
| 1 | `cpsc415-portfolio`, `cpsc415-week01`, `cpsc415-week02`, `cpsc415-week03`, in one reply | Commits; the latest is November 11 |
| 2 | `lane-faison`, `portfolio` | Not found, each with the list of my six public repositories |
| 3 | `cpsc415-week04`, and `lanefanity1-del/cpsc415-week05` | Commits; and a refusal, because the owner is misspelled: "this chatbot only looks at Lane's own repositories", with an example of a good call |
| 4 | `lanefaison1-del/cpsc415-week05` | Commits |
| | The cap | The visitor got "I couldn't finish answering that. You can email Lane at lanefaison1@gmail.com." |

Step 3 is misuse case 2 from a real model: the error result said what to do, and step 4 is the corrected call. After step 4 the model had every repository it needed, but the cap came before it could answer. In run 2 the same question on M3 also took four steps and passed, because the fourth step was the answer. The two guessed names and the misspelled owner are what cost run 3 its answer.

**My call:** a model error, not a problem with the case. The cap did its job and stays at four steps. The row stays a fail: neither the case nor the cap was changed to make it pass.

## What the check cannot catch

**A claim about what is not there, in plain words.** Question 4 on M3, run 1: "Lane did not commit anything yesterday." The model had looked at one repository, `cpsc415-portfolio`. That sentence has no repository name, commit ID or date in it, so the claim check had nothing to look at and passed it. The tool only showed that one repository had nothing on November 16. It said nothing about my other five public repositories, or about team repositories under other accounts. The sentence happened to be true for my public repositories (run 2 checked all six), but it would have passed just the same if it were false. MiMo kept to what it had checked all three times ("nothing from yesterday ... in that repository").

The evidence that would catch it: a second model, run on the eval only, that reads each answer next to its trace and says whether the answer claims more than the trace shows; and one line in the grounding prompt: when you say something is not there, name the repositories you checked. The second model runs on the eval and not on visitor turns, so a visitor's turn does not cost twice. Neither is built yet.

**A name the pattern cannot see.** Question 1 on MiMo, run 1, wrote the repository as "cpсc415-portfolio", with a Cyrillic "с" as the third letter. It looks right on the page, but the check's pattern only matches Latin letters, so the name was never checked. This one was a misspelling of a real name; an invented name written the same way would get through too. The evidence that catches it is code, not a person: map look-alike letters to Latin before the check, or flag any non-Latin letter in a word that looks like a repository name. Recorded as an open failure, to fix with the hosting work before November 30.

**A reading of the commits.** Question 1 on M3, run 2: "The pattern is test-first, with the implementation following each test." The commit messages show tests committed before the code twice, not after every test. It contains nothing code could check against; a person reading the answer next to the trace is the only evidence.

## The cost of a tool

| | MiMo | M3 |
|---|---|---|
| A question with a tool call (mean of 12) | $0.00029 | $0.0020 |
| A question without one (mean of 3) | $0.00005 | $0.00084 |
| With against without | about 6 times | about 2.4 times |
| The most steps, and that question's cost | 2 | 4, $0.0032 |

What this means for the hosting decision:

- **The site model stays MiMo.** On MiMo a question with a tool costs about the same as the $0.00033 per answer the October 5 budget assumed, so 2,000 site answers stay under $1 even if every one calls the tool. The spec's estimate for a tool question ($0.0008) was high. M3 costs about 7 times as much per tool question and was the only model that ever reached the cap.
- **A spoken turn barely changes.** Speech cost $0.002 to $0.009 per turn in `voice/CHECKS.md`; the tool adds about $0.00024, under a tenth of that.
- **The worst case grows.** The cap allows four chat calls per question, against one before this week. MiMo never took more than two steps, so the October 5 abuse ceiling (10,000 scripted requests, about $3.30) could roughly double, by my estimate rather than a measurement. The key's spending limit and the 10-requests-per-10-seconds rule still bound it.
