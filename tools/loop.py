"""The tool loop: the model asks, the program decides, and the model answers from what came back.

The model never runs anything. Each request it writes is parsed and checked here against the
schema, then run, refused, or held for a person (a side effect). Every problem goes back to the
model as the tool's result, never as an exception. The loop stops at a step cap, and then the
answer is the program's sentence, not the model's. Before an answer leaves, `check_answer` looks
for repository names, commit IDs and dates that no tool returned; an answer with one is held back.
Spec behaviors 41 to 49 and 51.
"""
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import github

_PROFILE = Path(__file__).resolve().parents[1] / "profile" / "profile.json"
CONTACT = json.loads(_PROFILE.read_text(encoding="utf-8"))["person"]["contact"]["email"]
CAP_ANSWER = f"I couldn't finish answering that. You can email Lane at {CONTACT}."
HELD_ANSWER = f"I couldn't confirm that from GitHub. You can email Lane at {CONTACT}."
MAX_STEPS = 4


@dataclass
class Registry:
    """The tools the model may ask for. `side_effects` are never run on the model's request alone."""
    tools: list
    functions: dict
    side_effects: set = field(default_factory=set)


REGISTRY = Registry(tools=[github.GITHUB_TOOL], functions={"recent_commits": github.recent_commits})


# ---- the decision -------------------------------------------------------------------------------
def validate(name: str, args, registry: Registry = REGISTRY) -> str | None:
    """An error message that says what to do, or None if the call fits the schema. Plain code."""
    schema = next((t["function"]["parameters"] for t in registry.tools if t["function"]["name"] == name), None)
    if schema is None:
        return f"unknown tool {name!r}; the only tools are {sorted(registry.functions)}"
    example = f"; use {github.EXAMPLE}" if name == "recent_commits" else ""
    if not isinstance(args, dict):
        return f"arguments must be a JSON object{example}"
    for req in schema.get("required", []):
        if req not in args:
            return f"missing required argument {req!r}{example}"
    for key, val in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            return f"unexpected argument {key!r}; the arguments are {sorted(schema['properties'])}{example}"
        if spec["type"] == "string" and not isinstance(val, str):
            return f"argument {key!r} must be a string{example}"
        if spec["type"] == "integer":
            if isinstance(val, bool) or not isinstance(val, int):
                return f"argument {key!r} must be an integer"
            if not spec.get("minimum", val) <= val <= spec.get("maximum", val):
                return f"argument {key!r} must be between {spec['minimum']} and {spec['maximum']}"
    return None


def run_tool(name: str, arguments, registry: Registry = REGISTRY, confirmed: bool = False) -> dict:
    """What the loop does with every request. `arguments` arrives as the JSON text the model wrote."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError as e:
            return {"error": f"arguments were not valid JSON ({e.msg}); use {github.EXAMPLE}"}
    else:
        args = arguments
    problem = validate(name, args, registry)
    if problem:
        return {"error": problem}
    if name in registry.side_effects and not confirmed:
        return {"error": f"{name} has a side effect and needs a person's confirmation first; "
                         "tell the visitor it has not been done", "pending": {"tool": name, "arguments": args}}
    return registry.functions[name](**args)


# ---- the loop -----------------------------------------------------------------------------------
def run(client, request: dict, max_steps: int = MAX_STEPS, registry: Registry = REGISTRY,
        known_text: str = "", clean=None) -> dict:
    """One question. `request` is the chat request without tools; the loop adds them and the turns.
    `known_text` is what the model was told besides tool results (the profile, today's date).
    `clean` turns the model's text into what the visitor would see, so the check reads exactly that."""
    messages = list(request["messages"])
    steps, cost, pending, seen = [], 0.0, [], {}
    finish = None
    for step in range(1, max_steps + 1):
        t0 = time.time()
        reply = client.chat.send(**{**request, "messages": messages, "tools": registry.tools})
        cost += getattr(getattr(reply, "usage", None), "cost", None) or 0.0
        choice = reply.choices[0]
        finish = choice.finish_reason
        msg = choice.message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:                                           # the model answered
            text = (msg.content or "").strip()
            if clean:
                text = clean(text)
            steps.append({"step": step, "answer": text, "seconds": round(time.time() - t0, 2), "finish": finish})
            return _result(text, steps, "answer", cost, pending, finish, known_text)
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                        for tc in calls]})
        for tc in calls:
            key = (tc.function.name, _canonical(tc.function.arguments))
            if key in seen:                                     # the same request again: no second GitHub call
                result = {"note": "you already have this result; answer from it", "result": seen[key]}
            else:
                result = run_tool(tc.function.name, tc.function.arguments, registry)
                seen[key] = result
            if "pending" in result:
                pending.append(result["pending"])
            steps.append({"step": step, "tool": tc.function.name, "arguments": tc.function.arguments,
                          "result": result, "seconds": round(time.time() - t0, 2)})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
    return _result(CAP_ANSWER, steps, "cap", cost, pending, finish, known_text)   # the program's answer


