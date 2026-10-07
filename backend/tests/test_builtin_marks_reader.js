'use strict';
// Run the production reader function with controlled request completion order.
// Only DOM plumbing, rendering and the shared lock component boundary are stubbed.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.resolve(__dirname, '../../模板.html'), 'utf8');
const start = template.indexOf('async function rdRight() {');
const end = template.indexOf('function rdPop(', start);
assert.ok(start >= 0 && end > start, 'production rdRight function exists');
const source = template.slice(start, end);
const FILE_A = '资料/文献/解读/L1 示例/文本/A.md';
const FILE_B = '资料/文献/解读/L1 示例/文本/B.md';

function fixture() {
  const sub = {innerHTML: '<lock>OLD LOCK</lock>', isConnected: true};
  const body = {
    innerHTML: 'OLD BODY', isConnected: true,
    classList: {remove() {}, add() {}},
  };
  const requests = [], locks = [], follows = [];
  const ctx = {
    RD: {
      m: '文献', code: 'L1', tab: '文本', file: 'A.md',
      x: {folder: '解读/L1 示例', parts: {文本: ['A.md', 'B.md']}},
    },
    root: 'temporary-project-A', location: {hash: '#/reader/L1'}, sub, body,
    document: {querySelectorAll() { return []; }},
    moduleReadRoot: () => ctx.root,
    $: id => id === '#rdSub' ? ctx.sub : ctx.body,
    renderMd: text => text,
    esc: text => text,
    readingFlames: () => 'LOADING',
    rdFollow() { follows.push(ctx.RD.file); },
    builtinFileSlot(file, label, action) {
      locks.push({file, action});
      return '<lock path="' + file + '"></lock>';
    },
    api(method, url) {
      let resolve, reject;
      const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
      requests.push({method, url, resolve, reject});
      return promise;
    },
  };
  vm.createContext(ctx);
  vm.runInContext(source, ctx, {filename: 'production-rdRight.js'});
  return {ctx, sub, body, requests, locks, follows};
}

for (const outcome of ['success', 'error']) {
  test('late A ' + outcome + ' cannot replace visible B or attach an A lock', async () => {
    const f = fixture(), first = f.ctx.rdRight();
    assert.match(f.body.innerHTML, /LOADING/);
    assert.doesNotMatch(f.body.innerHTML, /OLD BODY/);
    assert.doesNotMatch(f.sub.innerHTML, /<lock/);
    assert.equal(f.locks.length, 0);

    f.ctx.RD.file = 'B.md';
    const second = f.ctx.rdRight();
    assert.doesNotMatch(f.sub.innerHTML, /<lock/);
    assert.equal(f.locks.length, 0);
    assert.deepEqual(f.requests.map(r => r.method), ['GET', 'GET']);
    assert.equal(decodeURIComponent(f.requests[1].url),
      'api/modules/文献/preview?path=解读/L1 示例/文本/B.md');
    const action = {path: FILE_B, state: 'unmarked', toggle_allowed: true};
    f.requests[1].resolve({text: 'CONTENT B', builtin_action: action});
    await second;
    const expectedBody = f.body.innerHTML, expectedSub = f.sub.innerHTML;

    if (outcome === 'success') f.requests[0].resolve({text: 'CONTENT A'});
    else f.requests[0].reject(Error('OLD ERROR'));
    await first;

    assert.equal(f.body.innerHTML, expectedBody);
    assert.equal(f.sub.innerHTML, expectedSub);
    assert.match(f.body.innerHTML, /CONTENT B/);
    assert.ok(f.sub.innerHTML.includes('path="' + FILE_B + '"'));
    assert.ok(!f.sub.innerHTML.includes('path="' + FILE_A + '"'));
    assert.equal(f.locks.length, 1);
    assert.equal(f.locks[0].file, FILE_B);
    assert.equal(f.locks[0].action, action);
    assert.deepEqual(f.follows, ['B.md']);
  });
}

for (const scenario of ['project', 'route', 'file', 'host', 'disconnected']) {
  test('reader ' + scenario + ' change suppresses stale text and lock', async () => {
    const f = fixture(), pending = f.ctx.rdRight(), before = f.body.innerHTML;
    if (scenario === 'project') f.ctx.root = 'temporary-project-B';
    if (scenario === 'route') f.ctx.location.hash = '#/saves';
    if (scenario === 'file') f.ctx.RD.file = 'B.md';
    if (scenario === 'host') f.ctx.body = {innerHTML: 'NEW HOST', isConnected: true};
    if (scenario === 'disconnected') f.body.isConnected = false;
    f.requests[0].resolve({text: 'STALE'});
    await pending;
    assert.equal(f.body.innerHTML, before);
    if (scenario === 'host') assert.equal(f.ctx.body.innerHTML, 'NEW HOST');
    assert.doesNotMatch(f.sub.innerHTML, /<lock/);
    assert.equal(f.locks.length, 0);
    assert.equal(f.follows.length, 0);
  });
}

test('failed current read displays the error without a file lock', async () => {
  const f = fixture(), pending = f.ctx.rdRight();
  f.requests[0].reject(Error('CURRENT ERROR'));
  await pending;
  assert.match(f.body.innerHTML, /CURRENT ERROR/);
  assert.doesNotMatch(f.sub.innerHTML, /<lock/);
  assert.equal(f.locks.length, 0);
  assert.equal(f.follows.length, 0);
});
