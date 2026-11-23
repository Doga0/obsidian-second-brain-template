---
name: sb-standup
description: Second Brain — Progress report from the board: work completed and started recently, cards in progress and blocked, overdue and upcoming dates, progress per project, and a suggestion for today. Use when the user runs /sb-standup or asks "where do I stand?" or "what did I do this week?".
argument-hint: [days, default 7] [--project <Hub>] [--save] [--scope personal|work|all]
---
# /sb-standup

1. Run `vault_tool.py tasks --json` (with `--project` if given). Check the latest entries in `99 System/Log.md` and recently changed source notes.
2. Report (short, scannable):
   - **Done** in the last N days (by `completed`), per project
   - **In progress** (`doing`): since when (`started`), subtask progress
   - **Blocked** (`blocked`): why (from the card's Notes) and what it's waiting on
   - **Overdue / due within 7 days**: date table. Compare against deadlines written in hubs, and flag any deadline that has no card.
   - **Project progress**: `done/total` and date of last movement; call out active projects with no movement for 14+ days
   - **Suggestion for today** (max 3 cards): based on priority, dates and how much is already in progress, with reasons, labelled *AI suggestion*
3. Don't change any card's `status`. If the user asks, update cards with `/sb-task`.
4. With `--save`, write `Personal/70 Analyses/` (work scope: `Work/70 Analyses/`) `<date> - Standup.md` (`type: analysis`, `source: /sb-standup`) and `log standup`.
