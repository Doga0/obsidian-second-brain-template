---
name: sb-brief
description: "Second Brain — Current status brief for a project or research area (goal, where you left off, decisions, open questions, board, next steps, risks); with `--handoff` it writes a handoff note to the project memory at the end of a session. Use when the user runs /sb-brief, asks \"where was I on X?\", or says \"save today\" / \"write a handoff\"."
---
# /sb-brief

1. Get the project's context pack with `vault_tool.py pack --project <hub>`: goal, status, decisions (with their status), board, open questions, next steps, recent Log entries, recently changed notes and the project memory (pins, recent sessions, dead ends) in one call. Read only what the pack left out (including sections dropped for the budget) from the hub or the `Decision - *` notes, by line range. Get what changed and when with `vault_tool.py timeline --project <hub> --since <~2 weeks ago>` (decision status changes, task status, experiments).
2. Output (about 25 lines max):
   - **Goal** (1 sentence)
   - **Where you left off**: first the last memory session's "where we left off / next step"; then what changed since that date (recently changed notes, the latest decision; from the timeline). If notes changed after the memory, say the memory may be out of date.
   - **Pinned / dead ends**: the memory's pinned items and approaches not to try again, if any (briefly)
   - **Decisions**: accepted · pending
   - **Open questions** (most important first)
   - **Board**: done/total, cards in progress and blocked
   - **Next 3 steps**: picked from `todo` cards, with reasons
   - **Risks / blockers**: labelled as AI observation
   - **2–3 sections worth re-reading**: `[[Note#Heading]]`
3. Don't write anything. With `--update`, show the proposed new text for the hub's "Status" section as a diff, get approval, then apply and `log brief "<hub> status updated"`.

## `--handoff`: session handoff
When work on a project ends (when the user asks, or after you suggest it and they agree), write a handoff note for future sessions. Goal: a new session (or another agent) can read it and carry on without the conversation.
1. If there is no memory note: `vault_tool.py memory <hub> --init` (creates `Memory - <hub>.md` in the project folder; ask first).
2. `vault_tool.py memory <hub> --since`: Log entries, changed notes, task moves and stale pins since the last session.
3. Combine that with what was discussed in this session and draft an entry (about 10 lines max) at the **end** of `## Sessions`:
   ```
   ### YYYY-MM-DD — <short title> (Claude)
   - Done: … (with [[note]] citations)
   - Tried, did not work: … (leave the line out if nothing)
   - Where we left off: …
   - Next step: …
   ```
   Write only what really happened in this session; don't repeat decisions, the board or open questions (they live in the hub and the decision notes). If a decision was made, suggest a decision note (`/sb-decide`); if an open question came up, suggest adding it to the hub.
4. **Dead ends**: if there is a lasting lesson (why an approach did not work, and the evidence), suggest an item under `## Dead ends`.
5. **Pinned**: suggest deleting pins whose work is done, and pinning temporary context a long piece of work must not lose (a schema, an error detail, an interim result) as `- YYYY-MM-DD: …`. Pins show up in the L0 context of every session (after compaction too); keep them few and short.
6. Show the draft, get approval, write it, then `vault_tool.py log brief "<hub> session handoff"`. Don't touch lines the user wrote.
