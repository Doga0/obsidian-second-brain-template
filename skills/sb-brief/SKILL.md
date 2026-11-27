---
name: sb-brief
description: "Second Brain — Current status brief for a project or research area (goal, where you left off, decisions, open questions, board, next steps, risks), for loading context when returning to it. Use when the user runs /sb-brief or asks \"where was I on X?\"."
---
# /sb-brief

1. Get the project's context pack with `vault_tool.py pack --project <hub>`: goal, status, decisions (with their status), board, open questions, next steps, recent Log entries and recently changed notes in one call. Read only what the pack left out (including sections dropped for the budget) from the hub or the `Decision - *` notes, by line range. Get what changed and when with `vault_tool.py timeline --project <hub> --since <~2 weeks ago>` (decision status changes, task status, experiments).
2. Output (about 25 lines max):
   - **Goal** (1 sentence)
   - **Where you left off**: recently changed notes with dates, the latest decision (from the timeline: what changed, when)
   - **Decisions**: accepted · pending
   - **Open questions** (most important first)
   - **Board**: done/total, cards in progress and blocked
   - **Next 3 steps**: picked from `todo` cards, with reasons
   - **Risks / blockers**: labelled as AI observation
   - **2–3 sections worth re-reading**: `[[Note#Heading]]`
3. Don't write anything. With `--update`, show the proposed new text for the hub's "Status" section as a diff, get approval, then apply and `log brief "<hub> status updated"`.
