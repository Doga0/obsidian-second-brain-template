---
type: moc
---
# Work

Entry point for the **Work** area. Work notes revolve around projects, clients and meetings, so this area is organized differently from Personal.

## Projects
```base
filters:
  and:
    - 'file.inFolder("Work")'
    - 'type == "project"'
views:
  - type: table
    name: Projects
    order:
      - file.name
      - status
      - file.mtime
```

## Meetings
```base
filters:
  and:
    - 'file.inFolder("Work/20 Meetings")'
views:
  - type: table
    name: Meetings
    order:
      - file.name
      - project
    sort:
      - property: file.name
        direction: DESC
```

## Organizations, people and systems
```base
filters:
  and:
    - 'file.inFolder("Work/30 Organizations & People") || file.inFolder("Work/40 Systems & APIs")'
views:
  - type: table
    name: Cards
    order:
      - file.name
      - type
      - file.folder
```

## Layout
| Folder | What goes there |
|---|---|
| `00 Inbox` | Raw work notes, pasted chats, quick captures |
| `10 Projects/<Name>/` | Project hub, design notes, `ADR-NNN - …` decision records |
| `20 Meetings` | `YYYY-MM-DD - Organization - Topic` (`Meeting` template) |
| `30 Organizations & People` | Client, vendor and people cards (`Org` template) |
| `40 Systems & APIs` | External systems, APIs, reusable technical knowledge |
| `50 Tasks` | Work task cards (the board's *Work* area) |
| `60 Attachments` · `70 Analyses` · `90 Archive` | Files · AI analyses of work notes · closed projects |
