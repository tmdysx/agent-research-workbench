'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../代码地图.js'), 'utf8');

class Events {
  constructor() { this.events = new Map(); }
  addEventListener(type, fn) { if (!this.events.has(type)) this.events.set(type, new Set()); this.events.get(type).add(fn); }
  removeEventListener(type, fn) { this.events.get(type)?.delete(fn); }
  emit(type, e = {}) { for (const fn of [...(this.events.get(type) || [])]) fn(e); }
  count() { return [...this.events.values()].reduce((n, s) => n + s.size, 0); }
}
class Element extends Events {
  constructor(name) {
    super(); this.name = name; this.tagName = name.toUpperCase(); this.style = {}; this.dataset = {}; this.hidden = false;
    this.children = [];this.parentNode = null;
    this.clientWidth = 1000; this.clientHeight = 600; this.innerHTML = ''; this.textContent = ''; this.value = '';
    const classes = new Set(); this.classList = { add: x => classes.add(x), remove: x => classes.delete(x),
      contains: x => classes.has(x), toggle: (x, on) => { if (on ?? !classes.has(x)) classes.add(x); else classes.delete(x); } };
  }
  getBoundingClientRect() { return { top: 60, left: 0, width: 1000, height: 600 }; }
  closest(s) { return s === 'button' && this.tagName === 'BUTTON' || s === '[data-cmx-drag]' && this.dataset.cmxDrag != null || s === '[data-cmx-size]' && this.dataset.cmxSize != null ? this : null; }
  matches(s) { return s === '[data-cmx-drag]' && this.dataset.cmxDrag != null || s === '[data-cmx-size]' && this.dataset.cmxSize != null; }
  contains(node) { for (let n = node; n; n = n.parentNode) if (n === this) return true;return false; }
  get nextSibling() { if (!this.parentNode) return null;return this.parentNode.children[this.parentNode.children.indexOf(this) + 1] || null; }
  focus() {}
  appendChild(child) { if (child.parentNode) child.parentNode.children.splice(child.parentNode.children.indexOf(child), 1);child.parentNode = this;this.children.push(child);return child; }
  insertBefore(child, next) { this.appendChild(child);this.children.pop();this.children.splice(this.children.indexOf(next), 0, child);return child; }
  getContext() { return new Proxy({}, { get: (obj, key) => obj[key] || (() => {}) }); }
}
function environment(initial = 'map', files = []) {
  const window = new Events(), document = new Events(), styles = new Map(), frames = new Map(), intervals = new Map();
  let id = 0, attached = true;
  const host = new Element('section'), selectors = ['.cmx-stage', '.cmx-world', 'canvas', '.cmx-side', '.cmx-tip',
    '.cmx-legend', '.cmx-stat', '.cmx-load', 'input[type=search]', '.cmx-3d', '.cmx-tiers', '[data-act=tilt]', '[data-act=full]', '[data-cmx-color]', '.cmx-bar'];
  const nodes = Object.fromEntries(selectors.map(s => [s, new Element(s === 'canvas' ? 'canvas' : 'div')]));
  host.querySelector = s => nodes[s] || null;
  const views = ['flat', 'flow', 'pyr', 'fold', 'heat'].map(v => { const e = new Element('button');e.dataset.view = v;return e; });
  host.querySelectorAll = s => s === '[data-view]' ? views : [];
  host.appendChild(nodes['.cmx-bar']);host.appendChild(nodes['.cmx-stage']);nodes['.cmx-stage'].appendChild(nodes['.cmx-world']);nodes['.cmx-world'].appendChild(nodes.canvas);nodes['.cmx-stage'].appendChild(nodes['.cmx-side']);nodes['.cmx-side'].hidden = true;
  nodes['.cmx-side'].getBoundingClientRect = () => ({ top: 80, left: 680, width: 304, height: 500 });
  document.documentElement = new Element('html'); document.baseURI = 'http://127.0.0.1/'; document.fullscreenElement = null;
  document.getElementById = name => styles.get(name) || null;
  document.createElement = name => new Element(name);
  document.head = { appendChild: e => styles.set(e.id, e) };document.body = new Element('body');document.body.appendChild(host);const bodyContains = document.body.contains.bind(document.body);document.body.contains = n => attached && bodyContains(n);
  document.exitCalls = 0;
  document.exitFullscreen = async () => { document.exitCalls++;document.fullscreenElement = null;document.emit('fullscreenchange'); };
  window.devicePixelRatio = 1;window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  window.innerWidth = 1024;window.innerHeight = 768;window.moduleModes = { '普通模块': initial, '源代码': initial };window.getterKeys = [];
  window.researchOverviewMode = key => { window.getterKeys.push(key);return window.moduleModes[key] || 'map'; };
  const sandbox = { window, document, innerHeight: 900, performance: { now: () => 1000 },
    getComputedStyle: () => ({ getPropertyValue: key => key === '--card' ? '#faf9f5' : key === '--fg' ? '#141413' : '#777777' }),
    localStorage: { getItem: () => 'pyr', setItem() {} }, URL,
    requestAnimationFrame: fn => { const n = ++id; frames.set(n, fn);return n; }, cancelAnimationFrame: n => frames.delete(n),
    setTimeout: () => ++id, clearTimeout() {}, setInterval: fn => { const n = ++id;intervals.set(n, fn);return n; }, clearInterval: n => intervals.delete(n),
    MutationObserver: class { observe() {} disconnect() {} }, matchMedia: window.matchMedia };
  vm.runInNewContext(source, sandbox, { filename: '代码地图.js' });
  const map = window.CodeMap;
  const control = (extra = {}) => map.mount(host, { module: '普通模块', api: async (_, url) => url.includes('/codemap/files') ? { files, git: false } : { defs: [] }, ...extra });
  return { map, host, window, document, nodes, styles, frames, intervals, control, detach: () => { attached = false; },
    setMode: mode => { window.moduleModes['普通模块'] = mode;window.emit('research-overview-mode', { detail: { mode } }); },
    click: action => { const b = new Element('button');b.dataset.act = action;nodes['.cmx-bar'].emit('click', { target: b }); } };
}
const settle = () => new Promise(resolve => setImmediate(resolve));
const rows = () => [
  { rel: 'a.py', name: 'a.py', dir: '', lines: 10, mtime: 1, lang: 'py', users: [], fan_in: 0 },
  { rel: 'b.py', name: 'b.py', dir: '', lines: 12, mtime: 1, lang: 'py', users: ['a.py'], fan_in: 1 },
  { rel: 'c.py', name: 'c.py', dir: '', lines: 4, mtime: 1, lang: 'py', users: ['b.py'], fan_in: 1 }
];

