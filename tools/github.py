"""The chatbot's one tool: the latest commits in one of my public GitHub repositories.

    .venv/bin/python tools/github.py lanefaison1-del/cpsc415-portfolio

The schema below is what the model sees. The function is what the server runs, and only for my
own repositories. Everything that can go wrong comes back as a result the model can read, never an
exception: someone else's repository, one that does not exist (with my real ones listed), the rate
limit, or no answer. No key: public repositories allow 60 requests an hour per address.
Spec behaviors 41, 43 and 45.
"""
import json
import re
import sys
import urllib.error
import urllib.request

OWNER = "lanefaison1-del"
EXAMPLE = '{"repo": "lanefaison1-del/cpsc415-portfolio"}'
TIMEOUT = 20

GITHUB_TOOL = {"type": "function", "function": {
    "name": "recent_commits",
    "description": "The latest commits in one of Lane's public GitHub repositories (owner lanefaison1-del). "
                   "Call this before saying anything about what Lane has committed or worked on lately, or "
                   "what is in one of his repositories. If you do not know the repository's name, try "
                   "lanefaison1-del/cpsc415-portfolio; a not-found result lists the ones that exist.",
    "parameters": {"type": "object",
                   "properties": {"repo": {"type": "string",
                                           "description": "owner/name, for example lanefaison1-del/cpsc415-portfolio"},
                                  "count": {"type": "integer", "description": "How many commits, 1 to 10 (default 5)",
                                            "minimum": 1, "maximum": 10}},
                   "required": ["repo"]}}}


def _fetch(url: str):
    """The only function here that touches the network. Returns (status, parsed JSON or None)."""
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "lanefaison1-portfolio-chatbot"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, None


def my_repos() -> list:
    """The names of my public repositories, or an empty list if GitHub does not answer."""
    try:
        status, data = _fetch(f"https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed")
    except (urllib.error.URLError, TimeoutError, OSError):
        return []
    return [r["name"] for r in data] if status == 200 and isinstance(data, list) else []


def recent_commits(repo: str, count: int = 5) -> dict:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo or ""):
        return {"error": f"repo must be owner/name, got {repo!r}; use {EXAMPLE}"}
    owner = repo.split("/")[0]
    if owner.lower() != OWNER:
        return {"error": f"this chatbot only looks at Lane's own repositories ({OWNER}/...), not {owner}'s; "
                         f"use {EXAMPLE}"}
    try:
        status, data = _fetch(f"https://api.github.com/repos/{repo}/commits?per_page={count}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"error": f"could not reach GitHub ({e}); tell the visitor to try again later"}
    if status == 404:
        return {"found": False, "repo": repo, "error": f"no public repository named {repo}",
                "repos_on_record": my_repos()}
    if status in (403, 429):
        return {"error": "GitHub's rate limit was reached; tell the visitor to try again in an hour"}
    if status != 200 or not isinstance(data, list):
        return {"error": f"GitHub answered {status}; tell the visitor to try again later"}
    return {"repo": repo, "commits": [{"sha": c["sha"][:7], "date": c["commit"]["author"]["date"][:10],
                                       "message": c["commit"]["message"].splitlines()[0][:100]} for c in data]}


if __name__ == "__main__":
    print(json.dumps(recent_commits(sys.argv[1] if len(sys.argv) > 1 else f"{OWNER}/cpsc415-portfolio"), indent=1))
