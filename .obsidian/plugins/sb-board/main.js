/* Second Brain Board: kanban boards over notes.
 * Each card is a note; the column is a frontmatter property (default `status`).
 * Usage inside any note:
 *
 * ```sb-board
 * type: task                # task | project | research | idea | decision (comma-separated allowed)
 * project: Website Redesign # optional: only cards whose `project` links to this hub
 * columns: todo, doing, done   # optional, defaults per type
 * hide-done-after: 14       # optional: hide done cards completed more than N days ago
 * wip: doing=3              # optional: WIP limits, comma separated
 * title: Tasks              # optional
 * filters: true             # optional: show filter bar (default true)
 * scope: work               # optional: personal | work | all (default all; the filter bar can switch)
 * ```
 * The vault has two areas, Personal/ and Work/. New cards go to the area of their project.
 * Folders listed under "protected" in `99 System/config.json` are never read or written.
 */
'use strict';
const obsidian = require('obsidian');
const { Plugin, MarkdownRenderChild, Modal, Notice, Menu, Setting, TFile, normalizePath } = obsidian;

const CONFIG_PATH = '99 System/config.json';
const TEMPLATES = '99 System/Templates/';
const AREAS = {
  personal: { root: 'Personal', label: 'Personal', tasks: 'Personal/15 Tasks', ideas: 'Personal/50 Ideas' },
  work: { root: 'Work', label: 'Work', tasks: 'Work/50 Tasks', ideas: 'Work/00 Inbox' },
};
const SCOPE_ALIASES = { personal: 'personal', p: 'personal', work: 'work', w: 'work', all: '', both: '', '': '' };
function areaOf(path) {
  for (const [k, a] of Object.entries(AREAS)) if (path === a.root || path.startsWith(a.root + '/')) return k;
  return '';
}
function parseScope(v) {
  const k = String(v || '').trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(SCOPE_ALIASES, k) ? SCOPE_ALIASES[k] : '';
}
const BOARD_NOTE = 'Board.md';

const DEFAULT_COLUMNS = {
  task: ['todo', 'doing', 'done'],
  project: ['active', 'paused', 'done', 'archived'],
  research: ['active', 'paused', 'done', 'archived'],
  idea: ['idea', 'exploring', 'promoted', 'dropped'],
  decision: ['proposed', 'accepted', 'rejected', 'superseded'],
};
const LABELS = {
  backlog: 'Backlog', todo: 'To Do', doing: 'In Progress', blocked: 'Blocked', done: 'Done',
  active: 'Active', paused: 'Paused', archived: 'Archived',
  idea: 'Idea', exploring: 'Exploring', promoted: 'Promoted', dropped: 'Dropped',
  proposed: 'Proposed', accepted: 'Accepted', rejected: 'Rejected', superseded: 'Superseded',
  __none: 'Other',
};
const DONE_STATES = new Set(['done', 'archived', 'dropped', 'rejected', 'superseded']);
const PRIORITY = { high: 0, medium: 1, low: 2 };
const PRIORITY_LABEL = { high: 'High', medium: 'Medium', low: 'Low' };
const AI_ACTIONS = ['brief', 'challenge', 'connect', 'distill', 'summarize'];

