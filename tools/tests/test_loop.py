"""No-key tests for the chatbot's tool (spec behaviors 41 to 49). The model is scripted and GitHub
is faked, so nothing here touches the network or needs a key.

    .venv/bin/python -m pytest tools/tests -v      # from the repository root

Each test scripts what the model "did" and checks what the program did about it. The six misuse
cases the course names are marked MISUSE.
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import github
import loop
from loop import CAP_ANSWER, HELD_ANSWER, Registry, check_answer, run, run_tool

REPO = "lanefaison1-del/cpsc415-portfolio"
COMMITS = [{"sha": "042f79e8a1b2c3d4", "commit": {"author": {"date": "2026-11-16T22:01:00Z"},
                                                   "message": "Week 8 working rules\n\nmore"}},
           {"sha": "91c16d1ffeeddcc0", "commit": {"author": {"date": "2026-11-10T19:34:00Z"},
                                                   "message": "Voice: the loop, with the browser check"}}]
MY_REPOS = [{"name": "cpsc415-portfolio"}, {"name": "cpsc415-week05"}]


# ---- a faked GitHub: records every request, never opens a socket --------------------------------
@pytest.fixture
def gh(monkeypatch):
    """Replaces the one function in github.py that talks to the network."""
    state = NS(requests=[], status={})

    def fetch(url):
        state.requests.append(url)
        for part, status in state.status.items():
            if part in url:
                return status, None
        if "/users/lanefaison1-del/repos" in url:
            return 200, MY_REPOS
        if "/repos/lanefaison1-del/cpsc415-portfolio/commits" in url:
            return 200, COMMITS
        return 404, None

    monkeypatch.setattr(github, "_fetch", fetch)
    return state


# ---- a scripted model ---------------------------------------------------------------------------
def tool_call(name, arguments, call_id="call_1"):
    tc = NS(id=call_id, function=NS(name=name, arguments=arguments))
    return NS(choices=[NS(message=NS(content="", tool_calls=[tc]), finish_reason="tool_calls")],
              usage=NS(cost=0.0001))


def answer(text):
    return NS(choices=[NS(message=NS(content=text, tool_calls=None), finish_reason="stop")],
              usage=NS(cost=0.0001))


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []                                   # every request the loop sent

    @property
    def chat(self):
        return self

    def send(self, **kwargs):
        self.sent.append(copy.deepcopy(kwargs))
        if not self.replies:
            raise AssertionError("the loop asked the model again after the script ran out")
        return self.replies.pop(0)


def ask(fake, question="What has Lane committed lately?", **kw):
    request = {"model": "test/model", "messages": [{"role": "system", "content": "rules"},
                                                   {"role": "user", "content": question}]}
    return run(fake, request, **kw)


def tool_messages(sent):
    return [m for m in sent["messages"] if m["role"] == "tool"]


# ---- the schema --------------------------------------------------------------------------------
def test_the_schema_goes_with_every_request(gh):
    fake = FakeClient([answer("Hello.")])
    ask(fake)
    tools = fake.sent[0]["tools"]
    assert [t["function"]["name"] for t in tools] == ["recent_commits"]
    params = tools[0]["function"]["parameters"]
    assert params["required"] == ["repo"] and set(params["properties"]) == {"repo", "count"}
    assert "before" in tools[0]["function"]["description"].lower()      # it says when to call it


# ---- MISUSE 1: the single-shot call ------------------------------------------------------------
def test_single_shot_call_goes_back_as_a_tool_message_with_its_id(gh):
    fake = FakeClient([tool_call("recent_commits", json.dumps({"repo": REPO}), "call_7"),
                       answer("Lane's latest portfolio commit is Week 8 working rules, on 2026-11-16.")])
    r = ask(fake)
    assert r["stopped_by"] == "answer" and r["calls"] == ["recent_commits"]
    second = fake.sent[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-2]["tool_calls"][0]["id"] == "call_7"
    assert second[-1]["role"] == "tool" and second[-1]["tool_call_id"] == "call_7"
    result = json.loads(second[-1]["content"])
    assert result["commits"][0] == {"sha": "042f79e", "date": "2026-11-16", "message": "Week 8 working rules"}
    assert r["check"]["supported"] and r["answer"].startswith("Lane's latest")
    assert abs(r["cost"] - 0.0002) < 1e-9


def test_no_tool_needed_is_one_call(gh):
    fake = FakeClient([answer("Lane led the framing of his capstone.")])
    r = ask(fake, "What did Lane's capstone team build?")
    assert r["calls"] == [] and len(fake.sent) == 1 and gh.requests == []


# ---- MISUSE 2: bad arguments -------------------------------------------------------------------
def test_wrong_argument_name_gets_an_error_that_says_what_to_do_and_the_loop_continues(gh):
    fake = FakeClient([tool_call("recent_commits", json.dumps({"repository": REPO}), "call_1"),
                       tool_call("recent_commits", json.dumps({"repo": REPO}), "call_2"),
                       answer("Lane's latest commit is Week 8 working rules.")])
    r = ask(fake)
    first = tool_messages(fake.sent[1])[0]
    err = json.loads(first["content"])["error"]
    assert first["tool_call_id"] == "call_1"
    assert "missing required argument 'repo'" in err and '"repo": "lanefaison1-del/' in err
    assert r["stopped_by"] == "answer" and len(gh.requests) == 1      # only the good call reached GitHub


@pytest.mark.parametrize("arguments, words", [
    ('{"repo": "lanefaison1-del/cpsc', "not valid JSON"),
    ('["lanefaison1-del/cpsc415-portfolio"]', "JSON object"),
    ('{"repo": 42}', "must be a string"),
    ('{"repo": "lanefaison1-del/cpsc415-portfolio", "count": "five"}', "must be an integer"),
    ('{"repo": "lanefaison1-del/cpsc415-portfolio", "count": 50}', "between 1 and 10"),
    ('{"repo": "lanefaison1-del/cpsc415-portfolio", "branch": "main"}', "unexpected argument 'branch'"),
    ('{"repo": "cpsc415-portfolio"}', "owner/name"),
])
def test_bad_arguments_are_error_results_not_exceptions(gh, arguments, words):
    r = run_tool("recent_commits", arguments)
    assert words in r["error"] and gh.requests == []


# ---- MISUSE 3: the unknown tool ----------------------------------------------------------------
def test_unknown_tool_gets_an_error_naming_the_real_one(gh):
    fake = FakeClient([tool_call("get_resume", "{}"), answer("The profile covers his work; email Lane for a resume.")])
    ask(fake, "Send me his resume")
    err = json.loads(tool_messages(fake.sent[1])[0]["content"])["error"]
    assert "unknown tool 'get_resume'" in err and "recent_commits" in err


# ---- MISUSE 4: the endless caller --------------------------------------------------------------
def test_endless_caller_stops_at_the_cap_and_the_answer_is_the_programs(gh):
    fake = FakeClient([tool_call("recent_commits", json.dumps({"repo": REPO, "count": i + 1}), f"c{i}")
                       for i in range(10)])
    r = ask(fake)
    assert r["stopped_by"] == "cap" and len(fake.sent) == 4 and len(r["calls"]) == 4
    assert r["answer"] == CAP_ANSWER and CAP_ANSWER.startswith("I couldn't finish answering that. You can email Lane")
    assert loop.CONTACT in CAP_ANSWER and loop.CONTACT in HELD_ANSWER


def test_an_identical_repeat_gets_the_earlier_result_without_calling_github_again(gh):
    same = json.dumps({"repo": REPO})
    fake = FakeClient([tool_call("recent_commits", same, "a"), tool_call("recent_commits", same, "b"),
                       answer("Lane's latest commit is Week 8 working rules.")])
    r = ask(fake)
    repeat = json.loads(tool_messages(fake.sent[2])[-1]["content"])
    assert "already have this result" in repeat["note"] and repeat["result"]["repo"] == REPO
    assert len(gh.requests) == 1 and r["stopped_by"] == "answer"


# ---- MISUSE 5: the side effect held ------------------------------------------------------------
def test_a_side_effect_tool_is_held_as_pending_and_never_runs(gh):
    outbox = []
    schema = {"type": "function", "function": {
        "name": "request_intro", "description": "Ask Lane for an introduction.",
        "parameters": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}}
    reg = Registry(tools=[schema], functions={"request_intro": lambda email: outbox.append(email) or {"sent": True}},
                   side_effects={"request_intro"})
    fake = FakeClient([tool_call("request_intro", '{"email": "r@example.com"}'),
                       answer("Your request is noted; Lane has to confirm it before anything is sent.")])
    r = ask(fake, "Introduce me, I'm r@example.com", registry=reg)
    assert r["pending"] == [{"tool": "request_intro", "arguments": {"email": "r@example.com"}}]
    assert outbox == []
    assert "confirmation" in json.loads(tool_messages(fake.sent[1])[0]["content"])["error"]
    assert run_tool("request_intro", '{"email": "r@example.com"}', reg, confirmed=True) == {"sent": True}
    assert outbox == ["r@example.com"]                    # only a person's confirmation runs it


# ---- MISUSE 6: the unsupported claim -----------------------------------------------------------
def test_an_answer_naming_a_commit_no_tool_returned_is_held_back(gh):
    fake = FakeClient([answer("Yesterday Lane pushed commit 7ab12cd to cpsc415-portfolio.")])
    r = ask(fake, "What did Lane commit yesterday?")
    assert r["answer"] == HELD_ANSWER
    assert not r["check"]["supported"] and r["held_back"].startswith("Yesterday Lane pushed")
    assert any("7ab12cd" in u for u in r["check"]["unsupported"])


def test_the_claim_check_looks_at_repos_commit_ids_and_dates():
    steps = [{"tool": "recent_commits", "result": {"repo": REPO, "commits": [
        {"sha": "042f79e", "date": "2026-11-16", "message": "Week 8 working rules"}]}}]
    ok = "On November 16 Lane committed 042f79e, Week 8 working rules, to cpsc415-portfolio."
    assert check_answer(ok, steps, "")["supported"]
    for bad in ("He also pushed 9fe01ab.", "He committed on November 12.", "He committed on 2026-11-12.",
                "His cpsc415-week07 lab is done."):
        assert not check_answer(bad, steps, "")["supported"], bad


def test_profile_text_counts_as_a_source():
    assert check_answer("His week 1 lab is cpsc415-week01.", [], "github.com/lanefaison1-del/cpsc415-week01")["supported"]


def test_a_not_found_name_is_supported_only_in_a_negative_sentence(gh):
    steps = [{"tool": "recent_commits", "result": github.recent_commits("lanefaison1-del/cpsc415-week09")}]
    assert check_answer("There's no repository called cpsc415-week09. His repos include cpsc415-portfolio.",
                        steps, "")["supported"]
    r = check_answer("cpsc415-week09 has three commits on voice tests.", steps, "")
    assert not r["supported"] and "cpsc415-week09" in r["unsupported"][0]


def test_the_trace_records_each_step(gh):
    fake = FakeClient([tool_call("recent_commits", json.dumps({"repo": REPO})), answer("Week 8 working rules.")])
    r = ask(fake)
    step = r["steps"][0]
    assert step["tool"] == "recent_commits" and json.loads(step["arguments"]) == {"repo": REPO}
    assert step["result"]["repo"] == REPO and "seconds" in step
    assert r["steps"][-1]["answer"] == "Week 8 working rules."


def test_two_requests_in_one_reply_each_get_their_own_result(gh):
    tc1 = NS(id="a", function=NS(name="recent_commits", arguments=json.dumps({"repo": REPO})))
    tc2 = NS(id="b", function=NS(name="recent_commits", arguments='{"repo": "lanefaison1-del/cpsc415-week05"}'))
    both = NS(choices=[NS(message=NS(content="", tool_calls=[tc1, tc2]), finish_reason="tool_calls")],
              usage=NS(cost=0.0))
    fake = FakeClient([both, answer("The portfolio's latest commit is Week 8 working rules.")])
    r = ask(fake)
    assert [m["tool_call_id"] for m in tool_messages(fake.sent[1])] == ["a", "b"]
    assert r["calls"] == ["recent_commits", "recent_commits"]


# ---- the tool itself: GitHub's failures as results ---------------------------------------------
def test_someone_elses_repo_is_refused_without_a_request(gh):
    r = github.recent_commits("kousen/ai-integration-course")
    assert "only looks at Lane's own repositories" in r["error"] and gh.requests == []


def test_not_found_lists_my_repos(gh):
    r = github.recent_commits("lanefaison1-del/cpsc415-week09")
    assert r["found"] is False and r["repos_on_record"] == ["cpsc415-portfolio", "cpsc415-week05"]
    assert len(gh.requests) == 2


def test_rate_limit_and_timeout_are_results(gh, monkeypatch):
    gh.status["/commits"] = 403
    assert "rate limit" in github.recent_commits(REPO)["error"]
    monkeypatch.setattr(github, "_fetch", lambda url: (_ for _ in ()).throw(TimeoutError("timed out")))
    assert "could not reach GitHub" in github.recent_commits(REPO)["error"]


def test_count_is_passed_and_messages_are_trimmed(gh):
    r = github.recent_commits(REPO, 2)
    assert "per_page=2" in gh.requests[0] and r["commits"][0]["message"] == "Week 8 working rules"


def test_loop_module_exposes_the_registry():
    assert loop.REGISTRY.functions["recent_commits"] is github.recent_commits and not loop.REGISTRY.side_effects
