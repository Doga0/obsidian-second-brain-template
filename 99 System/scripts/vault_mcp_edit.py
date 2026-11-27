# -*- coding: utf-8 -*-
"""Narrow edit tools for the Second Brain MCP server (vault_mcp.py).

They let agents that only reach the vault through MCP run the editing workflows (connect, distill, decide,
experiment, inbox, ingest, lint, new, queue, task updates) while the vault rules are enforced here, not left
to the agent:
  - raw content of `type: source` notes never changes (only frontmatter and the context callout)
  - moves, task/decision status changes and task project changes need confirm=true; dry_run=true previews any edit
  - frontmatter keys come from the CLAUDE.md schema and values are validated; projects must exist
  - links need a reason; links and moves across the two areas need allow_cross_area=true
  - expected_sha (from vault_read_note) refuses an edit when the note changed since it was read
  - project lock and protected folders apply; every write is logged
There is no delete, merge or rename tool on purpose.

The module is language-neutral: messages follow the vault's area names (Kişisel/İş → Turkish, else English).
"""
import datetime, difflib, hashlib, os, re

M = None          # the vault_mcp module, set by tools()
LANG = "en"

TXT = {
    "tr": {
        "not_found": "not bulunamadı: {0}",
        "exists": "bu adda not zaten var: {0}",
        "similar_hub": "benzer bir proje zaten var: {0}. Yine de açmak için confirm=true",
        "hub_exists": "proje zaten var: {0}",
        "bad_folder": "klasör geçersiz: {0}. Bir alanın (Kişisel/, İş/) mevcut bir kategori klasörü altında olmalı, en fazla Alan/Kategori/Proje",
        "tasks_folder": "görev kartları için vault_create_task kullan",
        "bad_key": "bilinmeyen frontmatter alanı: {0}. İzinli: {1}",
        "bad_value": "{0} için geçersiz değer: {1}. Geçerli: {2}",
        "bad_date": "{0} YYYY-MM-DD olmalı",
        "source_body": "type: source notunun ham içeriği değiştirilemez (yalnızca frontmatter ve Bağlam callout'u)",
        "frontmatter": "frontmatter için vault_set_property kullan",
        "no_match": "metin bulunamadı (birebir eşleşmeli)",
        "many_match": "metin {0} kez geçiyor; daha uzun, tekil bir parça ver",
        "sha": "not okunduktan sonra değişmiş (sha {0} ≠ {1}); yeniden oku",
        "reason": "link için gerekçe (reason) zorunlu",
        "cross": "farklı alanlar arasında link/taşıma ({0} → {1}) yalnızca kullanıcı isterse: allow_cross_area=true",
        "confirm": "Bu işlem onay gerektirir ({0}). Plan aşağıda; kullanıcı onaylarsa confirm=true ile tekrar çağır.",
        "lock_hub": "proje kilidinde yalnızca kilitli projelerin hub'ı açılabilir: {0}",
        "lock_note": "proje kilidinde yeni not kilitli bir projeye bağlanmalı (project): {0}",
        "lock_lint": "proje kilidinde lint çalıştırılamaz (tüm vault'u raporlar)",
        "same": "değişiklik yok",
        "dup_link": "{0} zaten bu bölümde bağlı",
        "preview": "ÖNİZLEME (yazılmadı)",
        "done": "güncellendi",
        "created": "oluşturuldu",
        "moved": "taşındı",
        "template": "şablon bulunamadı: {0}. Var olanlar: {1}",
        "context": "Bağlam",
        "related": "İlgili",
        "index": "Index güncellendi",
        "why_status": "status değişikliği",
        "why_project": "görev kartının projesi değişiyor, kart yeni proje klasörüne taşınır",
        "why_move": "taşıma",
        "why_similar": "benzer ad",
        "not_editable": "bu not MCP ile düzenlenemez (yalnızca Kişisel/ ve İş/ notları ile AI Queue): {0}",
        "moc_readonly": "proje kilidinde MOC'lar salt okunur: {0}. Projeyi MOC'a bağlamak için hub'ın topics alanını doldur; MOC'a satır eklemeyi kullanıcıya öner",
        "no_moc": "MOC bulunamadı: {0}. Yakın adlar: {1}",
    },
    "en": {
        "not_found": "note not found: {0}",
        "exists": "a note with this name already exists: {0}",
        "similar_hub": "a similar project already exists: {0}. Pass confirm=true to create it anyway",
        "hub_exists": "project already exists: {0}",
        "bad_folder": "invalid folder: {0}. It must be under an existing category folder of an area (Personal/, Work/), at most Area/Category/Project",
        "tasks_folder": "use vault_create_task for task cards",
        "bad_key": "unknown frontmatter key: {0}. Allowed: {1}",
        "bad_value": "invalid value for {0}: {1}. Valid: {2}",
        "bad_date": "{0} must be YYYY-MM-DD",
        "source_body": "the raw content of a type: source note can't change (only frontmatter and the Context callout)",
        "frontmatter": "use vault_set_property for frontmatter",
        "no_match": "text not found (must match exactly)",
        "many_match": "the text occurs {0} times; give a longer, unique snippet",
        "sha": "the note changed since it was read (sha {0} ≠ {1}); read it again",
        "reason": "a link needs a reason",
        "cross": "links/moves across areas ({0} → {1}) only if the user asks: allow_cross_area=true",
        "confirm": "This needs approval ({0}). The plan is below; if the user approves, call again with confirm=true.",
        "lock_hub": "under a project lock only the locked projects' hubs can be created: {0}",
        "lock_note": "under a project lock a new note must belong to a locked project (project): {0}",
        "lock_lint": "lint can't run under a project lock (it reports on the whole vault)",
        "same": "no change",
        "dup_link": "{0} is already linked in this section",
        "preview": "PREVIEW (not written)",
        "done": "updated",
        "created": "created",
        "moved": "moved",
        "template": "template not found: {0}. Available: {1}",
        "context": "Context",
        "related": "Related",
        "index": "Index updated",
        "why_status": "status change",
        "why_project": "the task card's project changes, the card moves to the new project folder",
        "why_move": "move",
        "why_similar": "similar name",
        "not_editable": "this note can't be edited over MCP (only notes in Personal/ and Work/, and the AI Queue): {0}",
        "moc_readonly": "under a project lock MOCs are read-only: {0}. Link the project to a MOC through the hub's topics; suggest the MOC line to the user",
        "no_moc": "MOC not found: {0}. Close names: {1}",
    },
}


