# -*- coding: utf-8 -*-
"""Second Brain MCP server (stdio, standard library only).

Exposes this vault to MCP clients (Claude Desktop, Claude Code, Codex, other agents) with the same
rules as CLAUDE.md:
  - protected folders (99 System/config.json -> "protected") are invisible: not listed, searched or read
  - read tools: index, search, read_note, note_context, list_tasks, list_notes
  - write tools only CREATE new notes (capture to 00 Inbox, task cards in 15 Tasks/<Project>);
    they never overwrite, edit, move or delete, and every write is logged to 99 System/Log.md

  - prompts: every skills/sb-*/SKILL.md is served as an MCP prompt (slash command in clients), with a preamble
    that maps file/CLI steps to these tools; vault_skill returns the same text for clients without prompts

Run:  python -X utf8 "99 System/scripts/vault_mcp.py"

Project lock (optional): an agent can be limited to one or more projects:
  python -X utf8 "99 System/scripts/vault_mcp.py" --project "My Project" [--project "Other"] [--include-linked]
  (or env SB_PROJECTS="A;B"). In this mode every tool only sees the project's hub folder, its task folder
  (15 Tasks/<Project> / 50 Tasks/<Project>) and notes whose `project` is that hub; --include-linked also
  admits notes the hub links to directly unless they belong to another project. Anything else is
  "not found" / filtered out, and new tasks can only be created for the locked projects.
"""
import datetime, json, os, re, subprocess, sys

VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOOL = os.path.join(VAULT, "99 System", "scripts", "vault_tool.py")
def _protected():
    try:
        with open(os.path.join(VAULT, "99 System", "config.json"), encoding="utf-8") as fh:
            return [p.strip("/").replace("\\", "/") + "/" for p in json.load(fh).get("protected") or [] if p.strip("/")]
    except (OSError, ValueError):
        return []


PROTECTED = _protected()
HIDDEN = tuple(PROTECTED) + (".obsidian/", ".git/", ".claude/", ".agents/", ".codex/", "skills/", ".trash/", "99 System/.integrity/")
AREAS = {"personal": "Personal", "work": "Work"}
FOLDERS = {"personal": {"inbox": "Personal/00 Inbox", "tasks": "Personal/15 Tasks"},
           "work": {"inbox": "Work/00 Inbox", "tasks": "Work/50 Tasks"}}


def scope_of(a, default="all"):
    v = str(a.get("scope", "") or "").strip().lower()
    if not v:
        return default
    for names, val in ((("personal", "p"), "personal"), (("work", "w"), "work"), (("all", "both"), "all")):
        if v in names:
            return val
    raise ValueError("scope must be personal, work or all")


def area_of(rel):
    for k, f in AREAS.items():
        if rel == f or rel.startswith(f + "/"):
            return k
    return "shared"
PROTOCOL = "2025-06-18"
MAX_READ = 60000


def blocked(rel):
    r = rel.replace("\\", "/").lstrip("/")
    return any((r + "/").startswith(h) or r.startswith(h) for h in HIDDEN)


def safe_path(rel):
    """Vault-relative path → absolute, refusing anything outside the vault or in hidden/protected areas."""
    rel = str(rel).replace("\\", "/").strip().lstrip("/")
    if not rel.endswith(".md") and not os.path.splitext(rel)[1]:
        rel += ".md"
    full = os.path.abspath(os.path.join(VAULT, rel))
    if os.path.commonpath([full, VAULT]) != VAULT:
        raise PermissionError("path is outside the vault")
    r = os.path.relpath(full, VAULT).replace("\\", "/")
    if blocked(r):
        raise PermissionError("this folder is not accessible")
    return full, r


def run_tool(*args):
    res = subprocess.run([sys.executable, "-X", "utf8", TOOL, *args], cwd=VAULT, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=120)
    out = (res.stdout or "") + (("\n" + res.stderr) if res.returncode and res.stderr else "")
    # never leak protected paths even if a helper printed one
    return "\n".join(l for l in out.splitlines() if not any(p in l for p in PROTECTED)).strip()


def all_notes():
    out = []
    for root, dirs, files in os.walk(VAULT):
        relroot = os.path.relpath(root, VAULT).replace("\\", "/")
        relroot = "" if relroot == "." else relroot + "/"
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not blocked(relroot + d))
        for f in sorted(files):
            if f.endswith(".md") and f != "AGENTS.md":
                out.append(relroot + f)
    return out


