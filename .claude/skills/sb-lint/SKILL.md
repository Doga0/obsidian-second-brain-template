---
name: sb-lint
description: Second Brain — Vault health check: broken links, orphans, missing metadata, stale hubs, split candidates, overdue tasks, pending decisions, protected-folder integrity; with --deep also contradictions and outdated claims. Proposes fixes and applies them on approval. Use when the user runs /sb-lint or asks to "check the vault".
argument-hint: [--deep] [--yes]
---
# /sb-lint

1. Run `vault_tool.py lint` and `vault_tool.py index`; read `99 System/Health.md`.
2. If **protected-folder integrity** reports differences, report that first. Don't try to fix it. If the user changed those files themselves, suggest running `protected-baseline`.
3. Group the issues and show a table:
   - **Auto-fixable:** broken link → most likely target (similar name or alias); missing `type` → proposed value.
   - **Needs a decision:** orphan → hub or MOC it could link to (with a reason); active hub unchanged for 30+ days → `paused` or `archived`?; split candidate → split proposal with line ranges; overdue task → new date or `done`?
   - **Info:** pending decisions, `seed` notes, blocked tasks.
4. Apply what's approved. The raw-content rule still holds: in source notes only frontmatter and the callout may change.
5. With `--deep`, also check:
   - **Contradictions** between notes on the same topic (different statements about the same concept or decision). Show the evidence and propose a `> [!warning]` callout on the hub.
   - **Outdated claims**: deadlines already in the past, "not announced yet", version claims. List what needs verifying.
   - `seed` knowledge notes unchanged for 30+ days: suggest `/sb-distill`.
6. Run `lint` again and report the before/after difference. Then `vault_tool.py log lint "<summary>"`.
