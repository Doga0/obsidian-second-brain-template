# -*- coding: utf-8 -*-
"""Temporal queries over the vault's git history (shared by vault_tool.py and the MCP server).

  history(note)      every saved version of a note: frontmatter changes (status proposed → accepted …)
                     and section-level changes (§Gerekçe +3/−1), newest last
  at(note, date)     the note as it was at the end of a date
  timeline(project)  one chronological list for a project: decisions (created, status changes, decided),
                     task cards (created, status changes), hub sections, Experiment Log rows, other notes

Commit messages of the auto-backup ("vault backup: …") carry no meaning, so the meaning is derived from the
diff of each version. Uncommitted changes in the working copy are shown as the last version.
The module is language-neutral: messages follow the vault's area folders (Kişisel/ → Turkish, else English).
"""
import datetime, os, re, subprocess

TXT = {
    "tr": {"created": "oluşturuldu", "deleted": "silindi", "renamed": "taşındı/yeniden adlandırıldı: {0}",
           "added": "§{0} eklendi", "removed": "§{0} kaldırıldı", "changed": "§{0} değişti (+{1}/−{2})",
           "fm": "{0}: {1} → {2}", "fm_new": "{0}: {1}", "fm_del": "{0} kaldırıldı", "body": "giriş metni değişti (+{0}/−{1})",
           "wc": "çalışma kopyası (commit edilmemiş)", "none": "bu aralıkta değişiklik yok", "no_git": "git geçmişi yok",
           "at_head": "# {0} — {1} itibarıyla (sürüm {2}, {3})", "at_none": "{0} tarihinde bu not yoktu",
           "decision": "karar", "task": "görev", "hub": "hub", "experiment": "deney", "note": "not",
           "exp_row": "Experiment Log'a satır: {0}", "trigger": "kaynak/tetikleyen: {0}", "decided": "karar tarihi (decided)",
           "tl_head": "# Zaman çizelgesi — {0}", "noise": "{0} küçük değişiklik gizlendi"},
    "en": {"created": "created", "deleted": "deleted", "renamed": "moved/renamed: {0}",
           "added": "§{0} added", "removed": "§{0} removed", "changed": "§{0} changed (+{1}/−{2})",
           "fm": "{0}: {1} → {2}", "fm_new": "{0}: {1}", "fm_del": "{0} removed", "body": "intro text changed (+{0}/−{1})",
           "wc": "working copy (not committed)", "none": "no changes in this range", "no_git": "no git history",
           "at_head": "# {0} — as of {1} (version {2}, {3})", "at_none": "this note did not exist on {0}",
           "decision": "decision", "task": "task", "hub": "hub", "experiment": "experiment", "note": "note",
           "exp_row": "Experiment Log row: {0}", "trigger": "source/trigger: {0}", "decided": "decision date (decided)",
           "tl_head": "# Timeline — {0}", "noise": "{0} minor changes hidden"},
}
WATCH = ("type", "status", "priority", "due", "project", "decided", "started", "completed", "origin", "topics")
EXP_HEADS = ("experiment log",)


