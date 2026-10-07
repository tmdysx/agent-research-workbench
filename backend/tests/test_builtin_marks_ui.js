'use strict';
// Execute the actual inline component. The DOM below supplies browser plumbing,
// never a second implementation of the lock state or request decisions.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const template=fs.readFileSync(path.resolve(__dirname,'../../模板.html'),'utf8').replace(/\r\n/g,'\n');
function between(start,end){const a=template.indexOf(start),b=template.indexOf(end,a);assert.ok(a>=0&&b>a,start);return template.slice(a,b);}
function fn(name){
  const match=template.match(new RegExp('(?:async )?function '+name+'\\('));assert.ok(match,name);
  const start=match.index,brace=template.indexOf('{',start);let depth=0,quote='',line=false,block=false;
  for(let i=brace;i<template.length;i++){
    const c=template[i],next=template[i+1];
    if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&next==='/'){block=false;i++;}continue;}
    if(quote){if(c==='\\'){i++;continue;}if(c===quote)quote='';continue;}
    if(c==='/'&&next==='/'){line=true;i++;continue;}if(c==='/'&&next==='*'){block=true;i++;continue;}
    if(c==='"'||c==="'"||c==='`'){quote=c;continue;}
    if(c==='{')depth++;if(c==='}'&&--depth===0)return template.slice(start,i+1);
  }
  assert.fail('unterminated production function '+name);
}
const component=[between('function esc(s) {','function uiIcon('),fn('builtinFileSlot'),fn('builtinLockIcon'),
  between('const BuiltinFiles=(function(){','window.BuiltinFiles=BuiltinFiles;'),
  'globalThis.BuiltinFiles=BuiltinFiles;'].join('\n');
