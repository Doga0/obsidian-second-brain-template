# -*- coding: utf-8 -*-
"""Second Brain vault tool: deterministic helpers used by the /sb-* AI commands.
No dependencies beyond the Python 3.8+ standard library.

Usage (from the vault root):
  python "99 System/scripts/vault_tool.py" <command> [args]

Commands
  lint [--no-write]              Health check; writes 99 System/Health.md unless --no-write
  index                          Regenerate 99 System/Index.md (one-line catalog of every note)
  search <query> [--k N]         Ranked keyword search over note sections (accent-insensitive)
  context <note>                 Frontmatter, outline, outgoing links and backlinks of a note
  tasks [--project X] [--json]   Task board as text + last-7-days activity
  queue                          Pending AI requests (`ai:` property + AI Queue checklist)
  log <op> <text>                Append an entry to 99 System/Log.md
  stats                          Counts by type / status / folder
  protected-baseline             Record hashes of protected folders (see config.json)
  clean-examples [--yes]         List (or delete with --yes) notes marked `example: true`
  history <note> [--since D] [--until D]   Versions of a note: frontmatter and section changes (git)
  at <note> <YYYY-MM-DD>   The note as it was on that date
  timeline --project X [--since D] [--until D]   A project's decisions, tasks, hub and experiments on one timeline
  fmtcheck [notes] [--fix [--dry-run]] [--hook]  Format check (99 System/config.json: format_check, title_heading)
  import <file> [--json]         docx/xlsx/pptx/pdf/csv -> source note in the area's inbox (original kept in its attachments)

Areas and scope: the vault has two areas, Personal/ and Work/ (99 System, Home, Board are shared).
  --scope personal|work|all     limits search, tasks, queue, stats, lint and import (default all; import defaults to personal)

Protected folders (config.json -> "protected") are never parsed or written by this tool;
their files are only hashed so `lint` can prove they were not modified.
"""
import os, re, sys, json, math, hashlib, datetime, unicodedata
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vault_format as vf  # shared format check (config: 99 System/config.json)

VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CFG = vf.load_config(VAULT)
FLANG = vf.lang(VAULT)
os.chdir(VAULT)
SYSTEM = "99 System"
TEMPLATES = f"{SYSTEM}/Templates"
CONFIG = f"{SYSTEM}/config.json"
INTEGRITY = f"{SYSTEM}/.integrity/protected.sha256"
HEALTH = f"{SYSTEM}/Health.md"
INDEX = f"{SYSTEM}/Index.md"
LOG = f"{SYSTEM}/Log.md"
QUEUE_NOTE = f"{SYSTEM}/AI Queue.md"
TODAY = datetime.date.today()
GENERATED_NOTES = {f"{SYSTEM}/Index.md", f"{SYSTEM}/Health.md", f"{SYSTEM}/Log.md"}
AREAS = {"personal": "Personal", "work": "Work"}
AREA_FOLDERS = {
    "personal": {"inbox": "Personal/00 Inbox", "tasks": "Personal/15 Tasks", "attach": "Personal/60 Resources/Attachments"},
    "work": {"inbox": "Work/00 Inbox", "tasks": "Work/50 Tasks", "attach": "Work/60 Attachments"},
}
INBOXES = tuple(f["inbox"] + "/" for f in AREA_FOLDERS.values())
SCOPE = "all"


def parse_scope(v):
    k = (v or "").strip().lower()
    for names, val in ((("personal", "p"), "personal"), (("work", "w"), "work"), (("all", "both", ""), "all")):
        if k in names:
            return val
    raise SystemExit(f"unknown scope: {v} (personal | work | all)")


def area_of(p):
    for k, folder in AREAS.items():
        if p == folder or p.startswith(folder + "/"):
            return k
    return "shared"


def in_scope(p):
    return SCOPE == "all" or area_of(p) == SCOPE


def load_config():
    cfg = {"protected": [], "wip_limit": None}
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    except FileNotFoundError:
        pass
    cfg["protected"] = [p.strip("/").replace("\\", "/") for p in cfg.get("protected") or [] if p.strip("/")]
    return cfg


CFG = load_config()
PROTECTED = CFG["protected"]
WIP_LIMIT = CFG.get("wip_limit")

TYPES = {"project", "research", "task", "idea", "knowledge", "source", "resource", "moc",
         "system", "decision", "analysis", "meeting", "org"}
