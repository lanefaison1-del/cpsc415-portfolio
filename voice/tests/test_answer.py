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