def t(key, *a):
    return TXT[LANG][key].format(*a)


# ------------------------------------------------------------------ schema (CLAUDE.md §2)
STATUS = {
    "task": ["todo", "doing", "done", "backlog", "blocked"],
    "project": ["active", "paused", "done", "archived"],
    "research": ["active", "paused", "done", "archived"],
    "knowledge": ["seed", "evergreen"],
    "idea": ["idea", "exploring", "promoted", "dropped"],
    "decision": ["proposed", "accepted", "rejected", "superseded"],
}
TYPES = ["project", "research", "task", "idea", "knowledge", "source", "resource", "moc", "system", "decision",
         "analysis", "meeting", "org", "memory"]
ENUMS = {"type": TYPES, "priority": ["high", "medium", "low"], "origin": ["user", "ai-suggestion"],
         "ai": ["connect", "distill", "challenge", "summarize", "ingest", "brief"]}
DATES = {"due", "started", "completed", "decided", "created", "reviewed"}
LISTS = {"topics", "aliases"}
KEYS = ["type", "status", "priority", "due", "started", "completed", "project", "topics", "source", "origin",
        "ai", "ai_note", "aliases", "summary", "decided", "created", "reviewed"]
PLACEHOLDERS = ("KLASÖR-YOLU", "FOLDER-PATH")
NAME_HOLDERS = ("PROJE-ADI", "PROJECT-NAME")


# ------------------------------------------------------------------ helpers
def today():
    return datetime.date.today().isoformat()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def read(rel):
    with open(os.path.join(M.VAULT, rel), encoding="utf-8", newline="") as fh:
        return fh.read()


