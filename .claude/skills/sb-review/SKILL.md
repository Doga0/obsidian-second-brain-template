---
name: sb-review
description: Second Brain — Weekly review. Scans active projects, upcoming and past dates, the task board, pending decisions, Inbox, AI queue and seed notes, and writes a review note with a suggested focus. Use when the user runs /sb-review or asks for a "weekly review".
argument-hint: [--no-save]
---
# /sb-review

1. Run `vault_tool.py lint`, `vault_tool.py queue` and `vault_tool.py tasks`; read `Health.md`.
2. Read every `status: active` hub (`type: project|research`). For each: last change date, open cards on the board, open questions, `proposed` decisions.
3. Scan hubs and source notes for **dates**: the next 30 days (upcoming), and dates already past that still look open (possibly missed; ask the user).
4. Find the last review in `70 Analyses/` and summarize the changes in `99 System/Log.md` since then.
5. Write `70 Analyses/<YYYY-MM-DD> - Weekly Review.md` (`type: analysis`, `source: /sb-review`):
   - **Focus this week (max 3)**: with reasons and hub links
   - **Dates**: table (date · what · source · state)
   - **Pending decisions**: list, plus a reminder that they can be approved by changing `status` in the Home table
   - **Board**: done / started / blocked this week, overdue cards, deadlines that have no card (suggest `/sb-task` or `/sb-plan`)
   - **Projects**: 1–2 lines each with status, task progress (done/total) and blockers
   - **Maintenance**: Inbox count, AI queue, seed notes, Health issues
   - **AI observation**: one cross-project pattern or risk, labelled as such
6. With `--no-save`, show it in the chat only. If saved, run `log review "<date>"`.
