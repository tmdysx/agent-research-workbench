'use strict';
// Test the exported implementation without a browser, network, processes or project writes.
const test = require('node:test');
const assert = require('node:assert/strict');
const map = require(process.env.BRONZE_CHIP_TREE_SOURCE || '../../治理界面.js');

const ROOT='C:/temporary/community-project';
function fixture() {
  return {
    s0:{code:'S0',name:'社区活动',file:'治理/目标/S0.md'},
    goals:[{code:'S1-1',name:'报名',file:'治理/目标/S1-1.md',subs:[{code:'S2-1',what:'名册',how:'可查看',text:'待你验收'}]},
      {code:'S1-2',name:'场地',file:'治理/目标/S1-2.md',subs:[{code:'S2-1',what:'预约',text:'做完'}]}],
    modules:[{key:'登记',name:'登记',requirements:[{key:'req-a'}]},
      {key:'common:notes',name:'笔记本',kind:'common'}, {key:'笔记本',name:'笔记本 DIY'},
      {key:'旧模块',name:'旧模块',kind:'unavailable',missing:['承接模块不可用']}],
    requirements:[{key:'req-a',file:'治理/需求/登记.md',scope:'登记',code:'需-1',func:'登记姓名',effect:'能查姓名',source:'作者原话',goals:['S1-1'],modules:['登记','common:notes'],tasks:[{key:'S1-1::S2-1',goal:'S1-1',code:'S2-1',file:'治理/目标/S1-1.md'}]},
      {key:'req-b',file:'治理/需求/场地.md',scope:'场地',code:'需-1',func:'容纳人数',goals:[],modules:[],relation_note:'等你确认 S1-2'}],
    relations:[{goal:'S1-1',module:'登记',sources:[{file:'治理/计划/S1-1/P1.md',field:'目标 / 动到的模块'}]}]
  };
}
const build=data=>map.build('blueprint',data,{projectRoot:ROOT,projectName:'社区项目'});
const nodes=(m,kind)=>m.nodes.filter(n=>n.kind===kind);
const linked=(m,a,b)=>m.edges.some(e=>e.from===a.id&&e.to===b.id&&e.type==='linked');

test('a temporary non-research project uses its own labels and exact source files',()=>{
  const m=build(fixture());
  assert.equal(m.projectRoot,ROOT);
  assert.equal(nodes(m,'project')[0].title,'社区项目');
  assert.equal(nodes(m,'goal').length,3);
  assert.ok(!JSON.stringify(m).includes('论文'));
  assert.ok(nodes(m,'file').some(n=>n.file==='治理/计划/S1-1/P1.md'));
});
test('same requirement numbers in different files remain distinct',()=>{
  const m=build(fixture()),q=nodes(m,'requirement');
  assert.equal(q.length,2);assert.notEqual(q[0].id,q[1].id);
  assert.ok(q.every(n=>n.title.includes('需-1')));
  const fileEdges=q.map(n=>m.edges.filter(e=>e.from===n.id&&e.type==='source'));
  assert.equal(fileEdges[0].length,1);assert.equal(fileEdges[1].length,1);
  assert.notEqual(fileEdges[0][0].to,fileEdges[1][0].to);
});
test('same S2 code retains the goal and file; a shared requirement does not merge tasks',()=>{
  const m=build(fixture()),ts=nodes(m,'task');
  assert.equal(ts.length,2);assert.notEqual(ts[0].id,ts[1].id);
  assert.equal(ts[0].status,'待你验收');assert.equal(ts[1].status,'做完');
  const req=nodes(m,'requirement').find(n=>n.key==='req-a');
  assert.ok(linked(m,req,ts.find(n=>n.key==='S1-1::S2-1')));
  assert.ok(!linked(m,req,ts.find(n=>n.key==='S1-2::S2-1')));
});
test('one requirement can link two modules, including a common module without linking its DIY namesake',()=>{
  const m=build(fixture()),req=nodes(m,'requirement').find(n=>n.key==='req-a'),ms=nodes(m,'module');
  assert.ok(linked(m,req,ms.find(n=>n.key==='登记')));
  assert.ok(linked(m,req,ms.find(n=>n.key==='common:notes')));
  assert.ok(!linked(m,req,ms.find(n=>n.key==='笔记本')));
});
test('unassigned and tentative records create no guessed relationship',()=>{
  const data=fixture();data.goals[1].one_line='正文提到登记和需-1';data.goals[1].related_modules=['登记'];
  const m=build(data),q=nodes(m,'requirement').find(n=>n.key==='req-b'),goal=nodes(m,'goal').find(n=>n.key==='S1-2'),mod=nodes(m,'module').find(n=>n.key==='登记');
  assert.ok(!m.edges.some(e=>e.type==='linked'&&(e.to===q.id||e.from===q.id)));
  assert.ok(!linked(m,goal,mod));assert.ok(q.details.some(d=>d.value.includes('未分配')));
});
test('shared source file is deduplicated but retains multiple source edges',()=>{
  const m=build(fixture()),file=nodes(m,'file').find(n=>n.file==='治理/目标/S1-1.md');
  assert.equal(nodes(m,'file').filter(n=>n.file===file.file).length,1);
  assert.ok(m.edges.filter(e=>e.to===file.id&&e.type==='source').length>=2);
});
test('missing referenced goals are warnings and unavailable modules retain true missing state',()=>{
  const data=fixture();data.requirements[0].goals.push('S1-404');data.relations.push({goal:'S1-404',module:'登记'});
  const m=build(data);assert.ok(m.warnings.some(x=>x.includes('S1-404')));
  assert.ok(!nodes(m,'goal').some(n=>n.key==='S1-404'));
  assert.equal(nodes(m,'module').find(n=>n.key==='旧模块').missing,true);
});
test('empty project has no invented goals, modules or sources',()=>{
  const m=build({});assert.deepEqual(nodes(m,'goal'),[]);assert.deepEqual(nodes(m,'module'),[]);assert.deepEqual(nodes(m,'file'),[]);
  assert.ok(m.warnings.includes('没有目标记录 No goals'));
});
test('rules graph uses actual sections and children, excludes virtual navigation and does not parse text',()=>{
  const data={module:'戒律',sections:[{title:'总的',items:[{path:'@/AGENTS.md',name:'AGENTS.md'}]},
    {title:'总戒律',items:[{path:'1 通用戒律.md',name:'通用',text:'提到登记模块'}]},
    {title:'模块',items:[{path:'@/资料/登记/戒律.md',name:'登记规则'}]},
    {title:'其他',items:[{path:'附录',name:'附录',dir:true,children:[{path:'附录/说明.md',name:'说明'}]},{path:'#虚拟',name:'虚拟',virtual:true}]}]};
  const m=map.build('rules',data,{projectRoot:ROOT,module:'戒律'});
  assert.equal(nodes(m,'file').length,4);assert.equal(nodes(m,'directory').length,1);assert.ok(!m.nodes.some(n=>n.title==='虚拟'));
  assert.ok(m.edges.every(e=>e.type==='contains'));assert.ok(!nodes(m,'module').length);
  const file=nodes(m,'file').find(n=>n.title==='说明'),parent=nodes(m,'directory')[0];
  assert.ok(m.edges.some(e=>e.from===parent.id&&e.to===file.id));
  assert.equal(map.previewURL(file),'api/modules/%E6%88%92%E5%BE%8B/preview?path='+encodeURIComponent('附录/说明.md'));
});
test('an explicitly identical linked rule file keeps both groups and only one file node',()=>{
  const item={name:'规则',path:'@/治理/戒律/模块/登记.md'};
  const m=map.build('rules',{sections:[{title:'一组',items:[item]},{title:'二组',items:[item]}]},{projectRoot:ROOT,module:'戒律'});
  assert.equal(nodes(m,'file').length,1);const f=nodes(m,'file')[0];assert.equal(m.edges.filter(e=>e.to===f.id).length,2);
});
test('empty and truncated rule listings report their actual limits',()=>{
  const m=map.build('rules',{sections:[{title:'总戒律',items:[]}],truncated:true},{projectRoot:ROOT});
  assert.ok(nodes(m,'group')[0].missing);assert.equal(nodes(m,'file').length,0);
  assert.ok(m.warnings.some(x=>x.includes('截断')));
});
test('many nodes start in eight-entity batches with explicit source files and searchable later records',()=>{
  const data=fixture();for(let i=3;i<40;i++)data.goals.push({code:'S1-'+i,name:'活动'+i,file:'治理/目标/S1-'+i+'.md',subs:[]});
  const m=build(data),first=map.visible(m,{limit:8}),more=map.visible(m,{limit:16});
  assert.ok(first.more);assert.equal(first.nodes.filter(n=>n.kind!=='file').length,8);
  assert.ok(more.nodes.length>first.nodes.length);
  const found=map.visible(m,{query:'S1-39'});assert.ok(found.nodes.some(n=>n.key==='S1-39'));
});
test('local focus includes only direct declared neighbors, and all rendered edges have visible endpoints',()=>{
  const m=build(fixture()),g=nodes(m,'goal').find(n=>n.key==='S1-1'),view=map.visible(m,{focus:g.id});
  assert.ok(view.nodes.some(n=>n.key==='S1-1::S2-1'));
  assert.ok(!view.nodes.some(n=>n.key==='S1-2::S2-1'));
  const ids=new Set(view.nodes.map(n=>n.id));assert.ok(view.edges.every(e=>ids.has(e.from)&&ids.has(e.to)));
});
test('preview URLs preserve approved old paths and encode literal file characters',()=>{
  const url=map.previewURL({preview:{mode:'module',module:'戒律',path:'@/资料/登记/戒律 #1.md'}});
  assert.ok(url.includes(encodeURIComponent('@/资料/登记/戒律 #1.md')));
  assert.equal(map.previewURL({preview:{mode:'project',path:'治理/需求/a&b.md'}}),'api/project/preview?path='+encodeURIComponent('治理/需求/a&b.md'));
});
test('preview rejects absolute, traversal, command-scheme and control paths; missing nodes are never requested',()=>{
  for(const path of ['../secret','治理/../secret','C:/secret','/secret','https://example.test','javascript:alert(1)','a\u0000b'])assert.equal(map.previewURL({preview:{mode:'project',path}}),'');
  assert.equal(map.previewURL({missing:true,preview:{mode:'project',path:'规则.md'}}),'');
});
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
function readerFixture(){
  let ctx={root:ROOT,route:'blueprint',revision:1},active=true;
  const pending=[],results=[],errors=[],calls=[];
  const reader=map.createReader({context:()=>ctx,isCurrent:()=>active,request(method,url){calls.push([method,url]);const d=deferred();pending.push(d);return d.promise;},result:(n,d)=>results.push([n,d]),error:(n,e)=>errors.push([n,e])});
  const node={id:'file',preview:{mode:'project',path:'治理/目标/S0.md'}};
  return {reader,node,pending,results,errors,calls,setContext:x=>{ctx=x;},setActive:x=>{active=x;}};
}
test('preview reads only GET and accepts the current response',async()=>{
  const f=readerFixture(),p=f.reader.select(f.node);f.pending[0].resolve({text:'真实原文'});await p;
  assert.equal(f.calls[0][0],'GET');assert.equal(f.results[0][1].text,'真实原文');
});
test('fast node selection rejects the older response and error',async()=>{
  const f=readerFixture(),old=f.reader.select(f.node),fresh=f.reader.select({...f.node,id:'new'});
  f.pending[1].resolve({text:'新'});await fresh;f.pending[0].reject(new Error('旧错误'));await old;
  assert.equal(f.results.length,1);assert.equal(f.results[0][0].id,'new');assert.deepEqual(f.errors,[]);
});
test('project, page or data revision changes reject delayed responses',async()=>{
  for(const ctx of [{root:'other',route:'blueprint',revision:1},{root:ROOT,route:'rules',revision:1},{root:ROOT,route:'blueprint',revision:2}]){
    const f=readerFixture(),p=f.reader.select(f.node);f.setContext(ctx);f.pending[0].resolve({text:'旧'});await p;assert.deepEqual(f.results,[]);
  }
});
test('leaving the page, invalidation and destroy reject delayed previews',async()=>{
  for(const action of [f=>f.setActive(false),f=>f.reader.invalidate(),f=>f.reader.destroy()]){
    const f=readerFixture(),p=f.reader.select(f.node);action(f);f.pending[0].resolve({text:'旧'});await p;assert.deepEqual(f.results,[]);
  }
});
test('a missing preview makes no request and returns only the local node details',async()=>{
  const f=readerFixture();await f.reader.select({id:'empty'});assert.equal(f.calls.length,0);assert.equal(f.results[0][1],null);
});

