# Project conventions

## What this repository is
My individual portfolio for CPSC 415 (Trinity College, Fall 2026): a one-page personal website with a chatbot that answers a visitor's real question, "should we work together?", only from a profile I wrote, and says "not in the profile" or "not yet" instead of guessing. The intent is in [`intent/profile-site.md`](intent/profile-site.md) and the design in [`spec.md`](spec.md).

## Commands
```
# build: not yet (plan.md step 3: python3 build.py)
# test:  not yet (plan.md steps 3-5)
# run:   not yet (plan.md step 4)
# lint:  not yet
```

## Conventions
- The profile is the single source of truth for everything the site and the chatbot say about me. Only confirmed facts go in. Shipped work goes in `experience` or `projects`; work in progress goes in `learning`; skills I've deliberately skipped go in `not_yet`.
- Every project carries the four-question annotation: what is this, why this choice, what breaks, what I learned. The draft may leave fields empty until November 2; after that, every field is filled.
- Never put client names, deal names, or confidential client work anywhere in the repository: not in the profile, commit messages, or test cases. Post-graduation plans also stay out for now.
- Contact on the site is lanefaison1@gmail.com and LinkedIn. Never a phone number, home address, birth date, or GPA.
- Local scripts (build, eval) are Python, standard library, compatible with Python 3.9. JavaScript only where the platform requires it: the Cloudflare Pages Function and the browser chat widget, with no framework. The language and model for each component are recorded in `spec.md` with alternatives named.
- Test cases use fictional company names, never real ones.
- Model calls go through OpenRouter. The key comes from the environment locally and from the host's secret store when deployed, never from code or the repository.
- File names are lowercase with hyphens or underscores.

## Working rules
- Milestone 1 (tag `intent-spec`, October 5) went straight to `main`. From milestone 2 on, every change is one feature on its own branch, merged through a pull request reviewed against `REVIEW.md`. Never commit to `main` directly.
- Ensure all commits are authored by Lane Faison.
- Course requirement: intent and spec come before code, and `plan.md` is approved before implementation starts.
- Graded course rule: one feature per branch and pull request after the first commit. The order of the branches is in `plan.md`.
- Never commit `.env` or `.claude/settings.local.json`.

## Common mistakes
Previous bugs to avoid. Add to this list as they happen.