test('global mode maps to existing flat/Three pyramid and the dependency view', () => {
  const { map } = environment();
  assert.equal(map._overviewView('map'), 'flat');assert.equal(map._overviewView('flow'), 'flow');assert.equal(map._overviewView('model3d'), 'pyr');
  assert.equal(map._overviewView('__proto__'), 'flat');
});
test('dependency edges use recorded users in the correct direction without mutating rows', () => {
  const { map } = environment(), files = rows(), before = JSON.stringify(files), flow = map._flow(files);
  assert.equal(JSON.stringify(files), before);
  assert.deepEqual(JSON.parse(JSON.stringify(flow.edges)), [{ from: 'a.py', to: 'b.py' }, { from: 'b.py', to: 'c.py' }]);
  assert.ok(flow.byRel.get('a.py').x < flow.byRel.get('b.py').x);assert.ok(flow.byRel.get('b.py').x < flow.byRel.get('c.py').x);
});
test('cycles and self references retain only known edges and a finite layout', () => {
  const { map } = environment(), files = rows();files[0].users = ['c.py', 'a.py'];
  const flow = map._flow(files);assert.equal(flow.edges.length, 4);assert.equal(flow.files.length, 3);
  assert.ok(flow.files.every(n => [n.x, n.y, n.w, n.h].every(Number.isFinite)));assert.ok(Number.isFinite(flow.W));
});
test('unknown users, absent referenced files and truncated records are not filled by guesses', () => {
  const { map } = environment(), files = rows();files[0].users = ['outside.py', 'outside.py'];delete files[2].users;files[1].fan_in = 20;
  const flow = map._flow(files);assert.equal(flow.edges.length, 1);assert.equal(flow.unknown, 1);assert.equal(flow.truncated, 1);
});
test('empty code projects have finite map and flow extents', () => {
  const { map } = environment();for (const layout of [map._build([]), map._flow([])]) {
    assert.ok(Number.isFinite(layout.W) && Number.isFinite(layout.H));assert.equal(layout.files.length, 0);
  }
});
test('initial global map overrides old local pyramid preference; mode events retain camera and selection', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();
  assert.equal(ctl.stats().view, 'flat');f.click('zoom-in');ctl._pick('a.py', 0);await settle();
  const before = JSON.stringify(ctl.stats().camera), canvas = f.nodes.canvas;
  f.setMode('flow');
  assert.equal(ctl.stats().view, 'flow');assert.equal(ctl.stats().selected, 'a.py');assert.equal(ctl.stats().dependencies, 2);
  f.click('zoom-in');const flowCamera = JSON.stringify(ctl.stats().camera);
  f.setMode('map');assert.equal(JSON.stringify(ctl.stats().camera), before);
  f.setMode('flow');assert.equal(JSON.stringify(ctl.stats().camera), flowCamera);
  f.window.emit('research-overview-mode', { detail: { mode: 'bad' } });assert.equal(ctl.stats().view, 'flow');assert.equal(f.nodes.canvas, canvas);
  ctl.destroy();assert.equal(f.window.count(), 0);assert.equal(f.intervals.size, 0);
});
test('explicit plus/minus zoom both 2D modes without resetting center', async () => {
  for (const mode of ['map', 'flow']) {
    const f = environment(mode, rows()), ctl = f.control();await settle();const before = ctl.stats().camera;
    f.click('zoom-in');const zoomed = ctl.stats().camera;assert.ok(zoomed.z > before.z);assert.equal(zoomed.x, before.x);assert.equal(zoomed.y, before.y);
    f.click('zoom-out');assert.ok(Math.abs(ctl.stats().camera.z - before.z) < 1e-10);ctl.destroy();
  }
});
test('native fullscreen retains selection and camera, Escape exits without losing them', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();ctl._pick('a.py', 0);const before = JSON.stringify(ctl.stats().camera);
  f.host.requestFullscreen = async () => { f.document.fullscreenElement = f.host;f.document.emit('fullscreenchange'); };
  f.click('full');await settle();assert.equal(f.document.fullscreenElement, f.host);assert.equal(f.host.classList.contains('cmx-fs'), false);
  f.window.emit('keydown', { key: 'Escape', target: f.host });await settle();assert.equal(f.document.fullscreenElement, null);
  assert.equal(ctl.stats().selected, 'a.py');assert.equal(JSON.stringify(ctl.stats().camera), before);ctl.destroy();
});
test('rejected and missing fullscreen APIs use fixed overlay; explicit exit and global Escape clean it', async () => {
  for (const rejection of [false, true]) {
    const f = environment('flow', rows()), ctl = f.control();await settle();
    if (rejection) f.host.requestFullscreen = () => Promise.reject(new Error('Denied'));
    f.click('full');await settle();assert.equal(f.host.classList.contains('cmx-fs'), true);
    if (rejection) f.click('full');else f.window.emit('keydown', { key: 'Escape' });
    assert.equal(f.host.classList.contains('cmx-fs'), false);ctl.destroy();assert.equal(f.document.count(), 0);
  }
});
test('pending fullscreen cannot reopen a detached/disposed code map', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();let resolve;
  f.host.requestFullscreen = () => new Promise(done => { resolve = done; });f.click('full');f.detach();assert.equal(ctl.alive(), false);
  f.document.fullscreenElement = f.host;resolve();await settle();assert.equal(f.document.fullscreenElement, null);assert.equal(f.host.classList.contains('cmx-fs'), false);
  assert.equal(f.window.count(), 0);assert.equal(f.document.count(), 0);assert.equal(f.intervals.size, 0);
});
test('model3d mode uses the existing Three branch and returning to map retains selection', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();ctl._pick('a.py', 0);const before = JSON.stringify(ctl.stats().camera);
  f.setMode('model3d');await settle();assert.equal(ctl.stats().view, 'pyr');
  assert.equal(f.nodes['.cmx-world'].hidden, true);assert.equal(f.nodes['.cmx-3d'].hidden, false);
  // This Node VM has no WebGL/import callback; failed Three is an explicit unavailable state, never a fake model.
  assert.match(f.nodes['.cmx-3d'].innerHTML, /3D 用不了/);
  f.setMode('map');assert.equal(ctl.stats().selected, 'a.py');
  assert.equal(JSON.stringify(ctl.stats().camera), before);ctl.destroy();
});

