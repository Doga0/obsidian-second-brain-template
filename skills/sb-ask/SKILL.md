---
name: sb-ask
description: "Second Brain — Answer a question from the vault's notes with citations; separate what the notes say from the AI's own inference and point out gaps. Optionally save the answer as an analysis note. Use when the user runs /sb-ask or asks \"according to my notes…?\" or \"where did I leave X?\"."
---
# /sb-ask

1. Context: use the L0 context from the session start (Claude Code adds it with a hook; otherwise run `vault_tool.py pack`). If the question is about a project, get that project's pack with `vault_tool.py pack --project <hub>` (goal, status, decisions, board, recent changes). Read `99 System/Index.md` only when the question spans the whole vault or search finds nothing.
2. Run at least two `vault_tool.py search` queries (different wordings, synonyms, other languages used in the vault). Read the relevant sections by line number (a file reading tool with offset/limit). Use `context` to follow neighbouring notes. If the question is about time ("why did we change this", "what were we using last month", "after which experiment"), look at past versions with `vault_tool.py timeline --project <hub>`, `history <note>` and `at <note> <YYYY-MM-DD>`, and give the date and version in the answer.
3. Answer in this structure:
   - **Short answer** (2–4 sentences)
   - **What the vault says**: every claim cites `[[Note]]` or `[[Note#Heading]]`. If the source is an AI chat, add "(AI chat, unverified)".
   - **Contradictions / tensions**: if notes disagree, show both.
   - **AI inference**: interpretation that isn't written in the vault, clearly labelled.
   - **Gaps**: what the vault can't answer, and which command could close the gap.
4. If the vault has no source at all, don't answer from general knowledge; say so and suggest outside research or `/sb-ingest`.
5. With `--save` or on request: save `<YYYY-MM-DD> - <short question>.md` in `Personal/70 Analyses/` (work scope: `Work/70 Analyses/`) by the question's area (`type: analysis`, `source: /sb-ask`), link it from the relevant hub's "Related" section, then run `vault_tool.py index` and `log ask "<question>"`.
