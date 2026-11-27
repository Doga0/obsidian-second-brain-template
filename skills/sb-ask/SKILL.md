---
name: sb-ask
description: "Second Brain — Answer a question from the vault's notes with citations; separate what the notes say from the AI's own inference and point out gaps. Optionally save the answer as an analysis note. Use when the user runs /sb-ask or asks \"according to my notes…?\" or \"where did I leave X?\"."
---
# /sb-ask

1. Context: use the L0 context from the session start (Claude Code adds it with a hook; otherwise run `vault_tool.py pack`). If the question is about a project, get that project's pack with `vault_tool.py pack --project <hub>` (goal, status, decisions, board, recent changes). Read `99 System/Index.md` only when the question spans the whole vault or search finds nothing.
2. **Depth and read budget.** Pick by the question; follow `--quick` / `--deep` if the user gave one:
   - **Quick** (one fact, one project: "what did we decide on X"): about 12 KB of reading in total.
   - **Standard** (default): about 48 KB.
   - **Deep** (vault-wide, comparisons, "why" / "over time"): about 128 KB.
   The budget counts the pack, search output and the sections you read. Keep track of the notes and line ranges you have read; do not read an unchanged section twice. If the budget is not enough, say what evidence is missing and ask before going wider.
3. **Search, then go as far as the result's confidence needs.** The first line of `vault_tool.py search "<question terms>"` gives `confidence:`
   - **strong** → read the sections of the top 1–3 results by line range; answer if the evidence is enough. No second search.
   - **medium** → read the top 3. If the evidence does not fully answer the question, search once more (synonyms, or the language the notes are written in).
   - **weak** → before reading, search once more with different words: other languages used in the vault, synonyms, technical terms the notes are likely to use. If it is still weak, check the best 2–3 results; if they do not answer the question, say "I could not find it in the vault" and list the closest notes as "possibly related". Never present a weak match as the answer.
   - **none** → try once more with different words; if still nothing, go to step 5.
   - If notes contradict each other or the question asks "why", search for the other side too, whatever the confidence (the decision's alternatives, `superseded` notes).
   Search output is not evidence: the answer rests only on the sections you read. Use `context` to follow neighbouring notes. If the question is about time ("why did we change this", "what were we using last month", "after which experiment"), look at past versions with `vault_tool.py timeline --project <hub>`, `history <note>` and `at <note> <YYYY-MM-DD>`, and give the date and version in the answer.
4. Answer in this structure:
   - **Short answer** (2–4 sentences)
   - **What the vault says**: every claim cites `[[Note]]` or `[[Note#Heading]]`. If the source is an AI chat, add "(AI chat, unverified)".
   - **Contradictions / tensions**: if notes disagree, show both.
   - **AI inference**: interpretation that isn't written in the vault, clearly labelled.
   - **Gaps**: what the vault can't answer, and which command could close the gap.
5. If the vault has no source at all, don't answer from general knowledge; say so and suggest outside research or `/sb-ingest`.
6. With `--save` or on request: save `<YYYY-MM-DD> - <short question>.md` in `Personal/70 Analyses/` (work scope: `Work/70 Analyses/`) by the question's area (`type: analysis`, `source: /sb-ask`), link it from the relevant hub's "Related" section, then run `vault_tool.py index` and `log ask "<question>"`.
