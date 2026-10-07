'use strict';

// Run from project root: node --test <this file>
// Optional candidate path: ARCHIVE_NAV_TEMPLATE=<template> node --test <this file>
// Execute extracted production code in vm; the DOM below models generated nodes,
// native details state, events, focus and disconnection without external packages.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const defaultTemplate = path.resolve(__dirname, '../../模板.html');
const templatePath = process.env.ARCHIVE_NAV_TEMPLATE
  || (fs.existsSync(defaultTemplate) ? defaultTemplate : path.resolve(process.cwd(), '模板.html'));
const template = fs.readFileSync(templatePath, 'utf8');

function extractFunction(source, name) {
  const expression = new RegExp('(?:async\\s+)?function\\s+' + name + '\\s*\\(');
  const found = expression.exec(source);
  assert.ok(found, 'Production function absent: ' + name + ' in ' + templatePath);
  const start = found.index, body = source.indexOf('{', start);
  let depth = 0, quote = '', line = false, block = false;
  for (let i = body; i < source.length; i++) {
    const c = source[i], next = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && next === '/') { block = false; i++; } continue; }
    if (quote) { if (c === '\\') i++; else if (c === quote) quote = ''; continue; }
    if (c === '/' && next === '/') { line = true; i++; continue; }
    if (c === '/' && next === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error('Unclosed production function: ' + name);
}

const helperNames = ['saveTocLabel', 'saveTocRead', 'saveTocRemember', 'saveTocRow', 'saveTocGroup', 'renderSaveToc'];
const stateMatch = template.match(/(?:const|let)\s+SAVETOC\s*=[^\n]+/);
assert.ok(stateMatch, 'The selected template does not include the approved archive-navigation helpers: ' + templatePath);
const helperSource = stateMatch[0] + '\n' + helperNames.map(name => extractFunction(template, name)).join('\n');
const showSavesSource = extractFunction(template, 'showSaves');
const rowMarker = template.indexOf("const r = e.target.closest('.row[data-sv]')");
assert.ok(rowMarker >= 0, 'Original data-sv click dispatcher must remain');
const clickStart = template.lastIndexOf("$('#toc').addEventListener('click'", rowMarker);
const clickEnd = template.indexOf('\n});', rowMarker);
assert.ok(clickStart >= 0 && clickEnd > clickStart, 'Original data-sv click dispatcher must be extractable');
const clickSource = template.slice(clickStart, clickEnd + '\n});'.length);

const decode = value => String(value).replace(/&(?:amp|lt|gt|quot|#39|#x27);/g, entity => ({
  '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&#x27;': "'"
})[entity]);
const escape = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
})[c]);

class TextNode {
  constructor(text, parent) { this.text = decode(text); this.parentElement = parent; }
  get textContent() { return this.text; }
}

