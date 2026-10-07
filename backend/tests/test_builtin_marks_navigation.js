'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.resolve(__dirname,'../../模板.html'),'utf8').replace(/\r\n/g,'\n');
function slice(source,start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
function fn(name){const m=html.match(new RegExp('(?:async )?function '+name+'\\('));assert.ok(m,name);const brace=html.indexOf('{',m.index);let depth=0,quote='',line=false,block=false;for(let i=brace;i<html.length;i++){const c=html[i],n=html[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(quote){if(c==='\\'){i++;continue;}if(c===quote)quote='';continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){quote=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return html.slice(m.index,i+1);}assert.fail(name);}
// Share only browser plumbing with the component tests, without executing any
// test registration or substituting the production navigation/request logic.
const plumbing=fs.readFileSync(path.join(__dirname,'test_builtin_marks_ui.js'),'utf8');
const dom=slice(plumbing,'const decode=','const flush=')+'\nglobalThis.Element=Element;globalThis.Document=Document;';
const production=[slice(html,'function esc(s) {','function uiIcon('),
  slice(html,'const BI = {','function builtinStatus('),
  ...['builtinStatus','builtinResult','renderBuiltin','loadBuiltin','renderBuiltinMarks','showSaves','focusSettingsSection','showSettings'].map(fn),
  slice(html,"document.addEventListener('input', function (e) {\n  if(!e.target.closest('#setBuiltin'))", "document.addEventListener('change', function (e) {\n  const t = e.target;"),
  'globalThis.BI=BI;'].join('\n');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
  const requests=[],effects=[],mounts=[],ctx={};vm.createContext(ctx);vm.runInContext(dom,ctx);const doc=new ctx.Document();doc.activeElement=null;
  doc.getElementById=id=>doc.querySelector('#'+id);
  Object.defineProperty(ctx.Element.prototype,'id',{get(){return this.attrs.id||'';},set(v){this.attrs.id=v;}});
  Object.defineProperty(ctx.Element.prototype,'disabled',{get(){return Object.hasOwn(this.attrs,'disabled');},set(v){if(v)this.attrs.disabled='';else delete this.attrs.disabled;}});
  ctx.Element.prototype.focus=function(){doc.activeElement=this;};
  ctx.Element.prototype.scrollIntoView=function(options){effects.push(['scroll',this.id,options]);};
  Object.defineProperty(ctx.Element.prototype,'classList',{get(){return {toggle:(name,on)=>{const classes=new Set((this.attrs.class||'').split(/\s+/).filter(Boolean));on?classes.add(name):classes.delete(name);this.attrs.class=[...classes].join(' ');}};}});
  const oldMatch=ctx.Element.prototype.matches;ctx.Element.prototype.matches=function(selector){const c=selector.match(/^\.([a-z-]+)(\[.+\])$/);if(c)return (this.attrs.class||'').split(/\s+/).includes(c[1])&&oldMatch.call(this,c[2]);const m=selector.match(/^([a-z]+)(\[.+\])$/);return m?this.tagName===m[1]&&oldMatch.call(this,m[2]):oldMatch.call(this,selector);};
  function add(id,parent=doc.body){const el=new ctx.Element(doc,'div',{id});parent.appendChild(el);return el;}
  const host=add('saveview'),settings=add('setview'),toc=add('toc');
  Object.assign(ctx,{document:doc,window:ctx,$:s=>doc.querySelector(s),S:{project:{root:'C:/project',name:'Synthetic'},modules:[]},location:{hash:'#/settings'},view:'settings',SVSEL:'builtin',SVLOAD:0,SV:null,online:true,SETMODS:[],CAPSET:{},
    moduleReadRoot:()=>ctx.S.project.root,readingFlames:()=>'<span>loading</span>',completeReading:async()=>{},getLang:()=> 'zh',fmtSize:String,encodeURIComponent,
    builtinFileSlot:p=>'<span data-builtin-path="'+p+'"></span>',BuiltinFiles:{mount:node=>mounts.push(node)},
    toast:v=>effects.push(['toast',v]),setToc:(title,items)=>{effects.push(['toc',title,items]);toc.innerHTML=items.map(x=>'<a class="row" data-to="'+x.id+'"></a>').join('');},renderSaveToc:()=>effects.push(['save-toc']),wt3dStop:()=>effects.push(['stop']),
    showSaveForm:()=>effects.push(['form']),showSaveTree:()=>effects.push(['tree']),showNowNode:()=>effects.push(['now']),showSavePage:s=>effects.push(['page',s]),showSaveDetail:s=>effects.push(['detail',s]),
    api(method,url,data){if(url==='api/auto')return Promise.resolve({settings:{}});if(url==='api/capture-settings')return Promise.resolve({});let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});requests.push({method,url,data,resolve,reject});return promise;}});
  for(const name of ['mergeSetMods','renderSetMods','loadMachine','loadSkins','wallpaperSettingsReady','loadScan','loadSetAuto','loadSetSaves','loadSetTidy','saveSetMods','renderCapSet','hkInput','addFromSettings','setGeneralKv','uiStyleChoices','navIconChoices','motionChoices','wallpaperChoices','overviewChoices','uiIcon'])ctx[name]=()=>'';
  vm.runInContext(production,ctx,{filename:'production-builtin-navigation.js'});
  async function reply(i,data){assert.ok(requests[i],String(i));requests[i].resolve(data);await flush();}
  async function reject(i,error){requests[i].reject(error);await flush();}
  async function open(){await ctx.showSettings();await reply(requests.length-1,{default_parent:'C:/',files:3,business_options:[{name:'PPT',selected:true}]});const list=requests.length-1;assert.equal(requests[list].url,'api/builtin/files');await reply(list,{project:ctx.S.project.root,items:[]});return doc.querySelector('#setBuiltin');}
  return {ctx,doc,host,settings,requests,effects,mounts,add,reply,reject,open};
}