def _canonical(arguments) -> str:
    try:
        return json.dumps(json.loads(arguments) if isinstance(arguments, str) else arguments, sort_keys=True)
    except (json.JSONDecodeError, TypeError):
        return str(arguments)


def _result(text, steps, stopped_by, cost, pending, finish, known_text):
    out = {"answer": text, "steps": steps, "stopped_by": stopped_by, "cost": round(cost, 6),
           "calls": [s["tool"] for s in steps if "tool" in s], "pending": pending, "finish_reason": finish,
           "check": {"supported": True, "unsupported": []}, "held_back": None}
    if stopped_by == "answer":
        out["check"] = check_answer(text, steps, known_text)
        if not out["check"]["supported"]:                       # behavior 49: never shown to the visitor
            out["answer"], out["held_back"] = HELD_ANSWER, text
    return out


# ---- the claim check ----------------------------------------------------------------------------
_REPO = re.compile(r"\b(?:lanefaison1-del/)?(cpsc415-[a-z0-9-]*[a-z0-9])\b|\blanefaison1-del/([\w.-]*\w)", re.IGNORECASE)
_SHA = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b", re.IGNORECASE)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_NAMED = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?\b",
                    re.IGNORECASE)
_NEGATIVE = re.compile(r"\b(no|not|never|none|cannot|nothing)\b|n't\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _dates(text: str) -> set:
    """Every date in the text as (month, day), whichever way it is written."""
    out = {(int(m), int(d)) for _, m, d in _ISO.findall(text)}
    out |= {(_MONTHS.index(m.lower()[:3]) + 1, int(d)) for m, d in _NAMED.findall(text)}
    return out


def check_answer(answer: str, steps: list, known_text: str) -> dict:
    """Plain code looking for claims no source supports: a repository name, a commit ID, or a date
    that appears in no tool result and nowhere in `known_text`. A name that came back only as
    not found counts only in a sentence that says it does not exist. Invented claims in plain words
    ("he added tests") get past this; CHECKS.md says so."""
    found, not_found = [], set()
    for s in steps:
        r = s.get("result")
        if not isinstance(r, dict):
            continue
        r = r.get("result", r)                                  # a repeated request wraps the earlier result
        if r.get("found") is False:
            not_found.add(r["repo"].split("/")[-1].lower())
            found.append(json.dumps(r.get("repos_on_record", [])))
        elif "error" not in r:
            found.append(json.dumps(r))
    source = (" ".join(found) + " " + known_text).lower()
    shas = {m.lower() for m in _SHA.findall(source)}
    source_dates = _dates(source)
    unsupported = []
    for sentence in _SENTENCE.split(answer):
        negative = bool(_NEGATIVE.search(sentence))
        for m in _REPO.finditer(sentence):
            name = (m.group(1) or m.group(2)).lower()
            if name in source or (name in not_found and negative):
                continue
            unsupported.append(f"repository {name!r} that no tool returned")
        for sha in _SHA.findall(sentence):
            if not any(s.startswith(sha.lower()) or sha.lower().startswith(s) for s in shas):
                unsupported.append(f"commit {sha!r} that no tool returned")
        for d in sorted(_dates(sentence) - source_dates):
            unsupported.append(f"date {_MONTHS[d[0] - 1].title()} {d[1]} that no tool returned")
    return {"supported": not unsupported, "unsupported": unsupported}