class Element {
  constructor(tag, document, parent = null) {
    this.tagName = tag.toLowerCase(); this.ownerDocument = document;
    this.parentElement = parent; this.children = []; this.dataset = {};
    this.attributes = {}; this.listeners = new Map(); this._open = false;
    this._html = ''; this.tabIndex = -1; this.clicks = 0;
  }
  setAttribute(key, value) {
    this.attributes[key] = String(value);
    if (key.startsWith('data-')) this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
    if (key === 'open') this._open = true;
    if (key === 'tabindex') this.tabIndex = Number(value);
  }
  getAttribute(key) { return Object.prototype.hasOwnProperty.call(this.attributes, key) ? this.attributes[key] : null; }
  get className() { return this.attributes.class || ''; }
  get isConnected() { return this === this.ownerDocument.body || !!(this.parentElement && this.parentElement.isConnected); }
  get open() { return this._open; }
  set open(value) {
    const next = !!value, changed = next !== this._open;
    this._open = next;
    if (changed) this.dispatch('toggle', { bubbles: false });
  }
  get textContent() { return this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.innerHTML = escape(value); }
  get innerHTML() { return this._html; }
  set innerHTML(html) {
    this.children.forEach(child => { child.parentElement = null; });
    this.children = []; this._html = String(html);
    const stack = [this], tokens = this._html.match(/<\/?[^>]+>|[^<]+/g) || [];
    for (const token of tokens) {
      if (token.startsWith('</')) { if (stack.length > 1) stack.pop(); continue; }
      if (!token.startsWith('<')) { stack[stack.length - 1].children.push(new TextNode(token, stack[stack.length - 1])); continue; }
      const tag = /^<([\w-]+)/.exec(token); if (!tag) continue;
      const node = new Element(tag[1], this.ownerDocument, stack[stack.length - 1]);
      const attrs = token.slice(tag[0].length, -1);
      const attrPattern = /([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
      for (const attribute of attrs.matchAll(attrPattern)) node.setAttribute(attribute[1], decode(attribute[2] ?? attribute[3] ?? attribute[4] ?? ''));
      stack[stack.length - 1].children.push(node);
      if (!token.endsWith('/>') && !['input', 'img', 'br', 'hr', 'meta', 'link'].includes(node.tagName)) stack.push(node);
    }
  }
  matches(selector) {
    const tag = /^[\w-]+/.exec(selector), classes = [...selector.matchAll(/\.([\w-]+)/g)].map(match => match[1]);
    const attribute = /\[([\w-]+)(?:="([^"]*)")?\]/.exec(selector);
    return (!tag || this.tagName === tag[0])
      && classes.every(name => this.className.split(/\s+/).includes(name))
      && (!attribute || (this.getAttribute(attribute[1]) !== null && (attribute[2] === undefined || this.getAttribute(attribute[1]) === attribute[2])));
  }
  closest(selector) { for (let node = this; node; node = node.parentElement) if (node.matches(selector)) return node; return null; }
  contains(node) { for (let item = node; item; item = item.parentElement) if (item === this) return true; return false; }
  querySelectorAll(selector) {
    const result = [];
    const walk = node => node.children.forEach(child => {
      if (!(child instanceof Element)) return;
      if (child.matches(selector)) result.push(child); walk(child);
    });
    walk(this); return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  addEventListener(type, fn) { if (!this.listeners.has(type)) this.listeners.set(type, []); this.listeners.get(type).push(fn); }
  dispatch(type, details = {}) {
    const event = { type, target: this, key: '', defaultPrevented: false, bubbles: type !== 'toggle',
      preventDefault() { this.defaultPrevented = true; }, ...details };
    for (let node = this; node; node = event.bubbles ? node.parentElement : null) {
      for (const listener of node.listeners.get(type) || []) listener(event);
    }
    return event;
  }
  click() { this.clicks++; return this.dispatch('click'); }
  focus(options) { this.ownerDocument.activeElement = this; this.lastFocusOptions = options; }
}

const data = (prefix = 'A') => ({ total: 100, keep: 10, dropped: [], saves: [
  { code: prefix + '2', name: 'Latest', at: '2026-10-06 12:00', grade: '绿档', settled: true },
  { code: prefix + '1', name: 'Earlier', at: '2026-10-05 12:00', grade: '黄档', settled: false }
] });

function harness(options = {}) {
  const storage = options.storage || new Map(), document = { activeElement: null, title: '' };
  document.body = new Element('body', document);
  const toc = new Element('aside', document, document.body), saveview = new Element('main', document, document.body);
  document.body.children.push(toc, saveview);
  document.activeElement = document.body;
  const calls = [], first = options.data || data(), context = vm.createContext({
    console, document, Map, Set, Object, Array, JSON, String, Number,
    view: 'saves', S: { project: { root: options.root || 'project-A', name: 'Test project' } },
    SV: first, SVSEL: options.selection || 'tree', SVLOAD: 0, online: true,
    esc: escape, getLang: () => options.lang || 'zh', fmtSize: total => total + ' B',
    uiIcon: name => '<svg data-test-icon="' + escape(name) + '"><path d="M0 0"/></svg>',
    saveLamp: item => '<span class="sd ' + (item.grade === '绿档' ? 's-ok' : 's-warn') + '"></span>',
    localStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, String(value)) },
    $: selector => selector === '#toc' ? toc : selector === '#saveview' ? saveview : null,
    wt3dStop: () => calls.push(['stop']), showSaveTree: force => calls.push(['tree', force]),
    showSaveForm: () => calls.push(['new']), showNowNode: () => calls.push(['now']),
    showSavePage: key => calls.push(['page', key]), showSaveDetail: key => calls.push(['detail', key]),
    toast: message => calls.push(['toast', message]), setToc: (...args) => calls.push(['setToc', ...args]),
    window: { scrollTo: (...args) => calls.push(['scroll', ...args]) }
  });
  context.api = async () => context.SV;
  vm.runInContext(helperSource + '\n' + showSavesSource + '\n' + clickSource, context, { filename: templatePath });
  const row = key => toc.querySelectorAll('.row[data-sv]').find(node => node.dataset.sv === key);
  const group = key => toc.querySelectorAll('details[data-save-group]').find(node => node.dataset.saveGroup === key);
  return { context, toc, saveview, storage, calls, row, group, render: () => context.renderSaveToc(),
    state: () => vm.runInContext('SAVETOC', context) };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

test('production source selected: ' + templatePath, () => {
  assert.ok(helperNames.length && showSavesSource && clickSource);
});

test('first visit exposes overview, one checkpoint group and current date; removes persistent runs duplication', () => {
  const h = harness(); h.render();
  assert.equal(h.row('tree').getAttribute('aria-current'), 'page');
  assert.equal(h.group('checkpoints').open, true);
  assert.equal(h.group('day:2026-10-06').open, true);
  assert.equal(h.group('day:2026-10-05').open, false);
  assert.equal(h.group('branches').open, false);
  assert.equal(h.row('runs'), undefined);
  assert.deepEqual(h.toc.querySelectorAll('.row[data-sv]').map(node => node.dataset.sv),
    ['tree', '现在', 'new', 'A2', 'A1', 'branches', 'demos', 'merges']);
});

test('manual collapse survives periodic same-selection refresh and a fresh page load', () => {
  const h = harness({ selection: 'A2' }); h.render();
  h.group('day:2026-10-06').open = false;
  h.group('checkpoints').open = false;
  h.render();
  assert.equal(h.group('checkpoints').open, false);
  assert.equal(h.group('day:2026-10-06').open, false);
  // Loading the overview again must preserve the user's folds. Deep-linking to
  // a checkpoint intentionally opens its ancestors and is covered separately.
  const second = harness({ storage: h.storage }); second.render();
  assert.equal(second.group('checkpoints').open, false);
  assert.equal(second.group('day:2026-10-06').open, false);
});

test('fold state is isolated by project root and late detached toggle cannot overwrite the new project', () => {
  const h = harness(); h.render();
  const old = h.group('checkpoints'); old.open = false;
  h.context.S = { project: { root: 'project-B', name: 'B' } }; h.context.SV = data('B'); h.render();
  assert.equal(h.group('checkpoints').open, true);
  old.dispatch('toggle');
  assert.equal(h.storage.get('save-folds:project-A').includes('"checkpoints":false'), true);
  assert.equal(h.state().open.checkpoints, undefined);
  h.group('branches').open = true;
  h.context.S = { project: { root: 'project-A', name: 'A' } }; h.context.SV = data(); h.render();
  assert.equal(h.group('checkpoints').open, false);
  assert.equal(h.group('branches').open, false);
});

test('choosing a new checkpoint opens only its actual ancestors, preserving unrelated dates and branches', () => {
  const h = harness(); h.render();
  h.group('checkpoints').open = false; h.group('day:2026-10-06').open = false;
  h.context.SVSEL = 'A1'; h.render();
  assert.equal(h.group('checkpoints').open, true);
  assert.equal(h.group('day:2026-10-05').open, true);
  assert.equal(h.group('day:2026-10-06').open, false);
  assert.equal(h.group('branches').open, false);
  assert.equal(h.row('A1').getAttribute('aria-current'), 'page');
});

test('legacy runs selection stays readable and selected but disappears again after leaving', async () => {
  const h = harness({ selection: 'runs' }); await h.context.showSaves();
  assert.equal(h.group('branches').open, true);
  assert.equal(h.row('runs').getAttribute('aria-current'), 'page');
  assert.ok(h.row('runs').textContent.includes('Runs & windows'));
  assert.ok(h.calls.some(call => call[0] === 'page' && call[1] === 'runs'));
  h.context.SVSEL = 'tree'; await h.context.showSaves();
  assert.equal(h.row('runs'), undefined);
});

test('original page dispatch supports tree, branches, demos, merges, new, now and checkpoint details', async () => {
  const h = harness();
  const cases = [
    ['tree', ['tree', false]], ['branches', ['page', 'branches']], ['demos', ['page', 'demos']],
    ['merges', ['page', 'merges']], ['new', ['new']], ['现在', ['now']], ['A1', ['detail', 'A1']]
  ];
  for (const [selection, expected] of cases) {
    h.context.SVSEL = selection; h.calls.length = 0; await h.context.showSaves();
    assert.ok(h.calls.some(call => JSON.stringify(call) === JSON.stringify(expected)), selection + ' retained');
  }
});

test('unsafe user names and codes remain escaped text, never executable elements or attributes', () => {
  const item = { code: 'C<&"', name: '<img src=x onerror=alert(1)> & "name"', at: '2026-10-06 10:00', grade: '绿档' };
  const h = harness({ data: { total: 1, keep: 10, saves: [item] } }); h.render();
  assert.equal(h.toc.querySelectorAll('img').length, 0);
  const row = h.row(item.code); assert.ok(row);
  assert.equal(row.querySelector('.nm').getAttribute('title'), item.code + ' ' + item.name);
  assert.ok(row.textContent.includes(item.name));
  assert.equal(h.toc.querySelectorAll('[onerror]').length, 0);
});

test('Enter and Space activate real rows through the original click dispatcher without duplicate keyboard binding', async () => {
  const h = harness(); h.render(); h.render();
  assert.equal(h.toc.listeners.get('keydown').length, 1);
  for (const key of ['Enter', ' ']) {
    const row = h.row('A1'), event = row.dispatch('keydown', { key });
    assert.equal(event.defaultPrevented, true);
    assert.equal(row.clicks, 1);
    await flush(); assert.equal(h.context.SVSEL, 'A1');
    assert.ok(h.calls.some(call => call[0] === 'detail' && call[1] === 'A1'));
  }
});

test('summary keydown retains native details behavior and unrelated keys do not activate rows', () => {
  const h = harness(); h.render();
  const summary = h.group('branches').querySelector('summary');
  assert.equal(summary.dispatch('keydown', { key: 'Enter' }).defaultPrevented, false);
  assert.equal(summary.dispatch('keydown', { key: ' ' }).defaultPrevented, false);
  const row = h.row('A1'); row.dispatch('keydown', { key: 'ArrowDown' });
  assert.equal(row.clicks, 0);
});

test('refresh preserves keyboard focus at the previous row or fold summary without scrolling', () => {
  const h = harness(); h.render(); h.row('A1').focus(); h.render();
  assert.equal(h.context.document.activeElement, h.row('A1'));
  assert.equal(h.row('A1').lastFocusOptions.preventScroll, true);
  h.group('branches').querySelector('summary').focus(); h.render();
  assert.equal(h.context.document.activeElement, h.group('branches').querySelector('summary'));
});

test('empty saves retain now, new snapshot and an honest empty state without phantom checkpoint rows', async () => {
  const h = harness({ data: { total: 0, keep: 10, saves: [], dropped: [] } }); await h.context.showSaves();
  assert.ok(h.row('现在')); assert.ok(h.row('new'));
  assert.equal(h.toc.querySelectorAll('details[data-save-group]').length, 2);
  assert.ok(h.toc.textContent.includes('No snapshots yet'));
  assert.equal(h.group('checkpoints').querySelector('.save-toc-count').textContent, '0');
});

test('English mode changes system labels while preserving user checkpoint names and IDs', () => {
  const h = harness({ lang: 'en' }); h.render();
  assert.equal(h.row('tree').textContent, 'Overview');
  assert.equal(h.group('checkpoints').querySelector('.save-toc-name').textContent, 'Checkpoints');
  assert.ok(h.row('A2').textContent.includes('Latest'));
  assert.ok(h.row('A2').textContent.includes('A2'));
});

test('malformed browser storage falls back safely instead of breaking the directory', () => {
  for (const invalid of ['{broken', 'null', '[]', '"oops"']) {
    const h = harness({ storage: new Map([['save-folds:project-A', invalid]]) });
    assert.doesNotThrow(() => h.render()); assert.equal(h.group('checkpoints').open, true);
  }
});

test('a slow old-project response is rejected even with unchanged view, selection and request ticket', async () => {
  const h = harness(); h.render();
  const pending = deferred(); h.context.api = () => pending.promise;
  const request = h.context.showSaves();
  h.context.S = { project: { root: 'project-B', name: 'B' } }; h.context.SV = data('B'); h.render();
  const before = h.toc.innerHTML, callsBefore = h.calls.length;
  pending.resolve(data('OLD')); await request;
  assert.equal(h.context.SV.saves[0].code, 'B2');
  assert.equal(h.toc.innerHTML, before);
  assert.equal(h.calls.length, callsBefore);
});

test('an older same-project request cannot overwrite a later completed request', async () => {
  const h = harness(), first = deferred(), second = deferred();
  let requests = 0; h.context.api = () => ++requests === 1 ? first.promise : second.promise;
  const old = h.context.showSaves(), current = h.context.showSaves();
  second.resolve(data('NEW')); await current;
  first.resolve(data('OLD')); await old;
  assert.equal(h.context.SV.saves[0].code, 'NEW2');
  assert.ok(h.row('NEW2')); assert.equal(h.row('OLD2'), undefined);
});