const decode=s=>String(s).replace(/&quot;/g,'"').replace(/&#39;|&#x27;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
class Element{
  constructor(doc,tag='div',attrs={}){this.ownerDocument=doc;this.tagName=tag.toLowerCase();this.attrs={...attrs};this.children=[];this.parentNode=null;this.dataset={};this.html='';this.onclick=null;this.listeners=new Map();this.open=Object.hasOwn(attrs,'open');for(const[k,v]of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;}
  get isConnected(){return this.ownerDocument.body.contains(this);}get disabled(){return Object.hasOwn(this.attrs,'disabled');}
  contains(node){return node===this||this.children.some(n=>n.contains(node));}
  appendChild(node){node.remove();this.children.push(node);node.parentNode=this;return node;}
  remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(n=>n!==this);this.parentNode=null;}
  set innerHTML(html){this.html=html;for(const child of this.children)child.parentNode=null;this.children=[];const stack=[this];for(const token of html.matchAll(/<!--[\s\S]*?-->|<\/?[^>]+>|[^<]+/g)){const text=token[0];if(text.startsWith('<!--'))continue;if(text.startsWith('</')){if(stack.length>1)stack.pop();continue;}const tag=text.match(/^<([\w-]+)/);if(!tag)continue;const attrs={};for(const a of text.matchAll(/\s([\w-]+)(?:="([^"]*)"|='([^']*)')?/g))attrs[a[1]]=decode(a[2]??a[3]??'');const node=new Element(this.ownerDocument,tag[1],attrs);stack.at(-1).appendChild(node);if(!/^(input|img|br|hr|meta|link)$/i.test(tag[1])&&!text.endsWith('/>'))stack.push(node);}}
  get innerHTML(){return this.html;}
  matches(selector){if(selector==='details:not([open])')return this.tagName==='details'&&!this.open;if(selector.startsWith('#'))return this.attrs.id===selector.slice(1);const attr=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);if(attr)return Object.hasOwn(this.attrs,attr[1])&&(attr[2]===undefined||this.attrs[attr[1]]===attr[2]);return this.tagName===selector.toLowerCase();}
  closest(selector){for(let n=this;n;n=n.parentNode)if(n.matches(selector))return n;return null;}
  querySelectorAll(selector){const found=[];function walk(node){for(const n of node.children){if(n.matches(selector))found.push(n);walk(n);}}walk(this);return found;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  addEventListener(name,listener){if(!this.listeners.has(name))this.listeners.set(name,[]);this.listeners.get(name).push(listener);}
  emit(name,extra={}){for(const listener of this.listeners.get(name)||[])listener({target:this,preventDefault(){},stopPropagation(){},...extra});}
}
class Document{
  constructor(){this.body=new Element(this,'body');this.listeners=new Map();}
  querySelector(s){return this.body.querySelector(s);}querySelectorAll(s){return this.body.querySelectorAll(s);}
  addEventListener(name,listener){if(!this.listeners.has(name))this.listeners.set(name,[]);this.listeners.get(name).push(listener);}
  emit(name,extra={}){for(const listener of this.listeners.get(name)||[])listener({target:this.body,preventDefault(){},stopPropagation(){},...extra});}
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const PROJECT='c:/synthetic/project',FILE='资料/PPT/导出/示例.pdf',REV='1'.repeat(64),NEXT='2'.repeat(64);
function action(changes={}){return {project:PROJECT,path:FILE,revision:REV,state:'unmarked',enabled:false,toggle_allowed:true,owner_module:'PPT',origin:'',reason:'',...changes};}
function fixture(){
  const doc=new Document(),requests=[],messages=[],observers=[];
  const ctx={document:doc,window:null,S:{project:{root:'C:\\synthetic\\project\\'}},location:{hash:'#/m/PPT?f=example'},view:'mod',getLang:()=> 'zh',encodeURIComponent,
    toast:text=>messages.push(text),renderBuiltinMarks:()=>assert.fail('component test does not mount the management list'),
    api(method,url,data){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});requests.push({method,url,data,resolve,reject});return promise;},
    MutationObserver:class{constructor(callback){this.callback=callback;observers.push(this);}observe(node,options){this.node=node;this.options=options;}}};
  ctx.window=ctx;vm.createContext(ctx);vm.runInContext(component,ctx,{filename:'production-BuiltinFiles.js'});
  function slot(rel=FILE,label='',parent=doc.body){const wrapper=new Element(doc);wrapper.innerHTML=ctx.builtinFileSlot(rel,label);const result=wrapper.children[0];parent.appendChild(result);return result;}
  async function reply(index,value){assert.ok(requests[index],'request '+index);requests[index].resolve(value);await flush();}
  async function reject(index,error){requests[index].reject(error);await flush();}
  async function ready(changes={},rel=FILE){const s=slot(rel);ctx.BuiltinFiles.mount(s);await reply(requests.length-1,action(changes));return s;}
  return {ctx,doc,requests,messages,observers,slot,reply,reject,ready};
}
const button=s=>s.querySelector('button');
const writes=f=>f.requests.filter(r=>r.method==='PUT');

test('mount and refresh are read-only GETs and mount does not duplicate an existing holder',async()=>{
  const f=fixture(),s=f.slot();f.ctx.BuiltinFiles.mount(s);f.ctx.BuiltinFiles.mount(s);
  assert.equal(f.requests.length,1);assert.equal(f.requests[0].method,'GET');assert.equal(f.requests[0].url,'api/builtin/files?path='+encodeURIComponent(FILE));
  assert.equal(button(s).disabled,true);await f.reply(0,action());assert.equal(button(s).disabled,false);assert.equal(s.dataset.builtinState,'unmarked');
  const p=f.ctx.BuiltinFiles.refresh(s);assert.equal(f.requests.length,2);await f.reply(1,action());await p;assert.equal(writes(f).length,0);
});

test('mutation observer mounts inserted slots and a closed details waits for expansion',async()=>{
  const f=fixture(),details=new Element(f.doc,'details');f.doc.body.appendChild(details);const s=f.slot(FILE,'',details);
  assert.deepEqual({...f.observers[0].options},{childList:true,subtree:true});f.observers[0].callback([{addedNodes:[details]}]);assert.equal(f.requests.length,0);
  details.open=true;f.doc.emit('toggle',{target:details});assert.equal(f.requests.length,1);await f.reply(0,action());
  assert.equal(s.dataset.builtinState,'unmarked');assert.equal(writes(f).length,0);
});

test('PUT binds canonical server path, exact project and revision; pending calls cannot duplicate it',async()=>{
  const f=fixture(),s=await f.ready({},'资料/PPT/旧入口.pdf'),old=button(s);
  const pending=old.onclick();assert.equal(writes(f).length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(writes(f)[0].data)),{path:FILE,enabled:true,project:PROJECT,revision:REV});assert.equal(button(s).disabled,true);
  await old.onclick();await button(s).onclick();assert.equal(writes(f).length,1);
  await f.reply(1,action({state:'marked',enabled:true,revision:NEXT}));await pending;
  assert.equal(s.dataset.builtinState,'marked');assert.equal(button(s).attrs['aria-pressed'],'true');assert.equal(button(s).disabled,false);assert.equal(f.messages.length,1);
});

test('same-file peer slots cannot double-submit and reflect one confirmed result',async()=>{
  const f=fixture(),one=await f.ready(),two=await f.ready();const pending=button(one).onclick();await button(two).onclick();assert.equal(writes(f).length,1);
  await f.reply(2,action({state:'marked',enabled:true,revision:NEXT}));await pending;
  for(const s of [one,two]){assert.equal(s.dataset.builtinState,'marked');assert.equal(button(s).disabled,false);}
});

test('required and ineligible states remain disabled even when onclick is called directly',async()=>{
  for(const state of ['required','ineligible']){const f=fixture(),s=await f.ready({state,enabled:state==='required',toggle_allowed:false,reason:'protected'});
    assert.equal(button(s).disabled,true);await button(s).onclick();assert.equal(writes(f).length,0);assert.equal(s.dataset.builtinState,state);}
});

test('preview-declared ineligible source never creates a live slot or sends a GET',()=>{
  const f=fixture(),host=new Element(f.doc);f.doc.body.appendChild(host);
  host.innerHTML=f.ctx.builtinFileSlot(FILE,'',action({state:'ineligible',toggle_allowed:false,reason:'historical preview'}));
  f.ctx.BuiltinFiles.mount(host);
  assert.equal(host.querySelector('[data-builtin-path]'),null);assert.equal(button(host).disabled,true);
  assert.equal(button(host).attrs.title,'historical preview');assert.equal(f.requests.length,0);
});

test('missing marked file can send an explicit remove operation',async()=>{
  const f=fixture(),s=await f.ready({state:'missing',enabled:true,toggle_allowed:true});const pending=button(s).onclick();
  assert.equal(writes(f)[0].data.enabled,false);await f.reply(1,action({state:'missing',enabled:false,toggle_allowed:false,revision:NEXT}));await pending;
  assert.equal(button(s).disabled,true);assert.equal(button(s).attrs['aria-pressed'],'false');
});

test('superseded GET response cannot replace newer status',async()=>{
  const f=fixture(),s=f.slot();f.ctx.BuiltinFiles.mount(s);const later=f.ctx.BuiltinFiles.refresh(s);
  await f.reply(1,action({state:'marked',enabled:true,revision:NEXT}));await later;const before=s.innerHTML;
  await f.reply(0,action());assert.equal(s.innerHTML,before);assert.equal(s.dataset.builtinState,'marked');assert.equal(f.messages.length,0);
});

for(const scenario of ['project','route','disconnected','path']){
  test('old GET cannot paint after '+scenario+' changes',async()=>{
    const f=fixture(),s=f.slot();f.ctx.BuiltinFiles.mount(s);const before=s.innerHTML;
    if(scenario==='project')f.ctx.S.project.root='C:/synthetic/other';
    if(scenario==='route')f.ctx.location.hash='#/saves';
    if(scenario==='disconnected')s.remove();
    if(scenario==='path')s.dataset.builtinPath='materials/other.pdf';
    await f.reply(0,action({state:'marked',enabled:true}));assert.equal(s.innerHTML,before);assert.equal(f.messages.length,0);assert.equal(writes(f).length,0);
  });
  test('in-flight PUT cannot paint or toast after '+scenario+' changes',async()=>{
    const f=fixture(),s=await f.ready(),pending=button(s).onclick(),before=s.innerHTML;
    if(scenario==='project')f.ctx.S.project.root='C:/synthetic/other';
    if(scenario==='route')f.ctx.location.hash='#/saves';
    if(scenario==='disconnected')s.remove();
    if(scenario==='path')s.dataset.builtinPath='materials/other.pdf';
    await f.reply(1,action({state:'marked',enabled:true,revision:NEXT}));await pending;
    assert.equal(s.innerHTML,before);assert.equal(f.messages.length,0);assert.equal(writes(f).length,1);
  });
}

test('old project response does not affect a new project slot at the same file path',async()=>{
  const f=fixture(),old=await f.ready(),pending=button(old).onclick();old.remove();f.ctx.S.project.root='C:/synthetic/other';
  const current=await f.ready({project:'c:/synthetic/other',revision:'3'.repeat(64)});const before=current.innerHTML;
  await f.reply(1,action({state:'marked',enabled:true,revision:NEXT}));await pending;
  assert.equal(current.innerHTML,before);assert.equal(current.dataset.builtinState,'unmarked');assert.equal(f.messages.length,0);
});

test('409 rereads state once and never automatically resubmits the write',async()=>{
  const f=fixture(),s=await f.ready(),pending=button(s).onclick();await f.reject(1,Object.assign(Error('changed elsewhere'),{status:409}));
  assert.equal(f.requests.length,3);assert.equal(f.requests[2].method,'GET');assert.equal(writes(f).length,1);
  await f.reply(2,action({revision:NEXT}));await pending;
  assert.equal(s.dataset.builtinState,'unmarked');assert.equal(button(s).disabled,false);assert.equal(writes(f).length,1);
  assert.equal(f.messages[0],'changed elsewhere');const retry=button(s).onclick();assert.equal(writes(f)[1].data.revision,NEXT);
  await f.reply(3,action({state:'marked',enabled:true,revision:'3'.repeat(64)}));await retry;
});

test('failed conflict refresh remains read-only until the user chooses retry',async()=>{
  const f=fixture(),s=await f.ready(),pending=button(s).onclick();await f.reject(1,Object.assign(Error('conflict'),{status:409}));
  await f.reject(2,Error('offline'));await pending;
  assert.equal(s.dataset.builtinState,'error');assert.equal(writes(f).length,1);
  const retry=button(s).onclick();assert.equal(f.requests[3].method,'GET');
  await f.reply(3,action({state:'marked',enabled:true,revision:NEXT}));await retry;
  assert.equal(s.dataset.builtinState,'marked');assert.equal(writes(f).length,1);
});

test('ordinary write failure preserves the last confirmed state and permits explicit retry',async()=>{
  const f=fixture(),s=await f.ready({state:'marked',enabled:true}),pending=button(s).onclick();
  await f.reject(1,Error('synthetic write failure'));await pending;
  assert.equal(s.dataset.builtinState,'marked');assert.equal(button(s).attrs['aria-pressed'],'true');assert.equal(button(s).disabled,false);
  assert.equal(f.requests.length,2);assert.equal(f.messages[0],'synthetic write failure');
});

test('wrong project GET is rejected and its retry remains a GET',async()=>{
  const f=fixture(),s=f.slot();f.ctx.BuiltinFiles.mount(s);await f.reply(0,action({project:'c:/another/project'}));
  assert.equal(s.dataset.builtinState,'error');assert.equal(button(s).attrs['aria-pressed'],'false');
  const retry=button(s).onclick();assert.equal(f.requests[1].method,'GET');await f.reply(1,action());await retry;assert.equal(writes(f).length,0);
});

for(const wrong of ['project','path','revision','enabled'])test('unconfirmed '+wrong+' PUT result preserves previous state',async()=>{
  const f=fixture(),s=await f.ready(),pending=button(s).onclick();
  const changed={project:'c:/wrong',path:'materials/wrong.pdf',revision:'bad',enabled:false};
  await f.reply(1,action({state:'marked',enabled:true,revision:NEXT,[wrong]:changed[wrong]}));await pending;
  assert.equal(s.dataset.builtinState,'unmarked');assert.equal(button(s).attrs['aria-pressed'],'false');assert.equal(button(s).disabled,false);assert.equal(f.messages.length,1);
});

test('Escape never toggles a lock or cancels an already submitted operation',async()=>{
  const f=fixture(),s=await f.ready();f.doc.emit('keydown',{target:button(s),key:'Escape'});assert.equal(writes(f).length,0);
  const pending=button(s).onclick();f.doc.emit('keydown',{target:button(s),key:'Escape'});assert.equal(writes(f).length,1);
  await f.reply(1,action({state:'marked',enabled:true,revision:NEXT}));await pending;assert.equal(s.dataset.builtinState,'marked');
});

test('paths, labels and failure messages are escaped without creating executable elements',async()=>{
  const f=fixture(),hostile='"/><img src=x onerror="bad">',s=f.slot('materials/'+hostile,hostile);
  assert.equal(s.dataset.builtinPath,'materials/'+hostile);f.ctx.BuiltinFiles.mount(s);await f.reject(0,Error(hostile));
  assert.equal(s.querySelector('img'),null);assert.equal(s.querySelector('script'),null);assert.match(s.innerHTML,/&lt;img/);
  assert.match(button(s).attrs.title,/<img/);assert.equal(writes(f).length,0);
});
