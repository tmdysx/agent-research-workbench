'use strict';
// Verify real record relationships and liveness without scheduling or launching employees.
const test=require('node:test');
const assert=require('node:assert/strict');
const model=require('../../员工分配图.js');
const ROOT='C:/temporary/nonresearch-project';
function context(){return {online:true,errors:[],state:{project:{root:ROOT,name:'日常资料'}},roster:[
  {code:'G1',name:'统筹',roles:['规划','审核','验收','带队'],boss:'人',registered:true,holding:[]},
  {code:'G2',name:'施工甲',roles:['干活'],boss:'G1',registered:true,holding:[{goal:'S1-1',sub:'S2-1'}]},
  {code:'G3',name:'施工乙',roles:['干活'],boss:'G1',registered:true,holding:[{goal:'S1-2',sub:'S2-1'}]}],
  board:{items:[{key:'S1-1 S2-1',goal:'S1-1',code:'S2-1',who:'agent:施工甲',col:'在做',what:'资料整理'},
    {key:'S1-2 S2-1',goal:'S1-2',code:'S2-1',who:'施工乙',col:'在做',what:'清单核对'},
    {key:'S1-1 S2-2',goal:'S1-1',code:'S2-2',who:'',col:'能做',eligible:[{code:'G3',allowed:true}]}]},
  launch:{on:true,pause:'',plans:[],status:[{code:'G2',status:'running',action:'execute',current:{task:{goal:'S1-1',sub:'S2-1'}}}],
    windows:[{id:'w2',agent_code:'G2',project_root:ROOT,alive:true,task_key:'S1-1 S2-1'}]},deliveries:[]};}

