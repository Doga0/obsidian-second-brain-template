---
type: system
---
# Board

> [!tip] How to use
> **Drag and drop** a card between columns: this changes the note's `status`. **`+`** adds a card to a column. **Click** opens the note (`Ctrl/Cmd`+click: new tab). **Right-click**: move, set priority, send to the AI queue.
> Quick add from anywhere: `Ctrl/Cmd+P` → *Second Brain Board: Quick add task* (the open note's project is preselected). If you see code blocks instead of cards, enable the **Second Brain Board** plugin ([[Second Brain Guide#Board]]).
> **Areas:** the first menu in the filter bar is *All areas / Personal / Work*. New cards go to their project's area and folder (`Personal/15 Tasks/<Project>` or `Work/50 Tasks/<Project>`). To pin a board to one area, add `scope: work` to its block.

## Tasks
```sb-board
type: task
title: All tasks
hide-done-after: 14
```

## Projects and research
*The bar on each card is the share of the project's tasks that are done.*
```sb-board
type: project, research
```

## Idea pipeline
```sb-board
type: idea
filters: false
```

## Decisions
```sb-board
type: decision
filters: false
```

## Calendar
*✓ completed · 📅 due (red = overdue) · ▶ started · ⚖ decision. The board writes start/completion dates; set `due` on the card. For one project, add `project: <Hub>` to the block.*
```sb-calendar
show: completed, due, started, decided
```

## Tracking tables
```base
filters:
  and:
    - 'type == "task"'
    - '!file.inFolder("99 System")'
views:
  - type: table
    name: Open tasks by due date
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - project
      - status
      - priority
      - due
    sort:
      - property: due
        direction: ASC
  - type: table
    name: Recently completed
    filters:
      and:
        - 'status == "done"'
    order:
      - file.name
      - project
      - completed
    sort:
      - property: completed
        direction: DESC
```
