# Second Brain: Codex operating contract

Obsidian is the interface; the AI is the librarian and the user is the curator. Read CLAUDE.md before working in this vault. Its rules apply to Codex too, including protected folders from 99 System/config.json, immutable source content, scope separation, approval for moves and broad edits, and logging each write.

## Working in this vault

- Respect the protected folders listed in 99 System/config.json. Do not read, analyze, link or modify their contents.
- Keep Personal/ and Work/ separate. Reading defaults to all; writing follows the note or project area. Ask if the area is unclear.
- At session start run vault_tool.py pack for the L0 context (the session-start hook in this vault is defined for Claude Code only); for project work run pack --project <hub>. 99 System/Index.md is large: read it only for a vault-wide survey. Use vault_tool.py search and context, then inspect only relevant line ranges. Follow the schema and templates in CLAUDE.md and 99 System/Templates/.
- Mark AI inferences as AI observations or save them as analysis notes. Cite vault notes for claims and give every new link a reason.
- Log every write with python "99 System/scripts/vault_tool.py" log <command> "<what changed>".
- Reply in the user's language. Keep notes concise and scannable.

## Codex entrypoints

The shared workflows are in skills/sb-*/SKILL.md. Codex discovers .agents/skills/sb-*/SKILL.md, whose entrypoints load those shared files. Claude discovers .claude/skills/sb-*/SKILL.md and loads the same files. Update the shared skill when changing a workflow.

The project MCP server is configured in .codex/config.toml. If it is unavailable, use 99 System/scripts/vault_tool.py directly.
