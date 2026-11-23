---
type: project
status: active
topics: []
created: {{date}}
---
# {{title}}

## Goal
Why does this exist, and what does done look like?

## Status
- 

## Notes
<!-- Link the notes in this folder, one line each: what it is and why it matters -->

## Decisions
```base
filters:
  and:
    - 'type == "decision"'
    - 'file.inFolder("FOLDER-PATH")'
views:
  - type: table
    name: Decisions
    order:
      - file.name
      - status
      - origin
      - decided
```
*Replace FOLDER-PATH with this hub's folder (`/sb-new` does it for you). New decision: `/sb-decide` or the `Decision` template.*

## Open questions
- 

## Tasks
```sb-board
type: task
project: PROJECT-NAME
hide-done-after: 30
filters: false
```

## Related
<!-- Other projects/research: [[...]] — why related? -->
