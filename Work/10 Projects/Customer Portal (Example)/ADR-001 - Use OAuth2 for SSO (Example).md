---
type: decision
example: true
project: "[[Customer Portal (Example)]]"
status: accepted
origin: user
---
# ADR-001 - Use OAuth2 for SSO (Example)

> [!example] Example note — part of the template. Delete all examples with `python "99 System/scripts/vault_tool.py" clean-examples --yes`.

## Decision
Customers sign in through the client's existing OAuth2 identity provider.

## Rationale
The client already runs an identity provider; agreed in [[2026-01-15 - Acme Corp - Portal kickoff (Example)]].

## Alternatives
- Separate portal accounts: more support load, rejected.