STATUS = {
    "task": {"backlog", "todo", "doing", "blocked", "done"},
    "project": {"active", "paused", "done", "archived"},
    "research": {"active", "paused", "done", "archived"},
    "knowledge": {"seed", "evergreen"},
    "idea": {"idea", "exploring", "promoted", "dropped"},
    "decision": {"proposed", "accepted", "rejected", "superseded"},
}
AI_ACTIONS = {"connect", "distill", "challenge", "summarize", "ingest", "brief"}
GENERATED = {INDEX, HEALTH, LOG}

# ------------------------------------------------------------------ files


def is_protected(p):
    return any(p == d or p.startswith(d + "/") for d in PROTECTED)


def all_files():
    out = []
    for root, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and (root != "." or d != "skills")]
        for f in fs:
            out.append(os.path.normpath(os.path.join(root, f)).replace("\\", "/"))
    return out


FILES = all_files()
NOTES = sorted(f for f in FILES if f.endswith(".md") and f != "AGENTS.md" and not is_protected(f))
_cache = {}


def text(p):
    if is_protected(p):
        raise RuntimeError("refusing to parse a protected folder")
    if p not in _cache:
        with open(p, encoding="utf-8", errors="replace") as fh:
            _cache[p] = fh.read()
    return _cache[p]


def frontmatter(p):
    t = text(p)
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", t, re.S)
    fm = {}
    if not m:
        return fm, t
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^\s+-\s+", line) and key:
            v = re.sub(r"^\s+-\s+", "", line).strip().strip('"').strip("'")
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(v)
            continue
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            key, v = mm.group(1), mm.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                fm[key] = [x.strip().strip('"').strip("'") for x in inner.split(",")] if inner else []
            else:
                fm[key] = v.strip('"').strip("'")
    return fm, t[m.end():]


def name_of(p):
    return os.path.splitext(os.path.basename(p))[0]


def is_template(p):
    return p.startswith(TEMPLATES + "/")


def mtime(p):
    return datetime.date.fromtimestamp(os.path.getmtime(p))


def link_target(v):
    return re.sub(r"[\[\]\"]", "", v or "").split("|")[0].split("#")[0].strip()


BY_NAME = defaultdict(list)
for f in FILES:
    BY_NAME[os.path.basename(f)].append(f)
    if f.endswith(".md"):
        BY_NAME[name_of(f)].append(f)
ALIASES = {}
for n in NOTES:
    al = frontmatter(n)[0].get("aliases", [])
    for a in (al if isinstance(al, list) else [al]):
        if a:
            ALIASES.setdefault(a, n)


def resolve(target):
    t = target.strip()
    if t in BY_NAME:
        return BY_NAME[t]
    cand = t if os.path.splitext(t)[1] else t + ".md"
    return [cand] if cand in FILES else []


def strip_code(t):
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", t)


LINK_RE = re.compile(r"!?\[\[([^\]]+?)\]\]")


def links(p):
    out = []
    for m in LINK_RE.finditer(strip_code(text(p))):
        raw = m.group(1).replace("\\|", "|")
        name, _, head = raw.split("|")[0].partition("#")
        out.append((name or name_of(p), head, raw))
    return out


def headings(p):
    out, fence = [], False
    for i, line in enumerate(text(p).splitlines(), 1):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if m:
                out.append((i, len(m.group(1)), m.group(2)))
    return out


