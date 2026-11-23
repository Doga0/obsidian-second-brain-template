---
type: project
status: active
example: true
topics:
  - "[[MOC - Work]]"
---
# Customer Portal (Example)

> [!example] Example note — part of the template. Delete all examples with `python "99 System/scripts/vault_tool.py" clean-examples --yes`.

## Goal
Build a self-service portal for [[Acme Corp (Example)]] customers. Done = customers can log in with SSO and see their invoices.

## Status
- Kickoff held ([[2026-01-15 - Acme Corp - Portal kickoff (Example)]]); SSO approach decided.

## Notes
- [[Payments API (Example)]] — where invoice data comes from.

## Decisions (ADR)
```base
filters:
  and:
    - 'type == "decision"'
    - 'file.inFolder("Work/10 Projects/Customer Portal (Example)")'
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
- Which invoice history range does the client expect?

## Tasks
```sb-board
type: task
project: Customer Portal (Example)
hide-done-after: 30
filters: false
```