// ---------------------------------------------------------------- pure helpers
function today() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function daysBetween(a, b) {
  const pa = Date.parse(a + 'T00:00:00'), pb = Date.parse(b + 'T00:00:00');
  if (isNaN(pa) || isNaN(pb)) return null;
  return Math.round((pb - pa) / 86400000);
}
function asList(v) {
  if (v === undefined || v === null || v === '') return [];
  if (Array.isArray(v)) return v.map((x) => String(x).trim()).filter(Boolean);
  return String(v).split(',').map((x) => x.trim()).filter(Boolean);
}
function linkName(v) {
  if (Array.isArray(v)) v = v[0];
  if (v === undefined || v === null) return '';
  const s = String(v).trim();
  const m = s.match(/\[\[([^\]|#]+)/);
  const name = (m ? m[1] : s).trim();
  return name.split('/').pop().replace(/\.md$/, '');
}
function dateStr(v) {
  if (!v) return '';
  const m = String(v).trim().match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : '';
}
function sanitizeName(s) {
  return String(s).replace(/[\\/:*?"<>|#^\[\]]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 90);
}
function parseWip(v) {
  const out = {};
  for (const part of asList(v)) {
    const m = part.match(/^([\w-]+)\s*[=:]\s*(\d+)$/);
    if (m) out[m[1]] = parseInt(m[2], 10);
  }
  return out;
}
function parseConfig(src) {
  const cfg = {};
  for (const raw of src.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, '').trim();
    if (!line) continue;
    const m = line.match(/^([\w-]+)\s*:\s*(.*)$/);
    if (m) cfg[m[1].toLowerCase()] = m[2].trim();
  }
  const types = asList(cfg.type || 'task').map((t) => t.toLowerCase());
  return {
    types,
    primary: types[0],
    group: cfg.group || 'status',
    columns: asList(cfg.columns).length ? asList(cfg.columns) : (DEFAULT_COLUMNS[types[0]] || ['todo', 'doing', 'done']),
    project: cfg.project ? linkName(cfg.project) : '',
    folder: cfg.folder ? cfg.folder.replace(/\/$/, '') : '',
    hideDoneAfter: cfg['hide-done-after'] !== undefined && cfg['hide-done-after'] !== '' ? parseInt(cfg['hide-done-after'], 10) : null,
    wip: parseWip(cfg.wip),
    title: cfg.title || '',
    filters: cfg.filters === undefined ? true : !/^(false|no|0)$/i.test(cfg.filters),
    scope: parseScope(cfg.scope),
  };
}
function cardSort(a, b) {
  const pa = PRIORITY[a.priority] ?? 3, pb = PRIORITY[b.priority] ?? 3;
  if (pa !== pb) return pa - pb;
  if (a.due && b.due && a.due !== b.due) return a.due < b.due ? -1 : 1;
  if (a.due && !b.due) return -1;
  if (!a.due && b.due) return 1;
  return b.mtime - a.mtime;
}
function makeProtectedTest(list) {
  const dirs = (list || []).map((d) => String(d).replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')).filter(Boolean);
  return (path) => dirs.some((d) => path === d || path.startsWith(d + '/'));
}

// ---------------------------------------------------------------- modal
class NewCardModal extends Modal {
  constructor(app, opts, onSubmit) {
    super(app);
    this.opts = opts;
    this.onSubmit = onSubmit;
    this.values = { title: '', priority: opts.priority || '', due: '', project: opts.project || '', status: opts.status, area: opts.area || '' };
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h3', { text: this.opts.heading || 'New card' });
    new Setting(contentEl).setName('Title').addText((t) => {
      t.setPlaceholder('What needs to be done?').onChange((v) => (this.values.title = v));
      t.inputEl.style.width = '100%';
      setTimeout(() => t.inputEl.focus(), 30);
      t.inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); this.submit(); } });
    });
    if (this.opts.type === 'task') {
      new Setting(contentEl).setName('Project').addDropdown((d) => {
        d.addOption('', '— none —');
        for (const p of this.opts.projects || []) d.addOption(p, p);
        if (this.values.project && !(this.opts.projects || []).includes(this.values.project)) d.addOption(this.values.project, this.values.project);
        d.setValue(this.values.project).onChange((v) => (this.values.project = v));
      });
      new Setting(contentEl).setName('Priority').addDropdown((d) => {
        d.addOption('', '—'); d.addOption('high', 'High'); d.addOption('medium', 'Medium'); d.addOption('low', 'Low');
        d.setValue(this.values.priority).onChange((v) => (this.values.priority = v));
      });
      new Setting(contentEl).setName('Due date').addText((t) => {
        t.inputEl.type = 'date';
        t.onChange((v) => (this.values.due = v));
      });
    }
    new Setting(contentEl).setName('Area').setDesc("When a project is selected, the project's area is used").addDropdown((d) => {
      d.addOption('', 'Automatic');
      for (const [k, a] of Object.entries(AREAS)) d.addOption(k, a.label);
      d.setValue(this.values.area).onChange((v) => (this.values.area = v));
    });
    new Setting(contentEl).setName('Column').addDropdown((d) => {
      for (const c of this.opts.columns) d.addOption(c, LABELS[c] || c);
      d.setValue(this.values.status).onChange((v) => (this.values.status = v));
    });
    new Setting(contentEl).addButton((b) => b.setButtonText('Create').setCta().onClick(() => this.submit()));
  }
  submit() {
    if (!this.values.title.trim()) { new Notice('Title is required'); return; }
    this.close();
    this.onSubmit(this.values);
  }
  onClose() { this.contentEl.empty(); }
}

// ---------------------------------------------------------------- board renderer
class BoardChild extends MarkdownRenderChild {
  constructor(plugin, el, cfg, sourcePath) {
    super(el);
    this.plugin = plugin;
    this.app = plugin.app;
    this.cfg = cfg;
    this.sourcePath = sourcePath;
    this.state = { project: cfg.project || '', priority: '', q: '', soon: false, scope: cfg.scope || '' };
    this.timer = null;
  }
  onload() {
    const rerender = () => this.schedule();
    this.registerEvent(this.app.metadataCache.on('changed', rerender));
    this.registerEvent(this.app.metadataCache.on('resolved', rerender));
    this.registerEvent(this.app.vault.on('delete', rerender));
    this.registerEvent(this.app.vault.on('rename', rerender));
    this.render();
  }
  onunload() { if (this.timer) clearTimeout(this.timer); }
  schedule() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => { this.timer = null; this.render(); }, 250);
  }

  collect() {
    const cfg = this.cfg;
    const t = today();
    const cards = [];
    const taskStats = {};
    const projects = new Set();
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (this.plugin.isProtected(f.path) || f.path.startsWith(TEMPLATES)) continue;
      const cache = this.app.metadataCache.getFileCache(f);
      const fm = (cache && cache.frontmatter) || {};
      const type = String(fm.type || '').toLowerCase();
      if ((type === 'project' || type === 'research') && (!this.state.scope || areaOf(f.path) === this.state.scope)) projects.add(f.basename);
      if (type === 'task') {
        const pn = linkName(fm.project);
        if (pn) {
          const s = (taskStats[pn] = taskStats[pn] || { total: 0, done: 0, overdue: 0, doing: 0 });
          s.total += 1;
          const st = String(fm.status || '');
          if (st === 'done') s.done += 1;
          if (st === 'doing') s.doing += 1;
          const due = dateStr(fm.due);
          if (due && st !== 'done' && due < t) s.overdue += 1;
        }
      }
      if (!cfg.types.includes(type)) continue;
      if (cfg.folder && !f.path.startsWith(cfg.folder + '/')) continue;
      const tasks = ((cache && cache.listItems) || []).filter((li) => li.task !== undefined);
      cards.push({
        file: f,
        type,
        title: f.basename,
        status: fm[cfg.group] !== undefined && fm[cfg.group] !== null ? String(fm[cfg.group]) : '',
        priority: String(fm.priority || '').toLowerCase(),
        due: dateStr(fm.due),
        completed: dateStr(fm.completed),
        project: linkName(fm.project),
        ai: fm.ai ? String(fm.ai) : '',
        origin: fm.origin ? String(fm.origin) : '',
        example: fm.example === true || String(fm.example) === 'true',
        subTotal: tasks.length,
        subDone: tasks.filter((li) => li.task && li.task !== ' ').length,
        mtime: f.stat.mtime,
      });
    }
    return { cards, taskStats, projects: Array.from(projects).sort() };
  }

  passes(card) {
    const s = this.state, t = today();
    if (s.scope && areaOf(card.file.path) !== s.scope) return false;
    if (s.project && card.type !== 'project' && card.type !== 'research' && card.project !== s.project) return false;
    if (s.priority && card.priority !== s.priority) return false;
    if (s.q && !card.title.toLowerCase().includes(s.q.toLowerCase()) && !card.project.toLowerCase().includes(s.q.toLowerCase())) return false;
    if (s.soon) {
      if (!card.due || DONE_STATES.has(card.status)) return false;
      const d = daysBetween(t, card.due);
      if (d === null || d > 7) return false;
    }
    if (this.cfg.hideDoneAfter !== null && card.status === 'done' && card.completed) {
      const d = daysBetween(card.completed, t);
      if (d !== null && d > this.cfg.hideDoneAfter) return false;
    }
    return true;
  }

  render() {
    const el = this.containerEl;
    const memo = Array.from(el.querySelectorAll('.sb-col-cards')).map((x) => x.scrollTop);
    const boardScroll = el.querySelector('.sb-board') ? el.querySelector('.sb-board').scrollLeft : 0;
    el.empty();
    el.addClass('sb-board-root');
    const { cards, taskStats, projects } = this.collect();
    const cfg = this.cfg;

    const head = el.createDiv({ cls: 'sb-board-head' });
    if (cfg.title) head.createEl('div', { cls: 'sb-board-title', text: cfg.title });
    if (cfg.filters) this.renderFilters(head, projects);

    const visible = cards.filter((c) => this.passes(c));
    const board = el.createDiv({ cls: 'sb-board' });
    const cols = cfg.columns.slice();
    const extra = visible.filter((c) => !cols.includes(c.status));
    if (extra.length) cols.push('__none');

    cols.forEach((col, i) => {
      const colCards = (col === '__none' ? extra : visible.filter((c) => c.status === col)).sort(cardSort);
      const colEl = board.createDiv({ cls: 'sb-col' });
      colEl.dataset.col = col;
      if (DONE_STATES.has(col)) colEl.addClass('sb-col-done');
      const h = colEl.createDiv({ cls: 'sb-col-head' });
      h.createSpan({ cls: 'sb-col-name', text: LABELS[col] || col });
      const limit = cfg.wip[col];
      const cnt = h.createSpan({ cls: 'sb-col-count', text: limit ? `${colCards.length}/${limit}` : String(colCards.length) });
      if (limit && colCards.length > limit) { cnt.addClass('sb-over'); colEl.addClass('sb-col-over'); }
      if (col !== '__none' && (cfg.primary === 'task' || cfg.primary === 'idea')) {
        const add = h.createEl('button', { cls: 'sb-add clickable-icon', text: '+' });
        add.setAttr('aria-label', 'New card');
        add.onclick = () => this.newCard(col);
      }
      const list = colEl.createDiv({ cls: 'sb-col-cards' });
      if (memo[i]) list.scrollTop = memo[i];
      for (const c of colCards) this.renderCard(list, c, taskStats);
      if (!colCards.length) list.createDiv({ cls: 'sb-empty', text: 'Empty' });

      if (col !== '__none') {
        colEl.addEventListener('dragover', (e) => { e.preventDefault(); colEl.addClass('sb-drop'); });
        colEl.addEventListener('dragleave', (e) => { if (!colEl.contains(e.relatedTarget)) colEl.removeClass('sb-drop'); });
        colEl.addEventListener('drop', (e) => {
          e.preventDefault();
          colEl.removeClass('sb-drop');
          const path = e.dataTransfer.getData('text/sb-board-path');
          const file = path && this.app.vault.getAbstractFileByPath(path);
          if (file instanceof TFile) this.plugin.moveCard(file, cfg.group, col);
        });
      }
    });
    if (boardScroll) board.scrollLeft = boardScroll;
  }

  renderFilters(head, projects) {
    const bar = head.createDiv({ cls: 'sb-filters' });
    if (!this.cfg.scope) {
      const sc = bar.createEl('select', { cls: 'dropdown' });
      sc.createEl('option', { text: 'All areas', value: '' });
      for (const [k, a] of Object.entries(AREAS)) sc.createEl('option', { text: a.label, value: k });
      sc.value = this.state.scope;
      sc.onchange = () => { this.state.scope = sc.value; this.state.project = this.cfg.project || ''; this.render(); };
    }
    if (!this.cfg.project && this.cfg.primary !== 'project' && this.cfg.primary !== 'research') {
      const sel = bar.createEl('select', { cls: 'dropdown' });
      sel.createEl('option', { text: 'All projects', value: '' });
      for (const p of projects) sel.createEl('option', { text: p, value: p });
      sel.value = this.state.project;
      sel.onchange = () => { this.state.project = sel.value; this.render(); };
    }
    if (this.cfg.primary === 'task') {
      const pr = bar.createEl('select', { cls: 'dropdown' });
      pr.createEl('option', { text: 'All priorities', value: '' });
      for (const k of ['high', 'medium', 'low']) pr.createEl('option', { text: PRIORITY_LABEL[k], value: k });
      pr.value = this.state.priority;
      pr.onchange = () => { this.state.priority = pr.value; this.render(); };
      const soon = bar.createEl('label', { cls: 'sb-toggle' });
      const cb = soon.createEl('input', { type: 'checkbox' });
      cb.checked = this.state.soon;
      soon.appendText(' Due in 7 days / overdue');
      cb.onchange = () => { this.state.soon = cb.checked; this.render(); };
    }
    const q = bar.createEl('input', { type: 'search', cls: 'sb-search', placeholder: 'Search…' });
    q.value = this.state.q;
    q.oninput = () => { this.state.q = q.value; this.schedule(); };
  }

  renderCard(list, c, taskStats) {
    const t = today();
    const card = list.createDiv({ cls: 'sb-card' });
    card.setAttr('draggable', 'true');
    if (c.priority) card.addClass('sb-p-' + c.priority);
    card.createDiv({ cls: 'sb-card-title', text: c.title });
    const meta = card.createDiv({ cls: 'sb-card-meta' });
    if (c.priority && PRIORITY_LABEL[c.priority]) meta.createSpan({ cls: 'sb-badge sb-prio-' + c.priority, text: PRIORITY_LABEL[c.priority] });
    if (c.due) {
      const d = daysBetween(t, c.due);
      const b = meta.createSpan({ cls: 'sb-badge sb-due', text: '📅 ' + c.due.slice(5) });
      if (!DONE_STATES.has(c.status) && d !== null) {
        if (d < 0) { b.addClass('sb-overdue'); b.setAttr('title', `${-d} days overdue`); }
        else if (d <= 3) { b.addClass('sb-soon'); b.setAttr('title', d === 0 ? 'Today' : `${d} days left`); }
      }
    }
    if (c.project && !this.cfg.project && c.type !== 'project') meta.createSpan({ cls: 'sb-badge sb-proj', text: c.project });
    if (!this.state.scope && areaOf(c.file.path) === 'work') meta.createSpan({ cls: 'sb-badge sb-area', text: 'Work' });
    if (c.subTotal) meta.createSpan({ cls: 'sb-badge', text: `☑ ${c.subDone}/${c.subTotal}` });
    if (c.origin === 'ai-suggestion') meta.createSpan({ cls: 'sb-badge sb-ai', text: 'AI suggestion' });
    if (c.ai) meta.createSpan({ cls: 'sb-badge sb-ai', text: '🤖 ' + c.ai });
    if (c.example) meta.createSpan({ cls: 'sb-badge sb-muted', text: 'example' });
    if (c.type === 'project' || c.type === 'research') {
      const s = taskStats[c.title];
      if (s && s.total) {
        const pct = Math.round((100 * s.done) / s.total);
        card.createDiv({ cls: 'sb-progress' }).createDiv({ cls: 'sb-progress-bar' }).style.width = pct + '%';
        const line = card.createDiv({ cls: 'sb-card-meta' });
        line.createSpan({ cls: 'sb-badge', text: `${s.done}/${s.total} tasks · ${pct}%` });
        if (s.doing) line.createSpan({ cls: 'sb-badge', text: `${s.doing} in progress` });
        if (s.overdue) line.createSpan({ cls: 'sb-badge sb-overdue', text: `${s.overdue} overdue` });
      } else {
        card.createDiv({ cls: 'sb-card-meta' }).createSpan({ cls: 'sb-badge sb-muted', text: 'no tasks' });
      }
    }

    card.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/sb-board-path', c.file.path);
      e.dataTransfer.effectAllowed = 'move';
      card.addClass('sb-dragging');
    });
    card.addEventListener('dragend', () => card.removeClass('sb-dragging'));
    card.addEventListener('click', (e) => this.app.workspace.getLeaf(e.ctrlKey || e.metaKey ? 'tab' : false).openFile(c.file));
    card.addEventListener('mouseover', (e) => {
      this.app.workspace.trigger('hover-link', {
        event: e, source: 'sb-board', hoverParent: this, targetEl: card, linktext: c.file.path, sourcePath: this.sourcePath,
      });
    });
    card.addEventListener('contextmenu', (e) => { e.preventDefault(); this.cardMenu(e, c); });
  }

  cardMenu(e, c) {
    const menu = new Menu();
    menu.addItem((i) => i.setTitle('Open').setIcon('file').onClick(() => this.app.workspace.getLeaf(false).openFile(c.file)));
    menu.addItem((i) => i.setTitle('Open in new tab').setIcon('file-plus').onClick(() => this.app.workspace.getLeaf('tab').openFile(c.file)));
    menu.addSeparator();
    for (const col of this.cfg.columns) {
      if (col === c.status) continue;
      menu.addItem((i) => i.setTitle('Move → ' + (LABELS[col] || col)).setIcon('arrow-right').onClick(() => this.plugin.moveCard(c.file, this.cfg.group, col)));
    }
    if (c.type === 'task') {
      menu.addSeparator();
      for (const k of ['high', 'medium', 'low', '']) {
        menu.addItem((i) => i.setTitle('Priority: ' + (PRIORITY_LABEL[k] || 'none')).setIcon('flag').onClick(() => this.plugin.setProp(c.file, 'priority', k)));
      }
    }
    menu.addSeparator();
    for (const a of AI_ACTIONS) {
      menu.addItem((i) => i.setTitle('Send to AI queue: ' + a).setIcon('bot').onClick(async () => {
        await this.plugin.setProp(c.file, 'ai', a);
        new Notice(`Added to the AI queue (${a}). Run /sb-queue in Claude Code.`);
      }));
    }
    menu.showAtMouseEvent(e);
  }

  newCard(col) {
    const { projects } = this.collect();
    new NewCardModal(this.app, {
      type: this.cfg.primary, columns: this.cfg.columns, status: col,
      project: this.cfg.project || this.state.project || '', projects, area: this.state.scope || '',
      heading: this.cfg.primary === 'idea' ? 'New idea' : 'New task',
    }, (v) => this.plugin.createCard(this.cfg.primary, v)).open();
  }
}

