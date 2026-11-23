---
name: sb-distill
description: Second Brain — Distill a concept from a source note or from across the vault into an evergreen knowledge note (40 Knowledge), or update an existing seed note. Use when the user runs /sb-distill or asks to "turn this into permanent knowledge".
argument-hint: <concept | note name>
---
# /sb-distill

## If the argument is a concept
1. Use `vault_tool.py search` to find every context where it appears, including synonyms.
2. **Threshold:** without at least 2 different notes or projects, don't create a knowledge note. Leave the concept where it is and say why.
3. Update `40 Knowledge/<Concept>.md` if it exists, otherwise create it from the `Knowledge Note` template:
   - a `> [!info] Distilled by AI (<date>)` callout
   - **Essence**: 2–5 sentences; say so if you used general knowledge
   - **Where it appears in the vault**: one line per context, `[[Note]] §… — why it matters there`
   - **Related concepts** (with relation type) and **Open questions** (taken from the sources)
   - `status: seed`
4. Add a line to the relevant MOC's "Core concepts" section.

## If the argument is a note
1. Get its outline and list reusable concepts, methods and claims (at most 8), each with whether a second context exists and where.
2. The user picks; run the flow above for each pick.

## Promoting to evergreen
When the user has rewritten the note in their own words and verified it, suggest `status: evergreen`. Don't change it yourself.

Finally run `vault_tool.py index` and `log distill "<concept>"`.
