---
type: system
---
# Obsidian Second Brain Template

A ready-to-use Obsidian vault for running a **second brain**: projects, research, knowledge, ideas and tasks, with a **kanban board** and a shared **AI skill layer** for [Claude Code](https://claude.com/claude-code) and Codex.

- 🗂 **Two areas, Personal and Work:** a second-brain layout (Inbox → Projects / Research / Knowledge / Ideas → Archive) for personal notes, and a project / meeting / client layout for work; every view and command can show one or both
- 📋 **Kanban board:** Trello/Jira-style boards where every card is a real note (To Do / In Progress / Done), with drag and drop, priorities, due dates, subtasks and per-project progress bars
- ✅ **Decision log:** decisions are notes you approve with one click; AI-suggested decisions stay "proposed" until you accept them
- 🤖 **17 AI commands** (`/sb-ingest`, `/sb-ask`, `/sb-plan`, `/sb-review`, `/sb-challenge`, …) following the LLM-Wiki pattern (ingest → query → lint), with safety rules: propose before writing, never edit raw sources, log every change
- 📊 **Dashboards** built with native Obsidian Bases: pending decisions, active projects, AI queue, Inbox
- 🕓 **Version history built in:** the bundled Git plugin auto-commits every 10 minutes; connect your own private repo for off-site backup and multi-device sync
- 🗓 **Calendar, activity heatmap and reminders:** see what got done when, a GitHub-style activity graph, and notifications for due tasks
- ⚡ **One quick menu** (`Ctrl/Cmd+O`): jump to any note, create a note/task/idea, or run a command
- ✍️ **Writing tools:** `/` command menu, autocomplete, formatting toolbar, auto-updating table of contents, LaTeX shortcuts, folder icons
- 📄 **Files:** highlight and annotate PDFs, preview Word and Excel files, import docx/xlsx/pptx/pdf/csv as notes
- 🔌 **MCP server:** give Claude Desktop, Claude Code, Codex or other MCP clients safe, read-mostly access to your vault
- 🔒 **Protected folders:** keep private folders completely out of the AI's reach
- 🧪 Fictional **example notes** you can delete with one command

No paid plugins and no API keys. All plugins below come bundled and enabled; community plugins are unmodified releases from the official Obsidian plugin list, with their licenses included.

## Install

### Windows: one command (PowerShell)
```powershell
$d="$HOME\Documents\Second Brain"; iwr https://github.com/Doga0/obsidian-second-brain-template/archive/refs/heads/main.zip -UseBasicParsing -OutFile "$env:TEMP\sb.zip"; Expand-Archive "$env:TEMP\sb.zip" "$env:TEMP\sb" -Force; Move-Item "$env:TEMP\sb\obsidian-second-brain-template-main" $d; powershell -ExecutionPolicy Bypass -File "$d\setup.ps1"
```

### macOS / Linux: one command
```bash
d="$HOME/Documents/Second Brain"; curl -L https://github.com/Doga0/obsidian-second-brain-template/archive/refs/heads/main.tar.gz | tar xz -C /tmp && mv /tmp/obsidian-second-brain-template-main "$d" && bash "$d/setup.sh"
```

The command downloads the template into `Documents/Second Brain` and runs the setup script, which:
- installs Obsidian, Python and Git if they're missing (Windows: winget · macOS: Homebrew)
- creates the folder structure for both areas
- turns the vault into a Git repository with a first commit (local version history)
- registers the folder as an Obsidian vault and opens it
- runs a health check

When Obsidian asks whether to **trust this vault's plugins**, choose trust: that enables the bundled plugins (board, tools, Git and the rest).

### Back up to your own private repository (optional)
Out of the box the Git plugin keeps **local** history only. To also push to GitHub (backup + other devices), create an **empty private** repository and run:
```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\Documents\Second Brain\setup.ps1" -Remote https://github.com/<you>/<repo>.git
```
```bash
bash "$HOME/Documents/Second Brain/setup.sh" --remote https://github.com/<you>/<repo>.git
```
Setup pushes your vault and switches the Git plugin to automatic sync (commit + push every 10 minutes, pull on startup). Or click **Use this template** on GitHub, clone your new private repo and run setup inside it: the remote is detected automatically. Optional: `-GitName` / `-GitEmail` (`--git-name` / `--git-email`) set the commit identity.

**Manual install:** download the ZIP, unzip it anywhere, open the folder in Obsidian with *Open folder as vault*, and turn on community plugins in *Settings → Community plugins* (the bundled ones are already listed as enabled).

## Requirements
| | Needed for |
|---|---|
| [Obsidian](https://obsidian.md) 1.9+ | everything (Bases need 1.9) |
| Python 3.8+ | the AI commands' helper script (`vault_tool.py`) |
| [Git](https://git-scm.com) | version history (installed by setup on Windows; optional) |
| Desktop Obsidian | the Second Brain Tools plugin (calendar, heatmap, quick menu, reminders, spreadsheet view, import); everything else also works on mobile |
| [Claude Code](https://claude.com/claude-code) | the `/sb-*` AI commands (optional) |
| Codex (ChatGPT desktop) | the shared `sb-*` skills and project MCP server (optional) |

## First steps
1. Open **Home**: dashboards, current tasks, pending decisions, the AI command list.
2. Read **99 System/Second Brain Guide**: structure, metadata, board, commands, weekly routine.
3. Look around the *example* notes (a fictional website project), then delete them:
   `python "99 System/scripts/vault_tool.py" clean-examples --yes`
4. Open the folder in Claude Code or Codex and try `sb-new`, `sb-task`, or `sb-ask` (Claude: `/sb-*`; Codex: `$sb-*` or natural language).

## How it's organized
Two areas with different layouts, plus a shared system:
```
Personal/
  00 Inbox/        new notes land here
  10 Maps/         maps of content (MOC - <Area>)
  15 Tasks/        task cards for the board
  20 Projects/     <Project>/<Project>.md hub + notes + decisions
  30 Research/     <Research>/<Research>.md hub + experiments
  40 Knowledge/    evergreen concept notes
  50 Ideas/        not-yet-started ideas
  60 Resources/    reading list, attachments
  70 Analyses/     AI analyses and weekly reviews
  90 Archive/      finished projects
Work/
  MOC - Work.md    entry map
  00 Inbox/        raw work notes
  10 Projects/     <Project>/<Project>.md hub + design notes + ADR-NNN decisions
  20 Meetings/     YYYY-MM-DD - Organization - Topic
  30 Organizations & People/   client, vendor and people cards
  40 Systems & APIs/           external systems and APIs
  50 Tasks/        work task cards
  60 Attachments/ · 70 Analyses/ · 90 Archive/
99 System/         guide, templates, index, log, health, AI queue, config, scripts
Home.md · Board.md · CLAUDE.md (AI contract)
```
Boards, calendar, heatmap, reminders, AI commands and MCP tools show **both areas, personal only or work only**: the *area* menu in Obsidian, `--scope personal|work|all` in commands, `scope` in MCP.

## Plugins
Everything lives in `.obsidian/plugins/` with its settings, so it works right after setup.

| Plugin | Version | What it does | How to use it | License |
|---|---|---|---|---|
| **Second Brain Board** (`sb-board`) | 1.0.0 | Kanban boards where every card is a note and the column is its `status`: drag and drop, priorities, due dates, subtask counter, project progress bars | `Board.md`, `sb-board` blocks in hubs; `Ctrl/Cmd+P` → *Quick add task* | MIT (this template) |
| **Second Brain Tools** (`sb-tools`) | 1.0.0 | Calendar, GitHub-style activity heatmap, quick menu, due-date reminders, xlsx/csv viewer, file import; all area-aware | `Ctrl/Cmd+O` quick menu · calendar in `Board.md` · heatmap in `Home.md` · `Ctrl/Cmd+P` → *Import file* | MIT (this template) |
| **[Git](https://github.com/Vinzent03/obsidian-git)** | 2.43.0 | Auto-commit every 10 minutes; with a remote, push and pull on startup; file history | `Ctrl/Cmd+P` → *Git: Commit-and-sync* / *Open file history* | MIT |
| **[Various Complements](https://github.com/tadashi-aikawa/obsidian-various-complements-plugin)** | 11.4.2 | Autocomplete from the words and note names in your vault | Pick from the list while typing | MIT |
| **[Editing Toolbar](https://github.com/PKM-er/obsidian-editing-toolbar)** | 4.1.14 | Formatting toolbar (bold, headings, lists, colors, tables…) | Buttons above the editor | MPL-2.0 |
| **[Automatic Table of Contents](https://github.com/johansatge/obsidian-automatic-table-of-contents)** | 1.8.0 | Table of contents block that updates as the note changes | `/` → *Insert table of contents* | MIT |
| **[Latex Suite](https://github.com/artisticat1/obsidian-latex-suite)** | 1.14.5 | LaTeX snippets (`//` → `\frac`, `sr` → `^2`); `mk ` inline math, `dm ` block math. `mk` is set to fire only as a separate word | Type inside `$…$` / `$$…$$` | MIT |
| **[Iconize](https://github.com/FlorianWoelki/obsidian-iconize)** | 2.14.7 | Folder and file icons in the file explorer; the numbered folders come with icons | Right-click a folder → *Change icon* | MIT |
| **[PDF++](https://github.com/RyotaUshio/obsidian-pdf-plus)** | 0.40.31 | Highlight PDFs, link a selection into a note, comment; can also write annotations into the PDF | Select text in a PDF → pick a color | MIT |
| **[Docxer](https://github.com/Developer-Mike/obsidian-docxer)** | 2.3.1 | Preview Word (.docx) files, embed them in notes, convert them to Markdown | Open a `.docx` → *Convert* | GPL-3.0 |

The core **Slash commands** plugin is also on: type `/` at the start of a line to search every command (headings, tables, callouts, templates, TOC…). Details, choices and what was left out on purpose: *99 System/Second Brain Guide → Writing, navigation and tracking tools*.

## AI commands (Claude Code and Codex skills)
Open the vault in Claude Code and type `/sb-`, or in Codex invoke `$sb-ask` or describe the task naturally. The 17 shared workflows live in `skills/sb-*/SKILL.md`; `.claude/skills/` and `.agents/skills/` contain product entrypoints. The rules they all follow are in [`CLAUDE.md`](CLAUDE.md), with Codex guidance in [`AGENTS.md`](AGENTS.md) (propose before writing, never edit raw sources, keep the areas apart, never touch protected folders, log every write). Most take `--scope personal|work|all`.

| Command | Arguments | What it does |
|---|---|---|
| `/sb-ingest` | `<Inbox note \| URL \| text> [--yes]` `[--scope personal\|work\|all]` | Files a note/URL/text: decides its type, puts it in the right folder, adds reasoned links, updates the hub/MOC |
| `/sb-inbox` | `[--yes]` `[--scope personal\|work\|all]` | Classifies everything in the inboxes (`Personal/00 Inbox`, `Work/00 Inbox`) and processes it within its area with one approval table |
| `/sb-ask` | `<question> [--save]` `[--scope personal\|work\|all]` | Answers from your notes with citations; separates what the vault says from the AI's inference |
| `/sb-connect` | `<note name> [--yes]` `[--scope personal\|work\|all]` | Finds meaningful links for a note and adds them both ways, with relation type and reason |
| `/sb-distill` | `<concept \| note name>` | Distills a concept into a knowledge note (`Personal/40 Knowledge`; work: `Work/40 Systems & APIs`) or updates a seed note |
| `/sb-challenge` | `<note \| idea text> [--save]` | Red-teams an idea or decision: assumptions, weak points, counter-evidence, cheapest test |
| `/sb-emerge` | `[MOC name \| area] [--save]` `[--scope personal\|work\|all]` | Finds cross-project patterns, recurring questions and new idea combinations |
| `/sb-new` | `<project\|research\|idea\|moc> <name> [goal]` `[--scope personal\|work\|all]` | New project/research/idea/MOC in the right area: folder, hub from template, MOC link |
| `/sb-brief` | `<hub> [--update]` | Current state of a project: goal, decisions, open questions, next steps, risks |
| `/sb-decide` | `<hub> "<decision>" \| review` | Logs a decision or walks through pending (`proposed`) decisions to accept/reject |
| `/sb-experiment` | `<hub> "<experiment>" [result \| file]` | Adds an experiment to the hub's log or records its result against the hypotheses |
| `/sb-task` | `<task \| free text> [--project <Hub>] [--yes]` `[--scope personal\|work\|all]` | Creates (in the project's area), updates or moves board cards; extracts several tasks from free text |
| `/sb-plan` | `<Hub> [goal or horizon]` | Reads a hub and proposes an ordered, prioritized task plan; creates cards on approval |
| `/sb-standup` | `[days] [--project <Hub>] [--save]` `[--scope personal\|work\|all]` | Progress report: done/started work, blockers, overdue and upcoming dates, project progress |
| `/sb-review` | `[--no-save]` `[--scope personal\|work\|all]` | Weekly review: projects, dates, decisions, inboxes, AI queue; review note with Personal and Work sections |
| `/sb-lint` | `[--deep] [--yes]` `[--scope personal\|work\|all]` | Health check: broken links, orphans, missing metadata, stale hubs, notes in the wrong area, protected-folder integrity; `--deep` adds contradiction checks |
| `/sb-queue` | `[--yes]` `[--scope personal\|work\|all]` | Processes AI requests left in Obsidian (`ai:` property, `AI Queue.md`) |

## MCP server
`99 System/scripts/vault_mcp.py`: Python standard library only, stdio. The MCP client starts it when needed.
- **Claude Code:** defined in `.mcp.json` at the vault root (approve it the first time).
- **Codex (ChatGPT desktop):** the same server is defined in `.codex/config.toml` for a trusted project. Open the vault root and start a new chat after adding the configuration.
- **Claude Desktop:** add it to `claude_desktop_config.json` (example in the Guide).
- Every tool takes `scope`: `personal`, `work` or `all` (reads default to all). Protected folders, `.obsidian/`, `.git/`, `.claude/`, `.agents/`, `.codex/` and `skills/` are invisible. Write tools only **create** new files, in the project's area (else the `scope`); they can't change, move or delete existing notes. Every write is logged to `99 System/Log.md`.

| Tool | Kind | Parameters | What it does |
|---|---|---|---|
| `vault_index` | read | `scope` | Returns the catalog (`99 System/Index.md`): type, status and summary of every note, in Personal / Work sections |
| `vault_search` | read | `query`, `k`, `scope` | Ranked keyword search over note sections (accent-insensitive); file + line number |
| `vault_read_note` | read | `path`, `offset`, `limit`, `scope` | Reads a note with line numbers; accepts a path or a note name |
| `vault_note_context` | read | `note`, `scope` | Frontmatter, heading outline, outgoing links and backlinks |
| `vault_list_tasks` | read | `project`, `scope` | Board cards as JSON: area, status, priority, dates, subtask count |
| `vault_list_notes` | read | `folder`, `scope` | List of note files, optionally limited to a folder |
| `vault_capture` | create | `title`, `content`, `source`, `scope` | Writes a new note to the area's inbox (`Personal/00 Inbox` or `Work/00 Inbox`) |
| `vault_create_task` | create | `title`, `project`, `priority`, `due`, `description`, `subtasks`, `scope` | Writes a new `status: todo` task card to `Personal/15 Tasks` or `Work/50 Tasks` |

## Helper script
`python "99 System/scripts/vault_tool.py" <command>`: the deterministic tool behind the AI commands and plugins (add `-X utf8` after `python` on Windows). Every command takes `--scope personal|work|all`.

| Command | What it does |
|---|---|
| `lint [--no-write]` | Health check; writes `99 System/Health.md` |
| `index` | Regenerates the `99 System/Index.md` catalog |
| `search <query> [--k N]` | Section-level ranked search |
| `context <note>` | Outline, links and backlinks of a note |
| `tasks [--project X] [--json]` | The board as text/JSON + last 7 days of activity |
| `queue` | Pending AI requests |
| `import <file> [--json] [--scope work]` | docx/xlsx/pptx/pdf/csv → `type: source` note in the area's inbox; original kept in the area's attachments |
| `log <op> <text>` | Appends to `99 System/Log.md` |
| `stats` | Counts by type / status / folder |
| `protected-baseline` | Records hashes of protected folders |
| `clean-examples [--yes]` | Lists (or deletes) the example notes |

## Privacy
- Your notes stay local; nothing in the template sends data anywhere.
- AI skills run only when you invoke them in Claude Code or Codex; the MCP server runs only when an MCP client you configured starts it.
- Work and personal notes live in separate areas; commands only mix them when you ask for both.
- List private folders under `"protected"` in `99 System/config.json` to exclude them from every command and the board.
- If you keep your vault in Git, use a **private** repository.

## License
[MIT](LICENSE). Bundled community plugins keep their own licenses (MIT, except Editing Toolbar: MPL-2.0 and Docxer: GPL-3.0); each plugin folder in `.obsidian/plugins/` contains its `LICENSE`.
