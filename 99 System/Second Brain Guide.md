---
type: system
---
# Second Brain Guide

> [!info] This guide belongs to you: change it as you use the system. If the system doesn't fit you, change the system, not yourself.

## What this is
An Obsidian vault structured as a "second brain", plus an AI layer that runs in **Claude Code or Codex**:
- **Obsidian** is where you write, read, browse and approve: notes, hubs, maps, a kanban **board**, and dashboards built with Bases.
- **Claude Code and Codex** provide the AI layer: `/sb-*` commands file new material, find connections, answer questions from your notes, plan tasks and write reviews. They follow the rules in `CLAUDE.md`.
- **`vault_tool.py`** is a small dependency-free Python script the commands use for search, link checks, the index and task reports.

It follows Karpathy's *LLM Wiki* pattern: raw sources stay untouched, the AI maintains the linked wiki around them, and one schema file (`CLAUDE.md`) is the contract.

## Structure
The vault has two areas with different layouts; the shared system sits at the root.

**Personal/**
| Folder | What goes in | Rule |
|---|---|---|
| `00 Inbox` | Every new personal note | Write without thinking; empty it weekly |
| `10 Maps` | Maps of content (MOCs) | One per area; curated by hand |
| `15 Tasks` | Task cards (board) | `15 Tasks/<Project>/<card>`; the folder comes from `project`, cards without a project sit in the root |
| `20 Projects` | Work with an outcome and an end | **One folder + a hub with the same name** per project |
| `30 Research` | Academic or technical research, experiments | Same layout as projects; hub has an Experiment log |
| `40 Knowledge` | Evergreen concept notes | **Flat**, no subfolders |
| `50 Ideas` | Ideas you haven't started | Move to Research/Projects when you start |
| `60 Resources` | Reading list, `Attachments/` | |
| `70 Analyses` | AI analyses, weekly reviews | Written by commands; you read and link them |
| `90 Archive` | Finished or dropped project folders | Move the whole folder |

**Work/** (organized around projects, clients and meetings; entry point: [[MOC - Work]])
| Folder | What goes in | Rule |
|---|---|---|
| `00 Inbox` | Raw work notes, pasted chats | Process with `/sb-inbox --scope work` |
| `10 Projects/<Name>/` | Project hub, design notes, decisions | Decisions are numbered `ADR-001 - …` |
| `20 Meetings` | Meeting notes (`Meeting` template) | Name: `YYYY-MM-DD - Organization - Topic`; action items can become task cards |
| `30 Organizations & People` | Client, vendor and people cards (`Org` template) | Meetings and projects link here |
| `40 Systems & APIs` | External systems, APIs, reusable technical knowledge | The "knowledge" layer of work |
| `50 Tasks` | Work task cards | `50 Tasks/<Project>/<card>`; the board's *Work* area |
| `60 Attachments` · `70 Analyses` · `90 Archive` | Files · work analyses · closed projects | |

**At the root (shared):** `99 System` (this guide, templates, `Index`, `Log`, `Health`, `AI Queue`, `config.json`, `scripts/`), [[Home]], [[Board]], `CLAUDE.md`, `AGENTS.md` and shared `skills/`.

**Choosing an area (scope):** the *All areas / Personal / Work* menu on boards and the calendar; `--scope personal|work|all` in AI commands; `scope` in MCP tools. The default is both. New cards go to their project's area; new notes go to the open note's area.

**Project or research?** If it has a question and experiments → Research. If it has a deliverable (product, code, application) → Project. Unsure? Use Projects: as long as the links are right, nothing gets lost.

## Metadata (minimal schema)
| Field | Values | When |
|---|---|---|
| `type` | `project`, `research`, `task`, `idea`, `knowledge`, `source`, `resource`, `moc`, `system`, `decision`, `analysis` | When a note leaves the Inbox |
| `status` | task: `todo` · `doing` · `done` · project/research: `active` · `paused` · `done` · `archived` · knowledge: `seed` → `evergreen` · idea: `idea` · `exploring` · `promoted` · `dropped` · decision: `proposed` · `accepted` · `rejected` · `superseded` | Hubs, tasks, knowledge, decisions |
| `project` | `"[[Hub name]]"` | Notes and tasks that belong to a project |
| `topics` | list of `"[[MOC - …]]"` | Optional; creates backlinks on the MOC |
| `priority`, `due` | `high` · `medium` · `low`; `YYYY-MM-DD` | Tasks |
| `origin`, `decided` | `user` / `ai-suggestion`; date | Decisions |
| `ai`, `ai_note` | `connect` · `distill` · `challenge` · `summarize` · `ingest` · `brief` + instruction | When you want the AI to do something; removed when done |
| `source` | `AI chat (ChatGPT)`, a paper citation… | Source notes |
| `aliases`, `split: no` | old/alternative names; "long but single-topic" | When needed |

**No tags.** Topic = link/`topics`, kind = `type`, state = `status`, place = folder. Add a tag only for a need none of these cover.

## Adding a note
1. `Ctrl/Cmd+N`: the note lands in `Personal/00 Inbox`; for a work note use `Ctrl/Cmd+O` → `+ title` → *Work* (`Work/00 Inbox`). A title and content are enough.
2. Saving an AI chat or an article? Use the `Source Note` template and paste the text under "Raw content" untouched. Keep your own takeaways in their own section.
3. If a conversation grows past ~1000 lines, start the next question as a new note and link them in sequence from the hub.
4. With AI: `/sb-ingest <note or URL>` files and links it for you.

## Organizing a project
1. `/sb-new project <Name>` (or create `Personal/20 Projects/<Name>/<Name>.md`, or `Work/10 Projects/<Name>/<Name>.md` for work, from the `Project Hub` template).
2. Fill in **Goal** and **Status**. Put related notes in the folder and give each a line in the hub: *what it is and why it matters*.
3. Tasks are cards (`/sb-plan <Name>` proposes a plan); the hub's Tasks board shows only this project's cards.
4. Every decision is its own note (`Decision - <short name>.md`, via `/sb-decide` or the `Decision` template). The hub's Decisions table lists them automatically. Decisions the AI suggested stay `proposed` until you approve them on Home. Months later this tells you whether *you* decided something or a model suggested it.

## Organizing research
1. `/sb-new research <Name>`; write the **research question** in one sentence.
2. Sources (papers, AI chats, raw results) go in the folder, each with a line in the hub.
3. Each experiment is a row in the **Experiment log** (`/sb-experiment`). Rule: *change one thing at a time*.
4. Keep raw results (logs, tables) in the same folder and link them from the hub.
5. A verified finding that's useful in more than one context becomes a knowledge note (`/sb-distill`).

## Linking
- **Link + reason:** `[[Note]] — why is it related?` One sentence is enough. No reason, no link.
- **Section links:** `[[Note#Heading]]` or with an alias `[[Note#Heading|short name]]`. In tables write `\|` instead of `|`.
- **Name the relation:** *complements*, *contradicts*, *example of*, *replaces*. Mark contradictions with a `> [!warning]` callout.
- **When does a knowledge note get created?** When a concept shows up in a **second** context. If it appears in one place only, it stays in that project's note.
- **MOCs:** when you create a hub or knowledge note, add a line to the relevant MOC. MOCs are curated, not automatic.
- **Graph view:** `topics` links make MOCs act as cluster centers. For one note's neighbourhood use *Local graph*.

## Finding things
- `Ctrl/Cmd+O` quick menu: find any note (aliases included), create notes/tasks, run commands; classic Quick switcher on `Ctrl/Cmd+Shift+O` · `Ctrl/Cmd+Shift+F` search (`path:"20 Projects" keyword`, `[status:active]`)
- [[Home]]: tables for pending decisions, active projects, AI queue, Inbox, analyses, knowledge.
- Natural language: `/sb-ask <question>` in Claude Code, with cited answers. [[Index]] is a one-line catalog of every note.
- Hubs are the entry point to every project: "what did I decide here?" → the hub's Decisions table.

## Board
Trello/Jira-style management through the bundled **Second Brain Board** plugin (`.obsidian/plugins/sb-board/`). Every card is a real note and its column is the note's `status`, so the board, Bases tables, hubs and AI commands all see the same data.

**Enable it once:** *Settings → Community plugins → Turn on community plugins* → enable **Second Brain Board**. (When Obsidian asks whether to trust this vault's plugins, choose trust.) It downloads nothing; the code is a single file in this vault. While disabled, boards show as plain code blocks and no data is lost.

| Where | Shows |
|---|---|
| [[Board]] | All tasks (filterable) · projects with progress bars · idea pipeline · decisions · due-date table |
| [[Home]] | Current tasks |
| Each hub's Tasks section | That project's cards only |

- **Move:** drag and drop, or right-click → *Move →*. Moving to `doing` writes `started`, moving to `done` writes `completed`; progress reports use these dates.
- **Add:** the column's `+`, or `Ctrl/Cmd+P` → *Quick add task* (the open note's project is preselected). Cards go to the project's area and folder: `Personal/15 Tasks/<Project>/` or `Work/50 Tasks/<Project>/`. Change a card's `project` and it moves to the new project folder within a few seconds; to fix by hand, `Ctrl/Cmd+P` → *Sort task cards into project folders*.
- **Card details:** click the card. Description, **subtasks** (a checklist, shown as `☑ 2/5` on the card), notes. Hover for a preview.
- **Priority / due date:** right-click → *Priority*; set `due` in the card's Properties. Overdue dates turn red, dates within 3 days orange.
- **Send to AI:** right-click → *Send to AI queue: brief / challenge / connect…*, then `/sb-queue`.

**Make your own board:** put this block in any note:
````
```sb-board
type: task                 # task | project, research | idea | decision
project: My Project        # optional: one project
columns: todo, doing, done # optional: columns
wip: doing=2               # optional: WIP limit
hide-done-after: 14        # optional: hide old completed cards
title: This week           # optional
filters: false             # hide the filter bar
```
````

## AI commands
**Run them:** open this vault folder in Claude Code (the desktop app's Code tab, or run `claude` in a terminal inside the folder) and type `/sb-`; the commands are listed. The shared definitions live in `skills/sb-*/SKILL.md`; Claude and Codex entrypoints live in `.claude/skills/` and `.agents/skills/`. In Codex, invoke `$sb-ask` or describe the task naturally. Edit the shared skill to change the workflow.

| Pattern | In this vault |
|---|---|
| raw sources (immutable) | `type: source` notes; the text under the context callout is never changed |
| wiki (AI-maintained pages) | hubs, `40 Knowledge`, MOCs, `70 Analyses` |
| schema / contract | `CLAUDE.md` |
| index / log | [[Index]] (generated) and [[Log]] (every command appends) |
| ingest · query · lint | `/sb-ingest` · `/sb-ask` · `/sb-lint`, plus 14 more (list on [[Home]]) |

Every command follows the same safety rules:
- Moving, merging, bulk changes and decision status changes: **plan table first, then approval**. Pass `--yes` to approve up front (never for deletion).
- Raw source text isn't touched; AI commentary lives in labelled callouts or `70 Analyses` notes.
- Every change is written to [[Log]].

**Leaving work for the AI from Obsidian:**
- While reading a note, add `ai: challenge` (or `connect`, `distill`, `summarize`, `ingest`, `brief`) in Properties, optionally with an `ai_note`. It shows up in Home's *AI queue* table.
- Write free-form requests in [[AI Queue]].
- `/sb-queue` in Claude Code processes all of them, clears the `ai` field and checks off the items with a link to the result.

**The helper script** (Python 3.8+, no dependencies) can be run by hand too:
- `python "99 System/scripts/vault_tool.py" search "keyword"`: section-level, accent-insensitive search
- `… context "Note name"`: outline, links and backlinks
- `… tasks`: board as text, with last-7-days activity
- `… lint` / `… index`: refresh Health and Index

## Protected folders
Areas separate personal and work notes, but the AI can still read both. To keep a folder (e.g. confidential client notes) completely out of the AI's reach, add it to `99 System/config.json`:
```json
{ "protected": ["Work/Confidential"], "wip_limit": null }
```
Commands and the board plugin will never read, link or write it, and `lint` verifies with file hashes that nothing changed (run `python "99 System/scripts/vault_tool.py" protected-baseline` once after adding it). For extra safety, also exclude it from Git in `.gitignore`. `wip_limit` (e.g. `3`) makes `lint` warn when too many tasks are in progress.

## Version control
The vault is a Git repository (setup creates it) and the bundled **Git** plugin (by Vinzent03) records history automatically.
- **Local only (default):** a commit every 10 minutes. Nothing leaves your computer.
- **With your own private repo:** run setup with `-Remote <url>` (Windows) / `--remote <url>` (macOS/Linux). It pushes the vault and switches the plugin to commit + push every 10 minutes and pull on startup.
- **Old versions:** `Ctrl/Cmd+P` → *Git: Open file history*, or the *Source Control* view. Manual backup: *Git: Commit-and-sync*.
- **Settings:** *Settings → Git* (interval, commit message, pull/push).
- `.gitattributes` keeps every file byte-identical across machines; `.gitignore` excludes device-specific state. **Add your protected folders to `.gitignore` too** if they shouldn't be versioned.
- Use a **private** repository for your personal vault. Don't want Git at all? Disable the Git plugin in *Settings → Community plugins* and run setup with `-NoGit` / `--no-git`.

## Writing, navigation and tracking tools
All bundled and enabled. Community plugins come from the official Obsidian plugin list, unmodified, with their licenses in their folders.

| Need | How | Plugin |
|---|---|---|
| **Command menu** | Type `/` at the start of a line: headings, tables, callouts, code blocks, templates, TOC… every command is searchable | Core *Slash commands* |
| **Autocomplete** | Suggestions from the words and note names in your vault while you type | *Various Complements* |
| **Formatting toolbar** | Bold, headings, lists, colors, tables… as buttons above the editor | *Editing Toolbar* |
| **Table of contents** | `/` → *Insert table of contents*; a live block that updates as the note changes | *Automatic Table of Contents* |
| **LaTeX** | `$x^2$` inline, `$$…$$` block (built-in MathJax). Shortcuts: in math, `//` → `\frac{}{}`, `sr` → `^2`; in text, `mk ` → inline math, `dm ` → block | *Latex Suite* |
| **Quick menu (navigator)** | `Ctrl/Cmd+O`: find notes, PDFs and files (aliases included). `! title` → task, `+ title` → inbox note, `? title` → idea (each offered for Personal and Work), `>` → commands, `Ctrl/Cmd+Enter` opens in a new tab. The classic Quick switcher moved to `Ctrl/Cmd+Shift+O` | *Second Brain Tools* |
| **Calendar** | [[Board#Calendar]]: completed, started and due tasks plus decisions in a month view, with an area menu (or `scope: work` in the block) | *Second Brain Tools* (`sb-calendar` block) |
| **Activity heatmap** | [[Home#Activity]]: GitHub-style; tasks + notes + git commits per day, streak stats, area menu; click a day to see its work | *Second Brain Tools* (`sb-heatmap` block) |
| **Reminders** | Obsidian + system notification for tasks whose `due` is today/tomorrow or past (once a day per task); ⏰ counter in the status bar. Settings (including which area): *Settings → Second Brain Tools* | *Second Brain Tools* |
| **Folder icons** | Numbered folders come with icons; right-click a folder → *Change icon* | *Iconize* |
| **Working on PDFs** | Select text in a PDF → pick a color to highlight; copy/drag the selection into a note to get a link back to that spot. PDF++ can also write annotations into the PDF file (off by default) | *PDF++* |
| **Word (.docx)** | Preview inside Obsidian and embed with `![[file.docx]]`; the *Convert* button creates a Markdown copy (images go to an `Attachments/` folder next to the file, the original is kept) | *Docxer* |
| **Excel (.xlsx) / CSV** | Opens inside Obsidian as a table with sheet tabs | *Second Brain Tools* |
| **Import** | `Ctrl/Cmd+P` → *Import file* (docx, xlsx, pptx, pdf, csv) or right-click a file → *Convert to Markdown note*. The original goes to the area's attachments (`Personal/60 Resources/Attachments` or `Work/60 Attachments`), the text to that area's inbox as a `type: source` note (then `/sb-ingest`). From a terminal: `vault_tool.py import <file>` | *Second Brain Tools* + `vault_tool.py` |

Second Brain Tools is desktop-only (it uses Node for the spreadsheet view, git activity and import). The calendar, heatmap, reminders and import skip protected folders and `99 System/` and can be limited to one area; the quick menu lists every file, for navigation only, and marks work files.

**MCP (vault access for AI apps).** `99 System/scripts/vault_mcp.py` is a small MCP server (Python standard library only, stdio). The client starts it when needed.
- Tools: `vault_index`, `vault_search`, `vault_read_note`, `vault_note_context`, `vault_list_tasks`, `vault_list_notes`, plus `vault_capture` (Inbox) and `vault_create_task`, which only **create** files. It can't change, move or delete existing notes; every write is logged in [[Log]].
- Every tool takes `scope` (personal / work / all). Protected folders, `.obsidian`, `.git` and `.claude` are invisible: not listed, searched or read. Creating notes and tasks writes to the project's area (else the `scope`).
- **Claude Code:** defined in `.mcp.json` at the vault root; approve the `second-brain` server the first time.
- **Claude Desktop:** *Settings → Developer → Edit Config*, add the server below (use the full path to your vault), then restart Claude Desktop:
  ```json
  {"mcpServers": {"second-brain": {"command": "python", "args": ["-X", "utf8", "<path to vault>/99 System/scripts/vault_mcp.py"]}}}
  ```
  On macOS/Linux use `python3`; if Claude can't find Python, put the interpreter's full path in `command`.
- **Skills over MCP.** The server also offers the `skills/sb-*` workflows as MCP *prompts*, so an agent without access to the vault files can still use `/sb-ask`, `/sb-brief` and the rest. In Claude Code: `/mcp__second-brain__sb-ask <question>`; in Claude Desktop pick them from the `+` menu under the server. Clients without prompt support use the `vault_skill` tool (no `name` = list).
  - Each prompt starts with a short section that maps the skill's file and CLI steps to the MCP tools, plus the "Hard rules" section of CLAUDE.md.
  - Limit: MCP can't change existing notes. Skills that edit notes (connect, distill, decide, experiment, inbox, ingest, lint, new, queue) do the analysis and present the change as a plan ready to apply; it is applied in Obsidian or by an agent with file access.
- **Project lock (give an agent only some projects).** Start the server with `--project "<Hub name>"` (repeat it for several, or set `SB_PROJECTS="A;B"`). The agent then doesn't waste context on, or get confused by, other projects:
  - Visible: the project's hub folder, its task folder (`15 Tasks/<Project>`, `50 Tasks/<Project>`) and notes whose `project:` is that hub. Add `--include-linked` to also see notes the hub links to directly that belong to no other project (e.g. knowledge notes; MOCs and analyses stay out).
  - `vault_index` lists only those notes; `vault_search`, `vault_list_*` and `vault_note_context` are filtered; any other note is "not found"; `vault_create_task` only creates cards for the locked projects.
  - Example server entry: `"sb-website": {"command": "python", "args": ["-X", "utf8", "99 System/scripts/vault_mcp.py", "--project", "Website Redesign"]}`.
  - **Full isolation in Claude Code:** the lock only covers MCP; Claude Code's own file tools can still read the vault. Start the locked agent with only that server and those tools off:
    `claude --mcp-config sb-website.json --strict-mcp-config --disallowedTools "Read,Grep,Glob,Bash,Edit,Write"`

**Deliberate choices:**
- *Editing Toolbar* instead of *Markdown Formatting Assistant*: same job (formatting buttons), more widely used and maintained.
- No auto-formatter (*Linter*): it rewrites notes on save and could change raw source notes (`type: source`).
- Latex Suite's `mk` shortcut only fires as a separate word, so it doesn't trigger inside ordinary words.

## Weekly maintenance (15 min)
1. `/sb-review`: weekly review note with focus, dates, pending decisions, maintenance list.
2. `/sb-inbox`: empty the Inbox with one approval table.
3. On Home, go through **Decisions awaiting approval** and update their `status`.
4. `/sb-queue`: run the requests you left during the week.
5. Rewrite one `seed` note in your own words → `evergreen`.
6. Monthly: `/sb-lint --deep` (contradictions, outdated claims) and `/sb-emerge`.

## Keeping it healthy long-term
- **Before adding a folder**, check whether `type`, `project` or a MOC already does the job. Maximum depth: `Category/Project/note`.
- **Move and rename files inside Obsidian** (*Automatically update internal links* is on); moving them outside Obsidian breaks links.
- **AI output is a source, not knowledge.** Version numbers, dates, prices and citations from AI chats shouldn't enter knowledge notes unverified.
- **Plugins:** the bundled set is listed in [[#Writing, navigation and tracking tools]]. The core system (notes, Bases, templates, AI commands) also works without them. Before adding one: is it in the official list, maintained, and does it stay out of protected folders? Optional extras: *Homepage* (open Home at startup), the official *Web Clipper* (clip articles into the Inbox, then `/sb-ingest`). Dataview isn't needed; Bases covers it.
- **Example notes:** everything marked `example: true` can be removed with `python "99 System/scripts/vault_tool.py" clean-examples --yes`.
