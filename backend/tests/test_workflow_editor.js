'use strict';
// Pure graph rules and the editor's actual DOM handlers. No employee is launched.
const test=require('node:test');
const assert=require('node:assert/strict');
const editor=require('../../流程编辑器.js');
const ROOT='C:/temporary/nonresearch-workflow';
const context=()=>({online:false,state:{project:{root:ROOT,name:'资料整理'}},board:{items:[
  {key:'S1-1 S2-1',what:'整理清单',col:'能做'}, {key:'S1-2 S2-1',what:'核对来源',col:'在做'}]},
  roster:[{code:'G1',name:'施工甲',roles:['干活']},{code:'G2',name:'统筹',roles:['审核','验收']}],launch:{on:false},deliveries:[]});
const record=(code='W1',revision='rev-1')=>({code,revision,name:'一般工作流',graph:editor.freshGraph(),file:'自动化/工作流/项目/'+code+'.md'});
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('a new graph is start to end and contains no invented task or employee',()=>{
  const g=editor.freshGraph();assert.deepEqual(g.nodes.map(n=>n.type),['start','end']);assert.equal(g.edges.length,1);assert.ok(g.nodes.every(n=>!n.task&&!n.employee));assert.equal(editor.localValidation(g).ok,true);
});
test('task dropdown resolves complete unique keys, preserving duplicate bare S2 identifiers',()=>{
  const c=context();c.board.items.push({key:'S2-3',what:'裸编号'},{key:'S1-1 S2-1',what:'重复完整编号'});
  assert.deepEqual(editor.taskChoices(c).map(t=>t.key),['S1-2 S2-1']);assert.equal(editor.taskChoices(context()).length,2);
});
test('module task keys including spaces remain separate from same-number goal and other module tasks',()=>{
  const c=context();c.board.items.push({key:'工具 S2-1',what:'工具安装'},{key:'DIY 读书 清单 S2-1',what:'整理材料'},{key:'论文 S2-1',what:'查引用'});
  assert.deepEqual(editor.taskChoices(c).map(t=>t.key),['S1-1 S2-1','S1-2 S2-1','工具 S2-1','DIY 读书 清单 S2-1','论文 S2-1']);
});
test('employee choices use real unique G codes and display current role records',()=>{
  const c=context();c.roster.push({code:'G1',name:'重复'},{code:'not-G',name:'不存在'});
  assert.deepEqual(editor.employeeChoices(c),[{code:'G2',label:'G2 · 统筹 · 审核 / 验收'}]);assert.deepEqual(editor.employeeChoices({}),[]);
});
test('condition connections retain true and false outlets and never silently substitute an always edge',()=>{
  const g=editor.freshGraph();g.nodes.push({id:'n3',type:'condition',field:'plan_status',value:'invalid'});g.edges=[];
  assert.equal(editor.connect(g,'n1','n3','false'),true);assert.equal(g.edges[0].when,'always');
  assert.equal(editor.connect(g,'n3','n2','true'),true);assert.equal(editor.localValidation(g).ok,false);
  assert.equal(editor.connect(g,'n3','n2','false'),true);assert.equal(editor.localValidation(g).ok,true);assert.equal(editor.connect(g,'n3','n2','false'),false);
});
test('missing endpoints, duplicate IDs, unsupported types and cycles are reported',()=>{
  const g=editor.freshGraph();g.nodes.push({...g.nodes[0]},{id:'bad',type:'shell'});g.edges.push({id:'e2',from:'n2',to:'n1',when:'always'},{id:'e1',from:'absent',to:'n2'});
  const r=editor.localValidation(g);assert.equal(r.ok,false);assert.ok(r.errors.some(x=>x.includes('cycle')));assert.ok(r.errors.some(x=>x.includes('endpoint')));assert.ok(r.errors.some(x=>x.includes('Unsupported')));assert.ok(r.errors.some(x=>x.includes('duplicate')));
});
test('removing a draft node removes only its edges and undo restores its exact parameters',()=>{
  const d=new editor.Draft(record()),before=d.snapshot();d.mutate(g=>editor.removeNode(g,'n1'));assert.equal(d.graph.nodes.length,1);assert.equal(d.graph.edges.length,0);assert.equal(d.dirty,true);
  assert.equal(d.undoOnce(),true);assert.deepEqual(d.snapshot(),before);assert.equal(d.dirty,false);assert.equal(d.redoOnce(),true);assert.equal(d.graph.nodes.length,1);
});
test('local dirty drafts restore against a changed file without adopting the new revision',()=>{
  const d=new editor.Draft(record());d.mutate((g,s)=>{s.name='人的新名字';g.nodes[0].label='继续整理';});const local=d.persisted();
  const restored=new editor.Draft(record('W1','rev-2'),local);assert.equal(restored.name,'人的新名字');assert.equal(restored.graph.nodes[0].label,'继续整理');assert.equal(restored.revision,'rev-1');assert.equal(restored.remoteChanged,true);assert.equal(restored.dirty,true);
});
test('a pending save adopts the saved base but preserves input typed after submission',()=>{
  const d=new editor.Draft(record());d.mutate((g,s)=>s.name='提交时名字');const submitted={...d.snapshot(),version:d.version};d.mutate((g,s)=>s.name='随后新输入');d.savedResponse({...record('W1','rev-2'),name:submitted.name},submitted);
  assert.equal(d.revision,'rev-2');assert.equal(d.name,'随后新输入');assert.equal(d.saved.name,'提交时名字');assert.equal(d.dirty,true);
});
test('exported graph data does not share references with server or callers',()=>{
  const r=record(),d=new editor.Draft(r);d.graph.nodes[0].label='变了';assert.equal(r.graph.nodes[0].label,'');const stored=d.persisted();stored.graph.nodes.length=0;assert.equal(d.graph.nodes.length,2);
});
test('all text is escaped and small viewport floating panes stay within both axes',()=>{
  assert.equal(editor.esc('<script a="b">&\''),'&lt;script a=&quot;b&quot;&gt;&amp;&#39;');
  for(const v of [{width:1280,height:800},{width:2,height:2}]){const p=editor.clampPane({x:-999,y:9999,width:900,height:900},v);assert.ok(Object.values(p).every(Number.isFinite));assert.ok(p.x>=0&&p.y>=0&&p.x+p.width<=v.width&&p.y+p.height<=v.height);}
});