// Minimal host for the actual controller: it records HTML and real listener effects,
// rather than recreating graph or async-selection logic in the tests.
class Element {
  constructor(owner,attributes={}){this.owner=owner;this.ownerDocument=owner&&owner.ownerDocument;this.attributes={...attributes};this.dataset={};this.innerHTML='';this.textContent='';this.value='';this.hidden=false;this.listeners=new Map();this.scrollTop=0;this.scrollLeft=0;this.clientWidth=500;this.clientHeight=400;this.style={};
    const classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>classes.add(x)),remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x)};
    Object.entries(attributes).forEach(([key,value])=>{if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;});}
  hasAttribute(key){return Object.hasOwn(this.attributes,key);}
  setAttribute(key,value){this.attributes[key]=value;}
  appendChild(node){if(node.parentNode&&node.parentNode.children)node.parentNode.children=node.parentNode.children.filter(x=>x!==node);this.children=this.children||[];this.children.push(node);node.parentNode=this;return node;}
  closest(){return this;}
  matches(selector){return selector==='.gmap-search'&&this===this.owner.querySelector('.gmap-search');}
  addEventListener(type,fn,options){this.listeners.set(type,fn);(this.listenerOptions||=new Map()).set(type,options);}
  removeEventListener(type,fn){if(this.listeners.get(type)===fn){this.listeners.delete(type);if(this.listenerOptions)this.listenerOptions.delete(type);}}
  querySelectorAll(){return [];}
  emit(type,event={}){const fn=this.listeners.get(type);if(fn)fn({target:this,preventDefault(){},...event});}
}
class Host extends Element {
  constructor(doc){super(null);this.owner=this;this.ownerDocument=doc;this.isConnected=true;this.parts=new Map();}
  querySelector(selector){if(!this.parts.has(selector))this.parts.set(selector,new Element(this));return this.parts.get(selector);}
  contains(node){return node.owner===this;}
  emit(type,target,event={}){const fn=this.listeners.get(type);if(fn)fn({target,key:type==='keydown'?'Enter':'',preventDefault(){},...event});}
  target(attributes){return new Element(this,attributes);}
}
function controllerFixture(extra={}){
  const host=new Host(extra.document),calls=[],pending=[];
  const options={kind:'blueprint',data:fixture(),projectRoot:ROOT,projectName:'社区项目'};
  const helpers={language:()=> 'en',isCurrent:()=>host.isConnected,renderMarkdown:text=>'<p>'+text+'</p>',...extra.helpers,request:(method,url)=>{
    calls.push([method,url]);const d=deferred();pending.push(d);return d.promise;
  }};
  return {host,calls,pending,options,helpers,ctl:map.mount(host,options,helpers)};
}
test('real mount clicks read a source in the right pane, preserve the graph and make only a GET',async()=>{
  const f=controllerFixture(),goal=nodes(build(f.options.data),'goal').find(n=>n.key==='S1-1');
  f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));
  assert.equal(f.calls.length,0);assert.ok(f.host.querySelector('.gmap-reading-body').innerHTML.includes('data-gmap-node'));
  const file=nodes(build(f.options.data),'file').find(n=>n.file==='治理/目标/S1-1.md');
  f.host.emit('click',f.host.target({'data-gmap-node':file.id}));
  assert.equal(f.calls.length,1);assert.equal(f.calls[0][0],'GET');
  f.pending[0].resolve({kind:'md',text:'报名原文'});await Promise.resolve();await Promise.resolve();
  assert.ok(f.host.querySelector('.gmap-reading-body').innerHTML.includes('报名原文'));
  assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('gmap-svg'));
  assert.ok(!f.host.querySelector('.gmap-reading-body').innerHTML.includes('href='));
});
test('same host remount updates the actual controller and project switch rejects its old preview',async()=>{
  const f=controllerFixture(),file=nodes(build(f.options.data),'file')[0];
  f.host.emit('click',f.host.target({'data-gmap-node':file.id}));
  const ctl=map.mount(f.host,{...f.options,projectRoot:'C:/another-project',projectName:'另一项目'},f.helpers);
  assert.equal(ctl,f.ctl);assert.equal(f.host.listeners.size,3);
  f.pending[0].resolve({kind:'md',text:'不应出现的旧项目'});await Promise.resolve();await Promise.resolve();
  assert.ok(!f.host.querySelector('.gmap-reading-body').innerHTML.includes('不应出现'));
  assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('另一项目'));
});
test('actual controller search and batches never recreate the reading pane; destroy removes all host listeners',()=>{
  const f=controllerFixture(),reading=f.host.querySelector('.gmap-reading-body');reading.innerHTML='保留的阅读内容';
  const search=f.host.querySelector('.gmap-search');search.value='S1-2';f.host.emit('input',search);
  assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('S1-2'));assert.equal(reading.innerHTML,'保留的阅读内容');
  f.host.emit('click',f.host.target({'data-gmap-more':''}));assert.equal(reading.innerHTML,'保留的阅读内容');
  f.ctl.destroy();assert.equal(f.host.listeners.size,0);
});
test('rule totals do not double-count source files already listed as candidates',()=>{
  const data={sections:[{title:'模块',items:Array.from({length:20},(_,i)=>({name:'规则'+i,path:'@/治理/戒律/模块/'+i+'.md'}))}]};
  const m=map.build('rules',data,{projectRoot:ROOT,module:'戒律'}),v=map.visible(m,{limit:8});
  assert.equal(v.total,m.nodes.length);assert.ok(v.more);assert.ok(v.shown<=v.total);
});

test('all overview layouts preserve the same actual entity IDs and stay within finite SVG bounds',()=>{
  const m=build(fixture()),v=map.visible(m,{limit:100}),ids=v.nodes.map(n=>n.id).sort(),before=JSON.stringify(m);
  const shapes=['map','flow','model3d'].map(mode=>map.layout(v.nodes,v.edges,mode));
  for(const s of shapes){
    assert.deepEqual([...s.positions.keys()].sort(),ids);assert.ok(Number.isFinite(s.width)&&Number.isFinite(s.height));
    for(const p of s.positions.values()){assert.ok([p.x,p.y,p.z].every(Number.isFinite));assert.ok(p.x>=0&&p.y>=0);assert.ok(p.x+s.nodeWidth<=s.width&&p.y+s.nodeHeight<=s.height);}
  }
  assert.notDeepEqual([...shapes[0].positions],[...shapes[1].positions]);assert.equal(shapes[2].planes.length,3);
  assert.equal(JSON.stringify(m),before);
});

test('flow layout handles declared cycles without adding or changing a relation',()=>{
  const ns=[{id:'a',depth:0},{id:'b',depth:1},{id:'c',depth:2}],es=[{from:'a',to:'b',type:'linked'},{from:'b',to:'a',type:'linked'},{from:'b',to:'c',type:'source'}],before=JSON.stringify(es);
  const s=map.layout(ns,es,'flow');assert.equal(s.positions.size,3);assert.ok([...s.positions.values()].every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));assert.equal(JSON.stringify(es),before);
});

test('empty layouts and invalid modes have a usable finite map fallback',()=>{
  for(const mode of ['map','flow','model3d','invalid']){const s=map.layout([],[],mode);assert.ok(s.width>0&&s.height>0);assert.equal(s.positions.size,0);}
  assert.equal(map.normalizeMode('invalid'),'map');assert.equal(map.normalizeMode('model3d'),'model3d');
});