def norm(s):
    s = unicodedata.normalize("NFKD", s.replace("İ", "i").replace("I", "i").replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def build_graph():
    out_links, back, broken, bad_head = defaultdict(set), defaultdict(list), [], []
    for n in NOTES:
        if is_template(n) or n in GENERATED_NOTES:
            continue  # generated catalogs link to everything; they'd hide orphans
        for name, head, raw in links(n):
            r = resolve(name)
            if not r:
                broken.append((n, raw))
                continue
            tgt = r[0]
            out_links[n].add(tgt)
            if tgt != n:
                back[tgt].append(n)
            if head and tgt.endswith(".md") and not is_protected(tgt):
                hs = [h for _, _, h in headings(tgt)]
                if any(part not in hs for part in head.split("#")):
                    bad_head.append((n, raw))
    return out_links, back, broken, bad_head

# ------------------------------------------------------------------ protected folders


def protected_hashes():
    return {f: hashlib.sha256(open(f, "rb").read()).hexdigest() for f in FILES if is_protected(f)}


def cmd_protected_baseline():
    if not PROTECTED:
        print("No protected folders configured in 99 System/config.json")
        return
    os.makedirs(os.path.dirname(INTEGRITY), exist_ok=True)
    h = protected_hashes()
    with open(INTEGRITY, "w", encoding="utf-8") as fh:
        for k in sorted(h):
            fh.write(f"{h[k]}  {k}\n")
    print(f"baseline recorded: {len(h)} files in {', '.join(PROTECTED)}")


def protected_check():
    if not PROTECTED:
        return None, ["no protected folders configured"]
    if not any(os.path.isdir(d) for d in PROTECTED):
        return None, ["protected folders not present on this device"]
    if not os.path.exists(INTEGRITY):
        return None, ["no baseline yet: run `protected-baseline`"]
    base = {}
    for line in open(INTEGRITY, encoding="utf-8"):
        if line.strip():
            h, p = line.rstrip("\n").split("  ", 1)
            base[p] = h
    now = protected_hashes()
    diffs = [f"changed: {p}" for p in base if p in now and now[p] != base[p]]
    diffs += [f"removed: {p}" for p in base if p not in now]
    diffs += [f"new: {p}" for p in now if p not in base]
    return (not diffs), diffs

# ------------------------------------------------------------------ lint


def cmd_lint(write=True):
    out_links, back, broken, bad_head = build_graph()
    issues = defaultdict(list)
    for n, raw in broken:
        issues["Broken links"].append(f"[[{name_of(n)}]] → `{raw}`")
    for n, raw in bad_head:
        issues["Heading links that don't resolve"].append(f"[[{name_of(n)}]] → `{raw}`")
    by_type = defaultdict(list)
    for n in NOTES:
        if is_template(n) or not in_scope(n):
            continue
        fm, body = frontmatter(n)
        typ = fm.get("type")
        in_inbox = n.startswith(INBOXES)
        if not typ:
            if not in_inbox and os.path.basename(n) not in ("CLAUDE.md", "README.md"):
                issues["Missing `type` (outside Inbox)"].append(f"[[{name_of(n)}]] — `{n}`")
        elif typ not in TYPES:
            issues["Unknown `type`"].append(f"[[{name_of(n)}]] — `{typ}`")
        else:
            by_type[typ].append((n, fm))
            st = fm.get("status")
            if typ in STATUS and st and st not in STATUS[typ]:
                issues["Unknown `status`"].append(f"[[{name_of(n)}]] — `{typ}`/`{st}`")
        if in_inbox and not os.path.basename(n).startswith("README"):
            age = (TODAY - mtime(n)).days
            if age >= 7:
                issues["Waiting in Inbox for 7+ days"].append(f"[[{name_of(n)}]] — {age} days")
        if fm.get("ai") and fm["ai"] not in AI_ACTIONS:
            issues["Unknown `ai` action"].append(f"[[{name_of(n)}]] — `{fm['ai']}` (valid: {', '.join(sorted(AI_ACTIONS))})")
        lines = text(n).count("\n")
        prompts = len(re.findall(r"^>[^\s\[!]", strip_code(body), flags=re.M))
        if fm.get("split") != "no" and (lines > 1500 or (prompts >= 2 and lines > 400)):
            issues["Split candidates (very long / multi-turn)"].append(f"[[{name_of(n)}]] — {lines} lines, {prompts} prompts")
    if CFG["format_check"]:
        for n in NOTES:
            if is_template(n) or not in_scope(n):
                continue
            for _, msg in vf.issues(open(n, encoding="utf-8", errors="replace", newline="").read(), os.path.basename(n)[:-3], CFG, FLANG):
                issues["Format problems"].append(f"[[{name_of(n)}]] — {msg}")
    # orphans
    skip = {"Home.md", "Board.md", "CLAUDE.md", "README.md"}
    for n in NOTES:
        if is_template(n) or not in_scope(n) or n.startswith(SYSTEM + "/") or n.startswith(INBOXES) or os.path.basename(n) in skip:
            continue
        if frontmatter(n)[0].get("type") in ("decision", "task", "analysis"):
            continue  # shown through embedded Bases / boards
        if not back.get(n):
            issues["Orphan notes (no incoming links)"].append(f"[[{name_of(n)}]]")
    # stale hubs
    for typ in ("project", "research"):
        for n, fm in by_type[typ]:
            if fm.get("status") != "active":
                continue
            folder = os.path.dirname(n)
            last = max(mtime(f) for f in FILES if f.startswith(folder + "/"))
            if (TODAY - last).days > 30:
                issues["Active hubs unchanged for 30+ days"].append(f"[[{name_of(n)}]] — last change {last}")
    # tasks
    hubs = {name_of(n) for t in ("project", "research") for n, _ in by_type[t]}
    doing = []
    for n, fm in by_type["task"]:
        st, due, proj = fm.get("status"), (fm.get("due") or "")[:10], link_target(fm.get("project"))
        if st != "done" and due and due < TODAY.isoformat():
            issues["Overdue tasks"].append(f"[[{name_of(n)}]] — due {due} ({proj or 'no project'})")
        if proj and proj not in hubs:
            issues["Tasks linked to a missing project"].append(f"[[{name_of(n)}]] → `{proj}`")
        if st == "blocked":
            issues["Blocked tasks (info)"].append(f"[[{name_of(n)}]]")
        if st == "doing":
            doing.append(n)
    if WIP_LIMIT and len(doing) > WIP_LIMIT:
        issues[f"WIP limit exceeded (doing > {WIP_LIMIT})"].append(", ".join(f"[[{name_of(n)}]]" for n in doing))
    # duplicate names
    for k, v in BY_NAME.items():
        if k.endswith(".md") and len(v) > 1 and not any(is_protected(x) for x in v):
            issues["Duplicate file names (ambiguous links)"].append(", ".join(f"`{x}`" for x in v))
    pending = [n for n, fm in by_type["decision"] if fm.get("status") == "proposed"]
    seeds = [n for n, fm in by_type["knowledge"] if fm.get("status") == "seed"]
    ok, diffs = protected_check()
    q = queue_items()
    per_area = Counter(area_of(n) for n in NOTES if not is_template(n))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prot = "✅ unchanged" if ok else (f"⚠️ {len(diffs)} differences" if ok is False else "— " + diffs[0])
    rep = ["---", "type: system", "generated: true", "---", "# Vault Health", "",
           f"> [!info] Generated by `vault_tool.py lint` at {stamp}. Don't edit by hand; run `/sb-lint` to refresh.", "",
           "| Indicator | Value |", "|---|---|",
           f"| Scope | {SCOPE} |",
           f"| Notes | {sum(per_area.values())} (personal {per_area['personal']} · work {per_area['work']} · shared {per_area['shared']}) |",
           f"| Issue categories | {len(issues)} |",
           f"| Decisions awaiting approval | {len(pending)} |",
           f"| `seed` knowledge notes | {len(seeds)} |",
           f"| AI queue | {len(q)} |",
           f"| Protected folders | {prot} |", ""]
    if not issues:
        rep += ["✅ No structural issues found.", ""]
    for k, v in issues.items():
        rep += [f"## {k} ({len(v)})"] + [f"- {x}" for x in v[:60]] + ([f"- … +{len(v) - 60}"] if len(v) > 60 else []) + [""]
    if ok is False:
        rep += ["## Protected folder differences", "*If you made these changes yourself, run `protected-baseline`.*"] + [f"- {d}" for d in diffs[:30]] + [""]
    if pending:
        rep += ["## Decisions awaiting approval"] + [f"- [[{name_of(n)}]]" for n in pending] + [""]
    if write and SCOPE == "all":
        with open(HEALTH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(rep))
    print(json.dumps({"issues": {k: len(v) for k, v in issues.items()}, "pending_decisions": len(pending),
                      "seed_notes": len(seeds), "queue": len(q), "protected_ok": ok,
                      "scope": SCOPE, "notes": dict(per_area)}, ensure_ascii=False, indent=1))
    if not write:
        print("\n".join(rep))

# ------------------------------------------------------------------ index


def summary_of(fm, body):
    if fm.get("summary"):
        return fm["summary"]
    m = re.search(r"\*\*What:\*\*\s*(.+)", body)
    s = m.group(1) if m else ""
    if not s:
        for line in body.splitlines():
            l = line.strip()
            if l and not l.startswith(("#", "---", "```", "|", "![", "> [!")):
                s = l.lstrip("> ").strip()
                break
    s = re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"[*_`]", "", s)
    return (s[:157] + "…") if len(s) > 160 else s


