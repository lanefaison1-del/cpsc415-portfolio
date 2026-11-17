"""The chatbot's answer function. The typed path (/api/ask) and the voice path (/api/voice) both call it.

    python3 answer.py "What did Lane's capstone team build?"      # needs OPENROUTER_API_KEY

The instructions are the October 5 grounding rules, a spoken-answer rule, the tool rule, and the
profile. The question goes through the tool loop in tools/loop.py, so the model can ask for
recent_commits. The reply is cut to at most three sentences with markdown removed, so what the
page shows is exactly what is spoken and exactly what the claim check reads. An empty reply is a
failure and is never spoken. Spec behaviors 34, 35, 37 and 49 to 51.
"""
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import loop  # the tool loop lives in tools/ (spec component 10)

CHAT_MODEL = os.environ.get("CHAT_MODEL", "xiaomi/mimo-v2.6-flash")
HEADING = "LANE'S PROFILE (JSON)"
SPOKEN_RULE = ("Spoken answer rule: this answer will be read aloud. This overrides the length and list "
               "guidance above: at most three sentences, no lists, no markdown, and no URLs. "
               "An email address is allowed.")

_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_LIST_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
_LINE_MARK = re.compile(r"^\s*[#>]+\s*", re.MULTILINE)
_SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
_INITIALS = re.compile(r"(?:[a-z]\.)*[a-z]")
_ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "e.g", "i.e", "etc", "no"}


class EmptyAnswer(Exception):
    """The model returned nothing to say. Reported to the visitor, never sent to the speech model."""


def tool_rule(today: str | None = None) -> str:
    """What the model is told about the tool, with today's and yesterday's dates from the clock."""
    day = datetime.date.fromisoformat(today) if today else datetime.date.today()
    return ("Tool rule: the recent_commits tool returns the latest commits in Lane's public GitHub "
            "repositories. Call it before saying anything about what Lane has committed or worked on lately. "
            "Facts about his commits and repositories may come from its results as well as the profile, and "
            "nowhere else: never state a repository, commit, or date that a result did not contain. If a result "
            f"says a repository was not found, say so plainly. Today is {day.isoformat()}; yesterday was "
            f"{(day - datetime.timedelta(days=1)).isoformat()}.")


def system_prompt(root: Path = ROOT, today: str | None = None) -> str:
    """Grounding rules, then the spoken-answer rule and the tool rule, then the profile."""
    rules = (root / "evidence" / "grounding-draft.md").read_text(encoding="utf-8")
    if rules.count(HEADING) != 1:
        raise ValueError(f"the grounding rules must contain {HEADING!r} exactly once")
    profile = json.loads((root / "profile" / "profile.json").read_text(encoding="utf-8"))
    rules = rules.replace(HEADING, SPOKEN_RULE + "\n\n" + tool_rule(today) + "\n\n" + HEADING)
    return rules + "\n" + json.dumps(profile, indent=1)


def sentences(text: str) -> list[str]:
    """Split on . ! or ? followed by a space, except after initials (D.C.) and common abbreviations."""
    out, start = [], 0
    for m in _SENTENCE_END.finditer(text):
        before = text[start:m.start()].split()
        last = before[-1].lower().rstrip(".") if before else ""
        if m.group().startswith(".") and (last in _ABBREVIATIONS or _INITIALS.fullmatch(last)):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    rest = text[start:].strip()
    if rest:
        out.append(rest)
    return [s for s in out if s]


def spoken(text: str | None) -> str:
    """At most three sentences, no markdown."""
    t = _LINK.sub(r"\1", text or "")
    t = _LIST_MARK.sub("", t)
    t = _LINE_MARK.sub("", t)
    t = t.replace("*", "").replace("`", "")
    t = " ".join(t.split())
    return " ".join(sentences(t)[:3])


def answer(client, question: str, model: str = CHAT_MODEL) -> dict:
    """One question through the tool loop. Returns the cleaned answer, the trace, and what CHECKS.md
    records. The check reads exactly what would be spoken (behaviors 34, 49 and 50)."""
    t0 = time.time()
    prompt = system_prompt()
    request = {"model": model, "max_tokens": 2000, "temperature": 0.2, "reasoning": {"effort": "low"},
               "messages": [{"role": "system", "content": prompt},
                            {"role": "user", "content": question}]}
    if model.startswith("xiaomi/"):
        request["provider"] = {"order": ["xiaomi"], "allow_fallbacks": False}   # pinned, as the spec says
    r = loop.run(client, request, known_text=prompt, clean=spoken)
    if not r["answer"]:
        raise EmptyAnswer(f"the model returned no answer (finish reason: {r['finish_reason']})")
    return {"text": r["answer"], "model": model, "finish_reason": r["finish_reason"], "cost": r["cost"],
            "seconds": round(time.time() - t0, 1), "trace": r["steps"], "calls": r["calls"],
            "stopped_by": r["stopped_by"], "check": r["check"], "held_back": r["held_back"]}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('usage: python3 answer.py "question"')
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set; nothing was billed.")
    from openrouter import OpenRouter
    print(json.dumps(answer(OpenRouter(api_key=key), sys.argv[1]), indent=1))
