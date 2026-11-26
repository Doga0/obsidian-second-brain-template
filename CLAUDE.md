# Second Brain: AI operating contract

Shared rules for Claude Code and Codex in this vault. Codex also reads AGENTS.md. Obsidian is the interface; the AI is the librarian, the user is the curator. Human guide: `99 System/Second Brain Guide.md`.

## 0. Hard rules
1. **Protected folders are off-limits.** Folders listed under `"protected"` in `99 System/config.json` are never read, analyzed, linked, moved or written, and are excluded from search and analysis. The only exception is `vault_tool.py`, which hashes them for integrity checks.
2. **Raw content is immutable.** In `type: source` notes, never edit, shorten or delete the text below the `> [!abstract] Context` callout. Only frontmatter and that callout may change. If a note must be split, split it by line ranges, preserve every byte, and ask first.
3. **Propose, then write.** Moving, renaming, merging, deleting, changes touching more than 3 files, and changing a decision's `status` need a plan table and the user's approval first. `--yes` on a command counts as approval, except for deletion.
4. **Mark AI-generated content.** Your commentary and inferences go in a `> [!info]` / `> [!tip] AI observation` callout or a `type: analysis` note. Never write it as if it were the user's words.
5. **No fabrication.** If a date, number, citation or result isn't known, leave it blank or write "unverified". Don't add `created` to notes whose creation date is unknown.
6. **Log every write** with `python "99 System/scripts/vault_tool.py" log <command> "<what changed>"`.
7. **Keep the two areas apart.** The vault is split into `Personal/` and `Work/`. Every command takes `--scope personal|work|all`; without it, reading and analysis cover **all**, and writing goes to the area of the note/project in question (ask if unclear). Move notes between areas, or link work notes to personal ones, only when the user asks. Don't copy work content into personal notes.
8. **Every link has a reason.** Write `[[Note]] — why it's related`. Don't add links without one. Don't target headings that contain `:`, `|`, `^`, `[`, `]`; link the note and write "§N" instead.

## 1. Structure
The root holds only `Personal/`, `Work/`, the shared `99 System/`, `skills/`, tool configuration folders and `Home.md`, `Board.md`, `CLAUDE.md`, `AGENTS.md`, `README.md`.

