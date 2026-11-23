---
name: sb-new
description: "Second Brain — Create a new project, research area, idea or MOC: folder and hub from the templates, linked from the relevant MOC. Use when the user runs /sb-new or asks to \"start a new project/research\"."
---
# /sb-new

1. Get the type and name. If no goal is given, ask **one** question: "What is this for, and what does done look like?"
2. Run `vault_tool.py search <name and goal terms>` to see whether a similar hub or idea already exists. If one does, say so and suggest adding to it instead.
3. Create:
   - First pick the area: `--scope work` or a work context → Work; otherwise Personal. Ask if unsure.
   - **project**: Personal `Personal/20 Projects/<Name>/<Name>.md` · Work `Work/10 Projects/<Name>/<Name>.md`, from the `Project Hub` template (set the Base folder path accordingly)
   - **research**: `Personal/30 Research/<Name>/<Name>.md` (work research is a project under Work/10 Projects) from the `Research Hub` template (fill in the research question in one sentence)
   - **idea**: `Personal/50 Ideas/<Name>.md` (work idea: `Work/00 Inbox/<Name>.md`) (`type: idea`, `status: idea`)
   - **moc**: `Personal/10 Maps/MOC - <Name>.md` (work: `Work/MOC - Work.md` is the map; add a new one at the `Work/` root only if needed) from the `MOC` template (don't create it with fewer than 3 related notes; explain why)
   Replace the `{{date}}`/`{{title}}` placeholders, and also `FOLDER-PATH` (the Decisions Base) and `PROJECT-NAME` (the Tasks board), with the real folder and hub name. If the user named first steps, add them as cards with `/sb-task` or suggest `/sb-plan`.
4. Add a line to the relevant MOC (`[[Name]]` + reason) and fill in `topics`.
5. If this promotes an idea from Personal/50 Ideas, move the idea note into the new folder, set `status: promoted` and link it from the hub.
6. Run `vault_tool.py index` and `log new "<type>: <name>"`.