def cmd_index():
    areas = defaultdict(lambda: defaultdict(list))
    for n in NOTES:
        if is_template(n) or n in GENERATED:
            continue
        fm, body = frontmatter(n)
        areas[area_of(n)][fm.get("type", "untyped")].append((n, fm, body))
    order = ["moc", "project", "research", "task", "decision", "meeting", "org", "knowledge", "idea", "source", "analysis", "resource", "system", "untyped"]
    title = {"moc": "Maps (MOC)", "project": "Projects", "research": "Research", "task": "Tasks", "decision": "Decisions",
             "meeting": "Meetings", "org": "Organizations & people",
             "knowledge": "Knowledge", "idea": "Ideas", "source": "Sources", "analysis": "Analyses",
             "resource": "Resources", "system": "System", "untyped": "Inbox / untyped"}
    area_title = {"personal": "Personal", "work": "Work", "shared": "Shared (system)"}
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    out = ["---", "type: system", "generated: true", "---", *(["# Index", ""] if CFG["title_heading"] else []),
           f"> [!info] Generated by `vault_tool.py index` at {stamp}. AI commands read this catalog first. Don't edit by hand.", ""]
    total = 0
    for area in ("personal", "work", "shared"):
        groups = areas.get(area)
        if not groups:
            continue
        out += [f"# {area_title[area]} ({sum(len(v) for v in groups.values())})", ""]
        for g in order + [k for k in groups if k not in order]:
            if g not in groups:
                continue
            total += len(groups[g])
            out.append(f"## {area_title[area]} · {title.get(g, g)} ({len(groups[g])})")
            for n, fm, body in sorted(groups[g], key=lambda x: x[0]):
                extra = [x for x in (fm.get("status"), ("↑ " + link_target(fm["project"])) if fm.get("project") else None) if x]
                meta = f" *({' · '.join(extra)})*" if extra else ""
                out.append(f"- [[{name_of(n)}]]{meta} — {summary_of(fm, body)}")
            out.append("")
    with open(INDEX, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print(f"index written: {total} notes")

# ------------------------------------------------------------------ search / context


def sections(n):
    lines = text(n).splitlines()
    bounds = [(1, 0, name_of(n))] + headings(n)
    for i, (ln, _, h) in enumerate(bounds):
        end = bounds[i + 1][0] - 1 if i + 1 < len(bounds) else len(lines)
        yield ln, h, "\n".join(lines[ln - 1:end])


TOKEN = re.compile(r"[a-z0-9][a-z0-9\-_.]*[a-z0-9]|[a-z0-9]")


def cmd_search(q, k=12):
    qt = [t for t in TOKEN.findall(norm(q)) if len(t) > 1]
    if not qt:
        print("empty query")
        return
    docs = []
    for n in NOTES:
        if is_template(n) or n in GENERATED or not in_scope(n):
            continue
        for ln, h, body in sections(n):
            toks = TOKEN.findall(norm(body))
            docs.append((n, ln, h, body, Counter(toks), len(toks)))
    N = len(docs)
    avg = sum(d[5] for d in docs) / max(N, 1)
    df = Counter()
    for d in docs:
        for t in set(qt):
            if any(tok.startswith(t) for tok in d[4]):
                df[t] += 1
    scored = []
    for n, ln, h, body, c, L in docs:
        s = 0.0
        for t in qt:
            tf = sum(v for tok, v in c.items() if tok.startswith(t))
            if not tf:
                continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * L / avg))
            if t in norm(h) or t in norm(name_of(n)):
                s += idf * 1.5
        covered = sum(1 for t in qt if any(tok.startswith(t) for tok in c))
        s *= (covered / len(qt)) ** 1.5
        if s > 0:
            scored.append((s, n, ln, h, body))
    scored.sort(reverse=True)
    for s, n, ln, h, body in scored[:k]:
        nb = norm(body)
        pos = min([nb.find(t) for t in qt if nb.find(t) >= 0] or [0])
        snip = re.sub(r"\s+", " ", body[max(0, pos - 80): pos + 220]).strip()
        print(f"{s:6.2f}  {n}:{ln}  §{h}\n        {snip}\n")