class H:
    def __init__(self, vault):
        self.vault = vault
        self.L = "tr" if os.path.isdir(os.path.join(vault, "Kişisel")) else "en"

    def t(self, k, *a):
        return TXT[self.L][k].format(*a)

    # ------------------------------------------------------------ git
    def git(self, *args):
        r = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=self.vault, capture_output=True)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None

    def has_git(self):
        return self.git("rev-parse", "--is-inside-work-tree") is not None

    def versions(self, rel):
        """[(commit, iso_date, path_at_commit, status)] oldest first, following renames."""
        out = self.git("log", "--follow", "-M", "--format=@%H|%aI", "--name-status", "--", rel)
        if not out:
            return []
        res, cur = [], None
        for line in out.splitlines():
            if line.startswith("@"):
                h, d = line[1:].split("|", 1)
                cur = [h, d]
            elif line.strip() and cur:
                parts = line.split("\t")
                st, path = parts[0][0], parts[-1]
                res.append((cur[0], cur[1], path, st))
                cur = None
        return list(reversed(res))

    def show(self, commit, path):
        return self.git("show", f"{commit}:{path}")

    # ------------------------------------------------------------ parsing
    @staticmethod
    def split(text):
        m = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|\Z)", text or "", re.S)
        return (m.group(1), text[m.end():]) if m else ("", text or "")

    def fm(self, text):
        raw, _ = self.split(text)
        d, key = {}, None
        for line in raw.splitlines():
            m = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
            if m:
                key = m.group(1)
                d[key] = m.group(2).strip().strip('"')
            elif key and re.match(r"^\s*-\s", line):
                d[key] = (d[key] + ", " if d[key] else "") + line.strip()[1:].strip().strip('"')
        return d

    def sections(self, text):
        """{heading: body} with the text before the first heading under ''."""
        _, body = self.split(text)
        body = re.sub(r"(?ms)^```.*?^```[^\n]*$", lambda m: m.group(0).replace("#", "\u0000"), body)
        out, cur, buf = {}, "", []
        for line in body.replace("\r\n", "\n").split("\n"):
            m = re.match(r"^#{1,6} (.+?)\s*$", line)
            if m:
                out[cur] = "\n".join(buf).replace("\u0000", "#").strip()
                cur, buf = m.group(1).strip(), []
                while cur in out:
                    cur += " "
            else:
                buf.append(line)
        out[cur] = "\n".join(buf).replace("\u0000", "#").strip()
        return out

    @staticmethod
    def line_delta(a, b):
        a_l, b_l = [x for x in a.split("\n") if x.strip()], [x for x in b.split("\n") if x.strip()]
        sa, sb = set(a_l), set(b_l)
        return len([x for x in b_l if x not in sa]), len([x for x in a_l if x not in sb])

    def diff(self, old, new):
        """Human-readable changes between two versions of a note."""
        if old is None:
            return [self.t("created")]
        if new is None:
            return [self.t("deleted")]
        ch = []
        fo, fn = self.fm(old), self.fm(new)
        for k in WATCH:
            a, b = fo.get(k), fn.get(k)
            if a == b:
                continue
            ch.append(self.t("fm", k, a, b) if a and b else (self.t("fm_new", k, b) if b else self.t("fm_del", k)))
        so, sn = self.sections(old), self.sections(new)
        for h in sn:
            if h not in so and h:
                ch.append(self.t("added", h.strip()))
            elif h in so and so[h] != sn[h]:
                p, m = self.line_delta(so[h], sn[h])
                if p or m:
                    ch.append(self.t("body", p, m) if not h else self.t("changed", h.strip(), p, m))
        for h in so:
            if h not in sn and h:
                ch.append(self.t("removed", h.strip()))
        return ch

    # ------------------------------------------------------------ queries
    @staticmethod
    def day(d):
        return d[:10] if d else ""

    def in_range(self, d, since, until):
        return (not since or self.day(d) >= since) and (not until or self.day(d) <= until)

    def events(self, rel):
        """[(iso_date, short_commit, path, changes, old_text, new_text)] oldest first, incl. working copy."""
        vs = self.versions(rel)
        out, prev = [], None
        for h, d, path, st in vs:
            cur = None if st == "D" else self.show(h, path)
            changes = self.diff(prev, cur)
            if st == "R" and out and out[-1][2] != path:
                changes = [self.t("renamed", path)] + changes
            if changes:
                out.append((d, h[:7], path, changes, prev, cur))
            prev = cur
        full = os.path.join(self.vault, rel)
        if os.path.isfile(full):
            wc = open(full, encoding="utf-8", errors="replace").read()
            if prev is None or wc.replace("\r\n", "\n") != prev.replace("\r\n", "\n"):
                ch = self.diff(prev, wc)
                if ch:
                    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
                    out.append((now, self.t("wc"), rel, ch, prev, wc))
        return out

    def history(self, rel, since=None, until=None):
        if not self.has_git():
            return self.t("no_git")
        ev = [e for e in self.events(rel) if self.in_range(e[0], since, until)]
        if not ev:
            return self.t("none")
        lines = [f"# {rel}"]
        for d, h, path, ch, _, _ in ev:
            lines.append(f"- {d[:16].replace('T', ' ')} `{h}` — " + "; ".join(ch))
        return "\n".join(lines)

    def at(self, rel, date):
        if not self.has_git():
            return self.t("no_git")
        best = None
        for h, d, path, st in self.versions(rel):
            if self.day(d) <= date:
                best = (h, d, path, st)
        if not best or best[3] == "D":
            return self.t("at_none", date)
        text = self.show(best[0], best[2]) or ""
        return self.t("at_head", best[2], date, best[0][:7], best[1][:16].replace("T", " ")) + "\n\n" + text

    def timeline(self, project, notes, since=None, until=None, hub=None):
        """notes: [(rel, type)] belonging to the project; hub: the hub's rel path."""
        rows, hidden = [], 0
        for rel, typ in notes:
            kind = "hub" if rel == hub else {"decision": "decision", "task": "task"}.get(typ, "note")
            for d, h, path, ch, old, new in self.events(rel):
                name = os.path.basename(path)[:-3]
                if kind == "task":  # only lifecycle events for cards
                    ch = [c for c in ch if c == self.t("created") or c.startswith(("status:", "project:", "priority:", "due:"))]
                if kind == "hub":
                    for row in self.new_exp_rows(old, new):
                        rows.append((d, "experiment", name, [self.t("exp_row", row)]))
                    ch = [c for c in ch if not c.startswith("§Experiment Log")]
                if kind == "decision" and new is not None and old is None:
                    src = self.sections(new)
                    trig = [v for k, v in src.items() if k.strip().lower() in ("kaynak", "source")]
                    links = re.findall(r"\[\[([^\]|#]+)", trig[0]) if trig else []
                    if links:
                        ch = ch + [self.t("trigger", ", ".join(f"[[{x}]]" for x in links))]
                if not ch:
                    hidden += 1
                    continue
                rows.append((d, kind, name, ch))
            if kind == "decision":  # the decision date itself, when it predates the git history
                full = os.path.join(self.vault, rel)
                dec = self.fm(open(full, encoding="utf-8", errors="replace").read()).get("decided") if os.path.isfile(full) else None
                if dec and re.match(r"\d{4}-\d{2}-\d{2}", dec) and not any(r[2] == os.path.basename(rel)[:-3] and self.day(r[0]) == dec[:10] for r in rows):
                    rows.append((dec[:10] + "T00:00", "decision", os.path.basename(rel)[:-3], [self.t("decided")]))
        rows = [r for r in rows if self.in_range(r[0], since, until)]
        rows.sort(key=lambda r: r[0])
        out = [self.t("tl_head", project)]
        last_day = None
        for d, kind, name, ch in rows:
            if self.day(d) != last_day:
                last_day = self.day(d)
                out += ["", f"## {last_day}"]
            shown = ch if len(ch) <= 6 else ch[:6] + [f"+{len(ch) - 6}"]
            out.append(f"- {d[11:16] or '--:--'} · {self.t(kind)} · [[{name}]] — " + "; ".join(shown))
        if hidden:
            out += ["", f"*({self.t('noise', hidden)})*"]
        return "\n".join(out) if rows else self.t("none")

    def new_exp_rows(self, old, new):
        def rows(text):
            if not text:
                return []
            for k, v in self.sections(text).items():
                if k.strip().lower() in EXP_HEADS:
                    return [l.strip() for l in v.split("\n") if l.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", l.strip())][1:]
            return []
        before = set(rows(old))
        return [r for r in rows(new) if r not in before and r.strip("| ")]
