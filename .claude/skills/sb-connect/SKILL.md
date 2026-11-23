---
name: sb-connect
description: Second Brain — Find meaningful connections for one note across the vault, with relation type and reason for each, and add the approved ones in both directions. Use when the user runs /sb-connect or asks "what is this note related to?".
argument-hint: <note name> [--yes]
---
# /sb-connect

1. Run `vault_tool.py context <note>` to get existing links and the outline; read the note's main sections.
2. Extract 5–10 key concepts or claims and run `vault_tool.py search` for each.
3. Judge the candidates. Keep: the same concept in another context, complementary or contradicting information, another solution to the same problem, the source of a decision, a reusable method. Drop: plain word overlap, notes that are already linked, generic MOCs.
4. Show a table (at most 8 rows):
   | Target | Relation | Reason (1 sentence) | Confidence | Where it gets written |
   Relations: complements · contradicts · example of · continues · shares a method · same decision.
5. Apply the approved ones:
   - In source notes (`type: source`), only add `> **Related:** [[X]] — reason` inside the context callout.
   - In other notes, add a bullet under "Related" / "Related concepts".
   - Add a short backlink on the other side when it's meaningful.
   - For "contradicts", add a `> [!warning]` callout in both notes.
6. Run `vault_tool.py log connect "<note>: +N links"`.
