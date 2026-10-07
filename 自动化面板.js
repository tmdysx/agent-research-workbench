/* Project → goal → task. This is a view of existing records, never a scheduler. */
(function (global) {
  'use strict';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const words = { '能做':'Ready', '在做':'Claimed / in progress', '等着':'Waiting', '等验收':'Awaiting acceptance', '做完':'Done', '以后':'Later' };
  const colors = {'能做':'var(--muted)','在做':'var(--ch1)','等着':'var(--warn)','等验收':'var(--warn)','做完':'var(--good)','以后':'var(--muted)'};
  function goals(state, board) {
    const result = [], seen = new Set();
    ((state.blueprint || []).concat(state.module_blueprint || [])).forEach(g => {
      if (!seen.has(g.code)) { seen.add(g.code); result.push({key:g.code,name:g.name || g.code,kind:g.kind || 'S1'}); }
    });
    (board.items || []).forEach(t => { if (!seen.has(t.goal)) { seen.add(t.goal); result.push({key:t.goal,name:t.goal_name || t.goal,kind:t.kind}); } });
    return result;
  }
  function taskKey(r, launch, deliveries) {
    const c = r.current;
    if (!c || typeof c !== 'object') return '';
    const t = c.task || c.construction_plan || c.review || c.draft;
    if (t && t.goal && t.sub) return t.goal + ' ' + t.sub;
    const code = typeof t === 'string' ? t : t && t.code;
    const doc = (launch.plans || []).concat(deliveries || []).find(x => x.code === code);
    return doc && doc.goal && doc.sub ? doc.goal + ' ' + doc.sub : '';
  }
  function activity(ctx) {
    const active = new Set(), launch = ctx.launch || {};
    if (!ctx.state || !ctx.state.project || !ctx.state.project.root || !ctx.online || ctx.errors && ctx.errors.length || !launch.on || launch.pause) return active;
    (launch.status || []).forEach(r => {
      if (r.status !== 'running' || !r.code) return;
      const win = (launch.windows || []).find(w => w.alive && w.agent_code === r.code && w.project_root === ctx.state.project.root);
      const key = taskKey(r, launch, ctx.deliveries);
      if (win && key && (ctx.board.items || []).some(t => t.key === key)) active.add(key);
    });
    return active;
  }
  function eligibleWindows(ctx, task) {
    if (!task || !ctx.state || !ctx.state.project || !ctx.state.project.root) return [];
    const roster = ctx.roster || [], actor = String(task.who || '').replace(/^agent:/, '');
    const employee = roster.find(a => a.code === actor || a.name === actor);
    if (!employee || !employee.code) return [];
    return ((ctx.launch || {}).windows || []).filter(w => w.agent_code === employee.code && w.project_root === ctx.state.project.root);
  }
  function taskOwner(ctx, task) {
    const actor = String(task && task.who || '').replace(/^agent:/, '');
    const employee = (ctx.roster || []).find(a => a.code === actor || a.name === actor);
    return employee ? employee.code : actor;
  }
  function overviewMode(mode) { return ['map','flow','model3d'].includes(mode) ? mode : 'map'; }
  function readOverviewMode(ctx) { try { if(typeof global.researchOverviewMode==='function')return overviewMode(global.researchOverviewMode('common:auto')); }catch(e){} return overviewMode(ctx && ctx.overviewMode); }
  function clampPane(box, viewport) {
    const n=(v,f)=>Number.isFinite(v)?v:f,W=Math.max(1,n(viewport.width,1024)),H=Math.max(1,n(viewport.height,768)),gap=Math.min(8,W/4,H/4);
    const width=Math.min(W-gap*2,Math.max(1,n(box.width,320))),height=Math.min(H-gap*2,Math.max(1,n(box.height,500)));
    return {x:Math.max(gap,Math.min(n(box.x,gap),W-gap-width)),y:Math.max(gap,Math.min(n(box.y,gap),H-gap-height)),width,height};
  }
  function overviewLayout(mode, gs, goal, tasks) {
    mode=overviewMode(mode);
    const visible=(tasks||[]).filter(t=>t.goal===goal && gs.some(g=>g.key===t.goal)),H=Math.max(620,gs.length*42+90,visible.length*58+110);
    const nodes=[{id:'project:root',kind:'project',key:'',x:mode==='flow'?110:80,y:H/2,z:0,r:32}],edges=[];
    gs.forEach((g,i)=>{
      const angle=-Math.PI/2+i*2*Math.PI/Math.max(1,gs.length);
      nodes.push({id:'goal:'+g.key,kind:'goal',key:g.key,x:mode==='flow'?420:365,y:gs.length===1?H/2:45+i*(H-90)/Math.max(1,gs.length-1),z:0,r:12,
        world:mode==='model3d'?{x:260*Math.cos(angle),y:0,z:260*Math.sin(angle)}:null});
      edges.push({from:'project:root',to:'goal:'+g.key});
    });
    if(mode==='model3d')nodes[0].world={x:0,y:-210,z:0};
    const parent=nodes.find(n=>n.id==='goal:'+goal);
    visible.forEach((t,i)=>{
      const angle=-Math.PI/2+i*2*Math.PI/Math.max(1,visible.length);
      nodes.push({id:'task:'+t.key,kind:'task',key:t.key,x:mode==='flow'?835:730,y:55+i*58,z:0,r:8,
        world:mode==='model3d'?{x:parent.world.x+145*Math.cos(angle),y:200,z:parent.world.z+145*Math.sin(angle)}:null});
      edges.push({from:'goal:'+t.goal,to:'task:'+t.key});
    });
    return {mode,H:mode==='model3d'?620:H,nodes,edges};
  }
  function projectPoint(point, camera) {
    const n=(v,f)=>Number.isFinite(v)?v:f,c=camera||{},yaw=n(c.yaw,.55),pitch=n(c.pitch,.28),distance=Math.max(350,Math.min(1800,n(c.distance,850)));
    const x=n(point.x,0),y=n(point.y,0),z=n(point.z,0),rx=x*Math.cos(yaw)-z*Math.sin(yaw),rz=x*Math.sin(yaw)+z*Math.cos(yaw);
    const ry=y*Math.cos(pitch)-rz*Math.sin(pitch),depth=y*Math.sin(pitch)+rz*Math.cos(pitch),scale=720/Math.max(180,distance+depth);
    return {x:540+rx*scale,y:310+ry*scale,depth,scale};
  }
  function sceneSize(size, available) {
    const n=(v,f)=>Number.isFinite(v)?v:f, width=Math.max(300,n(available,1000));
    return {height:Math.max(440,Math.min(1800,n(size&&size.height,640))),width:Math.max(260,Math.min(width*.65,n(size&&size.width,420)))};
  }
  const model = {goals, taskKey, activity, eligibleWindows, overviewMode, overviewLayout, projectPoint, clampPane, sceneSize};
  let live = null;
  function update(host, ctx, helpers) {
    const root = ctx.state.project.root;
    if (!live || live.host !== host || live.root !== root || !host.querySelector('.ad-panel')) {
      if (live) dispose();
      live = new Panel(host, root, helpers);
    }
    live.update(ctx);
  }
  function dispose() { if (live) { live.destroy(); live = null; } }
  function Panel(host, root, helpers) {
    this.host = host; this.root = root; this.h = helpers; this.goal = ''; this.task = ''; this.q = ''; this.col = ''; this.limit = 8;
    this.tab = 'detail'; this.windowId = ''; this.input = false; this.motion = true; this.pose = {x:0,y:0,s:1}; this.epoch = 0; this.attachEpoch = 0;
    this.mode=readOverviewMode();this.poses={};this.camera={yaw:.55,pitch:.28,distance:850};
    this.signature = ''; this.terminalSrc = ''; this.requestId = 0; this.pendingSelect = null;
    this.fsSerial = 0; this.fsElement = null; this.fsPending = false; this.destroyed = false;
    this.windowOwner = null; this.windowWasMatched = false; this.detailRefresh = 0; this.detailMarkup = ''; this.detailRenderedKey = '';
    this.label = (zh,en) => this.h.lang() === 'en' ? en : zh + ' <span class="en">' + en + '</span>';
    const graphControls='<button class="sbtn" data-ad="out" aria-label="缩小 Zoom out">−</button><button class="sbtn" data-ad="in" aria-label="放大 Zoom in">+</button><button class="sbtn" data-ad="reset">'+this.label('复位','Reset')+'</button><button class="sbtn sticky-shortcut" data-ad="notes" aria-label="便签 Sticky note" title="便签 Sticky note">'+(this.h.notesIcon?this.h.notesIcon():'')+this.label('便签','Sticky note')+'</button>';
    host.innerHTML = '<div class="ad-panel"><div class="ad-controls"><button class="sbtn" data-auto-go="s:board">'+this.label('分列看板','Board')+'</button><input class="ad-search" aria-label="搜索任务 Search tasks" placeholder="' + (this.h.lang() === 'en' ? 'Search tasks' : '搜索任务：编号、名称、需求') + '"><select class="ad-status" aria-label="任务状态 Task status"><option value="">' + this.label('全部状态','All statuses') + '</option>' + Object.keys(words).map(c => '<option value="'+esc(c)+'">'+esc(this.h.lang()==='en'?words[c]:c)+'</option>').join('') + '</select><span class="ad-spacer"></span><button class="sbtn" data-ad="motion">'+this.label('暂停动画','Pause animation')+'</button>'+graphControls+'<button class="sbtn" data-ad="fullscreen">'+this.label('全屏','Fullscreen')+'</button></div>'
      + '<header class="ad-heading"><div><h1>'+this.label('自动化仪表盘','Automation dashboard')+'</h1><div class="ad-summary"></div></div></header><div class="ad-notice" role="status"></div>'
      + '<section class="ad-scene"><div class="ad-graph"><div class="ad-fullscreen-controls">'+graphControls+'<button class="sbtn" data-ad="fullscreen">'+this.label('退出全屏','Exit fullscreen')+'</button></div><svg class="ad-svg" viewBox="0 0 1080 620" role="group" aria-label="项目目标任务关系 Project goal task relationships"><g class="ad-world"></g></svg><div class="ad-graph-footer"></div></div><aside class="ad-aside"><div class="ad-pane-handle" data-ad-drag tabindex="0" role="button" aria-label="拖动详情与命令行 Drag details and terminal">'+this.label('详情与命令行','Details and terminal')+'</div><div class="ad-tabs" role="tablist"><button class="sbtn on" role="tab" aria-selected="true" data-ad="detail">'+this.label('任务详情','Task details')+'</button><button class="sbtn" role="tab" aria-selected="false" data-ad="terminal">'+this.label('命令行','Terminal')+'</button></div><section class="ad-detail"></section><section class="ad-terminal" hidden><button class="sbtn ad-exit-terminal" data-ad="terminal-fullscreen">'+this.label('退出全屏','Exit fullscreen')+'</button><div class="ad-window-controls"><select class="ad-windows" aria-label="选择已有命令行窗口 Select existing terminal"></select><button class="sbtn" data-ad="input">'+this.label('接管输入','Take input control')+'</button><button class="sbtn sticky-shortcut" data-ad="notes" aria-label="便签 Sticky note" title="便签 Sticky note">'+(this.h.notesIcon?this.h.notesIcon():'')+this.label('便签','Sticky note')+'</button><button class="sbtn" data-ad="terminal-fullscreen">'+this.label('放大窗口','Expand terminal')+'</button></div><div class="ad-terminal-status" role="status"></div><div class="ad-terminal-host"></div></section></aside></section><div class="ad-history"></div></div>';
    this.click = e => { const b=e.target.closest('[data-ad],[data-ad-goal],[data-ad-task]'); if (!b || !host.contains(b)) return; e.stopPropagation(); this.action(b); };
    this.keydown = e => {
      if(e.key==='Escape'){if(this.fsElement || document.fullscreenElement && host.contains(document.fullscreenElement))this.exitFullscreen();return;}
      if(this.paneBox && host.contains(e.target) && e.target.matches('[data-ad-drag]') && ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) { e.preventDefault();const step=e.shiftKey?32:8;this.paneBox.x+=(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0);this.paneBox.y+=(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0);this.positionPane();return; }
      if(host.contains(e.target) && (e.key==='Enter'||e.key===' ') && e.target.matches('[data-ad-goal],[data-ad-task]')) { e.preventDefault(); this.action(e.target); }
    };
    this.fullscreenChange = () => {
      const el=document.fullscreenElement;
      if(el){
        if(host.contains(el)){if(this.fsElement && (this.fsElement===el || this.fsElement.contains(el))){this.clearFullscreenFallback();this.fsElement=el;this.fsPending=false;}}
        else{this.clearFullscreenFallback();this.fsSerial++;this.fsElement=null;this.fsPending=false;}
      }
      else if(!this.fsPending && this.fsElement && !this.fsElement.classList.contains('ad-fs'))this.fsElement=null;
      this.syncPane();if(this.fsElement)this.placeNote();else this.returnNote();
    };
    this.overviewChange=()=>this.setMode(readOverviewMode(this.ctx));
    this.change = e => { if (e.target.matches('.ad-status')) { this.col=e.target.value;this.limit=8;this.draw(); } if(e.target.matches('.ad-windows')) {
      this.watch();this.windowId=e.target.value;
      const task=(this.ctx.board.items||[]).find(t=>t.key===this.task);
      this.windowOwner=taskOwner(this.ctx,task);this.windowWasMatched=eligibleWindows(this.ctx,task).some(w=>w.id===this.windowId);
      this.attach();
    } };
    this.search = e => { if(e.target.matches('.ad-search')) { this.q=e.target.value.trim().toLowerCase();this.limit=8;this.draw(); } };
    this.message = e => {
      const frame=host.querySelector('.ad-terminal-host iframe');
      if (!frame || e.source!==frame.contentWindow || !this.terminalSrc || e.origin!==new URL(this.terminalSrc).origin) return;
      const m=e.data || {};
      if(m.type==='terminal-ready' && m.viewer) { this.viewerReady=true; this.sendSelection(); }
      if(m.type==='terminal-selected' && m.requestId===this.requestId) {
        this.input=!!m.ok && m.mode==='control';
        this.status(m.ok ? (this.input ? this.label('正在接管输入','Input control enabled') : this.label('仅观看','Watch only')) : esc(m.error && (m.error.message || m.error) || '终端未就绪'));
        host.querySelector('[data-ad=input]').innerHTML=this.input?this.label('返回观看','Return to watching'):this.label('接管输入','Take input control');
      }
      if(m.type==='terminal-status') this.status(esc(m.message || m.state || ''));
    };
    host.addEventListener('click',this.click);host.addEventListener('change',this.change);host.addEventListener('input',this.search);global.addEventListener('keydown',this.keydown);global.addEventListener('message',this.message);global.addEventListener('research-overview-mode',this.overviewChange);document.addEventListener('fullscreenchange',this.fullscreenChange);
    this.sizeKey='research_dashboard_size:'+root;
    try{this.size=sceneSize(JSON.parse(global.localStorage.getItem(this.sizeKey)||'null'),host.clientWidth);}catch(_){this.size=sceneSize(null,host.clientWidth);}
    const scene=host.querySelector('.ad-scene'),aside=host.querySelector('.ad-aside');
    const grip=(kind,name)=>{const el=document.createElement('div');el.className='ad-size-grip ad-size-'+kind;el.dataset.adSize=kind;el.tabIndex=0;el.setAttribute('role','separator');el.setAttribute('aria-label',name);return el;};
    aside.appendChild(grip('pane','拉伸详情与命令行 Resize details and terminal'));
    scene.after(grip('height','拉伸总览高度 Resize overview height'));
    this.applySize=()=>{this.size=sceneSize(this.size,host.clientWidth);scene.style.height=this.size.height+'px';scene.style.setProperty('--ad-sidebar-width',this.size.width+'px');};
    this.saveSize=()=>{try{global.localStorage.setItem(this.sizeKey,JSON.stringify(this.size));}catch(_){}};
    this.applySize();
    this.sizeKeydown=e=>{const h=e.target.closest('[data-ad-size]');if(!h||!host.contains(h)||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const d=e.shiftKey?32:12,dx=e.key==='ArrowRight'?d:e.key==='ArrowLeft'?-d:0,dy=e.key==='ArrowDown'?d:e.key==='ArrowUp'?-d:0;
      if(this.paneBox&&h.dataset.adSize==='pane'){this.paneBox.width+=dx;this.paneBox.height+=dy;this.positionPane();}else{if(h.dataset.adSize==='pane')this.size.width+=dx;this.size.height+=dy;this.applySize();this.saveSize();}};
    host.addEventListener('keydown',this.sizeKeydown);
    this.paneDown=e=>{if(e.button!==0)return;const size=e.target.closest('[data-ad-size]');if(size&&host.contains(size)){e.preventDefault();e.stopPropagation();this.sizeDrag={x:e.clientX,y:e.clientY,kind:size.dataset.adSize,size:{...this.size},box:this.paneBox?{...this.paneBox}:null};if(size.setPointerCapture)size.setPointerCapture(e.pointerId);return;}const handle=e.target.closest('[data-ad-drag]');if(!this.paneBox||!handle||!host.contains(handle))return;e.preventDefault();e.stopPropagation();this.paneDrag={x:e.clientX,y:e.clientY,px:this.paneBox.x,py:this.paneBox.y};if(handle.setPointerCapture)handle.setPointerCapture(e.pointerId);};
    this.paneMove=e=>{if(this.sizeDrag){const d=this.sizeDrag,dx=e.clientX-d.x,dy=e.clientY-d.y;if(d.box&&d.kind==='pane'&&this.paneBox){this.paneBox.width=d.box.width+dx;this.paneBox.height=d.box.height+dy;this.positionPane();}else{this.size={height:d.size.height+dy,width:d.size.width+(d.kind==='pane'?-dx:0)};this.applySize();}return;}if(!this.paneDrag||!this.paneBox)return;this.paneBox.x=this.paneDrag.px+e.clientX-this.paneDrag.x;this.paneBox.y=this.paneDrag.py+e.clientY-this.paneDrag.y;this.positionPane();};
    this.paneUp=()=>{if(this.sizeDrag)this.saveSize();this.sizeDrag=null;this.paneDrag=null;};this.paneResize=()=>{if(this.paneBox)this.positionPane();else this.applySize();};
    this.paneCollapse=e=>{if(e.target===aside){this.watch();const terminal=this.host.querySelector('.ad-terminal');if(terminal&&(this.fsElement===terminal||document.fullscreenElement&&terminal.contains(document.fullscreenElement)))this.exitFullscreen();}};
    host.addEventListener('research-pane-collapse',this.paneCollapse);
    host.addEventListener('pointerdown',this.paneDown);global.addEventListener('pointermove',this.paneMove);global.addEventListener('pointerup',this.paneUp);global.addEventListener('pointercancel',this.paneUp);global.addEventListener('resize',this.paneResize);
    const svg=host.querySelector('.ad-svg');this.svg=svg;
    this.down=e=> { if(e.button!==0 || e.target.closest('[data-ad-goal],[data-ad-task]')) return;this.drag={x:e.clientX,y:e.clientY,px:this.pose.x,py:this.pose.y,yaw:this.camera.yaw,pitch:this.camera.pitch,rotate:this.mode==='model3d'&&!e.shiftKey};svg.setPointerCapture(e.pointerId); };
    this.move=e=> { if(!this.drag)return;if(this.drag.rotate){this.camera.yaw=this.drag.yaw+(e.clientX-this.drag.x)*.006;this.camera.pitch=Math.max(-1.2,Math.min(1.2,this.drag.pitch+(e.clientY-this.drag.y)*.005));this.queueProjection();return;}const r=svg.getBoundingClientRect(),vb=svg.viewBox.baseVal;this.pose.x=this.drag.px+(e.clientX-this.drag.x)*vb.width/r.width;this.pose.y=this.drag.py+(e.clientY-this.drag.y)*vb.height/r.height;this.transform(); };
    this.up=()=>{this.drag=null;};
    this.wheel=e=>{e.preventDefault();this.zoom(e.deltaY<0?1.12:1/1.12);};
    svg.addEventListener('pointerdown',this.down);svg.addEventListener('pointermove',this.move);svg.addEventListener('pointerup',this.up);svg.addEventListener('pointercancel',this.up);svg.addEventListener('wheel',this.wheel,{passive:false});
  }
  Panel.prototype.update = function(ctx) {
    // 成功刷新传来的普通 JSON 是新对象；同秒 stamp 不变也不能漏掉需求原文变化。
    if(this.detailBoard!==ctx.board || this.detailUpdated!==ctx.updated) {
      this.detailBoard=ctx.board;this.detailUpdated=ctx.updated;this.detailRefresh++;
    }
    this.ctx=ctx;
    this.setMode(readOverviewMode(ctx),false);
    const L=ctx.launch||{},counts=ctx.board.counts||{},gs=goals(ctx.state,ctx.board);
    if(this.goal && !gs.some(g=>g.key===this.goal)) { this.goal='';this.setTask(''); }
    if(this.task && !(ctx.board.items||[]).some(t=>t.key===this.task)) this.setTask('');
    const gate=L.pause?this.label('已暂停','Paused'):L.on?this.label('已允许自动开工','Automatic dispatch enabled'):this.label('未允许自动开工','Automatic dispatch disabled');
    this.host.querySelector('.ad-summary').innerHTML=gate+' · '+Object.keys(words).filter(c=>c!=='以后').map(c=>esc((this.h.lang()==='en'?words[c]:c)+' '+(counts[c] == null?'—':counts[c]))).join(' · ');
    this.host.querySelector('.ad-notice').innerHTML=ctx.errors&&ctx.errors.length?esc(ctx.errors.join(' · '))+' · '+this.label('保留最后成功数据','Showing last successful data'):(L.pause?esc(L.pause):'') + ((L.missing_roles||[]).length?'<details><summary>'+this.label('缺少岗位','Missing roles')+' · '+L.missing_roles.length+'</summary>'+L.missing_roles.map(esc).join('<br>')+'</details>':'');
    const sig=JSON.stringify([gs,ctx.board.items,Array.from(activity(ctx)),this.h.lang(),this.mode]);
    if(sig!==this.signature){this.signature=sig;this.draw();}
    this.windows();
    this.host.querySelector('.ad-panel').classList.toggle('ad-motion',this.motion && activity(ctx).size>0);
    if(this.task && this.tab==='detail') this.detail();
    if(this.tab==='terminal') this.attach();
  };
  Panel.prototype.setMode=function(mode,redraw){
    mode=overviewMode(mode);if(mode===this.mode)return;
    this.poses[this.mode]=Object.assign({},this.pose);this.mode=mode;this.pose=this.poses[mode]||{x:0,y:0,s:1};this.drag=null;
    const panel=this.host.querySelector('.ad-panel');if(panel)panel.dataset.overviewMode=mode;
    if(redraw!==false && this.ctx)this.draw();
  };
  Panel.prototype.draw=function(){
    const ctx=this.ctx, gs=goals(ctx.state,ctx.board), active=activity(ctx),items=ctx.board.items||[];
    let tasks=items.filter(t=>t.goal===this.goal&&(!this.col||t.col===this.col)&&(!this.q||[t.key,t.what,t.how].concat(t.needs||[]).join(' ').toLowerCase().includes(this.q)));
    tasks.sort((a,b)=>['在做','等验收','等着','能做','做完','以后'].indexOf(a.col)-['在做','等验收','等着','能做','做完','以后'].indexOf(b.col));
    const visible=tasks.slice(0,this.limit),layout=overviewLayout(this.mode,gs,this.goal,visible),H=layout.H,mid=H/2;
    const path=(x1,y1,x2,y2,on)=>'<path class="ad-edge'+(on?' active':'')+'" d="M'+x1+','+y1+' C'+(x1+90)+','+y1+' '+(x2-90)+','+y2+' '+x2+','+y2+'"/>';
    const node=(x,y,r,title,sub,data,on,chosen,color)=>'<g class="ad-node'+(on?' active':'')+(chosen?' selected':'')+'" role="button" tabindex="0" '+data+' aria-label="'+esc(title+' '+sub)+'" transform="translate('+x+' '+y+')"><title>'+esc(title+' '+sub)+'</title><circle class="ad-halo" r="'+(r+5)+'"/><circle r="'+r+'" style="stroke:'+(color||'var(--accent)')+'"/><text x="'+(r+12)+'" y="-3">'+esc(title.length>18?title.slice(0,17)+'…':title)+'</text><text class="ad-node-sub" x="'+(r+12)+'" y="15">'+esc(sub)+'</text></g>';
    const panel=this.host.querySelector('.ad-panel');if(panel)panel.dataset.overviewMode=this.mode;
    const positions=new Map(layout.nodes.map(n=>[n.id,this.mode==='model3d'?Object.assign({},n,projectPoint(n.world,this.camera)):n]));
    let edges='',nodes='';
    layout.edges.forEach((e,i)=>{
      const a=positions.get(e.from),b=positions.get(e.to),on=b.kind==='task'?active.has(b.key):items.some(t=>t.goal===b.key&&active.has(t.key));
      if(this.mode==='map')edges+=path(a.x+a.r,a.y,b.x,b.y,on);
      else{const d=this.mode==='flow'?'M'+(a.x+(a.kind==='project'?90:110))+','+a.y+' H'+((a.x+b.x)/2)+' V'+b.y+' H'+(b.x-(b.kind==='task'?125:110)):'M'+a.x+','+a.y+' L'+b.x+','+b.y;edges+='<path class="ad-edge'+(on?' active':'')+'" data-ad-edge-index="'+i+'" d="'+d+'"/>';}
    });
    const ordered=Array.from(positions.values());if(this.mode==='model3d')ordered.sort((a,b)=>b.depth-a.depth);
    ordered.forEach(n=>{
      const g=gs.find(g=>g.key===n.key),t=visible.find(t=>t.key===n.key),own=g?items.filter(t=>t.goal===g.key):[];
      const title=String(n.kind==='project'?ctx.state.project.name:g?g.name:t.what||t.key),sub=n.kind==='project'?'S0':g?(g.kind==='module'?(this.h.lang()==='en'?'Module tasks':'模块任务'):g.key)+' · '+own.length+' '+(this.h.lang()==='en'?'tasks':'件'):(this.h.lang()==='en'?words[t.col]||t.col:t.col)+' · '+t.key;
      const data=n.kind==='project'?'data-ad="reset"':g?'data-ad-goal="'+esc(g.key)+'"':'data-ad-task="'+esc(t.key)+'"',on=n.kind==='project'?active.size>0:g?own.some(t=>active.has(t.key)):active.has(t.key),chosen=g?g.key===this.goal:t&&t.key===this.task,color=n.kind==='project'?'var(--tool-gold)':t?colors[t.col]||'var(--muted)':'var(--accent)';
      if(this.mode==='map'){nodes+=node(n.x,n.y,n.r,title,sub,data,on,chosen,color);return;}
      const label=esc(title.length>18?title.slice(0,17)+'…':title),stroke=chosen?'var(--hover-gold)':color;
      let shape='';
      if(this.mode==='flow')shape='<rect x="-'+(n.kind==='task'?125:n.kind==='project'?90:110)+'" y="-23" width="'+(n.kind==='task'?250:n.kind==='project'?180:220)+'" height="46" rx="5" fill="var(--card)" style="stroke:'+stroke+'"/>';
      else{
        const p=n.world,r=n.kind==='project'?25:16,point=(x,y,z)=>{const v=projectPoint({x:p.x+x*r,y:p.y+y*r,z:p.z+z*r},this.camera);return(v.x-n.x)+','+(v.y-n.y);};
        shape=[[[1,-1,-1],[1,-1,1],[1,1,1],[1,1,-1]],[[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],[[-1,-1,-1],[1,-1,-1],[1,-1,1],[-1,-1,1]]].map((face,i)=>'<polygon points="'+face.map(p=>point(...p)).join(' ')+'" fill="var(--card)" style="stroke:'+stroke+'"/><polygon points="'+face.map(p=>point(...p)).join(' ')+'" fill="'+color+'" opacity="'+(.12+i*.09)+'"/>').join('');
      }
      nodes+='<g class="ad-node ad-'+(this.mode==='flow'?'flow':'model')+'-node'+(on?' active':'')+(chosen?' selected':'')+'" data-ad-node="'+esc(n.id)+'" role="button" tabindex="0" '+data+' aria-label="'+esc(title+' '+sub)+'" transform="translate('+n.x+' '+n.y+')"><title>'+esc(title+' '+sub)+'</title>'+shape+'<text x="'+(this.mode==='flow'?-(n.kind==='task'?115:n.kind==='project'?80:100):26)+'" y="-3">'+label+'</text><text class="ad-node-sub" x="'+(this.mode==='flow'?-(n.kind==='task'?115:n.kind==='project'?80:100):26)+'" y="15">'+esc(sub)+'</text></g>';
    });
    if(this.goal&&!visible.length){const empty=!items.some(t=>t.goal===this.goal);nodes+='<text x="750" y="'+mid+'" class="ad-node-sub">'+esc(this.h.lang()==='en'?(empty?'No tasks':'No matching tasks'):(empty?'暂无任务':'暂无符合条件的任务'))+'</text>';}
    const svg=this.host.querySelector('.ad-svg');svg.setAttribute('viewBox','0 0 1080 '+H);svg.querySelector('.ad-world').innerHTML=edges+nodes;this.sceneLayout=layout;this.transform();
    this.host.querySelector('.ad-graph-footer').innerHTML=(this.goal?esc((this.h.lang()==='en'?'Showing ':'显示 ')+visible.length+' / '+tasks.length)+' '+(visible.length<tasks.length?'<button class="sbtn" data-ad="more">'+this.label('再看 8 件','Show 8 more')+'</button>':''):this.label('点击目标展开任务','Select a goal to expand tasks'));
    this.host.querySelector('.ad-panel').classList.toggle('ad-motion',this.motion&&active.size>0);
    if(!this.task) this.host.querySelector('.ad-detail').innerHTML='<h2>'+this.label('选择任务','Select a task')+'</h2><p class="hint">'+this.label('需求、验收、计划与交付','Requirements, acceptance, plans and deliveries')+'</p>';
  };
  Panel.prototype.transform=function(){const w=this.host.querySelector('.ad-world');if(w)w.setAttribute('transform','translate('+this.pose.x+' '+this.pose.y+') scale('+this.pose.s+')');};
  Panel.prototype.queueProjection=function(){if(this.projectionFrame)return;if(typeof global.requestAnimationFrame!=='function'){this.projectCamera();return;}this.projectionFrame=global.requestAnimationFrame(()=>{this.projectionFrame=0;if(!this.destroyed)this.projectCamera();});};
  Panel.prototype.projectCamera=function(){
    if(this.mode!=='model3d' || !this.sceneLayout || this.sceneLayout.mode!=='model3d')return;
    const world=this.host.querySelector('.ad-world'),layout=this.sceneLayout,positions=new Map(layout.nodes.map(n=>[n.id,Object.assign({},n,projectPoint(n.world,this.camera))]));
    if(!world)return;
    world.querySelectorAll('[data-ad-edge-index]').forEach(el=>{const e=layout.edges[+el.dataset.adEdgeIndex];if(!e)return;const a=positions.get(e.from),b=positions.get(e.to);el.setAttribute('d','M'+a.x+','+a.y+' L'+b.x+','+b.y);});
    const elements=Array.from(world.querySelectorAll('[data-ad-node]')),focused=document.activeElement;
    elements.forEach(el=>{
      const n=positions.get(el.dataset.adNode);if(!n)return;el.setAttribute('transform','translate('+n.x+' '+n.y+')');
      const p=n.world,r=n.kind==='project'?25:16,point=(x,y,z)=>{const v=projectPoint({x:p.x+x*r,y:p.y+y*r,z:p.z+z*r},this.camera);return(v.x-n.x)+','+(v.y-n.y);},polys=el.querySelectorAll('polygon');
      [[[1,-1,-1],[1,-1,1],[1,1,1],[1,1,-1]],[[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],[[-1,-1,-1],[1,-1,-1],[1,-1,1],[-1,-1,1]]].forEach((face,i)=>{const pts=face.map(p=>point(...p)).join(' ');if(polys[i*2])polys[i*2].setAttribute('points',pts);if(polys[i*2+1])polys[i*2+1].setAttribute('points',pts);});
    });
    elements.sort((a,b)=>positions.get(b.dataset.adNode).depth-positions.get(a.dataset.adNode).depth).forEach(el=>world.appendChild(el));
    if(elements.includes(focused) && document.activeElement!==focused)focused.focus({preventScroll:true});
  };
  Panel.prototype.zoom=function(f){if(this.mode==='model3d'){this.camera.distance=Math.max(350,Math.min(1800,this.camera.distance/f));this.projectCamera();return;}this.pose.s=Math.max(.45,Math.min(3,this.pose.s*f));this.transform();};
  Panel.prototype.viewport=function(){return {width:global.innerWidth,height:global.innerHeight};};
  Panel.prototype.positionPane=function(){
    const pane=this.host.querySelector('.ad-aside');if(!pane || !this.paneBox)return;
    this.paneBox=clampPane(this.paneBox,this.viewport());const b=this.paneBox;
    Object.assign(pane.style,{position:'fixed',left:b.x+'px',top:b.y+'px',right:'auto',bottom:'auto',width:b.width+'px',height:b.height+'px',maxWidth:'none',maxHeight:'none',margin:'0',zIndex:'3'});
  };
  Panel.prototype.restorePane=function(){
    const pane=this.host.querySelector('.ad-aside');if(pane && this.paneStyle){Object.keys(this.paneStyle).forEach(k=>{pane.style[k]=this.paneStyle[k];});pane.classList.remove('ad-pane-floating');}
    this.paneStyle=null;this.paneBox=null;this.paneDrag=null;this.paneRect=null;
  };
  Panel.prototype.syncPane=function(){
    const scene=this.host.querySelector('.ad-scene'),pane=this.host.querySelector('.ad-aside'),active=!this.destroyed && this.fsElement===scene && scene && (document.fullscreenElement===scene || scene.classList.contains('ad-fs'));
    if(!active){this.restorePane();return;}if(!pane || this.paneBox)return;
    const r=this.paneRect || pane.getBoundingClientRect(),v=this.viewport();this.paneStyle={};
    ['position','left','top','right','bottom','width','height','maxWidth','maxHeight','margin','zIndex'].forEach(k=>{this.paneStyle[k]=pane.style[k]||'';});
    this.paneBox={x:(v.width||1024)-(r.width||350)-16,y:64,width:r.width||350,height:r.height||520};pane.classList.add('ad-pane-floating');this.positionPane();
  };
  Panel.prototype.openNotes=function(){
    if(typeof this.h.notes!=='function')return;const note=this.h.notes();if(!note || !this.fsElement)return;
    if(this.noteElement!==note){this.returnNote();this.noteElement=note;this.noteZ=note.style.zIndex||'';}this.placeNote();
  };
  Panel.prototype.placeNote=function(){
    const note=this.noteElement,el=this.fsElement;if(!note || !el)return;
    if(document.fullscreenElement===el && !el.contains(note))el.appendChild(note);
    note.style.zIndex='10001';
  };
  Panel.prototype.returnNote=function(){
    const note=this.noteElement || (typeof document.getElementById==='function'?document.getElementById('note'):null);
    if(note && this.host.contains(note))document.body.appendChild(note);
    if(this.noteElement){this.noteElement.style.zIndex=this.noteZ;this.noteElement=null;this.noteZ='';}
  };
  Panel.prototype.clearFullscreenFallback=function(){
    if(this.fsElement)this.fsElement.classList.remove('ad-fs');
    ['.ad-scene','.ad-terminal'].forEach(s=>{const el=this.host.querySelector(s);if(el)el.classList.remove('ad-fs');});
  };
  Panel.prototype.exitFullscreen=function(){
    const current=document.fullscreenElement,previous=this.fsElement;
    this.fsSerial++;this.fsPending=false;this.clearFullscreenFallback();this.fsElement=null;this.returnNote();this.restorePane();
    if(current && (current===previous || this.host.contains(current)) && typeof document.exitFullscreen==='function'){
      try{return Promise.resolve(document.exitFullscreen()).catch(()=>{});}catch(e){}
    }
    return Promise.resolve();
  };
  Panel.prototype.fullscreen=async function(el){
    if(this.destroyed || !el)return;
    const current=document.fullscreenElement,same=this.fsElement===el || current===el;
    const owned=current && (current===this.fsElement || this.host.contains(current));
    const exiting=this.exitFullscreen(),serial=this.fsSerial;
    if(same)return;
    if(owned)await exiting;
    if(this.destroyed || serial!==this.fsSerial)return;
    const pane=this.host.querySelector('.ad-aside');if(el===this.host.querySelector('.ad-scene') && pane)this.paneRect=pane.getBoundingClientRect();
    this.fsElement=el;this.fsPending=true;
    try{if(typeof el.requestFullscreen==='function')await el.requestFullscreen();}catch(e){}
    if(this.destroyed || serial!==this.fsSerial){
      // A late native success after Esc/disposal must not reopen the removed view.
      if(document.fullscreenElement===el && this.fsElement!==el && typeof document.exitFullscreen==='function'){
        try{await document.exitFullscreen();}catch(e){}
      }
      return;
    }
    this.fsPending=false;
    if(document.fullscreenElement===el || document.fullscreenElement && el.contains(document.fullscreenElement)){
      this.clearFullscreenFallback();this.fsElement=document.fullscreenElement;
    }else{this.fsElement=el;el.classList.add('ad-fs');}
    this.syncPane();this.placeNote();
  };
  Panel.prototype.action=function(b){
    if(b.dataset.adGoal){this.goal=b.dataset.adGoal;this.limit=8;this.setTask('');this.draw();return;}
    if(b.dataset.adTask){this.setTask(b.dataset.adTask);this.draw();this.detail();this.windows();if(this.tab==='terminal')this.attach();return;}
    const a=b.dataset.ad;
    if(a==='notes')this.openNotes();
    if(a==='more'){this.limit+=8;this.draw();}
    if(a==='in'||a==='out')this.zoom(a==='in'?1.2:1/1.2);
    if(a==='reset'){this.pose={x:0,y:0,s:1};if(this.mode==='model3d'){this.camera={yaw:.55,pitch:.28,distance:850};this.draw();}else this.transform();}
    if(a==='motion'){this.motion=!this.motion;b.innerHTML=this.motion?this.label('暂停动画','Pause animation'):this.label('播放动画','Play animation');this.host.querySelector('.ad-panel').classList.toggle('ad-motion',this.motion&&activity(this.ctx).size>0);}
    if(a==='fullscreen'||a==='terminal-fullscreen')this.fullscreen(this.host.querySelector(a==='fullscreen'?'.ad-scene':'.ad-terminal'));
    if(a==='detail'||a==='terminal'){
      const terminal=this.host.querySelector('.ad-terminal');
      if(a==='detail' && (this.fsElement===terminal || document.fullscreenElement && terminal.contains(document.fullscreenElement)))this.exitFullscreen();
      this.tab=a;if(a==='detail')this.watch();
      this.host.querySelector('.ad-detail').hidden=a!=='detail';this.host.querySelector('.ad-terminal').hidden=a!=='terminal';
      this.host.querySelectorAll('.ad-tabs button').forEach(x=>{x.classList.toggle('on',x.dataset.ad===a);x.setAttribute('aria-selected',String(x.dataset.ad===a));});
      if(a==='terminal')this.attach();else this.detail();
    }
    if(a==='input'&&this.windowId){this.input=!this.input;this.sendSelection(true);}
  };
  Panel.prototype.setTask=function(key){if(key!==this.task){this.watch();this.task=key;this.windowId='';this.windowOwner=null;this.windowWasMatched=false;this.pendingSelect=null;this.sendSelection();this.detailSignature='';this.detailMarkup='';this.detailRenderedKey='';this.epoch++;}};
  Panel.prototype.detail=async function(){
    const key=this.task;if(!key)return;const item=(this.ctx.board.items||[]).find(t=>t.key===key),sig=JSON.stringify([item,this.detailRefresh,this.h.lang()]);
    if(sig===this.detailSignature)return;this.detailSignature=sig;const epoch=++this.epoch;
    const box=this.host.querySelector('.ad-detail');if(this.detailRenderedKey!==key)box.innerHTML='<p class="hint">'+this.label('读取任务详情','Reading task details')+'</p>';
    try{const sp=key.lastIndexOf(' '),d=await this.h.api('GET','api/board/item?goal='+encodeURIComponent(key.slice(0,sp))+'&sub='+encodeURIComponent(key.slice(sp+1)));
      if(live!==this||epoch!==this.epoch||this.task!==key)return;
      const row=(zh,en,value)=>'<dt>'+this.label(zh,en)+'</dt><dd>'+value+'</dd>';
      const markup='<h2>'+esc(d.what)+'</h2><div class="hint">'+esc(d.key)+' · '+esc(this.h.lang()==='en'?words[d.col]||d.col:d.col)+'</div><dl class="ad-properties">'
        +row('需求','Requirements',(d.needs_full||[]).map(n=>'<p>'+esc(n.scope+' '+n.code)+'<br>'+esc(n.func)+'<br>'+esc(n.effect)+'</p>').join('')||this.label('未关联需求','No linked requirement'))
        +row('怎样验收','Acceptance criteria',esc(d.how||'未记录'))+row('负责人','Owner',esc(d.who||'未领取'))
        +row('施工计划','Work plan',this.h.plan(d.execution_plan))+row('等待原因','Waiting reason',esc(d.col==='等着'?d.text:d.wait_on||'—'))
        +row('交付','Delivery',d.j?'<button class="sbtn" data-auto-go="j:'+esc(d.j)+'">'+esc(d.j+' · '+d.j_state)+'</button>':this.label('尚未交付','No delivery'))+'</dl><button class="sbtn" data-auto-go="x:'+esc(d.key)+'">'+this.label('打开完整记录','Open full record')+'</button>';
      if(markup!==this.detailMarkup || this.detailRenderedKey!==key){const scroll=this.detailRenderedKey===key?box.scrollTop:0;box.innerHTML=markup;box.scrollTop=scroll;this.detailMarkup=markup;this.detailRenderedKey=key;}
    }catch(e){if(live===this&&epoch===this.epoch){this.detailSignature='';this.detailMarkup='';this.detailRenderedKey='';box.innerHTML='<p class="warnt">'+esc(e.message)+'</p>';}}
  };
  Panel.prototype.windows=function(){
    const task=(this.ctx.board.items||[]).find(t=>t.key===this.task),all=((this.ctx.launch||{}).windows||[]).filter(w=>w.project_root===this.root),matches=eligibleWindows(this.ctx,task);
    const other=all.filter(w=>!matches.some(x=>x.id===w.id)),owner=taskOwner(this.ctx,task);
    if(this.windowId&&(!all.some(w=>w.id===this.windowId)||this.windowOwner!==owner||this.windowWasMatched&&!matches.some(w=>w.id===this.windowId))){
      this.watch();this.windowId='';this.windowOwner=null;this.windowWasMatched=false;this.pendingSelect=null;this.sendSelection();
    }
    const s=this.host.querySelector('.ad-windows'),sig=JSON.stringify([matches,other,this.windowId,this.h.lang()]),en=this.h.lang()==='en';
    if(sig!==this.windowSignature){
      this.windowSignature=sig;
      const option=(w,unmatched)=>'<option value="'+esc(w.id)+'">'+esc(w.title+(w.agent_code?' · '+w.agent_code:' · '+(en?'Unlinked employee':'未关联员工'))+(unmatched?' · '+(en?'Not linked to this task':'未关联此任务'):'')+(w.alive?'':' · '+(en?'Exited':'已退出')))+'</option>';
      const group=(rows,zh,english,unmatched)=>rows.length?'<optgroup label="'+esc(en?english:zh)+'">'+rows.map(w=>option(w,unmatched)).join('')+'</optgroup>':'';
      s.innerHTML='<option value="">'+(en?'Select an existing window':'选择已有窗口')+'</option>'+group(matches,'该任务员工的窗口','Windows for the task employee',false)+group(other,'同项目其他窗口','Other windows in this project',true);s.value=this.windowId;
    }
    this.host.querySelector('[data-ad=input]').disabled=!this.windowId || !(all.find(w=>w.id===this.windowId)||{}).alive;
    if(!this.windowId)this.status(this.label('请选择已有窗口；不会自动开工','Select an existing window; viewing does not launch work'));
  };
  Panel.prototype.status=function(text){this.host.querySelector('.ad-terminal-status').innerHTML=text;};
  Panel.prototype.attach=async function(){
    const win=((this.ctx.launch||{}).windows||[]).find(w=>w.id===this.windowId&&w.project_root===this.root);
    if(this.windowId&&!win){this.status(this.label('窗口未关联当前项目','Window is not linked to this project'));return;}
    if(this.terminalSrc){this.sendSelection();return;}
    if(this.attaching)return;this.attaching=true;const token=++this.attachEpoch;
    try{const pages=await this.h.api('GET','api/pages');if(live!==this||token!==this.attachEpoch||this.tab!=='terminal')return;
      const p=pages.find(p=>p.name==='网页终端');
      if(!p||!p.ok||!p.enabled||!p.running){this.status(esc(!p?'未安装网页终端':!p.ok?p.msg:!p.enabled?'网页终端未启用':'网页终端服务未运行'));return;}
      const u=new URL(p.url);u.searchParams.set('view','1');u.searchParams.set('layout','single');u.searchParams.set('p',location.origin);u.searchParams.set('theme',document.documentElement.dataset.theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'));
      this.terminalSrc=u.href;this.viewerReady=false;
      const iframe=document.createElement('iframe');iframe.title='命令行观看 Terminal viewer';iframe.src=u.href;iframe.allowFullscreen=true;this.host.querySelector('.ad-terminal-host').appendChild(iframe);
    }catch(e){this.status(esc(e.message));}finally{this.attaching=false;}
  };
  Panel.prototype.sendSelection=function(modeOnly){
    const f=this.host.querySelector('.ad-terminal-host iframe');if(!f||!this.viewerReady)return;
    const choice=this.windowId+'|'+(this.input?'control':'watch');
    if(!modeOnly&&choice===this.pendingSelect)return;
    this.pendingSelect=choice;const id=++this.requestId;
    f.contentWindow.postMessage({type:modeOnly?'terminal-mode':'terminal-select',windowId:this.windowId||null,mode:this.input?'control':'watch',layout:'single',requestId:id},new URL(this.terminalSrc).origin);
    f.contentWindow.postMessage({type:'theme',theme:document.documentElement.dataset.theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light')},new URL(this.terminalSrc).origin);
  };
  Panel.prototype.watch=function(){this.input=false;this.pendingSelect='';this.sendSelection(true);const b=this.host.querySelector('[data-ad=input]');if(b)b.innerHTML=this.label('接管输入','Take input control');};
  Panel.prototype.destroy=function(){this.destroyed=true;if(this.projectionFrame && global.cancelAnimationFrame)global.cancelAnimationFrame(this.projectionFrame);this.exitFullscreen();this.watch();this.epoch++;this.attachEpoch=(this.attachEpoch||0)+1;this.host.removeEventListener('click',this.click);this.host.removeEventListener('change',this.change);this.host.removeEventListener('input',this.search);this.host.removeEventListener('keydown',this.sizeKeydown);this.host.removeEventListener('research-pane-collapse',this.paneCollapse);this.host.removeEventListener('pointerdown',this.paneDown);global.removeEventListener('pointermove',this.paneMove);global.removeEventListener('pointerup',this.paneUp);global.removeEventListener('pointercancel',this.paneUp);global.removeEventListener('resize',this.paneResize);global.removeEventListener('keydown',this.keydown);global.removeEventListener('message',this.message);global.removeEventListener('research-overview-mode',this.overviewChange);document.removeEventListener('fullscreenchange',this.fullscreenChange);if(this.svg){this.svg.removeEventListener('pointerdown',this.down);this.svg.removeEventListener('pointermove',this.move);this.svg.removeEventListener('pointerup',this.up);this.svg.removeEventListener('pointercancel',this.up);this.svg.removeEventListener('wheel',this.wheel);}};
  global.AutoDashboard={update,dispose,model};
  if(typeof module==='object'&&module.exports)module.exports=model;
})(typeof window==='object'?window:globalThis);
