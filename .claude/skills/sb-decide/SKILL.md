---
name: sb-decide
description: Second Brain — Record a decision for a project/research hub, or walk through decisions awaiting approval (status proposed) and accept/reject them. Use when the user runs /sb-decide, says they made a decision, or asks about pending decisions.
argument-hint: <hub> "<decision>" | review
---
# /sb-decide

## New decision: `/sb-decide <hub> "<decision>"`
1. Find the hub (`vault_tool.py context <hub>`). If no rationale was given, ask once.
2. Check for an existing decision on the same topic (`search` plus the `Decision - *` notes in the hub folder). Does the new one supersede it?
3. Create `<hub folder>/Decision - <short name>.md`:
   ```
   ---
   type: decision
   project: "[[<Hub>]]"
   status: accepted        # proposed if the user called it a proposal
   origin: user
   decided: <today>
   ---
   # Decision - <short name>
   ## Decision
   ## Rationale
   ## Source
   ## Alternatives / consequences
   ```
4. If an older decision is superseded, set its `status` to `superseded` (ask first: it's a status change) and link the two notes to each other.
5. If the decision answers an open question, mark it in the hub as `~~struck through~~ → [[Decision - …]]`.

## Review: `/sb-decide review`
1. List every `type: decision` note with `status: proposed`, grouped by hub.
2. For each, show a short summary and the source, then ask: accept / reject / later / change.
3. Update `status` accordingly and add `decided: <today>` to accepted ones. For rejected ones, add the user's reason to the body.

Finally run `vault_tool.py log decide "<summary>"`.