def find_note(q):
    r = resolve(q) or ([ALIASES[q]] if q in ALIASES else [])
    return r or [n for n in NOTES if norm(q) in norm(name_of(n)) and in_scope(n)]


def cmd_context(q):
    r = find_note(q)
    if not r:
        print("note not found:", q)
        return
    if len(r) > 1:
        print("multiple matches:", *r, sep="\n  ")
        return
    n = r[0]
    out_links, back, _, _ = build_graph()
    fm, _ = frontmatter(n)
    print(f"# {n}\nlines: {text(n).count(chr(10))}  modified: {mtime(n)}")
    print("frontmatter:", json.dumps(fm, ensure_ascii=False))
    print("\noutline:")
    for ln, lvl, h in headings(n):
        print(f"  {'  ' * (lvl - 1)}L{ln} {h[:100]}")
    print("\noutgoing:", *sorted(name_of(x) for x in out_links.get(n, [])), sep="\n  ")
    print("\nbacklinks:")
    for b in sorted(set(back.get(n, []))):
        ctx = next((re.sub(r"\s+", " ", l.strip())[:180] for l in text(b).splitlines() if f"[[{name_of(n)}" in l), "")
        print(f"  {name_of(b)} :: {ctx}")

# ------------------------------------------------------------------ tasks / queue / log / stats


