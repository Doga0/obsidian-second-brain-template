---
type: research
status: active
topics: []
created: {{date}}
---
# {{title}}

## Research question
> 

## Context and literature
- 

## Hypotheses
1. 

## Tasks
```sb-board
type: task
project: PROJECT-NAME
hide-done-after: 30
filters: false
```

## Experiment log
| Date | Experiment | Hypothesis / RQ | The one thing changed | Result |
|---|---|---|---|---|
| | | | | |

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

## Findings → knowledge
<!-- When a verified finding is useful in more than one context, create a note in 40 Knowledge and link it here -->
- 

## Open questions / future work
- 
