---
name: sb-inbox
description: "Second Brain — Classify and process every note waiting in the inboxes (Personal/00 Inbox, Work/00 Inbox) with a single approval table. Use when the user runs /sb-inbox or asks to \"empty / process the inbox\"."
---
# /sb-inbox

1. List the notes in both inboxes, or only `Work/00 Inbox/` with `--scope work`, only `Personal/00 Inbox/` with `--scope personal` (skip README notes). If empty, say so and stop. Each note stays in its own area: work inbox notes go to Work folders, personal ones to Personal folders; suggest moving between areas only if the user asks.
2. For each note, do steps 1–3 of `/sb-ingest`. Keep it brief: for long notes use the title, the first sections and `context`.
3. Show one table:
   | # | Note | Proposal: type → target | Links (with reasons) | Action |
   |---|---|---|---|---|
   Actions: `move` · `merge → [[X]]` (only if the content is truly the same, with evidence) · `idea` · `delete?` (never automatic) · `wait`.
4. The user answers "all", "1,3,5" or with corrections. With `--yes`, apply everything except `delete?` and `merge`.
5. Apply the approved rows with step 5 of `/sb-ingest`. Delete only on an explicit "delete".
6. Run `vault_tool.py index` and `vault_tool.py log inbox "<N> notes processed: …"`.
7. Summarize distill candidates and anything left in the Inbox.
