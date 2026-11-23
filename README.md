---
type: system
---
# Obsidian Second Brain Template

A ready-to-use Obsidian vault for running a **second brain**: projects, research, knowledge, ideas and tasks, with a **kanban board** and an **AI command layer** for [Claude Code](https://claude.com/claude-code).

- 🗂 **Simple structure:** Inbox → Projects / Research / Knowledge / Ideas → Archive, plus maps of content (MOCs)
- 📋 **Kanban board:** Trello/Jira-style boards where every card is a real note (To Do / In Progress / Done), with drag and drop, priorities, due dates, subtasks and per-project progress bars
- ✅ **Decision log:** decisions are notes you approve with one click; AI-suggested decisions stay "proposed" until you accept them
- 🤖 **17 AI commands** (`/sb-ingest`, `/sb-ask`, `/sb-plan`, `/sb-review`, `/sb-challenge`, …) following the LLM-Wiki pattern (ingest → query → lint), with safety rules: propose before writing, never edit raw sources, log every change
- 📊 **Dashboards** built with native Obsidian Bases: pending decisions, active projects, AI queue, Inbox
- 🔒 **Protected folders:** keep private folders completely out of the AI's reach
- 🧪 Fictional **example notes** you can delete with one command

No paid plugins and no API keys. The board plugin is bundled in the vault; everything else is native Obsidian.

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
- installs Obsidian and Python if they're missing (Windows: winget · macOS: Homebrew)
- creates the folder structure
- registers the folder as an Obsidian vault and opens it
- runs a health check

When Obsidian asks whether to **trust this vault's plugins**, choose trust: that enables the board.

**Prefer to keep your vault in Git?** Click **Use this template** on GitHub, create a **private** repository, clone it, then run `setup.ps1` / `setup.sh` inside it.

**Manual install:** download the ZIP, unzip it anywhere, open the folder in Obsidian with *Open folder as vault*, and enable the **Second Brain Board** plugin in *Settings → Community plugins*.

## Requirements
| | Needed for |
|---|---|
| [Obsidian](https://obsidian.md) 1.9+ | everything (Bases need 1.9) |
| Python 3.8+ | the AI commands' helper script (`vault_tool.py`) |
| [Claude Code](https://claude.com/claude-code) | the `/sb-*` AI commands (optional: the vault works without it) |

## First steps
1. Open **Home**: dashboards, current tasks, pending decisions, the AI command list.
2. Read **99 System/Second Brain Guide**: structure, metadata, board, commands, weekly routine.
3. Look around the *example* notes (a fictional website project), then delete them:
   `python "99 System/scripts/vault_tool.py" clean-examples --yes`
4. Open the folder in Claude Code and try `/sb-new project My Project`, `/sb-task`, `/sb-ask`.

## How it's organized
```
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
99 System/       guide, templates, index, log, health, AI queue, config, scripts
Home.md · Board.md · CLAUDE.md (AI contract)
```

## AI commands
| Command | What it does |
|---|---|
| `/sb-ingest` · `/sb-inbox` | file new notes/URLs/text with reasoned links |
| `/sb-ask` | answer from your notes, with citations |
| `/sb-connect` · `/sb-distill` | find links · turn a concept into a knowledge note |
| `/sb-challenge` · `/sb-emerge` | red-team an idea · find cross-project patterns |
| `/sb-new` · `/sb-brief` | start a project/research/idea/MOC · get back up to speed |
| `/sb-task` · `/sb-plan` · `/sb-standup` | cards · project plans · progress reports |
| `/sb-decide` · `/sb-experiment` | decision log · experiment log |
| `/sb-review` · `/sb-lint` · `/sb-queue` | weekly review · health check · process requests left in Obsidian |

The rules every command follows are in [`CLAUDE.md`](CLAUDE.md). Commands live in `.claude/skills/`, so you can edit them or add your own.

## Privacy
- Your notes stay local; nothing in the template sends data anywhere.
- AI commands run only when you call them in Claude Code.
- List private folders under `"protected"` in `99 System/config.json` to exclude them from every command and the board.
- If you keep your vault in Git, use a **private** repository.

## License
[MIT](LICENSE)
