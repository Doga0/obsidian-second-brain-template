---
name: sb-challenge
description: Second Brain — Red-team an idea, design or decision. Surface assumptions, weak points, counter-evidence in the vault and the cheapest test that could prove it wrong. Use when the user runs /sb-challenge or asks "what's wrong with this idea?".
argument-hint: <note | idea text> [--save]
---
# /sb-challenge

1. Read the target (for a note: main sections plus `context`). Restate the core claim in one sentence; the user corrects it if needed.
2. Use `vault_tool.py search` to find other notes on the same topic: supporting, contradicting, or ones that discussed the same risk before.
3. Output:
   - **Hidden assumptions** (the 3–5 most critical), each with why it matters
   - **Weakest point**: exactly one, with the reasoning
   - **Counter-evidence / tension in the vault**: with `[[Note]]` citations, or "none in the vault"
   - **Alternative explanation / competing approach**
   - **Cheapest falsification test**: a check doable in a day or one experiment
   - **The question nobody asked**
   Be tough but fair. Don't soften it with praise, and don't invent risks either.
4. On request, add the open questions to the hub's "Open questions" section; with `--save`, save to `Personal/70 Analyses/` (work scope: `Work/70 Analyses/`) `<date> - Challenge - <topic>.md`. Then `log challenge "<topic>"`.