test('actual bosses and full task keys produce distinct relationships without inventing an assignment',()=>{
  const m=model.build(context());assert.deepEqual(m.hierarchy.map(e=>[e.from,e.to]),[['agent:G1','agent:G2'],['agent:G1','agent:G3']]);
  assert.deepEqual(m.ownership.map(e=>[e.from,e.key]),[['agent:G2','S1-1 S2-1'],['agent:G3','S1-2 S2-1']]);
  assert.equal(m.tasks[2].ownerId,'');assert.equal(m.counts.unassigned,1);assert.equal(m.counts.active,1);
});
test('eligible candidates do not become owners',()=>{
  const c=context();c.roster.forEach(p=>p.holding=[]);c.board.items.forEach(t=>{t.who='';t.eligible=[{code:'G2',allowed:true}];});const m=model.build(c);
  assert.equal(m.ownership.length,0);assert.equal(m.counts.assigned,0);assert.equal(m.counts.unassigned,3);
});
test('an empty project keeps no fake people, bosses, tasks or runtime records',()=>{
  const m=model.build({state:{project:{root:ROOT}},roster:[],board:{items:[]},launch:{},deliveries:[]});
  assert.equal(m.people.length,0);assert.equal(m.tasks.length,0);assert.equal(m.hierarchy.length,0);assert.equal(m.counts.active,0);
  assert.equal(model.layout(m).nodes.filter(n=>n.kind==='person').length,0);assert.equal(m.stages.length,4);
});
test('fixed protocol stages are separate from actual employee relationships',()=>{
  const m=model.build(context()), l=model.layout(m);assert.equal(l.phases.length,4);assert.ok(l.phases.every(n=>n.kind!=='person'&&n.id.startsWith('stage:')));
  assert.ok(l.edges.every(e=>e.kind==='boss'&&e.from.startsWith('agent:')&&e.to.startsWith('agent:')));
});
test('legacy complete current string resolves but a bare S2 and a title never resolve',()=>{
  const c=context();assert.equal(model.currentTaskKey({current:'S1-2 S2-1'},c),'S1-2 S2-1');
  for(const current of ['S2-1','清单核对',null,{}, {task:{sub:'S2-1'}}])assert.equal(model.currentTaskKey({current},c),'');
});
test('plan and delivery references resolve only through a unique recorded full task',()=>{
  const c=context();c.launch.plans=[{code:'施-1',goal:'S1-1',sub:'S2-1'}];c.deliveries=[{code:'J1',goal:'S1-2',sub:'S2-1'}];
  assert.equal(model.currentTaskKey({current:{construction_plan:'施-1'}},c),'S1-1 S2-1');assert.equal(model.currentTaskKey({current:{review:'J1'}},c),'S1-2 S2-1');
  c.launch.plans.push({code:'施-1',goal:'S1-2',sub:'S2-1'});assert.equal(model.currentTaskKey({current:{construction_plan:'施-1'}},c),'');
});
test('ambiguous employee names never link a task to whichever record appeared first',()=>{
  const c=context();c.roster[2].name='施工甲';c.roster.forEach(p=>p.holding=[]);const m=model.build(c);
  assert.equal(m.tasks[0].ownerId,'');assert.equal(m.tasks[0].assignment,'unresolved');assert.equal(model.resolveAgent('施工甲',m.people),null);
  assert.equal(model.resolveAgent('G2',m.people).code,'G2');
});
test('unknown actor and unknown boss remain explicit unresolved records',()=>{
  const c=context();c.board.items[2].who='不存在';c.roster[1].boss='G99';const m=model.build(c);
  assert.equal(m.tasks[2].assignment,'unresolved');assert.ok(m.issues.some(i=>i.kind==='owner'));assert.ok(m.issues.some(i=>i.kind==='boss'));assert.equal(m.hierarchy.length,1);
});
test('a self boss creates no self loop',()=>{
  const c=context();c.roster[1].boss='G2';const m=model.build(c);assert.ok(!m.hierarchy.some(e=>e.from===e.to));assert.ok(m.issues.some(i=>i.kind==='boss'));
});
test('holding claim is explicit evidence only when it names a complete existing task',()=>{
  const c=context();c.board.items[0].who='';c.roster[1].holding.push({goal:'S1-1',sub:'S2-99'});const m=model.build(c);
  assert.equal(m.tasks[0].ownerId,'agent:G2');assert.deepEqual(m.people[1].missing,['S1-1 S2-99']);assert.equal(m.tasks.length,3);
});
test('conflicting owner and holding records are not silently repaired',()=>{
  const c=context();c.roster[2].holding.push({goal:'S1-1',sub:'S2-1'});const m=model.build(c);
  assert.equal(m.tasks[0].assignment,'unresolved');assert.equal(m.tasks[0].ownerId,'');assert.equal(m.people[1].active,null);
});
test('duplicate full task records cannot produce a confirmed run or ownership',()=>{
  const c=context();c.board.items.push({...c.board.items[0]});const m=model.build(c);
  assert.ok(m.tasks.filter(t=>t.key==='S1-1 S2-1').every(t=>t.assignment==='unresolved'));assert.equal(m.people[1].active,null);
});
for(const [label,change] of [
  ['offline',c=>{c.online=false;}],['failed refresh',c=>{c.errors=['offline'];}],['dispatch disabled',c=>{c.launch.on=false;}],
  ['paused project',c=>{c.launch.pause='人叫停';}],['paused employee',c=>{c.roster[1].paused=true;}],
  ['waiting runner',c=>{c.launch.status[0].status='waiting';}],['failed runner',c=>{c.launch.status[0].status='failed';}],
  ['no runner',c=>{c.launch.status=[];}],['no windows',c=>{c.launch.windows=[];}],['exited window',c=>{c.launch.windows[0].alive=false;}],
  ['unknown alive',c=>{delete c.launch.windows[0].alive;}],['different project',c=>{c.launch.windows[0].project_root='C:/other';}],
  ['different employee',c=>{c.launch.windows[0].agent_code='G3';}],['unknown current task',c=>{c.launch.status[0].current.task.sub='S2-99';}],
  ['task belongs to other employee',c=>{c.launch.status[0].current.task.goal='S1-2';}],['already completed task',c=>{c.board.items[0].col='做完';}],
  ['ambiguous runner records',c=>{c.launch.status.push({...c.launch.status[0]});}]
])test('animation is absent for '+label,()=>{const c=context();change(c);assert.equal(model.build(c).counts.active,0);});
test('a title mentioning an employee and project is not window binding evidence',()=>{
  const c=context();c.launch.windows=[{id:'w',alive:true,title:'G2 '+ROOT+' S1-1 S2-1'}];assert.equal(model.build(c).counts.active,0);
});
test('an employee window for another task or with no task binding cannot confirm this run',()=>{
  const c=context();c.launch.windows[0].task_key='S1-2 S2-1';assert.equal(model.build(c).counts.active,0);
  delete c.launch.windows[0].task_key;assert.equal(model.build(c).counts.active,0);
});
test('a cyclic boss configuration is marked and excluded from the valid hierarchy layout',()=>{
  const c=context();c.roster[0].boss='G2';const m=model.build(c);
  assert.equal(m.hierarchy.filter(e=>e.conflict).length,2);assert.equal(m.issues.filter(i=>i.kind==='boss-cycle').length,2);
  assert.equal(model.layout(m).edges.length,1);
});
test('independent plan reviewer can be confirmed using the real review target and living window',()=>{
  const c=context(),plan={code:'施-1',goal:'S1-1',sub:'S2-1',by:'agent:施工甲',state:'待审'};
  c.launch.plans=[plan];c.launch.status=[{code:'G1',status:'running',action:'review_plan',current:{construction_plan:plan}}];c.launch.windows=[{id:'review',agent_code:'G1',project_root:ROOT,alive:true,task_key:'S1-1 S2-1'}];
  const m=model.build(c);assert.equal(m.people[0].active.key,'S1-1 S2-1');assert.equal(m.pendingPlans.length,1);
});
test('self review and missing reviewer role never become confirmed activity',()=>{
  const c=context(),plan={code:'施-1',goal:'S1-1',sub:'S2-1',by:'agent:统筹',state:'待审'};
  c.launch.plans=[plan];c.launch.status=[{code:'G1',status:'running',action:'review_plan',current:{construction_plan:plan}}];c.launch.windows=[{id:'review',agent_code:'G1',project_root:ROOT,alive:true,task_key:'S1-1 S2-1'}];
  assert.equal(model.build(c).counts.active,0);plan.by='agent:施工甲';c.roster[0].roles=['带队'];assert.equal(model.build(c).counts.active,0);
});
test('an embedded review record must match a real unique pending record in the project',()=>{
  const c=context(),plan={code:'施-1',goal:'S1-1',sub:'S2-1',by:'agent:施工甲',state:'待审'};
  c.launch.status=[{code:'G1',status:'running',action:'review_plan',current:{construction_plan:plan}}];c.launch.windows=[{id:'review',agent_code:'G1',project_root:ROOT,alive:true,task_key:'S1-1 S2-1'}];
  assert.equal(model.build(c).counts.active,0);c.launch.plans=[{...plan}];assert.equal(model.build(c).counts.active,1);
  c.launch.plans[0].sub='S2-2';assert.equal(model.build(c).counts.active,0);c.launch.plans[0]={...plan,state:'通过'};assert.equal(model.build(c).counts.active,0);
  c.launch.plans=[{...plan},{...plan}];assert.equal(model.build(c).counts.active,0);
});
test('delivery pending and done are counted separately using recorded status',()=>{
  const c=context();c.deliveries=[{code:'J1',goal:'S1-1',sub:'S2-1',by:'agent:施工甲',state:'待你验收'},
    {code:'J2',goal:'S1-2',sub:'S2-1',by:'agent:施工乙',state:'验收通过'}];const m=model.build(c);
  assert.deepEqual(m.pendingDeliveries.map(d=>d.code),['J1']);assert.equal(m.people[1].deliveries[0].code,'J1');assert.equal(m.people[2].deliveries[0].code,'J2');
});
test('no researcher model, research workflow or numerical progress is fabricated by a nonresearch fixture',()=>{
  const c=context(),before=JSON.stringify(c),m=model.build(c);assert.equal(JSON.stringify(c),before);assert.equal(m.people[1].raw.program,undefined);
  assert.ok(!Object.hasOwn(m.people[1],'progress'));assert.ok(m.people.every(p=>p.tasks.every(t=>c.board.items.includes(t.raw))));
});
test('geometry preserves real employees and clamps floating details within the viewport',()=>{
  const l=model.layout(model.build(context()));assert.equal(l.nodes.filter(n=>n.kind==='person').length,3);assert.ok(l.nodes.every(n=>n.x>=0&&n.y>=0&&n.x+n.w<=l.width&&n.y+n.h<=l.height));
  for(const viewport of [{width:1280,height:800},{width:2,height:2}]){const p=model.clampPane({x:-999,y:9999,width:330,height:500},viewport);assert.ok(Object.values(p).every(Number.isFinite));assert.ok(p.x>=0&&p.y>=0&&p.x+p.width<=viewport.width&&p.y+p.height<=viewport.height);}
});

