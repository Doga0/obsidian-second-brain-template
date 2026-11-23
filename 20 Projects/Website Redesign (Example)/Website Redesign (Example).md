---
type: project
status: active
example: true
topics:
  - "[[MOC - Web Development (Example)]]"
---
# Website Redesign (Example)

> [!example] Example note — part of the template. Delete all examples with `python "99 System/scripts/vault_tool.py" clean-examples --yes`.

## Goal
Replace the old personal website with a faster, simpler one that's easy to update. Done = new site live on the custom domain, old one redirected.

## Status
- Generator chosen (see decisions). Writing content pages.

## Notes
- [[Notes - Hosting options (Example)]] — comparison that led to the hosting decision.
- [[Static Site Generators (Example)]] — the concept behind the main technical choice.

## Decisions
```base
filters:
  and:
    - 'type == "decision"'
    - 'file.inFolder("20 Projects/Website Redesign (Example)")'
views:
  - type: table
    name: Decisions
    order:
      - file.name
      - status
      - origin
      - decided
```

## Open questions
- Is a newsletter worth it at launch? → [[Newsletter for the site (Example)]]

## Tasks
```sb-board
type: task
project: Website Redesign (Example)
hide-done-after: 30
filters: false
```

## Related
- [[Page Speed Experiments (Example)]] — measures whether the new stack is actually faster.
