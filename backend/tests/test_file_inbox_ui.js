'use strict';
/* 阅读页「移到入口」：网页这一半（按钮、确认、请求、成功卡、跟删除共用的钥匙）。harness 照 test_file_delete_ui.js，取的是 模板.html 里真的那几段 */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const template=fs.readFileSync(path.join(__dirname,'../../模板.html'),'utf8');
function extract(text,start,end){const a=text.indexOf(start),b=text.indexOf(end,a);assert.ok(a>=0&&b>a,'Missing production function block '+start);return text.slice(a,b);}
const deleteBlock=extract(template,'/* ================= 阅读页删除 File delete UI ================= */','/* ================= 阅读页删除 File delete UI 结束 ================= */');
const inboxBlock=extract(template,'/* ================= 阅读页移到入口 File to intake UI ================= */','/* ================= 阅读页移到入口 File to intake UI 结束 ================= */');
const entries={showFile:extract(template,'/* 模块读取入口 showFile */','/* 模块读取入口 showFile 结束 */'),showModule:extract(template,'/* 模块读取入口 showModule */','/* 模块读取入口 showModule 结束 */'),
  previewProject:extract(template,'/* 阅读页删除入口 previewProject */','/* 阅读页删除入口 previewProject 结束 */'),loadPTree:extract(template,'/* 阅读页删除入口 loadPTree */','/* 阅读页删除入口 loadPTree 结束 */')};