test('late Three failure cannot overwrite the 2D or disposed holder', async () => {
  for (const leave of ['map', 'dispose']) {
    const f = environment('map', rows()), ctl = f.control();await settle();
    f.nodes['.cmx-3d'].innerHTML = 'Unchanged holder';
    f.setMode('model3d');
    if (leave === 'map') f.setMode('map');else ctl.destroy();
    await settle();assert.equal(f.nodes['.cmx-3d'].innerHTML, 'Unchanged holder');
    if (leave === 'map') ctl.destroy();
  }
});

test('module getter owns the view, other-module event payloads cannot replace it; toolbar stays a single row', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();assert.equal(f.window.getterKeys[0], '普通模块');
  assert.doesNotMatch(f.host.innerHTML, /data-view=/);assert.match(f.host.innerHTML, /data-act="notes"/);assert.match(f.styles.get('cmxCss').textContent, /flex-wrap:nowrap/);
  f.window.emit('research-overview-mode', { detail: { module: 'other', mode: 'model3d' } });assert.equal(ctl.stats().view, 'flat');
  f.window.moduleModes['普通模块'] = 'flow';f.window.emit('research-overview-mode', { detail: { mode: 'map' } });assert.equal(ctl.stats().view, 'flow');ctl.destroy();
  const fallback = environment('flow', rows()), empty = fallback.control({ module: '' });await settle();assert.equal(fallback.window.getterKeys[0], '源代码');empty.destroy();
});