test('3D projection rotates actual positions and camera input remains finite and bounded',()=>{
  const p={x:190,y:240,z:80},initial={yaw:-.45,pitch:.42},rotated=map.rotateCamera(initial,70,-40);
  assert.notDeepEqual(map.project3D(p,initial),map.project3D(p,rotated));assert.deepEqual(initial,{yaw:-.45,pitch:.42});
  const extreme=map.rotateCamera(initial,1e9,1e9);assert.ok(Math.abs(extreme.yaw)<=Math.PI&&Math.abs(extreme.pitch)<=1.12);
  const invalid=map.rotateCamera({yaw:NaN,pitch:Infinity},NaN,Infinity);assert.ok([invalid.yaw,invalid.pitch].every(Number.isFinite));
  const m=build(fixture()),v=map.visible(m,{limit:16});assert.notDeepEqual([...map.layout(v.nodes,v.edges,'model3d',initial).positions],[...map.layout(v.nodes,v.edges,'model3d',rotated).positions]);
});

test('wide-character label truncation respects a visual budget without splitting Unicode characters',()=>{
  const chinese=map.shortLabel('项目的完整需求和验收标准以及历史记录',13),latin=map.shortLabel('ABCDEFGHIJKLMNOPQRSTUVWXYZ',13);
  assert.ok(chinese.endsWith('…'));assert.ok(Array.from(chinese).length<=13);assert.ok(Array.from(latin).length>Array.from(chinese).length);
  assert.equal(map.shortLabel('短文件.md',13),'短文件.md');assert.ok(!map.shortLabel('𠮷'.repeat(30),13).includes('\ufffd'));
});

test('zoom uses actual SVG dimensions, clamps the range and resets rotation without changing reading',()=>{
  const f=controllerFixture(),reading=f.host.querySelector('.gmap-reading-body');reading.innerHTML='已选原文';
  const html=()=>f.host.querySelector('.gmap-graph').innerHTML;
  const initialWidth=Number(html().match(/width="(\d+)"/)[1]);
  f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));assert.equal(f.ctl.state().zoom,1.2);assert.ok(Number(html().match(/width="(\d+)"/)[1])>initialWidth);
  for(let i=0;i<50;i++)f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));assert.equal(f.ctl.state().zoom,3);
  for(let i=0;i<50;i++)f.host.emit('click',f.host.target({'data-gmap-zoom':'out'}));assert.equal(f.ctl.state().zoom,.5);
  f.host.emit('click',f.host.target({'data-gmap-zoom':'reset'}));assert.equal(f.ctl.state().zoom,1);assert.equal(Number(html().match(/width="(\d+)"/)[1]),initialWidth);assert.equal(reading.innerHTML,'已选原文');
  assert.equal(map.zoomLevel(NaN),1);assert.equal(map.zoomLevel(Infinity),1);f.ctl.destroy();
});

class SignalTarget {
  constructor(){this.listeners=new Map();}
  addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,new Set());this.listeners.get(type).add(fn);}
  removeEventListener(type,fn){const set=this.listeners.get(type);if(set){set.delete(fn);if(!set.size)this.listeners.delete(type);}}
  emit(type,event={}){for(const fn of this.listeners.get(type)||[])fn({preventDefault(){},...event});}
}
class FakeDocument extends SignalTarget {
  constructor(){super();this.defaultView=new SignalTarget();this.fullscreenElement=null;this.exits=0;this.styles=[];this.head={appendChild:s=>this.styles.push(s)};this.body=new Element(null);}
  getElementById(id){return this.styles.find(s=>s.id===id);}
  createElement(){const el=new Element(null);el.ownerDocument=this;return el;}
  exitFullscreen(){this.exits++;this.fullscreenElement=null;this.emit('fullscreenchange');return Promise.resolve();}
}
const flush=async()=>{await Promise.resolve();await Promise.resolve();await Promise.resolve();};

test('settings mode events change the display while retaining selection, search and reading',()=>{
  const doc=new FakeDocument();let configured='map';const f=controllerFixture({document:doc,helpers:{overviewMode:()=>configured}});
  const goal=nodes(build(f.options.data),'goal')[0];f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));
  const reading=f.host.querySelector('.gmap-reading-body');reading.scrollTop=77;const text=reading.innerHTML;
  const search=f.host.querySelector('.gmap-search');search.value='S0';f.host.emit('input',search);
  configured='flow';doc.defaultView.emit('research-overview-mode',{detail:{mode:'flow'}});
  assert.equal(f.ctl.state().mode,'flow');assert.equal(f.ctl.state().selected,goal.id);assert.equal(f.ctl.state().query,'S0');assert.equal(reading.innerHTML,text);assert.equal(reading.scrollTop,77);
  assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('marker-end='));
  configured='model3d';doc.defaultView.emit('research-overview-mode',{detail:{mode:'model3d'}});assert.ok(f.host.querySelector('.gmap').classList.contains('gmap-mode-model3d'));
  assert.equal(reading.innerHTML,text);f.ctl.destroy();
});

test('same-root updates preserve local view and unchanged file DOM including reading scroll',async()=>{
  const f=controllerFixture({helpers:{overviewMode:()=> 'map'}}),file=nodes(build(f.options.data),'file')[0],reading=f.host.querySelector('.gmap-reading-body');
  f.host.emit('click',f.host.target({'data-gmap-node':file.id}));f.pending[0].resolve({kind:'md',text:'保留同一段原文'});await flush();
  let html=reading.innerHTML,writes=0;Object.defineProperty(reading,'innerHTML',{get:()=>html,set:value=>{writes++;html=value;}});reading.scrollTop=95;
  f.host.emit('click',f.host.target({'data-gmap-mode':'model3d'}));f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));
  const graph=f.host.querySelector('.gmap-graph');graph.emit('pointerdown',{button:0,pointerId:1,clientX:40,clientY:40});graph.emit('pointermove',{pointerId:1,clientX:70,clientY:55});graph.emit('pointerup',{pointerId:1});
  const prior=f.ctl.state();f.ctl.update({...f.options,data:JSON.parse(JSON.stringify(f.options.data))},f.helpers);f.pending[1].resolve({kind:'md',text:'保留同一段原文'});await flush();
  assert.equal(writes,0);assert.equal(reading.scrollTop,95);assert.equal(f.ctl.state().selected,file.id);assert.equal(f.ctl.state().mode,'model3d');assert.equal(f.ctl.state().zoom,prior.zoom);assert.deepEqual(f.ctl.state().camera,prior.camera);
  f.ctl.destroy();
});

test('rotating a 3D map cannot accidentally select the release node; ordinary clicks can',()=>{
  const f=controllerFixture(),goal=nodes(build(f.options.data),'goal')[0],graph=f.host.querySelector('.gmap-graph');
  f.host.emit('click',f.host.target({'data-gmap-mode':'model3d'}));
  graph.emit('pointerdown',{button:0,pointerId:2,clientX:10,clientY:10});graph.emit('pointerup',{pointerId:2});
  f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));assert.equal(f.ctl.state().selected,goal.id);
  const other=nodes(build(f.options.data),'goal')[1];graph.emit('pointerdown',{button:0,pointerId:3,clientX:10,clientY:10});graph.emit('pointermove',{pointerId:3,clientX:60,clientY:40});graph.emit('pointerup',{pointerId:3});
  f.host.emit('click',f.host.target({'data-gmap-node':other.id}));assert.equal(f.ctl.state().selected,goal.id);assert.ok(!graph.classList.contains('dragging'));f.ctl.destroy();
});

test('native fullscreen targets the whole graph and reader and Esc leaves only this component',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),component=f.host.querySelector('.gmap');
  component.requestFullscreen=()=>{doc.fullscreenElement=component;doc.emit('fullscreenchange');return Promise.resolve();};
  f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.equal(doc.fullscreenElement,component);assert.equal(f.ctl.state().fullscreen,true);
  assert.ok(component!==f.host.querySelector('.gmap-graph'));doc.emit('keydown',{key:'Escape'});assert.equal(doc.fullscreenElement,null);assert.equal(doc.exits,1);
  doc.fullscreenElement={other:true};doc.emit('keydown',{key:'Escape'});f.ctl.destroy();assert.equal(doc.exits,1);
});

test('rejected native fullscreen falls back to a fixed layer and cleans up all owned listeners',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),component=f.host.querySelector('.gmap');
  component.requestFullscreen=()=>Promise.reject(new Error('Browser disallows fullscreen'));
  f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.ok(component.classList.contains('gmap-fs'));assert.equal(f.ctl.state().fullscreen,true);
  const reading=f.host.querySelector('.gmap-reading-body');reading.innerHTML='全屏中的原文';doc.emit('keydown',{key:'Escape'});assert.ok(!component.classList.contains('gmap-fs'));assert.equal(reading.innerHTML,'全屏中的原文');
  f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();f.ctl.destroy();assert.ok(!component.classList.contains('gmap-fs'));assert.equal(f.host.listeners.size,0);assert.equal(f.host.querySelector('.gmap-graph').listeners.size,0);assert.equal(doc.listeners.size,0);assert.equal(doc.defaultView.listeners.size,0);
});

test('leaving a page during native fullscreen permission cannot restore fullscreen later',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),component=f.host.querySelector('.gmap'),pending=deferred();
  component.requestFullscreen=()=>pending.promise.then(()=>{doc.fullscreenElement=component;});
  f.host.emit('click',f.host.target({'data-gmap-full':''}));f.host.isConnected=false;doc.defaultView.emit('hashchange');assert.equal(f.ctl.state().live,false);
  pending.resolve();await flush();assert.equal(doc.fullscreenElement,null);assert.equal(f.ctl.state().fullscreen,false);assert.equal(doc.exits,1);
});

test('switching project exits owned fullscreen and resets its local camera and selected file',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc});f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();
  f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));f.host.emit('click',f.host.target({'data-gmap-node':nodes(build(f.options.data),'goal')[0].id}));
  f.ctl.update({...f.options,projectRoot:'C:/temporary/another-project'},f.helpers);assert.equal(f.ctl.state().fullscreen,false);assert.equal(f.ctl.state().zoom,1);assert.equal(f.ctl.state().selected,'');f.ctl.destroy();
});

test('map styles are inserted once per document and provide finite native/fallback fullscreen layout',()=>{
  const doc=new FakeDocument(),a=controllerFixture({document:doc}),b=controllerFixture({document:doc});assert.equal(doc.styles.length,1);
  assert.ok(doc.styles[0].textContent.includes('.gmap:fullscreen'));assert.ok(doc.styles[0].textContent.includes('.gmap.gmap-fs'));assert.ok(doc.styles[0].textContent.includes('min-width:0;max-width:none'));a.ctl.destroy();b.ctl.destroy();
});