def find(name, scope="all"):
    name = str(name).strip()
    ok = allowed_notes()
    full, rel = safe_path(name)
    if os.path.isfile(full) and (ok is None or rel in ok or rel == "CLAUDE.md"):  # vault rules stay readable under a lock
        return rel
    base = name.split("/")[-1]
    base = base[:-3] if base.endswith(".md") else base
    pool = all_notes() if ok is None else sorted(ok)
    hits = [n for n in pool if os.path.basename(n)[:-3].lower() == base.lower() and (scope == "all" or area_of(n) == scope)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError("several notes match: " + ", ".join(hits))
    raise FileNotFoundError("note not found: " + name)


# ------------------------------------------------------------------ project lock
LOCK = {"projects": [], "linked": False}
FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
LINK_RE = re.compile(r"\[\[([^\]|#^]+)")


def parse_args(argv):
    projects, linked, i = [], False, 0
    while i < len(argv):
        if argv[i] == "--project" and i + 1 < len(argv):
            projects += re.split(r"[;,]", argv[i + 1]); i += 2; continue
        if argv[i] == "--include-linked":
            linked = True
        i += 1
    projects += re.split(r"[;,]", os.environ.get("SB_PROJECTS", ""))
    LOCK["projects"] = list(dict.fromkeys(clean_name(p) for p in projects if p.strip()))
    LOCK["linked"] = linked or os.environ.get("SB_INCLUDE_LINKED", "") in ("1", "true", "yes")


def head_of(rel):
    try:
        with open(os.path.join(VAULT, rel), encoding="utf-8", errors="replace") as fh:
            text = fh.read(4000)
    except OSError:
        return "", ""
    m = FM_RE.match(text)
    fm = m.group(1) if m else ""
    t = re.search(r"(?m)^type:\s*\"?([\w-]+)", fm)
    p = re.search(r"(?m)^project:\s*\"?\[\[([^\]|#]+)", fm)
    return (t.group(1) if t else ""), (p.group(1).strip() if p else "")


def project_owner(rel, notes_meta, hubs):
    """Which project a note belongs to (by hub folder, task folder or `project` field), else ''."""
    _, proj = notes_meta.get(rel, ("", ""))
    if proj:
        return proj
    for name, folder in hubs.items():
        if folder and rel.startswith(folder + "/"):
            return name
    for f in FOLDERS.values():
        if rel.startswith(f["tasks"] + "/"):
            parts = rel[len(f["tasks"]) + 1:].split("/")
            if len(parts) > 1:
                return parts[0]
    return ""


def allowed_notes():
    """Set of vault-relative note paths visible under the lock (None = no lock)."""
    if not LOCK["projects"]:
        return None
    notes = all_notes()
    meta = {n: head_of(n) for n in notes}
    hubs, hub_files = {}, {}  # project name -> hub folder ('' if the hub is not in its own folder)
    for n in notes:
        base = os.path.basename(n)[:-3]
        if meta[n][0] in ("project", "research") and area_of(n) in FOLDERS:
            folder = os.path.dirname(n)
            hubs[base] = folder if os.path.basename(folder) == base else ""
            hub_files[base] = n
    locked = {p.casefold() for p in LOCK["projects"]}
    owner = {n: project_owner(n, meta, hubs) for n in notes}
    ok = {n for n in notes if owner[n].casefold() in locked}
    ok |= {hub_files[p] for p in hub_files if p.casefold() in locked}
    if LOCK["linked"]:
        by_base = {}
        for n in notes:
            by_base.setdefault(os.path.basename(n)[:-3].casefold(), []).append(n)
        for p in [p for p in hub_files if p.casefold() in locked]:
            text = open(os.path.join(VAULT, hub_files[p]), encoding="utf-8", errors="replace").read()
            for target in LINK_RE.findall(text):
                for n in by_base.get(target.strip().split("/")[-1].casefold(), []):
                    if not owner[n] and meta[n][0] not in ("moc", "system", "analysis"):
                        ok.add(n)
    return ok


def check_project(name):
    if LOCK["projects"] and clean_name(name).casefold() not in {p.casefold() for p in LOCK["projects"]}:
        raise PermissionError("this server only serves these projects: " + ", ".join(LOCK["projects"]))


def clean_name(s):
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|#^\[\]]', " ", str(s))).strip()[:90]


def unique(folder, title):
    base = os.path.join(VAULT, folder, title)
    p, n = base + ".md", 2
    while os.path.exists(p):
        p = f"{base} ({n}).md"; n += 1
    return p


def log(op, msg):
    run_tool("log", op, msg)


# ------------------------------------------------------------------ tools
def locked_index(ok, sc):
    """Catalogue of the visible notes only (the shared Index.md would list every project)."""
    text = open(os.path.join(VAULT, "99 System", "Index.md"), encoding="utf-8").read()
    summary = {}
    for m in re.finditer(r"(?m)^- \[\[([^\]]+)\]\](.*)$", text):
        summary.setdefault(m.group(1).casefold(), m.group(2).strip())
    out = [f"# Index (locked to: {', '.join(LOCK['projects'])})"]
    folder = None
    for n in sorted(ok):
        if sc != "all" and area_of(n) != sc:
            continue
        d = os.path.dirname(n)
        if d != folder:
            out += ["", f"## {d}"]; folder = d
        base = os.path.basename(n)[:-3]
        t, _ = head_of(n)
        extra = summary.get(base.casefold(), "")
        out.append(f"- [[{base}]]" + (f" ({t})" if t and not extra else "") + (f" {extra}" if extra else ""))
    return "\n".join(out) if len(out) > 1 else "(no notes in the locked projects)"


def t_index(a):
    sc = scope_of(a)
    ok = allowed_notes()
    if ok is not None:
        return locked_index(ok, sc)[:MAX_READ]
    text = open(os.path.join(VAULT, "99 System", "Index.md"), encoding="utf-8").read()
    if sc != "all":
        head = {"personal": "# Personal", "work": "# Work"}[sc]
        parts = re.split(r"(?m)^(?=# )", text)
        text = "".join(p for p in parts if p.startswith(head)) or f"(no notes in {sc})"
    return text[:MAX_READ]


def t_search(a):
    q = str(a.get("query", "")).strip()
    if not q:
        raise ValueError("query is required")
    k = int(a.get("k", 10))
    ok = allowed_notes()
    if ok is None:
        return run_tool("search", q, "--k", str(k), "--scope", scope_of(a))
    # search wide, keep only hits inside the lock
    out = run_tool("search", q, "--k", "400", "--scope", scope_of(a))
    blocks, cur = [], None
    for line in out.splitlines():
        m = HIT_RE.match(line)
        if m:
            cur = [m.group(1) in ok, [line]]; blocks.append(cur)
        elif cur is not None:
            cur[1].append(line)
    kept = ["\n".join(b[1]).rstrip() for b in blocks if b[0]][:k]
    return "\n\n".join(kept) or "(no results in the locked projects)"


HIT_RE = re.compile(r"^\s*-?[\d.]+\s+(.+?\.md):\d+\s")


def t_read(a):
    rel = find(a.get("path") or a.get("note") or "", scope_of(a))
    lines = open(os.path.join(VAULT, rel), encoding="utf-8", errors="replace").read().splitlines()
    off = max(0, int(a.get("offset", 1)) - 1)
    lim = int(a.get("limit", 0)) or len(lines)
    chunk = lines[off:off + lim]
    body = "\n".join(f"{off + i + 1}\t{l}" for i, l in enumerate(chunk))
    return f"# {rel} (lines {off + 1}-{off + len(chunk)} of {len(lines)})\n{body}"[:MAX_READ]


def t_context(a):
    out = run_tool("context", find(a.get("note", ""), scope_of(a))[:-3].split("/")[-1])
    ok = allowed_notes()
    if ok is None:
        return out
    names = {os.path.basename(n)[:-3].casefold() for n in ok}
    keep, section, hidden = [], "", 0
    for line in out.splitlines():
        if re.match(r"^(outgoing|backlinks):", line):
            section = line[:-1]
        elif line and not line.startswith(" "):
            section = ""
        if section and line.startswith("  "):
            if line.strip().split(" :: ")[0].casefold() not in names:
                hidden += 1
                continue
        keep.append(line)
    if hidden:
        keep.append(f"\n({hidden} links outside the locked projects hidden)")
    return "\n".join(keep)


def t_tasks(a):
    args = ["tasks", "--json", "--scope", scope_of(a)]
    if LOCK["projects"]:
        rows = []
        for p in ([a["project"]] if a.get("project") else LOCK["projects"]):
            check_project(p)
            rows += json.loads(run_tool(*args, "--project", str(p)) or "[]")
        return json.dumps(rows, ensure_ascii=False, indent=1)
    if a.get("project"):
        args += ["--project", str(a["project"])]
    return run_tool(*args)


def t_list(a):
    sc = scope_of(a)
    folder = str(a.get("folder", "")).strip().strip("/")
    if folder and blocked(folder + "/"):
        raise PermissionError("this folder is not accessible")
    ok = allowed_notes()
    pool = all_notes() if ok is None else sorted(ok)
    notes = [n for n in pool if (not folder or n.startswith(folder + "/")) and (sc == "all" or area_of(n) == sc)]
    return "\n".join(notes[:2000]) or "(empty)"


def write_area(a):
    """Area for create tools: explicit scope, else the project's hub location, else personal."""
    sc = scope_of(a, default="")
    if sc in FOLDERS:
        return sc
    if sc == "all" and str(a.get("scope", "")).strip():
        raise ValueError("for writing, scope must be personal or work")
    if a.get("project"):
        hub = clean_name(a["project"])
        for n in all_notes():
            if os.path.basename(n)[:-3] == hub and area_of(n) in FOLDERS:
                return area_of(n)
    return "personal"


def t_capture(a):
    title = clean_name(a.get("title", "")) or "Captured note"
    content = str(a.get("content", "")).rstrip()
    p = unique(FOLDERS[write_area(a)]["inbox"], title)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    today = datetime.date.today().isoformat()
    src = str(a.get("source", "")).replace('"', "'").strip()
    fm = ["---", f"created: {today}"] + ([f'source: "{src}"'] if src else []) + ["---"]
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(fm + [f"# {a.get('title') or title}", "", content, ""]))
    rel = os.path.relpath(p, VAULT).replace("\\", "/")
    log("mcp-capture", f"[[{rel[:-3]}]] created (MCP)")
    return f"created: {rel}"