// A small DOM adapter invokes production handlers without depending on a browser package.
function decode(s){return String(s||'').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');}
class Element{
  constructor(tag='div',owner=null){this.tagName=tag.toUpperCase();this.owner=owner||this;this.parentNode=null;this.style={setProperty(k,v){this[k]=v;}};this.attributes={};this.dataset={};this.listeners=new Map();this.children=[];this.controls=new Map();this._html='';this.value='';this.options=[];this.scrollTop=0;this.isConnected=true;this.classSet=new Set();this.classList={toggle:(c,on)=>{if(on===undefined)on=!this.classSet.has(c);on?this.classSet.add(c):this.classSet.delete(c);},contains:c=>this.classSet.has(c),add:c=>this.classSet.add(c),remove:c=>this.classSet.delete(c)};}
  set innerHTML(v){this._html=v;this.controls.clear();this.options=[];const re=/<(input|select|button|g|div)\b([^>]*)>/g;let m;while((m=re.exec(v))){const e=new Element(m[1],this.owner);e.parentNode=this;const attrs=m[2];for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){e.attributes[a[1]]=decode(a[2]);if(a[1].startsWith('data-')){const k=a[1].slice(5).replace(/-([a-z])/g,(_,x)=>x.toUpperCase());e.dataset[k]=decode(a[2]);}if(a[1]==='value')e.value=decode(a[2]);}for(const k of ['wfe','wfeField','wfeNode','wfeEdge','wfeResize'])if(e.dataset[k]!==undefined)this.controls.set(k+':'+e.dataset[k],e);if(m[1]==='select'){const end=v.indexOf('</select>',re.lastIndex);e.innerHTML=v.slice(re.lastIndex,end);}}
    for(const o of v.matchAll(/<option value="([^"]*)"([^>]*)>/g))this.options.push({value:decode(o[1]),selected:o[2].includes('selected')});if(this.tagName==='SELECT'&&this.options.length)this.value=(this.options.find(o=>o.selected)||this.options[0]).value;
  }
  get innerHTML(){return this._html;}
  querySelector(s){const a=s.match(/^\[data-wfe(?:-(field|node|edge|resize))?="([^"]*)"\]$/);if(a){const k='wfe'+(a[1]?a[1][0].toUpperCase()+a[1].slice(1):'');return this.controls.get(k+':'+a[2])||this.owner.controls.get(k+':'+a[2])||null;}return this.owner.parts&&this.owner.parts.get(s)||null;}
  closest(s){for(const item of s.split(',')){const t=item.trim();if(t==='input'&&this.tagName==='INPUT'||t==='select'&&this.tagName==='SELECT'||t==='textarea'&&this.tagName==='TEXTAREA')return this;const m=t.match(/^\[data-([\w-]+)\]$/);if(m&&this.attributes['data-'+m[1]]!==undefined)return this;if(t.startsWith('.')&&this.classSet.has(t.slice(1)))return this;}return this.parentNode&&this.parentNode!==this?this.parentNode.closest(s):null;}
  contains(e){return !!e&&(e===this||e.owner===this.owner);}
  addEventListener(n,f){if(!this.listeners.has(n))this.listeners.set(n,new Set());this.listeners.get(n).add(f);}
  removeEventListener(n,f){if(this.listeners.has(n))this.listeners.get(n).delete(f);}
  fire(n,e={}){for(const f of this.listeners.get(n)||[])f({target:this,...e});}
  setAttribute(n,v){this.attributes[n]=v;if(n==='style')this.style={};}
  getAttribute(n){return this.attributes[n]||null;}
  getBoundingClientRect(){return {left:parseFloat(this.style.left)||0,top:parseFloat(this.style.top)||0,width:Math.min(parseFloat(this.style.maxWidth)||Infinity,parseFloat(this.style.width)||1300),height:Math.min(parseFloat(this.style.maxHeight)||Infinity,parseFloat(this.style.height)||780)};}
  setPointerCapture(){}
  focus(){global.document.activeElement=this;}
  appendChild(n){if(n.parentNode)n.parentNode.children=n.parentNode.children.filter(x=>x!==n);n.parentNode=this;this.children.push(n);}
  insertBefore(n){this.appendChild(n);}
}
class Host extends Element{
  set innerHTML(v){super.innerHTML=v;this.parts=new Map();for(const s of ['.wfe-panel','.wfe-scene','.wfe-svg','.wfe-world','.wfe-reading','.wfe-properties','.wfe-stage','.wfe-toolbar h2','.wfe-status','.wfe-meta','.wfe-handle','.wfe-more','.wfe-menu','.wfe-more summary','.wfe-legend']){const e=new Element(s==='.wfe-svg'?'svg':s==='.wfe-more'?'details':s==='.wfe-more summary'?'summary':'div',this);e.parentNode=this;for(const c of s.matchAll(/\.([\w-]+)/g))e.classSet.add(c[1]);this.parts.set(s,e);}this.parts.get('.wfe-more').appendChild(this.parts.get('.wfe-menu'));}
  get innerHTML(){return super.innerHTML;}
}
function environment(){
  const keys=['document','localStorage','innerWidth','innerHeight','addEventListener','removeEventListener','confirm'],old=new Map(keys.map(k=>[k,{exists:Object.hasOwn(global,k),value:global[k]}])),events=new Map(),store=new Map(),doc=new Element();doc.activeElement=null;doc.fullscreenElement=null;doc.body=new Element('body');doc.exitFullscreen=async()=>{doc.fullscreenElement=null;};
  global.document=doc;global.localStorage={getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)};global.innerWidth=1280;global.innerHeight=800;global.addEventListener=(n,f)=>{if(!events.has(n))events.set(n,new Set());events.get(n).add(f);};global.removeEventListener=(n,f)=>{if(events.has(n))events.get(n).delete(f);};global.confirm=()=>true;
  return {store,events,close(){editor.dispose();for(const [k,v]of old){if(v.exists)global[k]=v.value;else delete global[k];}},fire(n,e){for(const f of events.get(n)||[])f(e);}};
}
function mount(h={}){const host=new Host(),ctx=context(),p=editor.update(host,ctx,{lang:()=> 'zh',...h});return {host,ctx,p};}
function chooseRecord(p,r=record()){p.draft=new editor.Draft(r);p.selected='n1';p.ctx.online=true;p.loaded=true;p.readyToPersist=true;p.render();}
function input(p,field,value){const el=p.props.querySelector('[data-wfe-field="'+field+'"]');assert.ok(el,'input exists: '+field);el.value=value;global.document.activeElement=el;p.host.fire('input',{target:el});}

