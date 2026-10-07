/* 员工分配图只展示现有档案、领活和运行记录，不派活、不启动员工。 */
(function (global) {
  'use strict';
  const arr = x => Array.isArray(x) ? x : [];
  const str = x => x == null ? '' : String(x);
  const esc = x => str(x).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const actor = x => str(x).replace(/^agent:/, '').trim();
  function taskKey(x) {
    if (!x || typeof x !== 'object') return '';
    const sub = x.sub || x.code;
    if (x.goal && /^S2-\d+$/.test(str(sub))) return str(x.goal) + ' ' + sub;
    return /\S+ S2-\d+$/.test(str(x.key)) ? str(x.key) : '';
  }
  function resolveAgent(value, people) {
    const a = actor(value); if (!a) return null;
    let rows = people.filter(p => p.code && p.code === a);
    if (rows.length) return rows.length === 1 ? rows[0] : null;
    rows = people.filter(p => p.name === a);
    return rows.length === 1 ? rows[0] : null;
  }
  function currentTaskKey(run, ctx) {
    const c = run && run.current, board = arr((ctx.board || {}).items);
    if (typeof c === 'string') return board.filter(t => taskKey(t) === c).length === 1 ? c : '';
    if (!c || typeof c !== 'object') return '';
    const ref = c.task || c.construction_plan || c.review || c.draft;
    const direct = taskKey(ref); if (direct) return direct;
    const code = typeof ref === 'string' ? ref : ref && ref.code;
    if (!code) return '';
    const records = c.review ? arr(ctx.deliveries) : arr((ctx.launch || {}).plans);
    const matches = records.filter(r => r.code === code);
    return matches.length === 1 ? taskKey(matches[0]) : '';
  }
  function confirmedActivity(ctx, person, tasks) {
    const L = ctx.launch || {}, root = ctx.state && ctx.state.project && ctx.state.project.root;
    if (!root || ctx.online !== true || arr(ctx.errors).length || L.on !== true || L.pause || person.raw.paused === true || !person.code) return null;
    const runs = arr(L.status).filter(r => r.code === person.code);
    if (runs.length !== 1 || runs[0].status !== 'running') return null;
    const r = runs[0], key = currentTaskKey(r, ctx), matches = tasks.filter(t => t.key === key);
    const windows = arr(L.windows).filter(w => w.alive === true && w.agent_code === person.code && w.project_root === root && w.task_key === key);
    if (!key || matches.length !== 1 || !windows.length) return null;
    const c = r.current, action = r.action || c && c.action || '';
    if (action === 'review_plan' || action === 'review_delivery') {
      const ref = c && typeof c === 'object' && (action === 'review_plan' ? c.construction_plan : c.review);
      const records = action === 'review_plan' ? arr(L.plans) : arr(ctx.deliveries);
      const code = typeof ref === 'object' ? ref && ref.code : ref;
      const found = records.filter(x => code && x.code === code);
      const record = found.length === 1 ? found[0] : null;
      const author = record && resolveAgent(record.by || record.agent, ctx.roster || []);
      if (!record || taskKey(record) !== key || !author || author.code === person.code || !person.roles.includes(action === 'review_plan' ? '审核' : '验收')) return null;
      if (typeof ref === 'object' && actor(ref.by || ref.agent) && actor(ref.by || ref.agent) !== actor(record.by || record.agent)) return null;
      if (action === 'review_plan' ? (record.display_state || record.state) !== '待审' : !['等验收','待你验收'].includes(record.state)) return null;
    } else if (matches[0].ownerId !== person.id || matches[0].raw.col !== '在做') return null;
    return {key, action, run:r, windows};
  }
  function build(ctx) {
    ctx = ctx || {}; const L = ctx.launch || {}, issues = [];
    const people = arr(ctx.roster).map((r, i) => ({id:r.code ? 'agent:' + r.code : 'history:' + (r.file || r.name || i), code:str(r.code), name:str(r.name), raw:r,
      roles:arr(r.roles).map(str), boss:str(r.boss), group:arr(r.roles).includes('带队') ? 'lead' : arr(r.roles).includes('干活') ? 'work' : arr(r.roles).some(x => ['规划','审核','验收'].includes(x)) ? 'advisor' : 'other', tasks:[], missing:[], deliveries:[]}));
    const tasks = arr((ctx.board || {}).items).map((t, i) => ({key:taskKey(t), id:'task:' + (taskKey(t) || i), raw:t, ownerId:'', assignment:'unassigned'}));
    const keyCounts = new Map(); tasks.forEach(t => { if(t.key)keyCounts.set(t.key,(keyCounts.get(t.key)||0)+1); });
    people.forEach(p => arr(p.raw.holding).forEach(h => { const key=taskKey(h); if(key && !tasks.some(t=>t.key===key))p.missing.push(key); }));
    tasks.forEach(t => {
      if (!t.key || keyCounts.get(t.key) !== 1) {t.assignment='unresolved';issues.push({kind:'task',key:t.key,text:'任务编号缺失或重复'});return;}
      const who = actor(t.raw.who || t.raw.owner), owner = resolveAgent(who, people), holders = people.filter(p => arr(p.raw.holding).some(h => taskKey(h) === t.key));
      if ((who && !owner) || holders.length > 1 || owner && holders.some(p => p.id !== owner.id)) {
        t.assignment='unresolved';issues.push({kind:'owner',key:t.key,text:'负责人记录未明确对应档案'});return;
      }
      const p = owner || holders[0]; if(p){t.ownerId=p.id;t.assignment='assigned';p.tasks.push(t);}
    });
    const hierarchy = [];
    people.forEach(p => {
      if (p.boss && p.boss !== '人') { const boss=resolveAgent(p.boss,people);
        if(boss && boss.id!==p.id && boss.code === p.boss)hierarchy.push({from:boss.id,to:p.id,kind:'boss'});
        else issues.push({kind:'boss',agentId:p.id,text:'上级档案未明确对应：'+p.boss});
      }
      const runs = arr(L.status).filter(r => r.code && r.code === p.code);p.run = runs.length===1 ? runs[0] : null;
      p.windows = arr(L.windows).filter(w=>p.code && w.agent_code===p.code && w.project_root===(ctx.state && ctx.state.project && ctx.state.project.root));
      p.active = confirmedActivity(ctx,p,tasks);
      p.status = p.raw.paused || L.pause ? '暂停' : p.active ? '已确认运行' : p.run && p.run.status==='running' ? '运行未确认' : p.run && ['failed','stopped','waiting'].includes(p.run.status) ? ({failed:'失败',stopped:'停止',waiting:'等待'})[p.run.status] : p.tasks.length ? '已领活' : '空着';
      p.deliveries = arr(ctx.deliveries).filter(d=>resolveAgent(d.by,people)===p);
    });
    // A cycle is still a recorded conflict, never silently rendered as a valid hierarchy.
    const reaches=(from,to,seen)=>{if(from===to)return true;if(seen.has(from))return false;seen.add(from);return hierarchy.filter(e=>e.from===from).some(e=>reaches(e.to,to,seen));};
    hierarchy.forEach(e=>{if(reaches(e.to,e.from,new Set())){e.conflict=true;issues.push({kind:'boss-cycle',agentId:e.to,text:'上级记录成环：'+e.from+' → '+e.to});}});
    const ownership=tasks.filter(t=>t.ownerId).map(t=>({from:t.ownerId,to:t.id,key:t.key,kind:'claim'}));
    const pendingPlans=arr(L.plans).filter(p=>(p.display_state||p.state)==='待审');
    const pendingDeliveries=arr(ctx.deliveries).filter(d=>['等验收','待你验收'].includes(d.state));
    const stages=[{id:'plan',zh:'统筹与规划',en:'Coordination',people:people.filter(p=>p.roles.some(r=>['带队','规划'].includes(r))),value:people.filter(p=>p.roles.some(r=>['带队','规划'].includes(r))).length,unit:'份岗位档案'},
      {id:'dispatch',zh:'计划审核与分配',en:'Review & allocation',people:people.filter(p=>p.roles.includes('审核')),value:pendingPlans.length,unit:'份计划待审'},
      {id:'work',zh:'并行施工',en:'Parallel work',people:people.filter(p=>p.roles.includes('干活')),value:tasks.filter(t=>t.raw.col==='在做').length,unit:'件在做'},
      {id:'accept',zh:'交付验收',en:'Acceptance',people:people.filter(p=>p.roles.includes('验收')),value:pendingDeliveries.length,unit:'份交付待验收'}];
    return {root:ctx.state && ctx.state.project && ctx.state.project.root || '',people,tasks,hierarchy,ownership,issues,stages,pendingPlans,pendingDeliveries,
      counts:{people:people.length,registered:people.filter(p=>p.raw.registered===true).length,active:people.filter(p=>p.active).length,assigned:tasks.filter(t=>t.ownerId).length,unassigned:tasks.filter(t=>t.assignment==='unassigned').length,unresolved:tasks.filter(t=>t.assignment==='unresolved').length},ctx};
  }
  function layout(m, positions) {
    const nodes=[], groups={lead:[],work:[],advisor:[],other:[]};m.people.forEach(p=>groups[p.group].push(p));
    const card=(p,x,y)=>nodes.push({id:p.id,kind:'person',person:p,x,y,w:202,h:108});
    groups.lead.forEach((p,i)=>card(p,285+i%3*218,120+Math.floor(i/3)*125));
    const dispatchY=150+Math.max(1,Math.ceil(groups.lead.length/3))*125;
    const workY=dispatchY+150;groups.work.forEach((p,i)=>card(p,285+i%3*218,workY+70+Math.floor(i/3)*125));
    const acceptY=workY+100+Math.max(1,Math.ceil(groups.work.length/3))*125;
    groups.advisor.forEach((p,i)=>card(p,20,120+i*125));
    const otherY=Math.max(acceptY+130,140+groups.advisor.length*125);groups.other.forEach((p,i)=>card(p,285+i%3*218,otherY+Math.floor(i/3)*125));
    const phases=[{id:'stage:plan',stage:m.stages[0],x:390,y:20,w:300,h:78},{id:'stage:dispatch',stage:m.stages[1],x:370,y:dispatchY,w:340,h:90},
      {id:'stage:work',stage:m.stages[2],x:370,y:workY,w:340,h:54},{id:'stage:accept',stage:m.stages[3],x:370,y:acceptY,w:340,h:90}];
    const width=990,height=Math.max(acceptY+140,otherY+Math.ceil(groups.other.length/3)*125+25);
    nodes.push(...phases);nodes.forEach(n=>{if(n.kind==='person'&&positions&&Object.hasOwn(positions,n.id)){const p=clampNodePosition(positions[n.id],n,{width,height});n.x=p.x;n.y=p.y;}});
    const byId=new Map(nodes.map(n=>[n.id,n]));
    const edges=m.hierarchy.filter(e=>!e.conflict&&byId.has(e.from)&&byId.has(e.to)).map(e=>({...e,fromNode:byId.get(e.from),toNode:byId.get(e.to)}));
    return {nodes,phases,edges,width,height,groups};
  }
  function clampPane(box, viewport) {
    const n=(v,f)=>Number.isFinite(v)?v:f,W=Math.max(1,n(viewport.width,1024)),H=Math.max(1,n(viewport.height,768)),gap=Math.min(8,W/4,H/4);
    const width=Math.min(W-gap*2,Math.max(1,n(box.width,330))),height=Math.min(H-gap*2,Math.max(1,n(box.height,470)));
    return {x:Math.max(gap,Math.min(n(box.x,gap),W-gap-width)),y:Math.max(gap,Math.min(n(box.y,gap),H-gap-height)),width,height};
  }
  const STORAGE_KEY='tpl_agent_allocation';
  const finite=(x,f)=>typeof x==='number'&&Number.isFinite(x)?x:f;
  function clampNodePosition(point,node,scene){return {x:Math.max(0,Math.min(finite(point&&point.x,node.x),scene.width-node.w)),y:Math.max(0,Math.min(finite(point&&point.y,node.y),scene.height-node.h))};}
  function pointerDelta(dx,dy,scene,viewport,zoom){const scale=Math.max(.001,Math.min(Math.max(1,viewport.width)/scene.width,Math.max(1,viewport.height)/scene.height));const z=Math.max(.3,finite(zoom,1));return {x:finite(dx,0)/scale/z,y:finite(dy,0)/scale/z};}
  function normalizeLayout(raw){
    const r=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{},pose=r.pose&&typeof r.pose==='object'?r.pose:{},detail=r.detail&&typeof r.detail==='object'?r.detail:{};
    const positions=Object.create(null);if(r.positions&&typeof r.positions==='object'&&!Array.isArray(r.positions))Object.keys(r.positions).slice(0,200).forEach(id=>{const p=r.positions[id];if((id.startsWith('agent:')||id.startsWith('history:'))&&p&&Number.isFinite(p.x)&&Number.isFinite(p.y))positions[id]={x:Math.max(0,Math.min(5000,p.x)),y:Math.max(0,Math.min(5000,p.y))};});
    return {selected:typeof r.selected==='string'&&r.selected.length<400?r.selected:'stage:dispatch',pose:{x:Math.max(-10000,Math.min(10000,finite(pose.x,0))),y:Math.max(-10000,Math.min(10000,finite(pose.y,0))),s:Math.max(.3,Math.min(3.6,finite(pose.s,1)))},height:Math.max(480,Math.min(1800,finite(r.height,640))),detail:{width:Math.max(260,Math.min(720,finite(detail.width,330))),height:Math.max(260,Math.min(1200,finite(detail.height,560)))},positions,motion:r.motion!==false};
  }
  function readLayout(storage,root){if(!root||!storage)return normalizeLayout();try{const data=JSON.parse(storage.getItem(STORAGE_KEY)||'{}');return normalizeLayout(data&&typeof data==='object'&&Object.hasOwn(data,root)?data[root]:null);}catch(e){return normalizeLayout();}}
  function writeLayout(storage,root,value){if(!root||!storage)return false;try{let data;const text=storage.getItem(STORAGE_KEY);try{data=JSON.parse(text||'{}');}catch(e){data={};}const out=Object.create(null);if(data&&typeof data==='object'&&!Array.isArray(data))Object.keys(data).slice(0,100).forEach(key=>{if(key!==root)out[key]=normalizeLayout(data[key]);});out[root]=normalizeLayout(value);storage.setItem(STORAGE_KEY,JSON.stringify(out));return true;}catch(e){return false;}}
  const model={taskKey,resolveAgent,currentTaskKey,confirmedActivity,build,layout,clampPane,clampNodePosition,pointerDelta,normalizeLayout,readLayout,writeLayout};
  const controllers=new Map();let serial=0;
  const css=`
  .aag-panel{position:relative;margin-top:1.5rem;border-top:1px solid var(--line);padding-top:1rem;color:var(--fg);font-family:var(--font)}
  .aag-toolbar{display:flex;align-items:center;gap:.45rem;flex-wrap:nowrap;white-space:nowrap;overflow-x:auto;margin-bottom:.4rem}.aag-toolbar h2{font-size:1.125rem;font-weight:650;margin:0}.aag-spacer{flex:1}.aag-meta,.aag-notice{font-size:.8125rem;color:var(--muted);margin:.35rem 0}.aag-notice:empty{display:none}
  .aag-scene{display:grid;grid-template-columns:minmax(0,1fr) var(--aag-reading-width,22rem);gap:1rem;align-items:start}.aag-stage{min-width:0;overflow:hidden;border:1px solid var(--line);border-radius:.65rem;background:var(--plane);height:640px;display:flex;flex-direction:column}.aag-svg{display:block;width:100%;height:calc(100% - 2.8rem);min-height:0;flex:1;touch-action:none;user-select:none}.aag-svg text{font-family:var(--font);fill:var(--fg);font-size:.875rem}.aag-svg .aag-small{font-size:.75rem;fill:var(--muted)}.aag-svg .aag-name{font-weight:600}.aag-svg .aag-role{font-size:.75rem;fill:var(--accent)}.aag-card rect{fill:var(--card);stroke:var(--line);stroke-width:1}.aag-card:hover rect,.aag-card:focus rect{stroke:var(--hover-gold);stroke-width:1.4}.aag-card{cursor:pointer;outline:none}.aag-card.aag-selected rect{stroke:var(--accent);stroke-width:1.5}.aag-phase rect{fill:var(--card);stroke:var(--accent);stroke-width:.8}.aag-protocol{fill:none;stroke:var(--muted);stroke-width:1;stroke-dasharray:4 7;opacity:.65}.aag-boss{fill:none;stroke:var(--hover-gold);stroke-width:1.3}.aag-dot{fill:var(--muted)}.aag-confirmed .aag-dot{fill:var(--good)}.aag-motion .aag-confirmed .aag-dot{animation:aag-breathe 2.8s ease-in-out infinite}.aag-legend{display:flex;gap:1rem;align-items:center;font-size:.75rem;color:var(--muted);padding:.4rem .75rem;border-top:1px solid var(--line)}.aag-line-sample{display:inline-block;width:1.8rem;border-top:1px solid var(--hover-gold);vertical-align:middle;margin-right:.3rem}.aag-line-sample.protocol{border-top-style:dashed;border-color:var(--muted)}
  .aag-reading{background:var(--card);border:1px solid var(--line);border-radius:.65rem;overflow:hidden;min-width:0;display:flex;flex-direction:column;height:560px;box-sizing:border-box}.aag-reading-handle{padding:.5rem .7rem;border-bottom:1px solid var(--line);font-size:.8125rem;color:var(--muted)}.aag-reading-body{padding:.75rem;overflow:auto;min-height:0;flex:1;font-size:.875rem}.aag-reading-body h3{font-size:1rem;margin:.2rem 0 .65rem}.aag-reading-body h4{font-size:.875rem;margin:.9rem 0 .4rem}.aag-reading-body p{margin:.45rem 0}.aag-fields{display:grid;grid-template-columns:6rem minmax(0,1fr);gap:.3rem .6rem;margin:.6rem 0}.aag-fields dt{color:var(--muted)}.aag-fields dd{margin:0;overflow-wrap:anywhere}.aag-record{padding:.55rem 0;border-bottom:1px solid var(--line)}.aag-record:last-child{border-bottom:0}.aag-record .sbtn{margin-top:.35rem}.aag-reading-body .acts{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.6rem}.aag-body-text{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8125rem}.aag-log{margin-top:.8rem;font-size:.8125rem}.aag-log table{width:100%;border-collapse:collapse}.aag-log td{padding:.35rem .5rem;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}.aag-log td:first-child{color:var(--muted);white-space:nowrap}
  .aag-fs{position:fixed!important;inset:0!important;z-index:10000;background:var(--plane);margin:0;padding:.7rem;overflow:hidden;display:flex;flex-direction:column;box-sizing:border-box}.aag-fs .aag-scene{display:block;flex:1;min-height:0;position:relative}.aag-fs .aag-stage{height:100%}.aag-fs .aag-svg{height:calc(100% - 2rem);min-height:0;aspect-ratio:auto!important}.aag-fs .aag-reading{position:fixed;z-index:2;box-shadow:0 .4rem 1.6rem var(--ring);max-height:none}.aag-fs .aag-reading-handle{cursor:grab;touch-action:none}.aag-fs .aag-reading-body{min-height:0;box-sizing:border-box}.aag-fs [data-aag-size="height"]{display:none}.aag-fs .aag-log{display:none}.aag-fs #note{z-index:10001!important}
  .aag-size-grip{flex:0 0 .85rem;min-height:.85rem;cursor:ns-resize;touch-action:none;border-top:1px solid var(--line);background:var(--card);position:relative}.aag-size-grip:after{content:"";display:block;width:2.4rem;border-top:2px solid var(--muted);margin:.3rem auto}.aag-size-grip:hover,.aag-size-grip:focus{outline:1px solid var(--hover-gold)}.aag-reading-size{align-self:flex-end;width:1.2rem;min-height:1.2rem;cursor:nwse-resize;touch-action:none;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);margin:.2rem .35rem .35rem 0;box-sizing:border-box}.aag-reading-size:hover,.aag-reading-size:focus{outline:1px solid var(--hover-gold)}.aag-svg [data-aag-select^="agent:"],.aag-svg [data-aag-select^="history:"]{cursor:grab}
  @keyframes aag-breathe{0%,100%{opacity:1}50%{opacity:.35}}@media(prefers-reduced-motion:reduce){.aag-panel *{animation:none!important;transition:none!important}}
  `;
  function Panel(host,ctx,helpers){
    this.host=host;this.h=helpers||{};this.root=ctx.state&&ctx.state.project&&ctx.state.project.root||'';this.uid='aag-'+(++serial);try{this.storage=global.localStorage;}catch(e){this.storage=null;}const saved=readLayout(this.storage,this.root);this.selected=saved.selected;this.pose=saved.pose;this.motion=saved.motion;this.positions=saved.positions;this.height=saved.height;this.detailSize=saved.detail;this.destroyed=false;this.fs=false;this.fsMode='';this.fsSerial=0;
    this.host.innerHTML='<style>'+css+'</style><section class="aag-panel"><div class="aag-toolbar"><h2></h2><span class="aag-spacer"></span><button class="sbtn" data-aag="edit-flow"></button><button class="sbtn" data-aag="out">−</button><button class="sbtn" data-aag="in">+</button><button class="sbtn" data-aag="fit"></button><button class="sbtn" data-aag="motion"></button><button class="sbtn sticky-shortcut" data-aag="notes" aria-label="便签 Sticky note" title="便签 Sticky note"></button><button class="sbtn" data-aag="full"></button></div><div class="aag-meta"></div><div class="aag-notice" role="status"></div><div class="aag-scene"><div class="aag-stage"><svg class="aag-svg" role="group" aria-label="员工分配图 Agent allocation"><defs><marker id="'+this.uid+'-boss" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="var(--hover-gold)"/></marker></defs><g class="aag-world"></g></svg><div class="aag-legend"></div><div class="aag-size-grip" data-aag-size="height" tabindex="0" role="separator" aria-orientation="horizontal"></div></div><aside class="aag-reading"><div class="aag-reading-handle" data-aag-drag tabindex="0" role="button"></div><div class="aag-reading-body"></div><div class="aag-reading-size" data-aag-size="reading" tabindex="0" role="button"></div></aside></div><details class="aag-log"><summary></summary><div class="aag-log-body"></div></details></section>';
    this.panel=host.querySelector('.aag-panel');this.svg=host.querySelector('.aag-svg');this.world=host.querySelector('.aag-world');this.reading=host.querySelector('.aag-reading');this.body=host.querySelector('.aag-reading-body');this.stage=host.querySelector('.aag-stage');this.sceneEl=host.querySelector('.aag-scene');
    this.click=e=>{const b=e.target.closest('[data-aag],[data-aag-select],[data-aag-open]');if(!b||!host.contains(b))return;if(this.suppressUntil&&Date.now()<this.suppressUntil&&this.svg.contains(e.target)){e.preventDefault();e.stopPropagation();return;}e.stopPropagation();if(b.dataset.aagSelect){this.selected=b.dataset.aagSelect;this.draw();this.detail();this.persist();return;}if(b.dataset.aagOpen){const record=this.links&&this.links.get(b.dataset.aagOpen);if(record&&typeof this.h.openRecord==='function')this.h.openRecord(record);return;}this.action(b.dataset.aag);};
    this.key=e=>{
      if(e.key==='Escape'&&this.fs){this.exitFullscreen();return;}
      if(!host.contains(e.target)||!e.target.matches)return;
      const arrows=['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'],step=e.shiftKey?32:12;
      if(e.target.matches('[data-aag-size]')&&arrows.includes(e.key)){
        e.preventDefault();if(e.target.dataset.aagSize==='height')this.height=normalizeLayout({height:this.height+(e.key==='ArrowDown'?32:e.key==='ArrowUp'?-32:0)}).height;
        else {this.detailSize=normalizeLayout({detail:{width:this.detailSize.width+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),height:this.detailSize.height+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)}}).detail;if(this.fs){this.pane.width=this.detailSize.width;this.pane.height=this.detailSize.height;}}
        this.applySize();this.persist();return;
      }
      if(e.target.matches('[data-aag-select]')){
        const id=e.target.dataset.aagSelect,n=this.scene.nodes.find(x=>x.id===id);
        if(arrows.includes(e.key)&&n&&n.kind==='person'){e.preventDefault();this.selected=id;this.movePerson(id,{x:n.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),y:n.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)});this.detail();this.persist();this.focusNode(id);return;}
        if(['Enter',' '].includes(e.key)){e.preventDefault();this.selected=id;this.draw();this.detail();this.persist();this.focusNode(id);return;}
      }
      if(this.fs&&e.target.matches('[data-aag-drag]')&&arrows.includes(e.key)){e.preventDefault();this.pane.x+=(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0);this.pane.y+=(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0);this.placePane();}
    };
    this.down=e=>{
      if(e.button!==0)return;const size=e.target.closest('[data-aag-size]');
      if(size){e.preventDefault();e.stopPropagation();this.sizeDrag={kind:size.dataset.aagSize,x:e.clientX,y:e.clientY,height:this.height,detail:{...(this.fs?this.pane:this.detailSize)}};if(size.setPointerCapture)size.setPointerCapture(e.pointerId);return;}
      const h=e.target.closest('[data-aag-drag]');if(h&&this.fs){e.preventDefault();this.dragPane={x:e.clientX,y:e.clientY,px:this.pane.x,py:this.pane.y};if(h.setPointerCapture)h.setPointerCapture(e.pointerId);return;}
      if(!this.svg.contains(e.target))return;const card=e.target.closest('[data-aag-select]'),node=card&&this.scene.nodes.find(n=>n.id===card.dataset.aagSelect);
      if(node){if(node.kind!=='person')return;e.preventDefault();this.selected=node.id;this.dragNode={id:node.id,x:e.clientX,y:e.clientY,px:node.x,py:node.y,moved:false};if(this.svg.setPointerCapture)this.svg.setPointerCapture(e.pointerId);this.draw();this.detail();return;}
      this.drag={x:e.clientX,y:e.clientY,px:this.pose.x,py:this.pose.y};if(this.svg.setPointerCapture)this.svg.setPointerCapture(e.pointerId);
    };
    this.move=e=>{
      if(this.sizeDrag){const d=this.sizeDrag;if(d.kind==='height')this.height=normalizeLayout({height:d.height+e.clientY-d.y}).height;else{this.detailSize=normalizeLayout({detail:{width:d.detail.width+e.clientX-d.x,height:d.detail.height+e.clientY-d.y}}).detail;if(this.fs){this.pane.width=this.detailSize.width;this.pane.height=this.detailSize.height;}}this.applySize();return;}
      if(this.dragPane){this.pane.x=this.dragPane.px+e.clientX-this.dragPane.x;this.pane.y=this.dragPane.py+e.clientY-this.dragPane.y;this.placePane();return;}
      if(this.dragNode){const d=this.dragNode,dx=e.clientX-d.x,dy=e.clientY-d.y;if(!d.moved&&Math.max(Math.abs(dx),Math.abs(dy))<4)return;d.moved=true;const r=this.svg.getBoundingClientRect(),delta=pointerDelta(dx,dy,this.scene,r,this.pose.s);this.movePerson(d.id,{x:d.px+delta.x,y:d.py+delta.y});return;}
      if(this.drag){const r=this.svg.getBoundingClientRect(),delta=pointerDelta(e.clientX-this.drag.x,e.clientY-this.drag.y,this.scene,r,1);this.pose.x=this.drag.px+delta.x;this.pose.y=this.drag.py+delta.y;this.transform();}
    };
    this.up=()=>{if(this.dragNode&&this.dragNode.moved)this.suppressUntil=Date.now()+350;if(this.dragNode||this.drag||this.sizeDrag)this.persist();this.drag=null;this.dragPane=null;this.dragNode=null;this.sizeDrag=null;};
    this.wheel=e=>{e.preventDefault();this.zoom(e.deltaY<0?1.12:1/1.12);};this.resize=()=>this.applySize();this.dbl=e=>{if(this.fs&&e.target.closest('[data-aag-drag]')){this.defaultPane();this.placePane();}};
    this.fsChange=()=>{if(document.fullscreenElement===this.panel){this.fs=true;this.fsMode='native';this.syncFullscreen();}else if(this.fsMode==='native'){this.fs=false;this.fsMode='';this.syncFullscreen();}};
    host.addEventListener('click',this.click);host.addEventListener('pointerdown',this.down);host.addEventListener('dblclick',this.dbl);this.svg.addEventListener('wheel',this.wheel,{passive:false});global.addEventListener('pointermove',this.move);global.addEventListener('pointerup',this.up);global.addEventListener('pointercancel',this.up);global.addEventListener('keydown',this.key);global.addEventListener('resize',this.resize);document.addEventListener('fullscreenchange',this.fsChange);this.update(ctx);
  }
  Panel.prototype.label=function(zh,en){return typeof this.h.lang==='function'&&this.h.lang()==='en'?esc(en):esc(zh)+' <span class="en">'+esc(en)+'</span>';};
  Panel.prototype.text=function(zh,en){return typeof this.h.lang==='function'&&this.h.lang()==='en'?en:zh;};
  Panel.prototype.update=function(ctx,helpers){
    if(this.destroyed)return;if(helpers)this.h=helpers;this.ctx=ctx;this.m=build(ctx);this.scene=layout(this.m,this.positions);
    if(!this.scene.nodes.some(n=>n.id===this.selected))this.selected='stage:dispatch';
    this.host.querySelector('.aag-toolbar h2').innerHTML=this.label('员工分配图','Agent allocation');
    const labels={'edit-flow':['编辑流程','Edit flow'],fit:['适配','Fit'],motion:this.motion?['暂停动画','Pause animation']:['播放动画','Play animation'],notes:['便签','Sticky note'],full:this.fs?['退出全屏','Exit fullscreen']:['全屏','Fullscreen']};Object.keys(labels).forEach(k=>this.host.querySelector('[data-aag="'+k+'"]').innerHTML=(k==='notes'&&this.h.notesIcon?this.h.notesIcon():'')+this.label(...labels[k]));
    this.host.querySelector('[data-aag="out"]').setAttribute('aria-label',this.text('缩小','Zoom out'));this.host.querySelector('[data-aag="in"]').setAttribute('aria-label',this.text('放大','Zoom in'));
    this.host.querySelector('.aag-meta').textContent=this.text('档案','Profiles')+' '+this.m.counts.people+' · '+this.text('已领任务','Assigned tasks')+' '+this.m.counts.assigned+' · '+this.text('未分配','Unassigned')+' '+this.m.counts.unassigned+' · '+this.text('已确认运行','Verified running')+' '+this.m.counts.active;
    this.host.querySelector('.aag-notice').textContent=arr(ctx.errors).length?arr(ctx.errors).join(' · ')+' · '+this.text('保留最后成功数据','Last successful data retained'):(ctx.launch||{}).pause?str(ctx.launch.pause):arr((ctx.launch||{}).missing_roles).join(' · ');
    this.host.querySelector('.aag-reading-handle').innerHTML=this.label('详情与记录','Details & records');this.host.querySelector('.aag-reading-handle').setAttribute('aria-label',this.text('全屏时拖动详情窗','Drag details in fullscreen'));
    this.host.querySelector('.aag-legend').innerHTML='<span><i class="aag-line-sample protocol"></i>'+this.label('流程阶段','Protocol stages')+'</span><span><i class="aag-line-sample"></i>'+this.label('档案上级','Recorded supervisor')+'</span>';
    this.panel.classList.toggle('aag-motion',this.motion);this.applySize();this.draw();this.detail();this.log();if(this.fs)this.placePane();
  };
  Panel.prototype.draw=function(){
    const focused=document.activeElement&&this.svg.contains(document.activeElement)?document.activeElement.dataset.aagSelect:'',s=this.scene,trim=(x,n)=>Array.from(str(x)).slice(0,n).join('')+(Array.from(str(x)).length>n?'…':'');
    const line=(a,b,kind)=>kind==='protocol'?'<path class="aag-protocol" d="M'+(a.x+a.w/2)+' '+(a.y+a.h)+' C'+(a.x+a.w/2)+' '+(a.y+a.h+25)+' '+(b.x+b.w/2)+' '+(b.y-25)+' '+(b.x+b.w/2)+' '+b.y+'"/>':'';
    let html=line(s.phases[0],s.phases[1],'protocol')+line(s.phases[1],s.phases[2],'protocol');
    const work=s.phases[2],accept=s.phases[3];html+='<path class="aag-protocol" d="M'+(work.x+work.w)+' '+(work.y+work.h/2)+' H955 V'+(accept.y+accept.h/2)+' H'+(accept.x+accept.w)+'"/>';
    html+='<text class="aag-small" x="20" y="102">'+esc(this.text('规划与审核 / 验收','Planning & review / acceptance'))+'</text>';
    if(!s.groups.advisor.length)html+='<text class="aag-small" x="20" y="145">'+esc(this.text('未配置专职参谋','No dedicated advisor'))+'</text>';
    if(!s.groups.lead.length)html+='<text class="aag-small" x="415" y="155">'+esc(this.text('未配置带队员工','No lead configured'))+'</text>';
    if(!s.groups.work.length)html+='<text class="aag-small" x="415" y="'+(work.y+95)+'">'+esc(this.text('未配置施工员工','No worker configured'))+'</text>';
    s.edges.forEach(e=>{const a=e.fromNode,b=e.toNode,ax=a.x+a.w/2,ay=a.y+a.h,bx=b.x+b.w/2,by=b.y;html+='<path class="aag-boss" data-aag-boss="'+esc(e.from+'>'+e.to)+'" marker-end="url(#'+this.uid+'-boss)" d="M'+ax+' '+ay+' C'+ax+' '+(ay+35)+' '+bx+' '+(by-35)+' '+bx+' '+by+'"/>';});
    s.nodes.forEach(n=>{
      const selected=n.id===this.selected?' aag-selected':'';
      if(n.kind==='person'){const p=n.person,title=[p.code,p.name].filter(Boolean).join(' '),task=p.tasks[0];html+='<g class="aag-card'+selected+(p.active?' aag-confirmed':'')+'" data-aag-select="'+esc(n.id)+'" role="button" tabindex="0" aria-label="'+esc(title+' · '+p.roles.join('、')+' · '+p.status)+'"><title>'+esc(title+'\n'+p.roles.join('、')+'\n'+p.tasks.map(t=>t.key).join('、'))+'</title><rect x="'+n.x+'" y="'+n.y+'" width="'+n.w+'" height="'+n.h+'" rx="8"/><text class="aag-name" x="'+(n.x+12)+'" y="'+(n.y+23)+'">'+esc(trim(title,23))+'</text><text class="aag-role" x="'+(n.x+12)+'" y="'+(n.y+44)+'">'+esc(trim(p.roles.join(' · ')||this.text('岗位未记录','Role not recorded'),28))+'</text><text class="aag-small" x="'+(n.x+12)+'" y="'+(n.y+65)+'">'+esc(task?task.key+(p.tasks.length>1?' +'+(p.tasks.length-1):''):this.text('未领取任务','No assigned task'))+'</text><circle class="aag-dot" cx="'+(n.x+16)+'" cy="'+(n.y+89)+'" r="3"/><text class="aag-small" x="'+(n.x+27)+'" y="'+(n.y+94)+'">'+esc(this.statusText(p.status))+'</text></g>';
      }else{const st=n.stage;html+='<g class="aag-card aag-phase'+selected+'" data-aag-select="'+esc(n.id)+'" role="button" tabindex="0" aria-label="'+esc(this.text(st.zh,st.en))+'"><rect x="'+n.x+'" y="'+n.y+'" width="'+n.w+'" height="'+n.h+'" rx="8"/><text class="aag-name" x="'+(n.x+15)+'" y="'+(n.y+26)+'">'+esc(this.text(st.zh,st.en))+'</text><text class="aag-small" x="'+(n.x+15)+'" y="'+(n.y+46)+'">'+esc(st.value+' · '+this.text(st.unit,st.id==='plan'?'role profiles':st.id==='dispatch'?'plans awaiting review':st.id==='work'?'tasks in progress':'deliveries pending'))+'</text>'+(n.h>65?'<text class="aag-small" x="'+(n.x+15)+'" y="'+(n.y+67)+'">'+esc(trim(st.people.map(p=>p.code||p.name).join(' · ')||this.text('岗位未配置','No role configured'),42))+'</text>':'')+'</g>';}
    });
    if(!this.m.people.length)html+='<text class="aag-small" x="300" y="'+(accept.y+123)+'">'+esc(this.text('暂无员工档案','No employee profiles'))+'</text>';
    this.world.innerHTML=html;this.svg.setAttribute('viewBox','0 0 '+s.width+' '+s.height);this.svg.style.aspectRatio=s.width+'/'+s.height;this.transform();if(focused)this.focusNode(focused);
  };
  Panel.prototype.statusText=function(t){const labels={'已确认运行':'Verified running','运行未确认':'Run unconfirmed','暂停':'Paused','失败':'Failed','停止':'Stopped','等待':'Waiting','已领活':'Task claimed','空着':'Idle'};return this.text(t,labels[t]||t);};
  Panel.prototype.link=function(record,zh,en){const id='link-'+this.links.size;this.links.set(id,record);return '<button class="sbtn" data-aag-open="'+id+'">'+this.label(zh,en)+'</button>';};
  Panel.prototype.taskMarkup=function(t){const r=t.raw,plan=r.execution_plan;return '<div class="aag-record"><b>'+esc(t.key)+'</b><p>'+esc(r.what)+'</p><div class="hint">'+esc(r.col||'')+' · '+esc(r.who||this.text('未分配','Unassigned'))+'</div>'+(r.how?'<p>'+esc(r.how)+'</p>':'')+(plan?'<div class="hint">'+esc(plan.code+' · '+(plan.display_state||(plan.state==='通过'&&plan.valid===false?'失效':plan.state)||''))+'</div>':'')+this.link({kind:'task',key:t.key,taskKey:t.key},'打开任务','Open task')+'</div>';};
  Panel.prototype.detail=function(){
    this.links=new Map();const p=this.m.people.find(x=>x.id===this.selected),stage=this.m.stages.find(x=>'stage:'+x.id===this.selected),row=(zh,en,value)=>'<dt>'+this.label(zh,en)+'</dt><dd>'+value+'</dd>';let html='';
    if(p){const r=p.raw;html='<h3>'+esc([p.code,p.name].filter(Boolean).join(' '))+'</h3><dl class="aag-fields">'+row('状态','State',esc(this.statusText(p.status)))+row('岗位','Roles',esc(p.roles.join('、')||this.text('未记录','Not recorded')))+row('上级','Supervisor',esc(p.boss==='人'?this.text('你','You'):p.boss||this.text('未记录','Not recorded')))+row('程序','Program',esc(r.program||this.text('未记录','Not recorded')))+row('工种','Crafts',esc(arr(r.crafts).join('、')||this.text('未限定','Not limited')))+row('负责范围','Scope',esc(arr(r.scope).join('、')||this.text('未限定','Not limited')))+row('核心权限','Core permission',esc(r.core||this.text('未记录','Not recorded')))+row('等待原因','Waiting reason',esc(p.run&&p.run.reason||this.text('未记录','Not recorded')))+row('最近结果','Latest result',esc(p.run&&p.run.last_result||this.text('未记录','Not recorded')))+'</dl><div class="acts">'+this.link({kind:'agent',key:p.code||p.name,agentCode:p.code},'打开档案','Open profile')+(p.windows.length?this.link({kind:'terminal',key:'s:term',agentCode:p.code},'打开终端页','Open terminals'):'')+'</div><h4>'+this.label('当前任务','Current tasks')+'</h4>'+(p.tasks.map(t=>this.taskMarkup(t)).join('')||'<p class="hint">'+this.label('未领取任务','No assigned tasks')+'</p>')+(p.missing.length?'<p class="warnt">'+this.label('任务记录未找到','Task records unavailable')+'：'+esc(p.missing.join('、'))+'</p>':'')+'<h4>'+this.label('关联交付','Linked deliveries')+'</h4>'+(p.deliveries.slice(0,8).map(d=>'<div class="aag-record">'+esc(d.code+' · '+d.state)+'<p>'+esc(d.what)+'</p>'+this.link({kind:'delivery',key:d.code},'打开交付','Open delivery')+'</div>').join('')||'<p class="hint">'+this.label('尚无交付','No deliveries')+'</p>');
    }else if(stage){html='<h3>'+this.label(stage.zh,stage.en)+'</h3><div class="hint">'+this.label('固定流程阶段','Protocol stage')+'</div><h4>'+this.label('岗位档案','Role profiles')+'</h4>'+(stage.people.map(p=>'<div class="aag-record"><button class="sbtn" data-aag-select="'+esc(p.id)+'">'+esc([p.code,p.name].filter(Boolean).join(' '))+'</button><div class="hint">'+esc(p.roles.join('、'))+'</div></div>').join('')||'<p class="hint">'+this.label('岗位未配置','No role configured')+'</p>');
      if(stage.id==='dispatch'){html+='<h4>'+this.label('待审计划','Pending plans')+'</h4>'+(this.m.pendingPlans.map(p=>'<p>'+esc(p.code+' · '+taskKey(p)+' · '+(p.by||p.agent||''))+'</p>').join('')||'<p class="hint">'+this.label('暂无待审计划','No pending plans')+'</p>')+'<h4>'+this.label('未分配任务','Unassigned tasks')+'</h4>'+this.m.tasks.filter(t=>t.assignment==='unassigned').slice(0,12).map(t=>this.taskMarkup(t)).join('');}
      if(stage.id==='work')html+='<h4>'+this.label('在做的任务','Tasks in progress')+'</h4>'+this.m.tasks.filter(t=>t.raw.col==='在做').slice(0,12).map(t=>this.taskMarkup(t)).join('');
      if(stage.id==='accept')html+='<h4>'+this.label('待验收交付','Pending deliveries')+'</h4>'+(this.m.pendingDeliveries.map(d=>'<div class="aag-record">'+esc(d.code+' · '+taskKey(d)+' · '+d.state)+'<p>'+esc(d.what)+'</p>'+this.link({kind:'delivery',key:d.code},'打开交付','Open delivery')+'</div>').join('')||'<p class="hint">'+this.label('暂无待验收交付','No pending deliveries')+'</p>');
      html+='<div class="acts">'+this.link({kind:'organization',key:'s:agents'},'打开组织与员工','Open organization')+'</div>';
    }
    if(this.m.issues.length)html+='<details><summary>'+this.label('未明确的记录','Unresolved records')+' '+this.m.issues.length+'</summary>'+this.m.issues.map(i=>'<p class="hint">'+esc((i.key||'')+' '+i.text)+'</p>').join('')+'</details>';
    if(html!==this.detailHTML){const scroll=this.body.scrollTop;this.body.innerHTML=html;this.body.scrollTop=scroll;this.detailHTML=html;}
  };
  Panel.prototype.log=function(){
    const rows=[];arr((this.ctx.launch||{}).status).forEach(r=>{arr(r.history).forEach(h=>rows.push({at:h.at||h.updated||'',who:r.code||r.name||'',text:typeof h==='string'?h:[h.action,h.status||h.state,h.reason,h.last_result||h.result].filter(Boolean).join(' · ')}));if(!arr(r.history).length&&r.last_result)rows.push({at:r.updated||'',who:r.code||r.name||'',text:r.last_result});});arr(this.ctx.deliveries).forEach(d=>rows.push({at:d.at||'',who:d.by||'',text:[d.code,d.state,d.what].filter(Boolean).join(' · ')}));rows.sort((a,b)=>str(b.at).localeCompare(str(a.at)));
    this.host.querySelector('.aag-log summary').innerHTML=this.label('最近记录','Recent records')+' · '+rows.length;const body=this.host.querySelector('.aag-log-body'),html=rows.length?'<table>'+rows.slice(0,12).map(r=>'<tr><td>'+esc(r.at||'—')+'</td><td>'+esc(r.who)+'</td><td>'+esc(r.text)+'</td></tr>').join('')+'</table>':'<p class="hint">'+this.label('暂无运行历史或交付记录','No runtime history or deliveries')+'</p>';if(body.innerHTML!==html)body.innerHTML=html;
  };
  Panel.prototype.persist=function(){writeLayout(this.storage,this.root,{selected:this.selected,pose:this.pose,motion:this.motion,height:this.height,detail:this.detailSize,positions:this.positions});};
  Panel.prototype.focusNode=function(id){const node=Array.from(this.svg.querySelectorAll('[data-aag-select]')).find(n=>n.dataset.aagSelect===id);if(node&&node.focus)node.focus({preventScroll:true});};
  Panel.prototype.movePerson=function(id,point){const node=this.scene.nodes.find(n=>n.id===id&&n.kind==='person');if(!node)return;this.positions[id]=clampNodePosition(point,node,this.scene);this.scene=layout(this.m,this.positions);this.draw();};
  Panel.prototype.applySize=function(){
    if(!this.stage)return;this.stage.style.height=this.fs?'100%':this.height+'px';
    if(this.fs){this.placePane();return;}
    const width=this.sceneEl.getBoundingClientRect().width||global.innerWidth||990,readingWidth=Math.min(this.detailSize.width,Math.max(260,width-280));this.sceneEl.style.setProperty('--aag-reading-width',readingWidth+'px');this.reading.style.height=this.detailSize.height+'px';this.reading.style.width='';this.reading.style.left='';this.reading.style.top='';
    const h=this.host.querySelector('[data-aag-size="height"]'),r=this.host.querySelector('[data-aag-size="reading"]');h.setAttribute('aria-label',this.text('拖动调整图高','Drag to resize graph height'));h.setAttribute('aria-valuenow',this.height);h.setAttribute('aria-valuemin',480);h.setAttribute('aria-valuemax',1800);h.title=this.text('拖动底边，或方向键调整高度','Drag bottom edge or use arrow keys');r.setAttribute('aria-label',this.text('拉宽或拉高详情窗','Resize details width and height'));r.title=this.text('拖动右下角，或方向键调整大小','Drag corner or use arrow keys');
    const edit=this.host.querySelector('[data-aag="edit-flow"]');edit.disabled=typeof this.h.editFlow!=='function';
  };
  Panel.prototype.transform=function(){this.world.setAttribute('transform','translate('+this.pose.x+' '+this.pose.y+') scale('+this.pose.s+')');};
  Panel.prototype.zoom=function(factor){this.pose.s=Math.max(.3,Math.min(3.6,this.pose.s*factor));this.transform();this.persist();};
  Panel.prototype.action=function(action){if(action==='edit-flow'&&typeof this.h.editFlow==='function')this.h.editFlow();if(action==='in'||action==='out')this.zoom(action==='in'?1.2:1/1.2);if(action==='fit'){this.pose={x:0,y:0,s:1};this.transform();this.persist();}if(action==='motion'){this.motion=!this.motion;this.update(this.ctx);this.persist();}if(action==='notes'){if(typeof this.h.notes==='function'){const n=this.h.notes();if(n)this.note=n;this.placeNote();}}if(action==='full'){if(this.fs)this.exitFullscreen();else this.enterFullscreen();}};
  Panel.prototype.defaultPane=function(){this.pane={x:Math.max(8,global.innerWidth-this.detailSize.width-20),y:80,width:this.detailSize.width,height:this.detailSize.height};};
  Panel.prototype.placePane=function(){if(!this.fs)return;if(!this.pane)this.defaultPane();this.pane=clampPane(this.pane,{width:global.innerWidth,height:global.innerHeight});Object.assign(this.reading.style,{left:this.pane.x+'px',top:this.pane.y+'px',width:this.pane.width+'px',height:this.pane.height+'px'});};
  Panel.prototype.placeNote=function(){if(!this.fs||!this.note||!this.note.isConnected)return;if(!this.noteHome){this.noteHome={parent:this.note.parentNode,next:this.note.nextSibling};}if(this.note.parentNode!==this.panel)this.panel.appendChild(this.note);};
  Panel.prototype.returnNote=function(){if(!this.noteHome)return;const n=this.note,h=this.noteHome;this.noteHome=null;if(!n||!n.isConnected)return;const parent=h.parent&&h.parent.isConnected?h.parent:document.body;if(h.next&&h.next.parentNode===parent)parent.insertBefore(n,h.next);else parent.appendChild(n);};
  Panel.prototype.syncFullscreen=function(){this.panel.classList.toggle('aag-fs',this.fs);this.host.querySelector('[data-aag="full"]').innerHTML=this.label(this.fs?'退出全屏':'全屏',this.fs?'Exit fullscreen':'Fullscreen');if(this.fs){if(this.paneStyle==null)this.paneStyle=this.reading.getAttribute('style')||'';this.applySize();this.placePane();this.placeNote();}else{if(this.paneStyle!=null)this.reading.setAttribute('style',this.paneStyle);this.paneStyle=null;this.pane=null;this.applySize();this.returnNote();}};
  Panel.prototype.enterFullscreen=async function(){const token=++this.fsSerial;this.fs=true;this.fsMode='window';this.syncFullscreen();if(typeof this.panel.requestFullscreen==='function')try{await this.panel.requestFullscreen();if(this.destroyed||token!==this.fsSerial){if(document.fullscreenElement===this.panel)await document.exitFullscreen();return;}if(document.fullscreenElement===this.panel)this.fsMode='native';}catch(e){/* 当前窗口全屏已可使用。 */}};
  Panel.prototype.exitFullscreen=function(){++this.fsSerial;this.fs=false;this.fsMode='';this.syncFullscreen();if(document.fullscreenElement===this.panel&&document.exitFullscreen)Promise.resolve(document.exitFullscreen()).catch(()=>{});};
  Panel.prototype.getState=function(){return {selected:this.selected,pose:{...this.pose},motion:this.motion,height:this.height,detail:{...this.detailSize},positions:{...this.positions},fullscreen:this.fs,fullscreenMode:this.fsMode,pane:this.pane?{...this.pane}:null};};
  Panel.prototype.destroy=function(){if(this.destroyed)return;this.persist();this.destroyed=true;this.drag=this.dragPane=this.dragNode=this.sizeDrag=null;this.exitFullscreen();this.host.removeEventListener('click',this.click);this.host.removeEventListener('pointerdown',this.down);this.host.removeEventListener('dblclick',this.dbl);this.svg.removeEventListener('wheel',this.wheel);global.removeEventListener('pointermove',this.move);global.removeEventListener('pointerup',this.up);global.removeEventListener('pointercancel',this.up);global.removeEventListener('keydown',this.key);global.removeEventListener('resize',this.resize);document.removeEventListener('fullscreenchange',this.fsChange);controllers.delete(this.host);};
  function mount(host,ctx,helpers){let panel=controllers.get(host);const root=ctx.state&&ctx.state.project&&ctx.state.project.root||'';if(panel&&panel.root!==root){panel.destroy();panel=null;}if(!panel){panel=new Panel(host,ctx,helpers);controllers.set(host,panel);}else panel.update(ctx,helpers);return panel;}
  function update(host,ctx,helpers){return mount(host,ctx,helpers);}
  function dispose(host){if(host){const panel=controllers.get(host);if(panel)panel.destroy();}else Array.from(controllers.values()).forEach(panel=>panel.destroy());}
  global.AgentAllocation={model,mount,update,dispose};if(typeof module==='object'&&module.exports)module.exports=model;
})(typeof window==='object'?window:globalThis);