test('pagehide releases a still-connected component and language refresh updates all graph controls',()=>{
  const doc=new FakeDocument();let language='zh';const f=controllerFixture({document:doc,helpers:{language:()=>language}});
  assert.equal(f.host.querySelector('.gmap-title').textContent,'蓝图');language='en';f.ctl.update(f.options,f.helpers);
  assert.equal(f.host.querySelector('.gmap-title').textContent,'Blueprint');assert.equal(f.host.querySelector('.gmap-search').attributes.placeholder,'Search');
  doc.defaultView.emit('pagehide');assert.equal(f.ctl.state().live,false);assert.equal(doc.defaultView.listeners.size,0);
});

test('mind map starts with a center project, balanced left/right branches and no revealed grandchildren',()=>{
  const m=build(fixture()),root=nodes(m,'project')[0],v=map.mindVisible(m),s=map.layout(v.nodes,v.edges,'map'),center=s.positions.get(root.id);
  assert.ok(v.nodes.some(n=>n.kind==='goal'));assert.ok(v.nodes.some(n=>n.kind==='module'));assert.ok(!v.nodes.some(n=>n.kind==='file'||n.kind==='task'));
  assert.ok([...s.positions.values()].some(p=>p.x<center.x));assert.ok([...s.positions.values()].some(p=>p.x>center.x));assert.equal(center.x,(s.width-s.nodeWidth)/2);
});

test('expanding and collapsing a mind-map goal uses only actual relationships',()=>{
  const m=build(fixture()),root=nodes(m,'project')[0],goal=nodes(m,'goal').find(n=>n.key==='S1-1'),expanded=new Set([root.id,goal.id]);
  const v=map.mindVisible(m,{expanded}),task=nodes(m,'task').find(n=>n.key==='S1-1::S2-1');assert.ok(v.nodes.some(n=>n.id===task.id));
  assert.ok(v.edges.every(e=>m.edges.includes(e)));assert.ok(!v.nodes.some(n=>n.key==='S1-2::S2-1'));
  expanded.delete(goal.id);assert.ok(!map.mindVisible(m,{expanded}).nodes.some(n=>n.id===task.id));
});

test('many mind-map root branches use eight-item batches; search retains the actual source parent chain',()=>{
  const data=fixture();for(let i=3;i<30;i++)data.goals.push({code:'S1-'+i,name:'活动'+i,file:'治理/目标/S1-'+i+'.md',subs:[{code:'S2-1',what:'事项'+i}]});
  const m=build(data),root=nodes(m,'project')[0],first=map.mindVisible(m),next=map.mindVisible(m,{limit:16});
  assert.equal(first.shown,9);assert.ok(first.more);assert.ok(next.shown>first.shown);
  const found=map.mindVisible(m,{query:'S1-29::S2-1'}),parents=map.mindParents(m),target=nodes(m,'task').find(n=>n.key==='S1-29::S2-1');
  assert.ok(found.nodes.some(n=>n.id===target.id));assert.ok(found.nodes.some(n=>n.id===parents.get(target.id).from));assert.ok(found.nodes.some(n=>n.id===root.id));assert.equal(map.mindVisible(m,{query:'not-present'}).shown,0);
});

test('mind-map placement chooses an existing parent edge and keeps all multi-parent associations',()=>{
  const m=build(fixture()),parents=map.mindParents(m);assert.ok([...parents.values()].every(e=>m.edges.includes(e)&&e.type!=='previous'));
  const file=nodes(m,'file').find(n=>n.file==='治理/目标/S1-1.md');assert.ok(m.edges.filter(e=>e.to===file.id).length>1);
  const expanded=new Set(m.nodes.map(n=>n.id)),v=map.mindVisible(m,{expanded,limit:100});assert.equal(v.shown,m.nodes.length);assert.equal(v.edges.length,m.edges.length);
});

test('real mind-map controls toggle branches without replacing the reading area and preserve expansion on update',()=>{
  const f=controllerFixture(),goal=nodes(build(f.options.data),'goal').find(n=>n.key==='S1-1'),reading=f.host.querySelector('.gmap-reading-body');
  reading.innerHTML='已在阅读的文件';f.host.emit('click',f.host.target({'data-gmap-toggle':goal.id}));assert.ok(f.ctl.state().expanded.includes(goal.id));assert.equal(reading.innerHTML,'已在阅读的文件');
  assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('S1-1 S2-1'));
  f.ctl.update(f.options,f.helpers);assert.ok(f.ctl.state().expanded.includes(goal.id));
  f.host.emit('keydown',f.host.target({'data-gmap-toggle':goal.id}));assert.ok(!f.ctl.state().expanded.includes(goal.id));f.ctl.destroy();
});

function archiveFixture(){return {timeline:{nodes:[
  {code:'C1',name:'起点',at:'2026-10-01 10:00',prev:'',counts:{ideas:2,needs:1},files:[1,0,0]},
  {code:'C2',name:'验收',at:'2026-10-02 10:00',prev:'C1',since:'2026-10-01 10:00',grade:'绿档',counts:{deliveries:1},files:[0,3,0]},
  {code:'现在',name:'还没存的',prev:'C2',counts:{logs:4},files:[0,1,0]}]},saves:[{code:'C2',mode:'全量',checks:[{name:'桌面',ok:true}]}],
  world:{branches:[{code:'枝-1',name:'备选甲',base:'C1',path:'C:/temporary/branch-one',exists:true,state:'合了',fruit_checkpoint:'C1',demo:'演示甲',merged:{after:'C2',took:['a.md']}}]}};}
const archiveBuild=data=>map.build('archives',data,{projectRoot:ROOT,projectName:'社区项目'});

test('archive timeline previous records are temporal edges, never worktree ancestry',()=>{
  const m=archiveBuild(archiveFixture()),c1=nodes(m,'checkpoint').find(n=>n.key==='C1'),c2=nodes(m,'checkpoint').find(n=>n.key==='C2'),parents=map.mindParents(m),root=nodes(m,'project')[0];
  assert.ok(m.edges.some(e=>e.from===c1.id&&e.to===c2.id&&e.type==='previous'));assert.equal(parents.get(c2.id).from,root.id);
  assert.ok(c2.details.some(d=>d.label[0]==='上一时间档'&&d.value==='C1'));assert.ok(!m.edges.some(e=>e.from===c1.id&&e.to===c2.id&&e.type==='source'));
});

test('a branch uses only its explicitly recorded base, and merge results are annotations without merge-back edges',()=>{
  const m=archiveBuild(archiveFixture()),branch=nodes(m,'branch')[0],c1=nodes(m,'checkpoint').find(n=>n.key==='C1'),c2=nodes(m,'checkpoint').find(n=>n.key==='C2');
  assert.equal(map.mindParents(m).get(branch.id).from,c1.id);assert.ok(m.edges.some(e=>e.from===c1.id&&e.to===branch.id&&e.type==='source'));
  assert.ok(!m.edges.some(e=>e.from===branch.id&&e.to===c2.id||e.from===c2.id&&e.to===branch.id));assert.deepEqual(c2.mergeNotes,[{branch:'枝-1',fruit:'C1',demo:'演示甲',source:'C:/temporary/branch-one'}]);
});

test('a branch-local C1 fruit remains distinct from the main C1 and cannot read the main timeline endpoint',()=>{
  const m=archiveBuild(archiveFixture()),main=nodes(m,'checkpoint').find(n=>n.key==='C1'),fruit=nodes(m,'fruit')[0];assert.notEqual(main.id,fruit.id);
  assert.ok(fruit.id.includes('C:/temporary/branch-one'));assert.equal(map.previewURL(fruit),'');assert.equal(fruit.record.branch,'枝-1');assert.equal(fruit.record.code,'C1');assert.equal(map.previewURL(main),'api/timeline/C1');
});

test('same branch or fruit numbers in different explicitly recorded source projects cannot merge identities',()=>{
  const data=archiveFixture();data.world.branches.push({...data.world.branches[0],path:'C:/temporary/branch-two',demo:'演示乙'});
  const m=archiveBuild(data);assert.equal(nodes(m,'branch').length,2);assert.equal(nodes(m,'fruit').length,2);assert.notEqual(nodes(m,'branch')[0].id,nodes(m,'branch')[1].id);assert.equal(nodes(m,'checkpoint').find(n=>n.key==='C2').mergeNotes.length,2);
});

test('missing base, merge checkpoint and fruit IDs stay explicit without invented nodes',()=>{
  const data=archiveFixture();data.world.branches[0]={code:'枝-2',name:'待定',path:'C:/temporary/branch-other',state:'合了',demo:'未编号 Demo',merged:{after:'C404'}};
  const m=archiveBuild(data);assert.ok(m.warnings.some(x=>x.includes('来源档未记录')));assert.ok(m.warnings.some(x=>x.includes('C404')));assert.ok(!m.nodes.some(n=>n.key==='C404'));
  assert.ok(nodes(m,'fruit')[0].title.includes('果实编号未记录'));assert.ok(nodes(m,'checkpoint').every(n=>!n.mergeNotes.length));
});

test('archives preserve input records and the latest temporal checkpoints are the initial branches',()=>{
  const data=archiveFixture();for(let i=3;i<24;i++)data.timeline.nodes.splice(data.timeline.nodes.length-1,0,{code:'C'+i,name:'档'+i,prev:'C'+(i-1)});
  const before=JSON.stringify(data),m=archiveBuild(data),view=map.mindVisible(m);assert.equal(JSON.stringify(data),before);assert.ok(view.more);assert.ok(view.nodes.some(n=>n.kind==='now'));assert.ok(view.nodes.some(n=>n.key==='C23'));assert.ok(!view.nodes.some(n=>n.key==='C1'));
  assert.equal(map.build('archives',{}, {projectRoot:ROOT}).nodes.length,1);
});

test('timeline preview endpoints accept only real checkpoint notation or now, never URL or command input',()=>{
  assert.equal(map.previewURL({preview:{mode:'timeline',code:'现在'}}),'api/timeline/'+encodeURIComponent('现在'));
  for(const code of ['../../secret','C1?x=y','https://example.test','javascript:alert(1)','C1\u0000','枝-1'])assert.equal(map.previewURL({preview:{mode:'timeline',code}}),'');
});