test('real delegated input keeps its field mounted across readonly context updates',()=>{
  const env=environment();try{const {p}=mount();chooseRecord(p);const field=p.props.querySelector('[data-wfe-field="label"]');input(p,'label','每次都保留');p.update({...p.ctx,updated:'later'});assert.equal(p.props.querySelector('[data-wfe-field="label"]'),field);assert.equal(p.draft.graph.nodes[0].label,'每次都保留');assert.equal(p.draft.dirty,true);}finally{env.close();}
});
test('real click handler adds and removes a draft node with undo and no backend mutations',async()=>{
  const env=environment(),calls=[];try{const {p,host}=mount({api:(...args)=>{calls.push(args);return {};}});const type=host.querySelector('[data-wfe-field="add-type"]');type.value='condition';host.fire('click',{target:host.querySelector('[data-wfe="add"]')});assert.equal(p.draft.graph.nodes.length,3);assert.equal(p.draft.graph.nodes[2].type,'condition');host.fire('click',{target:p.props.querySelector('[data-wfe="remove"]')});assert.equal(p.draft.graph.nodes.length,2);await p.action('undo');assert.equal(p.draft.graph.nodes.length,3);assert.equal(calls.length,0);}finally{env.close();}
});
test('pointer drag moves only the selected node, is undoable, and empty canvas drag pans the whole graph',()=>{
  const env=environment();try{const {p,host}=mount();const before=editor.freshGraph(),node=p.world.querySelector('[data-wfe-node="n1"]');host.fire('pointerdown',{target:node,button:0,clientX:120,clientY:110,pointerId:1,preventDefault(){}});env.fire('pointermove',{clientX:170,clientY:150});env.fire('pointerup',{});assert.equal(p.draft.graph.nodes[0].x,before.nodes[0].x+50);assert.deepEqual(p.draft.graph.nodes[1],before.nodes[1]);p.draft.undoOnce();assert.deepEqual(p.draft.graph,before);host.fire('pointerdown',{target:p.svg,button:0,clientX:100,clientY:100,pointerId:2,preventDefault(){}});env.fire('pointermove',{clientX:160,clientY:125});env.fire('pointerup',{});assert.deepEqual(p.pose,{x:60,y:25,s:1});}finally{env.close();}
});
test('saving while typing adopts only the submitted version and keeps the newer input dirty',async()=>{
  const env=environment(),save=deferred(),calls=[];try{const {p}=mount({api:(method,path,body)=>{calls.push({method,path,body});return save.promise;}});chooseRecord(p);input(p,'name','第一次');const pending=p.action('save');input(p,'name','第二次');save.resolve({...record('W1','rev-2'),name:'第一次'});await pending;assert.equal(p.draft.name,'第二次');assert.equal(p.draft.revision,'rev-2');assert.equal(p.draft.dirty,true);assert.equal(calls[0].method,'PUT');assert.equal(calls[0].path,'api/auto/workflows');assert.equal(calls[0].body.name,'第一次');assert.equal(calls.length,1);}finally{env.close();}
});
test('version conflict leaves exact unsaved graph and forbids enabling until resolved',async()=>{
  const env=environment(),calls=[];try{const {p}=mount({api:(method,path,body)=>{calls.push({method,path,body});return Promise.reject(Object.assign(new Error('版本已更新'),{status:409}));}});chooseRecord(p);input(p,'label','有人的改动');const before=p.getState().graph;await p.action('save');assert.deepEqual(p.getState().graph,before);assert.equal(p.draft.revision,'rev-1');assert.equal(p.draft.remoteChanged,true);await p.action('control');assert.equal(calls.length,1);assert.ok(p.lastError.includes('本机草稿未覆盖'));}finally{env.close();}
});
test('validation and rehearsal use readonly graph APIs and stale results do not overwrite new edits',async()=>{
  const env=environment(),pending=deferred(),calls=[];try{const {p}=mount({api:(method,path,body)=>{calls.push({method,path,body});return pending.promise;}});chooseRecord(p);const job=p.action('validate');input(p,'label','校验途中写字');pending.resolve({ok:true,errors:[]});await job;assert.equal(p.messages,null);assert.equal(calls[0].path,'api/auto/workflows/validate');assert.equal(calls[0].method,'POST');p.h.api=(method,path,body)=>{calls.push({method,path,body});return {ok:true,read_only:true,waiting:[]};};await p.action('dry');assert.equal(p.dry.read_only,true);assert.equal(calls[1].path,'api/auto/workflows/dry-run');assert.ok(calls.every(c=>!c.path.includes('/launch')));}finally{env.close();}
});
test('explicit enable uses saved revision, stop uses immutable active snapshot even after draft changes',async()=>{
  const env=environment(),calls=[];try{const {p}=mount({api:(method,path,body)=>{calls.push({method,path,body});return {active:{code:'W1',state:body.action==='enable'?'active':'stopped',snapshot_revision:'snapshot-1'},guards:[]};}});chooseRecord(p);await p.action('control');assert.deepEqual(calls[0],{method:'POST',path:'api/auto/workflows/W1/control',body:{action:'enable',revision:'rev-1'}});input(p,'label','修改草稿不更换运行版本');await p.action('control');assert.equal(calls[1].body.action,'stop');assert.equal(calls[1].body.revision,'snapshot-1');assert.equal(p.draft.dirty,true);}finally{env.close();}
});
test('readonly list refresh preserves dirty graph, selection and pan while updating active facts',async()=>{
  const env=environment(),calls=[];try{const {p}=mount({api:(method,path)=>{calls.push(path);return {items:[{code:'W1',revision:'rev-2'}],active:{code:'W1',state:'stopped'},guards:['已停止']};}});chooseRecord(p);input(p,'label','保留');p.pose={x:20,y:30,s:1.4};p.selected='n2';await p.refresh(false);assert.equal(p.draft.graph.nodes[0].label,'保留');assert.equal(p.draft.revision,'rev-1');assert.deepEqual(p.pose,{x:20,y:30,s:1.4});assert.equal(p.selected,'n2');assert.deepEqual(calls,['api/auto/workflows']);}finally{env.close();}
});
test('workflow reads arriving out of order cannot reconnect to an earlier selected flow',async()=>{
  const env=environment(),a=deferred(),b=deferred();try{const {p}=mount({api:(method,path)=>path.endsWith('/W1')?a.promise:b.promise});p.ctx.online=true;const first=p.loadWorkflow('W1',false),second=p.loadWorkflow('W2',false);b.resolve(record('W2','b'));await second;a.resolve(record('W1','a'));await first;assert.equal(p.draft.code,'W2');assert.equal(p.draft.revision,'b');}finally{env.close();}
});
test('returning to employee view keeps an unsaved project-local draft and does not require discarding it',async()=>{
  const env=environment();let back=0;try{const {p}=mount({back:()=>back++});input(p,'label','离开也保留');global.confirm=()=>false;await p.action('back');assert.equal(back,1);const kept=JSON.parse(env.store.get('mh-workflow-draft:'+ROOT+':new'));assert.equal(kept.graph.nodes[0].label,'离开也保留');assert.equal(kept.dirty,true);}finally{env.close();}
});
test('a new unsaved draft restores after remount even if saved workflows exist',async()=>{
  const env=environment();try{let {p}=mount();input(p,'name','未保存新流程');p.destroy();const host=new Host(),c=context();c.online=true;p=editor.update(host,c,{api:(method,path)=>path==='api/auto/workflows'?{items:[{code:'W1'}]}:record(),lang:()=> 'zh'});await tick();assert.equal(p.draft.code,'');assert.equal(p.draft.name,'未保存新流程');assert.equal(p.draft.dirty,true);}finally{env.close();}
});
test('offline back, disposal and repeated remount retain the exact dirty new draft before any read',async()=>{
  const env=environment(),calls=[];try{let {p}=mount({api:(...args)=>{calls.push(args);throw new Error('offline');},back:()=>editor.dispose()});input(p,'name','离线未保存新流程');input(p,'label','玉树 <未保存>');const graph=p.getState().graph;await p.action('back');assert.equal(p.destroyed,true);p=mount().p;assert.equal(p.draft.name,'离线未保存新流程');assert.deepEqual(p.getState().graph,graph);assert.equal(p.draft.dirty,true);assert.equal(p.draft.code,'');p.destroy();p=mount().p;assert.equal(p.draft.name,'离线未保存新流程');assert.deepEqual(p.getState().graph,graph);assert.equal(p.draft.dirty,true);assert.equal(calls.length,0);}finally{env.close();}
});
test('offline mount restores a named W draft, its original revision and a remembered conflict',async()=>{
  const env=environment();try{let {p}=mount();chooseRecord(p,record('W7','original-revision'));input(p,'name','W7 本机改名');input(p,'label','W7 未保存节点');p.draft.remoteChanged=true;p.persist();p.destroy();p=mount().p;assert.equal(p.draft.code,'W7');assert.equal(p.draft.revision,'original-revision');assert.equal(p.draft.name,'W7 本机改名');assert.equal(p.draft.graph.nodes[0].label,'W7 未保存节点');assert.equal(p.draft.remoteChanged,true);assert.equal(p.draft.dirty,true);p.destroy();const kept=JSON.parse(env.store.get('mh-workflow-draft:'+ROOT+':W7'));assert.equal(kept.remoteChanged,true);assert.equal(kept.revision,'original-revision');}finally{env.close();}
});
test('an unread last-code placeholder does not overwrite another local draft or change the last selection',()=>{
  const env=environment();try{const prefix='mh-workflow-draft:'+ROOT+':',old={code:'',name:'另一份未保存草稿',graph:editor.freshGraph(),revision:'',dirty:true};env.store.set(prefix+'new',JSON.stringify(old));env.store.set(prefix+'last',JSON.stringify('W99'));const before=env.store.get(prefix+'new'),{p}=mount();assert.equal(p.draft.code,'W99');assert.equal(p.readyToPersist,false);p.destroy();assert.equal(env.store.get(prefix+'new'),before);assert.equal(env.store.get(prefix+'last'),JSON.stringify('W99'));assert.equal(env.store.has(prefix+'W99'),false);}finally{env.close();}
});
test('reconnecting an offline W draft compares the same file and keeps older dirty input on conflict',async()=>{
  const env=environment(),calls=[];try{let {p}=mount();chooseRecord(p,record('W7','rev-old'));input(p,'name','人还没保存的改名');p.destroy();p=mount({api:(method,path)=>{calls.push({method,path});return path==='api/auto/workflows'?{items:[{code:'W1'},{code:'W7',revision:'rev-new'}]}:record('W7','rev-new');}}).p;p.ctx.online=true;await p.refresh(false);assert.equal(p.draft.code,'W7');assert.equal(p.draft.revision,'rev-old');assert.equal(p.draft.name,'人还没保存的改名');assert.equal(p.draft.dirty,true);assert.equal(p.draft.remoteChanged,true);assert.deepEqual(calls.map(x=>x.path),['api/auto/workflows','api/auto/workflows/W7']);assert.ok(calls.every(x=>x.method==='GET'));}finally{env.close();}
});
test('initial online list arriving after typing cannot substitute another saved workflow',async()=>{
  const env=environment(),list=deferred(),calls=[];try{const {p}=mount({api:(method,path)=>{calls.push(path);return list.promise;}});p.ctx.online=true;const read=p.refresh(true);input(p,'name','等读取时新写的草稿');list.resolve({items:[{code:'W1'}]});await read;assert.equal(p.draft.code,'');assert.equal(p.draft.name,'等读取时新写的草稿');assert.equal(p.draft.dirty,true);assert.deepEqual(calls,['api/auto/workflows']);}finally{env.close();}
});
test('switching projects disposes old handlers and never restores the other project draft',()=>{
  const env=environment();try{const {p,host}=mount();input(p,'label','甲项目');const c=context();c.state.project.root='C:/temporary/project-b';const next=editor.update(host,c,{});assert.equal(p.destroyed,true);assert.notEqual(next,p);assert.equal(next.draft.graph.nodes[0].label,'');assert.equal(host.listeners.get('click').size,1);assert.equal(env.events.get('pointermove').size,1);}finally{env.close();}
});
test('native fullscreen rejection still gives window fullscreen with a movable, clamped pane and cleanup',async()=>{
  const env=environment();try{const {p}=mount();p.panel.requestFullscreen=()=>Promise.reject(new Error('Denied'));await p.enterFullscreen();assert.equal(p.fs,true);assert.equal(p.fsMode,'window');p.pane.x=-999;p.pane.y=9999;p.placePane();assert.ok(p.pane.x>=0&&p.pane.y+p.pane.height<=800);p.exitFullscreen();assert.equal(p.fs,false);p.destroy();for(const set of env.events.values())assert.equal(set.size,0);}finally{env.close();}
});
test('resize grips change chart and pane dimensions without editing task data or losing sizes on selection',()=>{
  const env=environment();try{const {p,host}=mount();const before=p.getState().graph,stageGrip=host.querySelector('[data-wfe-resize="stage"]'),paneGrip=host.querySelector('[data-wfe-resize="pane"]');assert.equal(p.stage.style.height,'640px');host.fire('pointerdown',{target:stageGrip,button:0,clientX:0,clientY:0,pointerId:1,preventDefault(){}});env.fire('pointermove',{clientX:0,clientY:120});env.fire('pointerup',{});assert.equal(p.stage.style.height,'760px');p.reading.style.width='390px';host.fire('pointerdown',{target:paneGrip,button:0,clientX:0,clientY:0,pointerId:2,preventDefault(){}});env.fire('pointermove',{clientX:160,clientY:80});env.fire('pointerup',{});assert.equal(p.reading.style.width,'550px');assert.equal(p.scene.style['--wfe-pane-width'],'550px');const height=p.reading.style.height;p.select('n2');p.update({...p.ctx,updated:'later'});assert.equal(p.reading.style.width,'550px');assert.equal(p.reading.style.height,height);assert.deepEqual(p.getState().graph,before);const saved=JSON.parse(env.store.get('mh-workflow-draft:'+ROOT+':view'));assert.equal(saved.width,'550px');assert.equal(saved.height,'760px');assert.equal(saved.paneHeight,height);}finally{env.close();}
});
test('focused resize grip supports shrinking by keyboard, with positive clamped geometry',()=>{
  const env=environment();try{const {p,host}=mount(),grip=host.querySelector('[data-wfe-resize="pane"]');p.reading.style.width='550px';p.reading.style.height='600px';env.fire('keydown',{target:grip,key:'ArrowLeft',preventDefault(){}});env.fire('keydown',{target:grip,key:'ArrowUp',preventDefault(){}});assert.equal(p.reading.style.width,'534px');assert.equal(p.reading.style.height,'584px');const small=editor.resizeBox({width:400,height:300},{x:-9999,y:-9999},{width:1300,height:800});assert.deepEqual(small,{width:260,height:260});}finally{env.close();}
});
test('rehearsal renders human readable node status, recorded conditions, and folded raw data',async()=>{
  const env=environment();try{const {p}=mount({api:()=>({ok:true,read_only:true,nodes:[{id:'n1',status:'waiting',reason:'尚无有效批准'}],edges:[{id:'e1',status:'waiting'}],decisions:[{node:'n1',actual:'invalid',result:null}],waiting:['计划范围已变']})});chooseRecord(p);await p.action('dry');assert.ok(p.props.innerHTML.includes('等待'));assert.ok(p.props.innerHTML.includes('尚无有效批准'));assert.ok(p.props.innerHTML.includes('批准已失效'));assert.ok(p.props.innerHTML.includes('未知，保持等待'));assert.ok(p.props.innerHTML.includes('<details><summary>演练数据'));assert.ok(!p.props.innerHTML.includes('<details open><summary>只读演练'));assert.ok(p.world.innerHTML.includes('演练：等待'));assert.ok(p.world.innerHTML.includes('wfe-edge waiting'));}finally{env.close();}
});
test('native SVG point conversion handles resized aspect ratios rather than stretching drag coordinates',()=>{
  const env=environment();try{const {p}=mount();p.svg.getBoundingClientRect=()=>({left:100,top:50,width:650,height:640});const point=p.point({clientX:155,clientY:215});assert.equal(point.x,110);assert.equal(point.y,80);}finally{env.close();}
});
test('disposing while a save is pending cannot resurrect a destroyed panel or consume another project draft',async()=>{
  const env=environment(),d=deferred();try{const {p}=mount({api:()=>d.promise});chooseRecord(p);input(p,'name','原本本机草稿');const job=p.action('save');p.destroy();d.resolve({...record('W1','late'),name:'服务器晚到'});await job;assert.equal(p.draft.revision,'rev-1');assert.equal(p.draft.name,'原本本机草稿');}finally{env.close();}
});