def t_task(a):
    title = clean_name(a.get("title", ""))
    if not title:
        raise ValueError("title is required")
    if LOCK["projects"]:
        if not a.get("project"):
            if len(LOCK["projects"]) > 1:
                raise ValueError("project is required: " + ", ".join(LOCK["projects"]))
            a = dict(a, project=LOCK["projects"][0])
        check_project(a["project"])
    fm = ["---", "type: task", "status: todo"]
    pr = str(a.get("priority", "")).lower()
    if pr in ("high", "medium", "low"):
        fm.append(f"priority: {pr}")
    if a.get("project"):
        fm.append(f'project: "[[{clean_name(a["project"])}]]"')
    due = str(a.get("due", "")).strip()
    if due:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
            raise ValueError("due must be YYYY-MM-DD")
        fm.append(f"due: {due}")
    fm += [f"created: {datetime.date.today().isoformat()}", "---"]
    subs = [f"- [ ] {s}" for s in a.get("subtasks", []) or []] or ["- [ ] "]
    body = [f"# {title}", "", "## Description", str(a.get("description", "")).strip(), "", "## Subtasks", *subs, "", "## Notes", ""]
    folder = FOLDERS[write_area(a)]["tasks"]
    if a.get("project"):
        folder = folder + "/" + clean_name(a["project"])  # cards live in <tasks>/<Project>/
    p = unique(folder, title)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(fm + body))
    rel = os.path.relpath(p, VAULT).replace("\\", "/")
    log("mcp-task", f"[[{rel[:-3]}]] task card created (MCP)")
    return f"created: {rel}"


