# -*- coding: utf-8 -*-
"""Second Brain MCP server (stdio, standard library only).

Exposes this vault to MCP clients (Claude Desktop, Claude Code, other agents) with the same
rules as CLAUDE.md:
  - protected folders (99 System/config.json -> "protected") are invisible: not listed, searched or read
  - read tools: index, search, read_note, note_context, list_tasks, list_notes
  - write tools only CREATE new notes (capture to 00 Inbox, task cards in 15 Tasks);
    they never overwrite, edit, move or delete, and every write is logged to 99 System/Log.md

Run:  python -X utf8 "99 System/scripts/vault_mcp.py"
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
HIDDEN = tuple(PROTECTED) + (".obsidian/", ".git/", ".claude/", ".trash/", "99 System/.integrity/")
INBOX, TASKS = "00 Inbox", "15 Tasks"
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
            if f.endswith(".md"):
                out.append(relroot + f)
    return out


def find(name):
    name = str(name).strip()
    try:
        full, rel = safe_path(name)
        if os.path.isfile(full):
            return rel
    except PermissionError:
        raise
    base = name.split("/")[-1]
    base = base[:-3] if base.endswith(".md") else base
    hits = [n for n in all_notes() if os.path.basename(n)[:-3].lower() == base.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError("several notes match: " + ", ".join(hits))
    raise FileNotFoundError("note not found: " + name)


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
def t_index(_):
    return open(os.path.join(VAULT, "99 System", "Index.md"), encoding="utf-8").read()[:MAX_READ]


def t_search(a):
    q = str(a.get("query", "")).strip()
    if not q:
        raise ValueError("query is required")
    return run_tool("search", q, "--k", str(int(a.get("k", 10))))


def t_read(a):
    rel = find(a.get("path") or a.get("note") or "")
    lines = open(os.path.join(VAULT, rel), encoding="utf-8", errors="replace").read().splitlines()
    off = max(0, int(a.get("offset", 1)) - 1)
    lim = int(a.get("limit", 0)) or len(lines)
    chunk = lines[off:off + lim]
    body = "\n".join(f"{off + i + 1}\t{l}" for i, l in enumerate(chunk))
    return f"# {rel} (lines {off + 1}-{off + len(chunk)} of {len(lines)})\n{body}"[:MAX_READ]


def t_context(a):
    return run_tool("context", find(a.get("note", ""))[:-3].split("/")[-1])


def t_tasks(a):
    args = ["tasks", "--json"]
    if a.get("project"):
        args[1:1] = ["--project", str(a["project"])]
    return run_tool(*args)


def t_list(a):
    folder = str(a.get("folder", "")).strip().strip("/")
    if folder and blocked(folder + "/"):
        raise PermissionError("this folder is not accessible")
    notes = [n for n in all_notes() if not folder or n.startswith(folder + "/")]
    return "\n".join(notes[:2000]) or "(empty)"


def t_capture(a):
    title = clean_name(a.get("title", "")) or "Captured note"
    content = str(a.get("content", "")).rstrip()
    p = unique(INBOX, title)
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
    p = unique(TASKS, title)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(fm + body))
    rel = os.path.relpath(p, VAULT).replace("\\", "/")
    log("mcp-task", f"[[{rel[:-3]}]] task card created (MCP)")
    return f"created: {rel}"


S = lambda props, req=(): {"type": "object", "properties": props, "required": list(req)}
STR, INT = {"type": "string"}, {"type": "integer"}
TOOLS = {
    "vault_index": (t_index, "Returns the vault catalog (99 System/Index.md): type, status and summary of every note. Read this first.", S({}), True),
    "vault_search": (t_search, "Ranked keyword search over note sections (accent-insensitive). Returns file paths and line numbers.", S({"query": STR, "k": INT}, ["query"]), True),
    "vault_read_note": (t_read, "Reads a note with line numbers. path: vault-relative path or note name. Use offset/limit to read a section.", S({"path": STR, "offset": INT, "limit": INT}, ["path"]), True),
    "vault_note_context": (t_context, "Frontmatter, heading outline, outgoing links and backlinks of a note.", S({"note": STR}, ["note"]), True),
    "vault_list_tasks": (t_tasks, "Board task cards (JSON): status, priority, dates, project. Filter with project.", S({"project": STR}), True),
    "vault_list_notes": (t_list, "List of note files; narrow it to a folder with folder.", S({"folder": STR}), True),
    "vault_capture": (t_capture, "Writes a NEW note to 00 Inbox (never changes an existing note). For capturing an idea or text the user asked for.", S({"title": STR, "content": STR, "source": STR}, ["title", "content"]), False),
    "vault_create_task": (t_task, "Writes a NEW task card to 15 Tasks (status: todo). priority: high|medium|low; due: YYYY-MM-DD (only if the user gave one).", S({"title": STR, "project": STR, "priority": STR, "due": STR, "description": STR, "subtasks": {"type": "array", "items": STR}}, ["title"]), False),
}


def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        return {"protocolVersion": ver, "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "second-brain", "version": "1.0.0"},
                "instructions": "A personal Obsidian vault. Start with vault_index, then vault_search and vault_read_note. "
                                "Write tools only create new notes/tasks; do not write unless the user asks."}
    if method == "ping":
        return {}
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