def cmd_fmtcheck(args):
    """Format check. --hook: Claude Code PostToolUse hook (stdin JSON); --fix [--dry-run]: safe fixes."""
    import subprocess
    if "--hook" in args:
        if not CFG["format_check"]:
            sys.exit(0)
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            sys.exit(0)
        ti = data.get("tool_input") or {}
        path = ti.get("file_path") or ti.get("path") or ""
        if not path.endswith(".md"):
            sys.exit(0)
        full = os.path.abspath(path)
        if os.path.commonpath([full, VAULT]) != VAULT or not os.path.isfile(full):
            sys.exit(0)
        r = os.path.relpath(full, VAULT).replace("\\", "/")
        if r.startswith((".", "skills/")) or is_template(r):
            sys.exit(0)
        old = subprocess.run(["git", "show", f"HEAD:{r}"], cwd=VAULT, capture_output=True)
        old = old.stdout.decode("utf-8", "replace") if old.returncode == 0 else None
        new = open(full, encoding="utf-8", errors="replace", newline="").read()
        probs = vf.new_issues(old, new, os.path.basename(r)[:-3], CFG, FLANG)
        if probs:
            sys.stderr.write(f"{'Format check'} ({r}):\n" + "\n".join(f"- {m}" for _, m in probs)
                             + f"\n{'For the safe fixes run'}: python -X utf8 \"99 System/scripts/vault_tool.py\" fmtcheck --fix \"{r}\"\n")
            sys.exit(2)
        sys.exit(0)
    paths = [x for x in args if not x.startswith("--")]
    targets = [x.replace("\\", "/") for x in paths] or [n for n in NOTES if in_scope(n) and not is_template(n)]
    fixing, dry = "--fix" in args, "--dry-run" in args
    if not CFG["format_check"] and not paths and not fixing:
        print('format_check is off (99 System/config.json)')
    found = 0
    for n in targets:
        if not os.path.isfile(n):
            continue
        raw = open(n, encoding="utf-8", errors="replace", newline="").read()
        name = os.path.basename(n)[:-3]
        if fixing:
            new = vf.fix(raw, name, CFG)
            if new != raw:
                found += 1
                print(f"{'would fix' if dry else 'fixed'}: {n}")
                if not dry:
                    open(n, "w", encoding="utf-8", newline="").write(new)
            continue
        for _, m in vf.issues(raw, name, CFG, FLANG):
            found += 1
            print(f"{n} :: {m}")
    if not found and not fixing:
        print('no format problems')
    if fixing and found and not dry:
        cmd_log("fmtcheck", f"{found} {'fixed'}")


def _opt(a, flag):
    if flag in a:
        i = a.index(flag)
        v = a[i + 1] if i + 1 < len(a) else ""
        del a[i:i + 2]
        return v
    return None


def _one_note(q):
    r = find_note(q)
    if not r:
        print('note not found' + ": " + q); sys.exit(1)
    if len(r) > 1:
        print('several notes match' + ": " + ", ".join(r)); sys.exit(1)
    return r[0]


def project_notes(project):
    """(hub rel, [(rel, type)]) for a project: hub folder, its task folder and notes whose `project` is the hub."""
    hub = None
    for n in NOTES:
        fm, _ = frontmatter(n)
        if fm.get("type") in ("project", "research") and name_of(n).lower() == project.lower():
            hub = n
    if not hub:
        return None, []
    name = name_of(hub)
    folder = os.path.dirname(hub) if os.path.basename(os.path.dirname(hub)) == name else None
    tasks = tuple(f"{f['tasks']}/{name}/" for f in AREA_FOLDERS.values())
    out = []
    for n in NOTES:
        fm, _ = frontmatter(n)
        proj = re.sub(r"[\[\]\"]", "", fm.get("project") or "").split("|")[0].strip()
        if n == hub or (folder and n.startswith(folder + "/")) or n.startswith(tasks) or proj == name:
            out.append((n, fm.get("type", "")))
    return hub, out