STR, INT = {"type": "string"}, {"type": "integer"}
# ------------------------------------------------------------------ skills as MCP prompts
SKILLS = os.path.join(VAULT, "skills")
CLAUDE_SKILLS = os.path.join(VAULT, ".claude", "skills")
# skills whose main job is changing existing notes; over MCP they can only propose the change
EDITING = {"sb-connect", "sb-distill", "sb-decide", "sb-experiment", "sb-inbox", "sb-ingest", "sb-lint", "sb-new", "sb-queue"}
MCP_PREAMBLE = """## You are running this workflow over MCP
The skill below was written for agents with direct access to the vault files. You reach the vault only through the `second-brain` MCP tools. Map the steps like this:

| In the skill | Over MCP |
|---|---|
| read `99 System/Index.md` | `vault_index` |
| `vault_tool.py search` | `vault_search` (then read the relevant sections with `vault_read_note` + offset/limit) |
| `vault_tool.py context` | `vault_note_context` |
| `vault_tool.py tasks [--project X]` | `vault_list_tasks` (`project`) |
| the file-reading tool | `vault_read_note` |
| a new task card | `vault_create_task` |
| a new note in the inbox | `vault_capture` |
| `--scope` | the tools' `scope` parameter |

**Not available over MCP:** editing, moving, renaming or deleting an existing note, `git mv`, `vault_tool.py lint / index / log / import`, writing new notes outside the inbox. When the skill asks for one of these, **do not pretend you did it**: show the change ready to apply (file path, which section, the text to add or change) and tell the user it has to be applied in Obsidian or by an agent with file access. MCP's create tools write the log themselves. Full vault rules: `vault_read_note` path=`CLAUDE.md`.
"""


