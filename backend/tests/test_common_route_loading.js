'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const full=fs.readFileSync(process.env.MH_COMMON_SOURCE||path.join(__dirname,'../../模板.html'),'utf8');
const range=(a,b)=>{const i=full.indexOf(a),j=full.indexOf(b,i);assert.ok(i>=0&&j>i,a);return full.slice(i,j);};
const common=range('/* ================= 通用读取事务 Common route reading ================= */','/* ================= 通用读取事务 Common route reading 结束 ================= */');
const plans=range('/* ================= 计划 Plans：','/* ================= 技能 Skills：');
const skills=range('/* ================= 技能 Skills：','/* ================= 问答 Q&A：');
const auto=range('async function showAuto() {','function asec(');
const terminal=range('async function showTerm(',"addEventListener('message'");
const queue=range('function queueAutoRefresh()', 'setInterval(function(){if(view');
const refreshOrders=range('async function refreshAutoToc()', 'function wsec(');
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
class Element{
  constructor(tag='div',id=''){this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.parentNode=null;this.dataset={};this.attributes={};this.listeners={};this._html='';this.writeCount=0;this.scrollTop=0;this.value='';}
  get isConnected(){return this.tagName==='BODY'||!!(this.parentNode&&this.parentNode.isConnected);}
  get firstElementChild(){return this.children[0]||null;}
  get innerHTML(){return this._html+this.children.filter(n=>!n.placeholder).map(n=>n.outerHTML).join('');}
  set innerHTML(value){this._html=String(value);++this.writeCount;this.children.forEach(c=>c.parentNode=null);this.children=[];
    for(const m of this._html.matchAll(/<([a-z]+)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)){const n=new Element(m[1],m[3]);n.placeholder=true;for(const a of m[2].matchAll(/([\w-]+)="([^"]*)"/g))n.setAttribute(a[1],a[2].replaceAll('&amp;','&'));this.appendChild(n);}}
  get outerHTML(){return '<'+this.tagName.toLowerCase()+Object.entries(this.attributes).map(([k,v])=>' '+k+'="'+v+'"').join('')+'>'+this.innerHTML+'</'+this.tagName.toLowerCase()+'>';}
  setAttribute(k,v){this.attributes[k]=String(v);if(k==='id')this.id=String(v);}getAttribute(k){return this.attributes[k]||null;}
  appendChild(n){if(n.parentNode)n.remove();n.parentNode=this;this.children.push(n);return n;}
  remove(){if(this.parentNode){this.parentNode.children.splice(this.parentNode.children.indexOf(this),1);this.parentNode=null;}}
  contains(n){return this===n||this.children.some(c=>c.contains(n));}
  addEventListener(k,f){(this.listeners[k]??=[]).push(f);}
  querySelector(s){return this.querySelectorAll(s)[0]||null;}
  querySelectorAll(s){const out=[];const walk=n=>n.children.forEach(c=>{if(s[0]==='#'&&c.id===s.slice(1))out.push(c);walk(c);});walk(this);return out;}
}
function fixture(mode='plans'){
  const e={requests:[],completed:[],failed:[],waits:[],timers:new Map(),hold:false,reduced:false,typing:false,boards:0,dashboards:0,toasts:[],body:new Element('body')};
  for(const id of ['toc','planview','skillsview','autoview'])e.body.appendChild(new Element('div',id));
  const storage=new Map();let timer=0;
  const c={console,Map,Set,WeakMap,URL,JSON,Promise,encodeURIComponent,view:mode,online:true,S:{project:{root:'C:/Synthetic/A',name:'Synthetic'}},location:{hash:'#/'+mode,origin:'http://127.0.0.1:18770'},
    document:{body:e.body,title:'',activeElement:null,documentElement:{dataset:{theme:'dark'}},createElement:t=>new Element(t)},
    $:s=>e.body.querySelector(s),window:null,history:{replaceState:(a,b,h)=>{c.location.hash=h;}},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
    getLang:()=>c.language||'zh',esc:s=>String(s??'').replace(/[&<>"]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[x])),uiIcon:()=>'',
    readingFlames:(zh,en)=>'<span class="flames">'+(c.language==='en'?en:zh)+'</span>',
    completeReading:async host=>{assert.ok(host.isConnected);e.completed.push(host);if(e.hold&&!e.reduced){const w=deferred();e.waits.push(w);await w.promise;}},
    failReading:(host,zh,en)=>{e.failed.push(host);host.innerHTML='<span role="alert">'+c.esc(c.language==='en'?en:zh)+'</span>';},
    api:(method,url)=>{assert.equal(method,'GET');const w=deferred();e.requests.push({method,url,...w});return w.promise;},
    toast:x=>e.toasts.push(x),setToc:(a,b,text)=>{c.$('#toc').innerHTML=text||a;},renderMd:t=>'MD:'+t,govButton:()=>'',previewBody:p=>({body:p.text}),pvWrap:x=>x,purl:x=>x,
    ordGet:()=>e.order||'time',ordSet:(k,v)=>{e.order=v;},ordSeg:()=>'<button>Sort</button>',dayName:x=>x,zenOn:()=>false,zenPos(){},
    appendNote(){throw Error('Unexpected note');},installThing(){throw Error('Unexpected installation');},autoTyping:()=>e.typing,
    AUSEL:'s:board',AUSERIAL:0,AUWAIT:false,ADERR:[],ADUPDATED:'',AUTOFRESH:null,WD:null,GD:null,AT:[],AJ:[],ATOOLS:[],AG:{items:[]},WL:{items:[]},AB:{items:[]},AU:{runs:[],workflows:[],handovers:[]},ADL:{on:false},
    WOPEN:null,WPICK:null,WOPT:null,WTARGET:false,WMSG:'',TERMP:'网页终端',TERM:{url:'',ready:false,queue:[]},innerHeight:1000,matchMedia:()=>({matches:false}),
    AutoDashboard:{dispose(){}},moduleOverviewEnabled:()=>e.overview||false,mountAutoDashboard:v=>{++e.dashboards;v.innerHTML='ACTUAL_DASHBOARD';},renderAutoToc:()=>{c.$('#toc').innerHTML='ACTUAL_AUTO_DIRECTORY';},
    boardHtml:()=>{++e.boards;return'ACTUAL_BOARD';},gkey:r=>'g:'+r.code,apage:()=>'',launchPanel:()=>'<p>Actual launch</p>',orgHtml:()=>'',unregHtml:()=>'',itemHtml:d=>d.text,taskHtml:d=>d.text,
    jobHtml:(x,tl)=>x.text+' '+tl.length,woHtml:()=>c.WD.wo.code,ordersHome:()=>'',reviewHome:()=>'',gitTable:()=>'',woNewHtml:()=>'',agentNewHtml:()=>'',runLamp:()=>'',loadFreeze(){},
    setTimeout:f=>{e.timers.set(++timer,f);return timer;},clearTimeout:n=>e.timers.delete(n),addEventListener(){}};
  c.window=c;c.scrollTo=()=>{};vm.createContext(c);vm.runInContext(common+plans+skills+queue+terminal+auto+refreshOrders,c);
  e.c=c;e.run=s=>vm.runInContext(s,c);e.call=(name,...args)=>c[name](...args);e.node=id=>c.$('#'+id);
  e.navigate=(page,hash='#/'+page)=>{c.invalidateCommonReading();c.view=page;c.location.hash=hash;};
  e.root=root=>{c.S={project:{root,name:root}};};e.flush=()=>{const callbacks=[...e.timers.values()];e.timers.clear();callbacks.forEach(f=>f());};return e;
}
const tick=()=>new Promise(setImmediate);
async function until(f){for(let i=0;i<30&&!f();i++)await tick();assert.ok(f());}
const plan=(path='a.md')=>({path,title:path,code:'P1',goal:'S1-1 Synthetic',date:'2026-10-06',mtime:1});
async function resolvePlan(e,work,text='Actual plan'){
  const list=e.requests.find(r=>r.url==='api/plans');list.resolve({items:[plan(),plan('b.md')]});await until(()=>e.requests.some(r=>r.url.includes('preview')));e.requests.at(-1).resolve({text});await work;
}
const skill=(id='one')=>({id,kind:'skill',title:{'zh-CN':id},name:id,available:true,package_revision:'1',languages:{'zh-CN':'SKILL.md',en:'SKILL.en.md'},issues:[]});
function autoData(url){return url==='api/auto'?{runs:[],workflows:[],handovers:[]}:url==='api/workorders'?{items:[],running:null}:url==='api/agents'?{items:[],protocol:'# Rules\nactual'}:url==='api/auto/launch'?{on:true,windows:[],status:[],plans:[]}:url==='api/board'?{items:[]}: {items:[]};}
function resolveAuto(e,start=0){for(const r of e.requests.slice(start,start+8))r.resolve(autoData(r.url));}

test('plan directory and body flames follow actual responses; file and sort reuse only successful same-root directory',async()=>{
  const e=fixture(),work=e.call('showPlans');assert.match(e.node('toc').innerHTML,/正在读取计划目录/);assert.match(e.node('planview').innerHTML,/正在读取计划页面/);assert.equal(e.requests.length,1);
  await resolvePlan(e,work);assert.equal(e.completed.length,2);assert.match(e.node('planview').innerHTML,/Actual plan/);
  e.run("PLAN='b.md'");const second=e.call('showPlans',{reuseDirectory:true});assert.equal(e.requests.length,3);assert.match(e.requests[2].url,/b.md/);e.requests[2].resolve({text:'B'});await second;
  e.order='structure';const sort=e.call('showPlans',{reuseDirectory:true});assert.equal(e.requests.filter(r=>r.url==='api/plans').length,1);e.requests.at(-1).resolve({text:'B'});await sort;
  const fresh=e.call('showPlans');assert.equal(e.requests.filter(r=>r.url==='api/plans').length,2);e.requests[4].resolve({items:[plan(),plan('b.md')]});await until(()=>e.requests.length===6);e.requests[5].resolve({text:'Fresh'});await fresh;
});
test('plan old result cannot write after page/root/hash/selection/host changes or leaving and returning same route',async()=>{
  for(const change of ['view','root','hash','selection','host','return']){const e=fixture(),work=e.call('showPlans');
    if(change==='view')e.navigate('skills');if(change==='root')e.root('C:/Synthetic/B');if(change==='hash')e.c.location.hash='#/plans?p=b.md';if(change==='selection')e.run("PLAN='b.md'");
    if(change==='host'){e.node('planview').remove();e.body.appendChild(new Element('div','planview'));}if(change==='return'){e.navigate('skills');e.navigate('plans');}
    const writes=e.node('toc').writeCount;e.requests[0].resolve({items:[plan()]});await work;assert.equal(e.node('toc').writeCount,writes);assert.equal(e.requests.length,1);assert.equal(e.completed.length,0);
  }
});
test('plan convergence is guarded again after switching during directory or body animation',async()=>{
  for(const phase of ['directory','body']){const e=fixture();e.hold=true;const work=e.call('showPlans');e.requests[0].resolve({items:[plan()]});await until(()=>e.waits.length===1);
    if(phase==='body'){e.waits[0].resolve();await until(()=>e.requests.length===2);e.requests[1].resolve({text:'old'});await until(()=>e.waits.length===2);}
    e.navigate('skills');const writes=e.node('toc').writeCount;e.waits.at(-1).resolve();await work;assert.equal(e.node('toc').writeCount,writes);assert.doesNotMatch(e.node('planview').innerHTML,/MD:old/);
  }
});
test('plan failures are truthful and directory success is not relabeled as failure when preview fails',async()=>{
  const e=fixture(),work=e.call('showPlans');e.requests[0].reject(Error('list failed'));await work;assert.equal(e.completed.length,0);assert.equal(e.failed.length,2);
  const f=fixture(),body=f.call('showPlans');f.requests[0].resolve({items:[plan()]});await until(()=>f.requests.length===2);f.requests[1].reject(Error('text failed'));await body;assert.equal(f.completed.length,1);assert.equal(f.failed.length,1);
});
test('skills catalog ownership rejects stale page/root/hash and completion continuations',async()=>{
  for(const change of ['root','hash','return','animation']){const e=fixture('skills');e.hold=change==='animation';const work=e.call('showSkills');
    if(change==='animation'){e.requests[0].resolve({items:[skill()],groups:[]});await until(()=>e.waits.length===2);}
    if(change==='root')e.root('C:/Synthetic/B');else if(change==='hash')e.c.location.hash='#/skills?s=two';else{e.navigate('plans');e.navigate('skills');}
    if(change==='animation')e.waits.forEach(w=>w.resolve());else e.requests[0].resolve({items:[skill()],groups:[]});await work;assert.equal(e.run('SK.length'),0);
  }
});
test('skills Chinese text converges only after real text and cannot overwrite selected English or a new root',async()=>{
  const e=fixture('skills'),catalog=e.call('showSkills');e.requests[0].resolve({items:[skill()],groups:[]});await catalog;
  e.run("SKSEL='one'");const zh=e.call('renderSkills');e.run("SKLANG='en'");const en=e.call('renderSkills');e.requests[2].resolve({text:'English actual'});await en;e.requests[1].resolve({text:'中文旧响应'});await zh;
  assert.equal(e.node('skbody').innerHTML,'MD:English actual');e.hold=true;e.run("SKLANG='zh-CN'");const old=e.call('renderSkills');e.requests[3].resolve({text:'old root'});await until(()=>e.waits.length===1);e.root('C:/Synthetic/B');e.waits[0].resolve();await old;assert.doesNotMatch(e.node('skbody').innerHTML,/old root/);
});
test('skills current failure plays failure rather than success and detached detail has no effects',async()=>{
  const e=fixture('skills'),list=e.call('showSkills');e.requests[0].reject(Error('manifest failure'));await list;assert.equal(e.completed.length,0);assert.equal(e.failed.length,2);
  const f=fixture('skills'),catalog=f.call('showSkills');f.requests[0].resolve({items:[skill()],groups:[]});await catalog;f.run("SKSEL='one'");const text=f.call('renderSkills');f.requests[1].reject(Error('text failure'));await text;assert.match(f.node('skbody').innerHTML,/role="alert".*text failure/);assert.equal(f.completed.length,2);
});
test('auto first entry immediately displays fixed navigation and real reading, waiting for all eight facts',async()=>{
  const e=fixture('auto');e.node('toc').innerHTML='OLD_SKILLS_DIRECTORY';const work=e.call('showAuto');assert.match(e.node('toc').innerHTML,/data-auto="s:term"/);assert.doesNotMatch(e.node('toc').innerHTML,/OLD_SKILLS|未允许|>0</);assert.equal(e.boards,0);
  e.requests.slice(0,7).forEach(r=>r.resolve(autoData(r.url)));await tick();assert.equal(e.boards,0);assert.equal(e.completed.length,0);e.requests[7].resolve(autoData(e.requests[7].url));await work;assert.equal(e.boards,1);assert.equal(e.completed.length,2);
});
test('auto background burst shares in-flight work and schedules one trailing refresh; direct write-followup is never swallowed',async()=>{
  const e=fixture('auto'),work=e.call('showAuto'),bursts=Array.from({length:10},()=>e.call('showAuto',{background:true}));assert.equal(e.requests.length,8);resolveAuto(e);await Promise.all([work,...bursts]);assert.equal(e.timers.size,1);e.flush();assert.equal(e.requests.length,16);resolveAuto(e,8);await until(()=>e.c.showAuto.active===null);
  const a=e.call('showAuto',{background:true}),b=e.call('showAuto');assert.equal(e.requests.length,32);resolveAuto(e,24);await b;resolveAuto(e,16);await a;assert.equal(e.boards,3);
});
test('auto route/root/selection and completion guards reject stale body, directory and errors',async()=>{
  for(const change of ['root','hash','selection','return','animation']){const e=fixture('auto');e.hold=change==='animation';const work=e.call('showAuto');
    if(change==='animation'){resolveAuto(e);await until(()=>e.waits.length===1);}
    if(change==='root')e.root('C:/Synthetic/B');else if(change==='hash')e.c.location.hash='#/auto?s=orders';else if(change==='selection')e.c.AUSEL='s:orders';else{e.navigate('plans');e.navigate('auto');}
    if(change==='animation')e.waits[0].resolve();else resolveAuto(e);await work;assert.equal(e.boards,0);assert.equal(e.toasts.length,0);
  }
});
test('auto initial partial failures never invent zero facts or a disabled dashboard',async()=>{
  const e=fixture('auto');e.overview=true;e.c.AUSEL='s:home';const work=e.call('showAuto');e.requests.forEach(r=>r.url==='api/board'?r.reject(Error('board failed')):r.resolve(autoData(r.url)));await work;assert.equal(e.dashboards,0);assert.equal(e.completed.length,0);assert.equal(e.failed.length,2);assert.match(e.node('autoview').innerHTML,/board failed/);
});
test('background completion preserves typing begun while pending and queues a real future refresh',async()=>{
  const e=fixture('auto'),v=e.node('autoview');v.autoReadingPage={root:'C:/Synthetic/A',selected:'s:board'};const input=new Element('input');input.value='unsaved';v.appendChild(input);const work=e.call('showAuto',{background:true});e.typing=true;resolveAuto(e);await work;assert.ok(v.contains(input));assert.equal(input.value,'unsaved');assert.equal(e.boards,0);assert.equal(e.c.AUWAIT,true);
});
test('terminal keeps the same iframe during refresh and a stale terminal result cannot mount',async()=>{
  const e=fixture('auto');e.c.AUSEL='s:term';const work=e.call('showAuto');resolveAuto(e);await until(()=>e.requests.length===10);e.requests[8].resolve([{name:'网页终端',ok:true,enabled:true,running:true,url:'http://127.0.0.1:18771/term?x=1'}]);e.requests[9].resolve(autoData('api/auto/launch'));await work;const frame=e.node('termFrame');assert.ok(frame);
  const next=e.call('showAuto',{background:true});resolveAuto(e,10);await until(()=>e.requests.length===20);e.requests[18].resolve([{name:'网页终端',ok:true,enabled:true,running:true,url:'http://127.0.0.1:18771/term?x=1'}]);e.requests[19].resolve(autoData('api/auto/launch'));await next;assert.equal(e.node('termFrame'),frame);
  const late=e.call('showTerm',e.node('autoview'));e.navigate('plans');e.requests[20].resolve([]);e.requests[21].resolve(autoData('api/auto/launch'));await late;assert.equal(e.node('termFrame'),frame);
});
test('body convergence rechecks auto identity and never paints after another selection, root or host',async()=>{
  for(const change of ['root','selection','host','return']){const e=fixture('auto');e.hold=true;const work=e.call('showAuto');resolveAuto(e);await until(()=>e.waits.length===1);e.waits[0].resolve();await until(()=>e.waits.length===2);
    if(change==='root')e.root('C:/Synthetic/B');if(change==='selection')e.c.AUSEL='s:orders';if(change==='host'){e.node('autoview').remove();e.body.appendChild(new Element('div','autoview'));}if(change==='return'){e.navigate('plans');e.navigate('auto');}
    e.waits[1].resolve();await work;assert.equal(e.boards,0);
  }
});
test('invalid plan, skill or automation payload fails before any success animation',async()=>{
  for(const mode of ['plans','skills','auto']){const e=fixture(mode),work=e.call(mode==='plans'?'showPlans':mode==='skills'?'showSkills':'showAuto');
    if(mode==='auto')e.requests.forEach(r=>r.resolve(r.url==='api/board'?{items:'invalid'}:autoData(r.url)));else e.requests[0].resolve({items:'invalid'});
    await work;assert.equal(e.completed.length,0);assert.ok(e.failed.length>=1);
  }
});
test('existing PaneSpirit completion interface respects immediate reduced-motion settlement without request timers',async()=>{
  const e=fixture();e.reduced=true;e.hold=true;const work=e.call('showPlans');await resolvePlan(e,work);assert.equal(e.waits.length,0);assert.equal(e.timers.size,0);assert.equal(e.completed.length,2);
});
test('late handover detail or work-order directory cannot update a different route',async()=>{
  const e=fixture('auto');e.c.AUSEL='h:H1';const work=e.call('showAuto');e.requests.forEach(r=>r.resolve(r.url==='api/auto'?{runs:[],workflows:[],handovers:[{code:'H1'}]}:autoData(r.url)));await until(()=>e.requests.length===9);e.navigate('plans');e.requests[8].reject(Error('old handover'));await work;assert.equal(e.failed.length,0);assert.equal(e.toasts.length,0);
  const f=fixture('auto'),directory=f.call('refreshAutoToc');f.navigate('skills');f.requests[0].resolve({items:[{code:'K1'}]});await directory;assert.equal(f.c.WL.items.length,0);assert.equal(f.completed.length,0);
});
test('background typing begun during body convergence preserves the input after the animation',async()=>{
  const e=fixture('auto'),v=e.node('autoview');v.autoReadingPage={root:'C:/Synthetic/A',selected:'s:board'};const input=new Element('input');input.value='unsaved after animation';v.appendChild(input);e.hold=true;
  const work=e.call('showAuto',{background:true});resolveAuto(e);await until(()=>e.waits.length===1);e.waits[0].resolve();await until(()=>e.waits.length===2);
  e.typing=true;e.waits[1].resolve();await work;assert.ok(v.contains(input));assert.equal(input.value,'unsaved after animation');assert.equal(e.boards,0);assert.equal(e.c.AUWAIT,true);
});
test('terminal background second GET and convergence both preserve newly typed input',async()=>{
  for(const phase of ['second-get','animation']){const e=fixture('auto'),v=e.node('autoview');e.c.AUSEL='s:term';v.autoReadingPage={root:'C:/Synthetic/A',selected:'s:term'};const input=new Element('input');input.value='terminal draft';v.appendChild(input);e.hold=phase==='animation';
    const work=e.call('showAuto',{background:true});resolveAuto(e);if(e.hold){await until(()=>e.waits.length===1);e.waits[0].resolve();}await until(()=>e.requests.length===10);
    if(phase==='second-get')e.typing=true;e.requests[8].resolve([{name:'网页终端',ok:true,enabled:true,running:true,url:'http://127.0.0.1:18771/term?x=1'}]);e.requests[9].resolve(autoData('api/auto/launch'));
    if(phase==='animation'){await until(()=>e.waits.length===2);e.typing=true;e.waits[1].resolve();}await work;
    assert.ok(v.contains(input));assert.equal(input.value,'terminal draft');assert.equal(e.c.AUWAIT,true);assert.equal(e.node('termFrame'),null);
  }
});