// ---------------------------------------------------------------- plugin
class SbBoardPlugin extends Plugin {
  async onload() {
    this.isProtected = makeProtectedTest([]);
    await this.loadVaultConfig();
    this.registerEvent(this.app.vault.on('modify', (f) => { if (f.path === CONFIG_PATH) this.loadVaultConfig(); }));
    this.registerMarkdownCodeBlockProcessor('sb-board', (src, el, ctx) => {
      ctx.addChild(new BoardChild(this, el, parseConfig(src), ctx.sourcePath));
    });
    this.registerHoverLinkSource('sb-board', { display: 'Second Brain Board', defaultMod: false });
    this.addRibbonIcon('layout-dashboard', 'Board', () => this.openBoard());
    this.addCommand({ id: 'open-board', name: 'Open board', callback: () => this.openBoard() });
    this.addCommand({ id: 'quick-add-task', name: 'Quick add task', callback: () => this.quickAdd('task') });
    this.addCommand({ id: 'quick-add-idea', name: 'Quick add idea', callback: () => this.quickAdd('idea') });
    // Task cards live in <tasks>/<Project>/; when a card's `project` changes, move it to the matching folder.
    this.relocateTimers = new Map();
    this.registerEvent(this.app.metadataCache.on('changed', (file) => this.scheduleRelocate(file)));
    this.addCommand({ id: 'sort-task-folders', name: 'Sort task cards into project folders', callback: () => this.relocateAll() });
  }