def write(rel, text):
    full = os.path.join(M.VAULT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def nl(text):
    return "\r\n" if "\r\n" in text else "\n"


SHARED_EDITABLE = ("99 System/AI Queue.md",)  # outside the areas only the AI queue can be edited


def target(a, key="note", editable=True):
    """Resolve an existing, visible note (lock + protected folders apply through M.find)."""
    name = a.get(key) or a.get("path") or ""
    try:
        rel = M.find(name)
    except FileNotFoundError:
        raise FileNotFoundError(t("not_found", name))
    if editable and M.area_of(rel) not in M.FOLDERS and rel not in SHARED_EDITABLE:
        raise PermissionError(t("not_editable", rel))
    if editable and M.LOCK["projects"] and M.head_of(rel)[0] == "moc":
        raise PermissionError(t("moc_readonly", rel))  # under a lock maps are visible but read-only
    return rel


def resolve_moc(name):
    """Canonical name of an existing MOC (type: moc); unknown names are refused with close matches."""
    name = re.sub(r"^\[\[|\]\]$", "", str(name).strip()).split("|")[0].strip()
    mocs = {os.path.basename(n)[:-3]: n for n in M.all_notes() if M.head_of(n)[0] == "moc"}
    for m in mocs:
        if m.casefold() == name.casefold():
            return m
    folded = {m.casefold(): m for m in mocs}
    close = [folded[c] for c in difflib.get_close_matches(name.casefold(), list(folded), n=3, cutoff=0.6)]
    raise ValueError(t("no_moc", name, ", ".join(close) or "-"))


def check_sha(a, text):
    exp = str(a.get("expected_sha", "") or "").strip()
    if exp and exp != sha(text):
        raise ValueError(t("sha", exp, sha(text)))


def split_fm(text):
    """(frontmatter block incl. both --- lines, rest). No frontmatter -> ('', text)."""
    m = re.match(r"\A---\r?\n.*?\r?\n---[ \t]*(\r?\n|\Z)", text, re.S)
    return (m.group(0), text[m.end():]) if m else ("", text)


def note_type(text):
    fm, _ = split_fm(text)
    m = re.search(r"(?m)^type:\s*\"?([\w-]+)", fm)
    return m.group(1) if m else ""


def fm_get(text, key):
    fm, _ = split_fm(text)
    m = re.search(rf"(?m)^{re.escape(key)}:[ \t]*(.*)$", fm)
    return m.group(1).strip().strip('"') if m else None


def context_block(text):
    """(start, end) of the `> [!abstract] …` context callout in text, or None."""
    m = re.search(r"(?m)^> \[!abstract\][^\n]*\n?(?:^>[^\n]*(?:\n|$))*", text)
    return (m.start(), m.end()) if m else None


def editable_spans(text):
    """Spans of a note's body that edits may touch. Source notes: only the context callout."""
    fm, _ = split_fm(text)
    if note_type(text) != "source":
        return [(len(fm), len(text))]
    cb = context_block(text)
    return [cb] if cb else []


def check_span(text, start, end):
    fm, _ = split_fm(text)
    if start < len(fm):
        raise PermissionError(t("frontmatter"))
    if not any(s <= start and end <= e for s, e in editable_spans(text)):
        raise PermissionError(t("source_body"))


def diff(rel, old, new):
    d = difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{rel}", f"b/{rel}", lineterm="", n=2)
    return "\n".join(list(d)[:200])


def area_name(rel):
    return M.area_of(rel)


def link_targets(text):
    return [x.strip().split("/")[-1] for x in re.findall(r"\[\[([^\]|#^]+)", text)]


def check_cross(rel, new_text, a):
    """New links from an area note to a note of the other area need allow_cross_area."""
    if a.get("allow_cross_area"):
        return
    src = area_name(rel)
    if src not in M.FOLDERS:
        return
    by_base = {}
    for n in M.all_notes():
        by_base.setdefault(os.path.basename(n)[:-3].casefold(), []).append(n)
    for name in link_targets(new_text):
        for n in by_base.get(name.casefold(), []):
            dst = area_name(n)
            if dst in M.FOLDERS and dst != src:
                raise PermissionError(t("cross", src, dst))


def finish(a, rel, old, new, op, msg, need=None):
    """Preview, ask for confirmation, or write + log."""
    if old == new:
        return t("same")
    M.fmt_guard(old, new, os.path.basename(rel)[:-3])
    d = diff(rel, old, new)
    if a.get("dry_run"):
        return f"{t('preview')}\n{d}"
    if need and not a.get("confirm"):
        return f"{t('confirm', need)}\n{d}"
    write(rel, new)
    M.log(op, f"[[{rel[:-3]}]] {msg} (MCP)")
    return f"{t('done')}: {rel} (sha {sha(new)})\n{d}"


def yaml_value(v):
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{}&*!|>'\"%@`]", s) or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def set_fm(text, key, value, remove=False):
    """Set/remove one frontmatter key (scalar or list), keeping every other line as is."""
    eol = nl(text)
    fm, body = split_fm(text)
    lines = fm.splitlines()[1:-1] if fm else []
    out, i, found = [], 0, False
    while i < len(lines):
        line = lines[i]
        if re.match(rf"^{re.escape(key)}:", line):
            found = True
            i += 1
            while i < len(lines) and re.match(r"^\s+-|^\s{2,}\S", lines[i]):
                i += 1
            if not remove:
                out += render(key, value)
            continue
        out.append(line)
        i += 1
    if not found and not remove:
        out += render(key, value)
    if not out and not fm:
        return text
    return "---" + eol + eol.join(out) + eol + "---" + eol + (body if fm else text)


def render(key, value):
    if isinstance(value, list):
        return [f"{key}: []"] if not value else [f"{key}:"] + [f"  - {yaml_value(v)}" for v in value]
    return [f"{key}: {yaml_value(value)}"]


def validate(key, value, ntype):
    if key not in KEYS:
        raise ValueError(t("bad_key", key, ", ".join(KEYS)))
    if key in LISTS:
        value = value if isinstance(value, list) else [x.strip() for x in str(value).split(",") if x.strip()]
        if key == "topics":
            value = [f"[[{resolve_moc(v)}]]" for v in value]
        return value
    value = str(value).strip()
    if key in DATES and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(t("bad_date", key))
    if key in ENUMS and value not in ENUMS[key]:
        raise ValueError(t("bad_value", key, value, ", ".join(ENUMS[key])))
    if key == "status" and ntype in STATUS and value not in STATUS[ntype]:
        raise ValueError(t("bad_value", key, value, ", ".join(STATUS[ntype])))
    if key == "project":
        name = re.sub(r"^\[\[|\]\]$", "", value)
        name = M.resolve_project(name)
        M.check_project(name)
        return f"[[{name}]]"
    return value


def check_folder(folder):
    folder = str(folder).replace("\\", "/").strip().strip("/")
    parts = folder.split("/")
    if M.blocked(folder + "/") or len(parts) < 2 or len(parts) > 3 or M.area_of(folder) not in M.FOLDERS:
        raise ValueError(t("bad_folder", folder))
    if not os.path.isdir(os.path.join(M.VAULT, parts[0], parts[1])):
        raise ValueError(t("bad_folder", folder))
    if folder.startswith(M.FOLDERS[M.area_of(folder)]["tasks"]):
        raise ValueError(t("tasks_folder"))
    return folder


def section_end(text, heading):
    """Insert position at the end of the section whose heading text is `heading` (any level), else None."""
    _, body = split_fm(text)
    off = len(text) - len(body)
    hs = list(re.finditer(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$", body))
    for i, h in enumerate(hs):
        if h.group(2).strip().casefold() == heading.strip().casefold():
            level = len(h.group(1))
            end = len(body)
            for h2 in hs[i + 1:]:
                if len(h2.group(1)) <= level:
                    end = h2.start()
                    break
            seg = body[h.end():end]
            return off + h.end() + len(seg.rstrip()), off + h.start(), off + end
    return None


# ------------------------------------------------------------------ tools
def t_create_note(a):
    title = M.clean_name(a.get("title", ""))
    if not title:
        raise ValueError("title")
    folder = check_folder(a.get("folder", ""))
    rel = f"{folder}/{title}.md"
    if os.path.exists(os.path.join(M.VAULT, rel)) or any(os.path.basename(n)[:-3].casefold() == title.casefold() for n in M.all_notes()):
        raise FileExistsError(t("exists", title))
    props = dict(a.get("properties") or {})
    tpl = str(a.get("template", "") or "").strip()
    if tpl:
        tdir = os.path.join(M.VAULT, "99 System", "Templates")
        avail = sorted(f[:-3] for f in os.listdir(tdir) if f.endswith(".md"))
        if tpl not in avail:
            raise ValueError(t("template", tpl, ", ".join(avail)))
        text = open(os.path.join(tdir, tpl + ".md"), encoding="utf-8").read()
        text = text.replace("{{title}}", title).replace("{{date}}", today())
        if "{{project}}" in text:  # Project Memory: the project it belongs to
            proj = re.sub(r"[\[\]\"]", "", str(props.get("project") or "")).split("|")[0].strip()
            proj = proj or (M.LOCK["projects"][0] if len(M.LOCK["projects"]) == 1 else os.path.basename(folder))
            text = text.replace("{{project}}", proj)
        for ph in PLACEHOLDERS:
            text = text.replace(ph, folder)
        for ph in NAME_HOLDERS:
            text = text.replace(ph, title)
    else:
        text = f"# {title}\n"
    titled = M.fmt_cfg()["title_heading"]  # false: the file name is the title, no `# H1` in the note
    if not titled:
        text = M.vf.strip_title(text, title)
    ntype = props.get("type") or note_type(text)
    is_hub = ntype in ("project", "research")
    need = None
    if is_hub:
        hubs = M.project_hubs()
        if any(h.casefold() == title.casefold() for h in hubs):
            raise FileExistsError(t("hub_exists", title))
        close = difflib.get_close_matches(title.casefold(), [h.casefold() for h in hubs], n=3, cutoff=0.85)
        if close:
            need = t("why_similar") + ": " + ", ".join(close)
        if M.LOCK["projects"] and title.casefold() not in {p.casefold() for p in M.LOCK["projects"]}:
            raise PermissionError(t("lock_hub", ", ".join(M.LOCK["projects"])))
    elif M.LOCK["projects"]:
        if not (props.get("project") or a.get("project")):
            if len(M.LOCK["projects"]) > 1:
                raise ValueError(t("lock_note", ", ".join(M.LOCK["projects"])))
            props["project"] = M.LOCK["projects"][0]
    if a.get("project") and not is_hub:
        props["project"] = a["project"]
    if "created" not in props and fm_get(text, "created") in (None, ""):
        props["created"] = today()
    for k, v in props.items():
        text = set_fm(text, k, validate(k, v, ntype))
    if ntype == "decision" and "decided" not in props and fm_get(text, "status") not in ("accepted", "rejected", "superseded"):
        text = set_fm(text, "decided", None, remove=True)  # a proposed decision has no decision date yet
    content = str(a.get("content", "") or "").strip()
    if content and tpl and re.search(r"(?m)^#{1,3} ", content):
        # content with its own headings is the filled-in body: it replaces the template body (frontmatter kept)
        fm, _ = split_fm(text)
        if titled and not re.match(r"#\s", content):
            content = f"# {title}\n\n" + content
        if not titled:
            content = M.vf.strip_title(content, title)
        text = fm + content + "\n"
    elif content:
        if not titled:
            content = M.vf.strip_title(content, title).strip()
        text = (text.rstrip("\n") + "\n\n" if text.strip() else text) + content + "\n"
    check_cross(rel, text, a)
    M.fmt_guard(None, text, title)
    if a.get("dry_run"):
        return f"{t('preview')}: {rel}\n{text[:4000]}"
    if need and not a.get("confirm"):
        return f"{t('confirm', need)}\n{rel}"
    write(rel, text)
    M.log("mcp-create", f"[[{rel[:-3]}]] {t('created')} (MCP)")
    return f"{t('created')}: {rel} (sha {sha(text)})"


def t_set_property(a):
    rel = target(a)
    old = read(rel)
    check_sha(a, old)
    key = str(a.get("key", "")).strip()
    ntype = note_type(old)
    if key not in KEYS:
        raise ValueError(t("bad_key", key, ", ".join(KEYS)))
    if a.get("remove"):
        return finish(a, rel, old, set_fm(old, key, None, remove=True), "mcp-property", f"-{key}")
    value = validate(key, a.get("value", ""), ntype)
    new = set_fm(old, key, value)
    need, move_to = None, None
    cur = fm_get(old, key)
    if key == "status" and ntype in ("task", "decision") and cur != value:
        need = t("why_status")
        if ntype == "task" and value == "done" and not fm_get(old, "completed"):
            new = set_fm(new, "completed", today())
        if ntype == "task" and value == "doing" and not fm_get(old, "started"):
            new = set_fm(new, "started", today())
        if ntype == "decision" and value == "accepted" and not fm_get(old, "decided"):
            new = set_fm(new, "decided", today())
    if key == "project" and ntype == "task":
        name = value[2:-2]
        area = M.area_of(M.project_hubs()[name])
        root = M.FOLDERS[area]["tasks"] if area in M.FOLDERS else M.FOLDERS[M.area_of(rel)]["tasks"]
        dest = f"{root}/{M.clean_name(name)}/{os.path.basename(rel)}"
        if dest != rel:
            need, move_to = t("why_project") + f" → {dest}", dest
    out = finish(a, rel, old, new, "mcp-property", f"{key}: {value}", need)
    if move_to and a.get("confirm") and not a.get("dry_run") and old != new:
        out += "\n" + do_move(rel, move_to)
    return out


def t_edit_text(a):
    rel = target(a)
    old = read(rel)
    check_sha(a, old)
    find_s, repl = str(a.get("old", "")), str(a.get("new", ""))
    if "\r\n" in old:
        find_s, repl = find_s.replace("\r\n", "\n").replace("\n", "\r\n"), repl.replace("\r\n", "\n").replace("\n", "\r\n")
    n = old.count(find_s) if find_s else 0
    if n == 0:
        raise ValueError(t("no_match"))
    if n > 1:
        raise ValueError(t("many_match", n))
    i = old.index(find_s)
    check_span(old, i, i + len(find_s))
    new = old[:i] + repl + old[i + len(find_s):]
    added = set(link_targets(repl)) - set(link_targets(find_s))
    if added:
        check_cross(rel, " ".join(f"[[{x}]]" for x in added), a)
    return finish(a, rel, old, new, "mcp-edit", "metin düzenlendi" if LANG == "tr" else "text edited")


def insert_in_section(rel, old, heading, block, a):
    eol = nl(old)
    block = block.strip("\n").replace("\r\n", "\n").replace("\n", eol)
    pos = section_end(old, heading)
    if pos:
        at = pos[0]
        check_span(old, at, at)
        return old[:at] + eol + block + old[at:]
    if note_type(old) == "source":
        raise PermissionError(t("source_body"))
    return old.rstrip("\r\n") + eol + eol + f"## {heading}" + eol + block + eol


def t_append(a):
    rel = target(a)
    old = read(rel)
    check_sha(a, old)
    heading, text = str(a.get("heading", "")).strip(), str(a.get("text", ""))
    if not heading or not text.strip():
        raise ValueError("heading, text")
    check_cross(rel, text, a)
    new = insert_in_section(rel, old, heading, text, a)
    return finish(a, rel, old, new, "mcp-append", f"§{heading} +{len(text.strip().splitlines())}")


def t_add_link(a):
    rel = target(a)
    old = read(rel)
    check_sha(a, old)
    dest = target(a, "target", editable=False)
    reason = str(a.get("reason", "")).strip()
    if not reason:
        raise ValueError(t("reason"))
    name = os.path.basename(dest)[:-3]
    check_cross(rel, f"[[{name}]]", a)
    line = f"- [[{name}]] — {reason}"
    if note_type(old) == "source":  # only the context callout may change
        cb = context_block(old)
        if not cb:
            raise PermissionError(t("source_body"))
        if f"[[{name}]]" in old[cb[0]:cb[1]]:
            return t("dup_link", name)
        eol = nl(old)
        seg = old[cb[0]:cb[1]].rstrip("\r\n")
        new = old[:cb[0]] + seg + eol + "> " + line + eol + old[cb[1]:]
    else:
        heading = str(a.get("heading", "") or t("related"))
        pos = section_end(old, heading)
        if pos and f"[[{name}]]" in old[pos[1]:pos[2]]:
            return t("dup_link", name)
        new = insert_in_section(rel, old, heading, line, a)
    return finish(a, rel, old, new, "mcp-link", f"+[[{name}]]")


def t_set_context(a):
    rel = target(a)
    old = read(rel)
    check_sha(a, old)
    eol = nl(old)
    body = [l.strip() for l in str(a.get("text", "")).replace("\r\n", "\n").split("\n")]
    block = f"> [!abstract] {t('context')}" + eol + eol.join("> " + l if l else ">" for l in body) + eol
    cb = context_block(old)
    if cb:
        new = old[:cb[0]] + block + old[cb[1]:]
    else:
        fm, rest = split_fm(old)
        h1 = re.match(r"#[ \t][^\n]*\n", rest)
        at = len(fm) + (h1.end() if h1 else 0)
        new = old[:at] + eol + block + eol + old[at:].lstrip("\r\n") if h1 else old[:at] + block + eol + old[at:]
    check_cross(rel, str(a.get("text", "")), a)
    return finish(a, rel, old, new, "mcp-context", t("context"))


def do_move(rel, dest):
    if os.path.exists(os.path.join(M.VAULT, dest)):
        raise FileExistsError(t("exists", dest))
    os.makedirs(os.path.dirname(os.path.join(M.VAULT, dest)), exist_ok=True)
    os.replace(os.path.join(M.VAULT, rel), os.path.join(M.VAULT, dest))
    try:
        os.rmdir(os.path.dirname(os.path.join(M.VAULT, rel)))  # only if now empty
    except OSError:
        pass
    M.log("mcp-move", f"[[{dest[:-3]}]] ← {rel} (MCP)")
    return f"{t('moved')}: {rel} → {dest}"


def t_move_note(a):
    rel = target(a)
    check_sha(a, read(rel))
    folder = check_folder(a.get("folder", ""))
    dest = f"{folder}/{os.path.basename(rel)}"
    if dest == rel:
        return t("same")
    src_area, dst_area = M.area_of(rel), M.area_of(dest)
    if src_area in M.FOLDERS and dst_area != src_area and not a.get("allow_cross_area"):
        raise PermissionError(t("cross", src_area, dst_area))
    if os.path.exists(os.path.join(M.VAULT, dest)):
        raise FileExistsError(t("exists", dest))
    plan = f"{rel} → {dest}"
    if a.get("dry_run"):
        return f"{t('preview')}\n{plan}"
    if not a.get("confirm"):
        return f"{t('confirm', t('why_move'))}\n{plan}"
    return do_move(rel, dest)


def t_maintain(a):
    action = str(a.get("action", "index")).strip()
    if action == "index":
        M.run_tool("index")
        return t("index")
    if action == "lint":
        if M.LOCK["projects"]:
            raise PermissionError(t("lock_lint"))
        return M.run_tool("lint", "--scope", M.scope_of(a))[:20000]
    raise ValueError("action: index | lint")


# ------------------------------------------------------------------ registration
def tools(mod):
    """Tool table entries for vault_mcp.TOOLS."""
    global M, LANG
    M = mod
    LANG = "tr" if any(k in M.AREAS for k in ("kişisel", "iş")) else "en"
    STR, BOOL = {"type": "string"}, {"type": "boolean"}
    common = {"expected_sha": STR, "dry_run": BOOL}
    obj = lambda props, req: {"type": "object", "properties": props, "required": req}
    D = {
        "tr": {
            "create": "YENİ not oluşturur (üzerine yazmaz). folder: alan/kategori[/proje] (örn. Kişisel/40 Knowledge, Kişisel/20 Projects/<Ad>). template: 99 System/Templates'teki ad (Project Hub, Research Hub, Knowledge Note, Decision, Analysis, MOC, Meeting, Org, Source Note, Project Memory); yer tutucular doldurulur. content başlık (##) içeriyorsa şablonun gövdesinin yerine geçer (doldurulmuş şablon), yoksa sona eklenir. properties: frontmatter (şema dışı alan reddedilir). Proje hub'ı oluşturmak da bununla (template=Project Hub). Kilitte not kilitli projeye bağlanır.",
            "prop": "Frontmatter alanı ayarlar/kaldırır (şemaya göre doğrulanır; project var olmalı). Görev/karar status değişikliği ve görev kartının project değişikliği confirm=true ister; görevde done→completed, doing→started, kararda accepted→decided otomatik eklenir.",
            "edit": "Bir notta birebir ve tekil bir metin parçasını değiştirir (tablo satırı doldurma, checklist işaretleme…). Frontmatter için vault_set_property. type: source notlarında yalnızca Bağlam callout'u düzenlenebilir.",
            "append": "Bir başlığın (heading) altındaki bölümün sonuna metin ekler; başlık yoksa sona ## başlık açar. Mevcut metni silmez.",
            "link": "Nota gerekçeli link satırı ekler: '- [[target]] — reason' (varsayılan bölüm: İlgili). Source notlarında Bağlam callout'una eklenir. Alanlar arası link allow_cross_area ister.",
            "context": "Notun '> [!abstract] Bağlam' callout'unu oluşturur veya değiştirir (source notlarında gövdeye dokunmadan).",
            "move": "Notu başka bir klasöre taşır (ad aynı kalır, üzerine yazmaz). Her zaman confirm=true ister; alanlar arası taşıma allow_cross_area ister.",
            "maintain": "action=index: Index.md'yi yeniden üretir. action=lint: sağlık raporu (Health.md); proje kilidinde kapalı.",
            "common": " expected_sha: vault_read_note'un verdiği sha (not değiştiyse reddeder). dry_run=true: yazmadan diff gösterir.",
        },
        "en": {
            "create": "Creates a NEW note (never overwrites). folder: area/category[/project] (e.g. Personal/40 Knowledge, Personal/20 Projects/<Name>). template: a name from 99 System/Templates (Project Hub, Research Hub, Knowledge Note, Decision, Analysis, MOC, Meeting, Org, Source Note, Project Memory); placeholders are filled. If content has headings (##) it replaces the template body (a filled-in template), otherwise it is appended. properties: frontmatter (keys outside the schema are refused). Also creates project hubs (template=Project Hub). Under a lock the note belongs to a locked project.",
            "prop": "Sets/removes a frontmatter key (validated against the schema; project must exist). Task/decision status changes and a task card's project change need confirm=true; task done→completed, doing→started and decision accepted→decided are added automatically.",
            "edit": "Replaces an exact, unique piece of text in a note (fill a table row, tick a checklist item…). Use vault_set_property for frontmatter. In type: source notes only the Context callout can be edited.",
            "append": "Appends text at the end of the section under a heading; if the heading is missing, adds a ## heading at the end. Never removes text.",
            "link": "Adds a link line with a reason: '- [[target]] — reason' (default section: Related). In source notes it goes into the Context callout. Links across areas need allow_cross_area.",
            "context": "Creates or replaces the note's '> [!abstract] Context' callout (in source notes without touching the body).",
            "move": "Moves a note to another folder (same name, never overwrites). Always needs confirm=true; moving across areas needs allow_cross_area.",
            "maintain": "action=index: rebuilds Index.md. action=lint: health report (Health.md); disabled under a project lock.",
            "common": " expected_sha: the sha from vault_read_note (refuses if the note changed). dry_run=true: shows the diff without writing.",
        },
    }[LANG]
    c = D["common"]
    return {
        "vault_create_note": (t_create_note, D["create"] + c, obj({"title": STR, "folder": STR, "template": STR, "content": STR, "project": STR,
                                                                    "properties": {"type": "object"}, "confirm": BOOL, "allow_cross_area": BOOL, **common}, ["title", "folder"]), False),
        "vault_set_property": (t_set_property, D["prop"] + c, obj({"note": STR, "key": STR, "value": {"type": ["string", "array"]}, "remove": BOOL,
                                                                   "confirm": BOOL, **common}, ["note", "key"]), False),
        "vault_edit_text": (t_edit_text, D["edit"] + c, obj({"note": STR, "old": STR, "new": STR, "allow_cross_area": BOOL, **common}, ["note", "old", "new"]), False),
        "vault_append": (t_append, D["append"] + c, obj({"note": STR, "heading": STR, "text": STR, "allow_cross_area": BOOL, **common}, ["note", "heading", "text"]), False),
        "vault_add_link": (t_add_link, D["link"] + c, obj({"note": STR, "target": STR, "reason": STR, "heading": STR, "allow_cross_area": BOOL, **common}, ["note", "target", "reason"]), False),
        "vault_set_context": (t_set_context, D["context"] + c, obj({"note": STR, "text": STR, "allow_cross_area": BOOL, **common}, ["note", "text"]), False),
        "vault_move_note": (t_move_note, D["move"] + c, obj({"note": STR, "folder": STR, "confirm": BOOL, "allow_cross_area": BOOL, **common}, ["note", "folder"]), False),
        "vault_maintain": (t_maintain, D["maintain"], obj({"action": {"type": "string", "enum": ["index", "lint"]}, "scope": STR}, ["action"]), False),
    }
