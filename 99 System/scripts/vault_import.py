# -*- coding: utf-8 -*-
"""Convert docx / xlsx / pptx / pdf / csv files into Markdown source notes (standard library only).

Used by `vault_tool.py import <file>` and by the Second Brain Tools plugin.
- The original file is kept (copied into 60 Resources/Attachments if it lives outside the vault).
- The note goes to 00 Inbox as `type: source`; the converted text is the raw content.
- PDF text: pypdf if installed, otherwise poppler's `pdftotext`, otherwise only an embed.
- Never reads or writes protected folders (99 System/config.json -> "protected").
"""
import csv, datetime, io, os, re, shutil, subprocess, zipfile
import xml.etree.ElementTree as ET

ATTACH = "60 Resources/Attachments"
INBOX = "00 Inbox"
SUPPORTED = {"docx", "xlsx", "pptx", "pdf", "csv"}
MAX_ROWS = 500

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
HEADING_RE = re.compile(r"(heading|ba\u015fl\u0131k|baslik|balk|titre|\u00fcberschrift|ueberschrift|t\u00edtulo|titolo)\s*(\d)", re.I)


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def md_table(rows):
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(cell(c) or " " for c in rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(out)


# ------------------------------------------------------------------ docx
def _run_text(r):
    parts = []
    for ch in r:
        if ch.tag == W + "t":
            parts.append(ch.text or "")
        elif ch.tag == W + "tab":
            parts.append("\t")
        elif ch.tag in (W + "br", W + "cr"):
            parts.append("\n")
    txt = "".join(parts)
    rpr = r.find(W + "rPr")
    if txt.strip() and rpr is not None:
        def on(tag):
            el = rpr.find(W + tag)
            return el is not None and el.get(W + "val") not in ("0", "false")
        lead = txt[: len(txt) - len(txt.lstrip())]
        trail = txt[len(txt.rstrip()):]
        core = txt.strip()
        if on("b"):
            core = f"**{core}**"
        if on("i"):
            core = f"*{core}*"
        txt = lead + core + trail
    return txt


def _para(p, styles):
    text = "".join(_run_text(r) for r in p.iter(W + "r")).strip()
    if not text:
        return ""
    ppr = p.find(W + "pPr")
    style = ""
    if ppr is not None:
        ps = ppr.find(W + "pStyle")
        if ps is not None:
            style = ps.get(W + "val", "")
        if ppr.find(W + "numPr") is not None:
            return "- " + text
    name = styles.get(style, style)
    if re.fullmatch(r"(title|konu ?ba\u015fl\u0131\u011f\u0131|puesto|titel)", name, re.I):
        return "# " + text
    m = HEADING_RE.search(name)
    if m:
        return "#" * min(6, int(m.group(2)) + 1) + " " + text
    if re.search(r"list", name, re.I):
        return "- " + text
    return text


def docx_to_md(path):
    z = zipfile.ZipFile(path)
    styles = {}
    if "word/styles.xml" in z.namelist():
        for st in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
            n = st.find(W + "name")
            if n is not None:
                styles[st.get(W + "styleId", "")] = n.get(W + "val", "")
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    out, images = [], sum(1 for n in z.namelist() if n.startswith("word/media/"))
    for el in body:
        if el.tag == W + "p":
            t = _para(el, styles)
            if t:
                out.append(t)
        elif el.tag == W + "tbl":
            rows = []
            for tr in el.iter(W + "tr"):
                rows.append([" ".join(_para(p, styles) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")])
            t = md_table(rows)
            if t:
                out.append(t)
    warn = f"{images} image(s) not converted; see the original file." if images else ""
    return "\n\n".join(out), warn


# ------------------------------------------------------------------ xlsx
def _col(ref):
    n = 0
    for ch in re.sub(r"\d", "", ref):
        n = n * 26 + ord(ch.upper()) - 64
    return n - 1


def xlsx_sheets(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    strings = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "si"):
            strings.append("".join(t.text or "" for t in si.iter(S + "t")))
    rels = {}
    if "xl/_rels/workbook.xml.rels" in names:
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            rels[r.get("Id")] = r.get("Target", "")
    out = []
    for sh in ET.fromstring(z.read("xl/workbook.xml")).iter(S + "sheet"):
        target = rels.get(sh.get(R + "id"), "")
        target = target[1:] if target.startswith("/") else "xl/" + target.lstrip("./")
        rows = []
        if target in names:
            for row in ET.fromstring(z.read(target)).iter(S + "row"):
                cells = {}
                for c in row.findall(S + "c"):
                    t, v = c.get("t"), c.find(S + "v")
                    if t == "s" and v is not None:
                        val = strings[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(S + "t"))
                    elif t == "b":
                        val = "TRUE" if v is not None and v.text == "1" else "FALSE"
                    else:
                        val = v.text if v is not None and v.text is not None else ""
                    cells[_col(c.get("r", "A1")) if c.get("r") else len(cells)] = val
                if cells:
                    w = max(cells) + 1
                    rows.append([cells.get(i, "") for i in range(w)])
        out.append((sh.get("name", "Sheet"), rows))
    return out


def xlsx_to_md(path):
    parts, warn = [], ""
    for name, rows in xlsx_sheets(path):
        parts.append(f"## {name}")
        if len(rows) > MAX_ROWS:
            warn = f"Long sheets were cut to the first {MAX_ROWS} rows."
        parts.append(md_table(rows[:MAX_ROWS]) or "*(empty)*")
    return "\n\n".join(parts), warn


# ------------------------------------------------------------------ pptx / csv / pdf
def pptx_to_md(path):
    z = zipfile.ZipFile(path)
    slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
    out = []
    for i, n in enumerate(slides, 1):
        lines = []
        for p in ET.fromstring(z.read(n)).iter(A + "p"):
            t = "".join(x.text or "" for x in p.iter(A + "t")).strip()
            if t:
                lines.append(t)
        out.append(f"## Slide {i}\n" + ("\n".join(f"- {l}" for l in lines) if lines else "*(no text)*"))
    return "\n\n".join(out), ""


def csv_to_md(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    warn = f"Cut to the first {MAX_ROWS} rows." if len(rows) > MAX_ROWS else ""
    return md_table(rows[:MAX_ROWS]), warn


def pdf_to_md(path):
    try:
        import pypdf  # optional
        pages = [(p.extract_text() or "").strip() for p in pypdf.PdfReader(path).pages]
    except ImportError:
        exe = shutil.which("pdftotext")
        if not exe:
            return "", "Could not extract PDF text (no pypdf or pdftotext); only the embedded view was added. Run `pip install pypdf` to get the text too."
        res = subprocess.run([exe, "-enc", "UTF-8", "-layout", path, "-"], capture_output=True)
        pages = [p.strip() for p in res.stdout.decode("utf-8", "replace").split("\f")]
    pages = [p for p in pages]
    while pages and not pages[-1]:
        pages.pop()
    if not any(pages):
        return "", "The PDF has no text layer (probably scanned); only the embedded view was added."
    return "\n\n".join(f"### Page {i}\n\n{p}" for i, p in enumerate(pages, 1) if p), ""


CONVERT = {"docx": docx_to_md, "xlsx": xlsx_to_md, "pptx": pptx_to_md, "csv": csv_to_md, "pdf": pdf_to_md}


# ------------------------------------------------------------------ note
def _unique(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem} ({n}){ext}"):
        n += 1
    return f"{stem} ({n}){ext}"


def safe_name(s):
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|#^\[\]]', " ", s)).strip()[:90] or "Import"


def import_file(src, vault, protected):
    """Returns dict(note, attachment, warning). Paths are vault-relative with '/'."""
    src_abs = os.path.abspath(src if os.path.isabs(src) else os.path.join(vault, src))
    if not os.path.isfile(src_abs):
        raise FileNotFoundError(f"file not found: {src}")
    rel = os.path.relpath(src_abs, vault).replace("\\", "/")
    inside = not rel.startswith("../") and not os.path.isabs(rel)
    if isinstance(protected, str):
        protected = [protected]
    if inside and any((rel + "/").startswith(p.strip("/") + "/") for p in protected or []):
        raise PermissionError("files in protected folders are not imported")
    ext = os.path.splitext(src_abs)[1].lower().lstrip(".")
    if ext not in SUPPORTED:
        raise ValueError(f"unsupported type: .{ext} (supported: {', '.join(sorted(SUPPORTED))})")
    if not inside:
        os.makedirs(os.path.join(vault, ATTACH), exist_ok=True)
        dest = _unique(os.path.join(vault, ATTACH, safe_name(os.path.splitext(os.path.basename(src_abs))[0]) + "." + ext))
        shutil.copy2(src_abs, dest)
        rel = os.path.relpath(dest, vault).replace("\\", "/")
        src_abs = dest
    body, warn = CONVERT[ext](src_abs)
    title = safe_name(os.path.splitext(os.path.basename(src_abs))[0])
    os.makedirs(os.path.join(vault, INBOX), exist_ok=True)
    note_abs = _unique(os.path.join(vault, INBOX, title + ".md"))
    today = datetime.date.today().isoformat()
    kind = {"docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint", "pdf": "PDF", "csv": "CSV"}[ext]
    lines = [
        "---", "type: source", f'source: "{kind} file: {os.path.basename(rel)}"', f"created: {today}", "---",
        f"# {title}", "",
        "> [!abstract] Context",
        f"> **What:** converted automatically from a {kind} file ({today}). Original: [[{rel}]]",
        "> **Why I saved it:** ",
        "> **Verification:** automatic conversion; formatting, images and formulas may be lost. Check the original when in doubt.",
    ]
    if warn:
        lines.append(f"> **Note:** {warn}")
    lines += ["", "## Raw content", ""]
    if ext in ("pdf", "docx"):  # pdf: native viewer, docx: Docxer embed
        lines += [f"![[{rel}]]", ""]
    lines += [body.strip() or "*(no text extracted)*", "", "## My takeaways", "- ", ""]
    with open(note_abs, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    return {"note": os.path.relpath(note_abs, vault).replace("\\", "/"), "attachment": rel, "warning": warn}
