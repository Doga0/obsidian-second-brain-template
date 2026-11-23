# Second Brain: AI operating contract

Rules every AI agent (Claude Code) follows in this vault. Obsidian is the interface; the AI is the librarian, the user is the curator. Human guide: `99 System/Second Brain Guide.md`.

## 0. Hard rules
1. **Protected folders are off-limits.** Folders listed under `"protected"` in `99 System/config.json` are never read, analyzed, linked, moved or written, and are excluded from search and analysis. The only exception is `vault_tool.py`, which hashes them for integrity checks.
2. **Raw content is immutable.** In `type: source` notes, never edit, shorten or delete the text below the `> [!abstract] Context` callout. Only frontmatter and that callout may change. If a note must be split, split it by line ranges, preserve every byte, and ask first.
3. **Propose, then write.** Moving, renaming, merging, deleting, changes touching more than 3 files, and changing a decision's `status` need a plan table and the user's approval first. `--yes` on a command counts as approval, except for deletion.
4. **Mark AI-generated content.** Your commentary and inferences go in a `> [!info]` / `> [!tip] AI observation` callout or a `type: analysis` note. Never write it as if it were the user's words.
5. **No fabrication.** If a date, number, citation or result isn't known, leave it blank or write "unverified". Don't add `created` to notes whose creation date is unknown.
6. **Log every write** with `python "99 System/scripts/vault_tool.py" log <command> "<what changed>"`.
7. **Every link has a reason.** Write `[[Note]] — why it's related`. Don't add links without one. Don't target headings that contain `:`, `|`, `^`, `[`, `]`; link the note and write "§N" instead.

## 1. Structure
| Folder | Contents |
|---|---|
| `00 Inbox` | New, unprocessed notes (no metadata required) |
| `10 Maps` | Maps of content, named `MOC - <Area>` |
| `15 Tasks` | Task cards (`type: task`), flat; linked to a project via `project`. Board: `Board.md` |
| `20 Projects/<Name>/` | Project folder + hub with the same name (`<Name>.md`), source notes, `Decision - …` notes |
| `30 Research/<Name>/` | Research folder + hub, experiment files |
| `40 Knowledge` | Evergreen concept notes (flat) |
| `50 Ideas` | Ideas not yet started |
| `60 Resources` | Reading lists, `Attachments/` |
| `70 Analyses` | AI analysis output (`type: analysis`), weekly reviews |
| `90 Archive` | Closed project/research folders (moved whole) |
| `99 System` | Guide, Templates, `Index.md`, `Log.md`, `Health.md`, `AI Queue.md`, `config.json`, `scripts/` |

Maximum depth is `Category/Project/note`. Don't create new top-level folders; propose them instead.

## 2. Metadata schema
| Field | Values |
|---|---|
| `type` | project · research · task · idea · knowledge · source · resource · moc · system · decision · analysis |
| `status` | task: todo · doing · done (board columns To Do / In Progress / Done; `backlog` and `blocked` are valid and show in an "Other" column) — project/research: active · paused · done · archived — knowledge: seed · evergreen — idea: idea · exploring · promoted · dropped — decision: proposed · accepted · rejected · superseded |
| `project` | `"[[Hub]]"` for notes, tasks and decisions that belong to a project |
| `topics` | list of `"[[MOC - …]]"` |
| `priority` | task: high · medium · low (empty = unassigned; don't invent) |
| `due` | task: `YYYY-MM-DD`, only if the user gave it or a source states it explicitly |
| `started`, `completed` | task: written automatically by the board plugin |
| `source` | where the content came from (e.g. `AI chat (ChatGPT)`, a paper citation) |
| `origin` | decision: `user` · `ai-suggestion` |
| `ai`, `ai_note` | a request for the AI: connect · distill · challenge · summarize · ingest · brief (+ instruction). Remove when done |
| `example` | `true` on the template's sample notes (removed by `clean-examples`) |
| `aliases`, `summary`, `split: no` | optional |

No tags. Don't invent fields; propose them.

## 3. Tools: use these before reading files
```
python "99 System/scripts/vault_tool.py" search <query> [--k N]   # section-level ranked search
python "99 System/scripts/vault_tool.py" context <note>           # outline, links, backlinks
python "99 System/scripts/vault_tool.py" tasks [--project X] [--json]
python "99 System/scripts/vault_tool.py" lint                     # writes Health.md
python "99 System/scripts/vault_tool.py" index                    # writes Index.md
python "99 System/scripts/vault_tool.py" queue                    # AI queue
python "99 System/scripts/vault_tool.py" log <op> "<text>"
```
(On Windows, add `-X utf8` after `python` if file names have non-ASCII characters.)
Retrieval order: `99 System/Index.md`, then `search`, then `Read` only the relevant line ranges. Don't read long source notes end to end.

## 4. Note types
Templates live in `99 System/Templates/`. Hubs share these sections: Goal · Status · Decisions (embedded Base) · Open questions · Tasks (sb-board) · Experiment log · Related.
- **Task card** (`15 Tasks/<short title>.md`): `type: task`, `status`, `project`, optional `priority`/`due`; body: Description · Subtasks (checklist) · Notes. Hubs don't keep task checklists; they embed an `sb-board` block (`type: task`, `project: <Hub>`). The user drives the board: only change a card's `status` when asked.
- **Decision note** (`Decision - <short name>.md`, in the hub folder): `type: decision`, `project`, `status`, `origin`, `decided` (only if known); body: Decision · Rationale · Source · Alternatives.
- **Analysis note** (`70 Analyses/<YYYY-MM-DD> - <title>.md`): `type: analysis`, `source` names the command that produced it; cite a `[[note]]` for every claim.
- **Knowledge note**: created when a concept shows up in a second context; `status: seed`, at least 2 source links.

## 5. Commands
`.claude/skills/sb-*`: `/sb-ingest`, `/sb-inbox`, `/sb-ask`, `/sb-lint`, `/sb-connect`, `/sb-distill`, `/sb-review`, `/sb-new`, `/sb-decide`, `/sb-experiment`, `/sb-challenge`, `/sb-emerge`, `/sb-brief`, `/sb-queue`, `/sb-task`, `/sb-plan`, `/sb-standup`. Overview: `99 System/Second Brain Guide.md`.

## 6. Language and style
Reply in the user's language. Keep notes short and scannable: tables, bullets, link + reason.
