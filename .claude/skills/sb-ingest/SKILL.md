---
name: sb-ingest
description: Second Brain — Process one Inbox note, URL or pasted text into the vault. Decide its type, place it in the right folder, add reasoned links, update the hub/MOC. Use when the user runs /sb-ingest or asks to "add/process this into the vault".
argument-hint: <Inbox note | URL | text> [--yes] [--scope personal|work|all]
---
# /sb-ingest

Follow `CLAUDE.md` (protected folders, immutable raw content, propose then write).

## Input
- **Inbox note** (`Personal/00 Inbox/…` or `Work/00 Inbox/…`): process it within its area.
- **URL**: read it with WebFetch. Don't copy the full text. Create a note in the area's inbox (`--scope work` → `Work/00 Inbox/`, otherwise `Personal/00 Inbox/`) from the `Source Note` template containing the link, a structured summary in your own words, and at most a few short quotes. Then process that note.
- **Pasted text / AI chat**: put it **unchanged** under "Raw content" in a `Source Note`, then process it.

## Steps
1. Read `99 System/Index.md`. Run `vault_tool.py search` with the note's key terms (2–3 queries, including synonyms).
2. **Classify:** `type`, target folder (existing project/research, new one, idea, knowledge?), `project`, `topics`. If unsure, offer the two most likely options.
3. **Link candidates:** for each, give the relation (complements / contradicts / example of / continues) and a one-sentence reason. Drop weak ones.
4. **Show a plan table:**
   | What | Value |
   |---|---|
   | Target path | … |
   | Frontmatter | … |
   | Context callout | **What:** … / **Related:** … |
   | Line added to hub | … |
   | Line added to MOC | (only for a new hub or knowledge note) |
   | Distill candidates | concepts now seen in a second context |
   Ask for approval unless `--yes`.
5. **Apply:** move the file (stop and ask if the name already exists at the target), add frontmatter and a `> [!abstract] Context` callout (never touch the body), and add `[[Note]] — reason` to the right hub section.
6. If a concept now appears in a second context, suggest `/sb-distill <concept>`.
7. Run `vault_tool.py index` and `vault_tool.py log ingest "<note> → <target>; +N links"`.

## Output
A short summary: where it went, which links were added, and the suggested next command.