  onunload() {
    for (const t of (this.relocateTimers || new Map()).values()) window.clearTimeout(t);
  }

  taskRootOf(path) {
    for (const k of Object.keys(AREAS)) if (path.startsWith(AREAS[k].tasks + '/')) return k;
    return '';
  }

  taskFolder(area, project) {
    const root = AREAS[area].tasks;
    const name = project ? sanitizeName(project) : '';
    return name ? `${root}/${name}` : root;
  }

  expectedTaskFolder(file) {
    const area = this.taskRootOf(file.path);
    if (!area) return null; // only cards inside a tasks folder are managed
    const fm = (this.app.metadataCache.getFileCache(file) || {}).frontmatter || {};
    if (fm.type !== 'task') return null;
    const project = linkName(fm.project);
    return this.taskFolder(this.projectArea(project) || area, project);
  }

  scheduleRelocate(file) {
    if (!(file instanceof TFile) || file.extension !== 'md' || !this.taskRootOf(file.path)) return;
    const prev = this.relocateTimers.get(file.path);
    if (prev) window.clearTimeout(prev);
    // wait until typing in the properties panel settles
    this.relocateTimers.set(file.path, window.setTimeout(() => {
      this.relocateTimers.delete(file.path);
      this.relocate(file).catch((e) => console.error('sb-board relocate', e));
    }, 2000));
  }

