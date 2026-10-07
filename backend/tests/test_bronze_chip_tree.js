'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const map=require(process.env.BRONZE_CHIP_TREE_SOURCE||path.resolve(__dirname,'../../治理界面.js'));
const ROOT='C:/temporary/bronze-chip-fixture';
function fixture(count=3,branchCount=1){
  const timeline=[];for(let i=1;i<=count;i++)timeline.push({code:'C'+i,name:'长名称'+i,at:'2026-10-'+String(i).padStart(2,'0')+'T10:00:00',prev:i===1?'':'C'+(i-1)});
  timeline.push({code:'现在',name:'未保存的长名称',prev:'C'+count});
  const branches=[];for(let i=1;i<=branchCount;i++)branches.push({code:'枝-'+i,name:'长工作树名称'+i,path:'C:/temporary/bronze-branch-'+i,base:'C1',state:'合了',at:'2026-10-01T16:00:00',fruit_checkpoint:'C'+i,fruit_at:'2026-10-02T16:00:00',demo:'实际果实演示'+i,merged:{after:'C3'}});
  return {timeline:{nodes:timeline},world:{branches}};
}
const build=data=>map.build('archives',data,{projectRoot:ROOT,projectName:'夹具项目'});
const of=(m,kind)=>m.nodes.filter(n=>n.kind===kind);
class Element{
  constructor(owner,attrs={}){this.owner=owner;this.ownerDocument=owner&&owner.ownerDocument;this.attrs={...attrs};this.dataset={};this.style={};this.innerHTML='';this.textContent='';this.listeners=new Map();this.scrollTop=0;this.scrollLeft=0;this.clientWidth=900;this.clientHeight=650;this.hidden=false;this.value='';this.children=[];const classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>classes.add(x)),remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x)};for(const[k,v]of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;}
  hasAttribute(k){return Object.hasOwn(this.attrs,k);}setAttribute(k,v){this.attrs[k]=v;}closest(){return this;}matches(){return false;}
  appendChild(n){if(n.parentNode&&n.parentNode.children)n.parentNode.children=n.parentNode.children.filter(x=>x!==n);this.children.push(n);n.parentNode=this;return n;}
  addEventListener(t,fn){this.listeners.set(t,fn);}removeEventListener(t,fn){if(this.listeners.get(t)===fn)this.listeners.delete(t);}querySelectorAll(){return [];}
  emit(t,e={}){this.listeners.get(t)?.({target:this,preventDefault(){},...e});}
}
class Host extends Element{
  constructor(doc){super(null);this.owner=this;this.ownerDocument=doc;this.parts=new Map();this.isConnected=true;}
  querySelector(s){if(!this.parts.has(s))this.parts.set(s,new Element(this));return this.parts.get(s);}contains(n){return n.owner===this;}target(a){return new Element(this,a);}
  emit(t,target,e={}){this.listeners.get(t)?.({target,preventDefault(){},...e});}
}
class Signal{
  constructor(){this.listeners=new Map();}addEventListener(t,fn){if(!this.listeners.has(t))this.listeners.set(t,new Set());this.listeners.get(t).add(fn);}removeEventListener(t,fn){this.listeners.get(t)?.delete(fn);}emit(t,e={}){for(const fn of this.listeners.get(t)||[])fn({preventDefault(){},...e});}
}
class Document extends Signal{
  constructor(){super();this.defaultView=new Signal();this.styles=[];this.body=new Element(null);this.fullscreenElement=null;this.head={appendChild:s=>this.styles.push(s)};}
  getElementById(id){return this.styles.find(s=>s.id===id);}createElement(){const el=new Element(null);el.ownerDocument=this;return el;}exitFullscreen(){this.fullscreenElement=null;this.emit('fullscreenchange');return Promise.resolve();}
}
function mountFixture(data=fixture(),extra={}){
  const doc=extra.doc||new Document(),host=new Host(doc),calls=[],options={kind:'archives',data,projectRoot:ROOT,projectName:'夹具项目'},helpers={language:()=> 'en',isCurrent:()=>host.isConnected,request:async(method,url)=>{calls.push([method,url]);return {counts:{},files:{}};},...extra.helpers};
  const ctl=map.mount(host,options,helpers);return {doc,host,ctl,options,helpers,calls};
}
const flush=async()=>{await Promise.resolve();await Promise.resolve();await Promise.resolve();};