def cmd_history(a):
    import vault_history
    h = vault_history.H(VAULT)
    since, until = _opt(a, "--since"), _opt(a, "--until")
    print(h.history(_one_note(" ".join(a)), since, until))


def cmd_at(a):
    import vault_history
    date = a[-1] if a and re.fullmatch(r"\d{4}-\d{2}-\d{2}", a[-1]) else None
    if not date:
        print('date must be YYYY-MM-DD'); sys.exit(1)
    print(vault_history.H(VAULT).at(_one_note(" ".join(a[:-1])), date))


def cmd_timeline(a):
    import vault_history
    since, until, project = _opt(a, "--since"), _opt(a, "--until"), _opt(a, "--project") or " ".join(a)
    hub, notes = project_notes(project)
    if not hub:
        print('project not found' + ": " + project); sys.exit(1)
    print(vault_history.H(VAULT).timeline(name_of(hub), notes, since, until, hub))


def task_rows(project=None):
    rows = []
    for n in NOTES:
        if is_template(n) or not in_scope(n):
            continue
        fm, body = frontmatter(n)
        if fm.get("type") != "task":
            continue
        proj = link_target(fm.get("project"))
        if project and norm(proj) != norm(project):
            continue
        subs = re.findall(r"^\s*- \[(.)\] \S", body, flags=re.M)
        rows.append({"task": name_of(n), "path": n, "area": area_of(n), "project": proj, "status": fm.get("status", ""),
                     "priority": fm.get("priority", ""), "due": (fm.get("due") or "")[:10],
                     "started": (fm.get("started") or "")[:10], "completed": (fm.get("completed") or "")[:10],
                     "modified": mtime(n).isoformat(),
                     "subtasks": f"{sum(1 for s in subs if s != ' ')}/{len(subs)}" if subs else ""})
    return rows


def cmd_tasks(project=None, as_json=False):
    rows = task_rows(project)
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    week_ago = (TODAY - datetime.timedelta(days=7)).isoformat()
    soon = (TODAY + datetime.timedelta(days=7)).isoformat()
    by_proj = defaultdict(list)
    for r in rows:
        by_proj[("Work · " if r["area"] == "work" else "Personal · " if r["area"] == "personal" else "") + (r["project"] or "(no project)")].append(r)
    for p in sorted(by_proj):
        rs = by_proj[p]
        print(f"## {p} — {sum(1 for r in rs if r['status'] == 'done')}/{len(rs)} done")
        for st in ["doing", "blocked", "todo", "backlog", "done"]:
            for r in sorted((x for x in rs if x["status"] == st), key=lambda x: (x["priority"] or "z", x["due"] or "9999")):
                flag = ""
                if r["due"] and r["status"] != "done":
                    flag = " ⚠️ OVERDUE" if r["due"] < TODAY.isoformat() else (" ⏰ soon" if r["due"] <= soon else "")
                print(f"  [{st:7}] {r['task']}" + (f" · {r['priority']}" if r["priority"] else "")
                      + (f" · due {r['due']}" if r["due"] else "") + (f" · ☑ {r['subtasks']}" if r["subtasks"] else "") + flag)
    done = sum(1 for r in rows if r["completed"] and r["completed"] >= week_ago)
    started = sum(1 for r in rows if r["started"] and r["started"] >= week_ago and r["status"] != "done")
    print(f"\nLast 7 days: {done} done, {started} started and still in progress. Open: {sum(1 for r in rows if r['status'] != 'done')}")


def queue_items():
    items = []
    for n in NOTES:
        if is_template(n) or not in_scope(n):
            continue
        fm, _ = frontmatter(n)
        if fm.get("ai"):
            items.append(("property", n, fm["ai"], fm.get("ai_note", "")))
    if os.path.exists(QUEUE_NOTE):
        for i, line in enumerate(text(QUEUE_NOTE).splitlines(), 1):
            m = re.match(r"^\s*- \[ \] (.+)$", line)
            if m and not m.group(1).strip().startswith("<"):
                items.append(("checklist", f"{QUEUE_NOTE}:{i}", m.group(1).strip(), ""))
    return items


def cmd_queue():
    items = queue_items()
    if not items:
        print("AI queue is empty.")
    for kind, where, what, note in items:
        print(f"[{kind}] {where} :: {what}" + (f" — {note}" if note else ""))