const code=extract(template,'function builtinFileSlot(','const BuiltinFiles=')+'\n'+extract(template,'/* ================= 模块读取事务 Module loading ================= */','/* ================= 模块读取事务 Module loading 结束 ================= */')+'\n'
  +deleteBlock+'\n'+inboxBlock+'\n'+Object.values(entries).join('\n');
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function decode(s){return String(s).replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');}
class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.parentNode=null;this.dataset={};this.attributes={};this.value='';this.disabled=false;this.hidden=false;this._html='';this.writes=0;this.events={};this.textContent='';this.scrollTop=0;const cs=new Set();this.classList={add:(...xs)=>xs.forEach(x=>cs.add(x)),remove:(...xs)=>xs.forEach(x=>cs.delete(x)),contains:x=>cs.has(x),toggle:(x,v)=>{const yes=v===undefined?!cs.has(x):!!v;yes?cs.add(x):cs.delete(x);return yes;}};}
  get isConnected(){let n=this;while(n){if(n.tagName==='BODY')return true;n=n.parentNode;}return false;}
  get firstElementChild(){return this.children[0]||null;}
  get innerHTML(){return this._html;}
  set innerHTML(html){this._html=String(html);++this.writes;for(const c of [...this.children])c.remove();const stack=[this];for(const m of this._html.matchAll(/<\/?[A-Za-z][^>]*>/g)){const token=m[0];if(token.startsWith('</')){if(stack.length>1)stack.pop();continue;}const tag=token.match(/^<([A-Za-z0-9]+)/)[1],n=new Element(tag);for(const a of token.matchAll(/([\w-]+)(?:="([^"]*)")?/g)){if(a.index===1)continue;n.setAttribute(a[1],decode(a[2]||''));}stack.at(-1).appendChild(n);if(!/^(input|img|hr|br|meta|link)$/i.test(tag)&&!token.endsWith('/>'))stack.push(n);}}
  appendChild(n){if(n.parentNode)n.remove();n.parentNode=this;this.children.push(n);return n;}
  remove(){if(this.parentNode){this.parentNode.children.splice(this.parentNode.children.indexOf(this),1);this.parentNode=null;}}
  setAttribute(k,v){this.attributes[k]=String(v);if(k==='id')this.id=v;if(k==='class')String(v).split(/\s+/).forEach(c=>this.classList.add(c));if(k==='disabled')this.disabled=true;if(k==='value')this.value=v;if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,x)=>x.toUpperCase())]=v;}
  getAttribute(k){return this.attributes[k]??null;}
  contains(n){return this===n||this.children.some(c=>c.contains(n));}
  matches(s){const attrs=[...s.matchAll(/\[([^\]=]+)(?:="([^"]*)")?\]/g)],base=s.replace(/\[[^\]]*\]/g,'');if(base[0]==='#'&&this.id!==base.slice(1))return false;if(base[0]==='.'&&!base.slice(1).split('.').every(c=>this.classList.contains(c)))return false;if(base&&base[0]!=='.'&&base[0]!=='#'&&this.tagName.toLowerCase()!==base)return false;return attrs.every(a=>a[2]===undefined?Object.hasOwn(this.attributes,a[1]):this.attributes[a[1]]===a[2]);}
  querySelectorAll(s){const out=[];const walk=n=>n.children.forEach(c=>{if(c.matches(s))out.push(c);walk(c);});walk(this);return out;}
  querySelector(s){return this.querySelectorAll(s)[0]||null;}
}
const root='C:/Synthetic/Alpha',canonical='资料/A/子/旧稿.md',version='a'.repeat(64);
function del(extra={}){return{allowed:true,path:canonical,project:root.toLowerCase(),revision:version,reason:'',...extra};}
function inbox(extra={}){return{applicable:true,allowed:true,path:canonical,project:root.toLowerCase(),revision:version,reason:'',module:'A',folder:'子',...extra};}
function preview(extra={}){return{kind:'text',text:'保留的原文',size:20,mtime:'2026-10-08',delete_action:del(),inbox_action:inbox(),...extra};}
function result(extra={}){return{action:'移到外部资料入口',from:canonical,to:'资料/_外部资料入口/旧稿.md',item:{id:7,status:'waiting',name:'旧稿.md',orig:canonical,candidates:[{module:'A',folder:'子',conf:'高',reason:'原来在这里',by:'原位置'}]},back:{module:'A',folder:'子'},by:'人',reason:'人在文件阅读页点了「移到入口」',log_id:'志-0042',...extra};}
function harness(scope='module'){
  const e={requests:[],toasts:[],confirms:[],completed:[],renderedTrees:[],opened:[],confirmValue:true,body:new Element('body')};
  for(const id of ['tree','modview','searchview','ptree','sres','spv','sq']){const n=new Element(id==='sq'?'input':'div');n.id=id;e[id]=n;e.body.appendChild(n);}
  const c={console,Set,WeakMap,JSON,Promise,Number,encodeURIComponent,S:{project:{root,name:'Alpha'},modules:[{name:'A',files:2}]},view:scope==='module'?'mod':'search',cur:scope==='module'?'A':null,online:true,MV:{name:'A',sel:null,shown:null,tree:null,open:new Set()},PV:{tree:null,sel:null,open:new Set()},PCACHE:{},CMAPCTL:null,ZPOS:{},LASTFILE:{},scrollY:7,ACT:{viewed:[]},MODULEMAP:'#模块总览',OPENABLE_KINDS:['text'],ZEN:{slide:null},location:{hash:scope==='module'?'#/m/A':'#/search'},history:{replaceState:(a,b,url)=>{c.location.hash=url;}},document:{createElement:tag=>new Element(tag)},window:{},$:s=>e.body.querySelector(s),esc,getLang:()=>e.lang||'zh',
    readingFlames:(zh,en)=>'<span>'+((e.lang==='en')?en:zh)+'</span>',completeReading:async n=>{assert.ok(n.isConnected);e.completed.push(n);},
    api:(method,url,data)=>{if(method==='POST'&&url==='api/files/trash'){assert.ok(e.promptValue!==undefined,'删除只在专门的测试里发');assert.deepEqual(Object.keys(data).sort(),['path','project','reason','revision']);}
      else if(method==='POST'){assert.equal(url,'api/files/inbox');assert.deepEqual(Object.keys(data).sort(),['path','project','revision']);}else{assert.equal(method,'GET');assert.ok(/^api\/modules\/[^/]+\/(preview\?path=|tree)/.test(url)||/^api\/project\/(preview\?path=|tree)/.test(url),url);}const w=deferred();e.requests.push({method,url,data,...w});return w.promise;},
    confirm:text=>{e.confirms.push(text);if(e.onConfirm)e.onConfirm();return e.confirmValue;},prompt:()=>{if(e.promptValue===undefined)throw Error('移到入口不该弹原因框');return e.promptValue;},toast:s=>e.toasts.push(String(s)),
    shown:p=>p.startsWith('@/')?p.slice(2):'资料/'+c.cur+'/'+p,rawUrl:(name,p)=>'files/'+name+'/'+p,
    previewBody:p=>({body:'<article>'+esc(p.text)+'</article>',wide:!!p.wide}),pvWrap:s=>s,fmtSize:s=>String(s),fmtTime:s=>String(s),govButton:()=>'',stickyNoteIcon:()=>'<svg></svg>',
    act:(array,x)=>array.push(x),zkey:(m,p)=>m+'|'+p,fileHash:p=>c.location.hash='#/m/'+c.cur+'?f='+encodeURIComponent(p),landOn:(name,p)=>c.MV.shown=p,modHref:name=>'#/m/'+name,
    appendNote(){},openLocal(){},renderTree:m=>{e.renderedTrees.push(c.MV.tree);},moduleOverviewEnabled:()=>false,isModuleOverviewPath:p=>p==='#模块总览',moduleDefaultFile:()=> 'another.md',moduleOverviewPath:()=> '#模块总览',renderIntro:()=>e.modview.innerHTML='<p>Intro</p>',
    openItem:p=>e.opened.push(p),zenOn:()=>false,zenLand(){},zenPos(){},zenPrefetch(){},pnodes:xs=>xs.map(x=>'<span>'+esc(x.name)+'</span>').join('')};
  c.window=c;vm.createContext(c);vm.runInContext(code,c);e.c=c;e.eval=s=>vm.runInContext(s,c);e.call=(fn,...args)=>c[fn](...args);e.node=(selector,scope=e.modview)=>scope.querySelector(selector);
  e.leave=()=>{c.invalidateModuleReading();c.fileDeleteRelease();c.view='settings';c.cur=null;c.location.hash='#/settings';};
  e.root=()=>{c.S={...c.S,project:{root:'C:/Synthetic/Beta',name:'Beta'}};c.moduleReadProjectChanged();c.fileDeleteProjectChanged();};
  return e;
}
const tick=()=>new Promise(a=>setImmediate(a));async function until(fn){for(let i=0;i<30&&!fn();i++)await tick();assert.ok(fn(),'Expected production awaited operation');}
async function readModule(e,p=preview(),file='子/旧稿.md'){const pending=e.call('showFile',file);e.requests.at(-1).resolve(p);await pending;return e.node('[data-file-inbox]');}
async function readProject(e,p=preview(),file=canonical){const pending=e.call('previewProject',file);e.requests.at(-1).resolve(p);await pending;return e.node('[data-file-inbox]',e.spv);}
async function movedModule(e,button,r=result()){const pending=e.call('fileInboxRequest',button);e.requests.at(-1).resolve(r);await until(()=>e.requests.at(-1).method==='GET'&&e.requests.at(-1).url.endsWith('/tree'));e.requests.at(-1).resolve({items:[],name:'A'});return pending;}
const posts=e=>e.requests.filter(x=>x.method==='POST');

test('button hidden when the file is not applicable; delete stays where it was',async()=>{for(const patch of [{inbox_action:undefined},{inbox_action:inbox({applicable:false,allowed:false})},{inbox_action:null}]){for(const scope of ['module','project']){const e=harness(scope),p=preview(patch);
  const button=scope==='module'?await readModule(e,p):await readProject(e,p),host=scope==='module'?e.modview:e.spv;assert.equal(button,null);assert.doesNotMatch(host.innerHTML,/data-file-inbox|移到入口/);assert.ok(host.querySelector('[data-file-delete]'));}}});
test('label, tooltip and placement: 移到入口 right after delete, enabled only with complete server metadata',async()=>{const e=harness(),button=await readModule(e);assert.equal(button.disabled,false);assert.match(e.modview.innerHTML,/data-file-delete[^>]*>删除<\/button><button class="sbtn" type="button" data-file-inbox title="移到外部资料入口，重新分拣；可以放回原处">移到入口<\/button>/);
  const ctx=button.fileInboxContext;assert.equal(ctx.slot,'fileInboxContext');assert.equal(e.call('fileDeleteCurrent',ctx),true);assert.deepEqual({...ctx.action},inbox());});
test('refused or incomplete metadata disables the button with the escaped server reason and cannot be bypassed',async()=>{
  for(const patch of [{allowed:false,reason:'「蓝图」是固定的治理模块 <script>x()</script>'},{module:''},{module:7},{folder:undefined},{path:'资料/B/子/旧稿.md'},{revision:'fake'},{project:'C:/Wrong'},{path:'../outside'},{applicable:'yes'}]){
    const e=harness(),button=await readModule(e,preview({inbox_action:inbox(patch)}));if(patch.applicable){assert.equal(button,null);continue;}
    assert.equal(button.disabled,true,JSON.stringify(patch));assert.equal(await e.call('fileInboxRequest',button),false);assert.equal(e.confirms.length,0);assert.equal(posts(e).length,0);assert.doesNotMatch(e.modview.innerHTML,/<script>/);
    if(patch.reason){assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(button.getAttribute('title'),patch.reason);assert.match(e.modview.innerHTML,/class="hint file-inbox-reason">「蓝图」是固定的治理模块 &lt;script&gt;/);}}});
test('cancel is zero writes; confirm names the real path, intake, the original place and 放回原处',async()=>{const e=harness(),button=await readModule(e),old=e.modview.innerHTML;e.confirmValue=false;const count=e.requests.length;
  assert.equal(await e.call('fileInboxRequest',button),false);assert.equal(e.requests.length,count);assert.equal(e.confirms.length,1);const text=e.confirms[0];
  assert.ok(text.includes('\n'+canonical+'\n'));assert.match(text,/外部资料入口（资料\/_外部资料入口\/）/);assert.match(text,/只动这 1 个文件/);assert.match(text,/原位置（A \/ 子）/);assert.match(text,/放回原处/);assert.equal(e.modview.innerHTML,old);assert.equal(button.disabled,false);
  const r=harness(),b=await readModule(r,preview({inbox_action:inbox({folder:''})}));r.confirmValue=false;await r.call('fileInboxRequest',b);assert.match(r.confirms[0],/原位置（A）/);});
test('POST sends exactly the server path/project/revision, no reason, roles or guessed fields',async()=>{const e=harness(),button=await readModule(e),pending=e.call('fileInboxRequest',button),req=e.requests.at(-1);
  assert.equal(req.method,'POST');assert.deepEqual({...req.data},{path:canonical,project:root.toLowerCase(),revision:version});req.reject(Error('文件在打开后发生变化，请重新阅读最新内容后再移动'));assert.equal(await pending,false);assert.match(e.toasts[0],/文件在打开后发生变化/);
  assert.equal(button.disabled,false);assert.equal(e.node('[data-file-delete]').disabled,false);assert.match(e.modview.innerHTML,/保留的原文/);assert.equal(e.c.MV.sel,'子/旧稿.md');});
test('double click sends one POST; delete is disabled and refused meanwhile; module watcher sees file-delete-pending',async()=>{const e=harness(),button=await readModule(e),old=e.modview.innerHTML,pending=e.call('fileInboxRequest',button),deleteButton=e.node('[data-file-delete]');
  assert.equal(button.disabled,true);assert.equal(deleteButton.disabled,true);assert.equal(await e.call('fileInboxRequest',button),false);assert.equal(await e.call('fileDeleteRequest',deleteButton),false);
  deleteButton.disabled=false;assert.equal(await e.call('fileDeleteRequest',deleteButton),false,'shared key also blocks delete');assert.equal(posts(e).length,1);assert.equal(e.modview.innerHTML,old);
  const count=e.requests.length,watch=await e.call('showModule');assert.equal(watch.scope,'file-delete-pending');assert.equal(e.requests.length,count);
  e.requests.at(-1).resolve(result());await until(()=>e.requests.at(-1).url.endsWith('/tree'));e.requests.at(-1).resolve({items:[]});assert.equal(await pending,true);assert.match(e.modview.innerHTML,/已移到外部资料入口/);});
test('delete in flight keeps the intake button from sending',async()=>{const e=harness(),button=await readModule(e);e.eval('FILE_DELETE.inflight.add(JSON.stringify([fileDeleteRoot('+JSON.stringify(root)+'),'+JSON.stringify(canonical)+']))');
  assert.equal(await e.call('fileInboxRequest',button),false);assert.equal(e.confirms.length,0);const again=await readModule(e);assert.equal(again.disabled,true);});
test('stale context changes inside the native confirm never send the move',async()=>{for(const change of ['root','view','path','hash','serial','host']){const e=harness(),button=await readModule(e);
  e.onConfirm=()=>{if(change==='root')e.root();else if(change==='view')e.leave();else if(change==='path')e.c.MV.sel='other.md';else if(change==='hash')e.c.location.hash='#/other';else if(change==='serial')e.eval('++FILE_DELETE.serial');else{e.modview.remove();const n=new Element();n.id='modview';e.body.appendChild(n);}};
  assert.equal(await e.call('fileInboxRequest',button),false,change);assert.equal(posts(e).length,0,change);}});
test('late success or failure after navigation changes neither the new page nor toasts',async()=>{for(const kind of ['success','error']){const e=harness(),button=await readModule(e),pending=e.call('fileInboxRequest',button),req=e.requests.at(-1);
  e.root();e.modview.innerHTML='<input value="other project">';if(kind==='success')req.resolve(result());else req.reject(Error('old error'));assert.equal(await pending,false);
  assert.match(e.modview.innerHTML,/other project/);assert.equal(e.toasts.length,0);assert.equal(e.requests.length,2);assert.equal(e.eval('FILE_DELETE.inflight.size'),0);}});
test('module success leaves an intake card, clears selection and this root\'s cache, refreshes tree, opens nothing, and the card survives later refreshes',async()=>{const e=harness(),button=await readModule(e),file=e.c.MV.sel;
  e.c.PCACHE[JSON.stringify([root,'A',file])]='old';e.c.PCACHE[JSON.stringify(['C:/Other','A',file])]='other';assert.equal(await movedModule(e,button),true);
  assert.match(e.modview.innerHTML,/已移到外部资料入口，可以放回原处/);assert.match(e.modview.innerHTML,/href="#\/inbox">去外部资料入口分拣或放回</);assert.match(e.modview.innerHTML,/#7 · 资料\/_外部资料入口\/旧稿\.md/);assert.match(e.modview.innerHTML,/原位置：A \/ 子/);assert.match(e.modview.innerHTML,/志-0042/);
  assert.ok(e.node('[data-file-inbox-result]'));assert.equal(e.c.MV.sel,null);assert.equal(e.c.MV.shown,null);assert.equal(e.c.LASTFILE.A,undefined);assert.equal(e.c.PCACHE[JSON.stringify([root,'A',file])],undefined);assert.equal(e.c.PCACHE[JSON.stringify(['C:/Other','A',file])],'other');
  assert.equal(e.requests[2].url,'api/modules/A/tree');assert.equal(e.renderedTrees.length,1);assert.equal(e.opened.length,0);assert.equal(e.c.location.hash,'#/m/A');assert.equal(e.eval('FILE_DELETE.inflight.size'),0);
  const old=e.modview.innerHTML,later=e.call('showModule');e.requests.at(-1).resolve({items:[{name:'another',path:'another.md'}]});await later;assert.equal(e.modview.innerHTML,old);assert.equal(e.opened.length,0);assert.equal(e.call('fileDeleteHoldModule'),true);});
test('project success clears PV selection, keeps the card, refreshes the project tree and never opens another file',async()=>{const e=harness('project'),button=await readProject(e),pending=e.call('fileInboxRequest',button);e.requests.at(-1).resolve(result());
  await until(()=>e.requests.at(-1).url==='api/project/tree');assert.equal(e.c.PV.sel,'');assert.match(e.spv.innerHTML,/data-file-inbox-result/);e.requests.at(-1).resolve({name:'Alpha',items:[{name:'remaining.md'}]});assert.equal(await pending,true);
  assert.match(e.ptree.innerHTML,/remaining.md/);assert.match(e.spv.innerHTML,/去外部资料入口分拣或放回/);assert.equal(e.opened.length,0);assert.equal(e.requests.length,3);
  const f=harness('project'),b=await readProject(f),p=f.call('fileInboxRequest',b);f.requests.at(-1).resolve(result());await until(()=>f.requests.at(-1).url==='api/project/tree');f.requests.at(-1).reject(Error('断了'));assert.equal(await p,true);assert.match(f.toasts[0],/^文件已移到外部资料入口；目录刷新失败：断了/);});
test('an unconfirmed result keeps the page and buttons with an 未确认 toast',async()=>{for(const patch of [{from:'资料/A/别的.md'},{to:'资料/A/子/旧稿.md'},{to:undefined},{item:{id:'7',status:'waiting'}},{item:{id:7,status:'sorted'}},{item:undefined}]){const e=harness(),button=await readModule(e),old=e.modview.innerHTML,pending=e.call('fileInboxRequest',button);
  e.requests.at(-1).resolve(result(patch));assert.equal(await pending,false,JSON.stringify(patch));assert.equal(e.modview.innerHTML,old);assert.match(e.toasts[0],/未确认/);assert.equal(button.disabled,false);assert.equal(e.node('[data-file-delete]').disabled,false);assert.equal(e.c.MV.sel,'子/旧稿.md');}
  const x=harness(),b=await readModule(x),p=x.call('fileInboxRequest',b);x.requests.at(-1).resolve(null);assert.equal(await p,false);assert.match(x.toasts[0],/未确认/);});
test('warnings, log IDs, target names and original places are escaped',async()=>{const e=harness(),button=await readModule(e);await movedModule(e,button,result({warning:'<script>bad()</script>',log_id:'<img src=x>',to:'资料/_外部资料入口/<b>.md',back:{module:'A',folder:'<i>'}}));
  assert.doesNotMatch(e.modview.innerHTML,/<script>|<img|<b>|<i>/);assert.match(e.modview.innerHTML,/&lt;script&gt;/);assert.match(e.modview.innerHTML,/&lt;b&gt;\.md/);});
test('English wording for button, tooltip, confirm, card and errors',async()=>{const e=harness();e.lang='en';const button=await readModule(e);assert.match(e.modview.innerHTML,/>To Intake<\/button>/);assert.match(e.modview.innerHTML,/title="Move to Intake to re-sort; it can be put back where it was"/);
  e.confirmValue=false;await e.call('fileInboxRequest',button);assert.match(e.confirms[0],/Move this file to Intake/);assert.ok(e.confirms[0].includes(canonical));assert.match(e.confirms[0],/Put it back/);
  e.confirmValue=true;await movedModule(e,button);assert.match(e.modview.innerHTML,/Moved to Intake; it can be put back/);assert.match(e.modview.innerHTML,/Sort or put back in Intake/);
  const x=harness();x.lang='en';const b=await readModule(x),p=x.call('fileInboxRequest',b);x.requests.at(-1).resolve({});await p;assert.match(x.toasts[0],/unconfirmed/);});
test('template hooks are typeof-guarded inside showFile/previewProject and stay away from render/openItem/route',()=>{
  for(const [name,body] of [['showFile',entries.showFile],['previewProject',entries.previewProject]]){const calls=[...body.matchAll(/fileInbox\w+\(/g)];assert.equal(calls.length,2,name);
    for(const m of calls){const fn=m[0].slice(0,-1);assert.ok(body.includes("typeof "+fn+"==='function'?"+fn+'(')||body.includes("if(typeof "+fn+"==='function')"+fn+'('),name+' '+fn);}}
  assert.match(entries.showFile,/fileInboxButton\(p\.inbox_action\)/);assert.match(entries.showFile,/fileInboxBind\(mv,p\.inbox_action,'module',path,name,MODULE_READ\.serial\)/);assert.match(entries.previewProject,/fileInboxBind\(host,p\.inbox_action,'project',path,name,null\)/);
  assert.doesNotMatch(template,/function render\(s\)[\s\S]{0,320}fileInbox/);assert.doesNotMatch(template,/function openItem\(path, quiet\)[\s\S]{0,180}fileInbox/);assert.doesNotMatch(template,/function route\(\)[\s\S]{0,160}fileInbox/);
  assert.doesNotMatch(inboxBlock,/api\/files\/trash|prompt\(|next_task|role\s*:/);});
test('intake cards: 原位置 candidate is labelled 放回原处 and keeps its folder; others stay 放这里',()=>{
  const src=extract(template,'/* 外部资料入口卡片 renderCards */','/* 外部资料入口卡片 renderCards 结束 */'),body=new Element('body'),box=new Element('div'),hint=new Element('span');box.id='icards';hint.id='inbHint';body.appendChild(box);body.appendChild(hint);
  const c={S:{modules:[{name:'A'},{name:'论文'}]},INB:[result().item,{id:8,status:'waiting',name:'新.md',orig:'新.md',size:1,created_at:'2026-10-08T10:00',created_by:'人',candidates:[{module:'论文',conf:'中',reason:'像草稿',by:'agent:甲'}]}],
    $:s=>body.querySelector(s),esc,fmtSize:String,fmtTime:String,who:by=>by==='人'?'你':String(by||'').replace(/^agent:/,''),setToc(){}};
  c.INB[0]={...c.INB[0],size:3,created_at:'2026-10-08T09:00',created_by:'人'};vm.createContext(c);vm.runInContext(src+';renderCards();',c);
  const puts=box.querySelectorAll('[data-put]');assert.equal(puts.length,2);assert.equal(puts[0].dataset.put,'A');assert.equal(puts[0].dataset.folder,'子');
  assert.match(box.innerHTML,/data-folder="子">放回原处<\/button>/);assert.match(box.innerHTML,/data-folder="">放这里<\/button>/);assert.match(box.innerHTML,/<span class="who">原位置<\/span>/);assert.match(box.innerHTML,/原来是 资料\/A\/子\/旧稿\.md/);});
test('English dictionary covers the new intake words and refusal sentences',()=>{const w={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../界面英文.js'),'utf8'),{window:w});const U=w.UI_EN,D=U.dict;
  const en=s=>{if(Object.hasOwn(D,s))return D[s];let out=s;U.parts.forEach(r=>{out=out.replace(r[0],r[1]);});return out;};
  assert.equal(en('放回原处'),'Put it back');assert.equal(en('原位置'),'Original place');assert.equal(en('原来在这里'),'It was here');assert.equal(en('移到入口'),'To Intake');
  assert.doesNotMatch(Object.keys(D).join('\n'),/你点一个才放进模块/);assert.match(template,new RegExp(Object.keys(D).find(k=>k.startsWith('外面的材料扔进来')).replace(/[.*+?^${}()|[\]\\/]/g,'\\$&')));
  for(const s of ['「蓝图」是固定的治理模块（想法 · 蓝图 · 戒律 · 源代码），里面的文件不移到入口','「A」模块的 .链接.txt 挂着它（子）：挪走链接就断了；先改 .链接.txt 再移到入口','外部资料入口里已经有一份内容一模一样的「旧稿.md」（#3）在等分拣：先去入口处理那一份，或把这一份删掉','没挪成，文件还在原处：disk full','没放成，文件还在入口：disk full','「做法/子」里的「做法」是链接文件夹，不能当去向','文献解读（解读/）跟着原文走，由文献库管理，不移到入口','这个文件在项目外，不能从网页移动'])assert.doesNotMatch(en(s),/[\u3400-\u9fff]{3}/,s);});

test('each button checks that its context is still the one bound to it: a re-bound button makes the old context stale',async()=>{
  const e=harness(),button=await readModule(e),old=button.fileInboxContext,deleteButton=e.node('[data-file-delete]'),oldDelete=deleteButton.fileDeleteContext;
  assert.equal(e.call('fileDeleteCurrent',old),true);assert.equal(e.call('fileDeleteCurrent',oldDelete),true);
  e.eval("fileInboxBind($('#modview'),"+JSON.stringify(inbox())+",'module','子/旧稿.md','A',MODULE_READ.serial);fileDeleteBind($('#modview'),"+JSON.stringify(del())+",'module','子/旧稿.md','A',MODULE_READ.serial)");
  assert.notEqual(button.fileInboxContext,old);assert.notEqual(deleteButton.fileDeleteContext,oldDelete);
  assert.equal(e.call('fileDeleteCurrent',old),false,'old intake context must be stale once the button is re-bound');assert.equal(e.call('fileDeleteCurrent',oldDelete),false,'old delete context must be stale once the button is re-bound');
  assert.equal(e.call('fileDeleteCurrent',button.fileInboxContext),true);assert.equal(e.call('fileDeleteCurrent',deleteButton.fileDeleteContext),true);
  // 请求在路上时按钮被重新绑定：旧请求回来既不改页面也不弹提示，新绑定的那份照样能用
  const f=harness(),b=await readModule(f),html=f.modview.innerHTML,pending=f.call('fileInboxRequest',b),req=f.requests.at(-1);
  f.eval("fileInboxBind($('#modview'),"+JSON.stringify(inbox())+",'module','子/旧稿.md','A',MODULE_READ.serial)");assert.equal(b.disabled,true,'still in flight');
  req.resolve(result());assert.equal(await pending,false);assert.equal(f.modview.innerHTML,html);assert.equal(f.toasts.length,0);assert.equal(f.requests.length,2);assert.equal(f.eval('FILE_DELETE.inflight.size'),0);
  const g=harness(),d=await readModule(g),gp=g.call('fileInboxRequest',d),greq=g.requests.at(-1);g.eval("fileInboxBind($('#modview'),"+JSON.stringify(inbox())+",'module','子/旧稿.md','A',MODULE_READ.serial)");
  greq.reject(Error('old error'));assert.equal(await gp,false);assert.equal(g.toasts.length,0);});
test('delete in flight disables the intake button on the same page and restores it afterwards',async()=>{for(const outcome of ['error','unconfirmed']){const e=harness(),button=await readModule(e),deleteButton=e.node('[data-file-delete]');e.promptValue='放错了';
  const pending=e.call('fileDeleteRequest',deleteButton),req=e.requests.at(-1);assert.equal(req.url,'api/files/trash');assert.equal(deleteButton.disabled,true);assert.equal(button.disabled,true,'intake button disabled while delete is in flight');
  assert.equal(await e.call('fileInboxRequest',button),false);assert.equal(e.confirms.length,0);assert.equal(posts(e).length,1);
  if(outcome==='error')req.reject(Error('磁盘满'));else req.resolve({});assert.equal(await pending,false);assert.equal(e.toasts.length,1);
  assert.equal(button.disabled,false,'intake button restored');assert.equal(deleteButton.disabled,false);assert.equal(e.eval('FILE_DELETE.inflight.size'),0);}
  const r=harness(),refused=await readModule(r,preview({inbox_action:inbox({allowed:false,reason:'「A」模块的 .链接.txt 挂着它（子）：挪走链接就断了；先改 .链接.txt 再移到入口'})})),rd=r.node('[data-file-delete]');r.promptValue='放错了';
  const rp=r.call('fileDeleteRequest',rd);assert.equal(refused.disabled,true);r.requests.at(-1).reject(Error('x'));await rp;assert.equal(refused.disabled,true,'a refused intake button stays disabled');assert.equal(rd.disabled,false);
  const s=harness(),sb=await readModule(s),sd=s.node('[data-file-delete]');s.promptValue='放错了';const sp=s.call('fileDeleteRequest',sd),sreq=s.requests.at(-1);s.leave();sreq.reject(Error('late'));await sp;
  assert.equal(sb.disabled,true,'a stale page is left alone');assert.equal(s.toasts.length,0);});
test('refused without a server reason falls back to 这个文件不能移到入口',async()=>{for(const lang of ['zh','en']){for(const patch of [{allowed:false,reason:''},{revision:'fake'}]){const e=harness();e.lang=lang;const button=await readModule(e,preview({inbox_action:inbox(patch)})),want=lang==='en'?"This file can't be moved to the intake":'这个文件不能移到入口';
  assert.equal(button.disabled,true);assert.equal(button.getAttribute('title'),want);assert.equal(e.node('.file-inbox-reason').getAttribute('class'),'hint file-inbox-reason');assert.ok(e.modview.innerHTML.includes('>'+esc(want)+'</span>'));assert.doesNotMatch(e.modview.innerHTML,/阅读版本|file version/);}}});
function renderInbox(items){const src=extract(template,'/* 外部资料入口卡片 renderCards */','/* 外部资料入口卡片 renderCards 结束 */'),body=new Element('body'),box=new Element('div'),hint=new Element('span');box.id='icards';hint.id='inbHint';body.appendChild(box);body.appendChild(hint);
  const c={S:{modules:[{name:'A'},{name:'论文'}]},INB:items,$:s=>body.querySelector(s),esc,fmtSize:String,fmtTime:String,who:by=>by==='人'?'你':String(by||'').replace(/^agent:/,''),setToc(){}};vm.createContext(c);vm.runInContext(src+';renderCards();',c);return box;}
test('intake cards say 挪回来的 for items moved back from a module and 放进来的 otherwise',()=>{const moved={...result().item,size:3,created_at:'t',created_by:'人'},fresh={id:8,status:'waiting',name:'新.md',orig:'新.md',size:1,created_at:'t',created_by:'人',candidates:[{module:'论文',conf:'中',reason:'像草稿',by:'agent:甲'}]};
  const box=renderInbox([moved,fresh,{...moved,id:9,created_by:'agent:甲'},{...fresh,id:10,candidates:[]}]),metas=box.querySelectorAll('.meta').map(m=>m.parentNode.dataset.id);assert.deepEqual(metas,['7','8','9','10']);
  const cards=box.innerHTML.split('<div class="icard"').slice(1);assert.match(cards[0],/ · 你挪回来的 · 原来是 资料\/A\/子\/旧稿\.md/);assert.doesNotMatch(cards[0],/放进来的/);assert.match(cards[1],/ · 你放进来的/);assert.doesNotMatch(cards[1],/挪回来的/);
  assert.match(cards[2],/ · 甲挪回来的/);assert.match(cards[3],/ · 你放进来的/);});
test('sorting shows the server warning as a toast when the log entry failed',async()=>{const src=extract(template,'async function sortItem(','function sortingPrompt()');
  for(const [reply,want] of [[{items:[],warning:'已经放进去了，日志写入失败'},'已经放进去了，日志写入失败'],[{items:[{id:2}]},'已放进 资料/A/子/'],[{items:[]},'已放进 资料/论文/']]){
    const calls=[],toasts=[],acts=[],c={api:async(method,url,data)=>{calls.push({method,url,data});return reply;},toast:s=>toasts.push(s),act:(a,x)=>acts.push(x),ACT:{sorted:'sorted'},INB:null,renderCards(){c.rendered=(c.rendered||0)+1;}};
    vm.createContext(c);vm.runInContext(src,c);const folder=want.includes('子')?'子':'';await c.sortItem({id:7,name:'旧稿.md'},folder?'A':'论文',folder);
    assert.deepEqual(calls.map(x=>[x.method,x.url,{...x.data}]),[['POST','api/inbox/7/sort',{module:folder?'A':'论文',folder}]]);assert.deepEqual(toasts,[want]);assert.equal(c.INB,reply.items);assert.equal(c.rendered,1);assert.equal(acts.length,1);}});
test('English dictionary covers move refusals rewritten from the delete checks, the moved-back wording and the sort warning',()=>{const w={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../界面英文.js'),'utf8'),{window:w});const U=w.UI_EN,D=U.dict;
  const en=s=>{if(Object.hasOwn(D,s))return D[s];let out=s;U.parts.forEach(r=>{out=out.replace(r[0],r[1]);});return out;};
  for(const s of ['这里只能移动单个文件，不能移动文件夹或整个模块','隐藏文件夹和运行缓存不能在文件阅读页移动','符号链接或目录联接只能阅读，不能在这里移动原件','移动路径必须是当前项目内的相对路径','移动路径不能越界或使用路径别名',
    '读取期间文件或路径发生变化，请重新打开后再移动','文件的上级路径不是普通文件夹','这个文件不能移到入口','已经放进去了，日志写入失败'])
    {assert.ok(Object.hasOwn(D,s),s);assert.doesNotMatch(en(s),/[㐀-鿿]/,s);}
  assert.equal(en('这个文件不能移到入口'),"This file can't be moved to the intake");assert.equal(en('你挪回来的'),'moved back by you');assert.equal(en('甲挪回来的'),'moved back by 甲');assert.equal(en('你放进来的'),'added by you');
  assert.equal(en('3 · t · 你挪回来的 · 原来是 资料/A/子/旧稿.md'),'3 · t · moved back by you · originally 资料/A/子/旧稿.md');
  // agent 分拣被拒：文案照 backend/intake.py 的 governed + _agent_may_place
  const intake=fs.readFileSync(path.join(__dirname,'../intake.py'),'utf8');assert.ok(intake.includes('：agent 不能直接分拣到「{where}」。要放这类位置请让人在网页上点'),'intake.py wording changed; update 界面英文.js');
  const whys=[...intake.slice(intake.indexOf('def governed('),intake.indexOf('def _agent_may_place(')).matchAll(/return f?"([^"]+)"/g)].map(m=>m[1].replace('{module}','蓝图'));assert.equal(whys.length,6);
  for(const why of whys){const out=en(why+'：agent 不能直接分拣到「蓝图/S1-9 新目标.md」。要放这类位置请让人在网页上点');assert.match(out,/agents cannot sort directly into “蓝图\/S1-9 新目标\.md”\. For a place like this, ask a person/,why);
    assert.doesNotMatch(out.replace('蓝图/S1-9 新目标.md','').replace(/“蓝图”/,'').replace(/\((技能|解读)\/\)|\.链接\.txt/,''),/[\u3400-\u9fff]{2}/,why);}
  assert.match(en('「蓝图」是固定的治理模块（想法 · 蓝图 · 戒律 · 源代码）：agent 不能直接分拣到「蓝图」。要放这类位置请让人在网页上点'),/^“蓝图” is a fixed governance module \(Ideas · Blueprint · Rules · Code\): agents cannot sort/);});
