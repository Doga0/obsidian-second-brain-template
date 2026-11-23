---
type: system
---
# Home

> [!tip] How it works
> **Obsidian is the interface, Claude Code is the engine.** You write, read and approve here; analysis and reorganization happen in Claude Code through `/sb-…` commands. New note: `Ctrl/Cmd+N` lands in the Personal Inbox; for a work note use `Ctrl/Cmd+O` → `+ title` → *Work*. Leave work for the AI: [[AI Queue]], or add a property like `ai: challenge` to a note.
>
> **First time here?** Read the [[Second Brain Guide]]. The notes marked *example* show how everything fits together; delete them all with `python "99 System/scripts/vault_tool.py" clean-examples --yes`.

> **Two areas:** `Personal/` and `Work/`. Boards, calendar, heatmap and AI commands show both or just one (the *area* menu in Obsidian, `--scope work` in commands).

**Board:** [[Board]] · **Work:** [[MOC - Work]] · **Health:** [[Health]] · **Catalog:** [[Index]] · **History:** [[Log]]

## Currently working on
*Full board, projects and idea pipeline: [[Board]]. One menu for everything: `Ctrl/Cmd+O` (open a note, `!` new task, `+` new note, `>` commands). Work cards carry an orange **Work** badge; pick an area in the menu above the board.*
```sb-board
type: task
hide-done-after: 7
```

## Activity
*Tasks completed/started, notes created/edited and git commits per day. Click a day to see what happened.*
```sb-heatmap
weeks: 52
source: tasks, notes, git
```

## Decisions awaiting approval
*Click a `status` cell and change it to `accepted` or `rejected`. The hub updates immediately.*
```base
filters:
  and:
    - 'type == "decision"'
    - 'status == "proposed"'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Pending
    order:
      - file.name
      - project
      - status
      - origin
  - type: table
    name: All decisions
    filters:
      and:
        - 'status != "proposed"'
    order:
      - file.name
      - project
      - status
      - origin
      - decided
```

## Projects and research
```base
filters:
  and:
    - 'type == "project" || type == "research"'
    - '!file.inFolder("99 System")'
properties:
  file.name:
    displayName: Hub
  status:
    displayName: Status
  file.mtime:
    displayName: Last change
views:
  - type: table
    name: Active
    filters:
      and:
        - 'status == "active"'
    order:
      - file.name
      - type
      - status
      - file.mtime
    sort:
      - property: file.mtime
        direction: DESC
  - type: table
    name: All
    order:
      - file.name
      - type
      - status
      - file.mtime
```

## Maps of content
```base
filters:
  and:
    - 'type == "moc"'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Maps
    order:
      - file.name
      - file.mtime
```

## AI commands
| Command | What it does | When |
|---|---|---|
| `/sb-ingest <note/URL/text>` | Classify, file and link with reasons | A new source arrives |
| `/sb-inbox` | Process the whole Inbox with one approval table | Weekly |
| `/sb-ask <question> [--save]` | Answer from your notes, with citations | "Where was I / what did we say?" |
| `/sb-brief <hub>` | Get back up to speed on a project | Returning to a project |
| `/sb-connect <note>` | Suggest meaningful links | After an important note |
| `/sb-distill <concept/note>` | Create/update a knowledge note | A concept shows up a 2nd time |
| `/sb-challenge <note/idea>` | Red team: assumptions, counter-evidence, cheapest test | Before deciding |
| `/sb-emerge [area]` | Cross-project patterns and new ideas | Monthly |
| `/sb-decide <hub> "<decision>"` · `review` | Record a decision / approve pending ones | When deciding |
| `/sb-experiment <hub> "<experiment>"` | Log an experiment and interpret results | Before/after experiments |
| `/sb-new <type> <name>` | New project / research / idea / MOC | Starting something |
| `/sb-task <task/text>` | Create, update or complete cards; extract tasks from text | Anytime |
| `/sb-plan <hub>` | Break a project into ordered, prioritized tasks | New milestone |
| `/sb-standup [days]` | Progress: done, in progress, overdue, today's focus | Start of day/week |
| `/sb-review` | Weekly review note | Weekly |
| `/sb-lint [--deep]` | Health check and repairs | Weekly |
| `/sb-queue` | Process the AI Queue and `ai:` requests | When the queue has items |

## AI queue
```base
filters:
  and:
    - 'file.hasProperty("ai")'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Waiting
    order:
      - file.name
      - ai
      - ai_note
```
Free-form requests: [[AI Queue]]

## Inbox
[[README - Inbox|How to process the Inbox]] · or `/sb-inbox` (work only: `/sb-inbox --scope work`)
```base
filters:
  and:
    - 'file.inFolder("Personal/00 Inbox") || file.inFolder("Work/00 Inbox")'
    - '!file.name.startsWith("README")'
views:
  - type: table
    name: Inbox
    order:
      - file.name
      - file.ctime
    sort:
      - property: file.ctime
        direction: DESC
```

## Recent analyses
```base
filters:
  and:
    - 'type == "analysis"'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Analyses
    order:
      - file.name
      - source
      - file.ctime
    sort:
      - property: file.ctime
        direction: DESC
```

## Knowledge notes
```base
filters:
  and:
    - 'type == "knowledge"'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Knowledge
    order:
      - file.name
      - status
      - file.mtime
    sort:
      - property: file.mtime
        direction: DESC
```

## More
[[MOC - Work]] · [[Reading List]] · [[README - Ideas|Ideas]] · [[README - Archive|Archive]] · [[Second Brain Guide]] · Templates: `99 System/Templates`