def cmd_log(op, msg):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if not os.path.exists(LOG):
        head = "---\ntype: system\n---\n# Log\n\n> [!info] Chronological record of every change made by the AI commands (newest at the bottom).\n\n"
        if not CFG["title_heading"]:
            head = vf.strip_title(head, "Log")
        open(LOG, "w", encoding="utf-8").write(head)
    raw = open(LOG, "rb").read()
    crlf = raw.count(b"\r\n")
    eol = "\r\n" if crlf > raw.count(b"\n") - crlf else "\n"  # keep the file's (majority) line endings
    with open(LOG, "a", encoding="utf-8", newline="") as fh:
        fh.write(f"- `{stamp}` **{op}** — {msg}{eol}")
    print("logged")


def cmd_stats():
    c, s, fo = Counter(), Counter(), Counter()
    for n in NOTES:
        if is_template(n) or not in_scope(n):
            continue
        fm, _ = frontmatter(n)
        c[fm.get("type", "—")] += 1
        s[(fm.get("type", "—"), fm.get("status", "—"))] += 1
        fo["/".join(n.split("/")[:2]) if area_of(n) != "shared" else (n.split("/")[0] if "/" in n else "(root)")] += 1
    print("type:", dict(c))
    print("status:", {f"{a}/{b}": v for (a, b), v in s.items()})
    print("folder:", dict(fo))


def cmd_clean_examples(yes=False):
    ex = [n for n in NOTES if not is_template(n) and str(frontmatter(n)[0].get("example", "")).lower() == "true"]
    if not ex:
        print("No example notes found.")
        return
    for n in ex:
        print(("deleting " if yes else "would delete ") + n)
    if not yes:
        print(f"\n{len(ex)} example notes. Run again with --yes to delete them.")
        return
    for n in ex:
        os.remove(n)
        NOTES.remove(n)
        FILES.remove(n)
        _cache.pop(n, None)
    for d in sorted({os.path.dirname(n) for n in ex}, key=len, reverse=True):
        if d and os.path.isdir(d) and not os.listdir(d) and d.startswith(("Personal/20 Projects/", "Personal/30 Research/", "Work/10 Projects/", "Personal/15 Tasks/", "Work/50 Tasks/")):
            os.rmdir(d)
    cmd_log("clean-examples", f"{len(ex)} example notes deleted")
    cmd_index()


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(0)
    explicit_scope = None
    if "--scope" in a:
        i = a.index("--scope")
        explicit_scope = parse_scope(a[i + 1] if i + 1 < len(a) else "")
        SCOPE = explicit_scope
        a = a[:i] + a[i + 2:]
    cmd = a[0]
    if cmd == "lint":
        cmd_lint(write="--no-write" not in a)
    elif cmd == "index":
        cmd_index()
    elif cmd == "search":
        k = 12
        if "--k" in a:
            i = a.index("--k")
            k = int(a[i + 1])
            a = a[:i] + a[i + 2:]
        cmd_search(" ".join(a[1:]), k)
    elif cmd == "context":
        cmd_context(" ".join(a[1:]))
    elif cmd == "tasks":
        proj = a[a.index("--project") + 1] if "--project" in a else None
        cmd_tasks(proj, "--json" in a)
    elif cmd == "queue":
        cmd_queue()
    elif cmd == "log":
        cmd_log(a[1], " ".join(a[2:]))
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "protected-baseline":
        cmd_protected_baseline()
    elif cmd == "clean-examples":
        cmd_clean_examples("--yes" in a)
    elif cmd == "history":
        cmd_history(a[1:])
    elif cmd == "at":
        cmd_at(a[1:])
    elif cmd == "timeline":
        cmd_timeline(a[1:])
    elif cmd == "fmtcheck":
        cmd_fmtcheck(a[1:])
    elif cmd == "import":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import vault_import
        files = [x for x in a[1:] if not x.startswith("--")]
        if not files:
            print("usage: import <file> [--json]")
            sys.exit(1)
        for f in files:
            try:
                area = explicit_scope if explicit_scope in AREA_FOLDERS else "personal"
                res = vault_import.import_file(f, VAULT, PROTECTED, AREA_FOLDERS[area]["inbox"], AREA_FOLDERS[area]["attach"])
            except Exception as e:  # report, keep going
                res = {"error": f"{f}: {e}"}
            if "note" in res:
                cmd_log("import", f"{res['attachment']} -> [[{res['note'][:-3]}]]" + (f" ({res['warning']})" if res["warning"] else ""))
            print(json.dumps(res, ensure_ascii=False) if "--json" in a else (res.get("error") or f"note: {res['note']}" + (f"\nwarning: {res['warning']}" if res["warning"] else "")))
    else:
        print(__doc__)
        sys.exit(1)
