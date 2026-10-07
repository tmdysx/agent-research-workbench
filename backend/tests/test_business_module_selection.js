'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const html = fs.readFileSync(path.resolve(__dirname, '../../模板.html'), 'utf8');
const begin = html.indexOf('const BI ='), end = html.indexOf('async function showSettings()', begin);
assert.ok(begin >= 0 && end > begin);
const source = html.slice(begin, end);
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const data = () => ({files: 10, bytes: 300, default_parent: 'C:/TEMP', fixed_modules: ['想法','蓝图','戒律','源代码','测试','文献','论文'],
  business_options: [{name:'PPT',selected:true},{name:'剪辑',selected:false},{name:'写小说',selected:false}]});
function fixture() {
  const listeners = {}, nodes = new Map(), calls = [];
  function element() { return {innerHTML:'', textContent:'', value:'', open:false, disabled:false,
    addEventListener(){}, querySelector(){return null;}, querySelectorAll(){return [];}, contains(){return false;}, focus(){},
    setAttribute(){}, showModal(){this.open=true;}, close(){this.open=false;}}; }
  for (const key of ['#setBuiltin','#setview','#biStatus','#biExtraSummary','#biResult','#biName','#biWhere','#biSelected','#biDialogStats','#biDialogStatus','#biDialogTree']) nodes.set(key,element());
  const c = {Set,Map,console,esc,fmtSize:n=>String(n),readingFlames:()=>'<span>Loading</span>',completeReading:async()=>{},
    getLang:()=>'zh',moduleReadRoot:()=>'C:/fixture',location:{hash:'#/settings'},view:'settings',renderBuiltinMarks:()=>{},   // 10-07 页面后来用到的小函数
    $:sel=>nodes.get(sel)||null, document:{activeElement:null,body:{appendChild:d=>nodes.set('#biDialog',d)},
      createElement:element,addEventListener:(kind,fn)=>(listeners[kind]??=[]).push(fn)},
    api:async(method,url,body)=>{calls.push({method,url,body});if(url==='api/settings/builtin')return data();if(url.endsWith('/preview'))return {files:4,bytes:30,extra_files:0,extra_bytes:0};if(url.includes('/browse'))return {items:[]};return {target:'C:/TEMP/new',file_count:4,bytes:30};}};
  vm.createContext(c); vm.runInContext(source + '\nglobalThis.BI = BI;',c);
  return {c,nodes,listeners,calls};
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('initial defaults retain PPT while unrelated business modules remain unselected', async () => {
  const f=fixture(); await f.c.loadBuiltin();
  assert.deepEqual(Array.from(f.c.BI.business),['PPT']);
  assert.match(f.nodes.get('#setBuiltin').innerHTML,/业务模块可勾选/);
  f.c.BI.business.add('剪辑'); await f.c.loadBuiltin(true);
  assert.deepEqual(Array.from(f.c.BI.business),['PPT','剪辑']);
});

test('module checkbox reuses the tree and never generates whole-module extra paths', () => {
  const f=fixture(), b=f.c.BI; b.business=new Set(['PPT']);
  b.dirs.set('资料',{items:[{name:'文献',path:'资料/文献',kind:'folder',required:true},
    {name:'PPT',path:'资料/PPT',kind:'folder',required:false,business_module:'PPT'},
    {name:'剪辑',path:'资料/剪辑',kind:'folder',required:false,business_module:'剪辑'}]});
  const rendered=f.c.builtinTreeRows('资料');
  assert.match(rendered,/data-bi-module="PPT" checked/);
  assert.match(rendered,/data-bi-module="剪辑"/);
  assert.doesNotMatch(rendered,/data-bi-select="资料\/(PPT|剪辑)"/);
  assert.doesNotMatch(rendered,/资料\/文献/);
  assert.match(rendered,/Templates only/);
});

test('changing a business checkbox previews the independent module list and keeps extras empty', async () => {
  const f=fixture(), b=f.c.BI; b.data=data();b.business=new Set(['PPT']);b.modal=true;
  const target={dataset:{biModule:'剪辑'},checked:true,hasAttribute:k=>k==='data-bi-module'};
  f.listeners.change[0]({target});await settle();
  assert.deepEqual(Array.from(b.business),['PPT','剪辑']);assert.equal(b.extra.size,0);
  const request=f.calls.find(r=>r.url.endsWith('/preview'));
  assert.deepEqual(Array.from(request.body.business_modules),['PPT','剪辑']);
  assert.deepEqual(Array.from(request.body.extra),[]);
});

test('cancel restores both selections and late preview cannot overwrite the next dialog', async () => {
  const f=fixture(),b=f.c.BI;b.data=data();b.business=new Set(['PPT']);b.extra=new Set(['笔记/明确选择.md']);
  let resolve;f.c.api=(method,url)=>{f.calls.push({method,url});if(url.endsWith('/preview'))return new Promise(r=>resolve=r);return Promise.resolve({items:[]});};
  f.c.openBuiltinDialog();assert.match(f.nodes.get('#biDialog').innerHTML,/想法 · 蓝图 · 戒律 · 源代码 · 测试 · 文献 · 论文/);
  b.business.add('剪辑');b.extra.clear();f.c.closeBuiltinDialog(false);
  assert.deepEqual(Array.from(b.business),['PPT']);assert.deepEqual(Array.from(b.extra),['笔记/明确选择.md']);
  resolve({files:999,bytes:999});await settle();assert.equal(b.stats,null);
});

test('latest preview wins when business choices change during calculation', async () => {
  const f=fixture(),b=f.c.BI;b.data=data();b.business=new Set(['PPT']);b.modal=true;
  const pending=[];f.c.api=()=>new Promise(r=>pending.push(r));
  const first=f.c.builtinPreview();b.business.add('剪辑');++b.selection;
  const second=f.c.builtinPreview();pending[1]({files:12,bytes:12});await second;
  pending[0]({files:99,bytes:99});await first;
  assert.equal(b.stats.files,12);assert.equal(b.statsSelection,1);assert.equal(b.previewing,false);
});

test('create sends an explicit empty list and performs no installation, launch or publication', async () => {
  const f=fixture(),b=f.c.BI;b.data=data();b.business=new Set();b.name='new';
  const button={dataset:{bi:'new'}};
  await f.listeners.click[0]({target:{closest:sel=>sel==='[data-bi]'?button:null}});
  const create=f.calls.find(r=>r.url==='api/settings/new-project');
  assert.ok(create);assert.deepEqual(Array.from(create.body.business_modules),[]);
  assert.deepEqual(Array.from(create.body.extra),[]);
  assert.equal(f.calls.length,1);assert.equal(b.creating,false);
  assert.deepEqual(Array.from(b.business),['PPT']);
});