function assertMenuVisible(p){const r=p.menu.getBoundingClientRect();assert.ok(r.left>=0&&r.top>=0);assert.ok(r.left+r.width<=global.innerWidth&&r.top+r.height<=global.innerHeight);}
test('opening More below the second chart clamps every menu button region into the viewport without launching work',()=>{
  const env=environment(),calls=[];try{const {p,host}=mount({api:(...a)=>calls.push(a)});global.innerWidth=1257;global.innerHeight=586;p.summary.getBoundingClientRect=()=>({left:1250,right:1378,top:1480,bottom:1510,width:128,height:30});p.menu.style.width='320px';p.menu.style.height='300px';p.more.open=true;p.more.fire('toggle');assertMenuVisible(p);assert.equal(p.menu.parentNode,p.panel);assert.equal(p.menu.classList.contains('wfe-menu-open'),true);const add=host.querySelector('[data-wfe="add"]');host.querySelector('[data-wfe-field="add-type"]').value='condition';host.fire('click',{target:add});assert.equal(p.draft.graph.nodes.length,3);assert.equal(p.draft.graph.nodes[2].type,'condition');assert.equal(calls.length,0);}finally{env.close();}
});
test('More follows captured scroll and viewport resize, retains fullscreen ownership and cleans up listeners on dispose',async()=>{
  const env=environment();try{const {p}=mount(),menu=p.menu;let anchor={left:850,right:978,top:500,bottom:530,width:128,height:30};p.summary.getBoundingClientRect=()=>anchor;menu.style.width='320px';menu.style.height='300px';p.more.open=true;p.more.fire('toggle');assertMenuVisible(p);const before=menu.style.top;anchor={...anchor,top:30,bottom:60};env.fire('scroll',{});assert.notEqual(menu.style.top,before);global.innerWidth=800;global.innerHeight=480;env.fire('resize',{});assertMenuVisible(p);p.panel.requestFullscreen=async()=>{global.document.fullscreenElement=p.panel;};await p.enterFullscreen();assert.equal(p.menu,menu);assert.equal(menu.parentNode,p.panel);assertMenuVisible(p);global.document.fullscreenElement=null;global.document.fire('fullscreenchange');assert.equal(p.fs,false);assert.equal(menu.parentNode,p.panel);assertMenuVisible(p);p.more.open=false;p.more.fire('toggle');assert.equal(menu.parentNode,p.more);assert.equal(menu.classList.contains('wfe-menu-open'),false);p.destroy();assert.equal(p.more.listeners.get('toggle').size,0);assert.equal(env.events.get('scroll').size,0);assert.equal(env.events.get('resize').size,0);}finally{env.close();}
});
test('More keeps native summary/button keyboard activation and Escape first restores its trigger in fullscreen',async()=>{
  const env=environment();try{const {p,host}=mount();await p.enterFullscreen();p.more.open=true;p.more.fire('toggle');let prevented=0;env.fire('keydown',{target:p.summary,key:'ArrowDown',preventDefault(){prevented++;}});assert.equal(global.document.activeElement,host.querySelector('[data-wfe="new"]'));const add=host.querySelector('[data-wfe="add"]');global.document.activeElement=add;env.fire('keydown',{target:add,key:'Enter',preventDefault(){prevented++;}});assert.equal(prevented,1,'native button Enter is not swallowed or duplicated');host.fire('click',{target:add});assert.equal(p.draft.graph.nodes.length,3);env.fire('keydown',{target:add,key:'Escape',preventDefault(){prevented++;}});assert.equal(p.more.open,false);assert.equal(p.menu.parentNode,p.more);assert.equal(global.document.activeElement,p.summary);assert.equal(p.fs,true);env.fire('keydown',{target:p.summary,key:'Escape',preventDefault(){}});assert.equal(p.fs,false);}finally{env.close();}
});
test('oversized More contents remain scrollable and constrained after a very small viewport resize',()=>{
  const env=environment();try{const {p}=mount();p.more.open=true;p.more.fire('toggle');global.innerWidth=180;global.innerHeight=110;env.fire('resize',{});assertMenuVisible(p);assert.equal(p.menu.style.maxWidth,'164px');assert.equal(p.menu.style.maxHeight,'94px');assert.equal(p.draft.graph.nodes.length,2);}finally{env.close();}
});