test('legacy saves builtin selection loads the archive tree without navigating to settings',async()=>{
  const f=fixture();f.ctx.view='saves';f.ctx.location.hash='#/saves?c=builtin';const pending=f.ctx.showSaves();
  assert.equal(f.requests.length,1);assert.equal(f.requests[0].url,'api/checkpoints');await f.reply(0,{saves:[]});await pending;
  assert.equal(f.ctx.SVSEL,'tree');assert.equal(f.ctx.location.hash,'#/saves?c=builtin');assert.equal(f.ctx.view,'saves');
  assert.equal(f.host.querySelector('#setBuiltin'),null);assert.equal(f.effects.filter(x=>x[0]==='tree').length,1);
  assert.ok(!f.host.querySelectorAll('a').some(a=>(a.attrs.href||'').startsWith('#/settings')));
});

test('archives main navigation opens the tree after builtin settings even with a cached legacy selection',async()=>{
  const f=fixture();
  // Settings is entered explicitly. Returning via the main archive link must
  // not turn a previous in-memory builtin selection into a settings redirect.
  f.ctx.location.hash='#/settings?s=set-builtin';f.ctx.SVSEL='builtin';await f.open();assert.ok(f.settings.querySelector('#setBuiltin'));
  f.ctx.location.hash='#/saves';f.ctx.view='saves';const index=f.requests.length,pending=f.ctx.showSaves();
  assert.equal(f.requests.length,index+1);assert.equal(f.requests[index].url,'api/checkpoints');
  await f.reply(index,{saves:[]});await pending;
  assert.equal(f.ctx.location.hash,'#/saves');assert.equal(f.ctx.view,'saves');assert.equal(f.ctx.SVSEL,'tree');
  assert.equal(f.effects.filter(x=>x[0]==='tree').length,1);assert.equal(f.requests.length,index+1);
  assert.equal(f.host.querySelector('#setBuiltin'),null);assert.equal(f.doc.querySelectorAll('#setBuiltin').length,1);
});

test('showSaves stale checkpoint response cannot dispatch after another page selection',async()=>{
  const f=fixture();f.ctx.view='saves';f.ctx.location.hash='#/saves?c=C1';f.ctx.SVSEL='C1';const pending=f.ctx.showSaves();f.ctx.SVSEL='tree';await f.reply(0,{saves:[{code:'C1'}]});await pending;assert.equal(f.effects.length,0);
});

