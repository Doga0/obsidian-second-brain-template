/* Second Brain Tools — calendar, activity heatmap, quick menu, due-date reminders,
 * spreadsheet viewer (xlsx/csv) and file import for this vault.
 *
 *   ```sb-calendar            ```sb-heatmap
 *   project: MyHub    # opt    weeks: 52         # opt
 *   show: completed, due, started, decided      source: tasks, notes, git   # opt
 *   scope: work      # opt    scope: personal   # opt (personal | work | all)
 *   ```                       ```
 *
 * The vault has two areas, Personal/ and Work/; calendar, heatmap, reminders and the quick menu
 * can be limited to one of them. 99 System/ and protected folders (99 System/config.json) are never counted.
 */
'use strict';
const obsidian = require('obsidian');
const { Plugin, MarkdownRenderChild, Modal, Notice, SuggestModal, FileView, PluginSettingTab, Setting, TFile, normalizePath, prepareFuzzySearch } = obsidian;

const SYSTEM = '99 System/';
const AREAS = {
  personal: { root: 'Personal', label: 'Personal', inbox: 'Personal/00 Inbox', attach: 'Personal/60 Resources/Attachments', tasks: 'Personal/15 Tasks', ideas: 'Personal/50 Ideas' },
  work: { root: 'Work', label: 'Work', inbox: 'Work/00 Inbox', attach: 'Work/60 Attachments', tasks: 'Work/50 Tasks', ideas: 'Work/00 Inbox' },
};
const SCOPE_ALIASES = { personal: 'personal', p: 'personal', work: 'work', w: 'work', all: '', both: '', '': '' };
const CONFIG_PATH = '99 System/config.json';
let PROTECTED_DIRS = [];
function isProtected(path) { return PROTECTED_DIRS.some((d) => path === d || path.startsWith(d + '/')); }
function areaOf(path) {
  for (const [k, a] of Object.entries(AREAS)) if (path === a.root || path.startsWith(a.root + '/')) return k;
  return '';
}
function parseScope(v) {
  const k = String(v || '').trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(SCOPE_ALIASES, k) ? SCOPE_ALIASES[k] : '';
}
function inScope(path, scope) { return !scope || areaOf(path) === scope; }
function scopeSelect(parent, value, onChange) {
  const sel = parent.createEl('select', { cls: 'dropdown sbt-scope' });
  sel.createEl('option', { text: 'All areas', value: '' });
  for (const [k, a] of Object.entries(AREAS)) sel.createEl('option', { text: a.label, value: k });
  sel.value = value || '';
  sel.onchange = () => onChange(sel.value);
  return sel;
}
const TOOL = '99 System/scripts/vault_tool.py';
const VIEW_SHEET = 'sb-sheet-view';
const DONE = new Set(['done', 'archived', 'dropped', 'rejected', 'superseded']);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const KIND = {
  completed: { icon: '✓', label: 'Completed' },
  due: { icon: '📅', label: 'Due' },
  started: { icon: '▶', label: 'Started' },
  decided: { icon: '⚖', label: 'Decision' },
};
const DEFAULTS = { remind: true, systemNotify: true, daysAhead: 1, intervalMin: 30, remindScope: '' };

