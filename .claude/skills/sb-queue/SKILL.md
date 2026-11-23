---
name: sb-queue
description: Second Brain — Process the AI requests the user left from inside Obsidian: the `ai:` property on notes (connect, distill, challenge, summarize, ingest, brief) and the unchecked items in "99 System/AI Queue.md". Use when the user runs /sb-queue or asks to "process the queue".
argument-hint: [--yes] [--scope personal|work|all]
---
# /sb-queue

1. Run `vault_tool.py queue`. If it's empty, say so and stop.
2. Map each item to a command:
   | `ai:` value | Command |
   |---|---|
   | connect | /sb-connect <note> |
   | distill | /sb-distill <note> |
   | challenge | /sb-challenge <note> --save |
   | summarize | write a **What:** summary into the note's context callout (don't touch the body) |
   | ingest | /sb-ingest <note> |
   | brief | /sb-brief <note> |
   AI Queue items are free text. If one starts with an `/sb-*` command, run it; otherwise interpret the intent and show in the table which command will handle it. Treat `ai_note` as an instruction.
3. Show one plan table (item · command · expected change). Get approval unless `--yes`.
4. Run the items in order; each command's own rules apply (approval, raw content). Analyses are saved to the note's area: `Personal/70 Analyses/` (work scope: `Work/70 Analyses/`).
5. Close each finished item:
   - property: remove `ai` and `ai_note` from the note's frontmatter
   - checklist: turn the item into `- [x] … → [[result note]]`
6. Run `vault_tool.py log queue "<N> requests processed"` and list anything that couldn't be done, with the reason.