test('builtins is an independent settings section and archives has no builtin entry',async()=>{
  const f=fixture(),box=await f.open();assert.ok(f.settings.contains(box));assert.equal(f.doc.querySelectorAll('#setBuiltin').length,1);assert.equal(f.host.querySelector('#setBuiltin'),null);
  const policy=f.doc.querySelector('#setSaves');assert.ok(policy);assert.notEqual(box.closest('section'),policy.closest('section'));
  assert.equal(box.closest('section').id,'set-builtin');assert.equal(policy.closest('section').id,'set-saves');
  const headings=f.effects.find(x=>x[0]==='toc')[2];assert.equal(headings.filter(x=>x.id==='set-builtin').length,1);assert.equal(headings.filter(x=>x.id==='set-saves').length,1);assert.equal(headings.filter(x=>/存档[和与]内置/.test(x.label)).length,0);
  assert.match(html,/\['savesTab','archive','存档','Archives'\]/);assert.doesNotMatch(html,/function showBuiltinPanel\(/);assert.doesNotMatch(fn('renderSaveToc'),/内置|c=builtin|#\/settings/);
});

test('settings builtin deep link selects its own directory row without selecting archives',async()=>{
  const f=fixture();f.ctx.location.hash='#/settings?s=set-builtin';await f.open();
  const scroll=f.effects.filter(x=>x[0]==='scroll');assert.equal(scroll.length,1);assert.equal(scroll[0][1],'set-builtin');assert.equal(scroll[0][2].behavior,'auto');
  const row=f.doc.querySelector('[data-to="set-builtin"]');assert.ok(row.attrs.class.split(/\s+/).includes('on'));
  assert.ok(!f.doc.querySelector('[data-to="set-saves"]').attrs.class.split(/\s+/).includes('on'));
});

test('new-project form starts collapsed and refresh preserves its chosen expansion state and draft',async()=>{
  const f=fixture();await f.open();let detail=f.doc.querySelector('[data-builtin-new]');assert.ok(detail);assert.equal(detail.tagName,'details');assert.equal(detail.open,false);
  const input=f.doc.querySelector('#biName');input.value='Keep draft';f.doc.emit('input',{target:input});
  for(const expanded of [true,false]){
    detail.open=expanded;const index=f.requests.length,pending=f.ctx.loadBuiltin();await f.reply(index,{files:5});await pending;await f.reply(index+1,{project:'C:/project',items:[]});
    const next=f.doc.querySelector('[data-builtin-new]');assert.notEqual(next,detail);assert.equal(next.open,expanded);assert.equal(f.doc.querySelector('#biName').value,'Keep draft');detail=next;
  }
});

for(const change of ['hash','project'])test('pending settings readiness does not scroll after '+change+' changes',async()=>{
  const f=fixture();f.ctx.location.hash='#/settings?s=set-builtin';await f.ctx.showSettings();
  if(change==='hash')f.ctx.location.hash='#/settings?s=set-look';else f.ctx.S.project.root='D:/other';
  await f.reply(0,{files:3});await flush();assert.equal(f.effects.filter(x=>x[0]==='scroll').length,0);assert.equal(f.ctx.BI.data,null);
});

test('delegated form input survives a same-project refresh and ignores unrelated fields',async()=>{
  const f=fixture();await f.open();const name=f.doc.querySelector('#biName'),where=f.doc.querySelector('#biWhere');name.value='My draft';where.value='D:/Projects';
  f.doc.emit('input',{target:name});f.doc.emit('input',{target:where});const unrelated=f.add('biName',f.settings);unrelated.value='Wrong form';f.doc.emit('input',{target:unrelated});
  assert.equal(f.ctx.BI.name,'My draft');assert.equal(f.ctx.BI.where,'D:/Projects');const pending=f.ctx.loadBuiltin();await f.reply(2,{default_parent:'C:/new',files:5});await pending;
  assert.equal(f.doc.querySelector('#biName').value,'My draft');assert.equal(f.doc.querySelector('#biWhere').value,'D:/Projects');assert.equal(f.doc.querySelector('#biWhere').placeholder,'C:/new');
});

test('focused fields prevent refresh and focus acquired during GET prevents DOM replacement',async()=>{
  const f=fixture();await f.open();const box=f.doc.querySelector('#setBuiltin'),name=f.doc.querySelector('#biName');name.focus();await f.ctx.loadBuiltin();assert.equal(f.requests.length,2);
  f.doc.activeElement=null;const pending=f.ctx.loadBuiltin();name.value='Currently typing';f.doc.emit('input',{target:name});name.focus();await f.reply(2,{files:99});await pending;
  assert.equal(f.doc.querySelector('#setBuiltin'),box);assert.equal(f.doc.querySelector('#biName'),name);assert.equal(name.value,'Currently typing');assert.equal(f.ctx.BI.data.files,3);
});

for(const change of ['page','project','box','settings-hash'])test('loadBuiltin ignores a stale '+change+' response',async()=>{
  const f=fixture();await f.open();const oldData=f.ctx.BI.data,box=f.doc.querySelector('#setBuiltin'),before=box.innerHTML,pending=f.ctx.loadBuiltin();
  if(change==='page'){f.ctx.view='saves';f.ctx.location.hash='#/saves';}
  if(change==='project')f.ctx.S.project.root='D:/other';
  if(change==='box'){box.remove();f.add('setBuiltin',f.settings);}
  if(change==='settings-hash')f.ctx.location.hash='#/settings?s=appearance';
  await f.reply(2,{files:999});await pending;assert.equal(f.ctx.BI.data,oldData);assert.equal(box.innerHTML,before);assert.equal(f.requests.length,3);
});

test('loadBuiltin guards the completion-animation await as well as the network response',async()=>{
  const f=fixture();await f.open();let complete;f.ctx.completeReading=()=>new Promise(r=>{complete=r;});const old=f.ctx.BI.data,pending=f.ctx.loadBuiltin();await f.reply(2,{files:99});
  assert.equal(typeof complete,'function');f.ctx.location.hash='#/saves?c=tree';f.ctx.SVSEL='tree';complete();await pending;assert.equal(f.ctx.BI.data,old);assert.equal(f.requests.length,3);
});

test('new project resets prior form data, selected extras and stale directory caches',async()=>{
  const f=fixture();await f.open();const oldBox=f.doc.querySelector('#setBuiltin');Object.assign(f.ctx.BI,{name:'Previous project draft',where:'D:/old',business:new Set(['PPT']),extra:new Set(['private.txt']),beforeExtra:new Set(['private.txt']),result:{target:'old'},stats:{files:99},statsSelection:4});f.ctx.BI.dirs.set('private',{items:[]});f.ctx.BI.errors.set('private','old error');
  f.ctx.S.project.root='D:/new';await f.ctx.showSettings();assert.notEqual(f.doc.querySelector('#setBuiltin'),oldBox);assert.equal(f.ctx.BI.name,'');assert.equal(f.ctx.BI.where,'');assert.equal(f.ctx.BI.extra.size,0);assert.equal(f.ctx.BI.beforeExtra.size,0);assert.equal(f.ctx.BI.dirs.size,0);assert.equal(f.ctx.BI.errors.size,0);assert.equal(f.ctx.BI.result,null);assert.equal(f.ctx.BI.stats,null);
  await f.reply(2,{files:5,business_options:[{name:'Novel',selected:true}]});assert.equal(f.doc.querySelector('#biName').value,'');assert.deepEqual([...f.ctx.BI.business],['Novel']);await f.reply(3,{project:'D:/new',items:[]});
});

test('newer load wins over an older response on the same page',async()=>{
  const f=fixture();await f.open();const first=f.ctx.loadBuiltin(),second=f.ctx.loadBuiltin();await f.reply(3,{files:22});await second;await f.reply(2,{files:11});await first;assert.equal(f.ctx.BI.data.files,22);assert.equal(f.requests.filter(x=>x.method!=='GET').length,0);
});

test('load error keeps populated form and draft rather than rebuilding it',async()=>{
  const f=fixture();await f.open();const name=f.doc.querySelector('#biName');name.value='Keep me';f.doc.emit('input',{target:name});const pending=f.ctx.loadBuiltin();await f.reject(2,Error('offline'));await pending;
  assert.equal(f.doc.querySelector('#biName'),name);assert.equal(name.value,'Keep me');assert.equal(f.ctx.BI.message,'offline');assert.equal(f.ctx.BI.data.files,3);
});

for(const change of ['project','page','detached','newer'])test('marked-file list ignores stale '+change+' responses',async()=>{
  const f=fixture(),host=f.add('manual-list',f.host);host.innerHTML='<span>previous</span>';const first=f.ctx.renderBuiltinMarks(host),before=host.innerHTML;
  if(change==='project')f.ctx.S.project.root='D:/other';if(change==='page')f.ctx.location.hash='#/search';if(change==='detached')host.remove();
  if(change==='newer'){const second=f.ctx.renderBuiltinMarks(host);await f.reply(1,{project:'C:/project',items:[]});await second;}
  const expected=change==='newer'?host.innerHTML:before;await f.reply(0,{project:'C:/project',items:[{path:'old.txt',state:'marked'}]});await first;assert.equal(host.innerHTML,expected);
});

test('marked-file refresh keeps expanded state, accepts equivalent Windows roots and suppresses missing-file links',async()=>{
  const f=fixture(),host=f.add('manual-list',f.host);host.innerHTML='<details open><summary>Existing</summary></details>';const pending=f.ctx.renderBuiltinMarks(host);
  await f.reply(0,{project:'c:\\PROJECT\\',items:[{path:'missing.pdf',state:'missing'},{path:'present.pdf',state:'marked'}]});await pending;
  assert.equal(host.querySelector('details').open,true);assert.equal(f.mounts.length,1);assert.equal(host.querySelectorAll('a').length,1);assert.match(host.querySelector('a').attrs.href,/present.pdf/);
  const again=host.querySelector('[data-builtin-refresh]').onclick();assert.equal(f.requests[1].method,'GET');await f.reply(1,{project:'C:/project',items:[]});await again;assert.equal(f.requests.filter(x=>x.method!=='GET').length,0);
});

test('marked-file list rejects a different project and exposes a read-only retry',async()=>{
  const f=fixture(),host=f.add('manual-list',f.host),pending=f.ctx.renderBuiltinMarks(host);await f.reply(0,{project:'D:/other',items:[{path:'foreign.txt'}]});await pending;
  assert.doesNotMatch(host.innerHTML,/foreign.txt/);assert.ok(host.querySelector('[data-builtin-refresh]'));const retry=host.querySelector('[data-builtin-refresh]').onclick();assert.equal(f.requests[1].method,'GET');await f.reply(1,{project:'C:/project',items:[]});await retry;
});