test('notes helper is explicit and called once; native/fallback notes preserve text and return safely', async () => {
  for (const native of [true, false]) {
    const f = environment('map', rows()), note = new Element('note'), textarea = new Element('textarea');let calls = 0;
    note.style.zIndex = '40';textarea.value = 'Hand-written original — 不改';note.appendChild(textarea);f.document.body.appendChild(note);f.styles.set('note', note);
    const ctl = f.control({ notes: () => { calls++;return note; } });await settle();assert.equal(calls, 0);
    if (native) f.host.requestFullscreen = async () => { f.document.fullscreenElement = f.host;f.document.emit('fullscreenchange'); };
    f.click('full');await settle();assert.equal(calls, 0);f.click('notes');assert.equal(calls, 1);assert.equal(textarea.value, 'Hand-written original — 不改');assert.equal(note.style.zIndex, '10001');
    assert.equal(note.parentNode, native ? f.host : f.document.body);
    f.click('full');await settle();assert.equal(note.parentNode, f.document.body);assert.equal(note.style.zIndex, '40');assert.equal(textarea.value, 'Hand-written original — 不改');ctl.destroy();
  }
});

test('fullscreen details use only a dedicated handle, clamp to viewport, and restore DOM/style on exit', async () => {
  const f = environment('map', rows()), ctl = f.control();await settle();ctl._pick('a.py', 0);await settle();
  const pane = f.nodes['.cmx-side'], oldParent = pane.parentNode;pane.style.left = 'Original left';
  f.click('full');await settle();assert.equal(pane.parentNode, f.host);assert.equal(pane.classList.contains('cmx-pane-floating'), true);
  const handle = new Element('div');handle.dataset.cmxDrag = '';pane.appendChild(handle);
  let prevented = 0;pane.emit('pointerdown', { button: 0, target: new Element('textarea'), clientX: 0, clientY: 0, preventDefault: () => prevented++, stopPropagation() {} });
  f.window.emit('pointermove', { clientX: -9999, clientY: -9999 });assert.equal(prevented, 0);assert.notEqual(pane.style.left, '8px');
  pane.emit('pointerdown', { button: 0, target: handle, clientX: 0, clientY: 0, preventDefault: () => prevented++, stopPropagation() {} });f.window.emit('pointermove', { clientX: -9999, clientY: -9999 });
  assert.equal(prevented, 1);assert.equal(pane.style.left, '8px');assert.equal(pane.style.top, '8px');
  f.window.emit('pointerup');f.window.innerWidth = 220;f.window.innerHeight = 160;f.window.emit('resize');assert.equal(parseFloat(pane.style.width), 204);assert.equal(parseFloat(pane.style.height), 144);
  pane.emit('keydown', { target: handle, key: 'ArrowRight', preventDefault() {} });assert.equal(pane.style.left, '8px');
  f.window.emit('keydown', { key: 'Escape' });assert.equal(pane.parentNode, oldParent);assert.equal(pane.style.left, 'Original left');assert.equal(pane.classList.contains('cmx-pane-floating'), false);assert.equal(ctl.stats().selected, 'a.py');
  f.click('full');await settle();ctl.destroy();assert.equal(pane.parentNode, oldParent);assert.equal(f.window.count(), 0);
});