function archiveController(extra={}){
  const f=controllerFixture(extra);f.options={...f.options,kind:'archives',data:archiveFixture()};f.ctl.update(f.options,f.helpers);return f;
}

test('selecting checkpoint or now reads the exact timeline by GET inline with true counts and history',async()=>{
  const f=archiveController(),m=archiveBuild(f.options.data),c2=nodes(m,'checkpoint').find(n=>n.key==='C2');f.host.emit('click',f.host.target({'data-gmap-node':c2.id}));
  assert.deepEqual(f.calls,[['GET','api/timeline/C2']]);f.pending[0].resolve({counts:{ideas:0,needs:1,items:1,deliveries:1,logs:3,decisions:0},ideas:[],needs:[{key:'登记 需-1',text:'真实要求'}],items:[{key:'S1-1 S2-1',text:'真实任务'}],deliveries:[{code:'J1',state:'待你验收'}],logs:[{id:'志-1',text:'已交付'}],decisions:[],files:{counts:[1,2,0],added:['新文件.md'],changed:['原文件.md'],removed:[]}});await flush();
  const html=f.host.querySelector('.gmap-reading-body').innerHTML;assert.ok(html.includes('真实要求'));assert.ok(html.includes('待你验收'));assert.ok(html.includes('志-1'));assert.ok(html.includes('File changes'));assert.ok(html.includes('新文件.md'));assert.ok(!html.includes('href='));
  f.host.emit('click',f.host.target({'data-gmap-node':nodes(m,'now')[0].id}));assert.equal(f.calls[1][1],'api/timeline/'+encodeURIComponent('现在'));f.ctl.destroy();
});

test('branch and fruit inline reading never fetch the main checkpoint; only an explicit button opens their original record',()=>{
  let opened=null;const f=archiveController({helpers:{openRecord:r=>{opened=r;}}}),m=archiveBuild(f.options.data),fruit=nodes(m,'fruit')[0];
  f.host.emit('click',f.host.target({'data-gmap-node':fruit.id}));assert.equal(f.calls.length,0);assert.equal(opened,null);assert.ok(f.host.querySelector('.gmap-reading-body').innerHTML.includes('演示甲'));
  f.host.emit('click',f.host.target({'data-gmap-record':''}));assert.equal(opened.kind,'fruit');assert.equal(opened.branch,'枝-1');assert.equal(opened.code,'C1');f.ctl.destroy();
});

test('a delayed timeline read cannot replace a newer branch record, another project or a destroyed archive view',async()=>{
  for(const action of ['branch','project','destroy']){
    const f=archiveController(),m=archiveBuild(f.options.data),c1=nodes(m,'checkpoint').find(n=>n.key==='C1');f.host.emit('click',f.host.target({'data-gmap-node':c1.id}));
    if(action==='branch')f.host.emit('click',f.host.target({'data-gmap-node':nodes(m,'branch')[0].id}));else if(action==='project')f.ctl.update({...f.options,projectRoot:'C:/temporary/another'},f.helpers);else f.ctl.destroy();
    f.pending[0].resolve({counts:{logs:99},logs:[{text:'不应出现的旧档'}]});await flush();assert.ok(!f.host.querySelector('.gmap-reading-body').innerHTML.includes('不应出现'));f.ctl.destroy();
  }
});

test('refreshing a selected archive re-GETs its current history while preserving expansion, zoom and reading scroll',async()=>{
  const f=archiveController(),c2=nodes(archiveBuild(f.options.data),'checkpoint').find(n=>n.key==='C2'),data={counts:{logs:1},logs:[{text:'第一轮'}],files:{counts:[0,0,0]}};
  f.host.emit('click',f.host.target({'data-gmap-node':c2.id}));f.pending[0].resolve(data);await flush();const reading=f.host.querySelector('.gmap-reading-body');reading.scrollTop=44;
  f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));const prior=f.ctl.state();f.ctl.update(f.options,f.helpers);assert.equal(f.calls.length,2);f.pending[1].resolve({...data,logs:[{text:'新发生的日志'}]});await flush();
  assert.ok(reading.innerHTML.includes('新发生的日志'));assert.equal(reading.scrollTop,44);assert.equal(f.ctl.state().zoom,prior.zoom);assert.deepEqual(f.ctl.state().expanded,prior.expanded);f.ctl.destroy();
});

test('fullscreen notes are only opened by an explicit button and are restored after exit without edits',async()=>{
  const doc=new FakeDocument(),note=new Element(null);note.innerHTML='人的原始笔记';doc.body.appendChild(note);let calls=0;
  const f=controllerFixture({document:doc,helpers:{notes:()=>{calls++;return note;}}}),component=f.host.querySelector('.gmap');component.requestFullscreen=()=>{doc.fullscreenElement=component;return Promise.resolve();};
  assert.equal(calls,0);f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.equal(calls,0);
  f.host.emit('click',f.host.target({'data-gmap-notes':''}));assert.equal(calls,1);assert.equal(note.parentNode,component);assert.equal(note.innerHTML,'人的原始笔记');
  doc.emit('keydown',{key:'Escape'});assert.equal(note.parentNode,doc.body);assert.equal(note.innerHTML,'人的原始笔记');assert.equal(f.calls.length,0);f.ctl.destroy();
});

test('the archive world tree prints the merged fruit on its checkpoint without a merge path or automatic navigation',()=>{
  const f=archiveController(),html=f.host.querySelector('.gmap-graph').innerHTML;assert.ok(html.includes('Merged 枝-1 / C1'));assert.ok(html.includes('演示甲'));assert.ok(!html.includes('gmap-edge-merge'));assert.equal(f.calls.length,0);f.ctl.destroy();
});

test('archives leave their dedicated 3D world-tree switching to the parent while other governance maps offer projection',()=>{
  const a=archiveController(),b=controllerFixture();assert.ok(!a.host.innerHTML.includes('data-gmap-mode'));assert.ok(!b.host.innerHTML.includes('data-gmap-mode'));a.ctl.destroy();b.ctl.destroy();
});

test('world-tree height and vertical checkpoint order follow the actual visible timeline',()=>{
  const m=archiveBuild(archiveFixture()),v=map.worldVisible(m),s=map.worldLayout(m,v.nodes),c1=nodes(m,'checkpoint').find(n=>n.key==='C1'),c2=nodes(m,'checkpoint').find(n=>n.key==='C2'),now=nodes(m,'now')[0];
  assert.ok(s.positions.get(now.id).y<s.positions.get(c2.id).y);assert.ok(s.positions.get(c2.id).y<s.positions.get(c1.id).y);
  const data=archiveFixture();for(let i=3;i<12;i++)data.timeline.nodes.splice(data.timeline.nodes.length-1,0,{code:'C'+i,prev:'C'+(i-1)});const large=archiveBuild(data),sv=map.worldLayout(large,map.worldVisible(large,{limit:16}).nodes);assert.ok(sv.height>s.height);
});

test('world-tree curves use only declared temporal/base/fruit edges, and unmatched sources remain standalone',()=>{
  const data=archiveFixture();data.world.branches.push({code:'枝-3',name:'无来源',path:'C:/temporary/unknown',exists:true});const m=archiveBuild(data),v=map.worldVisible(m),s=map.worldLayout(m,v.nodes),orphan=nodes(m,'branch').find(n=>n.key==='枝-3');
  assert.ok(s.orphans.includes(orphan.id));assert.ok(s.positions.get(orphan.id).orphan);assert.ok(!s.curves.some(c=>c.to===orphan.id));
  assert.ok(s.curves.every(c=>m.edges.some(e=>e.from===c.from&&e.to===c.to&&e.type===c.type)));assert.ok(s.curves.some(c=>c.type==='source'&&c.d.includes(' H ')&&c.d.includes(' A 40 40 ')&&c.d.includes(' V ')));assert.ok(s.curves.some(c=>c.type==='contains'&&c.d.includes(' V ')));
  assert.ok(s.curves.every(c=>c.type!=='merged'));for(const p of s.positions.values())assert.ok([p.x,p.y,p.z].every(Number.isFinite)&&p.x>=0&&p.x<s.width&&p.y>=0&&p.y<s.height);
});

test('world-tree search brings in the exact base and never substitutes main C1 for a branch-local fruit',()=>{
  const m=archiveBuild(archiveFixture()),v=map.worldVisible(m,{query:'备选甲'});assert.ok(v.nodes.some(n=>n.kind==='branch'));assert.ok(v.nodes.some(n=>n.kind==='checkpoint'&&n.key==='C1'));
  const fruit=nodes(m,'fruit')[0],f=map.worldVisible(m,{query:fruit.key});assert.ok(f.nodes.some(n=>n.id===fruit.id));assert.ok(f.nodes.some(n=>n.kind==='branch'));assert.ok(f.edges.every(e=>m.edges.includes(e)));
});

test('archive SVG is a straight-axis bronze chip tree with circle nodes and no ornamental leaves',()=>{
  const f=archiveController(),html=f.host.querySelector('.gmap-graph').innerHTML;assert.ok(html.includes('gmap-world-svg'));assert.ok(html.includes('<circle'));assert.ok(!html.includes('gmap-world-leaf'));assert.ok(!html.includes('<rect'));assert.ok(!html.includes('data-gmap-toggle'));f.ctl.destroy();
});

test('world-tree breathing requires explicit running evidence and a live branch state; pause does not change records',()=>{
  for(const row of [{state:'长着',running:true},{state:'结果了',running:true},{state:'长着'},{state:'合了',running:true},{state:'长着',running:false}]){
    const f=archiveController();f.options.data.world.branches[0]={...f.options.data.world.branches[0],...row};const before=JSON.stringify(f.options.data);f.ctl.update(f.options,f.helpers);
    const has=f.host.querySelector('.gmap-graph').innerHTML.includes('gmap-world-running');assert.equal(has,row.running===true&&['长着','结果了'].includes(row.state));
    f.host.emit('click',f.host.target({'data-gmap-motion':''}));assert.equal(f.ctl.state().motion,false);assert.ok(f.host.querySelector('.gmap').classList.contains('gmap-motion-paused'));assert.equal(JSON.stringify(f.options.data),before);f.ctl.destroy();
  }
});