  async relocate(file) {
    if (!this.app.vault.getAbstractFileByPath(file.path)) return false;
    const folder = this.expectedTaskFolder(file);
    if (folder === null || (file.parent && file.parent.path === folder)) return false;
    if (!this.app.vault.getAbstractFileByPath(folder)) await this.app.vault.createFolder(folder).catch(() => {});
    let path = normalizePath(`${folder}/${file.name}`);
    let n = 2;
    while (this.app.vault.getAbstractFileByPath(path)) path = normalizePath(`${folder}/${file.basename} (${n++}).md`);
    const from = file.parent ? file.parent.path : '';
    await this.app.fileManager.renameFile(file, path);
    await this.removeIfEmpty(from);
    return true;
  }

  async removeIfEmpty(folderPath) {
    const f = this.app.vault.getAbstractFileByPath(folderPath);
    if (!f || f instanceof TFile || !this.taskRootOf(folderPath + '/x')) return;
    if (Object.values(AREAS).some((a) => a.tasks === folderPath)) return; // never remove the area roots
    if (f.children && f.children.length === 0) await this.app.vault.delete(f, true).catch(() => {});
  }

  async relocateAll() {
    let moved = 0;
    for (const f of this.app.vault.getMarkdownFiles()) if (this.taskRootOf(f.path) && (await this.relocate(f))) moved++;
    new Notice(moved ? `${moved} card(s) moved to their project folder.` : 'All cards are already in the right folder.');
  }