test('pane clamp is finite and retains all of the pane even in a small viewport', () => {
  const { map } = environment();for (const viewport of [{ width: 1024, height: 768 }, { width: 1, height: 1 }]) {
    const b = map._clampPane({ x: -Infinity, y: Infinity, width: 5000, height: 7000 }, viewport);
    assert.ok(Object.values(b).every(Number.isFinite));assert.ok(b.x >= 0 && b.y >= 0);assert.ok(b.x + b.width <= viewport.width && b.y + b.height <= viewport.height);
  }
});

function readingGrip(f) { const grip=new Element('button');grip.dataset.cmxSize='';f.nodes['.cmx-side'].appendChild(grip);return grip; }

test('normal code reading panes resize in both 2D views without modifying data or the camera',async()=>{
  for(const mode of ['map','flow']){
    const data=rows(),f=environment(mode,data),ctl=f.control();await settle();ctl._pick('a.py',0);await settle();
    const original=JSON.stringify(data),pane=f.nodes['.cmx-side'],grip=readingGrip(f),camera=JSON.stringify(ctl.stats().camera);
    pane.emit('pointerdown',{button:0,pointerId:70,target:grip,clientX:0,clientY:0,preventDefault(){},stopPropagation(){}});
    f.window.emit('pointermove',{pointerId:70,clientX:100,clientY:80});f.window.emit('pointerup',{pointerId:70});
    assert.equal(pane.style.width,'404px');assert.equal(pane.style.height,'580px');assert.equal(JSON.stringify(ctl.stats().camera),camera);assert.equal(JSON.stringify(data),original);assert.equal(ctl.stats().selected,'a.py');ctl.destroy();
  }
});

test('reading size survives code selection, source refresh and overview switching',async()=>{
  const f=environment('map',rows()),ctl=f.control();await settle();ctl._pick('a.py',0);await settle();const pane=f.nodes['.cmx-side'],grip=readingGrip(f);
  pane.emit('keydown',{target:grip,key:'ArrowRight',shiftKey:true,preventDefault(){}});pane.emit('keydown',{target:grip,key:'ArrowDown',preventDefault(){}});
  const size=JSON.stringify(ctl.stats().paneSize),width=pane.style.width,height=pane.style.height;ctl._pick('b.py',0);await settle();await ctl.refresh();await settle();
  assert.equal(ctl.stats().selected,'b.py');assert.equal(JSON.stringify(ctl.stats().paneSize),size);assert.equal(pane.style.width,width);assert.equal(pane.style.height,height);
  f.setMode('flow');assert.equal(pane.style.width,width);assert.equal(pane.style.height,height);assert.match(pane.innerHTML,/data-cmx-size/);ctl.destroy();
});