test('all main checkpoints and the project share one exact center axis, without counts affecting radii',()=>{
  const data=fixture(),m=build(data),s=map.worldLayout(m,map.worldVisible(m).nodes),main=m.nodes.filter(n=>['checkpoint','now','project'].includes(n.kind));assert.equal(new Set(main.map(n=>s.positions.get(n.id).x)).size,1);assert.equal(s.nodeRadius,7);
  data.timeline.nodes[0].counts={files:100000};const other=map.worldLayout(build(data),map.worldVisible(build(data)).nodes);assert.equal(other.nodeRadius,s.nodeRadius);
});
test('every source uses the same exact quarter-circle H A40 V tangent geometry',()=>{
  const m=build(fixture(3,12)),s=map.worldLayout(m,m.nodes),sources=s.curves.filter(c=>c.type==='source');assert.equal(sources.length,12);
  for(const c of sources){const a=s.positions.get(c.from),b=s.positions.get(c.to),v=c.d.match(/^M ([\d.]+) ([\d.]+) H ([\d.]+) A 40 40 0 0 ([01]) ([\d.]+) ([\d.]+) V ([\d.]+)$/);assert.ok(v,c.d);const side=b.x>a.x?1:-1;assert.equal(+v[1],a.x);assert.equal(+v[2],a.y+7);assert.equal(+v[3],b.x-side*40);assert.equal(+v[4],side<0?1:0);assert.equal(+v[5],b.x);assert.equal(+v[6],a.y+7-40);assert.equal(+v[7],b.y);assert.ok(b.y<+v[6]);assert.equal(c.radius,40);}
});
test('twelve branches from one base use twelve separate vertical columns with circle and label clearance',()=>{
  const m=build(fixture(3,12)),s=map.worldLayout(m,m.nodes),branches=of(m,'branch');const xs=branches.map(n=>s.positions.get(n.id).x);assert.equal(new Set(xs).size,12);
  for(let i=0;i<xs.length;i++)for(let j=i+1;j<xs.length;j++)assert.ok(Math.abs(xs[i]-xs[j])>=140);
  const entities=m.nodes.filter(n=>n.kind!=='project');for(let i=0;i<entities.length;i++)for(let j=i+1;j<entities.length;j++){const a=s.positions.get(entities[i].id),b=s.positions.get(entities[j].id);assert.ok(Math.abs(a.x-b.x)>=140||Math.abs(a.y-b.y)>=18,'Node clearance: '+entities[i].key+' / '+entities[j].key);}
});
test('real event times put branch and fruit in their correct timeline intervals, with fruit in its own column',()=>{
  const m=build(fixture()),s=map.worldLayout(m,m.nodes),byCode=k=>s.positions.get(m.nodes.find(n=>n.kind==='checkpoint'&&n.key===k).id),branch=s.positions.get(of(m,'branch')[0].id),fruit=s.positions.get(of(m,'fruit')[0].id);
  assert.ok(byCode('C1').y>branch.y&&branch.y>byCode('C2').y);assert.ok(byCode('C2').y>fruit.y&&fruit.y>byCode('C3').y);assert.equal(fruit.x,branch.x);assert.equal(branch.timeStatus,'recorded');assert.equal(fruit.timeStatus,'recorded');
});
test('unknown and contradictory times are explicit and never become a made-up timestamp',()=>{
  const data=fixture();delete data.world.branches[0].at;delete data.world.branches[0].fruit_at;let m=build(data),s=map.worldLayout(m,m.nodes);for(const n of m.nodes.filter(n=>['branch','fruit'].includes(n.kind))){assert.equal(s.positions.get(n.id).timeStatus,'unrecorded');assert.equal(s.positions.get(n.id).time,'');}
  data.world.branches[0].at='2026-09-30T12:00:00';data.world.branches[0].fruit_at='2026-09-29T12:00:00';m=build(data);s=map.worldLayout(m,m.nodes);for(const n of m.nodes.filter(n=>['branch','fruit'].includes(n.kind)))assert.equal(s.positions.get(n.id).timeStatus,'before-source');
});
test('partial views compress displayed rows but preserve real sources and same-set positions',()=>{
  const data=fixture(155,3),m=build(data),all=map.worldLayout(m,m.nodes),fruit=of(m,'fruit')[1],v=map.worldVisible(m,{query:fruit.key}),partial=map.worldLayout(m,v.nodes),again=map.worldLayout(m,v.nodes);
  assert.ok(v.nodes.some(n=>n.kind==='checkpoint'&&n.key==='C1'));assert.ok(partial.height<all.height);assert.ok(partial.partial);assert.deepEqual(partial,again);
  const branch=of(m,'branch')[0],withoutBase=map.worldLayout(m,[branch,of(m,'fruit')[0]]);assert.ok(!withoutBase.orphans.includes(branch.id));assert.ok(!withoutBase.curves.some(c=>c.type==='source'));assert.equal(withoutBase.positions.get(branch.id).timeStatus,'recorded');
});
test('missing sources stand apart; every real relationship curve has both visible actual endpoints',()=>{
  const data=fixture();data.world.branches.push({code:'枝-404',path:'C:/temporary/missing',base:'C404',fruit_checkpoint:'C1'});const m=build(data),v=map.worldVisible(m,{limit:100}),s=map.worldLayout(m,v.nodes),ids=new Set(v.nodes.map(n=>n.id)),orphan=of(m,'branch').find(n=>n.key==='枝-404');assert.ok(s.orphans.includes(orphan.id));assert.ok(s.positions.get(orphan.id).orphan);assert.ok(!s.curves.some(c=>c.to===orphan.id));
  for(const c of s.curves){assert.ok(ids.has(c.from)&&ids.has(c.to));assert.ok(m.edges.some(e=>e.from===c.from&&e.to===c.to&&e.type===c.type));assert.ok(!['merge','merged'].includes(c.type));}
});
test('branch-local C numbers never alias the main checkpoint or another branch-local fruit',()=>{
  const data=fixture(3,2);data.world.branches.forEach(b=>b.fruit_checkpoint='C1');const m=build(data),main=of(m,'checkpoint').find(n=>n.key==='C1'),fruits=of(m,'fruit');assert.equal(new Set([main.id,...fruits.map(n=>n.id)]).size,3);assert.ok(fruits.every(n=>map.previewURL(n)===''));assert.ok(of(m,'checkpoint').find(n=>n.key==='C3').mergeNotes.every(n=>n.fruit==='C1'));
});
test('SVG default text is compact IDs; complete labels remain in accessible titles and existing reading',async()=>{
  const f=mountFixture(),html=f.host.querySelector('.gmap-graph').innerHTML,shown=[...html.matchAll(/<text[^>]*>(.*?)<\/text>/g)].map(m=>m[1]);assert.ok(shown.includes('C1'));assert.ok(shown.includes('枝-1'));assert.ok(!shown.some(s=>s.includes('长工作树名称')||s.includes('长名称')||s.includes('2026-')));assert.ok(html.includes('长工作树名称1'));assert.ok(!html.includes('gmap-world-leaf'));assert.ok(!html.includes('<rect'));const branch=of(build(f.options.data),'branch')[0];f.host.emit('click',f.host.target({'data-gmap-node':branch.id}));await flush();assert.ok(f.host.querySelector('.gmap-reading-body').innerHTML.includes('长工作树名称1'));assert.equal(f.calls.length,0);f.ctl.destroy();
});
test('all merged fruits are visible notes on the target, with no invented merge-back path',()=>{
  const f=mountFixture(fixture(3,3)),html=f.host.querySelector('.gmap-graph').innerHTML;for(let i=1;i<=3;i++)assert.ok(html.includes('Merged 枝-'+i+' / C'+i));assert.ok(!html.includes('gmap-world-curve merge'));assert.equal(f.calls.length,0);f.ctl.destroy();
});
test('same-model refresh reuses the component, graph, viewport, reading pane and camera state',async()=>{
  const f=mountFixture(),graph=f.host.querySelector('.gmap-graph'),component=f.host.querySelector('.gmap'),reading=f.host.querySelector('.gmap-reading-body'),branch=of(build(f.options.data),'branch')[0];f.host.emit('click',f.host.target({'data-gmap-node':branch.id}));await flush();reading.scrollTop=31;graph.scrollTop=123;graph.scrollLeft=45;f.host.emit('click',f.host.target({'data-gmap-zoom':'in'}));graph.emit('pointerdown',{button:0,pointerId:7,clientX:10,clientY:10});graph.emit('pointermove',{pointerId:7,clientX:60,clientY:35});graph.emit('pointerup',{pointerId:7});const before=f.ctl.state(),viewport={top:graph.scrollTop,left:graph.scrollLeft};f.ctl.update(f.options,f.helpers);assert.equal(f.host.querySelector('.gmap'),component);assert.equal(f.host.querySelector('.gmap-graph'),graph);assert.equal(f.host.querySelector('.gmap-reading-body'),reading);assert.equal(reading.scrollTop,31);assert.equal(graph.scrollTop,viewport.top);assert.equal(graph.scrollLeft,viewport.left);assert.equal(f.ctl.state().zoom,before.zoom);assert.deepEqual(f.ctl.state().pan,before.pan);assert.equal(f.ctl.state().selected,before.selected);f.ctl.destroy();
});
test('fullscreen notes move only on explicit request and return intact while the viewport remains the same',async()=>{
  const doc=new Document(),note=new Element(null);note.innerHTML='夹具笔记';doc.body.appendChild(note);let noteCalls=0;const f=mountFixture(fixture(),{doc,helpers:{notes:()=>{noteCalls++;return note;}}}),component=f.host.querySelector('.gmap'),graph=f.host.querySelector('.gmap-graph');component.requestFullscreen=()=>{doc.fullscreenElement=component;return Promise.resolve();};f.host.emit('click',f.host.target({'data-gmap-full':''}));await flush();assert.equal(noteCalls,0);f.host.emit('click',f.host.target({'data-gmap-notes':''}));assert.equal(note.parentNode,component);f.ctl.update(f.options,f.helpers);assert.equal(f.host.querySelector('.gmap-graph'),graph);assert.equal(note.parentNode,component);doc.emit('keydown',{key:'Escape'});assert.equal(note.parentNode,doc.body);assert.equal(note.innerHTML,'夹具笔记');f.ctl.destroy();
});
test('zero, one and sixty checkpoints with orphan records remain finite inside the canvas without fabricated IDs',()=>{
  for(const count of [0,1,60]){const data=fixture(count,0);data.world.branches.push({code:'枝-未知',base:'C404',path:'C:/temporary/unlinked'});const before=JSON.stringify(data),m=build(data),s=map.worldLayout(m,m.nodes);assert.equal(JSON.stringify(data),before);assert.ok(!m.nodes.some(n=>n.key==='C404'));for(const p of s.positions.values())assert.ok([p.x,p.y,p.z].every(Number.isFinite)&&p.x>=0&&p.x<s.width&&p.y>=0&&p.y<s.height);}
});