test('world-tree entry animation runs only when new record identities appear, and reduced motion keeps paths visible',()=>{
  const doc=new FakeDocument(),f=archiveController({document:doc});f.ctl.update(f.options,f.helpers);assert.ok(!f.host.querySelector('.gmap-graph').innerHTML.includes('gmap-world-new'));
  f.options.data.world.branches.push({code:'枝-2',name:'新枝',base:'C2',path:'C:/temporary/new-branch',state:'长着'});f.ctl.update(f.options,f.helpers);assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('gmap-world-new'));
  const css=doc.styles[0].textContent;assert.ok(css.includes('prefers-reduced-motion:reduce'));assert.ok(css.includes('stroke-dashoffset:0'));assert.ok(css.includes('gmap-branch-grow'));f.ctl.destroy();
});

test('module alias uses the real file tree with its own name and no invented rule semantics',()=>{
  const data={sections:[{title:'脚本',items:[{name:'示例.py',path:'脚本/示例.py'}]}]},m=map.build('module',data,{projectRoot:ROOT,module:'图表'});assert.equal(m.kind,'module');assert.ok(m.edges.every(e=>e.type==='contains'));
  assert.equal(map.previewURL(nodes(m,'file')[0]),'api/modules/'+encodeURIComponent('图表')+'/preview?path='+encodeURIComponent('脚本/示例.py'));assert.ok(!JSON.stringify(m).includes('戒律'));
  const f=controllerFixture();f.ctl.update({...f.options,kind:'module',module:'图表',data},f.helpers);assert.equal(f.host.querySelector('.gmap-title').textContent,'图表');f.ctl.destroy();
});

test('index alias keeps same-number records distinct by explicit original-page source and makes no inferred facts',()=>{
  const data={items:[{id:'P1',label:'计划一',summary:'原文摘要甲',record:{view:'plans',key:'治理/计划/甲/P1.md'}},{id:'P1',label:'计划二',summary:'原文摘要乙',record:{view:'plans',key:'治理/计划/乙/P1.md'}},{label:'未关联',summary:'仅记录摘要'}]},m=map.build('index',data,{projectRoot:ROOT,module:'计划'});
  assert.equal(nodes(m,'entry').length,3);assert.notEqual(nodes(m,'entry')[0].id,nodes(m,'entry')[1].id);assert.ok(m.edges.every(e=>e.type==='contains'));assert.ok(!nodes(m,'file').length);assert.ok(!nodes(m,'task').length);assert.equal(nodes(m,'entry')[2].record.record,null);
});

test('index selection reads its supplied summary inline and only an explicit button opens the original page',()=>{
  let opened=null;const f=controllerFixture({helpers:{openRecord:r=>{opened=r;}}}),data={items:[{id:'A-1',label:'答疑',summary:'人已有的回答',record:{view:'qa',key:'A-1'}}]};f.options={...f.options,kind:'index',module:'答疑',data};f.ctl.update(f.options,f.helpers);
  const entry=nodes(map.build('index',data,f.options),'entry')[0];f.host.emit('click',f.host.target({'data-gmap-node':entry.id}));assert.equal(f.calls.length,0);assert.equal(opened,null);assert.ok(f.host.querySelector('.gmap-reading-body').innerHTML.includes('人已有的回答'));
  f.host.emit('click',f.host.target({'data-gmap-record':''}));assert.equal(opened.view,'qa');assert.equal(opened.key,'A-1');f.ctl.destroy();
});

test('changing another module setting cannot switch the current overview or reading selection',()=>{
  const doc=new FakeDocument();let ownMode='map';const f=controllerFixture({document:doc,helpers:{overviewMode:()=>ownMode}}),goal=nodes(build(f.options.data),'goal')[0];f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));
  doc.defaultView.emit('research-overview-mode',{detail:{mode:'flow',key:'别的模块'}});assert.equal(f.ctl.state().mode,'map');assert.equal(f.ctl.state().selected,goal.id);
  ownMode='flow';doc.defaultView.emit('research-overview-mode',{detail:{mode:'map'}});assert.equal(f.ctl.state().mode,'flow');assert.equal(f.ctl.state().selected,goal.id);f.ctl.destroy();
});

test('changing the module scope of a shared host resets the earlier module selection and preview',async()=>{
  const f=controllerFixture(),data={items:[{name:'规则.md',path:'规则.md'}]};f.options={...f.options,kind:'module',module:'甲',data};f.ctl.update(f.options,f.helpers);const file=nodes(map.build('module',data,f.options),'file')[0];f.host.emit('click',f.host.target({'data-gmap-node':file.id}));
  f.ctl.update({...f.options,module:'乙'},f.helpers);f.pending[0].resolve({text:'甲的旧文'});await flush();assert.equal(f.ctl.state().selected,'');assert.ok(!f.host.querySelector('.gmap-reading-body').innerHTML.includes('甲的旧文'));f.ctl.destroy();
});

test('panel clamping is pure and keeps the entire floating reading box within a small available canvas',()=>{
  const original={x:-900,y:999,w:900,h:700},c=map.clampPanel(original,{width:420,height:260});assert.deepEqual(original,{x:-900,y:999,w:900,h:700});assert.ok(c.x>=8&&c.y>=8&&c.x+c.w<=412&&c.y+c.h<=252);
  const tiny=map.clampPanel({x:NaN,y:Infinity,w:Infinity,h:NaN},{width:200,height:140});assert.ok(Object.values(tiny).every(Number.isFinite));assert.ok(tiny.x+tiny.w<=192&&tiny.y+tiny.h<=132);
});

test('fullscreen reading moves only by its handle, remains clamped on resize, and exits back to the normal sidebar',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc});f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();const handle=f.host.querySelector('.gmap-reading-handle'),reading=f.host.querySelector('.gmap-reading-body'),panel=f.host.querySelector('.gmap-reading');
  reading.innerHTML='不可误拖的正文';const initial=f.ctl.state().panelBox;reading.emit('pointerdown',{button:0,pointerId:8,clientX:100,clientY:100});reading.emit('pointermove',{pointerId:8,clientX:-900,clientY:-900});assert.deepEqual(f.ctl.state().panelBox,initial);
  handle.emit('pointerdown',{button:0,pointerId:9,clientX:150,clientY:100});handle.emit('pointermove',{pointerId:9,clientX:-900,clientY:900});handle.emit('pointerup',{pointerId:9});const moved=f.ctl.state().panelBox;assert.equal(moved.x,8);assert.ok(moved.y+moved.h<=392);assert.equal(reading.innerHTML,'不可误拖的正文');
  const canvas=f.host.querySelector('.gmap-layout');canvas.clientWidth=260;canvas.clientHeight=220;doc.defaultView.emit('resize');const fit=f.ctl.state().panelBox;assert.ok(fit.x+fit.w<=252&&fit.y+fit.h<=212);
  doc.emit('keydown',{key:'Escape'});assert.equal(panel.style.left,'');assert.equal(panel.style.width,'');assert.equal(reading.innerHTML,'不可误拖的正文');f.ctl.destroy();assert.equal(handle.listeners.size,0);assert.equal(doc.defaultView.listeners.size,0);
});

test('compact toolbar has one row with settings-only mode choice and a real fit control',()=>{
  const f=controllerFixture();assert.equal((f.host.innerHTML.match(/class="gmap-toolbar"/g)||[]).length,1);assert.ok(!f.host.innerHTML.includes('data-gmap-mode'));assert.ok(!f.host.innerHTML.includes('data-gmap-home'));assert.ok(f.host.innerHTML.includes('data-gmap-zoom="fit"'));
  const read=f.host.querySelector('.gmap-reading-body');read.innerHTML='保留原文';f.host.emit('click',f.host.target({'data-gmap-zoom':'fit'}));assert.ok(f.ctl.state().zoom<1);assert.equal(read.innerHTML,'保留原文');f.ctl.destroy();
});

test('selecting a later batch keeps it visible and future timeline refreshes do not hide its selected archive',()=>{
  const f=archiveController();for(let i=3;i<20;i++)f.options.data.timeline.nodes.splice(f.options.data.timeline.nodes.length-1,0,{code:'C'+i,prev:'C'+(i-1)});f.ctl.update(f.options,f.helpers);
  f.host.emit('click',f.host.target({'data-gmap-more':''}));const m=archiveBuild(f.options.data),older=nodes(m,'checkpoint').find(n=>n.key==='C5');f.host.emit('click',f.host.target({'data-gmap-node':older.id}));assert.equal(f.ctl.state().limit,16);assert.ok(f.host.querySelector('.gmap-graph').innerHTML.includes('C5'));
  assert.ok(map.worldVisible(m,{limit:8,selected:older.id}).nodes.some(n=>n.id===older.id));f.ctl.destroy();
});

test('blank-space dragging pans both 2D views without changing data, relationships or the 3D camera',()=>{
  for(const mode of ['map','flow']){
    const f=controllerFixture(),data=JSON.stringify(f.options.data),camera=f.ctl.state().camera;
    f.host.emit('click',f.host.target({'data-gmap-mode':mode}));const graph=f.host.querySelector('.gmap-graph');
    graph.emit('pointerdown',{button:0,pointerId:50,clientX:100,clientY:100});
    graph.emit('pointermove',{pointerId:50,clientX:145,clientY:70});graph.emit('pointerup',{pointerId:50});
    assert.deepEqual(f.ctl.state().pan,{x:45,y:-30});assert.deepEqual(f.ctl.state().camera,camera);
    assert.equal(JSON.stringify(f.options.data),data);assert.match(graph.innerHTML,/transform:translate\(45px,-30px\)/);
    assert.equal(f.calls.length,0);f.ctl.destroy();
  }
});

test('world-tree, rules and ordinary module overviews share blank-space panning without guessed links',()=>{
  for(const [kind,data] of [['archives',archiveFixture()],['rules',{sections:[]}],['module',{items:[{name:'规范.md',path:'规范.md'}]}],['index',{items:[{label:'已有记录'}]}]]){
    const f=controllerFixture();f.options={...f.options,kind,module:'临时模块',data};f.ctl.update(f.options,f.helpers);
    const before=JSON.stringify(data),graph=f.host.querySelector('.gmap-graph'),initialPan=f.ctl.state().pan;
    graph.emit('pointerdown',{button:0,pointerId:51,clientX:20,clientY:30});graph.emit('pointermove',{pointerId:51,clientX:-30,clientY:60});graph.emit('pointerup',{pointerId:51});
    assert.deepEqual(f.ctl.state().pan,{x:initialPan.x-50,y:initialPan.y+30});assert.equal(JSON.stringify(data),before);assert.equal(f.calls.length,0);f.ctl.destroy();
  }
});