function memoryStorage(){const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),values};}
test('layout defaults are large and corrupt or extreme saved dimensions are safely bounded',()=>{
  const d=model.normalizeLayout();assert.equal(d.height,640);assert.equal(d.detail.height,560);
  const bad=model.normalizeLayout({height:Infinity,detail:{width:-100,height:99999},pose:{x:NaN,y:99999,s:-9},positions:{'agent:G2':{x:Infinity,y:2},'__proto__':{x:2,y:2}}});
  assert.equal(bad.height,640);assert.equal(bad.detail.width,260);assert.equal(bad.detail.height,1200);assert.equal(bad.pose.x,0);assert.equal(bad.pose.y,10000);assert.equal(bad.pose.s,.3);assert.equal(Object.keys(bad.positions).length,0);
});
test('project scoped layout persistence preserves selected employee, pan, dimensions and positions without storing records',()=>{
  const storage=memoryStorage(),other='C:/another-project';
  assert.equal(model.writeLayout(storage,ROOT,{selected:'agent:G2',height:900,pose:{x:30,y:-20,s:1.7},detail:{width:450,height:680},positions:{'agent:G2':{x:310,y:410}}}),true);
  model.writeLayout(storage,other,{selected:'agent:G3',height:700});const a=model.readLayout(storage,ROOT),b=model.readLayout(storage,other);
  assert.equal(a.selected,'agent:G2');assert.equal(a.height,900);assert.equal(a.pose.s,1.7);assert.equal(a.detail.width,450);assert.equal(a.positions['agent:G2'].y,410);assert.equal(b.selected,'agent:G3');assert.equal(b.height,700);
  assert.ok(!storage.getItem('tpl_agent_allocation').includes('资料整理'));assert.ok(!storage.getItem('tpl_agent_allocation').includes('roles'));assert.equal(model.readLayout(storage,'C:/unknown').height,640);
});
test('corrupt and blocked browser storage never prevents a view and corrupt JSON can be replaced',()=>{
  const storage=memoryStorage();storage.setItem('tpl_agent_allocation','{broken');assert.equal(model.readLayout(storage,ROOT).height,640);assert.equal(model.writeLayout(storage,ROOT,{height:800}),true);assert.equal(model.readLayout(storage,ROOT).height,800);
  const blocked={getItem(){throw new Error('Denied');},setItem(){throw new Error('Denied');}};assert.equal(model.readLayout(blocked,ROOT).height,640);assert.equal(model.writeLayout(blocked,ROOT,{height:800}),false);assert.equal(model.writeLayout(storage,'',{height:800}),false);
});
test('moving an employee changes only layout and both endpoints of real boss edges follow it',()=>{
  const c=context(),before=JSON.stringify(c),m=model.build(c),old=model.layout(m),next=model.layout(m,{'agent:G2':{x:730,y:300}}),edge=next.edges.find(e=>e.to==='agent:G2');
  assert.equal(next.nodes.find(n=>n.id==='agent:G2').x,730);assert.equal(edge.toNode.y,300);assert.equal(edge.from,'agent:G1');assert.equal(JSON.stringify(c),before);assert.equal(old.nodes.find(n=>n.id==='agent:G2').x,285);
  assert.equal(next.nodes.filter(n=>n.kind==='person').length,3);assert.deepEqual(m.ownership.map(e=>e.key),['S1-1 S2-1','S1-2 S2-1']);
});
test('drag delta respects SVG letterboxing and zoom rather than treating the node move as a camera move',()=>{
  const d=model.pointerDelta(20,20,{width:1000,height:800},{width:500,height:800},2);assert.deepEqual(d,{x:20,y:20});
  const b=model.clampNodePosition({x:-500,y:99999},{x:10,y:10,w:202,h:108},{width:990,height:1000});assert.deepEqual(b,{x:0,y:892});
});

