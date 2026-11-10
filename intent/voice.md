# Intent: spoken interface

## Goal

A visitor to Lane's portfolio site can ask the chatbot a question out loud and hear the answer. The server transcribes the recording, the chatbot answers from the profile exactly as it does for typed questions, and the answer is spoken back.

## Who it is for

The same visitors as [`profile-site.md`](profile-site.md): anyone deciding whether to work with Lane. Today they would have to type, and the typed chatbot is not built yet either.

## Constraints

- **The spoken answer is the chatbot's answer.** It comes only from the profile, under the same grounding rules as a typed answer. Refusing to fabricate applies to what is said aloud exactly as to what is typed.
- **The transcript is model output and may be wrong.** The program checks what it can without knowing what the visitor meant: an empty transcript is a failure, said plainly. The rest is made visible: every turn shows "I heard: ..." above the answer. The answer goes ahead without a confirmation step.
- **Recording length:** 30 seconds, then the recording stops by itself.
- **The key stays on the server.** The browser sends only audio.
- **Nothing is kept.** A visitor's recording, transcript, answer and spoken audio exist only for the one request. They are never written to disk or logged.
- **Voice:** `en-US-Harper:MAI-Voice-2.1-Flash`. The assistant talks about Lane in the third person, and the voice must not pass for Lane's own.
- **Length:** at most three spoken sentences, no markdown.
- **Never said aloud:** client or deal names, confidential client work, post-graduation plans, phone number, home address, birth date, GPA.
- **Cost:** about half a cent per spoken question. No automatic retries.
- **Where it runs for now:** a local Python server in `voice/`, answering from `profile/profile.json` and the October 5 grounding rules. The Cloudflare chatbot in `plan.md` does not exist yet, and `voice/CHECKS.md` says so.
- **Workflow:** commits go to `main`, as the Week 7 lab assigns.
- **Deadline:** November 9, 2026, 1:30 PM.

## Not in scope

- Deploying the voice route or making the hosting decision. Both come before November 30.
- Building the typed Cloudflare chatbot.
- Conversation memory across spoken questions.
- A cloned or imitated version of Lane's voice.
- Tools for the chatbot (Week 8).

## Success looks like

- Asked what Lane's capstone team built and what his part was, the page shows what it heard with his name intact, and the answer describes the project and his role without inventing anything.
- Asked about Tableau, which the profile never mentions, the answer says the profile does not cover it and points to email.
- A silent recording gets "I didn't catch that." No answer or speech call is made.
- The browser's network log shows requests only to the site's own server and no key.

## Open questions

None that block the spec.

**Approved by:** Lane Faison, 2026-11-10
