# Intent: profile site

## Goal
A one-page personal website for Lane Faison with a chat assistant. A visitor's real question is "should we work with Lane?" The assistant answers only from a profile Lane wrote. When the profile doesn't support an answer, it says so, or says the skill is on Lane's "not yet" list, instead of guessing.

## Who it is for
Anyone deciding whether to work with Lane, treated the same: recruiters and hiring teams in consulting, banking, and private equity; founders and investors in defense technology; professors and classmates. Today they read a résumé or LinkedIn and email him their follow-up questions.

## Constraints
- **The profile is a record of shipped work.** Work in progress is labeled as learning. Skills Lane has deliberately not prioritized go in a "not yet" list, each with his reason.
- **What the profile covers:**
  - Shipped work: the senior engineering capstone (finished); summer 2026 diligence and modeling work at Renaissance Strategic Advisors; the two AI tools built there; the Hanwha Aerospace internship; a defense market-research toolkit; PowerPoint automation; interview-preparation tools; CPSC 415 labs (only weeks already shipped); presidency of the Mark Twain Center.
  - One background line: former president of Club Tennis and the ASME chapter, Entrepreneurship Club executive board.
  - Light personal detail: a semester in Rome, functional Italian, tennis.
  - Not yet: SQL; writing code by hand; front-end frameworks; cloud infrastructure and DevOps; banking-grade LBO and merger models; venture capital investment memos; accounting.
- **Never on the site or in an answer:** client or deal names and any confidential client work; post-graduation plans (for now); phone number, home address, birth date.
- **Voice:** the assistant speaks about Lane in the third person, as his site's assistant.
- **Contact:** lanefaison1@gmail.com and LinkedIn.
- **Model access:** OpenRouter, using the same key as the course labs. When deployed, the key lives in the host's secret store, never in the repository.
- **Cost:** cheap enough per answer that site traffic never threatens the lab key's spending limit.
- **Workflow:** commits go straight to `main` for this milestone.
- **Deadlines:** intent and spec October 5; plan and profile drafted October 19; chatbot answering November 2; adversarial test set run and site deployed November 30; final tag December 14.

## Not in scope
- Answering anything not about Lane's work, or acting as a general-purpose chatbot.
- Commitments on Lane's behalf: availability, start dates, compensation, relocation.
- Ranking Lane against other people or groups.
- Collecting visitor contact details, scheduling, or forms.
- A voice interface (Week 7) or tools for the chatbot (Week 8). Each gets its own intent later.
- Multiple pages, a blog, or a content-management system.

## Success looks like
- Asked about a "not yet" skill (for example, SQL), the assistant says Lane lists it as not yet and gives his reason. It never claims the skill.
- Asked about something the profile doesn't cover, it says so and points to email. It never invents an employer, number, date, or link.
- Asked a comparative, flattering, false-premise, confidential, or personal question, it handles it the way the spec's rules say, and the adversarial test set shows it.
- Asked a fair question about shipped work, it answers specifically. It does not refuse what the profile supports.
- Every project in the profile answers the four questions: what is this, why this choice, what breaks, what I learned.

## Open questions
These don't change the design. Settle them in the profile draft due October 19.
- LinkedIn URL.
- Whether the profile includes GPA.
- Dates of the Hanwha Aerospace internship.
- Which shipped work backs each defense domain area (UAS and counter-UAS, directed energy, space systems, defense acquisition), given that the deal work stays unnamed.

**Approved by:** Lane Faison, 2026-10-05