// A small DOM contract invokes the real mount/update handlers; it has no network,
// employees, task queue, browser commands or writable project files.
const fs=require('node:fs'),vm=require('node:vm');
class Events{
  constructor(){this.listeners=new Map();}
  addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,new Set());this.listeners.get(type).add(fn);}
  removeEventListener(type,fn){this.listeners.get(type)?.delete(fn);}
  emit(type,event){for(const fn of [...(this.listeners.get(type)||[])])fn(event);}
  count(){return [...this.listeners.values()].reduce((n,s)=>n+s.size,0);}
}
class Element extends Events{
  constructor(name,parent,document){super();this.name=name;this.parentNode=parent||null;this.document=document;this.children=[];this.dataset={};this.attrs={};this.style={setProperty(k,v){this[k]=v;}};this.scrollTop=0;const classes=new Set();this.classList={toggle(k,on){if(on??!classes.has(k))classes.add(k);else classes.delete(k);},contains:k=>classes.has(k)};}
  contains(node){for(let n=node;n;n=n.parentNode)if(n===this)return true;return false;}
  appendChild(node){if(node.parentNode)node.parentNode.children=node.parentNode.children.filter(x=>x!==node);node.parentNode=this;this.children.push(node);return node;}
  insertBefore(node,next){this.appendChild(node);this.children=this.children.filter(x=>x!==node);this.children.splice(Math.max(0,this.children.indexOf(next)),0,node);}
  get isConnected(){return this.document.body.contains(this);}
  get nextSibling(){const c=this.parentNode?.children||[];return c[c.indexOf(this)+1]||null;}
  matches(sel){return sel==='[data-aag-select]'?!!this.dataset.aagSelect:sel==='[data-aag-drag]'?this.dataset.aagDrag!==undefined:sel==='[data-aag-size]'?!!this.dataset.aagSize:false;}
  closest(sel){const names=sel.split(',');for(let n=this;n;n=n.parentNode)if(names.some(x=>n.matches(x)||x==='[data-aag]'&&n.dataset.aag||x==='[data-aag-open]'&&n.dataset.aagOpen))return n;return null;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k]||null;}
  getBoundingClientRect(){return {width:this.name==='scene'?1100:990,height:this.name==='svg'?Number(this.parentNode.style.height?.replace('px',''))||640:600,left:0,top:0};}
  setPointerCapture(){}
  focus(){this.document.activeElement=this;}
  querySelectorAll(){return this.cards||[];}
  set innerHTML(html){this.html=html;if(this.name==='world'){this.cards=[];for(const m of html.matchAll(/data-aag-select="([^"]+)"/g)){const el=new Element('card',this,this.document);el.dataset.aagSelect=m[1];this.cards.push(el);}}}
  get innerHTML(){return this.html||'';}
}
function domFixture(storage=memoryStorage()){
  const window=new Events(),document=new Events();document.body=new Element('body',null,document);document.activeElement=null;document.fullscreenElement=null;
  window.innerWidth=1280;window.innerHeight=900;window.localStorage=storage;const host=document.body.appendChild(new Element('host',null,document));
  const panel=host.appendChild(new Element('panel',null,document)),scene=panel.appendChild(new Element('scene',null,document)),stage=scene.appendChild(new Element('stage',null,document)),svg=stage.appendChild(new Element('svg',null,document)),world=svg.appendChild(new Element('world',null,document)),reading=scene.appendChild(new Element('reading',null,document)),body=reading.appendChild(new Element('reading-body',null,document));
  svg.querySelectorAll=()=>world.cards||[];const nodes={'.aag-panel':panel,'.aag-scene':scene,'.aag-stage':stage,'.aag-svg':svg,'.aag-world':world,'.aag-reading':reading,'.aag-reading-body':body};
  for(const name of ['.aag-toolbar h2','.aag-meta','.aag-notice','.aag-reading-handle','.aag-legend','.aag-log summary','.aag-log-body'])nodes[name]=panel.appendChild(new Element(name,null,document));
  nodes['.aag-reading-handle'].dataset.aagDrag='';
  for(const action of ['out','in','fit','motion','notes','full','edit-flow']){const el=panel.appendChild(new Element('button',null,document));el.dataset.aag=action;nodes['[data-aag="'+action+'"]']=el;}
  for(const action of ['height','reading']){const el=(action==='height'?stage:reading).appendChild(new Element('grip',null,document));el.dataset.aagSize=action;nodes['[data-aag-size="'+action+'"]']=el;}
  host.querySelector=selector=>nodes[selector]||null;
  document.exitFullscreen=async()=>{document.fullscreenElement=null;document.emit('fullscreenchange',{});};
  let open=0,edit=0;const helpers={lang:()=> 'zh',openRecord:()=>{open++;},editFlow:()=>{edit++;}};
  vm.runInNewContext(fs.readFileSync(require.resolve('../../员工分配图.js'),'utf8'),{window,document,console,Promise,Date});
  const ctl=window.AgentAllocation.mount(host,context(),helpers);
  const event=(target,values={})=>({target,button:0,clientX:20,clientY:20,pointerId:1,preventDefault(){},stopPropagation(){},...values});
  return {window,document,host,panel,scene,stage,svg,world,reading,body,nodes,ctl,helpers,storage,event,opened:()=>open,edited:()=>edit};
}
test('real mount updates reuse host and retain selected employee, reading scroll, sizes and pan',()=>{
  const f=domFixture(),card=f.world.cards.find(n=>n.dataset.aagSelect==='agent:G2');f.host.emit('click',f.event(card));f.ctl.pose={x:30,y:50,s:1.4};f.ctl.height=850;f.ctl.detailSize={width:420,height:650};f.body.scrollTop=155;
  const ctl=f.window.AgentAllocation.update(f.host,context(),{...f.helpers,lang:()=> 'en'});assert.equal(ctl,f.ctl);assert.equal(ctl.getState().selected,'agent:G2');assert.equal(ctl.getState().pose.s,1.4);assert.equal(f.body.scrollTop,155);assert.equal(f.stage.style.height,'850px');assert.equal(f.reading.style.height,'650px');assert.equal(f.opened(),0);ctl.destroy();
});
test('actual pointer drag moves a card without changing assignment or treating its trailing click as navigation',()=>{
  const f=domFixture(),card=f.world.cards.find(n=>n.dataset.aagSelect==='agent:G2'),old=f.ctl.scene.nodes.find(n=>n.id==='agent:G2');
  f.host.emit('pointerdown',f.event(card));f.window.emit('pointermove',f.event(card,{clientX:90,clientY:60}));f.window.emit('pointerup',f.event(card));
  const next=f.ctl.scene.nodes.find(n=>n.id==='agent:G2');assert.ok(next.x>old.x);assert.equal(f.ctl.getState().selected,'agent:G2');assert.equal(f.ctl.m.tasks[0].ownerId,'agent:G2');
  const other=f.world.cards.find(n=>n.dataset.aagSelect==='agent:G3');f.host.emit('click',f.event(other));assert.equal(f.ctl.getState().selected,'agent:G2');assert.equal(f.opened(),0);assert.ok(model.readLayout(f.storage,ROOT).positions['agent:G2']);f.ctl.destroy();
});
test('actual bottom and detail resize handlers persist dimensions and keyboard alternatives work',()=>{
  const f=domFixture(),height=f.nodes['[data-aag-size="height"]'],reading=f.nodes['[data-aag-size="reading"]'];
  f.host.emit('pointerdown',f.event(height));f.window.emit('pointermove',f.event(height,{clientY:180}));f.window.emit('pointerup',f.event(height));assert.equal(f.ctl.height,800);assert.equal(f.stage.style.height,'800px');
  f.host.emit('pointerdown',f.event(reading));f.window.emit('pointermove',f.event(reading,{clientX:110,clientY:120}));f.window.emit('pointerup',f.event(reading));assert.equal(f.ctl.detailSize.width,420);assert.equal(f.ctl.detailSize.height,660);
  f.window.emit('keydown',f.event(height,{key:'ArrowDown'}));assert.equal(f.ctl.height,832);f.window.emit('keydown',f.event(reading,{key:'ArrowRight'}));assert.equal(f.ctl.detailSize.width,432);assert.equal(model.readLayout(f.storage,ROOT).height,832);f.ctl.destroy();
});
test('employee arrow keys preserve keyboard focus and save only layout coordinates',()=>{
  const f=domFixture(),card=f.world.cards.find(n=>n.dataset.aagSelect==='agent:G2');card.focus();f.window.emit('keydown',f.event(card,{key:'ArrowRight'}));
  assert.equal(f.document.activeElement.dataset.aagSelect,'agent:G2');assert.equal(f.ctl.getState().selected,'agent:G2');assert.equal(f.ctl.positions['agent:G2'].x,297);assert.equal(f.ctl.m.hierarchy.length,2);assert.equal(f.opened(),0);f.ctl.destroy();
});
test('editing callback changes mode only when the explicit button is clicked',()=>{
  const f=domFixture();assert.equal(f.edited(),0);f.ctl.update(context());assert.equal(f.edited(),0);f.host.emit('click',f.event(f.nodes['[data-aag="edit-flow"]']));assert.equal(f.edited(),1);assert.equal(f.opened(),0);f.ctl.destroy();
});
test('project switches destroy old listeners and cannot inherit another project layout',()=>{
  const f=domFixture();f.ctl.height=900;f.ctl.selected='agent:G2';f.ctl.persist();const old=f.ctl,c=context();c.state.project.root='C:/different-project';const next=f.window.AgentAllocation.update(f.host,c,f.helpers);
  assert.notEqual(next,old);assert.equal(old.destroyed,true);assert.equal(next.height,640);assert.equal(next.selected,'stage:dispatch');assert.equal(f.window.count(),5);assert.equal(f.document.count(),1);
  next.destroy();assert.equal(f.window.count(),0);assert.equal(f.document.count(),0);assert.equal(f.host.count(),0);assert.equal(f.svg.count(),0);
});
test('dispose and remount restore saved selection and view without leaked pointer handlers',()=>{
  const f=domFixture();f.ctl.selected='agent:G3';f.ctl.pose={x:12,y:30,s:1.6};f.ctl.height=940;f.ctl.positions['agent:G3']={x:660,y:490};f.window.AgentAllocation.dispose(f.host);
  assert.equal(f.window.count(),0);const next=f.window.AgentAllocation.mount(f.host,context(),f.helpers);assert.equal(next.selected,'agent:G3');assert.equal(next.pose.s,1.6);assert.equal(next.height,940);assert.equal(next.positions['agent:G3'].x,660);assert.equal(f.window.count(),5);next.destroy();assert.equal(f.window.count(),0);
});
test('fullscreen detail resizing and note lifecycle retain original note element',async()=>{
  const f=domFixture(),note=f.document.body.appendChild(new Element('note',null,f.document));note.innerHTML='UNSAVED HUMAN TEXT';f.ctl.h.notes=()=>note;
  await f.ctl.enterFullscreen();assert.equal(f.ctl.fs,true);f.ctl.action('notes');assert.equal(note.parentNode,f.panel);
  const grip=f.nodes['[data-aag-size="reading"]'];f.host.emit('pointerdown',f.event(grip));f.window.emit('pointermove',f.event(grip,{clientX:180,clientY:190}));f.window.emit('pointerup',f.event(grip));assert.equal(f.ctl.pane.width,490);assert.equal(f.ctl.pane.height,730);
  f.ctl.exitFullscreen();assert.equal(note.parentNode,f.document.body);assert.equal(note.innerHTML,'UNSAVED HUMAN TEXT');assert.equal(f.ctl.detailSize.width,490);assert.equal(f.reading.style.height,'730px');f.ctl.destroy();
});