// ---------------------------------------------------------------- pure helpers
const pad = (n) => String(n).padStart(2, '0');
function ymd(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function today() { return ymd(new Date()); }
function dateStr(v) {
  if (!v) return '';
  const m = String(Array.isArray(v) ? v[0] : v).trim().match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : '';
}
function daysBetween(a, b) {
  const pa = Date.parse(a + 'T00:00:00'), pb = Date.parse(b + 'T00:00:00');
  if (isNaN(pa) || isNaN(pb)) return null;
  return Math.round((pb - pa) / 86400000);
}
function addDays(s, n) { const d = new Date(s + 'T00:00:00'); d.setDate(d.getDate() + n); return ymd(d); }
function linkName(v) {
  if (Array.isArray(v)) v = v[0];
  if (v === undefined || v === null) return '';
  const s = String(v).trim();
  const m = s.match(/\[\[([^\]|#]+)/);
  return (m ? m[1] : s).trim().split('/').pop().replace(/\.md$/, '');
}
function asList(v) { return String(v || '').split(',').map((x) => x.trim()).filter(Boolean); }
function parseConfig(src) {
  const cfg = {};
  for (const raw of String(src).split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, '').trim();
    const m = line.match(/^([\w-]+)\s*:\s*(.*)$/);
    if (m) cfg[m[1].toLowerCase()] = m[2].trim();
  }
  return cfg;
}
function sanitizeName(s) { return String(s).replace(/[\\/:*?"<>|#^\[\]]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 90); }
function analysable(path, scope) { return !path.startsWith(SYSTEM) && !isProtected(path) && inScope(path, scope); }

/** Group task/decision dates by day. items: [{date, kind, file, title, status, project}] */
function collectDated(app, opts = {}) {
  const kinds = opts.kinds || Object.keys(KIND);
  const out = [];
  for (const f of app.vault.getMarkdownFiles()) {
    if (!analysable(f.path, opts.scope)) continue;
    const fm = (app.metadataCache.getFileCache(f) || {}).frontmatter;
    if (!fm) continue;
    const type = String(fm.type || '');
    if (type !== 'task' && type !== 'decision') continue;
    const project = linkName(fm.project);
    if (opts.project && project !== opts.project) continue;
    const status = String(fm.status || '');
    const add = (kind, v) => { const d = dateStr(v); if (d && kinds.includes(kind)) out.push({ date: d, kind, file: f, title: f.basename, status, project }); };
    if (type === 'task') {
      add('completed', fm.completed);
      add('started', fm.started);
      if (!DONE.has(status)) add('due', fm.due);
    } else add('decided', fm.decided);
  }
  return out;
}

/** Activity counts per day. Returns {map: {date: {tasks, notes, git, total}}} */
function activityFromVault(app, sources, since, scope) {
  const map = {};
  const bump = (d, key, n = 1) => {
    if (!d || d < since) return;
    const e = (map[d] = map[d] || { tasks: 0, notes: 0, git: 0, total: 0 });
    e[key] += n; e.total += n;
  };
  for (const f of app.vault.getMarkdownFiles()) {
    if (!analysable(f.path, scope)) continue;
    const fm = ((app.metadataCache.getFileCache(f) || {}).frontmatter) || {};
    if (sources.includes('tasks') && fm.type === 'task') {
      bump(dateStr(fm.completed), 'tasks');
      bump(dateStr(fm.started), 'tasks');
    }
    if (sources.includes('notes')) {
      const created = dateStr(fm.created) || ymd(new Date(f.stat.ctime));
      bump(created, 'notes');
      const modified = ymd(new Date(f.stat.mtime));
      if (modified !== created) bump(modified, 'notes');
    }
  }
  return map;
}
function levels(values) { // 4 thresholds from the distribution of non-zero days
  const v = values.filter((x) => x > 0).sort((a, b) => a - b);
  if (!v.length) return [1, 2, 3, 4];
  const q = (p) => v[Math.min(v.length - 1, Math.floor(p * (v.length - 1)))];
  return [1, Math.max(2, q(0.25)), Math.max(3, q(0.5)), Math.max(4, q(0.75))];
}
function streaks(map, end) {
  let cur = 0, best = 0, run = 0;
  const days = Object.keys(map).filter((d) => map[d].total > 0).sort();
  let prev = null;
  for (const d of days) { run = prev && daysBetween(prev, d) === 1 ? run + 1 : 1; best = Math.max(best, run); prev = d; }
  let d = end;
  if (!(map[d] && map[d].total)) d = addDays(d, -1); // today may still be empty
  while (map[d] && map[d].total) { cur += 1; d = addDays(d, -1); }
  return { cur, best };
}

// ---------------------------------------------------------------- zip + xlsx (desktop: uses node zlib)
function unzip(buf) {
  const zlib = require('zlib');
  const b = Buffer.from(buf);
  let eocd = -1;
  for (let i = b.length - 22; i >= Math.max(0, b.length - 65557); i--) if (b.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw new Error('not a ZIP file');
  const count = b.readUInt16LE(eocd + 10);
  let p = b.readUInt32LE(eocd + 16);
  const files = {};
  for (let n = 0; n < count; n++) {
    if (b.readUInt32LE(p) !== 0x02014b50) break;
    const method = b.readUInt16LE(p + 10), csize = b.readUInt32LE(p + 20);
    const nlen = b.readUInt16LE(p + 28), elen = b.readUInt16LE(p + 30), clen = b.readUInt16LE(p + 32);
    const local = b.readUInt32LE(p + 42);
    const name = b.slice(p + 46, p + 46 + nlen).toString('utf8');
    const lnl = b.readUInt16LE(local + 26), lel = b.readUInt16LE(local + 28);
    const start = local + 30 + lnl + lel;
    const data = b.slice(start, start + csize);
    files[name] = () => (method === 0 ? data : zlib.inflateRawSync(data)).toString('utf8');
    p += 46 + nlen + elen + clen;
  }
  return files;
}
function colIndex(ref) { let n = 0; for (const ch of ref.replace(/\d+$/, '')) n = n * 26 + (ch.charCodeAt(0) - 64); return n - 1; }
function colName(i) { let s = ''; i += 1; while (i > 0) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; }
function parseXlsx(buf, parseXml) {
  const z = unzip(buf);
  const xml = (n) => (z[n] ? parseXml(z[n]()) : null);
  const strings = [];
  const ss = xml('xl/sharedStrings.xml');
  if (ss) for (const si of Array.from(ss.getElementsByTagName('si'))) strings.push(Array.from(si.getElementsByTagName('t')).map((t) => t.textContent).join(''));
  const rels = {};
  const rx = xml('xl/_rels/workbook.xml.rels');
  if (rx) for (const r of Array.from(rx.getElementsByTagName('Relationship'))) rels[r.getAttribute('Id')] = r.getAttribute('Target');
  const wb = xml('xl/workbook.xml');
  const sheets = [];
  for (const s of Array.from(wb ? wb.getElementsByTagName('sheet') : [])) {
    const rid = s.getAttribute('r:id') || s.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id');
    let target = rels[rid] || '';
    target = target.startsWith('/') ? target.slice(1) : 'xl/' + target.replace(/^\.\//, '');
    const doc = xml(target);
    const rows = [];
    if (doc) {
      for (const row of Array.from(doc.getElementsByTagName('row'))) {
        const r = parseInt(row.getAttribute('r'), 10) - 1 || rows.length;
        const cells = [];
        for (const c of Array.from(row.getElementsByTagName('c'))) {
          const ref = c.getAttribute('r');
          const idx = ref ? colIndex(ref) : cells.length;
          const t = c.getAttribute('t');
          const v = c.getElementsByTagName('v')[0];
          let val = '';
          if (t === 's') val = strings[parseInt(v && v.textContent, 10)] ?? '';
          else if (t === 'inlineStr') val = Array.from(c.getElementsByTagName('t')).map((x) => x.textContent).join('');
          else if (t === 'b') val = v && v.textContent === '1' ? 'TRUE' : 'FALSE';
          else val = v ? v.textContent : '';
          cells[idx] = val;
        }
        rows[r] = cells;
      }
    }
    sheets.push({ name: s.getAttribute('name') || 'Sheet', rows: Array.from(rows, (r) => r || []) });
  }
  return sheets;
}
function parseCsv(text) {
  const delim = (text.split('\n')[0].match(/;/g) || []).length > (text.split('\n')[0].match(/,/g) || []).length ? ';' : ',';
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (ch === '"') q = false; else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === delim) { row.push(cell); cell = ''; }
    else if (ch === '\n') { row.push(cell.replace(/\r$/, '')); rows.push(row); row = []; cell = ''; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return [{ name: 'CSV', rows }];
}

// ---------------------------------------------------------------- calendar
class CalendarChild extends MarkdownRenderChild {
  constructor(plugin, el, cfg) {
    super(el);
    this.plugin = plugin; this.app = plugin.app;
    this.project = cfg.project ? linkName(cfg.project) : '';
    this.scope = parseScope(cfg.scope);
    this.fixedScope = !!this.scope;
    this.kinds = asList(cfg.show).filter((k) => KIND[k]);
    if (!this.kinds.length) this.kinds = Object.keys(KIND);
    const now = new Date();
    this.y = now.getFullYear(); this.m = now.getMonth();
    this.timer = null;
  }
  onload() {
    const re = () => { clearTimeout(this.timer); this.timer = setTimeout(() => this.render(), 300); };
    this.registerEvent(this.app.metadataCache.on('changed', re));
    this.registerEvent(this.app.vault.on('delete', re));
    this.registerEvent(this.app.vault.on('rename', re));
    this.render();
  }
  onunload() { clearTimeout(this.timer); }
  render() {
    const el = this.containerEl;
    el.empty(); el.addClass('sbt-cal');
    const items = collectDated(this.app, { project: this.project, kinds: this.kinds, scope: this.scope });
    const byDay = {};
    for (const it of items) (byDay[it.date] = byDay[it.date] || []).push(it);

    const head = el.createDiv({ cls: 'sbt-cal-head' });
    const nav = (dm) => { this.m += dm; if (this.m < 0) { this.m = 11; this.y--; } if (this.m > 11) { this.m = 0; this.y++; } this.render(); };
    head.createEl('button', { text: '‹', cls: 'clickable-icon' }).onclick = () => nav(-1);
    head.createDiv({ cls: 'sbt-cal-title', text: `${MONTHS[this.m]} ${this.y}` + (this.project ? ` · ${this.project}` : '') });
    head.createEl('button', { text: '›', cls: 'clickable-icon' }).onclick = () => nav(1);
    head.createEl('button', { text: 'Today', cls: 'sbt-today-btn' }).onclick = () => { const n = new Date(); this.y = n.getFullYear(); this.m = n.getMonth(); this.render(); };
    if (!this.fixedScope && !this.project) scopeSelect(head, this.scope, (v) => { this.scope = v; this.render(); });
    const legend = head.createDiv({ cls: 'sbt-legend' });
    for (const k of this.kinds) legend.createSpan({ cls: `sbt-chip sbt-${k}`, text: `${KIND[k].icon} ${KIND[k].label}` });

    const grid = el.createDiv({ cls: 'sbt-cal-grid' });
    for (const d of DAYS) grid.createDiv({ cls: 'sbt-cal-dow', text: d });
    const first = new Date(this.y, this.m, 1);
    const offset = (first.getDay() + 6) % 7;
    const inMonth = new Date(this.y, this.m + 1, 0).getDate();
    const t = today();
    let monthCount = 0;
    for (let i = 0; i < offset; i++) grid.createDiv({ cls: 'sbt-cal-cell sbt-empty' });
    for (let day = 1; day <= inMonth; day++) {
      const ds = `${this.y}-${pad(this.m + 1)}-${pad(day)}`;
      const cell = grid.createDiv({ cls: 'sbt-cal-cell' });
      if (ds === t) cell.addClass('sbt-is-today');
      cell.createDiv({ cls: 'sbt-cal-num', text: String(day) });
      const list = (byDay[ds] || []).sort((a, b) => a.kind.localeCompare(b.kind));
      monthCount += list.length;
      for (const it of list.slice(0, 4)) {
        const e = cell.createDiv({ cls: `sbt-cal-item sbt-${it.kind}`, text: `${KIND[it.kind].icon} ${it.title}` });
        if (it.kind === 'due' && ds < t) e.addClass('sbt-overdue');
        e.setAttr('title', `${KIND[it.kind].label}: ${it.title}${it.project ? ' · ' + it.project : ''}`);
        e.onclick = (ev) => this.app.workspace.getLeaf(ev.ctrlKey || ev.metaKey ? 'tab' : false).openFile(it.file);
      }
      if (list.length > 4) {
        const more = cell.createDiv({ cls: 'sbt-cal-more', text: `+${list.length - 4}` });
        more.onclick = () => new DayModal(this.app, ds, list).open();
      }
    }
    el.createDiv({ cls: 'sbt-foot', text: monthCount ? `${monthCount} entries this month` : 'No entries this month' });
  }
}
class DayModal extends Modal {
  constructor(app, day, items) { super(app); this.day = day; this.items = items; }
  onOpen() {
    this.titleEl.setText(this.day);
    for (const it of this.items) {
      const row = this.contentEl.createDiv({ cls: `sbt-cal-item sbt-${it.kind}`, text: `${KIND[it.kind].icon} ${it.title}` });
      row.onclick = () => { this.close(); this.app.workspace.getLeaf(false).openFile(it.file); };
    }
  }
  onClose() { this.contentEl.empty(); }
}

// ---------------------------------------------------------------- heatmap
class HeatmapChild extends MarkdownRenderChild {
  constructor(plugin, el, cfg) {
    super(el);
    this.plugin = plugin; this.app = plugin.app;
    this.weeks = Math.min(104, Math.max(4, parseInt(cfg.weeks, 10) || 52));
    this.sources = asList(cfg.source || 'tasks, notes, git').map((s) => s.toLowerCase());
    this.scope = parseScope(cfg.scope);
    this.fixedScope = !!this.scope;
    this.timer = null;
  }
  onload() {
    const re = () => { clearTimeout(this.timer); this.timer = setTimeout(() => this.render(), 1500); };
    this.registerEvent(this.app.metadataCache.on('changed', re));
    this.render();
  }
  onunload() { clearTimeout(this.timer); }
  async render() {
    const end = today();
    const endD = new Date(end + 'T00:00:00');
    const startD = new Date(endD); startD.setDate(startD.getDate() - (this.weeks * 7 - 1) - ((endD.getDay() + 6) % 7));
    const since = ymd(startD);
    const map = activityFromVault(this.app, this.sources, since, this.scope);
    if (this.sources.includes('git')) {
      const commits = await this.plugin.gitDays(since, this.scope);
      for (const [d, n] of Object.entries(commits)) {
        const e = (map[d] = map[d] || { tasks: 0, notes: 0, git: 0, total: 0 });
        e.git += n; e.total += n;
      }
    }
    const el = this.containerEl;
    el.empty(); el.addClass('sbt-heat');
    const th = levels(Object.values(map).map((x) => x.total));
    const total = Object.values(map).reduce((s, x) => s + x.total, 0);
    const activeDays = Object.values(map).filter((x) => x.total > 0).length;
    const st = streaks(map, end);
    if (!this.fixedScope) {
      const bar = el.createDiv({ cls: 'sbt-heat-bar' });
      scopeSelect(bar, this.scope, (v) => { this.scope = v; this.render(); });
    }
    const stats = el.createDiv({ cls: 'sbt-heat-stats' });
    const stat = (n, l) => { const s = stats.createDiv({ cls: 'sbt-stat' }); s.createDiv({ cls: 'sbt-stat-n', text: String(n) }); s.createDiv({ cls: 'sbt-stat-l', text: l }); };
    stat(total, `activities (${this.weeks} weeks)`); stat(activeDays, 'active days'); stat(st.cur, 'current streak'); stat(st.best, 'longest streak');

    const wrap = el.createDiv({ cls: 'sbt-heat-wrap' });
    const labels = wrap.createDiv({ cls: 'sbt-heat-dows' });
    ['Mon', '', 'Wed', '', 'Fri', '', ''].forEach((d) => labels.createDiv({ text: d }));
    const grid = wrap.createDiv({ cls: 'sbt-heat-grid' });
    const months = el.createDiv({ cls: 'sbt-heat-months' });
    let d = since, lastMonth = -1, col = 0;
    while (d <= end) {
      const week = grid.createDiv({ cls: 'sbt-heat-week' });
      const dt = new Date(d + 'T00:00:00');
      if (dt.getMonth() !== lastMonth) {
        const m = months.createSpan({ text: MONTHS[dt.getMonth()].slice(0, 3) });
        m.style.gridColumnStart = String(col + 1);
        lastMonth = dt.getMonth();
      }
      for (let i = 0; i < 7; i++) {
        const c = week.createDiv({ cls: 'sbt-heat-cell' });
        if (d > end) { c.addClass('sbt-future'); d = addDays(d, 1); continue; }
        const e = map[d];
        const n = e ? e.total : 0;
        const lvl = n === 0 ? 0 : n >= th[3] ? 4 : n >= th[2] ? 3 : n >= th[1] ? 2 : 1;
        c.addClass('sbt-l' + lvl);
        const parts = e ? [e.tasks && `${e.tasks} task`, e.notes && `${e.notes} note`, e.git && `${e.git} commit`].filter(Boolean).join(', ') : '';
        c.setAttr('title', `${d}: ${n ? parts : 'no activity'}`);
        const day = d;
        c.onclick = () => this.plugin.openDay(day, this.scope);
        d = addDays(d, 1);
      }
      col += 1;
    }
    months.style.gridTemplateColumns = `repeat(${col}, 13px)`;
    const leg = el.createDiv({ cls: 'sbt-heat-legend' });
    leg.createSpan({ text: 'Less ' });
    for (let i = 0; i <= 4; i++) leg.createDiv({ cls: 'sbt-heat-cell sbt-l' + i });
    leg.createSpan({ text: ' More · source: ' + this.sources.join(', ') });
  }
}

// ---------------------------------------------------------------- quick menu
class QuickMenu extends SuggestModal {
  constructor(plugin) {
    super(plugin.app);
    this.plugin = plugin;
    this.setPlaceholder('Find a note · ">" commands · "+" new note · "!" new task · "?" new idea');
    this.setInstructions([
      { command: '↵', purpose: 'open / create' },
      { command: 'ctrl ↵', purpose: 'new tab' },
      { command: '>', purpose: 'commands' },
      { command: '+ ! ?', purpose: 'note · task · idea' },
    ]);
    this.scope.register(['Mod'], 'Enter', (e) => { this.newTab = true; this.selectActiveSuggestion(e); return false; });
  }
  getSuggestions(query) {
    const q = query.trim();
    const app = this.app;
    if (q.startsWith('>')) {
      const fz = prepareFuzzySearch(q.slice(1).trim());
      return app.commands.listCommands()
        .map((c) => ({ c, m: q.length > 1 ? fz(c.name) : { score: 0 } }))
        .filter((x) => x.m).sort((a, b) => b.m.score - a.m.score).slice(0, 60)
        .map((x) => ({ kind: 'command', title: x.c.name, command: x.c }));
    }
    const act = app.workspace.getActiveFile();
    const primary = (act && areaOf(act.path)) || 'personal';
    const other = primary === 'work' ? 'personal' : 'work';
    const create = { '+': 'note', '!': 'task', '?': 'idea' }[q[0]];
    if (create) {
      const title = q.slice(1).trim();
      return [{ kind: 'create', what: create, title, area: primary }, { kind: 'create', what: create, title, area: other }];
    }
    const out = [];
    if (q) {
      out.push({ kind: 'create', what: 'note', title: q, area: primary }, { kind: 'create', what: 'task', title: q, area: primary },
        { kind: 'create', what: 'note', title: q, area: other }, { kind: 'create', what: 'task', title: q, area: other });
    }
    const files = app.vault.getFiles().filter((f) => !f.path.startsWith('.'));
    if (!q) {
      const recent = app.workspace.getLastOpenFiles().map((p) => app.vault.getAbstractFileByPath(p)).filter((f) => f instanceof TFile);
      return recent.map((file) => ({ kind: 'file', file, title: file.basename })).concat([
        { kind: 'create', what: 'task', title: '', area: primary }, { kind: 'create', what: 'note', title: '', area: primary },
        { kind: 'create', what: 'task', title: '', area: other }, { kind: 'create', what: 'note', title: '', area: other },
        { kind: 'create', what: 'idea', title: '', area: 'personal' },
        { kind: 'open', path: 'Board.md', title: 'Board' }, { kind: 'open', path: 'Home.md', title: 'Home' },
      ]);
    }
    const fz = prepareFuzzySearch(q);
    const scored = [];
    for (const f of files) {
      let m = fz(f.basename) || fz(f.path), alias = '';
      if (!m && f.extension === 'md') {
        const fm = ((app.metadataCache.getFileCache(f) || {}).frontmatter) || {};
        for (const a of [].concat(fm.aliases || [])) { const am = fz(String(a)); if (am) { m = am; alias = String(a); break; } }
      }
      if (m) scored.push({ f, s: m.score + (f.extension === 'md' ? 0.1 : 0), alias });
    }
    scored.sort((a, b) => b.s - a.s);
    const hits = scored.slice(0, 40).map((x) => ({ kind: 'file', file: x.f, title: x.f.basename, alias: x.alias }));
    return hits.concat(out);
  }
  renderSuggestion(item, el) {
    el.addClass('sbt-qm-item');
    const icon = { file: '📄', command: '⌘', open: '🏠', create: { note: '➕', task: '✅', idea: '💡' }[item.what] }[item.kind];
    el.createSpan({ cls: 'sbt-qm-icon', text: icon });
    const body = el.createDiv({ cls: 'sbt-qm-body' });
    if (item.kind === 'create') {
      const label = { note: 'New note', task: 'New task', idea: 'New idea' }[item.what];
      const ar = AREAS[item.area || 'personal'];
      body.createDiv({ text: (item.title ? `${label}: ${item.title}` : `${label}…`) + ` · ${ar.label}` });
      body.createDiv({ cls: 'sbt-qm-sub', text: { note: ar.inbox, task: ar.tasks + '/<project> · board', idea: ar.ideas + ' · board' }[item.what] });
    } else if (item.kind === 'file') {
      body.createDiv({ text: item.title + (item.alias ? `  ← ${item.alias}` : '') });
      const sub = item.file.parent && item.file.parent.path !== '/' ? item.file.parent.path : '';
      if (areaOf(item.file.path) === 'work') el.addClass('sbt-qm-work');
      body.createDiv({ cls: 'sbt-qm-sub', text: sub + (item.file.extension !== 'md' ? ` · .${item.file.extension}` : '') });
    } else body.createDiv({ text: item.title });
  }
  async onChooseSuggestion(item) {
    const leaf = () => this.app.workspace.getLeaf(this.newTab ? 'tab' : false);
    if (item.kind === 'file') return leaf().openFile(item.file);
    if (item.kind === 'open') { const f = this.app.vault.getAbstractFileByPath(item.path); if (f instanceof TFile) return leaf().openFile(f); return; }
    if (item.kind === 'command') return this.app.commands.executeCommandById(item.command.id);
    if (item.kind === 'create') return this.plugin.create(item.what, item.title, this.newTab, item.area);
  }
}
class TitleModal extends Modal {
  constructor(app, heading, onSubmit) { super(app); this.heading = heading; this.onSubmit = onSubmit; }
  onOpen() {
    this.titleEl.setText(this.heading);
    let v = '';
    new Setting(this.contentEl).setName('Title').addText((t) => {
      t.onChange((x) => (v = x));
      t.inputEl.style.width = '100%';
      setTimeout(() => t.inputEl.focus(), 30);
      t.inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter' && v.trim()) { e.preventDefault(); this.close(); this.onSubmit(v.trim()); } });
    });
  }
  onClose() { this.contentEl.empty(); }
}

// ---------------------------------------------------------------- reminders
class DueListModal extends Modal {
  constructor(app, items) { super(app); this.items = items; }
  onOpen() {
    this.titleEl.setText('Upcoming and overdue tasks');
    if (!this.items.length) this.contentEl.createDiv({ text: 'No upcoming or overdue tasks.' });
    for (const it of this.items) {
      const row = this.contentEl.createDiv({ cls: 'sbt-due-row' + (it.days < 0 ? ' sbt-overdue' : '') });
      row.createSpan({ text: `${it.due} · ${it.title}` });
      row.createSpan({ cls: 'sbt-qm-sub', text: ' ' + dueText(it.days) + (it.project ? ' · ' + it.project : '') });
      row.onclick = () => { this.close(); this.app.workspace.getLeaf(false).openFile(it.file); };
    }
  }
  onClose() { this.contentEl.empty(); }
}
function dueText(days) { return days < 0 ? `${-days} day(s) overdue` : days === 0 ? 'due today' : days === 1 ? 'due tomorrow' : `due in ${days} days`; }

// ---------------------------------------------------------------- spreadsheet view
class SheetView extends FileView {
  constructor(leaf) { super(leaf); this.sheet = 0; }
  getViewType() { return VIEW_SHEET; }
  getDisplayText() { return this.file ? this.file.name : 'Spreadsheet'; }
  getIcon() { return 'table'; }
  canAcceptExtension(ext) { return ext === 'xlsx' || ext === 'csv'; }
  async onLoadFile(file) {
    const el = this.contentEl;
    el.empty(); el.addClass('sbt-sheet');
    try {
      this.sheets = file.extension === 'csv'
        ? parseCsv(await this.app.vault.read(file))
        : parseXlsx(await this.app.vault.readBinary(file), (s) => new DOMParser().parseFromString(s, 'application/xml'));
    } catch (e) {
      el.createDiv({ cls: 'sbt-error', text: 'Could not read the file: ' + e.message });
      return;
    }
    this.sheet = 0;
    this.draw();
  }
  async onUnloadFile() { this.contentEl.empty(); }
  draw() {
    const el = this.contentEl;
    el.empty();
    const bar = el.createDiv({ cls: 'sbt-sheet-bar' });
    this.sheets.forEach((s, i) => {
      const b = bar.createEl('button', { text: s.name, cls: i === this.sheet ? 'mod-cta' : '' });
      b.onclick = () => { this.sheet = i; this.draw(); };
    });
    const imp = bar.createEl('button', { text: 'Convert to Markdown note' });
    imp.onclick = () => this.app.plugins.plugins['sb-tools'].runImport(this.file.path);
    const rows = this.sheets[this.sheet].rows;
    const width = rows.reduce((m, r) => Math.max(m, r.length), 0);
    const LIMIT = 2000;
    const wrap = el.createDiv({ cls: 'sbt-sheet-wrap' });
    const table = wrap.createEl('table');
    const hr = table.createEl('thead').createEl('tr');
    hr.createEl('th');
    for (let c = 0; c < width; c++) hr.createEl('th', { text: colName(c) });
    const body = table.createEl('tbody');
    rows.slice(0, LIMIT).forEach((r, i) => {
      const tr = body.createEl('tr');
      tr.createEl('th', { text: String(i + 1) });
      for (let c = 0; c < width; c++) tr.createEl('td', { text: r[c] ?? '' });
    });
    if (rows.length > LIMIT) el.createDiv({ cls: 'sbt-foot', text: `Showing the first ${LIMIT} rows (of ${rows.length}).` });
  }
}

// ---------------------------------------------------------------- settings
class SbToolsSettings extends PluginSettingTab {
  constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
  display() {
    const c = this.containerEl; c.empty();
    const s = this.plugin.settings;
    const save = () => { this.plugin.saveData(s); this.plugin.restartReminders(); };
    new Setting(c).setName('Reminders').setDesc('Notify about tasks whose `due` date is near or past').addToggle((t) => t.setValue(s.remind).onChange((v) => { s.remind = v; save(); }));
    new Setting(c).setName('System notification').setDesc('Also show an operating-system notification').addToggle((t) => t.setValue(s.systemNotify).onChange((v) => { s.systemNotify = v; save(); }));
    new Setting(c).setName('Days ahead').setDesc('0 = only due today and overdue').addSlider((sl) => sl.setLimits(0, 7, 1).setValue(s.daysAhead).setDynamicTooltip().onChange((v) => { s.daysAhead = v; save(); }));
    new Setting(c).setName('Reminder area').setDesc('Which area\'s tasks to remind about').addDropdown((d) => {
      d.addOption('', 'All areas');
      for (const [k, a] of Object.entries(AREAS)) d.addOption(k, a.label);
      d.setValue(s.remindScope || '').onChange((v) => { s.remindScope = v; save(); this.plugin.updateStatus(); });
    });
    new Setting(c).setName('Check interval (minutes)').addSlider((sl) => sl.setLimits(5, 120, 5).setValue(s.intervalMin).setDynamicTooltip().onChange((v) => { s.intervalMin = v; save(); }));
  }
}

// ---------------------------------------------------------------- plugin
class SbToolsPlugin extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULTS, (await this.loadData()) || {});
    await this.loadVaultConfig();
    this.registerEvent(this.app.vault.on('modify', (f) => { if (f.path === CONFIG_PATH) this.loadVaultConfig(); }));
    this.registerMarkdownCodeBlockProcessor('sb-calendar', (src, el, ctx) => ctx.addChild(new CalendarChild(this, el, parseConfig(src))));
    this.registerMarkdownCodeBlockProcessor('sb-heatmap', (src, el, ctx) => ctx.addChild(new HeatmapChild(this, el, parseConfig(src))));
    this.registerView(VIEW_SHEET, (leaf) => new SheetView(leaf));
    try { this.registerExtensions(['xlsx', 'csv'], VIEW_SHEET); } catch (e) { console.warn('sb-tools: xlsx/csv view already registered', e); }

    this.addRibbonIcon('search', 'Quick menu', () => new QuickMenu(this).open());
    this.addCommand({ id: 'quick-menu', name: 'Quick menu (open · create · run)', callback: () => new QuickMenu(this).open() });
    this.addCommand({ id: 'new-note', name: 'New note (Inbox)', callback: () => this.create('note', '') });
    this.addCommand({ id: 'new-task', name: 'New task', callback: () => this.create('task', '') });
    this.addCommand({ id: 'due-list', name: 'Show upcoming tasks', callback: () => new DueListModal(this.app, this.dueItems(7)).open() });
    this.addCommand({ id: 'check-reminders', name: 'Check reminders now', callback: () => this.checkReminders(true) });
    this.addCommand({ id: 'import-file', name: 'Import file (docx, xlsx, pdf, pptx, csv → note)', callback: () => this.pickAndImport() });
    this.addCommand({ id: 'import-current', name: 'Convert current file to Markdown note', checkCallback: (checking) => {
      const f = this.app.workspace.getActiveFile();
      const ok = f && ['docx', 'xlsx', 'pdf', 'pptx', 'csv'].includes(f.extension) && !isProtected(f.path);
      if (ok && !checking) this.runImport(f.path);
      return !!ok;
    } });
    this.addSettingTab(new SbToolsSettings(this.app, this));
    this.registerEvent(this.app.workspace.on('file-menu', (menu, file) => {
      if (file instanceof TFile && ['docx', 'xlsx', 'pdf', 'pptx', 'csv'].includes(file.extension) && !isProtected(file.path)) {
        menu.addItem((i) => i.setTitle('Convert to Markdown note').setIcon('file-input').onClick(() => this.runImport(file.path)));
      }
    }));

    this.statusEl = this.addStatusBarItem();
    this.statusEl.addClass('mod-clickable');
    this.statusEl.onclick = () => new DueListModal(this.app, this.dueItems(7)).open();
    this.app.workspace.onLayoutReady(() => {
      this.registerEvent(this.app.metadataCache.on('resolved', () => this.updateStatus()));
      this.registerEvent(this.app.metadataCache.on('changed', () => this.updateStatus()));
      this.updateStatus();
      setTimeout(() => this.checkReminders(false), 4000);
      this.restartReminders();
    });
  }
  async loadVaultConfig() {
    try {
      if (await this.app.vault.adapter.exists(CONFIG_PATH)) {
        const cfg = JSON.parse(await this.app.vault.adapter.read(CONFIG_PATH));
        PROTECTED_DIRS = (cfg.protected || []).map((d) => String(d).replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')).filter(Boolean);
      }
    } catch (e) { console.error('sb-tools: could not read ' + CONFIG_PATH, e); }
  }

  // ------------------------------------------------ create
  async create(what, title, newTab, area) {
    const act0 = this.app.workspace.getActiveFile();
    area = area || (act0 && areaOf(act0.path)) || 'personal';
    if (!title) {
      const heading = { note: 'New note', task: 'New task', idea: 'New idea' }[what] + ' · ' + AREAS[area].label;
      return new TitleModal(this.app, heading, (t) => this.create(what, t, newTab, area)).open();
    }
    const board = this.app.plugins.plugins['sb-board'];
    if (what !== 'note' && board && board.createCard) {
      let project = '';
      const act = this.app.workspace.getActiveFile();
      if (act && areaOf(act.path) === area) {
        const fm = (this.app.metadataCache.getFileCache(act) || {}).frontmatter || {};
        if (fm.type === 'project' || fm.type === 'research') project = act.basename;
        else if (fm.project) project = linkName(fm.project);
      }
      const f = await board.createCard(what, { title, status: what === 'task' ? 'todo' : 'idea', priority: '', due: '', project, area });
      if (f) await this.app.workspace.getLeaf(newTab ? 'tab' : false).openFile(f);
      return;
    }
    const INBOX = AREAS[area].inbox;
    if (!this.app.vault.getAbstractFileByPath(INBOX)) await this.app.vault.createFolder(INBOX).catch(() => {});
    const base = sanitizeName(title) || 'New note';
    let path = normalizePath(`${INBOX}/${base}.md`), n = 2;
    while (this.app.vault.getAbstractFileByPath(path)) path = normalizePath(`${INBOX}/${base} (${n++}).md`);
    const f = await this.app.vault.create(path, `---\ncreated: ${today()}\n---\n# ${title}\n\n`);
    const leaf = this.app.workspace.getLeaf(newTab ? 'tab' : false);
    await leaf.openFile(f);
  }

  // ------------------------------------------------ reminders
  dueItems(ahead, scope) {
    if (scope === undefined) scope = this.settings.remindScope || '';
    const t = today(), out = [];
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (!analysable(f.path, scope)) continue;
      const fm = (this.app.metadataCache.getFileCache(f) || {}).frontmatter;
      if (!fm || fm.type !== 'task' || DONE.has(String(fm.status || ''))) continue;
      const due = dateStr(fm.due);
      if (!due) continue;
      const days = daysBetween(t, due);
      if (days !== null && days <= ahead) out.push({ file: f, title: f.basename, due, days, project: (areaOf(f.path) === 'work' ? 'Work · ' : '') + linkName(fm.project) });
    }
    return out.sort((a, b) => a.days - b.days);
  }
  updateStatus() {
    if (!this.statusEl) return;
    const items = this.dueItems(this.settings.daysAhead);
    const over = items.filter((i) => i.days < 0).length, now = items.filter((i) => i.days === 0).length, soon = items.length - over - now;
    const parts = [over && `${over} overdue`, now && `${now} today`, soon && `${soon} upcoming`].filter(Boolean);
    this.statusEl.setText(parts.length ? '⏰ ' + parts.join(' · ') : '');
    this.statusEl.setAttr('title', 'Upcoming tasks (click)');
  }
  restartReminders() {
    if (this.interval) window.clearInterval(this.interval);
    this.interval = null;
    if (!this.settings.remind) return;
    this.interval = window.setInterval(() => this.checkReminders(false), Math.max(5, this.settings.intervalMin) * 60000);
    this.registerInterval(this.interval);
  }
  notifiedKey() { return 'sb-tools-notified'; }
  loadNotified() {
    try { return JSON.parse(this.app.loadLocalStorage ? this.app.loadLocalStorage(this.notifiedKey()) || '{}' : window.localStorage.getItem(this.notifiedKey()) || '{}'); } catch (e) { return {}; }
  }
  saveNotified(v) {
    const s = JSON.stringify(v);
    try { if (this.app.saveLocalStorage) this.app.saveLocalStorage(this.notifiedKey(), s); else window.localStorage.setItem(this.notifiedKey(), s); } catch (e) { /* ignore */ }
  }
  checkReminders(manual) {
    this.updateStatus();
    if (!this.settings.remind && !manual) return;
    const t = today();
    const items = this.dueItems(this.settings.daysAhead);
    const seen = this.loadNotified();
    for (const k of Object.keys(seen)) if (seen[k] !== t) delete seen[k];
    const fresh = manual ? items : items.filter((i) => seen[i.file.path] !== t);
    if (!fresh.length) { if (manual) new Notice('No upcoming or overdue tasks.'); return; }
    const lines = fresh.slice(0, 6).map((i) => `• ${i.title} (${dueText(i.days)})`);
    if (fresh.length > 6) lines.push(`… and ${fresh.length - 6} more`);
    const notice = new Notice('⏰ Task reminder\n' + lines.join('\n'), 15000);
    if (notice.noticeEl) notice.noticeEl.onclick = () => new DueListModal(this.app, items).open();
    if (this.settings.systemNotify && typeof Notification !== 'undefined') {
      try {
        const n = new Notification('Second Brain: task reminder', { body: lines.join('\n') });
        n.onclick = () => { window.focus(); new DueListModal(this.app, items).open(); };
      } catch (e) { /* system notifications not permitted */ }
    }
    for (const i of fresh) seen[i.file.path] = t;
    this.saveNotified(seen);
  }

  // ------------------------------------------------ heatmap helpers
  gitDays(since, scope) {
    return new Promise((resolve) => {
      const base = this.app.vault.adapter && this.app.vault.adapter.basePath;
      if (!base) return resolve({});
      let cp;
      try { cp = require('child_process'); } catch (e) { return resolve({}); }
      const args = ['log', `--since=${since}`, '--date=short', '--format=%ad'];
      if (scope && AREAS[scope]) args.push('--', AREAS[scope].root);
      cp.execFile('git', args, { cwd: base, windowsHide: true, maxBuffer: 8 * 1024 * 1024 }, (err, stdout) => {
        if (err) return resolve({});
        const out = {};
        for (const d of String(stdout).split(/\r?\n/)) if (d) out[d] = (out[d] || 0) + 1;
        resolve(out);
      });
    });
  }
  openDay(day, scope) {
    const items = collectDated(this.app, { scope }).filter((i) => i.date === day);
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (!analysable(f.path, scope)) continue;
      const fm = ((this.app.metadataCache.getFileCache(f) || {}).frontmatter) || {};
      if (dateStr(fm.created) === day || ymd(new Date(f.stat.mtime)) === day) items.push({ date: day, kind: 'note', file: f, title: f.basename });
    }
    const KN = Object.assign({ note: { icon: '📝', label: 'Note' } }, KIND);
    const m = new Modal(this.app);
    m.titleEl.setText(day);
    if (!items.length) m.contentEl.createDiv({ text: 'No tasks or notes for this day (activity may be git commits only).' });
    for (const it of items) {
      const r = m.contentEl.createDiv({ cls: 'sbt-cal-item sbt-' + it.kind, text: `${KN[it.kind].icon} ${it.title}` });
      r.onclick = () => { m.close(); this.app.workspace.getLeaf(false).openFile(it.file); };
    }
    m.open();
  }

  // ------------------------------------------------ import
  pickAndImport() {
    const act = this.app.workspace.getActiveFile();
    const area = (act && areaOf(act.path)) || 'personal';
    const ATTACH = AREAS[area].attach;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx,.xlsx,.pdf,.pptx,.csv';
    input.onchange = async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (!this.app.vault.getAbstractFileByPath(ATTACH)) await this.app.vault.createFolder(ATTACH).catch(() => {});
      const name = file.name.replace(/[\\/:*?"<>|#^\[\]]/g, ' ');
      let path = normalizePath(`${ATTACH}/${name}`), n = 2;
      const dot = name.lastIndexOf('.');
      while (this.app.vault.getAbstractFileByPath(path)) path = normalizePath(`${ATTACH}/${name.slice(0, dot)} (${n++})${name.slice(dot)}`);
      await this.app.vault.createBinary(path, await file.arrayBuffer());
      this.runImport(path);
    };
    input.click();
  }
  runImport(path) {
    if (isProtected(path)) return;
    const area = areaOf(path) || 'personal';
    const base = this.app.vault.adapter && this.app.vault.adapter.basePath;
    if (!base) { new Notice('Import works on desktop only.'); return; }
    const cp = require('child_process');
    const notice = new Notice('Importing: ' + path.split('/').pop(), 0);
    const tryRun = (cmds) => {
      if (!cmds.length) { notice.hide(); new Notice('Python not found: import needs Python 3.'); return; }
      const [exe, ...pre] = cmds[0];
      cp.execFile(exe, [...pre, '-X', 'utf8', TOOL, 'import', path, '--json', '--scope', area], { cwd: base, windowsHide: true, maxBuffer: 32 * 1024 * 1024 }, async (err, stdout, stderr) => {
        if (err && err.code === 'ENOENT') return tryRun(cmds.slice(1));
        notice.hide();
        let res = null;
        try { res = JSON.parse(String(stdout).trim().split(/\r?\n/).pop()); } catch (e) { /* not json */ }
        if (!res || !res.note) { new Notice('Import failed: ' + (String(stderr || stdout || (err && err.message)).trim().slice(-300))); return; }
        new Notice(`Note created: ${res.note}` + (res.warning ? `\n${res.warning}` : ''), 8000);
        const tryOpen = (k) => {
          const f = this.app.vault.getAbstractFileByPath(res.note);
          if (f instanceof TFile) this.app.workspace.getLeaf('tab').openFile(f);
          else if (k < 10) setTimeout(() => tryOpen(k + 1), 300);
        };
        tryOpen(0);
      });
    };
    tryRun([['python'], ['py', '-3'], ['python3']]);
  }
  onunload() { if (this.interval) window.clearInterval(this.interval); }
}

SbToolsPlugin._test = { isProtected, setProtected: (l) => { PROTECTED_DIRS = l; }, areaOf, parseScope, inScope, AREAS, parseConfig, dateStr, daysBetween, addDays, levels, streaks, parseCsv, parseXlsx, unzip, colIndex, colName, collectDated, activityFromVault, linkName, dueText, sanitizeName };
module.exports = SbToolsPlugin;