test('2D dragging starts only on blank space, ordinary node clicks still read, and drag release cannot select',()=>{
  const f=controllerFixture(),goal=nodes(build(f.options.data),'goal')[0],graph=f.host.querySelector('.gmap-graph'),target=f.host.target({'data-gmap-node':goal.id});
  graph.emit('pointerdown',{target,button:0,pointerId:52,clientX:20,clientY:20});graph.emit('pointermove',{pointerId:52,clientX:60,clientY:70});graph.emit('pointerup',{pointerId:52});
  assert.deepEqual(f.ctl.state().pan,{x:0,y:0});f.host.emit('click',target);assert.equal(f.ctl.state().selected,goal.id);
  graph.emit('pointerdown',{button:0,pointerId:53,clientX:20,clientY:20});graph.emit('pointermove',{pointerId:53,clientX:70,clientY:90});graph.emit('pointerup',{pointerId:53});
  const other=nodes(build(f.options.data),'goal')[1];f.host.emit('click',f.host.target({'data-gmap-node':other.id}));assert.equal(f.ctl.state().selected,goal.id);
  assert.equal(graph.classList.contains('dragging'),false);f.ctl.destroy();
});

test('pan and resized reading dimensions survive selection and refresh; fit resets only the camera offset',()=>{
  const f=controllerFixture(),goal=nodes(build(f.options.data),'goal')[0],graph=f.host.querySelector('.gmap-graph'),grip=f.host.querySelector('[data-gmap-size]');
  f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));
  grip.emit('pointerdown',{button:0,pointerId:54,clientX:0,clientY:0});grip.emit('pointermove',{pointerId:54,clientX:30,clientY:100});grip.emit('pointerup',{pointerId:54});
  assert.deepEqual(f.ctl.state().panelSize,{w:360,h:520});assert.equal(f.host.querySelector('.gmap-reading').style.height,'520px');
  graph.emit('pointerdown',{button:0,pointerId:55,clientX:0,clientY:0});graph.emit('pointermove',{pointerId:55,clientX:40,clientY:25});graph.emit('pointerup',{pointerId:55});
  f.ctl.update(f.options,f.helpers);assert.equal(f.ctl.state().selected,goal.id);assert.deepEqual(f.ctl.state().pan,{x:40,y:25});assert.deepEqual(f.ctl.state().panelSize,{w:360,h:520});
  f.host.emit('click',f.host.target({'data-gmap-zoom':'fit'}));assert.deepEqual(f.ctl.state().pan,{x:0,y:0});assert.equal(f.ctl.state().selected,goal.id);assert.deepEqual(f.ctl.state().panelSize,{w:360,h:520});f.ctl.destroy();
});

test('normal reading corners shrink with limits and keyboard resizing, and never rewrite the body',()=>{
  const f=controllerFixture(),grip=f.host.querySelector('[data-gmap-size]'),body=f.host.querySelector('.gmap-reading-body');body.innerHTML='已有正文与标记';body.scrollTop=75;
  grip.emit('pointerdown',{button:0,pointerId:56,clientX:0,clientY:0});grip.emit('pointermove',{pointerId:56,clientX:-2000,clientY:-2000});grip.emit('pointerup',{pointerId:56});
  assert.deepEqual(f.ctl.state().panelSize,{w:180,h:120});grip.emit('keydown',{key:'ArrowRight'});grip.emit('keydown',{key:'ArrowDown',shiftKey:true});
  assert.deepEqual(f.ctl.state().panelSize,{w:188,h:152});assert.equal(body.innerHTML,'已有正文与标记');assert.equal(body.scrollTop,75);assert.equal(f.calls.length,0);f.ctl.destroy();assert.equal(grip.listeners.size,0);
});

test('fullscreen corner resizes the stored floating box, remains clamped and retains desired size on exit',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),grip=f.host.querySelector('[data-gmap-size]');
  f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();const before=f.ctl.state().panelBox;
  grip.emit('pointerdown',{button:0,pointerId:57,clientX:0,clientY:0});grip.emit('pointermove',{pointerId:57,clientX:-70,clientY:-100});grip.emit('pointerup',{pointerId:57});
  assert.equal(f.ctl.state().panelBox.w,before.w-70);assert.equal(f.ctl.state().panelBox.h,before.h-100);
  grip.emit('keydown',{key:'ArrowRight',shiftKey:true});assert.equal(f.ctl.state().panelBox.w,before.w-38);
  const desired={...f.ctl.state().panelSize};doc.emit('keydown',{key:'Escape'});assert.equal(f.ctl.state().fullscreen,false);assert.deepEqual(f.ctl.state().panelSize,desired);assert.equal(f.host.querySelector('.gmap-reading').style.height,desired.h+'px');
  f.ctl.destroy();assert.equal(grip.listeners.size,0);assert.equal(doc.defaultView.listeners.size,0);
});

test('switching project or module resets pan and reading size and cancels captured resize work',()=>{
  for(const scope of [{projectRoot:'C:/temporary/other'},{kind:'module',module:'另一模块',data:{items:[]}}]){
    const f=controllerFixture(),grip=f.host.querySelector('[data-gmap-size]'),graph=f.host.querySelector('.gmap-graph');
    grip.emit('keydown',{key:'ArrowDown',shiftKey:true});graph.emit('pointerdown',{button:0,pointerId:58,clientX:0,clientY:0});graph.emit('pointermove',{pointerId:58,clientX:80,clientY:50});
    grip.emit('pointerdown',{button:0,pointerId:59,clientX:0,clientY:0});f.ctl.update({...f.options,...scope},f.helpers);
    grip.emit('pointermove',{pointerId:59,clientX:300,clientY:300});graph.emit('pointermove',{pointerId:58,clientX:300,clientY:300});
    assert.deepEqual(f.ctl.state().pan,{x:0,y:0});assert.deepEqual(f.ctl.state().panelSize,{w:330,h:420});assert.equal(f.host.querySelector('.gmap-layout').style.gridTemplateColumns,'');f.ctl.destroy();
  }
});

test('reading corner sizing ignores another pointer and disposed controllers cannot be resized',()=>{
  const f=controllerFixture(),grip=f.host.querySelector('[data-gmap-size]');grip.emit('pointerdown',{button:0,pointerId:60,clientX:0,clientY:0});
  grip.emit('pointermove',{pointerId:61,clientX:50,clientY:50});assert.deepEqual(f.ctl.state().panelSize,{w:330,h:420});f.ctl.destroy();
  grip.emit('pointermove',{pointerId:60,clientX:50,clientY:50});assert.deepEqual(f.ctl.state().panelSize,{w:330,h:420});assert.equal(grip.listeners.size,0);assert.equal(f.host.querySelector('.gmap-graph').listeners.size,0);
});

function heightCorner(f){return f.host.querySelector('.gmap').children.find(el=>Object.hasOwn(el.dataset,'gmapHeight'));}
test('the real blueprint height corner preserves graph, selection, zoom, scroll and the independently sized reading pane',()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),corner=heightCorner(f),graph=f.host.querySelector('.gmap-graph'),goal=nodes(build(f.options.data),'goal')[0];
  f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));
  f.host.querySelector('[data-gmap-size]').emit('keydown',{key:'ArrowDown',shiftKey:true});graph.scrollTop=78;graph.scrollLeft=39;
  const before=f.ctl.state(),html=graph.innerHTML;corner.emit('pointerdown',{button:0,pointerId:70,clientY:0});corner.emit('pointermove',{pointerId:70,clientY:200});corner.emit('pointerup',{pointerId:70});
  assert.equal(f.ctl.state().frameHeight,600);assert.equal(graph.innerHTML,html);assert.equal(graph.scrollTop,78);assert.equal(graph.scrollLeft,39);assert.equal(f.ctl.state().selected,before.selected);assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().panelSize,before.panelSize);
  f.ctl.update(f.options,f.helpers);assert.equal(f.ctl.state().frameHeight,600);assert.deepEqual(f.ctl.state().panelSize,before.panelSize);f.ctl.destroy();assert.equal(corner.listeners.size,0);
});
test('fullscreen stops an active whole-frame drag, hides its corner, and restores ordinary height on exit',async()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),corner=heightCorner(f);corner.emit('keydown',{key:'ArrowDown',shiftKey:true});const height=f.ctl.state().frameHeight;
  corner.emit('pointerdown',{button:0,pointerId:71,clientY:0});f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.equal(corner.hidden,true);corner.emit('pointermove',{pointerId:71,clientY:500});assert.equal(f.ctl.state().frameHeight,height);
  doc.emit('keydown',{key:'Escape'});assert.equal(corner.hidden,false);assert.equal(f.ctl.state().frameHeight,height);f.ctl.destroy();
});
test('changing project cancels whole-frame resize; other module overviews do not gain an unrequested corner',()=>{
  const doc=new FakeDocument(),f=controllerFixture({document:doc}),corner=heightCorner(f);corner.emit('pointerdown',{button:0,pointerId:72,clientY:0});f.ctl.update({...f.options,projectRoot:'C:/别的项目'},f.helpers);corner.emit('pointermove',{pointerId:72,clientY:500});assert.equal(f.ctl.state().frameHeight,null);
  f.ctl.update({...f.options,kind:'rules',data:{sections:[]}},f.helpers);assert.equal(corner.hidden,true);assert.equal(corner.listeners.size,0);f.ctl.destroy();
});

function wheelAt(graph,deltaY,point={x:150,y:100},extra={}){
  let prevented=0,stopped=0;
  graph.emit('wheel',{deltaY,deltaMode:0,clientX:point.x,clientY:point.y,preventDefault(){prevented++;},stopPropagation(){stopped++;},...extra});
  return {prevented,stopped};
}
function near(actual,expected){assert.ok(Math.abs(actual-expected)<1e-8,actual+' differs from '+expected);}