test('155 checkpoints default to eight records plus the root in a compact visible canvas',()=>{const m=build(fixture(155,0)),v=map.worldVisible(m),s=map.worldLayout(m,v.nodes);assert.equal(v.nodes.filter(n=>['checkpoint','now'].includes(n.kind)).length,8);assert.ok(v.more);assert.equal(s.width,640);assert.ok(s.height<=650);assert.ok(s.axis.x>0&&s.axis.x<640);assert.ok(s.axis.bottom<s.height);});
test('three branches and different real sources retain distinct compact lanes and real source paths',()=>{const data=fixture(7,3);data.world.branches.forEach((b,i)=>{b.base='C'+(i+1);b.at='2026-10-'+String(i+1).padStart(2,'0')+'T16:00:00';b.fruit_at='2026-10-'+String(i+2).padStart(2,'0')+'T16:00:00';});const m=build(data),v=map.worldVisible(m),s=map.worldLayout(m,v.nodes);assert.ok(s.width>=600&&s.width<=800);assert.equal(new Set(of(m,'branch').map(n=>s.positions.get(n.id).x)).size,3);for(const c of s.curves.filter(c=>c.type==='source'))assert.ok(m.edges.some(e=>e.from===c.from&&e.to===c.to&&e.type==='source'));});
test('first world render fits the current viewport and the axis is horizontally visible without dragging',()=>{const f=mountFixture(fixture(155,0)),graph=f.host.querySelector('.gmap-graph'),html=graph.innerHTML,m=build(f.options.data),s=map.worldLayout(m,map.worldVisible(m).nodes),state=f.ctl.state();assert.ok(s.axis.x*state.zoom+state.pan.x>=0&&s.axis.x*state.zoom+state.pan.x<graph.clientWidth);assert.ok(state.zoom<=1);assert.ok(s.height*state.zoom<=graph.clientHeight);assert.equal(graph.scrollLeft,0);assert.ok(state.pan.x>=0);assert.ok(html.includes('Partial view'));f.ctl.destroy();});