  async loadVaultConfig() {
    try {
      if (await this.app.vault.adapter.exists(CONFIG_PATH)) {
        const cfg = JSON.parse(await this.app.vault.adapter.read(CONFIG_PATH));
        this.isProtected = makeProtectedTest(cfg.protected);
      }
    } catch (e) {
      console.error('sb-board: could not read ' + CONFIG_PATH, e);
    }
  }

  async openBoard() {
    const f = this.app.vault.getAbstractFileByPath(BOARD_NOTE);
    if (f instanceof TFile) await this.app.workspace.getLeaf(false).openFile(f);
    else new Notice(`${BOARD_NOTE} not found`);
  }

  activeProjects() {
    const out = [];
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (this.isProtected(f.path) || f.path.startsWith(TEMPLATES)) continue;
      const fm = (this.app.metadataCache.getFileCache(f) || {}).frontmatter || {};
      if ((fm.type === 'project' || fm.type === 'research') && fm.status !== 'archived') out.push(f.basename);
    }
    return out.sort();
  }

  quickAdd(type) {
    let project = '';
    const active = this.app.workspace.getActiveFile();
    const area = active ? areaOf(active.path) : '';
    if (active && !this.isProtected(active.path)) {
      const fm = (this.app.metadataCache.getFileCache(active) || {}).frontmatter || {};
      if (fm.type === 'project' || fm.type === 'research') project = active.basename;
      else if (fm.project) project = linkName(fm.project);
    }
    new NewCardModal(this.app, {
      type, columns: DEFAULT_COLUMNS[type], status: type === 'task' ? 'todo' : 'idea', project, projects: this.activeProjects(), area,
      heading: type === 'task' ? 'Quick task' : 'Quick idea',
    }, (v) => this.createCard(type, v)).open();
  }

  async moveCard(file, group, col) {
    if (this.isProtected(file.path)) return;
    const d = today();
    await this.app.fileManager.processFrontMatter(file, (fm) => {
      const type = String(fm.type || '');
      fm[group] = col;
      if (group !== 'status') return;
      if (type === 'task') {
        if (col === 'done') fm.completed = d; else delete fm.completed;
        if (col === 'doing' && !fm.started) fm.started = d;
      }
      if (type === 'decision' && col === 'accepted' && !fm.decided) fm.decided = d;
    });
    if (col === 'promoted') new Notice('Idea promoted: run /sb-new in Claude Code to create its hub.');
  }

  async setProp(file, key, value) {
    if (this.isProtected(file.path)) return;
    await this.app.fileManager.processFrontMatter(file, (fm) => {
      if (value === '' || value === null || value === undefined) delete fm[key]; else fm[key] = value;
    });
  }

  projectArea(name) {
    if (!name) return '';
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (f.basename !== name || f.path.startsWith(TEMPLATES)) continue;
      const fm = (this.app.metadataCache.getFileCache(f) || {}).frontmatter || {};
      if (fm.type === 'project' || fm.type === 'research') return areaOf(f.path);
    }
    return '';
  }

  async titleHeading() {
    try { return JSON.parse(await this.app.vault.adapter.read('99 System/config.json')).title_heading !== false; } catch (e) { return true; }
  }
  async createCard(type, v) {
    const area = this.projectArea(v.project) || v.area || 'personal';
    const folder = type === 'idea' ? AREAS[area].ideas : this.taskFolder(area, v.project);
    if (!this.app.vault.getAbstractFileByPath(folder)) await this.app.vault.createFolder(folder).catch(() => {});
    const base = sanitizeName(v.title) || 'New card';
    let path = normalizePath(`${folder}/${base}.md`);
    let n = 2;
    while (this.app.vault.getAbstractFileByPath(path)) path = normalizePath(`${folder}/${base} (${n++}).md`);
    const lines = ['---', `type: ${type}`, `status: ${v.status}`];
    if (type === 'task') {
      if (v.priority) lines.push(`priority: ${v.priority}`);
      if (v.project) lines.push(`project: "[[${v.project}]]"`);
      if (v.due) lines.push(`due: ${v.due}`);
    }
    lines.push(`created: ${today()}`, '---');
    if (await this.titleHeading()) lines.push(`# ${v.title.trim()}`);  // config title_heading: false → file name is the title
    lines.push('');
    if (type === 'task') lines.push('## Description', '', '## Subtasks', '- [ ] ', '', '## Notes', '');
    else lines.push('## Idea', '', '## Why it matters / what it connects to', '', '## Next step', '');
    const file = await this.app.vault.create(path, lines.join('\n'));
    new Notice('Card created: ' + file.basename);
    return file;
  }
}

SbBoardPlugin._test = { areaOf, parseScope, AREAS, parseConfig, linkName, dateStr, sanitizeName, cardSort, daysBetween, parseWip, asList, makeProtectedTest };
module.exports = SbBoardPlugin;
