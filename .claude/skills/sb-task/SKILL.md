---
name: sb-task
description: Second Brain — Create, update or move task cards on the board. Can extract several tasks from free text (meeting notes, a to-do list, a chat). Use when the user runs /sb-task or says "add a task", "put this on the board", "mark X as done".
argument-hint: <task | free text> [--project <Hub>] [--yes] [--scope personal|work|all]
---
# /sb-task

Task cards are notes in `Personal/15 Tasks/` and `Work/50 Tasks/` (`type: task`). A card goes to its project's area; without a project use `--scope` or the content (work → Work), and ask if unsure. The schema is in `CLAUDE.md`.

## New task(s)
1. Extract tasks from the text. Each gets an **actionable title** (verb + object, ≤ 60 characters, valid as a file name: no `\ / : * ? " < > | # ^ [ ]`).
2. Pick the project for each: `--project` if given, otherwise the most likely hub from the text and `vault_tool.py search`. Ask when unsure.
3. Check for duplicates (`vault_tool.py tasks --project <Hub>`). If a similar card exists, suggest updating it instead of creating a new one.
4. Fill `priority` and `due` only if the user said so or the text states them explicitly. Default to `status: todo`; use `doing` if the user said they've started.
5. Show a table (title · project · status · priority · due) and get approval (skip with `--yes`). Then write each card in the `Task` template layout:
   ```
   ---
   type: task
   status: todo
   priority: high        # optional
   project: "[[Hub]]"
   due: 2026-01-31       # optional
   created: <today>
   ---
   # <Title>
   ## Description
   <context from the user's text; link the source if there is one>
   ## Subtasks
   - [ ] …
   ## Notes
   ```
6. Run `vault_tool.py log task "<N> tasks: …"`.

## Update / move
"X is done", "I started X", "X is blocked because …": find the card and update `status`. For `done` add `completed: <today>`; for `doing` add `started` if missing. Write a blocking reason under "Notes". Ask if the match is ambiguous.