test('fullscreen code corner updates internal box and restores the same reader with its new size',async()=>{
  const f=environment('map',rows()),ctl=f.control();await settle();ctl._pick('a.py',0);await settle();const pane=f.nodes['.cmx-side'],oldParent=pane.parentNode;
  f.click('full');await settle();const grip=readingGrip(f),before=ctl.stats().paneBox;
  pane.emit('pointerdown',{button:0,pointerId:71,target:grip,clientX:0,clientY:0,preventDefault(){},stopPropagation(){}});f.window.emit('pointermove',{pointerId:71,clientX:120,clientY:-130});f.window.emit('pointerup',{pointerId:71});
  assert.equal(ctl.stats().paneBox.width,before.width+120);assert.equal(ctl.stats().paneBox.height,before.height-130);assert.equal(parseFloat(pane.style.width),ctl.stats().paneBox.width);
  const chosen=JSON.stringify(ctl.stats().paneSize);f.click('full');await settle();assert.equal(pane.parentNode,oldParent);assert.equal(ctl.stats().paneBox,null);assert.equal(JSON.stringify(ctl.stats().paneSize),chosen);assert.equal(pane.style.width,'424px');assert.equal(pane.style.height,'370px');assert.equal(ctl.stats().selected,'a.py');ctl.destroy();
});

test('resize uses only its corner, respects active pointer and has bounded keyboard shrinking',async()=>{
  const f=environment('map',rows()),ctl=f.control();await settle();ctl._pick('a.py',0);await settle();const pane=f.nodes['.cmx-side'],grip=readingGrip(f);
  pane.emit('pointerdown',{button:0,pointerId:72,target:grip,clientX:0,clientY:0,preventDefault(){},stopPropagation(){}});f.window.emit('pointermove',{pointerId:73,clientX:500,clientY:500});assert.equal(pane.style.width,undefined);
  f.window.emit('pointermove',{pointerId:72,clientX:-3000,clientY:-3000});f.window.emit('pointerup',{pointerId:72});assert.equal(pane.style.width,'180px');assert.equal(pane.style.height,'120px');
  pane.emit('keydown',{target:grip,key:'ArrowLeft',preventDefault(){}});pane.emit('keydown',{target:grip,key:'ArrowUp',preventDefault(){}});assert.equal(pane.style.width,'180px');assert.equal(pane.style.height,'120px');
  pane.emit('pointerdown',{button:0,target:new Element('textarea'),clientX:0,clientY:0,preventDefault(){},stopPropagation(){}});f.window.emit('pointermove',{clientX:900,clientY:900});assert.equal(pane.style.width,'180px');ctl.destroy();assert.equal(f.window.count(),0);
});

test('small normal and fullscreen viewports clamp the entire requested reader without losing its preference',async()=>{
  const f=environment('map',rows()),ctl=f.control();await settle();ctl._pick('a.py',0);await settle();const pane=f.nodes['.cmx-side'],grip=readingGrip(f);
  pane.emit('pointerdown',{button:0,pointerId:74,target:grip,clientX:0,clientY:0,preventDefault(){},stopPropagation(){}});f.window.emit('pointermove',{pointerId:74,clientX:2000,clientY:2000});f.window.emit('pointerup',{pointerId:74});
  assert.equal(ctl.stats().paneSize.width,960);assert.equal(ctl.stats().paneSize.height,1200);assert.ok(parseFloat(pane.style.height)<=584);
  f.click('full');await settle();f.window.innerWidth=220;f.window.innerHeight=160;f.window.emit('resize');assert.equal(parseFloat(pane.style.width),204);assert.equal(parseFloat(pane.style.height),144);
  assert.equal(ctl.stats().paneSize.height,1200);ctl.destroy();assert.equal(f.window.count(),0);assert.equal(f.document.count(),0);
});

test('disposed code pane resize has no listeners and another project starts with its own dimensions',async()=>{
  const a=environment('map',rows()),ctl=a.control();await settle();ctl._pick('a.py',0);await settle();const pane=a.nodes['.cmx-side'],grip=readingGrip(a);
  pane.emit('keydown',{target:grip,key:'ArrowRight',shiftKey:true,preventDefault(){}});assert.equal(ctl.stats().paneSize.width,336);ctl.destroy();const frozen=JSON.stringify(ctl.stats().paneSize);
  a.window.emit('pointermove',{clientX:500,clientY:500});assert.equal(JSON.stringify(ctl.stats().paneSize),frozen);assert.equal(a.window.count(),0);
  const b=environment('flow',rows()),other=b.control({module:'另一项目'});await settle();assert.equal(other.stats().paneSize.width,304);assert.equal(other.stats().paneSize.height,520);assert.equal(other.stats().selected,'');
  assert.match(b.styles.get('cmxCss').textContent,/\.cmx-side\[hidden\]\{display:none\}/);other.destroy();
});
