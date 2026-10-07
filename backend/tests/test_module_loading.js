'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const staged=!!process.env.MH_MODULE_SOURCE,sourcePath=process.env.MH_MODULE_SOURCE||path.join(__dirname,'../../模板.html');
const full=fs.readFileSync(sourcePath,'utf8');
function extract(begin,end){const a=full.indexOf(begin),b=full.indexOf(end,a);assert.ok(a>=0&&b>a,'Missing production block: '+begin);return full.slice(a,b);}
const source=extract('/* ================= 模块读取事务 Module loading ================= */','/* ================= 模块读取事务 Module loading 结束 ================= */')
  +['showModule','showFile','showCodemap','zenPrefetch'].map(name=>extract('/* 模块读取入口 '+name+' */','/* 模块读取入口 '+name+' 结束 */')).join('\n')
  +extract('/* 阅读页删除入口 loadPTree */','/* 阅读页删除入口 loadPTree 结束 */');
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
class Element {
  constructor(tag='div',id=''){this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.parentNode=null;this.dataset={};this.attributes={};this.value='';this._html='';this.writeCount=0;
    const classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>classes.add(x)),remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x),
      toggle:(x,force)=>{const yes=force===undefined?!classes.has(x):!!force;if(yes)classes.add(x);else classes.delete(x);return yes;}};}
  get isConnected(){let n=this;while(n){if(n.tagName==='BODY')return true;n=n.parentNode;}return false;}
  get firstElementChild(){return this.children[0]||null;}
  get innerHTML(){return this._html;}
  set innerHTML(value){this._html=String(value);++this.writeCount;this.children.forEach(c=>c.parentNode=null);this.children=[];
    if(value){const first=new Element('div');this.appendChild(first);for(const m of String(value).matchAll(/id="([^"]+)"/g)){const node=new Element('div',m[1]);this.appendChild(node);}}
  }
  setAttribute(k,v){this.attributes[k]=String(v);}getAttribute(k){return this.attributes[k]||null;}
  appendChild(child){if(child.parentNode)child.remove();child.parentNode=this;this.children.push(child);return child;}
  remove(){if(this.parentNode){const a=this.parentNode.children;a.splice(a.indexOf(this),1);this.parentNode=null;}}
  contains(child){if(this===child)return true;return this.children.some(c=>c.contains(child));}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  querySelectorAll(selector){const found=[];const matches=n=>selector[0]==='#'?n.id===selector.slice(1):selector==='.cmx-stage'?n.classList.contains('cmx-stage'):
    selector==='.fi.on'?n.classList.contains('fi')&&n.classList.contains('on'):selector==='.fi[data-file]'?n.classList.contains('fi')&&n.dataset.file!==undefined:
    selector==='a[data-cf]'?n.tagName==='A'&&n.dataset.cf!==undefined:false;
    const walk=n=>n.children.forEach(c=>{if(matches(c))found.push(c);walk(c);});walk(this);return found;}
}
function harness(){
  const e={requests:[],completed:[],failed:[],completionWaits:[],toasts:[],renderedTrees:[],opened:[],controllers:[],mounts:0,refreshes:0,destroys:0,holdComplete:false,reduced:false,
    overview:false,unknown:null,zen:false,zenCalls:0,rows:[],body:new Element('body')};
  e.mv=new Element('div','modview');e.tree=new Element('div','tree');e.body.appendChild(e.tree);e.body.appendChild(e.mv);
  e.ptree=new Element('aside','ptree');e.toc=new Element('aside','toc');e.body.appendChild(e.ptree);e.body.appendChild(e.toc);
  const context={console,WeakMap,JSON,Promise,Set,location:{hash:'#/m/A'},scrollY:42,S:{project:{root:'C:/Projects/Alpha',name:'Alpha'},modules:['A','B','源代码','文献'].map(name=>({name}))},
    cur:'A',view:'mod',online:true,MV:{name:'A',tree:null,sel:null,shown:null,open:new Set()},PCACHE:{},CMAPCTL:null,ZPOS:{},LASTFILE:{},ACT:{viewed:[]},
    CODEMAP:'#代码地图',CODELIST:'#代码清单',MODULEMAP:'#模块总览',BLUEPRINTMAP:'#蓝图总览',RULEMAP:'#戒律二维总览',OPENABLE_KINDS:['text'],ZEN:{slide:null},
    document:{title:'',body:e.body,createElement:tag=>new Element(tag),querySelector:s=>e.body.querySelector(s)},
    $:selector=>e.body.querySelector(selector),getLang:()=>e.lang||'zh',
    initialReadPending:()=>false,initialReadShow:()=>{},PV:{tree:null,sel:'keep.md',open:new Set(['keep-dir'])},FILE_DELETE:{treeSerial:0},
    fileDeleteProjectChanged:()=>{},fileDeleteRoot:()=>context.S&&context.S.project.root||'',pnodes:items=>items.map(x=>x.name||x.path||'').join(''),
    readingFlames:(zh,en)=>'<span class="three-flames">'+(e.lang==='en'?en:zh)+'</span>',
    completeReading:async host=>{assert.ok(host.isConnected,'Only an owned live status may complete');e.completed.push(host);
      if(e.holdComplete&&!e.reduced){const wait=deferred();e.completionWaits.push(wait);await wait.promise;}},
    failReading:(host,zh,en)=>{e.failed.push(host);host.innerHTML='<span role="status">'+context.esc(e.lang==='en'?en:zh)+'</span>';},
    api:(method,url)=>{assert.equal(method,'GET','Loading must never mutate/start/scan');assert.match(url,/^(api\/modules\/.+\/(tree|preview\?path=|codemap)|api\/project\/tree|api\/state)/);
      const wait=deferred();e.requests.push({url,method,...wait});return wait.promise;},
    toast:message=>e.toasts.push(String(message)),esc:s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
    renderTree:()=>e.renderedTrees.push(context.MV.tree),moduleOverviewEnabled:()=>e.overview,moduleOverviewPath:name=>name==='源代码'?context.CODEMAP:context.MODULEMAP,
    isModuleOverviewPath:path=>['#模块总览','#蓝图总览','#戒律总览','#代码地图','#项目全景'].includes(path),
    moduleDefaultFile:()=>{const item=context.MV.tree&&context.MV.tree.items&&context.MV.tree.items.find(x=>x.path&&x.path[0]!=='#');return item&&item.path||null;},
    renderIntro:()=>{e.mv.innerHTML='<p>Intro</p>';},zkey:(m,p)=>m+'|'+p,shown:p=>'资料/'+context.cur+'/'+p,rawUrl:(m,p)=>'files/'+m+'/'+p,
    previewBody:p=>({body:'<article>'+p.text+'</article>',wide:!!p.wide}),pvWrap:html=>html,fmtSize:s=>String(s),fmtTime:s=>String(s),govButton:()=>'',
    act:(list,item)=>list.push(item),fileHash:p=>{context.location.hash='#/m/'+encodeURIComponent(context.cur)+'?f='+encodeURIComponent(p);},
    landOn:(name,p)=>{context.MV.shown=p;},appendNote(){},openLocal(){},overviewNotes(){},stickyNoteIcon(){return '';},
    cmapHead:()=>'<h1>Source</h1><button id="treeTgl"></button><button id="cite"></button>',cmapWire(){},builtinFileSlot:()=>'',   // 10-07 文件页多了内置小锁
    zenOn:()=>e.zen,zenLand:()=>++e.zenCalls,zenPos:()=>++e.zenCalls,zenSeq:()=>e.zenSequence||null};
  context.window=context;
  context.CodeMap={mount:(box,opts)=>{
    ++e.mounts;const stage=new Element('div');stage.classList.add('cmx-stage');box.appendChild(stage);const ready=deferred();let alive=true,serial=0,settled=false;
    const ctl={module:opts.module,ready:ready.promise,camera:{x:71,y:23,z:2},alive:()=>alive&&stage.isConnected,
      refresh:()=>{++e.refreshes;return load();},destroy:()=>{if(!alive)return;alive=false;++e.destroys;if(!settled){settled=true;ready.resolve({ok:false,module:opts.module,destroyed:true});}}};
    function load(){const ticket=++serial;return opts.api('GET','api/modules/'+encodeURIComponent(opts.module)+'/codemap/files').then(d=>{
      if(!alive||!stage.isConnected)return{ok:false,module:opts.module,destroyed:true};if(ticket!==serial)return{ok:false,module:opts.module,stale:true};
      return d||{ok:true,module:opts.module};});}
    load().then(result=>{if(!settled){settled=true;ready.resolve(result);}},error=>{if(!settled){settled=true;ready.resolve({ok:false,module:opts.module,error:error.message});}});
    e.controllers.push(ctl);return ctl;}};
  vm.createContext(context);vm.runInContext(source,context,{filename:sourcePath});
  context.openItem=(p,quiet)=>{context.invalidateModuleReading();e.opened.push(p);
    if(e.unknown){context.MV.sel=p;return e.unknown(p);}
    if(p===context.CODEMAP||p===context.CODELIST)return context.showCodemap(p===context.CODELIST);
    if(p[0]==='#'){context.MV.sel=p;e.mv.innerHTML='<section>Virtual page</section>';return;}
    return context.showFile(p,quiet);};
  e.context=context;context.moduleReadProjectChanged();
  e.navigate=(name,path=null)=>{context.invalidateModuleReading();context.view='mod';context.cur=name;context.MV.name=name;context.MV.sel=path;context.location.hash='#/m/'+encodeURIComponent(name)+(path?'?f='+encodeURIComponent(path):'');};
  e.leave=()=>{context.invalidateModuleReading();context.view='settings';context.cur=null;context.location.hash='#/settings';};
  e.root=root=>{context.S={...context.S,project:{root,name:root}};context.moduleReadProjectChanged();};
  e.replaceHost=()=>{e.mv.remove();e.mv=new Element('div','modview');e.body.appendChild(e.mv);};
  e.call=(name,...args)=>context[name](...args);return e;
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function until(predicate){for(let i=0;i<25&&!predicate();++i)await tick();assert.ok(predicate(),'Expected production async operation');}
const preview=(text='ok',extra={})=>({kind:'text',text,size:3,mtime:12,...extra});
const tree=(text='ok',items=[])=>({text,items});
const codeList=(name='a.py')=>({groups:[{dir:'backend',files:[{path:name,name,says:'Program'}]}]});

test('pending tree appends independent flames, preserves current DOM, and commits only after real success plus completion',async()=>{
  const e=harness(),input=new Element('input');input.value='unsaved';e.mv.appendChild(input);e.holdComplete=true;const pending=e.call('showModule');
  assert.ok(e.mv.contains(input));assert.equal(input.value,'unsaved');assert.equal(e.context.MV.tree,null);assert.equal(e.completed.length,0);
  assert.match(e.tree.children.at(-1).innerHTML,/正在读取模块目录/);assert.equal(e.mv.children.length,1);e.requests[0].resolve(tree('new'));await until(()=>e.completed.length===1);
  assert.equal(e.context.MV.tree,null);assert.equal(e.renderedTrees.length,0);e.completionWaits[0].resolve();const result=await pending;
  assert.equal(e.context.MV.tree.text,'new');assert.equal(e.renderedTrees.length,1);assert.equal(result.scope,'module-directory');assert.equal(result.mediaReady,false);
});
test('tree A→B→A late success and late error cannot overwrite the newest tree or toast',async()=>{
  const e=harness(),a1=e.call('showModule');e.navigate('B');const b=e.call('showModule');e.navigate('A');const a2=e.call('showModule');
  e.requests[2].resolve(tree('latest'));await a2;e.requests[0].resolve(tree('old A'));e.requests[1].reject(Error('old B failure'));await Promise.all([a1,b]);
  assert.equal(e.context.MV.tree.text,'latest');assert.equal(e.renderedTrees.length,1);assert.equal(e.completed.length,1);assert.equal(e.toasts.length,0);
});
test('tree completion callback is guarded again after root, view, path or DOM changes',async()=>{
  for(const change of ['root','view','path','dom']){const e=harness();e.holdComplete=true;const pending=e.call('showModule');e.requests[0].resolve(tree('late'));await until(()=>e.completionWaits.length===1);
    if(change==='root')e.root('C:/Projects/Beta');else if(change==='view')e.leave();else if(change==='path')e.context.MV.sel='new.md';else e.replaceHost();
    e.completionWaits[0].resolve();await pending;assert.equal(e.context.MV.tree,null);assert.equal(e.renderedTrees.length,0);assert.equal(e.toasts.length,0);}
});
test('tree error, offline or missing module has no success merge and no false infinite wait',async()=>{
  const e=harness(),pending=e.call('showModule');e.requests[0].reject(Error('<bad tree>'));const result=await pending;
  assert.equal(result.ok,false);assert.equal(e.completed.length,0);assert.equal(e.context.MV.tree,null);assert.match(e.tree.children.at(-1).innerHTML,/&lt;bad tree&gt;/);assert.equal(e.failed.length,1);
  for(const reason of ['offline','missing']){const x=harness();if(reason==='offline')x.context.online=false;else x.context.S.modules=[];
    assert.equal((await x.call('showModule')).ok,false);assert.equal(x.requests.length,0);assert.equal(x.completed.length,0);assert.equal(x.mv.children.length,1);}
});
test('a zero-delay successful tree adds no artificial timeout; reduced completion remains immediate',async()=>{
  const e=harness();e.reduced=true;e.holdComplete=true;const pending=e.call('showModule');e.requests[0].resolve(tree());await pending;
  assert.equal(e.completed.length,1);assert.equal(e.completionWaits.length,0);assert.equal(e.renderedTrees.length,1);
});
test('unknown async openItem is not falsely declared whole-page or media ready',async()=>{
  const e=harness(),waiting=deferred();e.context.MV.sel='#未知业务页';e.unknown=()=>waiting.promise;
  const pending=e.call('showModule');e.requests[0].resolve(tree());await until(()=>e.opened.length===1);
  assert.equal(e.completed.length,1,'Only the actual directory scope completes');waiting.resolve(undefined);const result=await pending;
  assert.equal(result.scope,'module-directory');assert.equal(result.contentReady,false);assert.equal(result.mediaReady,false);assert.equal(e.completed.length,1);
});
test('directory hands off to a real preview request with its own status and exact successful scope',async()=>{
  const e=harness();e.context.MV.sel='a.md';const pending=e.call('showModule');e.requests[0].resolve(tree());await until(()=>e.requests.length===2);
  assert.equal(e.completed.length,1);assert.match(e.mv.children.at(-1).innerHTML,/正在读取预览资料/);e.requests[1].resolve(preview());const result=await pending;
  assert.equal(result.scope,'preview-metadata');assert.equal(result.mediaReady,false);assert.equal(e.completed.length,2);
});
test('pending preview preserves existing inputs and iframe; same metadata refresh retains their DOM identity',async()=>{
  const e=harness();const first=e.call('showFile','a.md');e.requests[0].resolve(preview());await first;
  const input=new Element('input'),iframe=new Element('iframe');input.value='draft';e.mv.appendChild(input);e.mv.appendChild(iframe);const writes=e.mv.writeCount;
  const refresh=e.call('showFile','a.md');assert.ok(e.mv.contains(input));assert.ok(e.mv.contains(iframe));assert.equal(e.mv.writeCount,writes);
  e.requests[1].resolve(preview());await refresh;assert.equal(e.mv.writeCount,writes);assert.ok(e.mv.contains(input));assert.ok(e.mv.contains(iframe));assert.equal(input.value,'draft');
});
test('changed preview metadata replaces the page after its real result; returns no media-loaded claim',async()=>{
  const e=harness(),a=e.call('showFile','a.md');e.requests[0].resolve(preview('first'));await a;const writes=e.mv.writeCount;
  const b=e.call('showFile','a.md');assert.equal(e.mv.writeCount,writes);e.requests[1].resolve(preview('changed'));const result=await b;
  assert.equal(e.mv.writeCount,writes+1);assert.match(e.mv.innerHTML,/changed/);assert.equal(result.scope,'preview-metadata');assert.equal(result.mediaReady,false);
});
test('preview A→B→A and repeated same path reject late success and error without clearing latest selection',async()=>{
  for(const paths of [['a.md','b.md','a.md'],['a.md','a.md','a.md']]){const e=harness(),p1=e.call('showFile',paths[0]),p2=e.call('showFile',paths[1]),p3=e.call('showFile',paths[2]);
    e.requests[2].resolve(preview('latest'));await p3;e.requests[0].resolve(preview('old'));e.requests[1].reject(Error('old failure'));await Promise.all([p1,p2]);
    assert.equal(e.context.MV.sel,paths[2]);assert.match(e.mv.innerHTML,/latest/);assert.equal(e.completed.length,1);assert.equal(e.toasts.length,0);}
});
test('preview old errors and completion continuation cannot mutate a changed root/view/path/host',async()=>{
  for(const change of ['root','view','path','dom']){for(const failure of [true,false]){const e=harness();e.holdComplete=!failure;const pending=e.call('showFile','a.md');
    if(!failure){e.requests[0].resolve(preview('late'));await until(()=>e.completionWaits.length===1);}
    if(change==='root')e.root('C:/Projects/Beta');else if(change==='view')e.leave();else if(change==='path')e.context.MV.sel='new.md';else e.replaceHost();
    const writes=e.mv.writeCount;if(failure)e.requests[0].reject(Error('old error'));else e.completionWaits[0].resolve();await pending;
    assert.equal(e.mv.writeCount,writes);assert.equal(e.toasts.length,0);if(change==='path')assert.equal(e.context.MV.sel,'new.md');}}
});
test('current preview error preserves a previous same-page DOM and is not treated as completion, including quiet',async()=>{
  for(const quiet of [false,true]){const e=harness(),first=e.call('showFile','a.md');e.requests[0].resolve(preview());await first;const input=new Element('input');input.value='draft';e.mv.appendChild(input);
    const count=e.completed.length,pending=e.call('showFile','a.md',quiet);e.requests[1].reject(Error('connection lost'));const result=await pending;
    assert.equal(result.ok,false);assert.equal(e.completed.length,count);assert.equal(e.context.MV.sel,'a.md');assert.ok(e.mv.contains(input));assert.equal(input.value,'draft');
    assert.match(e.mv.children.at(-1).innerHTML,/connection lost/);assert.equal(e.toasts.length,quiet?0:1);}
});
test('root-scoped preview cache never supplies another project and is consumed only once',async()=>{
  const e=harness(),oldKey=e.context.modulePreviewKey('A','a.md','C:/Projects/Other');e.context.PCACHE[oldKey]=Promise.resolve(preview('wrong root'));
  const cached=e.context.modulePreviewKey('A','a.md');e.context.PCACHE[cached]=Promise.resolve(preview('right root'));const first=await e.call('showFile','a.md');
  assert.equal(first.ok,true);assert.equal(e.requests.length,0);assert.match(e.mv.innerHTML,/right root/);assert.equal(e.context.PCACHE[cached],undefined);
  const second=e.call('showFile','a.md');assert.equal(e.requests.length,1);e.requests[0].resolve(preview('fresh'));await second;assert.match(e.mv.innerHTML,/fresh/);
});
test('project change clears all old cache entries and the owned old-root code controller',async()=>{
  const e=harness();e.context.PCACHE[e.context.modulePreviewKey('A','a.md')]=Promise.resolve(preview());e.navigate('源代码');const pending=e.call('showCodemap',false);
  assert.equal(e.mounts,1);e.root('C:/Projects/Beta');await pending;assert.equal(Object.keys(e.context.PCACHE).length,0);assert.equal(e.destroys,1);assert.equal(e.context.CMAPCTL,null);assert.equal(e.completed.length,0);
});
test('prefetch failure cannot delete a newer promise for the same key; uses captured root and module',async()=>{
  const e=harness();e.zenSequence={cur:'a.md',list:[{key:'before.md'},{key:'a.md'},{key:'after.md'}]};e.call('zenPrefetch');assert.equal(e.requests.length,2);
  const key=e.context.modulePreviewKey('A','before.md'),replacement=Promise.resolve(preview('new'));e.context.PCACHE[key]=replacement;
  e.navigate('B');e.requests[0].reject(Error('old prefetch'));e.requests[1].resolve(preview());await tick();assert.equal(e.context.PCACHE[key],replacement);
  assert.match(e.requests[0].url,/modules\/A\/preview/);assert.ok(key.includes('C:/Projects/Alpha'));assert.ok(!Object.keys(e.context.PCACHE).includes('A|before.md'));
});
test('first code map waits for its original ready and does not refresh or duplicate GET',async()=>{
  const e=harness();e.navigate('源代码');const first=e.call('showCodemap',false);assert.equal(e.mounts,1);assert.equal(e.requests.length,1);assert.equal(e.refreshes,0);assert.equal(e.completed.length,0);
  const second=e.call('showCodemap',false);assert.equal(e.mounts,1);assert.equal(e.requests.length,1);assert.equal(e.refreshes,0);
  e.requests[0].resolve({ok:true,module:'源代码'});await Promise.all([first,second]);assert.equal(e.completed.length,1);assert.equal(e.context.MV.sel,e.context.CODEMAP);
});
test('alive code map refresh retains controller, stage, input, camera and view without rebuilding',async()=>{
  const e=harness();e.navigate('源代码');const initial=e.call('showCodemap',false);e.requests[0].resolve({ok:true,module:'源代码'});await initial;
  const ctl=e.controllers[0],stage=e.mv.querySelector('.cmx-stage'),input=new Element('input');input.value='unsaved search';e.mv.appendChild(input);const writes=e.mv.writeCount;
  const refresh=e.call('showCodemap',false);assert.equal(e.refreshes,1);assert.equal(e.requests.length,2);assert.equal(e.mounts,1);assert.equal(e.destroys,0);assert.equal(e.mv.writeCount,writes);
  e.requests[1].resolve({ok:true,module:'源代码'});const result=await refresh;assert.equal(result.ok,true);assert.equal(e.context.CMAPCTL,ctl);assert.equal(e.mv.querySelector('.cmx-stage'),stage);
  assert.equal(input.value,'unsaved search');assert.ok(e.mv.contains(input));assert.deepEqual(ctl.camera,{x:71,y:23,z:2});
});
test('code map initial error/destroyed/stale result never calls completion',async()=>{
  for(const state of ['error','destroyed','stale']){const e=harness();e.navigate('源代码');const pending=e.call('showCodemap',false);
    e.requests[0].resolve({ok:false,module:'源代码',[state]:true,error:'real map failure'});const result=await pending;
    assert.equal(result.ok,false);assert.equal(e.completed.length,0);assert.equal(e.mounts,1);assert.equal(e.refreshes,0);}
});
test('late code map ready/error cannot settle a new route, file, controller or root',async()=>{
  for(const change of ['view','file','root','controller']){const e=harness();e.navigate('源代码');const pending=e.call('showCodemap',false);
    if(change==='view')e.leave();else if(change==='root')e.root('C:/Projects/Beta');else if(change==='file'){const file=e.call('showFile','new.py');e.requests[1].resolve(preview('new page'));await file;}
    else{e.controllers[0].destroy();e.navigate('A');e.context.MV.sel=e.context.CODEMAP;const fresh=e.call('showCodemap',false);e.requests[1].resolve({ok:true,module:'A'});await fresh;}
    const completed=e.completed.length;e.requests[0].resolve({ok:true,module:'源代码'});await pending;assert.equal(e.completed.length,completed);
    if(change==='controller')assert.equal(e.context.CMAPCTL,e.controllers[1]);}
});
test('code map completion continuation guards controller liveness and cannot settle a replacement loader',async()=>{
  const e=harness();e.navigate('源代码');e.holdComplete=true;const first=e.call('showCodemap',false);e.requests[0].resolve({ok:true,module:'源代码'});await until(()=>e.completionWaits.length===1);
  e.controllers[0].destroy();e.context.invalidateModuleReading();e.context.MV.sel='pending.md';const file=e.call('showFile','pending.md');const status=e.mv.children.at(-1);
  e.completionWaits[0].resolve();await first;assert.ok(e.mv.contains(status));assert.match(status.innerHTML,/正在读取预览资料/);assert.equal(e.context.MV.sel,'pending.md');
  e.holdComplete=false;e.requests[1].resolve(preview());await file;
});
test('code list pending preserves old map/input; errors do not destroy current controller or complete',async()=>{
  const e=harness();e.navigate('源代码');const map=e.call('showCodemap',false);e.requests[0].resolve({ok:true,module:'源代码'});await map;const ctl=e.context.CMAPCTL,stage=e.mv.querySelector('.cmx-stage');
  const list=e.call('showCodemap',true);assert.ok(e.mv.contains(stage));assert.equal(e.context.CMAPCTL,ctl);assert.equal(e.destroys,0);
  e.requests[1].reject(Error('list failure'));assert.equal((await list).ok,false);assert.equal(e.destroys,0);assert.equal(e.completed.length,1);assert.equal(e.context.CMAPCTL,ctl);
});
test('code list commits after success, preserves identical list DOM on refresh, and rejects old A→B→A',async()=>{
  const e=harness();e.navigate('源代码');const first=e.call('showCodemap',true);e.requests[0].resolve(codeList());await first;
  const input=new Element('input');input.value='draft';e.mv.appendChild(input);const writes=e.mv.writeCount,refresh=e.call('showCodemap',true);e.requests[1].resolve(codeList());await refresh;
  assert.equal(e.mv.writeCount,writes);assert.ok(e.mv.contains(input));
  const old=e.call('showCodemap',true);e.navigate('A');const middle=e.call('showCodemap',true);e.navigate('源代码');const latest=e.call('showCodemap',true);
  e.requests[4].resolve(codeList('latest.py'));await latest;const count=e.completed.length;e.requests[2].resolve(codeList('old.py'));e.requests[3].reject(Error('old failure'));await Promise.all([old,middle]);
  assert.match(e.mv.innerHTML,/latest.py/);assert.equal(e.completed.length,count);assert.equal(e.toasts.length,0);
});
test('invalid preview/codemap payload is an actual failure and never a successful completion',async()=>{
  for(const method of ['showFile','showCodemap']){const e=harness(),pending=method==='showFile'?e.call(method,'a.md'):e.call(method,true);e.requests[0].resolve(undefined);
    const result=await pending;assert.equal(result.ok,false);assert.equal(e.completed.length,0);assert.equal(e.context.MV.sel,method==='showFile'?'a.md':e.context.CODELIST);}
});
test('a changed hash invalidates tree, preview and list even before a route event arrives',async()=>{
  for(const kind of ['tree','preview','list']){const e=harness(),pending=kind==='tree'?e.call('showModule'):kind==='preview'?e.call('showFile','a.md'):e.call('showCodemap',true);
    e.context.location.hash='#/m/A?f=another.md';e.requests[0].resolve(kind==='tree'?tree():kind==='preview'?preview():codeList());await pending;
    assert.equal(e.completed.length,0);assert.equal(e.renderedTrees.length,0);assert.equal(e.mv.innerHTML,'');assert.equal(e.toasts.length,0);}
});
test('replacing the directory host invalidates a response without touching the new host or cached tree',async()=>{
  const e=harness(),pending=e.call('showModule');e.tree.remove();e.tree=new Element('div','tree');e.body.appendChild(e.tree);const writes=e.tree.writeCount;
  e.requests[0].resolve(tree('late'));await pending;assert.equal(e.context.MV.tree,null);assert.equal(e.renderedTrees.length,0);assert.equal(e.tree.writeCount,writes);assert.equal(e.completed.length,0);
});
test('an old cached preview Promise cannot commit after project A→B→A or erase fresh selection on error',async()=>{
  for(const failure of [false,true]){const e=harness(),old=deferred();e.context.PCACHE[e.context.modulePreviewKey('A','a.md')]=old.promise;
    const pending=e.call('showFile','a.md');e.root('C:/Projects/Beta');e.root('C:/Projects/Alpha');const latest=e.call('showFile','a.md');
    assert.equal(e.requests.length,1);e.requests[0].resolve(preview('latest root'));await latest;
    if(failure)old.reject(Error('cached old error'));else old.resolve(preview('old cache'));await pending;
    assert.match(e.mv.innerHTML,/latest root/);assert.equal(e.context.MV.sel,'a.md');assert.equal(e.completed.length,1);assert.equal(e.toasts.length,0);}
});
test('invalid directory payload fails before completion and never replaces the previous tree',async()=>{
  const e=harness();e.context.MV.tree=tree('previous');const pending=e.call('showModule');e.requests[0].resolve(null);const result=await pending;
  assert.equal(result.ok,false);assert.equal(e.completed.length,0);assert.equal(e.context.MV.tree.text,'previous');assert.equal(e.renderedTrees.length,0);
});
test('production integration contains route/root/selection/cache hooks',{skip:staged},()=>{
  for(const signature of ['function route()','function openItem(path, quiet)','function vOpen(path)','function openFile(module, path)']){
    const a=full.indexOf(signature);assert.ok(a>=0,signature);assert.match(full.slice(a,a+130),/invalidateModuleReading\(\)/,signature+' must invalidate even same selection');}
  const start=full.indexOf('function render(s)');assert.match(full.slice(start,start+230),/S = s;[\s\S]*moduleReadProjectChanged\(\)/);
  assert.match(full,/modulePreviewKey\(name,it\.key,root\)/);assert.doesNotMatch(source,/api\/scan\/now|PaneSpirit\.scan|api\(['"]POST/);
});

test('project directory pending and guarded completion preserve current DOM, selection and open folders',async()=>{
  const e=harness();e.context.view='search';e.context.cur=null;e.context.location.hash='#/search';e.holdComplete=true;
  const old=new Element('div');e.ptree.appendChild(old);const input=new Element('input');input.value='search draft';e.mv.appendChild(input);
  const pending=e.call('loadPTree');assert.ok(e.ptree.contains(old));assert.match(e.ptree.children.at(-1).innerHTML,/正在读取项目目录/);
  e.requests[0].resolve({name:'Alpha',items:[{name:'new.md'}]});await until(()=>e.completionWaits.length===1);
  assert.equal(e.context.PV.tree,null);e.completionWaits[0].resolve();await pending;
  assert.equal(e.context.PV.tree.name,'Alpha');assert.equal(e.context.PV.sel,'keep.md');assert.ok(e.context.PV.open.has('keep-dir'));assert.equal(input.value,'search draft');
});
test('project directory latest result wins over old success and failure; current failure retains old tree',async()=>{
  const e=harness();e.context.view='search';e.context.location.hash='#/search';e.context.PV.tree={name:'previous',items:[]};
  const a=e.call('loadPTree'),b=e.call('loadPTree'),c=e.call('loadPTree');e.requests[2].resolve({name:'latest',items:[]});await c;
  e.requests[0].resolve({name:'old',items:[]});e.requests[1].reject(Error('old error'));await Promise.all([a,b]);
  assert.equal(e.context.PV.tree.name,'latest');assert.equal(e.failed.length,0);assert.equal(e.completed.length,1);
  const oldHtml=e.ptree.innerHTML,d=e.call('loadPTree');e.requests[3].reject(Error('<current error>'));await d;
  assert.equal(e.context.PV.tree.name,'latest');assert.equal(e.ptree.innerHTML,oldHtml);assert.match(e.ptree.children.at(-1).innerHTML,/&lt;current error&gt;/);assert.equal(e.failed.length,1);
});
test('project directory completion rechecks root, route, hash and status host before committing',async()=>{
  for(const change of ['root','view','hash','host']){
    const e=harness();e.context.view='search';e.context.location.hash='#/search';e.holdComplete=true;const pending=e.call('loadPTree');
    e.requests[0].resolve({name:'late',items:[]});await until(()=>e.completionWaits.length===1);
    if(change==='root')e.root('C:/Projects/Beta');else if(change==='view')e.context.view='settings';else if(change==='hash')e.context.location.hash='#/search?f=new.md';
    else{e.ptree.remove();e.ptree=new Element('aside','ptree');e.body.appendChild(e.ptree);}
    e.completionWaits[0].resolve();await pending;assert.equal(e.context.PV.tree,null);assert.equal(e.failed.length,0);
  }
});
test('invalid project directory is a failure without merge and route invalidation retires its own pending status',async()=>{
  const e=harness();e.context.view='search';e.context.location.hash='#/search';let pending=e.call('loadPTree');e.requests[0].resolve(null);await pending;
  assert.equal(e.completed.length,0);assert.equal(e.failed.length,1);assert.equal(e.context.PV.tree,null);
  pending=e.call('loadPTree');const status=e.ptree.children.at(-1);e.context.invalidateProjectReading();assert.equal(status.isConnected,false);
  e.requests[1].reject(Error('after navigation'));await pending;assert.equal(e.failed.length,1);
});

const initialSource=extract('async function load() {','function readingFlames(')
  +extract('/* ================= 首次项目读取 Initial project loading ================= */','/* ================= 首次项目读取 Initial project loading 结束 ================= */');
function initialHarness(mode='mod',onlineProtocol=true){
  const e=harness(),c=e.context;e.stateRenders=[];e.routes=0;e.connections=[];e.searchLoads=0;
  c.S=null;c.online=false;c.loadSeq=0;c.CAN_ONLINE=onlineProtocol;c.view=mode;c.location.hash=mode==='mod'?'#/m/A':'#/search';
  c.setConn=state=>{e.connections.push(state);c.online=state==='on';};c.render=s=>{e.stateRenders.push(s);c.S=s;};
  c.route=()=>{++e.routes;};c.loadFresh=()=>{};c.loadCommands=()=>{};c.loadPTree=()=>++e.searchLoads;
  vm.runInContext(initialSource,c,{filename:sourcePath});e.phase=()=>vm.runInContext('INITIAL_READ.phase',c);c.initialReadShow();return e;
}
test('module entry before the first state response keeps initial flames and does not report offline or issue a directory request',async()=>{
  const e=initialHarness(),status=e.mv.children.at(-1),result=await e.call('showModule');
  assert.equal(result.scope,'initial-project-state');assert.equal(e.requests.length,0);assert.equal(e.mv.children.at(-1),status);
  assert.match(status.innerHTML,/正在读取项目/);assert.doesNotMatch(e.mv.innerHTML+status.innerHTML,/没连后端/);assert.equal(e.tree.children.length,0);
});
test('initial project read shows phoenix and flames until actual state success and owned completion, then routes once',async()=>{
  const e=initialHarness();assert.match(e.mv.children.at(-1).innerHTML,/initial-reading-brand/);assert.match(e.mv.children.at(-1).innerHTML,/正在读取项目/);
  e.holdComplete=true;const pending=e.call('load');assert.equal(e.routes,0);assert.equal(e.stateRenders.length,0);
  e.requests[0].resolve({project:{root:'C:/Projects/Alpha'},modules:[]});await until(()=>e.completionWaits.length===1);
  assert.equal(e.stateRenders.length,0);e.completionWaits[0].resolve();await pending;
  assert.equal(e.phase(),'ready');assert.equal(e.routes,1);assert.equal(e.stateRenders.length,1);assert.equal(e.completed.length,1);assert.equal(e.mv.children.length,0);
});
test('initial actual state failure and invalid payload fail visibly without routing or false success',async()=>{
  for(const invalid of [false,true]){const e=initialHarness(),pending=e.call('load');if(invalid)e.requests[0].resolve({});else e.requests[0].reject(Error('<state unavailable>'));
    await pending;assert.equal(e.phase(),'failed');assert.equal(e.routes,0);assert.equal(e.completed.length,0);assert.equal(e.failed.length,1);assert.equal(e.stateRenders.length,0);
    assert.match(e.mv.children.at(-1).innerHTML,/读取项目失败/);assert.equal(e.context.online,false);}
});
test('initial state late response cannot complete a replaced owner or overwrite newer state',async()=>{
  const e=initialHarness(),a=e.call('load'),b=e.call('load');e.requests[1].resolve({project:{root:'latest'},modules:[]});await b;
  e.requests[0].resolve({project:{root:'old'},modules:[]});await a;assert.equal(e.stateRenders.length,1);assert.equal(e.context.S.project.root,'latest');assert.equal(e.routes,1);
  const x=initialHarness(),pending=x.call('load');x.context.location.hash='#/settings';x.context.view='settings';x.requests[0].resolve({project:{root:'Alpha'},modules:[]});
  x.context.showSettings=()=>{};await pending;assert.equal(x.completed.length,0);assert.equal(x.routes,0);assert.equal(x.failed.length,0);
});
test('initial search state keeps input DOM and starts only the real directory reader; file mode issues no request',async()=>{
  const e=initialHarness('search'),input=new Element('input');input.value='unfinished search';e.mv.appendChild(input);
  const pending=e.call('load');e.requests[0].resolve({project:{root:'Alpha'},modules:[]});await pending;
  assert.equal(e.routes,0);assert.equal(e.searchLoads,1);assert.equal(input.value,'unfinished search');assert.ok(e.mv.contains(input));
  const file=initialHarness('mod',false);await file.call('load');assert.equal(file.requests.length,0);assert.equal(file.completed.length,0);assert.equal(file.phase(),'offline');
});
