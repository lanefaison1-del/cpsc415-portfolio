"""Check a transcript in plain code. No model, no key.

A transcript is model output, so something other than the transcriber has to check it:
how far the words drift from what was said (word error rate), whether the words that
must survive did (names, numbers), and whether anything came back at all.
Spec behaviors 29, 32 and 33.
"""
import re

_WORD = re.compile(r"[a-z0-9']+")


def words(text: str | None) -> list[str]:
    """Lower-case words with punctuation removed, so 'Hello, world!' equals 'hello world'."""
    return _WORD.findall((text or "").lower().replace("’", "'"))


def wer(expected: str, got: str | None) -> float:
    """Word error rate: insertions, deletions and substitutions per expected word.
    0.0 is a perfect transcript; an empty transcript scores 1.0."""
    e, g = words(expected), words(got)
    if not e:
        return 0.0 if not g else 1.0
    prev = list(range(len(g) + 1))
    for i, ew in enumerate(e, 1):
        cur = [i]
        for j, gw in enumerate(g, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ew != gw)))
        prev = cur
    return prev[-1] / len(e)


def _bare(word: str) -> str:
    """A possessive counts as the word itself: "faison's" becomes "faison"."""
    return word.removesuffix("'s").replace("'", "")


def survives(required: str, got: str | None) -> bool:
    """True when some run of adjacent transcript words joins exactly to the required word.

    Whole words only, so "plane" does not contain "Lane". Spacing and case do not count,
    so "boot camp" is "bootcamp" and "C P S C 415" is "CPSC 415"."""
    target = "".join(_bare(w) for w in words(required))
    if not target:
        return True
    tokens = [_bare(w) for w in words(got)]
    for start in range(len(tokens)):
        joined = ""
        for token in tokens[start:]:
            joined += token
            if joined == target:
                return True
            if not target.startswith(joined):
                break
    return False


def compare(expected: str, got: str | None, must_contain: list[str] | None = None,
            max_wer: float = 0.15) -> dict:
    """The verdict recorded per clip. An empty transcript is a failed transcript, not a crash."""
    rate = wer(expected, got)
    missing = [w for w in (must_contain or []) if not survives(w, got)]
    empty = not words(got)
    return {"ok": rate <= max_wer and not missing and not empty,
            "wer": round(rate, 3), "missing": missing, "empty": empty}
