# Intent: one real tool for the chatbot

## Goal

The portfolio chatbot can answer a question the profile cannot: what I have actually committed lately. It gets one tool, `recent_commits(repo)`, which returns the last few commits of a public GitHub repository. The model asks for the tool; the server runs it and sends the result back as the next message.

## Who it is for

The same visitors as [`profile-site.md`](profile-site.md): anyone deciding whether to work with me. Today the chatbot only knows what the profile says, so "what has Lane been working on this week?" gets "not in the profile."

## Constraints

- **The model never runs anything.** Our code validates every tool request against the schema, runs it or refuses it, and returns every problem (bad arguments, an unknown tool, a repository that does not exist, GitHub's rate limit) as a result the model can read, never as an exception.
- **No claim the tool did not return.** The chatbot must not name a repository, a commit, or a date the tool did not return.
- **Which repositories:** any public repository the visitor names.
- **Step cap:** four steps per question. At the cap, the answer is the program's sentence: "I couldn't finish answering that in 4 steps."
- **An unsupported claim** is flagged by code and recorded in the trace.
- **The profile stays where it is.** The tool adds what the profile does not have; the grounding rules still apply.
- **One answer function.** The typed path and the voice path both go through the tool loop, and the trace (which tool, with what, and what came back) is returned with the answer.
- **The key stays on the server.** GitHub needs no key for public repositories.
- **Cost:** every tool call is one more chat call. The eval records the cost per question.
- **Workflow:** commits go to `main`, as the Week 8 lab assigns.
- **Deadline:** November 16, 2026, 1:30 PM.

## Not in scope

- A tool with a side effect (introductions, email). The side-effect rule is still tested with a scripted model.
- Private repositories, or a GitHub token in the deployed site.
- Deploying the tool or the hosting decision, which come before November 30.

## Success looks like

- Asked what I committed lately to my portfolio, the answer names commits the tool returned and nothing else, and the trace shows the call and the result.
- Asked about a repository I do not have, the answer says it was not found instead of describing it.
- Asked a question the profile already answers, the chatbot answers without calling the tool, or the eval records that it called it anyway.

## Open questions

None that block the spec.