**Personal/**
| Folder | Contents |
|---|---|
| `Personal/00 Inbox` | New, unprocessed notes (no metadata required) |
| `Personal/10 Maps` | Maps of content, named `MOC - <Area>` |
| `Personal/15 Tasks/<Project>/` | Task cards (`type: task`); each project has its own subfolder (same name as `project`), cards without a project sit in the root |
| `Personal/20 Projects/<Name>/` | Project folder + hub with the same name (`<Name>.md`), source notes, `Decision - …` notes |
| `Personal/30 Research/<Name>/` | Research folder + hub, experiment files |
| `Personal/40 Knowledge` | Evergreen concept notes (flat) |
| `Personal/50 Ideas` | Ideas not yet started |
| `Personal/60 Resources` | Reading lists, `Attachments/` |
| `Personal/70 Analyses` | AI analysis output (`type: analysis`), weekly reviews |
| `Personal/90 Archive` | Closed project/research folders (moved whole) |

**Work/** (organized around projects, clients and meetings)
| Folder | Contents |
|---|---|
| `Work/MOC - Work.md` | Entry map of the work area |
| `Work/00 Inbox` | Raw work notes, pasted chats |
| `Work/10 Projects/<Name>/` | Project hub (`<Name>.md`), design/source notes, `ADR-NNN - <short name>.md` decision records |
| `Work/20 Meetings` | `type: meeting`; named `YYYY-MM-DD - Organization - Topic` (no date if unknown) |
| `Work/30 Organizations & People` | `type: org` cards for clients, vendors and people |
| `Work/40 Systems & APIs` | External systems, APIs, reusable technical knowledge (`type: resource`) |
| `Work/50 Tasks/<Project>/` | Work task cards (in project subfolders) |
| `Work/60 Attachments` · `Work/70 Analyses` · `Work/90 Archive` | Files · work analyses · closed projects |

**99 System** (shared): Guide, Templates, `Index.md`, `Log.md`, `Health.md`, `AI Queue.md`, `config.json`, `scripts/`.

Maximum depth is `Area/Category/Project/note`. Don't create new top-level folders; propose them instead.

## 2. Metadata schema
| Field | Values |
|---|---|
| `type` | project · research · task · idea · knowledge · source · resource · moc · system · decision · analysis · meeting (work meeting) · org (organization/person card) |
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
python "99 System/scripts/vault_tool.py" import <file>          # docx/xlsx/pptx/pdf/csv -> source note in the area's inbox
python "99 System/scripts/vault_tool.py" fmtcheck [note] [--fix]   # format check; --fix applies safe fixes
python "99 System/scripts/vault_tool.py" history <note> [--since D]  # versions of a note: frontmatter/section changes (git)
python "99 System/scripts/vault_tool.py" at <note> <YYYY-MM-DD>     # the note as it was on that date
python "99 System/scripts/vault_tool.py" timeline --project <Hub>  # decisions, tasks, hub, experiments on one timeline
```
All of them take `--scope personal|work|all` (import defaults to personal; `--scope work` → `Work/00 Inbox` + `Work/60 Attachments`). `Index.md` is split into Personal / Work / Shared sections.
(On Windows, add `-X utf8` after `python` if file names have non-ASCII characters.)
MCP server: `99 System/scripts/vault_mcp.py` (same rules; every tool takes `scope`; protected folders are invisible; writes go to the project's area; the edit tools in `vault_mcp_edit.py` enforce these rules server-side, and there is no delete/merge/rename). Started with `--project "<Hub>"` (or `SB_PROJECTS`) it only sees those projects' notes and tasks; see Guide → MCP. Skills are also served as MCP prompts (and through the `vault_skill` tool).
Retrieval order: `99 System/Index.md`, then `search`, then read only the relevant line ranges. Don't read long source notes end to end.

## 4. Note types
Format settings in `99 System/config.json`: `format_check` (default false; when true the MCP tools refuse writes that break a note's format and a Claude Code hook in `.claude/settings.json` checks every Edit/Write) and `title_heading` (default true; false = the file name is the title, so notes don't repeat it as `# Title`).
Templates live in `99 System/Templates/`. Hubs share these sections: Goal · Status · Decisions (embedded Base) · Open questions · Tasks (sb-board) · Experiment log · Related.
- **Task card** (`Personal/15 Tasks/<Project>/` or `Work/50 Tasks/<Project>/<short title>.md`, by the project's area; folder root without a project. When a card's `project` changes, the board plugin moves it to the new project folder): `type: task`, `status`, `project`, optional `priority`/`due`; body: Description · Subtasks (checklist) · Notes. Hubs don't keep task checklists; they embed an `sb-board` block (`type: task`, `project: <Hub>`). The user drives the board: only change a card's `status` when asked.
- **Decision note** (Personal: `Decision - <short name>.md`; Work: `ADR-NNN - <short name>.md`; in the hub folder): `type: decision`, `project`, `status`, `origin`, `decided` (only if known); body: Decision · Rationale · Source · Alternatives.
- **Analysis note** (`Personal/70 Analyses/` or `Work/70 Analyses/<YYYY-MM-DD> - <title>.md`): `type: analysis`, `source` names the command that produced it; cite a `[[note]]` for every claim.
- **Meeting note** (Work): `type: meeting`, `project`; body: Notes · Decisions · Action items (action items can become task cards).
- **Organization card** (Work): `type: org`; body: Role · Linked notes · People.
- **Knowledge note**: created when a concept shows up in a second context; `status: seed`, at least 2 source links.

## 5. Commands
Shared workflows live in `skills/sb-*`. Claude entrypoints in `.claude/skills/sb-*` and Codex entrypoints in `.agents/skills/sb-*` load them. Commands: `/sb-ingest`, `/sb-inbox`, `/sb-ask`, `/sb-lint`, `/sb-connect`, `/sb-distill`, `/sb-review`, `/sb-new`, `/sb-decide`, `/sb-experiment`, `/sb-challenge`, `/sb-emerge`, `/sb-brief`, `/sb-queue`, `/sb-task`, `/sb-plan`, `/sb-standup`. Overview: `99 System/Second Brain Guide.md`.

## 6. Language and style
Reply in the user's language. Keep notes short and scannable: tables, bullets, link + reason.
