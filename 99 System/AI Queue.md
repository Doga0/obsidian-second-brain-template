---
type: system
---
# AI Queue

> [!tip] Leave work for the AI from inside Obsidian
> Write analysis requests here as checklist items while you read, then run **`/sb-queue`** in Claude Code. Finished items get checked and linked to their result.
> Faster for a single note: add an `ai` property in its Properties panel: `connect` · `distill` · `challenge` · `summarize` · `ingest` · `brief`. Optionally add an `ai_note` with instructions. Or right-click a card on the board → *Send to AI queue*.

## Requests
- [ ] <example — delete me: /sb-challenge Website Redesign (Example) — what is the weakest assumption?>

## Requests from notes (`ai` property)
```base
filters:
  and:
    - 'file.hasProperty("ai")'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: AI requests
    order:
      - file.name
      - ai
      - ai_note
      - file.mtime
```

## Example requests
| You want | Write |
|---|---|
| What is this note related to? | `/sb-connect [[Note]]` |
| According to my notes, how did I solve X? | `/sb-ask How did I solve X? --save` |
| Weak points of this idea | `/sb-challenge [[Note]]` |
| New ideas across projects | `/sb-emerge` |
| Turn this concept into a permanent note | `/sb-distill <concept>` |
