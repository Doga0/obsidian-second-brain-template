---
name: sb-new
description: Second Brain — Create a new project, research area, idea or MOC: folder and hub from the templates, linked from the relevant MOC. Use when the user runs /sb-new or asks to "start a new project/research".
argument-hint: <project|research|idea|moc> <name> [goal]
---
# /sb-new

1. Get the type and name. If no goal is given, ask **one** question: "What is this for, and what does done look like?"
2. Run `vault_tool.py search <name and goal terms>` to see whether a similar hub or idea already exists. If one does, say so and suggest adding to it instead.
3. Create:
   - **project**: `20 Projects/<Name>/<Name>.md` from the `Project Hub` template
   - **research**: `30 Research/<Name>/<Name>.md` from the `Research Hub` template (fill in the research question in one sentence)
   - **idea**: `50 Ideas/<Name>.md` (`type: idea`, `status: idea`)
   - **moc**: `10 Maps/MOC - <Name>.md` from the `MOC` template (don't create it with fewer than 3 related notes; explain why)
   Replace the `{{date}}`/`{{title}}` placeholders, and also `FOLDER-PATH` (the Decisions Base) and `PROJECT-NAME` (the Tasks board), with the real folder and hub name. If the user named first steps, add them as cards with `/sb-task` or suggest `/sb-plan`.
4. Add a line to the relevant MOC (`[[Name]]` + reason) and fill in `topics`.
5. If this promotes an idea from 50 Ideas, move the idea note into the new folder, set `status: promoted` and link it from the hub.
6. Run `vault_tool.py index` and `log new "<type>: <name>"`.