def skill_names():
    try:
        return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))
    except OSError:
        return []


def skill_meta(path):
    """(frontmatter dict of simple `key: value` lines, body) of a SKILL.md."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return {}, ""
    m = FM_RE.match(text)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                try:
                    v = json.loads(v)
                except ValueError:
                    v = v[1:-1]
            if v:
                meta[k.strip()] = v
    return meta, (text[m.end():] if m else text).strip()


def core_rules():
    """Section 0 of CLAUDE.md (the hard rules), so a file-less agent still follows them."""
    try:
        text = open(os.path.join(VAULT, "CLAUDE.md"), encoding="utf-8").read()
    except OSError:
        return ""
    m = re.search(r"(?ms)^## 0\..*?(?=^## )", text)
    return m.group(0).strip() if m else ""


def skill_prompt(name, args=""):
    if name not in skill_names():
        raise LookupError(f"unknown skill: {name}")
    meta, body = skill_meta(os.path.join(SKILLS, name, "SKILL.md"))
    parts = [MCP_PREAMBLE]
    if name in EDITING:
        parts.append("> This skill mostly changes existing notes: over MCP, do the analysis and proposal part and present the changes as a plan ready for approval.\n")
    if LOCK["projects"]:
        parts.append(f"> This server is locked to these projects: {', '.join(LOCK['projects'])}. Do not look for other projects.\n")
    rules = core_rules()
    if rules:
        parts.append(rules + "\n")
    parts += [f"---\n# Skill: /{name}\n", body, "\n## User input\n", str(args).strip() or "(no input)"]
    return meta.get("description", ""), "\n".join(parts)


# Some clients (Claude Code) split the slash-command text on spaces and hand the words to the declared
# arguments in order; continuation slots keep the rest of the sentence instead of dropping it.
CONT_N = 30
CONT_ARGS = [{"name": f"w{i}", "description": "(rest of the input; leave empty)", "required": False} for i in range(2, CONT_N + 1)]


def joined_args(argmap):
    argmap = argmap or {}
    words = [str(argmap.get("args", "") or "")] + [str(argmap.get(f"w{i}", "") or "") for i in range(2, CONT_N + 1)]
    return " ".join(w for w in words if w.strip())


def prompt_list():
    out = []
    for n in skill_names():
        meta, _ = skill_meta(os.path.join(SKILLS, n, "SKILL.md"))
        hint, _ = skill_meta(os.path.join(CLAUDE_SKILLS, n, "SKILL.md"))
        desc = meta.get("description", "")
        if n in EDITING:
            desc += " (MCP: cannot change existing notes; proposes the change instead.)"
        out.append({"name": n, "description": desc,
                    "arguments": [{"name": "args", "description": hint.get("argument-hint", "Command input"), "required": False}] + CONT_ARGS})
    return out


def t_skill(a):
    name = str(a.get("name", "")).strip().lstrip("/")
    if not name:
        return "\n".join(f"/{p['name']} — {p['arguments'][0]['description']}" for p in prompt_list()) or "(no skills)"
    return skill_prompt(name, a.get("args", ""))[1]


SCOPE_PROP = {"type": "string", "enum": ["personal", "work", "all"],
              "description": "Area: personal (Personal/), work (Work/) or all. Reads default to all."}
S = lambda props, req=(): {"type": "object", "properties": dict(props, scope=SCOPE_PROP), "required": list(req)}
TOOLS = {
    "vault_index": (t_index, "Returns the vault catalog (99 System/Index.md): type, status and summary of every note; scope narrows it to the Personal or Work section. Read this first.", S({}), True),
    "vault_search": (t_search, "Ranked keyword search over note sections (accent-insensitive), limited by scope. Returns file paths and line numbers.", S({"query": STR, "k": INT}, ["query"]), True),
    "vault_read_note": (t_read, "Reads a note with line numbers. path: vault-relative path or note name. Use offset/limit to read a section.", S({"path": STR, "offset": INT, "limit": INT}, ["path"]), True),
    "vault_note_context": (t_context, "Frontmatter, heading outline, outgoing links and backlinks of a note.", S({"note": STR}, ["note"]), True),
    "vault_list_tasks": (t_tasks, "Board task cards (JSON): area, status, priority, dates, project. Filter with project and scope.", S({"project": STR}), True),
    "vault_list_notes": (t_list, "List of note files; narrow it with folder and scope.", S({"folder": STR}), True),
    "vault_skill": (t_skill, "Second Brain workflows (/sb-ask, /sb-brief, /sb-task …): with no name, lists them; with a name, returns that skill's instructions adapted for MCP, which you then follow. args: the command input. For clients without MCP prompts.", {"type": "object", "properties": {"name": STR, "args": STR}, "required": []}, True),
    "vault_capture": (t_capture, "Writes a NEW note to an inbox (never changes an existing note): scope=work -> Work/00 Inbox, otherwise Personal/00 Inbox.", S({"title": STR, "content": STR, "source": STR}, ["title", "content"]), False),
    "vault_create_task": (t_task, "Writes a NEW task card (status: todo) to Work/50 Tasks/<Project> or Personal/15 Tasks/<Project> (folder root without a project): by scope, else the project's area, else personal. priority: high|medium|low; due: YYYY-MM-DD (only if the user gave one).", S({"title": STR, "project": STR, "priority": STR, "due": STR, "description": STR, "subtasks": {"type": "array", "items": STR}}, ["title"]), False),
}


def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        return {"protocolVersion": ver, "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}},
                "serverInfo": {"name": "second-brain", "version": "1.0.0"},
                "instructions": "An Obsidian vault with two areas, Personal/ and Work/ (scope: personal | work | all). Start with vault_index, then vault_search and vault_read_note. "
                                "Write tools only create new notes/tasks; do not write unless the user asks." +
                                ((" This server is locked to these projects: " + ", ".join(LOCK["projects"]) +
                                  ". Other projects, tasks and notes are not visible; do not look for them.") if LOCK["projects"] else "")}
    if method == "ping":
        return {}
    if method == "prompts/list":
        return {"prompts": prompt_list()}
    if method == "prompts/get":
        p = msg.get("params") or {}
        desc, text = skill_prompt(str(p.get("name", "")), joined_args(p.get("arguments")))
        return {"description": desc, "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}
    if method == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s, "annotations": {"readOnlyHint": ro, "destructiveHint": False}}
                          for n, (_, d, s, ro) in TOOLS.items()]}
    if method == "tools/call":
        p = msg.get("params") or {}
        name = p.get("name")
        if name not in TOOLS:
            raise LookupError(f"unknown tool: {name}")
        try:
            text = TOOLS[name][0](p.get("arguments") or {})
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as e:  # tool errors are results, not protocol errors
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
    if mid is None:
        return None  # notification
    raise LookupError(f"unsupported method: {method}")


def main():
    parse_args(sys.argv[1:])
    stdin = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n"); stdout.flush()
            continue
        mid = msg.get("id")
        try:
            result = handle(msg)
            if mid is None:
                continue
            resp = {"jsonrpc": "2.0", "id": mid, "result": result}
        except LookupError as e:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": str(e)}}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}
        stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        stdout.flush()


if __name__ == "__main__":
    main()
