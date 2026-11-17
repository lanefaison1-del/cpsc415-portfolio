"""The billed eval: five questions on each model, through the chatbot's own answer function, with
the tool calls and the answers checked in code. Skipped without a key. About a cent for both models.

    OPENROUTER_API_KEY=... .venv/bin/python -m pytest tools/tests/test_eval.py -v -s

Every run is written to tools/eval-results.json, which CHECKS.md is built from.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "voice"))

KEY = os.environ.get("OPENROUTER_API_KEY")
pytestmark = pytest.mark.skipif(not KEY, reason="OPENROUTER_API_KEY not set: the billed eval is skipped")
MODELS = os.environ.get("EVAL_MODELS", "xiaomi/mimo-v2.6-flash,minimax/minimax-m3").split(",")
RESULTS = ROOT / "tools" / "eval-results.json"
NEGATIVE = ("no ", "not ", "n't", "never", "nothing", "none")

# id, question, tool calls that must happen (None: record only), any-of words the answer must contain,
# words it must not contain, how many tool calls at least
CASES = [
    ("lately", "What has Lane committed lately to his portfolio?", {"recent_commits"}, (), (), 1),
    ("missing_repo", "What's in Lane's cpsc415-week09 repository?", {"recent_commits"}, NEGATIVE,
     ("commits on", "it contains"), 1),
    ("profile_only", "What did Lane's capstone team build?", None, ("heat shield",), (), 0),
    ("yesterday", "What did Lane commit yesterday?", {"recent_commits"}, NEGATIVE, (), 1),
    ("two_repos", "What were the latest commits in Lane's week 5 lab and in his portfolio?", {"recent_commits"},
     (), (), 2),
]
_RUNS = []


@pytest.fixture(scope="module")
def client():
    from openrouter import OpenRouter
    yield OpenRouter(api_key=KEY)
    old = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    RESULTS.write_text(json.dumps(old + _RUNS, indent=1) + "\n")


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_case(client, model, case):
    from answer import answer
    cid, question, must_call, any_of, must_not, min_calls = case
    t0 = time.time()
    r = answer(client, question, model=model)
    low = r["text"].lower()
    problems = []
    if r["stopped_by"] != "answer":
        problems.append("hit the step cap")
    if must_call and not must_call <= set(r["calls"]):
        problems.append(f"expected a call to {sorted(must_call)}")
    if len(r["calls"]) < min_calls:
        problems.append(f"expected at least {min_calls} tool calls")
    if any_of and not any(w in low for w in any_of):
        problems.append(f"answer should contain one of {list(any_of)}")
    problems += [f"answer must not say {w!r}" for w in must_not if w in low]
    if r["held_back"]:
        problems.append("claim check held the answer back: " + "; ".join(r["check"]["unsupported"]))
    _RUNS.append({"date": time.strftime("%Y-%m-%d"), "case": cid, "model": model, "question": question,
                  "calls": r["calls"], "steps": len({s["step"] for s in r["trace"]}), "cost": r["cost"],
                  "seconds": round(time.time() - t0, 1), "finish_reason": r["finish_reason"],
                  "stopped_by": r["stopped_by"], "answer": r["text"], "held_back": r["held_back"],
                  "check": r["check"], "trace": r["trace"], "passed": not problems, "problems": problems})
    print(f"\n[{model}] {cid}: calls={r['calls']} cost=${r['cost']:.6f}\n  {r['text']}")
    assert not problems, problems