test('blueprint and world-tree canvases hide scrollbars while reading stays scrollable and other overviews keep their original viewport',()=>{
  const doc=new FakeDocument(),a=controllerFixture({document:doc}),b=archiveController({document:doc});
  assert.ok(a.host.querySelector('.gmap').classList.contains('gmap-wheel-canvas'));assert.ok(b.host.querySelector('.gmap').classList.contains('gmap-wheel-canvas'));
  const css=doc.styles[0].textContent;assert.ok(css.includes('.gmap.gmap-wheel-canvas .gmap-canvas,.gmap.gmap-wheel-canvas .gmap-graph{overflow:hidden}'));assert.ok(css.includes('.gmap .gmap-reading-body{padding:.85rem;overflow:auto;'));
  a.ctl.update({...a.options,kind:'rules',data:{sections:[]}},a.helpers);assert.ok(!a.host.querySelector('.gmap').classList.contains('gmap-wheel-canvas'));
  const graph=a.host.querySelector('.gmap-graph'),prior=a.ctl.state(),result=wheelAt(graph,-80);assert.equal(result.prevented,0);assert.equal(a.ctl.state().zoom,prior.zoom);assert.deepEqual(a.ctl.state().pan,prior.pan);a.ctl.destroy();b.ctl.destroy();
});

test('actual wheel zoom keeps the pointer content anchored for blueprint and world tree without reading or source changes',()=>{
  for(const make of [controllerFixture,archiveController]){
    const f=make(),graph=f.host.querySelector('.gmap-graph'),reading=f.host.querySelector('.gmap-reading-body'),data=JSON.stringify(f.options.data);
    graph.getBoundingClientRect=()=>({left:120,top:80});graph.clientLeft=1;graph.clientTop=2;reading.innerHTML='synthetic unchanged reading';reading.scrollTop=43;
    graph.scrollLeft=21;graph.scrollTop=31;const before=f.ctl.state(),anchor={x:159,y:98},world={x:(anchor.x+21-before.pan.x)/before.zoom,y:(anchor.y+31-before.pan.y)/before.zoom};
    const result=wheelAt(graph,-80,{x:280,y:180}),after=f.ctl.state();assert.ok(after.zoom>before.zoom);near(world.x*after.zoom+after.pan.x,anchor.x);near(world.y*after.zoom+after.pan.y,anchor.y);
    assert.equal(graph.scrollLeft,0);assert.equal(graph.scrollTop,0);assert.equal(result.prevented,1);assert.equal(result.stopped,1);assert.deepEqual(graph.listenerOptions.get('wheel'),{passive:false});assert.equal(reading.innerHTML,'synthetic unchanged reading');assert.equal(reading.scrollTop,43);assert.equal(JSON.stringify(f.options.data),data);assert.equal(f.calls.length,0);f.ctl.destroy();
  }
});

test('wheel normalizes pixel, line and page deltas, ignores invalid deltas, and clamps the existing zoom limits',()=>{
  const zooms=[];
  for(const [deltaY,deltaMode] of [[-16,0],[-1,1],[-.04,2]]){const f=controllerFixture(),graph=f.host.querySelector('.gmap-graph');wheelAt(graph,deltaY,{x:170,y:120},{deltaMode});zooms.push(f.ctl.state().zoom);f.ctl.destroy();}
  near(zooms[0],zooms[1]);near(zooms[0],zooms[2]);
  const f=controllerFixture(),graph=f.host.querySelector('.gmap-graph');for(const deltaY of [0,NaN,Infinity,-Infinity]){const before=f.ctl.state();assert.equal(wheelAt(graph,deltaY).prevented,0);assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().pan,before.pan);}
  for(let i=0;i<50;i++)wheelAt(graph,-1000);assert.equal(f.ctl.state().zoom,3);const max=f.ctl.state();wheelAt(graph,-1000);assert.deepEqual(f.ctl.state().pan,max.pan);
  for(let i=0;i<50;i++)wheelAt(graph,1000);assert.equal(f.ctl.state().zoom,.5);const min=f.ctl.state();wheelAt(graph,1000);assert.deepEqual(f.ctl.state().pan,min.pan);assert.equal(f.calls.length,0);f.ctl.destroy();
});

test('wheel and existing pointer drag share pan without capturing a click, while fit and reset retain reading and selection',()=>{
  const f=controllerFixture(),graph=f.host.querySelector('.gmap-graph'),goal=nodes(build(f.options.data),'goal')[0];f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));const reading=f.host.querySelector('.gmap-reading-body'),text=reading.innerHTML;
  graph.emit('pointerdown',{button:0,pointerId:81,clientX:10,clientY:20});graph.emit('pointermove',{pointerId:81,clientX:30,clientY:30});wheelAt(graph,-80);const wheelPan=f.ctl.state().pan;
  graph.emit('pointermove',{pointerId:81,clientX:35,clientY:37});near(f.ctl.state().pan.x,wheelPan.x+5);near(f.ctl.state().pan.y,wheelPan.y+7);graph.emit('pointerup',{pointerId:81});assert.ok(!graph.classList.contains('dragging'));
  f.host.emit('click',f.host.target({'data-gmap-zoom':'fit'}));assert.deepEqual(f.ctl.state().pan,{x:0,y:0});assert.equal(graph.scrollTop,0);assert.equal(graph.scrollLeft,0);assert.equal(f.ctl.state().selected,goal.id);assert.equal(reading.innerHTML,text);
  f.host.emit('click',f.host.target({'data-gmap-zoom':'reset'}));assert.equal(f.ctl.state().zoom,1);assert.deepEqual(f.ctl.state().pan,{x:0,y:0});assert.equal(f.calls.length,0);f.ctl.destroy();
});

test('toolbar zoom on hidden-scroll canvases anchors their viewport center instead of writing hidden scroll offsets',()=>{
  const f=controllerFixture(),graph=f.host.querySelector('.gmap-graph');graph.emit('pointerdown',{button:0,pointerId:82,clientX:0,clientY:0});graph.emit('pointermove',{pointerId:82,clientX:30,clientY:20});graph.emit('pointerup',{pointerId:82});const before=f.ctl.state(),x=graph.clientWidth/2,y=graph.clientHeight/2,world={x:(x-before.pan.x)/before.zoom,y:(y-before.pan.y)/before.zoom};
  f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));const after=f.ctl.state();near(world.x*after.zoom+after.pan.x,x);near(world.y*after.zoom+after.pan.y,y);assert.equal(graph.scrollTop,0);assert.equal(graph.scrollLeft,0);f.ctl.destroy();
});

test('wheel views preserve zoom, pan and reading on refresh and mode changes, with the original project-change reset',()=>{
  const doc=new FakeDocument();let configured='map';const f=controllerFixture({document:doc,helpers:{overviewMode:()=>configured}}),graph=f.host.querySelector('.gmap-graph'),goal=nodes(build(f.options.data),'goal')[0];f.host.emit('click',f.host.target({'data-gmap-node':goal.id}));const reading=f.host.querySelector('.gmap-reading-body');reading.scrollTop=77;wheelAt(graph,-80);const before=f.ctl.state(),text=reading.innerHTML;
  f.ctl.update(f.options,f.helpers);assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().pan,before.pan);assert.equal(f.ctl.state().selected,before.selected);assert.equal(reading.innerHTML,text);assert.equal(reading.scrollTop,77);
  for(const next of ['flow','model3d']){configured=next;doc.defaultView.emit('research-overview-mode',{detail:{mode:next}});assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().pan,before.pan);assert.equal(f.ctl.state().selected,goal.id);assert.equal(reading.innerHTML,text);const prior=f.ctl.state(),point={x:180,y:130},world={x:(point.x-prior.pan.x)/prior.zoom,y:(point.y-prior.pan.y)/prior.zoom};wheelAt(graph,-20,point);const after=f.ctl.state();near(world.x*after.zoom+after.pan.x,point.x);near(world.y*after.zoom+after.pan.y,point.y);assert.ok(graph.innerHTML.includes('transform:translate('+after.pan.x+'px,'+after.pan.y+'px)'));wheelAt(graph,20,point);}
  f.ctl.update({...f.options,projectRoot:'C:/temporary/new-project'},f.helpers);assert.equal(f.ctl.state().selected,'');assert.equal(f.ctl.state().zoom,1);assert.deepEqual(f.ctl.state().pan,{x:0,y:0});assert.ok(f.host.querySelector('.gmap').classList.contains('gmap-wheel-canvas'));assert.equal(f.calls.length,0);f.ctl.destroy();
});

test('wheel remains anchored in native and fallback fullscreen, leaves detail scrolling alone, and releases the listener on dispose',async()=>{
  for(const fallback of [false,true]){const doc=new FakeDocument(),f=controllerFixture({document:doc}),graph=f.host.querySelector('.gmap-graph'),component=f.host.querySelector('.gmap');component.requestFullscreen=()=>fallback?Promise.reject(new Error('denied')):(doc.fullscreenElement=component,doc.emit('fullscreenchange'),Promise.resolve());f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.equal(f.ctl.state().fullscreen,true);
    graph.clientWidth=1000;graph.clientHeight=700;graph.getBoundingClientRect=()=>({left:40,top:90});const prior=f.ctl.state(),point={x:410,y:330},world={x:(point.x-prior.pan.x)/prior.zoom,y:(point.y-prior.pan.y)/prior.zoom};wheelAt(graph,-80,{x:450,y:420});const next=f.ctl.state();near(world.x*next.zoom+next.pan.x,point.x);near(world.y*next.zoom+next.pan.y,point.y);
    const reading=f.host.querySelector('.gmap-reading-body');assert.ok(!reading.listeners.has('wheel'));doc.emit('keydown',{key:'Escape'});f.ctl.destroy();assert.ok(!graph.listeners.has('wheel'));assert.ok(!graph.listenerOptions.has('wheel'));const state=f.ctl.state();assert.equal(wheelAt(graph,-80).prevented,0);assert.deepEqual(f.ctl.state(),state);
  }
});

test('a stale or detached map does not consume a wheel event or alter its view',()=>{
  const f=controllerFixture(),graph=f.host.querySelector('.gmap-graph'),before=f.ctl.state();f.host.isConnected=false;assert.equal(wheelAt(graph,-80).prevented,0);assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().pan,before.pan);f.ctl.destroy();
});
