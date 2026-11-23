---
name: sb-plan
description: Second Brain — Read a project/research hub and its notes and produce an actionable task plan for the board. Takes existing cards, decisions, open questions and dates into account; proposes missing tasks, order and priorities, and creates cards on approval. Use when the user runs /sb-plan or asks to "break this project into tasks / make a plan".
argument-hint: <Hub> [goal or horizon, e.g. "2 weeks"]
---
# /sb-plan

1. Run `vault_tool.py context <Hub>` and `vault_tool.py tasks --project <Hub>`. Read the hub, its accepted decisions, and the roadmap or "next step" sections of its source notes (`search` plus `Read` by line number).
2. Pin down the goal: use the user's horizon or goal if given; otherwise propose the next **concrete milestone** from the hub's goal and confirm it with one question.
3. Build the plan:
   - Existing cards: which serve the goal, which should wait in `todo`, which are too big (split them)?
   - Missing tasks: half-day to two-day pieces of work with a checkable definition of done. Put uncertainty-reducing work (feasibility, measurement) first. For research, change one variable per experiment.
   - Dependencies: what is each task waiting on?
   - **Suggested** priority (high/medium/low) with a reason. Only suggest dates when the sources contain a real deadline, and mark them "verify".
4. Show a table: `# · task · new/existing · suggested status · priority · depends on · reason`. The user picks and corrects.
5. Create or update the approved cards with the `/sb-task` rules. Record dependencies in the card's "Notes" as `Before: [[Task]]`.
6. If the plan contains a decision (e.g. which direction first), suggest `/sb-decide`. Then `log plan "<Hub>: +N tasks"`.
