"""No-key tests for the answer function (spec behaviors 34, 35 and 37). The model is a fake.

    .venv/bin/python -m pytest voice/tests/test_answer.py -v     # from the repository root
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from answer import (
    HEADING,
    SPOKEN_RULE,
    EmptyAnswer,
    answer,
    sentences,
    spoken,
    system_prompt,
)


class FakeClient:
    """Stands in for the OpenRouter client: returns a canned reply and records the request."""

    def __init__(self, content, finish_reason="stop"):
        self.sent = None

        def send(**kwargs):
            self.sent = kwargs
            message = SimpleNamespace(content=content)
            return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
                                   usage=SimpleNamespace(cost=0.0001))

        self.chat = SimpleNamespace(send=send)


def test_at_most_three_sentences():
    text = "One is first. Two is second! Three is third? Four is cut."
    assert spoken(text) == "One is first. Two is second! Three is third?"


def test_abbreviations_do_not_end_a_sentence():
    text = "Lane interned in Washington, D.C. this summer. He met Prof. Smith. Two. Three."
    assert sentences(text) == ["Lane interned in Washington, D.C. this summer.", "He met Prof. Smith.",
                               "Two.", "Three."]


def test_markdown_is_removed():
    text = "**Lane** built a `retriever`.\n\n- one item\n- two items\n\nSee [his profile](https://example.com)."
    out = spoken(text)
    for mark in ("*", "`", "- ", "[", "]("):
        assert mark not in out
    assert "Lane built a retriever." in out and "his profile" in out


def test_an_email_address_survives():
    assert spoken("Email Lane at lanefaison1@gmail.com. He replies.") == "Email Lane at lanefaison1@gmail.com. He replies."


def test_an_empty_answer_is_a_failure_not_something_to_speak():
    for content in (None, "", "   ", "**"):
        with pytest.raises(EmptyAnswer):
            answer(FakeClient(content, finish_reason="length"), "What did Lane build?")


def test_the_answer_comes_back_cleaned_with_its_cost():
    reply = answer(FakeClient("**Lane** led the framing. He chose the cone. He wrote the conclusions. Extra."), "q")
    assert reply["text"] == "Lane led the framing. He chose the cone. He wrote the conclusions."
    assert reply["cost"] == 0.0001 and reply["finish_reason"] == "stop"


def test_the_request_uses_the_spec_settings():
    client = FakeClient("Fine.")
    answer(client, "What did Lane build?")
    sent = client.sent
    assert sent["model"] == "xiaomi/mimo-v2.6-flash"
    assert sent["temperature"] == 0.2 and sent["max_tokens"] == 2000
    assert sent["reasoning"] == {"effort": "low"}
    assert sent["provider"] == {"order": ["xiaomi"], "allow_fallbacks": False}
    assert sent["messages"][0]["role"] == "system"
    assert sent["messages"][1] == {"role": "user", "content": "What did Lane build?"}


def test_the_prompt_is_the_grounding_rules_then_the_spoken_rule_then_the_profile():
    prompt = system_prompt()
    assert prompt.index("Rules") < prompt.index(SPOKEN_RULE) < prompt.index(HEADING)
    profile = json.loads(prompt.split(HEADING, 1)[1])
    assert profile["person"]["name"] == "Lane Faison"


# ---- Week 8: the tool in the chatbot (spec behaviors 46, 49, 50, 51) ---------------------------
class ScriptedClient:
    """Returns scripted replies in order: a tool request first, then an answer."""

    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

        def send(**kwargs):
            self.sent.append(kwargs)
            return self.replies.pop(0)
        self.chat = SimpleNamespace(send=send)


def _tool_request(arguments, call_id="call_1"):
    tc = SimpleNamespace(id=call_id, function=SimpleNamespace(name="recent_commits", arguments=arguments))
    message = SimpleNamespace(content="", tool_calls=[tc])
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                           usage=SimpleNamespace(cost=0.0001))


def _answer(text):
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")],
                           usage=SimpleNamespace(cost=0.0001))


@pytest.fixture
def no_network(monkeypatch):
    import github
    monkeypatch.setattr(github, "_fetch", lambda url: (200, [{"sha": "042f79e8a1", "commit": {
        "author": {"date": "2026-11-16T22:01:00Z"}, "message": "Week 8 working rules"}}]))


def test_the_answer_carries_the_tool_and_returns_the_trace(no_network):
    client = ScriptedClient([_tool_request('{"repo": "lanefaison1-del/cpsc415-portfolio"}'),
                             _answer("**Lane's** latest portfolio commit is Week 8 working rules, on 2026-11-16.")])
    reply = answer(client, "What has Lane committed lately?")
    assert client.sent[0]["tools"][0]["function"]["name"] == "recent_commits"
    assert reply["text"] == "Lane's latest portfolio commit is Week 8 working rules, on 2026-11-16."
    assert reply["trace"][0]["tool"] == "recent_commits" and reply["calls"] == ["recent_commits"]
    assert reply["cost"] == pytest.approx(0.0002)


def test_an_unsupported_claim_never_reaches_the_visitor(no_network):
    reply = answer(ScriptedClient([_answer("Yesterday Lane pushed 9fe01ab to cpsc415-portfolio.")]), "q")
    import loop
    assert reply["text"] == loop.HELD_ANSWER
    assert reply["held_back"].startswith("Yesterday") and not reply["check"]["supported"]


def test_the_prompt_tells_the_model_about_the_tool_and_today():
    prompt = system_prompt(today="2026-11-17")
    assert "recent_commits" in prompt and "2026-11-17" in prompt and "2026-11-16" in prompt
    assert prompt.index(SPOKEN_RULE) < prompt.index("recent_commits") < prompt.index(HEADING)


def test_the_typed_route_returns_the_trace(no_network):
    import server
    client = ScriptedClient([_tool_request('{"repo": "lanefaison1-del/cpsc415-portfolio"}'),
                             _answer("Lane's latest commit is Week 8 working rules.")])
    reply = server.typed_turn(client, "What has Lane committed lately?")
    assert reply["trace"][0]["result"]["repo"] == "lanefaison1-del/cpsc415-portfolio"
    assert "sk-or-v1" not in json.dumps(reply)
