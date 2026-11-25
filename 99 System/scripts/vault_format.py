# -*- coding: utf-8 -*-
"""Format check for vault notes (shared by vault_tool.py, the MCP edit tools and the Claude Code hook).

Settings in `99 System/config.json` (missing keys use the defaults below):
  format_check   true  -> writes that would introduce a format problem are refused (MCP), reported (hook, lint)
  title_heading  false -> the file name is the title (Obsidian's inline title); notes don't repeat it as `# H1`

Checks are about structure that tools and plugins rely on, not about style:
  bom · mixed line endings · unclosed or malformed frontmatter · duplicate frontmatter keys ·
  unclosed code fence · title repeated as H1 · the same heading repeated with an empty first section
  (a template pasted twice). Raw text inside notes (several H1s in a pasted AI chat) is not judged.

The module is language-neutral: messages follow the vault's area folders (Kişisel/ → Turkish, else English).
"""
import json, os, re

DEFAULTS = {"format_check": False, "title_heading": True}

MSG = {
    "tr": {
        "bom": "dosya BOM ile başlıyor",
        "eol_mixed": "karışık satır sonları (CRLF ve LF birlikte)",
        "fm_unclosed": "frontmatter kapanmamış (ikinci --- yok)",
        "fm_line": "frontmatter'da geçersiz satır: {0}",
        "fm_dup": "frontmatter alanı iki kez var: {0}",
        "fence": "kapanmamış kod bloğu (```)",
        "title_h1": "başlık dosya adı olarak gösteriliyor; notun içinde '# {0}' tekrarlanmamalı",
        "title_twice": "'# {0}' başlığı birden fazla kez var",
        "section_dup": "'{0}' başlığı tekrarlanıyor ve ilki boş (şablon iki kez eklenmiş olabilir)",
        "refused": "format kontrolü bu yazmayı reddetti",
    },
    "en": {
        "bom": "file starts with a BOM",
        "eol_mixed": "mixed line endings (CRLF and LF together)",
        "fm_unclosed": "frontmatter is not closed (no second ---)",
        "fm_line": "invalid frontmatter line: {0}",
        "fm_dup": "frontmatter key appears twice: {0}",
        "fence": "unclosed code block (```)",
        "title_h1": "the file name is shown as the title; the note shouldn't repeat '# {0}'",
        "title_twice": "the heading '# {0}' appears more than once",
        "section_dup": "the heading '{0}' is repeated and the first one is empty (template added twice?)",
        "refused": "the format check refused this write",
    },
}


def lang(vault):
    return "tr" if os.path.isdir(os.path.join(vault, "Kişisel")) else "en"


def load_config(vault):
    cfg = dict(DEFAULTS)
    try:
        with open(os.path.join(vault, "99 System", "config.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        for k in DEFAULTS:
            if isinstance(data.get(k), bool):
                cfg[k] = data[k]
    except (OSError, ValueError):
        pass
    return cfg


FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)(?:\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.S)
FM_LINE = re.compile(r"^(?:[A-Za-z_][\w-]*:.*|-\s.*|\s+.*|\s*#.*|\s*)$")


def split(text):
    """(frontmatter block or '', body)."""
    m = FM_RE.match(text)
    return (text[:m.end()], text[m.end():]) if m else ("", text)


def strip_fences(body):
    return re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", body)


def issues(text, name, cfg, L="en"):
    """List of (code, message) for one note. name = file name without .md."""
    t = MSG[L]
    out = []
    if text.startswith("﻿"):
        out.append(("bom", t["bom"]))
        text = text[1:]
    if "\r\n" in text and re.search(r"(?<!\r)\n", text):
        out.append(("eol_mixed", t["eol_mixed"]))
    fm, body = split(text)
    if re.match(r"---[ \t]*\r?\n", text) and not fm:
        out.append(("fm_unclosed", t["fm_unclosed"]))
        body = text
    if fm:
        keys = []
        for line in FM_RE.match(text).group(1).splitlines():
            if not FM_LINE.match(line):
                out.append(("fm_line", t["fm_line"].format(line.strip()[:60])))
            m = re.match(r"^([A-Za-z_][\w-]*):", line)
            if m:
                keys.append(m.group(1))
        for k in sorted({k for k in keys if keys.count(k) > 1}):
            out.append(("fm_dup", t["fm_dup"].format(k)))
    fences = [l for l in body.splitlines() if re.match(r"^\s{0,3}(```|~~~)", l)]
    if len(fences) % 2:
        out.append(("fence", t["fence"]))
    plain = strip_fences(body)
    h1 = [m.group(1).strip() for m in re.finditer(r"(?m)^# (.+?)\s*$", plain)]
    first = re.match(r"\s*# (.+?)[ \t]*(?:\r?\n|$)", plain)
    if not cfg.get("title_heading", True) and first and first.group(1).strip() == name:
        out.append(("title_h1", t["title_h1"].format(name)))
    if h1.count(name) > 1:
        out.append(("title_twice", t["title_twice"].format(name)))
    heads = list(re.finditer(r"(?m)^(#{1,6}) (.+?)\s*$", plain))
    for i, h in enumerate(heads[:-1]):
        nxt = heads[i + 1]
        same_later = any(x.group(1) == h.group(1) and x.group(2) == h.group(2) for x in heads[i + 1:])
        between = plain[h.end():nxt.start()]
        empty = not re.sub(r"<!--.*?-->|^\s*-\s*$|\s", "", between, flags=re.S | re.M)
        if same_later and empty and len(nxt.group(1)) <= len(h.group(1)):
            out.append(("section_dup", t["section_dup"].format(h.group(1) + " " + h.group(2))))
    seen, uniq = set(), []
    for o in out:
        if o not in seen:
            seen.add(o); uniq.append(o)
    return uniq


def new_issues(old, new, name, cfg, L="en"):
    before = set(issues(old, name, cfg, L)) if old is not None else set()
    return [i for i in issues(new, name, cfg, L) if i not in before]


def strip_title(text, name):
    """Remove a leading `# <name>` H1 (and the blank line after it) right after the frontmatter."""
    fm, body = split(text)
    m = re.match(r"([ \t]*\r?\n)*# (.+?)[ \t]*(\r?\n|$)([ \t]*\r?\n)?", body)
    if m and m.group(2).strip() == name:
        return fm + body[m.end():]
    return text


def fix(text, name, cfg):
    """Safe automatic fixes: BOM, mixed line endings (to the majority), repeated title H1."""
    if text.startswith("﻿"):
        text = text[1:]
    crlf = text.count("\r\n")
    lf = len(re.findall(r"(?<!\r)\n", text))
    if crlf and lf:
        text = text.replace("\r\n", "\n")
        if crlf > lf:
            text = text.replace("\n", "\r\n")
    if not cfg.get("title_heading", True):
        text = strip_title(text, name)
    return text
