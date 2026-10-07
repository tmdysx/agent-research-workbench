/* 蓝图内的治理全文、关联设置及人和 agent 共用的正文编辑入口。 */
const GOV = { kind: 'all', key: '', tab: 'needs', data: null, seq: 0, editor: null, drafts: new Map() };
function govButton(file, title) { return '<button class="sbtn" data-gov-edit="' + esc(file) + '">' + esc(title || '编辑 Edit') + '</button>'; }
function govRead(file, title) { return '<button class="sbtn" data-gov-read="' + esc(file) + '">' + esc(title || file) + '</button>'; }
function govBuiltin(file){return typeof builtinFileSlot==='function'?builtinFileSlot(file):'';}
function govDoc(d, open) {
  return '<details class="gov-doc"' + (open ? ' open' : '') + '><summary>' + esc(d.title) + '</summary><div class="hint" data-nt>' + esc(d.file) + '</div>'
    + (d.file && /^(治理\/|资料\/.*(?:需求|戒律|蓝图)\.md|资料\/蓝图\/S)/.test(d.file) ? govButton(d.file) : '')
    + (!d.missing?govBuiltin(d.file):'')
    + (d.missing ? '<p class="hint">尚未记录 Not recorded</p>' : '<article class="md" data-nt>' + renderMd(d.text) + '</article>') + '</details>';
}
async function govLoad(kind, key, host) {
  if (GOV.editor) return;
  const seq = ++GOV.seq;
  if (GOV.kind !== kind || GOV.key !== key) GOV.tab = 'needs';
  GOV.kind = kind; GOV.key = key;
  const owner=document.getElementById(host);
  const projectRoot=()=>typeof S!=='undefined'&&S&&S.project?S.project.root:'';
  const root=projectRoot(),current=()=>seq===GOV.seq&&owner===document.getElementById(host)&&!GOV.editor&&root===projectRoot();
  try {
    const d = await api('GET', 'api/governance?kind=' + encodeURIComponent(kind) + '&key=' + encodeURIComponent(key));
    if (!current()) return;
    if(typeof completeReading==='function')await completeReading(owner);
    if(!current())return;
    GOV.data = d; GOV.host = host; govRender();
    if (GOV.reveal && host === 'gov-detail') {
      GOV.reveal = false;
      document.getElementById('bp-detail')?.scrollIntoView({block:'start'});
    }
  } catch (e) { if(current()&&owner)owner.textContent=e.message; }
}
function govRender() {
  const d = GOV.data, el = document.getElementById(GOV.host);
  if (!d || !el || GOV.editor) return;
  const module = d.kind === 'module' ? d.key : '', goal = d.kind === 'goal' ? d.key : '';
  let h = '<div class="gov-tabs">' + [['needs','需求与验收 Needs'],['rules','适用戒律 Rules'],['plans','任务与计划 Plans'],['records','交付与记录 Records']].map(function (t) {
    return '<button class="sbtn' + (GOV.tab === t[0] ? ' on' : '') + '" data-gov-tab="' + t[0] + '">' + t[1] + '</button>';
  }).join('') + '</div>';
  const create = function (kind) { return '<button class="sbtn" data-gov-new="' + kind + '" data-gov-module="' + esc(module) + '" data-gov-goal="' + esc(goal) + '">新建' + kind + ' New</button>'; };
  if (GOV.tab === 'needs') {
    h += '<div class="acts">' + create('需求') + '</div>';
    h += d.requirements.map(function (q) {
      return '<section class="gov-need"><h3 data-nt>' + esc(q.scope + ' ' + q.code + ' · ' + q.func) + '</h3><p data-nt>' + esc(q.effect || '缺验收标准') + '</p>'
        + '<div class="hint" data-nt>' + esc(q.state + ' · ' + (q.goals.join('、') || '未关联目标') + ' · ' + (q.modules.map(function (m) { const x = d.options.modules.find(function (x) { return x.key === m; }); return x ? x.name : m; }).join('、') || '未分配模块')) + '</div>'
        + (q.missing_modules.length ? '<p class="hint">承接模块不可用：' + esc(q.missing_modules.join('、')) + '</p>' : '')
        + (q.relation_note ? '<p class="hint" data-nt>' + esc(q.relation_note) + '</p>' : '')
        + govBuiltin(q.file) + govButton(q.file, '编辑需求 Edit') + ' <button class="sbtn" data-gov-assign="' + esc(q.key) + '">设置关联 Assign</button></section>';
    }).join('') || '<p class="hint">缺需求 No requirements</p>';
    h += d.documents.filter(function (x) { return !/\/任务\//.test(x.file); }).map(function (x) { return govDoc(x, true); }).join('');
  } else if (GOV.tab === 'rules') {
    h += create('戒律') + d.rules.map(function (x) { return govDoc(x, true); }).join('');
  } else if (GOV.tab === 'plans') {
    h += '<div class="acts">' + create('任务') + create('计划') + '</div>';
    h += d.tasks.length ? '<table><tr><th>任务 Task</th><th>做什么 Work</th><th>状态 Status</th></tr>' + d.tasks.map(function (x) { return '<tr><td data-nt>' + esc(x.goal + ' ' + x.code) + '</td><td data-nt>' + esc(x.what) + '<div class="hint">' + esc(x.how) + '</div></td><td data-nt>' + (typeof linkJ === 'function' ? linkJ(x.text) : esc(x.text)) + ' ' + govButton(x.file) + '</td></tr>'; }).join('') + '</table>' : '<p class="hint">没有任务记录 No tasks</p>';
    h += d.plans.length ? d.plans.map(function (x) { return '<div class="bp-plan"><span data-nt>' + esc(x.date + ' · ' + x.goal + ' · ' + x.code) + '</span> ' + govRead(x.path, x.title) + ' ' + govButton(x.path) + '</div>'; }).join('') : '<p class="hint">没有明确关联的计划 No linked plans</p>';
    h += d.documents.filter(function (x) { return /\/任务\//.test(x.file); }).map(function (x) { return govDoc(x, true); }).join('');
  } else {
    h += '<h3>交付 Deliveries</h3>' + (d.deliveries.map(function (x) { return govRead('自动化/交付/' + x.file, x.code + ' · ' + x.state); }).join(' ') || '<p class="hint">没有关联交付 No deliveries</p>');
    h += '<h3>开工单 Work orders</h3>' + (d.workorders.map(function (x) { return '<a href="#/auto?k=' + encodeURIComponent(x.code) + '">' + esc(x.code + ' · ' + x.name + ' · ' + x.stored) + '</a>'; }).join(' · ') || '<p class="hint">没有关联开工单 No work orders</p>');
    h += '<h3>日志 Log</h3>' + (d.logs.map(function (x) { return '<p data-nt><b>' + esc(x.id + ' · ' + x.at + ' · ' + x.by) + '</b><br>' + esc(x.body) + '</p>'; }).join('') || '<p class="hint">没有明确关联的日志 No linked log</p>');
    h += '<h3>材料 Materials</h3>' + d.materials.map(function (x) { return govRead(x.file, x.name); }).join(' ');
  }
  el.innerHTML = (d.problems.length ? '<div class="warnbar">' + d.problems.map(esc).join('<br>') + '</div>' : '') + h + '<div id="gov-reading"></div>';
}
function govEditor(d) {
  if (GOV.editor) return;
  GOV.editor = d;
  let box = document.getElementById('gov-editor');
  if (!box) { box = document.createElement('dialog'); box.id = 'gov-editor'; document.body.appendChild(box); }
  box.innerHTML = '<div class="gov-editor-head"><h2>编辑正文 Edit</h2>'+(!d.missing?govBuiltin(d.save_path||d.file):'')+'<button class="sbtn" data-gov-close>关闭 Close</button></div><div class="hint" data-nt>' + esc(d.save_path || d.file) + '</div>'
    + '<textarea id="gov-text" aria-label="治理正文" spellcheck="false"></textarea><div class="acts"><button class="btn" data-gov-save>保存 Save</button><span id="gov-save-state"></span></div><div id="gov-conflict"></div>';
  const input = document.getElementById('gov-text'), cached = GOV.drafts.get(d.save_path || d.file);
  input.value = cached === undefined ? d.text : cached.text; input.defaultValue = d.text;
  if (cached) d.revision = cached.revision;
  input.oninput = function () { GOV.drafts.set(d.save_path || d.file, {text:input.value, revision:d.revision}); };
  box.oncancel = function (e) { e.preventDefault(); govClose(); };
  box.showModal(); input.focus();
}
function govClose() {
  const box = document.getElementById('gov-editor');
  if (!GOV.editor) return;
  const ta = document.getElementById('gov-text');
  if (ta && ta.value !== ta.defaultValue) GOV.drafts.set(GOV.editor.save_path || GOV.editor.file, {text:ta.value, revision:GOV.editor.revision});
  GOV.editor = null; box.close();
  if (cur === '蓝图' && MV.sel === PANORAMA) showPanorama();
  else if (GOV.host && document.getElementById(GOV.host)) govLoad(GOV.kind, GOV.key, GOV.host);
  else refreshView();
}
if (typeof document !== 'undefined') document.addEventListener('click', async function (e) {
  const b = e.target.closest('[data-gov-edit],[data-gov-read],[data-gov-new],[data-gov-tab],[data-gov-save],[data-gov-close],[data-gov-assign],[data-gov-linksave],[data-gov-rebase]');
  if (!b) return;
  try {
    if (b.hasAttribute('data-gov-tab')) { GOV.tab = b.dataset.govTab; govRender(); }
    else if (b.hasAttribute('data-gov-edit')) govEditor(await api('GET', 'api/governance/document?path=' + encodeURIComponent(b.dataset.govEdit)));
    else if (b.hasAttribute('data-gov-new')) govEditor(await api('GET', 'api/governance/draft?kind=' + encodeURIComponent(b.dataset.govNew) + '&module=' + encodeURIComponent(b.dataset.govModule || '') + '&goal=' + encodeURIComponent(b.dataset.govGoal || '')));
    else if (b.hasAttribute('data-gov-close')) govClose();
    else if (b.hasAttribute('data-gov-save')) {
      const d = GOV.editor, ta = document.getElementById('gov-text'), state = document.getElementById('gov-save-state');
      b.disabled = true;
      try {
        const updated = await api('PUT', 'api/governance/document', {path: d.save_path || d.file, text: ta.value, revision: d.revision});
        GOV.editor = updated; ta.defaultValue = ta.value; GOV.drafts.delete(d.save_path || d.file);
        state.textContent = '已保存 Saved'; document.getElementById('gov-conflict').innerHTML = ''; await load();
      } catch (err) {
        state.textContent = err.message;
        if (err.status === 409) {
          const latest = await api('GET', 'api/governance/document?path=' + encodeURIComponent(d.save_path || d.file));
          GOV.latest = latest;
          document.getElementById('gov-conflict').innerHTML = '<button class="sbtn" data-gov-rebase>已对照合并，更新保存基准 Merged</button><details open><summary>另一方的最新版本 Latest version</summary><pre data-nt>' + esc(latest.text) + '</pre></details>';
        }
      } finally { b.disabled = false; }
    } else if (b.hasAttribute('data-gov-rebase')) {
      GOV.editor.revision = GOV.latest.revision;
      GOV.drafts.set(GOV.editor.save_path || GOV.editor.file, {text:document.getElementById('gov-text').value, revision:GOV.latest.revision});
      document.getElementById('gov-save-state').textContent = '已更新版本，请保存 Ready to save';
    } else if (b.hasAttribute('data-gov-read')) {
      const r = await api('GET', 'api/project/preview?path=' + encodeURIComponent(b.dataset.govRead));
      const host = document.getElementById('gov-reading');
      if (host) { host.innerHTML = '<h3 data-nt>' + esc(r.name) + '</h3>'+govBuiltin(r.builtin_action&&r.builtin_action.path||b.dataset.govRead) + (r.text !== undefined ? '<article class="md" data-nt>' + renderMd(r.text) + '</article>' : '<iframe title="材料预览" style="width:100%;height:60vh;border:0" src="pfiles/' + b.dataset.govRead.split('/').map(encodeURIComponent).join('/') + '"></iframe>'); host.scrollIntoView({block:'start'}); }
    } else if (b.hasAttribute('data-gov-assign')) {
      const q = GOV.data.requirements.find(function (q) { return q.key === b.dataset.govAssign; });
      const select = function (items, checked, name) { return items.map(function (x) { return '<label><input type="checkbox" name="' + name + '" value="' + esc(x.key) + '"' + (checked.includes(x.key) ? ' checked' : '') + '> ' + esc(x.name) + '</label>'; }).join(''); };
      const host = document.getElementById('gov-reading');
      host.innerHTML = '<form id="gov-links"><h3>关联目标 Goals</h3><div class="gov-choices">' + select(GOV.data.options.goals, q.goals, 'goals') + '</div><h3>承接模块 Modules</h3><div class="gov-choices">' + select(GOV.data.options.modules, q.modules, 'modules') + '</div><button type="button" class="btn" data-gov-linksave="' + esc(q.key) + '">保存关联 Save</button></form>'; host.scrollIntoView({block:'start'});
    } else if (b.hasAttribute('data-gov-linksave')) {
      const data = new FormData(document.getElementById('gov-links'));
      await api('POST', 'api/governance/assign', {key:b.dataset.govLinksave, revision:GOV.data.requirements.find(function (q) { return q.key === b.dataset.govLinksave; }).revision, goals:data.getAll('goals'), modules:data.getAll('modules')});
      await load(); govLoad(GOV.kind, GOV.key, GOV.host);
    }
  } catch (err) { toast(err.message); }
});
if (typeof window !== 'undefined') window.addEventListener('beforeunload', function (e) {
  if (GOV.drafts.size) { e.preventDefault(); e.returnValue = ''; }
});

/* 二维总览只投影已有 JSON 的包含、明确关联和来源，不扫描正文补关系。 */
const GovMap = (function () {
  'use strict';
  const arr = x => Array.isArray(x) ? x : [];
  const str = x => x == null ? '' : String(x);
  const path = x => str(x).replace(/\\/g, '/');
  const escape = x => str(x).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const id = (kind, key, file) => JSON.stringify([kind, str(key), path(file)]);
  const kinds = {project:['项目','Project'],goal:['目标','Goal'],task:['任务','Task'],requirement:['需求','Requirement'],module:['模块','Module'],group:['分组','Group'],directory:['文件夹','Folder'],file:['文件','File'],checkpoint:['存档','Checkpoint'],now:['现在','Now'],branch:['工作树','Branch'],fruit:['果实','Fruit'],entry:['记录','Record']};
  const edgeNames = {contains:['包含','Contains'],linked:['关联','Linked'],source:['来源','Source'],previous:['上一时间档','Previous temporal checkpoint']};
  const countNames = {ideas:['想法','Ideas'],needs:['需求','Requirements'],items:['任务','Tasks'],deliveries:['交付','Deliveries'],logs:['日志','Logs'],decisions:['决定','Decisions']};
  const recordText = value => value==null?'':typeof value==='object'?JSON.stringify(value):str(value);
  function build(kind, data, options) {
    data = data || {}; options = options || {};
    kind = ['rules','archives','module','index'].includes(kind) ? kind : 'blueprint';
    const nodes = [], edges = [], index = new Map(), seenEdges = new Set();
    const warnings = arr(data.problems).map(str), root = path(options.projectRoot);
    const add = n => { if (!index.has(n.id)) { n.order = nodes.length; nodes.push(n); index.set(n.id,n); } return index.get(n.id); };
    const edge = (from, to, type, detail) => {
      if (!from || !to || from === to || !index.has(from) || !index.has(to)) return;
      const key = JSON.stringify([from,to,type,str(detail)]);
      if (!seenEdges.has(key)) { seenEdges.add(key); edges.push({from,to,type,detail:str(detail)}); }
    };
    const project = add({id:id('project',root),kind:'project',key:root,title:str(options.projectName||options.name)||'项目 Project',depth:0,details:[]});
    const sourceFile = file => {
      file = path(file); if (!file) return null;
      return add({id:id('file',file),kind:'file',key:file,title:file.split('/').pop(),file,depth:2,details:[],preview:{mode:'project',path:file}});
    };
    const source = (n, file, field) => { const f = sourceFile(file); if (f) edge(n.id,f.id,'source',field); };
    if (kind === 'archives') {
      const checkpoints=new Map(),branches=[],saves=arr(data.saves);
      arr(data.timeline&&data.timeline.nodes).slice().reverse().forEach(row=>{
        const code=str(row.code),meta=saves.find(s=>str(s.code)===code)||{},isNow=code==='现在';
        if(!code)return;
        const n=add({id:id(isNow?'now':'checkpoint',code,root),kind:isNow?'now':'checkpoint',key:code,title:code+' · '+str(row.name||meta.name),depth:1,status:str(row.grade||meta.grade),
          source:'api/timeline/'+encodeURIComponent(code),record:{kind:isNow?'now':'checkpoint',code,record:row,metadata:meta},preview:{mode:'timeline',code},mergeNotes:[],
          details:[{label:['时间','Time'],value:str(row.at||meta.at)},{label:['记录者','Recorded by'],value:str(row.by||meta.by)},
            {label:['上一时间档','Previous temporal checkpoint'],value:str(row.prev)},{label:['时间范围','Time interval'],value:str(row.since)},
            {label:['安全点定性','Settled safety point'],value:row.settled===true?'是 Yes':row.settled===false?'否 No':''},
            {label:['存档方式','Save mode'],value:str(meta.mode)},{label:['检查','Checks'],value:recordText(meta.checks)},
            {label:['来源','Source'],value:root+' · api/timeline/'+code}]});
        checkpoints.set(code,n);edge(project.id,n.id,'contains');
      });
      checkpoints.forEach(n=>{
        const prev=str(n.record.record.prev);if(!prev)return;
        const target=checkpoints.get(prev);if(target)edge(target.id,n.id,'previous','仅时间顺序 Temporal order only');
        else warnings.push(n.key+' · 上一时间档缺失 Previous temporal checkpoint missing: '+prev);
      });
      arr(data.world&&data.world.branches).forEach((row,i)=>{
        const code=str(row.code),source=path(row.path)||root+'::branch-record:'+i;
        const n=add({id:id('branch',code||'unrecorded:'+i,source),kind:'branch',key:code,title:(code||'编号未记录 ID unrecorded')+' · '+str(row.name),depth:2,status:str(row.state),missing:row.exists===false,
          source,record:{kind:'branch',code,branch:code,record:row},details:[{label:['用途','Purpose'],value:str(row.why)},{label:['来源档','Source checkpoint'],value:str(row.base)||'未记录 Unrecorded'},
            {label:['项目路径','Project path'],value:path(row.path)||'未记录 Unrecorded'},{label:['时间','Time'],value:str(row.at)},
            {label:['果实','Fruit'],value:str(row.fruit_checkpoint)||'编号未记录 ID unrecorded'},{label:['Demo','Demo'],value:str(row.demo)},
            {label:['检查','Checks'],value:recordText(row.checks)},{label:['负责','Assigned'],value:recordText(row.held)},
            {label:['合回存档','Merged checkpoint'],value:str(row.merged&&row.merged.after)},{label:['合并记录','Merge record'],value:recordText(row.merged)}]});
        branches.push(n);edge(project.id,n.id,'contains');
        const base=checkpoints.get(str(row.base));if(base)edge(base.id,n.id,'source','明确来源档 Explicit base checkpoint');
        else warnings.push(n.title+' · 来源档'+(row.base?'缺失 Source checkpoint missing: '+str(row.base):'未记录 Source checkpoint unrecorded'));
        if(row.fruit_checkpoint||row.demo){
          const fruit=str(row.fruit_checkpoint),f=add({id:id('fruit',code+'::'+(fruit||'unrecorded'),source),kind:'fruit',key:code+' / '+fruit,title:(code||'编号未记录 ID unrecorded')+' / '+(fruit||'果实编号未记录 Fruit ID unrecorded'),depth:3,
            source,status:str(row.state),record:{kind:'fruit',code:fruit,branch:code,record:row},details:[{label:['枝内存档','Branch-local checkpoint'],value:fruit||'编号未记录 ID unrecorded'},
              {label:['所属工作树','Branch'],value:code||'编号未记录 ID unrecorded'},{label:['项目路径','Project path'],value:path(row.path)||'未记录 Unrecorded'},
              {label:['Demo','Demo'],value:str(row.demo)},{label:['果实时间','Fruit time'],value:str(row.fruit_at)},{label:['记录者','Recorded by'],value:str(row.fruit_by)},
              {label:['检查','Checks'],value:recordText(row.checks)}]});
          edge(n.id,f.id,'contains','枝自己的果实 Branch-local fruit');
        }
      });
      branches.forEach(n=>{
        const row=n.record.record;if(!row.merged)return;
        const after=str(row.merged.after),target=checkpoints.get(after),note={branch:n.key||'编号未记录 ID unrecorded',fruit:str(row.fruit_checkpoint)||'果实编号未记录 Fruit ID unrecorded',demo:str(row.demo),source:n.source};
        // 合并只在目标档写注记；禁止以合并为由画合回连线。
        if(target){target.mergeNotes.push(note);target.details.push({label:['合并了','Merged'],value:note.branch+' / '+note.fruit+(note.demo?' · '+note.demo:'')});}
        else warnings.push(n.title+' · '+(after?'合回档缺失 Merged checkpoint missing: '+after:'合回档未记录 Merged checkpoint unrecorded'));
      });
      if(!checkpoints.size)warnings.push('没有时间档记录 No timeline checkpoints');
    } else if (kind === 'index') {
      arr(data.items).forEach((row,i)=>{
        const target=row.record&&typeof row.record==='object'&&!Array.isArray(row.record)&&Object.keys(row.record).length?row.record:null,key=str(row.id||(target&&(target.view||target.key)?str(target.view)+'::'+str(target.key):'entry:'+i)),source=path(row.file)||root+'::'+str(options.module||target&&target.view)+'::'+JSON.stringify(target||{entry:i});
        const n=add({id:id('entry',key,source),kind:'entry',key,title:str(row.label||row.id),depth:1,source,
          record:{kind:'index',...target,record:target},details:[{label:['摘要','Summary'],value:str(row.summary)}]});edge(project.id,n.id,'contains');
      });
      if(!arr(data.items).length)warnings.push('没有记录 No records');
    } else if (kind === 'rules'||kind === 'module') {
      const module = str(options.module || data.module || '戒律');
      const sections = arr(data.sections);
      const visit = (item, parent, depth, ordinal) => {
        if (!item || item.virtual) return;
        const raw = path(item.path), identity = raw || 'entry:' + ordinal;
        const canonical = path(item.file || item.real_path || (raw.startsWith('@/') ? raw.slice(2) : ''));
        const isDir = item.dir === true;
        const key = canonical ? id(isDir?'directory':'file',canonical) : id(isDir?'directory':'file',module,identity);
        const n = add({id:key,kind:isDir?'directory':'file',key:identity,title:str(item.label || item.name || raw),file:canonical,
          depth,missing:item.missing===true,details:[{label:['路径','Path'],value:raw},{label:['记录','Record'],value:str(item.note)}],
          preview:!isDir && raw ? {mode:'module',module,path:raw} : null});
        edge(parent.id,n.id,'contains');
        arr(item.children).forEach((child,i) => visit(child,n,depth+1,ordinal+'.'+i));
      };
      if (sections.length) sections.forEach((section,i) => {
        const n = add({id:id('group',str(section.title),String(i)),kind:'group',key:String(i),title:str(section.title),depth:1,
          missing:!arr(section.items).length,details:[]});
        edge(project.id,n.id,'contains');
        arr(section.items).forEach((item,j) => visit(item,n,2,i+'.'+j));
      });
      else arr(data.items).forEach((item,i) => visit(item,project,1,String(i)));
      if (!nodes.some(n=>n.kind==='file')) warnings.push(kind==='rules'?'没有可读取的戒律文件 No rule files':'没有可读取文件 No readable files');
      if (data.truncated) warnings.push('目录已截断，图中仅显示已读取文件 Directory listing is truncated');
    } else {
      const goals = new Map(), modules = new Map(), requirements = new Map(), tasks = new Map();
      const task = (row, owner, file) => {
        const goal = str(row.goal || owner), code = str(row.code || row.sub), full = str(row.key || goal+'::'+code);
        const n = add({id:id('task',full,file),kind:'task',key:full,title:goal+' '+code+' · '+str(row.what),file:path(file),depth:1,
          status:str(row.text || row.state),details:[{label:['怎么验','Check'],value:str(row.how)}]});
        tasks.set(full+'\n'+path(file),n); source(n,file,'任务原文 Task record'); return n;
      };
      [data.s0].concat(arr(data.goals)).filter(Boolean).forEach(g => {
        const code = str(g.code), n = add({id:id('goal',code,g.file),kind:'goal',key:code,title:code+' · '+str(g.name),file:path(g.file),depth:0,
          details:[{label:['目标','Purpose'],value:str(g.one_line)}]});
        goals.set(code,n); edge(project.id,n.id,'contains'); source(n,g.file,'目标原文 Goal record');
        arr(g.subs).forEach(row => edge(n.id,task(row,code,row.file||g.file).id,'contains'));
      });
      arr(data.modules).forEach(m => {
        const key = str(m.key), n = add({id:id('module',key),kind:'module',key,title:str(m.name||key),depth:1,
          missing:m.kind==='unavailable',status:arr(m.missing).join(' · '),details:[]});
        modules.set(key,n); edge(project.id,n.id,'contains');
        arr(m.blueprint_files).forEach(f=>source(n,f,'模块蓝图 Module blueprint'));
        if (m.need && m.need.file) source(n,m.need.file,'需求原文 Requirement record');
        const rows = arr(m.tasks).length ? arr(m.tasks) : arr(m.blueprint && m.blueprint.subs);
        rows.forEach(row=>edge(n.id,task(row,str(row.goal||key),row.file||(m.blueprint||{}).file).id,'contains'));
      });
      arr(data.requirements).forEach(q => {
        const key = str(q.key || path(q.file)+'::'+str(q.scope)+'::'+str(q.code));
        const n = add({id:id('requirement',key,q.file),kind:'requirement',key,title:str(q.scope)+' '+str(q.code)+' · '+str(q.func),file:path(q.file),depth:1,
          status:str(q.state),details:[{label:['验收','Acceptance'],value:str(q.effect)},{label:['来自','From'],value:str(q.source)},
            {label:['待确认','Unconfirmed'],value:str(q.relation_note)},
            {label:['关联目标','Goals'],value:arr(q.goals).join('、')||'未关联目标 Unlinked'},
            {label:['承接模块','Modules'],value:arr(q.modules).join('、')||'未分配模块 Unassigned'}]});
        requirements.set(key,n); edge(project.id,n.id,'contains'); source(n,q.file,'需求原文 Requirement record');
        arr(q.goals).forEach(key=>{
          const target = goals.get(str(key)); if (target) edge(target.id,n.id,'linked','关联目标 Goals');
          else warnings.push(n.title+' · 找不到目标 Missing goal: '+str(key));
        });
        arr(q.modules).forEach(key=>{
          const target = modules.get(str(key)); if (target) edge(n.id,target.id,'linked','承接模块 Modules');
          else if (arr(q.missing_modules).includes(key)) warnings.push(n.title+' · 承接模块不可用 Module unavailable: '+str(key));
        });
        arr(q.tasks).forEach(row=>{
          const file = path(row.file), full = str(row.key || str(row.goal)+'::'+str(row.code));
          const target = tasks.get(full+'\n'+file) || task(row,row.goal,file);
          edge(n.id,target.id,'linked','需求关联任务 Requirement task');
        });
      });
      // 后台的模块 requirements 列表能明确区分通用入口和同名 DIY 目录。
      arr(data.modules).forEach(m=>arr(m.requirements).forEach(q=>{
        const target = requirements.get(str(q.key)), owner = modules.get(str(m.key));
        if (target && owner) edge(target.id,owner.id,'linked','承接模块 Modules');
      }));
      arr(data.relations).forEach(r=>{
        const goal = goals.get(str(r.goal)), module = modules.get(str(r.module));
        if (!goal || !module) { warnings.push('关联端点不存在 Missing relation endpoint: '+str(r.goal)+' / '+str(r.module)); return; }
        edge(goal.id,module.id,'linked','明确记录 Explicit record');
        arr(r.sources).forEach(s=>{source(goal,s.file,s.field);source(module,s.file,s.field);});
      });
      if (!goals.size) warnings.push('没有目标记录 No goals');
    }
    return {kind,projectRoot:root,scope:str(options.module),nodes,edges,warnings:[...new Set(warnings)]};
  }
  function visible(model, options) {
    options=options||{}; const limit=Math.max(8,Number(options.limit)||8), query=str(options.query).trim().toLocaleLowerCase();
    const byId=new Map(model.nodes.map(n=>[n.id,n])), rank={project:0,goal:1,group:1,directory:2,module:2,requirement:3,task:4,file:5};
    let candidates;
    if (query) candidates=model.nodes.filter(n=>[n.title,n.key,n.file,n.status,...arr(n.details).map(d=>d.value)].join(' ').toLocaleLowerCase().includes(query));
    else if (options.focus && byId.has(options.focus)) {
      const linked = new Set([options.focus]);
      model.edges.forEach(e=>{if(e.from===options.focus)linked.add(e.to);if(e.to===options.focus)linked.add(e.from);});
      candidates=model.nodes.filter(n=>linked.has(n.id) && n.kind!=='file').sort((a,b)=>{
        if(a.id===options.focus)return -1;if(b.id===options.focus)return 1;
        const focusRank={task:0,requirement:1,module:2,directory:2,group:3,goal:3,project:4};
        return (focusRank[a.kind]??5)-(focusRank[b.kind]??5)||a.order-b.order;
      });
      if (model.kind==='rules'||model.kind==='module') candidates=model.nodes.filter(n=>linked.has(n.id));
    } else candidates=model.nodes.filter(n=>['rules','module'].includes(model.kind)||n.kind!=='file').sort((a,b)=>(rank[a.kind]??9)-(rank[b.kind]??9)||a.order-b.order);
    const picked=candidates.slice(0,limit), ids=new Set(picked.map(n=>n.id)),scope=new Set(candidates.map(n=>n.id));
    const sourceIds=new Set(),scopeFiles=new Set();
    model.edges.forEach(e=>{if(byId.get(e.to).kind==='file'){if(ids.has(e.from))sourceIds.add(e.to);if(scope.has(e.from))scopeFiles.add(e.to);}});
    const files=model.nodes.filter(n=>n.kind==='file'&&!ids.has(n.id)&&sourceIds.has(n.id));
    files.slice(0,limit).forEach(n=>{picked.push(n);ids.add(n.id);});
    return {nodes:picked,edges:model.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)),more:candidates.length>limit||files.length>limit,
      shown:picked.length,total:new Set([...scope,...scopeFiles]).size};
  }
  // 多个真实父边只择一条用于摆放；其余真实关系仍保留，不新增“树祖先”。
  function mindParents(model) {
    const byId=new Map(model.nodes.map(n=>[n.id,n])),parents=new Map(),project=model.nodes.find(n=>n.kind==='project');
    const rank=e=>e.type==='contains'&&e.from!==project?.id?0:e.type==='source'?1:e.type==='contains'?2:3;
    for(const n of model.nodes){
      if(n.kind==='project')continue;
      const candidates=model.edges.filter(e=>e.to===n.id&&e.type!=='previous'&&byId.has(e.from)).sort((a,b)=>rank(a)-rank(b));
      for(const e of candidates){
        let p=e.from,cycle=p===n.id;const visited=new Set();
        while(!cycle&&parents.has(p)&&!visited.has(p)){visited.add(p);p=parents.get(p).from;cycle=p===n.id;}
        if(!cycle){parents.set(n.id,e);break;}
      }
    }
    return parents;
  }
  function mindVisible(model, options) {
    options=options||{};const root=model.nodes.find(n=>n.kind==='project'),limit=Math.max(8,Number(options.limit)||8),query=str(options.query).trim().toLocaleLowerCase();
    const byId=new Map(model.nodes.map(n=>[n.id,n])),parents=mindParents(model),children=new Map(model.nodes.map(n=>[n.id,[]]));
    parents.forEach((edge,key)=>children.get(edge.from)?.push(key));
    const expanded=options.expanded instanceof Set?options.expanded:new Set(root?[root.id]:[]),ids=new Set(root?[root.id]:[]);let more=false,total=model.nodes.length;
    function ancestors(key){const seen=new Set();while(byId.has(key)&&!seen.has(key)){seen.add(key);ids.add(key);key=parents.get(key)?.from;}}
    if(options.selected&&!query)ancestors(options.selected);
    if(query){
      const matches=model.nodes.filter(n=>[n.title,n.key,n.file,n.source,n.status,...arr(n.details).map(d=>d.value)].join(' ').toLocaleLowerCase().includes(query));
      matches.slice(0,limit).forEach(n=>ancestors(n.id));more=matches.length>limit;
      const all=new Set(ids);for(const n of matches){let k=n.id;const seen=new Set();while(byId.has(k)&&!seen.has(k)){seen.add(k);all.add(k);k=parents.get(k)?.from;}}total=all.size;
      if(!matches.length)ids.clear();
    }else{
      const processed=new Set();
      while(true){
        const pending=[...ids].filter(key=>expanded.has(key)&&!processed.has(key));if(!pending.length)break;
        for(const key of pending){
          processed.add(key);const owned=children.get(key)||[];if(owned.length>limit)more=true;owned.slice(0,limit).forEach(ancestors);
          if(key===root?.id)continue;
          const neighbors=[...new Set(model.edges.filter(e=>e.from===key&&e.type!=='previous'||e.to===key&&e.type==='linked').map(e=>e.from===key?e.to:e.from))];
          if(neighbors.length>limit)more=true;neighbors.slice(0,limit).forEach(ancestors);
        }
      }
    }
    const nodes=model.nodes.filter(n=>ids.has(n.id));return {nodes,edges:model.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)),more,shown:nodes.length,total,parents,children};
  }
  function worldVisible(model,options){
    options=options||{};const limit=Math.max(8,Number(options.limit)||8),query=str(options.query).trim().toLocaleLowerCase(),root=model.nodes.find(n=>n.kind==='project'),ids=new Set(root?[root.id]:[]),parents=mindParents(model);
    const add=key=>{const seen=new Set();while(key&&!seen.has(key)){seen.add(key);ids.add(key);key=parents.get(key)?.from;}};
    if(options.selected&&!query)add(options.selected);
    let more=false;
    if(query){const matches=model.nodes.filter(n=>[n.title,n.key,n.source,n.status,...arr(n.details).map(d=>d.value)].join(' ').toLocaleLowerCase().includes(query));matches.slice(0,limit).forEach(n=>add(n.id));more=matches.length>limit;if(!matches.length)ids.clear();}
    else{
      const main=model.nodes.filter(n=>['checkpoint','now'].includes(n.kind));main.slice(0,limit).forEach(n=>add(n.id));more=main.length>limit;
      const branches=model.nodes.filter(n=>n.kind==='branch'&&(ids.has(parents.get(n.id)?.from)||parents.get(n.id)?.from===root?.id));
      branches.slice(0,limit).forEach(n=>{add(n.id);model.edges.filter(e=>e.from===n.id&&e.type==='contains').forEach(e=>add(e.to));});more=more||branches.length>limit;
    }
    const nodes=model.nodes.filter(n=>ids.has(n.id));return {nodes,edges:model.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)),more,shown:nodes.length,total:model.nodes.length};
  }
  const stableHash=value=>Array.from(str(value)).reduce((h,c)=>(Math.imul(h,31)+c.codePointAt(0))>>>0,0);
  // 竖干表示已记录时间顺序；枝只能从明确 base 生出，枝果实不共用主干编号。
  // 排完整模型的真实时间序位，再选可见实体；中轴不是工作树祖先关系。
  function worldLayout(model,nodes){
    const all=arr(model.nodes),known=new Set(nodes.map(n=>n.id)),positions=new Map(),full=new Map(),curves=[],orphans=[];
    const main=all.filter(n=>['checkpoint','now'].includes(n.kind)),mainIndex=new Map(main.map((n,i)=>[n.id,i]));
    const branches=all.filter(n=>n.kind==='branch'),events=main.map(()=>[]),radius=40,nodeRadius=7,step=64,labelWidth=120,padding=40;
    const row=n=>n.record&&n.record.record||{},time=n=>str(n.kind==='fruit'?row(n).fruit_at:row(n).at||n.record&&n.record.metadata&&n.record.metadata.at);
    const stamp=value=>/^\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+-]+(?:Z|[+-][0-9:]+)?)?$/.test(str(value))?Date.parse(str(value).replace(' ','T')):NaN;
    const mainTime=main.map(n=>stamp(time(n))),attached=[],unlinked=[];
    function gapAt(at,baseIndex){
      let gap=baseIndex;
      if(Number.isFinite(at))while(gap>0&&Number.isFinite(mainTime[gap-1])&&at>=mainTime[gap-1])gap--;
      return gap;
    }
    branches.forEach(n=>{
      const source=model.edges.find(e=>e.type==='source'&&e.to===n.id&&mainIndex.has(e.from));
      const fruits=model.edges.filter(e=>e.type==='contains'&&e.from===n.id).map(e=>all.find(x=>x.id===e.to)).filter(n=>n&&n.kind==='fruit');
      if(!source){unlinked.push(n,...fruits);return;}
      const baseIndex=mainIndex.get(source.from),baseAt=mainTime[baseIndex],at=stamp(time(n)),invalid=Number.isFinite(at)&&Number.isFinite(baseAt)&&at<baseAt;
      const gap=invalid?baseIndex:gapAt(at,baseIndex),entry={node:n,source,fruits,baseIndex,gap,time:time(n),at:invalid?NaN:at,timeStatus:invalid?'before-source':Number.isFinite(at)?'recorded':'unrecorded'};
      attached.push(entry);events[gap].push(entry);
      fruits.forEach(f=>{
        const fruitAt=stamp(time(f)),invalidFruit=Number.isFinite(fruitAt)&&((Number.isFinite(baseAt)&&fruitAt<baseAt)||(Number.isFinite(at)&&fruitAt<at));
        const fruitGap=invalidFruit?gap:Math.min(gap,gapAt(fruitAt,baseIndex));
        events[fruitGap].push({node:f,owner:n.id,time:time(f),at:invalidFruit?NaN:fruitAt,timeStatus:invalidFruit?'before-source':Number.isFinite(fruitAt)?'recorded':'unrecorded'});
      });
    });
    // 完整模型负责真实时间/身份；列只按当前可见枝的稳定顺序分配。
    const displayed=attached.filter(e=>known.has(e.node.id)||e.fruits.some(f=>known.has(f.id)));
    const left=Math.ceil(displayed.length/2),right=Math.floor(displayed.length/2),lane=140;
    const center=Math.max(320,padding+80+left*lane),width=Math.max(640,center+Math.max(200,right*lane+120)+padding);
    attached.forEach(entry=>{entry.side=1;entry.x=center;});
    displayed.forEach((entry,i)=>{entry.side=i%2?1:-1;entry.x=center+entry.side*(Math.floor(i/2)+1)*lane;});
    let y=40;
    main.forEach((n,i)=>{
      const group=events[i];
      group.sort((a,b)=>Number.isFinite(a.at)!==Number.isFinite(b.at)?(Number.isFinite(a.at)?-1:1):Number.isFinite(a.at)?b.at-a.at||a.node.order-b.node.order:a.node.order-b.node.order);
      // 缺时间不编日期；只按明确 contains 保证果实在自己枝的端部之上。
      group.filter(e=>e.owner).forEach(f=>{const child=group.indexOf(f),parent=group.findIndex(e=>e.node.id===f.owner);if(parent>=0&&child>parent){group.splice(child,1);group.splice(parent,0,f);}});
      group.forEach(event=>{
        const owner=attached.find(e=>e.node.id===(event.owner||event.node.id));
        full.set(event.node.id,{x:owner.x,y,z:0,side:owner.side,time:event.time,timeStatus:event.timeStatus});y+=step;
      });
      full.set(n.id,{x:center,y,z:0,side:1,time:time(n),timeStatus:Number.isFinite(mainTime[i])?'recorded':'unrecorded'});
      y+=Math.max(64,36+arr(n.mergeNotes).length*16);
    });
    const root=all.find(n=>n.kind==='project'),rootY=y+64;
    if(root)full.set(root.id,{x:center,y:rootY,z:0});
    const placed=new Set(unlinked.map(n=>n.id));all.filter(n=>n.kind==='fruit'&&!full.has(n.id)&&!placed.has(n.id)).forEach(n=>unlinked.push(n));
    const orphanTop=rootY+112;
    unlinked.forEach((n,i)=>{full.set(n.id,{x:padding+24,y:orphanTop+i*100,z:0,side:1,orphan:true,time:time(n),timeStatus:'unlinked'});if(known.has(n.id))orphans.push(n.id);});
    // 不让未显示的155档或完整模型底座撑满画布；同一visible集合布局幂等。
    const ordered=nodes.filter(n=>full.has(n.id)&&!full.get(n.id).orphan).slice().sort((a,b)=>full.get(a.id).y-full.get(b.id).y||a.order-b.order);
    const shownMain=ordered.filter(n=>['checkpoint','now'].includes(n.kind));
    let compactY=40;
    shownMain.forEach(n=>{full.get(n.id).y=compactY;compactY+=Math.max(64,36+arr(n.mergeNotes).length*16);});
    const timedMain=shownMain.filter(n=>Number.isFinite(stamp(time(n))));
    const eventY=(at,fallback)=>{
      if(!Number.isFinite(at)||!timedMain.length)return fallback;
      for(let i=0;i<timedMain.length-1;i++){
        const a=timedMain[i],b=timedMain[i+1],ta=stamp(time(a)),tb=stamp(time(b));
        if(at<=ta&&at>=tb&&ta>tb)return full.get(a.id).y+(ta-at)/(ta-tb)*(full.get(b.id).y-full.get(a.id).y);
      }
      return at>stamp(time(timedMain[0]))?full.get(timedMain[0].id).y-40:fallback;
    };
    displayed.forEach(entry=>{
      const base=full.get(entry.source.from),fallback=known.has(entry.source.from)?base.y-40:Math.max(80,compactY);
      const p=full.get(entry.node.id);p.y=Math.max(24,Math.min(fallback,eventY(entry.at,fallback)));
      entry.fruits.forEach(f=>{const q=full.get(f.id),at=q.timeStatus==='recorded'?stamp(time(f)):NaN;q.y=Math.max(8,Math.min(p.y-18,eventY(at,p.y-18)));});
    });
    const displayedBottom=Math.max(compactY,...displayed.flatMap(e=>[full.get(e.node.id).y,...e.fruits.map(f=>full.get(f.id).y)]));
    if(root&&known.has(root.id)){full.get(root.id).y=displayedBottom;compactY=displayedBottom+32;}
    const compactOrphanTop=compactY+32;
    const shownOrphans=unlinked.filter(n=>known.has(n.id));
    shownOrphans.forEach((n,i)=>{full.get(n.id).y=compactOrphanTop+i*64;});
    attached.forEach(entry=>{
      const base=full.get(entry.source.from),p=full.get(entry.node.id),start=base.y+nodeRadius;
      if(known.has(entry.source.from)&&known.has(entry.node.id))curves.push({...entry.source,radius,
        d:'M '+base.x+' '+start+' H '+(p.x-entry.side*radius)+' A '+radius+' '+radius+' 0 0 '+(entry.side<0?1:0)+' '+p.x+' '+(start-radius)+' V '+p.y});
      entry.fruits.forEach(f=>{const fruit=full.get(f.id),edge=model.edges.find(e=>e.type==='contains'&&e.from===entry.node.id&&e.to===f.id);
        if(edge&&known.has(entry.node.id)&&known.has(f.id))curves.push({...edge,d:'M '+p.x+' '+p.y+' V '+fruit.y});});
    });
    model.edges.filter(e=>e.type==='previous'&&known.has(e.from)&&known.has(e.to)).forEach(e=>{
      const a=full.get(e.from),b=full.get(e.to);if(a&&b)curves.push({...e,d:'M '+center+' '+a.y+' V '+b.y});
    });
    nodes.forEach(n=>{const p=full.get(n.id);if(p)positions.set(n.id,p);});
    const height=Math.max(220,shownOrphans.length?compactOrphanTop+shownOrphans.length*64+32:compactY+32);
    return {mode:'world',positions,curves,orphans,width:Math.ceil(width),height:Math.ceil(height),nodeWidth:140,nodeHeight:36,nodeRadius,partial:nodes.length<all.length,
      axis:ordered.some(n=>['checkpoint','now'].includes(n.kind))?{x:center,top:Math.min(...ordered.filter(n=>['checkpoint','now'].includes(n.kind)).map(n=>full.get(n.id).y)),bottom:Math.max(...ordered.filter(n=>['checkpoint','now','project'].includes(n.kind)).map(n=>full.get(n.id).y))-12}:null,orphanTop:compactOrphanTop};
  }
  function clampPanel(box,bounds){
    const width=Math.max(1,Number(bounds.width)||1),height=Math.max(1,Number(bounds.height)||1),w=Math.min(Math.max(180,Number(box.w)||320),Math.max(1,width-16)),h=Math.min(Math.max(120,Number(box.h)||360),Math.max(1,height-16));
    return {x:Math.min(Math.max(8,Number(box.x)||8),Math.max(8,width-w-8)),y:Math.min(Math.max(8,Number(box.y)||8),Math.max(8,height-h-8)),w,h};
  }
  function previewURL(node) {
    const p=node && node.preview; if(!p||node.missing)return '';
    if(p.mode==='timeline')return p.code==='现在'||/^C\d+$/.test(str(p.code))?'api/timeline/'+encodeURIComponent(p.code):'';
    let rel=path(p.path), check=rel.startsWith('@/')?rel.slice(2):rel;
    if(!check||/^[a-zA-Z][a-zA-Z0-9+.-]*:|^\/|[\x00-\x1f\x7f]/.test(check)||check.split('/').some(x=>x==='..'||x==='.'))return '';
    if(p.mode==='module'&&p.module)return 'api/modules/'+encodeURIComponent(p.module)+'/preview?path='+encodeURIComponent(rel);
    if(p.mode==='project'&&!rel.startsWith('@/'))return 'api/project/preview?path='+encodeURIComponent(rel);
    return '';
  }
  // 独立的请求门：项目、页签、选择或数据版本变了，旧响应一律不能写回。
  function createReader(options) {
    let serial=0,live=true;
    const context=()=>JSON.stringify(options.context());
    return {async select(node) {
      const request=++serial, before=context(), url=previewURL(node);
      if(!live||!options.isCurrent())return;
      if(!url){options.result(node,null);return;}
      try {
        const data=await options.request('GET',url);
        if(live&&request===serial&&before===context()&&options.isCurrent()){
          if(options.complete)await options.complete(node,data);
          if(live&&request===serial&&before===context()&&options.isCurrent())options.result(node,data);
        }
      }catch(error){if(live&&request===serial&&before===context()&&options.isCurrent())options.error(node,error);}
    },invalidate(){++serial;},destroy(){live=false;++serial;}};
  }
  const normalizeMode = mode => ['map','flow','model3d'].includes(mode) ? mode : 'map';
  const zoomLevel = value => Number.isFinite(Number(value)) ? Math.min(3,Math.max(.5,Number(value))) : 1;
  const defaultCamera = () => ({yaw:-.45,pitch:.42});
  function rotateCamera(camera, dx, dy) {
    camera=camera||defaultCamera();
    const yaw=(Number.isFinite(camera.yaw)?camera.yaw:0)+(Number.isFinite(dx)?dx:0)*.006;
    return {yaw:Math.atan2(Math.sin(yaw),Math.cos(yaw)),pitch:Math.min(1.12,Math.max(-1.12,(Number.isFinite(camera.pitch)?camera.pitch:0)+(Number.isFinite(dy)?dy:0)*.006))};
  }
  function shortLabel(value, budget) {
    const chars=Array.from(str(value)),cost=c=>/[\u0000-\u024f]/u.test(c) ? .58 : 1;
    if(chars.reduce((sum,c)=>sum+cost(c),0)<=budget)return chars.join('');
    let used=0,result='';for(const c of chars){if(used+cost(c)>Math.max(0,budget-1))break;used+=cost(c);result+=c;}return result+'…';
  }
  function project3D(point, camera) {
    camera=camera||defaultCamera();
    const x=point.x*Math.cos(camera.yaw)+point.z*Math.sin(camera.yaw),z=-point.x*Math.sin(camera.yaw)+point.z*Math.cos(camera.yaw);
    return {x,y:point.y*Math.cos(camera.pitch)-z*Math.sin(camera.pitch),z:point.y*Math.sin(camera.pitch)+z*Math.cos(camera.pitch)};
  }
  // 布局改变阅读方式，不新增实体或任务先后关系。
  function layout(nodes, edges, mode, camera) {
    mode=normalizeMode(mode);const positions=new Map(),planes=[],nodeWidth=mode==='model3d'?200:218,nodeHeight=nodes.some(n=>arr(n.mergeNotes).length)?88:58;
    let width=738,height=260;
    if(mode==='map'){
      const root=nodes.find(n=>n.kind==='project')||nodes[0];if(!root)return {mode,positions,planes,width,height,nodeWidth,nodeHeight};
      const parents=mindParents({nodes,edges}),children=new Map(nodes.map(n=>[n.id,[]])),step=nodeHeight+24,gap=nodeWidth+42;
      nodes.forEach(n=>{if(n.id!==root.id)children.get(parents.get(n.id)?.from||root.id)?.push(n.id);});
      const spans=new Map(),depths=new Map();
      function span(key){const cs=children.get(key)||[];const value=Math.max(step,cs.reduce((sum,c)=>sum+span(c),0));spans.set(key,value);depths.set(key,cs.length?1+Math.max(...cs.map(c=>depths.get(c))):0);return value;}
      span(root.id);const sides=[[],[]],sizes=[0,0];(children.get(root.id)||[]).forEach(key=>{const side=sizes[0]<=sizes[1]?0:1;sides[side].push(key);sizes[side]+=spans.get(key);});
      const depth=Math.max(1,depths.get(root.id)),baseWidth=2*depth*gap+nodeWidth+48;
      width=Math.max(width,baseWidth);height=Math.max(height,...sizes.map(n=>n+60));const center=(width-nodeWidth)/2,centerY=(height-nodeHeight)/2;
      positions.set(root.id,{x:center,y:centerY,z:0});
      function place(key,side,level,top){
        positions.set(key,{x:center+side*level*gap,y:top+(spans.get(key)-nodeHeight)/2,z:0});
        let y=top;for(const child of children.get(key)||[]){place(child,side,level+1,y);y+=spans.get(child);}
      }
      sides.forEach((ns,i)=>{let y=(height-sizes[i])/2;for(const key of ns){place(key,i===0?-1:1,1,y);y+=spans.get(key);}});
    }else if(mode==='flow'){
      const known=new Set(nodes.map(n=>n.id)),indegree=new Map(nodes.map(n=>[n.id,0])),rank=new Map(nodes.map(n=>[n.id,0])),outgoing=new Map(nodes.map(n=>[n.id,[]]));
      edges.forEach(e=>{if(known.has(e.from)&&known.has(e.to)){indegree.set(e.to,indegree.get(e.to)+1);outgoing.get(e.from).push(e.to);}});
      const queue=nodes.filter(n=>indegree.get(n.id)===0).map(n=>n.id),done=new Set();
      for(let i=0;i<queue.length;i++){const key=queue[i];done.add(key);outgoing.get(key).forEach(to=>{rank.set(to,Math.max(rank.get(to),rank.get(key)+1));indegree.set(to,indegree.get(to)-1);if(indegree.get(to)===0)queue.push(to);});}
      // 真实记录即使成环仍可显示；不将环补成不存在的依赖。
      nodes.filter(n=>!done.has(n.id)).forEach(n=>rank.set(n.id,Math.max(1,Number(n.depth)||1)));
      const columns=new Map();nodes.forEach(n=>{const c=rank.get(n.id);if(!columns.has(c))columns.set(c,[]);columns.get(c).push(n);});
      columns.forEach((ns,c)=>ns.forEach((n,i)=>positions.set(n.id,{x:24+c*262,y:30+i*(nodeHeight+24),z:0})));
      width=Math.max(width,...Array.from(columns.keys(),c=>c*262+nodeWidth+48));height=Math.max(height,...Array.from(columns.values(),ns=>ns.length*(nodeHeight+24)+60));
    }else{
      const layers=[[],[],[]],layer=n=>['project','goal','group','checkpoint','now'].includes(n.kind)?0:['file','fruit'].includes(n.kind)?2:1;
      nodes.forEach(n=>layers[layer(n)].push(n));
      const points=[],floorPoints=[];
      layers.forEach((ns,l)=>{
        if(!ns.length)return;
        const cols=Math.min(3,ns.length),rows=Math.ceil(ns.length/cols),halfX=Math.max(130,(cols-1)*145+130),halfZ=Math.max(75,(rows-1)*110+75),y=l*230;
        ns.forEach((n,i)=>points.push({id:n.id,...project3D({x:(i%cols-(cols-1)/2)*290,y,z:(Math.floor(i/cols)-(rows-1)/2)*220},camera)}));
        floorPoints.push({layer:l,points:[[-halfX,-halfZ],[halfX,-halfZ],[halfX,halfZ],[-halfX,halfZ]].map(([x,z])=>project3D({x,y:y+34,z},camera))});
      });
      const all=points.concat(...floorPoints.map(p=>p.points));
      const minX=Math.min(0,...all.map(p=>p.x)),maxX=Math.max(0,...all.map(p=>p.x)),minY=Math.min(0,...all.map(p=>p.y)),maxY=Math.max(0,...all.map(p=>p.y));
      const offsetX=24-minX,offsetY=36-minY;
      points.forEach(p=>positions.set(p.id,{x:p.x+offsetX,y:p.y+offsetY,z:p.z}));
      floorPoints.forEach(p=>planes.push({layer:p.layer,points:p.points.map(q=>({x:q.x+offsetX+nodeWidth/2,y:q.y+offsetY+nodeHeight/2}))}));
      width=Math.max(width,maxX-minX+nodeWidth+48);height=Math.max(height,maxY-minY+nodeHeight+72);
    }
    return {mode,positions,planes,width:Math.ceil(width),height:Math.ceil(height),nodeWidth,nodeHeight};
  }
  function mapStyles(doc) {
    if(!doc||!doc.createElement||!doc.head||doc.getElementById('governance-map-style'))return;
    const style=doc.createElement('style');style.id='governance-map-style';style.textContent=`
      .gmap .gmap-svg{min-width:0;max-width:none}.gmap .gmap-node text{font:.875rem var(--font,system-ui);fill:var(--fg)}
      .gmap .gmap-node .gmap-node-kind{font-size:.6875rem;fill:var(--muted)}.gmap .gmap-node.missing rect{stroke-dasharray:4 3}
      .gmap .gmap-toggle rect{fill:var(--plane);stroke:var(--line)}.gmap .gmap-toggle text{font-size:.875rem;text-anchor:middle;fill:var(--fg2)}
      .gmap .gmap-toggle:focus-visible rect{stroke:var(--accent);stroke-width:2}.gmap .gmap-merge-note{font-size:.6875rem;fill:var(--fg2)}
      .gmap .gmap-world-svg{min-width:0}
      .gmap .gmap-world-axis{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linecap:round;vector-effect:non-scaling-stroke}
      .gmap .gmap-world-curve{fill:none;stroke:var(--hover-gold,var(--accent));stroke-width:1.4;stroke-linecap:round;vector-effect:non-scaling-stroke}.gmap .gmap-world-curve.previous{stroke:var(--accent);stroke-width:2.4}
      .gmap .gmap-world-point{fill:var(--card);stroke:var(--hover-gold,var(--accent));stroke-width:1.4;vector-effect:non-scaling-stroke}.gmap .gmap-world-node.checkpoint .gmap-world-point{stroke:var(--accent)}.gmap .gmap-world-node.now .gmap-world-point{stroke:var(--accent);stroke-dasharray:3 4}.gmap .gmap-world-core{fill:var(--accent)}
      .gmap .gmap-world-node:hover .gmap-world-point,.gmap .gmap-world-node:focus-visible .gmap-world-point,.gmap .gmap-world-node.selected .gmap-world-point{stroke:var(--hover-gold,var(--accent));stroke-width:2}.gmap .gmap-world-node.selected .gmap-world-point{fill:color-mix(in srgb,var(--accent) 12%,var(--card))}.gmap .gmap-world-node.missing .gmap-world-point{stroke-dasharray:3 3}
      .gmap .gmap-world-label,.gmap .gmap-world-node .gmap-world-label{font:.8125rem var(--font,system-ui);fill:var(--fg)}.gmap .gmap-world-state,.gmap .gmap-world-node .gmap-world-state,.gmap .gmap-world-time{font:.6875rem var(--font,system-ui);fill:var(--muted)}.gmap .gmap-world-node .gmap-merge-note{font-size:.625rem;fill:var(--fg2)}
      .gmap .gmap-world-halo{fill:none;stroke:var(--accent);opacity:.2}.gmap .gmap-world-new{animation:gmap-grow .7s ease-out both;transform-box:fill-box;transform-origin:center}
      .gmap .gmap-world-running .gmap-world-halo{animation:gmap-breathe 3.8s ease-in-out infinite}
      .gmap .gmap-world-curve.gmap-world-new{stroke-dasharray:1;stroke-dashoffset:1;animation:gmap-branch-grow .9s ease-out both}
      .gmap.gmap-motion-paused .gmap-world-new,.gmap.gmap-motion-paused .gmap-world-halo{animation:none}
      .gmap.gmap-motion-paused .gmap-world-curve.gmap-world-new{stroke-dashoffset:0}
      @keyframes gmap-grow{from{opacity:0}to{opacity:1}}@keyframes gmap-branch-grow{to{stroke-dashoffset:0}}@keyframes gmap-breathe{50%{opacity:.55;stroke-width:2.5}}
      @media(prefers-reduced-motion:reduce){.gmap .gmap-world-new,.gmap .gmap-world-halo{animation:none}.gmap .gmap-world-curve.gmap-world-new{stroke-dashoffset:0}}
      .gmap .gmap-node rect,.gmap .gmap-edge,.gmap .gmap-plane{vector-effect:non-scaling-stroke}
      .gmap .gmap-edge-source{stroke-dasharray:3 3}.gmap .gmap-edge-linked{stroke:var(--accent);opacity:.6}
      .gmap .gmap-edge-previous{stroke-dasharray:1 5;stroke:var(--muted);opacity:.6}
      .gmap .gmap-arrow{fill:var(--muted)}.gmap .gmap-plane{fill:var(--accent);fill-opacity:.025;stroke:var(--line);stroke-width:1}
      .gmap .gmap-toolbar{flex-wrap:nowrap;overflow-x:auto;gap:.35rem}.gmap .gmap-toolbar h2{margin:0;font-size:.95rem;white-space:nowrap}.gmap .gmap-toolbar>*{flex-shrink:0}.gmap .gmap-toolbar .gmap-search{width:10rem;min-width:6rem}
      .gmap .gmap-zoom{display:flex;align-items:center;gap:.25rem}.gmap .gmap-zoom output{min-width:3rem;text-align:center;font: .75rem var(--mono,monospace)}
      .gmap .gmap-canvas{position:relative;min-width:0}.gmap .gmap-context{position:absolute;bottom:.6rem;left:.6rem;z-index:1}
      .gmap .gmap-reading{padding:0;display:flex;flex-direction:column;overflow:hidden}.gmap .gmap-reading-body{padding:.85rem;overflow:auto;min-height:0;flex:1;overflow-wrap:anywhere}
      .gmap .gmap-reading-size{align-self:flex-end;flex-shrink:0;width:1.6rem;height:1.35rem;border:0;background:transparent;color:var(--muted);font:.9rem var(--font,system-ui);cursor:nwse-resize;touch-action:none;user-select:none}.gmap .gmap-reading-size:hover,.gmap .gmap-reading-size:focus-visible{color:var(--hover-gold,var(--accent));outline:1px solid var(--hover-gold,var(--accent));outline-offset:-2px}
      .gmap .gmap-reading-handle{display:none;padding:.45rem .75rem;border-bottom:1px solid var(--line);font-size:.75rem;cursor:grab;touch-action:none;user-select:none}
      .gmap .gmap-toolbar button[aria-pressed=true]{border-color:var(--accent);background:var(--plane)}
      .gmap.gmap-wheel-canvas .gmap-canvas,.gmap.gmap-wheel-canvas .gmap-graph{overflow:hidden}.gmap .gmap-graph{cursor:grab;touch-action:none}.gmap .gmap-graph.dragging{cursor:grabbing}
      .gmap.gmap-mode-model3d .gmap-node{cursor:pointer}.gmap .gmap-reading{font-size:.875rem}
      .gmap:fullscreen,.gmap.gmap-fs{box-sizing:border-box;background:var(--card);color:var(--fg);margin:0;padding:1rem;display:flex;flex-direction:column;width:100%;height:100%;overflow:hidden}
      .gmap.gmap-fs{position:fixed;inset:0;width:100vw;height:100vh;z-index:80}
      .gmap:fullscreen .gmap-layout,.gmap.gmap-fs .gmap-layout{flex:1;min-height:0}
      .gmap:fullscreen .gmap-layout,.gmap.gmap-fs .gmap-layout{position:relative;display:block}
      .gmap:fullscreen .gmap-canvas,.gmap.gmap-fs .gmap-canvas{height:100%}
      .gmap:fullscreen .gmap-graph,.gmap:fullscreen .gmap-reading,.gmap.gmap-fs .gmap-graph,.gmap.gmap-fs .gmap-reading{height:100%;max-height:none;box-sizing:border-box}
      .gmap:fullscreen .gmap-header,.gmap.gmap-fs .gmap-header{margin-top:0}
      .gmap:fullscreen .gmap-reading,.gmap.gmap-fs .gmap-reading{position:absolute;right:1rem;top:1rem;width:22rem;height:65%;z-index:3;min-width:0;box-shadow:0 .5rem 2rem var(--ring);border-color:var(--hover-gold,var(--line))}
      .gmap:fullscreen .gmap-reading-handle,.gmap.gmap-fs .gmap-reading-handle{display:block}
      .gmap:fullscreen .gmap-legend,.gmap.gmap-fs .gmap-legend{margin:.2rem 0 .6rem}
      .gmap:fullscreen .gmap-warnings,.gmap.gmap-fs .gmap-warnings{max-height:15vh;overflow:auto}
      body:has(.gmap.gmap-fs) #note{z-index:90}body:has(.gmap.gmap-fs) #toast{z-index:91}
      .overview-height-corner{position:absolute;right:2px;bottom:2px;z-index:2;width:16px;height:16px;padding:2px;border:0;border-radius:2px;background:transparent;color:var(--muted);cursor:ns-resize;touch-action:none;user-select:none;opacity:.65}
      .overview-height-corner svg{display:block;width:100%;height:100%;pointer-events:none}.overview-height-corner:hover,.overview-height-corner:focus-visible{color:var(--hover-gold,var(--accent));opacity:1;outline:1px solid var(--hover-gold,var(--accent));outline-offset:1px}.overview-height-corner[hidden]{display:none}
      .gmap.gmap-height-adjustable{position:relative;padding-bottom:18px}.gmap .gmap-layout[data-overview-sized]{height:var(--overview-frame-height);min-height:0}.gmap .gmap-layout[data-overview-sized] .gmap-canvas{height:100%;min-height:0}.gmap .gmap-layout[data-overview-sized] .gmap-graph{height:100%;max-height:none;box-sizing:border-box}.gmap .gmap-layout[data-overview-sized] .gmap-reading{min-height:0;max-height:100%;box-sizing:border-box}
      .gmap:fullscreen .gmap-layout[data-overview-sized],.gmap.gmap-fs .gmap-layout[data-overview-sized]{height:auto}.gmap:fullscreen .overview-height-corner,.gmap.gmap-fs .overview-height-corner{display:none}
    `;doc.head.appendChild(style);
  }
  // Only container geometry is changed: no redraw, refit, data write or navigation.
  function mountHeightControl({target,handle,projectRoot='',scope='',isFullscreen=()=>false,isCurrent=()=>true,onResize=()=>{}}) {
    const doc=target.ownerDocument,win=doc&&doc.defaultView;
    mapStyles(doc);
    let live=true,drag=null,key='',height=null;
    const clamp=n=>Math.max(320,Math.min(2400,Math.round(n)));
    function property(value){
      if(target.style.setProperty){if(value===null)target.style.removeProperty('--overview-frame-height');else target.style.setProperty('--overview-frame-height',value+'px');}
      else {if(value===null)delete target.style['--overview-frame-height'];else target.style['--overview-frame-height']=value+'px';}
      if(value===null)delete target.dataset.overviewSized;else target.dataset.overviewSized='';
    }
    function measured(){const r=target.getBoundingClientRect&&target.getBoundingClientRect();return clamp(r&&r.height||target.clientHeight||560);}
    function end(){const prior=drag;drag=null;if(prior&&handle.releasePointerCapture){try{handle.releasePointerCapture(prior.id);}catch(_){}}}
    function sync(){const full=isFullscreen();handle.hidden=full;if(full||!isCurrent())end();}
    function save(){if(!key)return;try{win&&win.localStorage.setItem(key,String(height));}catch(_){} }
    function apply(n){if(!live||!isCurrent()||isFullscreen()||!Number.isFinite(n))return; height=clamp(n);property(height);onResize();}
    function update(root,nextScope){
      const next=root?'tpl_overview_height:'+JSON.stringify([String(root),String(nextScope)]):'';
      if(key===next){sync();return;}
      end();key=next;height=null;property(null);
      try{const raw=key&&win&&win.localStorage.getItem(key);if(raw&&/^\d+(?:\.\d+)?$/.test(raw)){const n=Number(raw);if(Number.isFinite(n)&&n>=320&&n<=2400){height=clamp(n);property(height);}}}catch(_){}
      sync();
    }
    const down=e=>{if(e.button!==0||!live||!isCurrent()||isFullscreen()||!Number.isFinite(e.clientY))return;end();drag={id:e.pointerId,y:e.clientY,h:measured()};if(handle.setPointerCapture){try{handle.setPointerCapture(e.pointerId);}catch(_){}}e.preventDefault();};
    const move=e=>{if(!drag||e.pointerId!==drag.id)return;if(!isCurrent()||isFullscreen()){end();return;}apply(drag.h+e.clientY-drag.y);e.preventDefault();};
    const up=e=>{if(!drag||drag.id!==e.pointerId)return;save();end();};
    const keyboard=e=>{if(!['ArrowUp','ArrowDown'].includes(e.key)||!live||!isCurrent()||isFullscreen())return;e.preventDefault();apply((height||measured())+(e.key==='ArrowDown'?1:-1)*(e.shiftKey?32:8));save();};
    const events={pointerdown:down,pointermove:move,pointerup:up,pointercancel:up,lostpointercapture:up,keydown:keyboard};
    for(const [type,fn] of Object.entries(events))handle.addEventListener(type,fn);
    update(projectRoot,scope);
    return {update,sync,state:()=>({height,key,dragging:!!drag}),destroy(){if(!live)return;live=false;end();for(const [type,fn] of Object.entries(events))handle.removeEventListener(type,fn);}};
  }
  const mounted = new WeakMap();
  function mount(host, options, helpers) {
    if(typeof host==='string'&&typeof document!=='undefined')host=document.querySelector(host);
    if(!host)throw new Error('找不到二维总览容器 Missing map host');
    const existing=mounted.get(host); if(existing){existing.update(options,helpers);return existing;}
    let opts=options||{},help=helpers||{},model,limit=8,query='',focus='',selected='',revision=0,live=true,expanded=new Set(),noteNode=null,animated=new Set();
    let worldInitialFit=true;
    let motion=true,panelBox=null,panelDrag=null,panelResize=null,panelSize={w:330,h:420},panelSized=false,wasFull=false,pan={x:0,y:0};
    let mode='map',preference=null,zoom=1,camera=defaultCamera(),fallback=false,fullPending=false,fullSerial=0,drag=null,suppressClickUntil=0;
    const doc=host.ownerDocument||(typeof document!=='undefined'?document:null),win=doc&&doc.defaultView||(typeof window!=='undefined'?window:null);
    mapStyles(doc);
    const lang=()=>help.language?help.language():typeof getLang==='function'?getLang():'both';
    const label=x=>x[0]===x[1]?x[0]:lang()==='en'?x[1]:lang()==='zh'?x[0]:x[0]+' · '+x[1];
    const current=()=>live&&host.isConnected!==false&&(!help.isCurrent||help.isCurrent());
    const wheelCanvas=()=>model&&['blueprint','archives'].includes(model.kind);
    const request=(method,url)=>help.request?help.request(method,url):api(method,url);
    const markdown=text=>help.renderMarkdown?help.renderMarkdown(text):typeof renderMd==='function'?renderMd(text):'<pre>'+escape(text)+'</pre>';
    const title=()=>opts.kind==='archives'?['世界树','World tree']:['module','index'].includes(opts.kind)?[str(opts.module||opts.name||'总览'),str(opts.module||opts.name||'Overview')]:opts.kind==='rules'?['戒律','Rules']:['蓝图','Blueprint'];
    host.innerHTML='<section class="gmap"><header class="gmap-toolbar"><h2 class="gmap-title">'+label(title())+'</h2><span class="gmap-count"></span>'
      +'<input type="search" class="gmap-search" placeholder="'+label(['搜索','Search'])+'" aria-label="'+label(['搜索节点','Search nodes'])+'">'
      +'<div class="gmap-zoom"><button class="sbtn" type="button" data-gmap-zoom="out" aria-label="'+label(['缩小','Zoom out'])+'">−</button><output class="gmap-scale">100%</output><button class="sbtn" type="button" data-gmap-zoom="in" aria-label="'+label(['放大','Zoom in'])+'">+</button><button class="sbtn" type="button" data-gmap-zoom="fit">'+label(['适配','Fit'])+'</button></div><button class="sbtn" type="button" data-gmap-motion>'+label(['暂停动画','Pause motion'])+'</button><button class="sbtn" type="button" data-gmap-full>'+label(['全屏','Fullscreen'])+'</button><button class="sbtn sticky-shortcut" type="button" data-gmap-notes aria-label="便签 Sticky note" title="便签 Sticky note">'+(help.notesIcon?help.notesIcon():'')+label(['便签','Sticky note'])+'</button></header>'
      +'<p class="gmap-legend hint"></p><div class="gmap-warnings"></div><div class="gmap-layout"><div class="gmap-canvas"><div class="gmap-graph"></div><div class="gmap-context"><button class="sbtn" type="button" data-gmap-more>'+label(['查看更多','Show more'])+'</button></div></div><section class="gmap-reading"><header class="gmap-reading-handle" tabindex="0">'+label(['阅读','Reading'])+'</header><div class="gmap-reading-body" aria-live="polite" tabindex="-1"></div><button type="button" class="gmap-reading-size" data-gmap-size aria-label="'+label(['拖动或用方向键调整阅读窗大小','Drag or use arrow keys to resize reading pane'])+'" title="'+label(['调整大小','Resize'])+'">↘</button></section></div></section>';
    const component=host.querySelector('.gmap'),canvasLayout=host.querySelector('.gmap-layout'),graph=host.querySelector('.gmap-graph'),readPanel=host.querySelector('.gmap-reading'),reading=host.querySelector('.gmap-reading-body'),readHandle=host.querySelector('.gmap-reading-handle'),counter=host.querySelector('.gmap-count'),more=host.querySelector('[data-gmap-more]');
    const fullButton=host.querySelector('[data-gmap-full]');
    const sizeHandle=host.querySelector('[data-gmap-size]');
    const heightHandle=doc&&doc.createElement?doc.createElement('button'):null;
    let heightControl=null;
    if(heightHandle){heightHandle.type='button';heightHandle.className='overview-height-corner';heightHandle.dataset.gmapHeight='';heightHandle.setAttribute('aria-label',label(['拖动或用上下方向键调整总览高度','Drag or use up/down keys to resize overview height']));heightHandle.title=label(['调整总览高度','Resize overview height']);heightHandle.innerHTML='<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 10 10 3M7 10 10 7" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>';component.appendChild(heightHandle);}
    // 定时更新内容相同不重写阅读 DOM，保留选择、滚动和全屏容器。
    function writeReading(html,keepScroll){
      if(reading.innerHTML===html)return;
      const top=keepScroll?reading.scrollTop:0;reading.innerHTML=html;reading.scrollTop=top||0;
    }
    function archiveBody(node,data){
      if(!node.record)return '';
      if(node.kind==='entry')return node.record.record?(help.openRecord?'<button class="sbtn" type="button" data-gmap-record>'+label(['打开原页','Open original page'])+'</button>':''):'<p class="hint">'+label(['没有原页入口','No original page reference'])+'</p>';
      const isTimeline=['checkpoint','now'].includes(node.kind),record=data||node.record.record;
      let html='';
      const fields={code:['编号','ID'],id:['编号','ID'],key:['来源编号','Source ID'],text:['原文','Text'],at:['时间','Time'],goal:['目标','Goal'],sub:['任务','Task'],what:['内容','Content'],state:['状态','Status'],by:['记录者','Recorded by'],kind:['分类','Kind'],name:['检查','Check'],ok:['通过','Passed'],detail:['详情','Detail'],ref:['引用','Reference']};
      const showRows=(name,rows)=>'<details class="gmap-history"><summary>'+label(name)+' · '+(Array.isArray(rows)?rows.length:label(['未返回','Not returned']))+'</summary>'
        +(Array.isArray(rows)?rows.length?rows.map(row=>'<p data-nt>'+escape(typeof row==='string'?row:Object.entries(row).map(([k,v])=>label(fields[k]||[k,k])+': '+recordText(v)).join(' · '))+'</p>').join(''):'<p class="hint">'+label(['没有记录','No records'])+'</p>':'')+'</details>';
      if(isTimeline){
        const counts=record.counts||{};
        html+='<div class="kv">'+Object.entries(countNames).filter(([key])=>Object.prototype.hasOwnProperty.call(counts,key)).map(([key,name])=>'<span class="k">'+label(name)+'</span><span data-nt>'+escape(counts[key])+'</span>').join('')+'</div>';
        for(const [key,name] of Object.entries(countNames))html+=showRows(name,record[key]);
        const files=record.files||{},countsFiles=arr(files.counts);
        html+='<h4>'+label(['文件变化','File changes'])+'</h4>';
        if(countsFiles.length)html+='<p data-nt>'+[['新增','Added'],['改动','Changed'],['移除','Removed']].map((name,i)=>label(name)+' '+recordText(countsFiles[i])).join(' · ')+'</p>';
        html+=showRows(['新增文件','Added files'],files.added)+showRows(['改动文件','Changed files'],files.changed)+showRows(['移除文件','Removed files'],files.removed);
      }else{
        html+=showRows(['检查','Checks'],record.checks);
        if(record.merged){html+='<h4>'+label(['合并记录','Merge record'])+'</h4>';for(const key of ['took','merged','deleted','conflicts','records'])if(Array.isArray(record.merged[key]))html+=showRows([key,key],record.merged[key]);}
        if(help.openRecord)html+='<button class="sbtn" type="button" data-gmap-record>'+label(['打开原记录','Open original record'])+'</button>';
      }
      return html;
    }
    const reader=createReader({context:()=>({root:model.projectRoot,revision}),isCurrent:current,request,
      complete:()=>win&&win.PaneSpirit&&typeof win.PaneSpirit.complete==='function'?win.PaneSpirit.complete(reading):Promise.resolve(false),
      result(node,data){
        const sources=model.edges.filter(e=>e.from===node.id&&e.type==='source').map(e=>model.nodes.find(n=>n.id===e.to)).filter(n=>n&&n.kind==='file');
        let h='<h3 data-nt>'+escape(node.title)+'</h3><p class="hint" data-nt>'+escape(node.status||'')+'</p>'
          +arr(node.details).filter(d=>d.value).map(d=>'<p><b>'+label(d.label)+'：</b><span data-nt>'+escape(d.value)+'</span></p>').join('');
        if(sources.length)h+='<div class="gmap-file-actions">'+sources.map(n=>'<button class="sbtn" type="button" data-gmap-node="'+escape(n.id)+'" data-nt>'+escape(n.file)+'</button>').join(' ')+'</div>';
        if(node.record)h+=archiveBody(node,data);
        else if(data){
          h+='<div class="hint" data-nt>'+escape(node.preview.path)+'</div>';
          if(data.text!==undefined)h+=data.kind==='md'||/\.md$/i.test(node.preview.path)?'<article class="md" data-nt>'+markdown(str(data.text))+'</article>':'<pre class="gmap-text" data-nt>'+escape(data.text)+'</pre>';
          else h+='<p class="hint">'+label(['此文件未返回文字，请从原文件入口预览','No text returned; use the existing file preview'])+'</p>';
        }else if(!sources.length)h+='<p class="hint">'+label(['没有可读取文件','No readable file'])+'</p>';
        writeReading(h,true);
      },error(node,error){writeReading('<h3 data-nt>'+escape(node.title)+'</h3><p class="gmap-error" data-nt>'+escape(error.message||error)+'</p>',true);}});
    const fullActive=()=>fallback||!!(doc&&doc.fullscreenElement===component);
    const panelBounds=()=>({width:canvasLayout.clientWidth||win&&win.innerWidth||800,height:canvasLayout.clientHeight||win&&win.innerHeight||600});
    function applyPanel(){
      if(!fullActive()){
        if(panelSized){const width=Math.min(panelSize.w,Math.max(180,(canvasLayout.clientWidth||800)-120));canvasLayout.style.gridTemplateColumns='minmax(0,1fr) '+width+'px';Object.assign(readPanel.style,{width:'',height:panelSize.h+'px',maxHeight:heightControl&&heightControl.state().height?'100%':'none'});}
        return;
      }
      const bounds=panelBounds();panelBox=clampPanel(panelBox||{x:bounds.width-panelSize.w-20,y:70,w:panelSize.w,h:Math.min(panelSize.h,bounds.height-90)},bounds);
      Object.assign(readPanel.style,{left:panelBox.x+'px',top:panelBox.y+'px',right:'auto',width:panelBox.w+'px',height:panelBox.h+'px'});
    }
    function syncFull(){
      const active=fullActive();fullButton.textContent=label(active?['退出全屏','Exit fullscreen']:['全屏','Fullscreen']);fullButton.setAttribute('aria-pressed',String(active));
      if(heightControl)heightControl.sync();
      if(active)applyPanel();else{if(wasFull){Object.assign(readPanel.style,{left:'',top:'',right:'',width:'',height:''});endPanelDrag();endPanelResize();}applyPanel();}wasFull=active;
    }
    function exitFull(){
      ++fullSerial;fullPending=false;fallback=false;component.classList.remove('gmap-fs');
      if(noteNode&&noteNode.parentNode===component&&doc&&doc.body){doc.body.appendChild(noteNode);noteNode=null;}
      if(doc&&doc.fullscreenElement===component&&doc.exitFullscreen){try{const p=doc.exitFullscreen();if(p&&p.catch)p.catch(()=>{});}catch(_){}}
      syncFull();
    }
    async function toggleFull(){
      if(fallback||doc&&doc.fullscreenElement===component||fullPending){exitFull();return;}
      if(!current())return;const attempt=++fullSerial;fullPending=true;
      try{
        if(!component.requestFullscreen)throw new Error('Native fullscreen unavailable');
        await component.requestFullscreen();
        if(attempt!==fullSerial||!current()){
          if(doc&&doc.fullscreenElement===component&&doc.exitFullscreen){try{await doc.exitFullscreen();}catch(_){}}
          return;
        }
      }catch(_){if(attempt===fullSerial&&current()){fallback=true;component.classList.add('gmap-fs');}}
      finally{if(attempt===fullSerial)fullPending=false;syncFull();}
    }
    function worldSVG(view,shape){
      let svg='<svg class="gmap-svg gmap-world-svg" role="group" aria-label="'+escape(label(['青铜芯片树：时间序位与明确工作树来源','Bronze chip tree: timeline order and explicit branch sources']))+'" width="'+Math.round(shape.width*zoom)+'" height="'+Math.round(shape.height*zoom)+'" viewBox="0 0 '+shape.width+' '+shape.height+'" data-nt>';
      if(shape.partial)svg+='<text class="gmap-world-state" x="16" y="18">'+escape(label(['局部视图 · 只排列当前显示记录','Partial view · current records only']))+'</text>';
      if(shape.axis&&view.nodes.length)svg+='<path class="gmap-world-axis" d="M '+shape.axis.x+' '+shape.axis.top+' V '+shape.axis.bottom+'"><title>'+escape(label(['时间序位；不是工作树祖先关系','Timeline order; not branch ancestry']))+'</title></path>';
      shape.curves.forEach(c=>{
        const grow=!animated.has(c.to);
        svg+='<path class="gmap-world-curve '+c.type+(grow?' gmap-world-new':'')+'" pathLength="1" d="'+c.d+'"><title>'+escape(label(edgeNames[c.type])+(c.detail?' · '+c.detail:''))+'</title></path>';
      });
      if(shape.orphans.length)svg+='<text class="gmap-world-state" x="40" y="'+(shape.orphanTop-32)+'">'+escape(label(['来源未关联','Source unlinked']))+'</text>';
      view.nodes.forEach(n=>{
        const p=shape.positions.get(n.id);if(!p)return;
        if(n.kind==='project'){svg+='<text class="gmap-world-label" text-anchor="middle" x="'+p.x+'" y="'+p.y+'">'+escape(n.title)+'</text>';return;}
        const row=n.record&&n.record.record||{},running=n.kind==='branch'&&row.running===true&&['长着','结果了'].includes(row.state),fresh=!animated.has(n.id),side=p.side||1,anchor=side<0?'end':'start',x=side*14;
        const hasFruit=n.kind==='branch'&&view.edges.some(e=>e.from===n.id&&e.type==='contains'),radius=n.kind==='fruit'?7:n.kind==='branch'?(hasFruit?4:6):n.kind==='now'?6:shape.nodeRadius;
        const notes=arr(n.mergeNotes).map(m=>label(['合并了','Merged'])+' '+m.branch+' / '+m.fruit+(m.demo?' · '+m.demo:''));
        const timing=p.timeStatus==='before-source'?label(['时间早于来源，待核对','Time precedes source; check record']):p.time||label(['时间未记录','Time unrecorded']);
        const caption=n.kind==='fruit'?n.record.code||label(['果实未编号','Fruit ID unrecorded']):n.kind==='now'?label(['现在','Now']):n.key||label(['编号未记录','ID unrecorded']);
        svg+='<g class="gmap-node gmap-world-node '+n.kind+(n.id===selected?' selected':'')+(n.missing?' missing':'')+(running?' gmap-world-running':'')+(fresh?' gmap-world-new':'')+'" transform="translate('+p.x+' '+p.y+')" data-gmap-node="'+escape(n.id)+'" role="button" tabindex="0" aria-label="'+escape(n.title)+'" aria-pressed="'+(n.id===selected)+'"><title>'+escape(n.title+'\n'+(n.source||n.key)+'\n'+timing+(notes.length?'\n'+notes.join('\n'):''))+'</title>';
        if(running)svg+='<circle class="gmap-world-halo" r="12"/>';
        svg+='<circle class="gmap-world-point" r="'+radius+'"/>';
        if(n.kind==='fruit')svg+='<circle class="gmap-world-core" r="2"/>';
        svg+='<text class="gmap-world-label" x="'+x+'" y="3" text-anchor="'+anchor+'">'+escape(shortLabel(caption,18))+'</text>';
        notes.forEach((note,i)=>{svg+='<text class="gmap-world-label gmap-merge-note" x="14" y="'+(22+i*16)+'">'+escape(shortLabel(note,24))+'</text>';});
        svg+='</g>';animated.add(n.id);
      });return svg+'</svg>';
    }
    function render() {
      if(!current())return;
      host.querySelector('.gmap-title').textContent=label(title());more.textContent=label(['查看更多','Show more']);
      host.querySelector('[data-gmap-zoom="fit"]').textContent=label(['适配','Fit']);host.querySelector('.gmap-legend').textContent=[...new Set(model.edges.map(e=>e.type))].map(type=>label(edgeNames[type])).join(' · ');
      const motionButton=host.querySelector('[data-gmap-motion]');motionButton.hidden=model.kind!=='archives';motionButton.textContent=label(motion?['暂停动画','Pause motion']:['恢复动画','Resume motion']);motionButton.setAttribute('aria-pressed',String(!motion));
      component.classList.remove('gmap-motion-paused');if(!motion)component.classList.add('gmap-motion-paused');readHandle.textContent=label(['阅读','Reading']);
      const notesButton=host.querySelector('[data-gmap-notes]');notesButton.innerHTML=(help.notesIcon?help.notesIcon():'')+label(['便签','Sticky note']);notesButton.hidden=!help.notes;
      const search=host.querySelector('.gmap-search');search.setAttribute('placeholder',label(['搜索','Search']));search.setAttribute('aria-label',label(['搜索节点','Search nodes']));
      host.querySelector('[data-gmap-zoom="out"]').setAttribute('aria-label',label(['缩小','Zoom out']));host.querySelector('[data-gmap-zoom="in"]').setAttribute('aria-label',label(['放大','Zoom in']));
      const isWorld=model.kind==='archives'&&mode==='map',view=isWorld?worldVisible(model,{limit,query,selected}):mode==='map'?mindVisible(model,{limit,query,expanded,selected}):visible(model,{limit,query,focus}),shape=isWorld?worldLayout(model,view.nodes):layout(view.nodes,view.edges,mode,camera),xy=shape.positions,w=shape.nodeWidth,h=shape.nodeHeight;
      if(isWorld&&worldInitialFit&&graph.clientWidth>0){
        zoom=zoomLevel(Math.min(1,(graph.clientWidth-2)/shape.width,(graph.clientHeight||Math.min(560,shape.height))/shape.height));
        pan={x:Math.max(0,graph.clientWidth/2-(shape.axis?shape.axis.x:shape.width/2)*zoom),y:0};graph.scrollLeft=0;graph.scrollTop=0;worldInitialFit=false;
      }
      component.classList.remove('gmap-mode-map','gmap-mode-flow','gmap-mode-model3d');component.classList.add('gmap-mode-'+mode);
      host.querySelector('.gmap-scale').textContent=Math.round(zoom*100)+'%';
      host.querySelector('[data-gmap-zoom="out"]').disabled=zoom<=.5;host.querySelector('[data-gmap-zoom="in"]').disabled=zoom>=3;
      let svg='';if(!isWorld){svg='<svg class="gmap-svg" role="group" aria-label="'+label(['节点与文件关系','Node and file relationships'])+'" width="'+Math.round(shape.width*zoom)+'" height="'+Math.round(shape.height*zoom)+'" viewBox="0 0 '+shape.width+' '+shape.height+'" data-nt>';
      if(mode==='flow')svg+='<defs><marker id="gmap-arrow-'+model.kind+'" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path class="gmap-arrow" d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>';
      shape.planes.forEach(plane=>{svg+='<polygon class="gmap-plane" points="'+plane.points.map(p=>p.x.toFixed(2)+','+p.y.toFixed(2)).join(' ')+'"/>';});
      view.edges.forEach(e=>{
        const a=xy.get(e.from),b=xy.get(e.to),same=a.x===b.x,forward=b.x>=a.x,x1=a.x+(forward?w:0),x2=same?b.x+w:b.x+(forward?0:w),y1=a.y+h/2,y2=b.y+h/2;
        const bend=same?x1+16:(x1+x2)/2;
        const line=mode==='model3d'?'M '+(a.x+w/2)+' '+(a.y+h)+' L '+(b.x+w/2)+' '+b.y:'M '+x1+' '+y1+' C '+bend+' '+y1+' '+bend+' '+y2+' '+x2+' '+y2;
        svg+='<path class="gmap-edge gmap-edge-'+e.type+'" d="'+line+'"'+(mode==='flow'?' marker-end="url(#gmap-arrow-'+model.kind+')"':'')+'><title>'+escape(label(edgeNames[e.type])+(e.detail?' · '+e.detail:''))+'</title></path>';
      });
      const ordered=mode==='model3d'?view.nodes.slice().sort((a,b)=>xy.get(a.id).z-xy.get(b.id).z):view.nodes;
      ordered.forEach(n=>{
        const p=xy.get(n.id),caption=str(n.title),canExpand=mode==='map'&&model.edges.some(e=>e.from===n.id&&e.type!=='previous'||e.to===n.id&&e.type==='linked'),short=shortLabel(caption,(w-(canExpand?48:20))/15);
        const mergeText=arr(n.mergeNotes).map(note=>label(['合并了','Merged'])+' '+note.branch+' / '+note.fruit+(note.demo?' · '+note.demo:''));
        svg+='<g class="gmap-node'+(n.id===selected?' selected':'')+(n.missing?' missing':'')+'" transform="translate('+p.x.toFixed(2)+' '+p.y.toFixed(2)+')" data-gmap-node="'+escape(n.id)+'" role="button" tabindex="0" aria-label="'+escape(caption)+'" aria-pressed="'+(n.id===selected)+'"><title>'+escape(caption+'\n'+(n.file||n.source||n.key)+(mergeText.length?'\n'+mergeText.join('\n'):''))+'</title><rect width="'+w+'" height="'+h+'" rx="6"/><text x="10" y="20">'+escape(short)+'</text><text class="gmap-node-kind" x="10" y="42">'+escape(label(kinds[n.kind])+(n.missing?' · '+label(['缺失','Missing']):''))+'</text>';
        if(canExpand)svg+='<g class="gmap-toggle" data-gmap-toggle="'+escape(n.id)+'" role="button" tabindex="0" aria-label="'+escape(label(expanded.has(n.id)?['收起分支','Collapse branch']:['展开分支','Expand branch'])+' '+caption)+'" aria-expanded="'+expanded.has(n.id)+'" transform="translate('+(w-30)+' 5)"><rect width="24" height="23" rx="4"/><text x="12" y="17">'+(expanded.has(n.id)?'−':'+')+'</text></g>';
        if(mergeText.length)svg+='<text class="gmap-merge-note" x="10" y="61">'+escape(shortLabel(label(['合并了','Merged'])+' '+n.mergeNotes[0].branch+' / '+n.mergeNotes[0].fruit,(w-20)/12))+'</text><text class="gmap-merge-note" x="10" y="77">'+escape(shortLabel(mergeText.length>1?label(['另有合并记录','More merge records'])+' '+(mergeText.length-1):n.mergeNotes[0].demo,(w-20)/12))+'</text>';
        svg+='</g>';
      });
      svg+='</svg>';}
      const drawn=isWorld?worldSVG(view,shape):svg;
      graph.innerHTML=drawn.replace('<svg ','<svg style="transform:translate('+(mode==='model3d'&&!wheelCanvas()?0:pan.x)+'px,'+(mode==='model3d'&&!wheelCanvas()?0:pan.y)+'px)" ')+(view.nodes.length?'':'<p class="hint">'+label(['没有匹配节点','No matching nodes'])+'</p>');
      counter.textContent=view.shown+' / '+view.total+' · '+label(['节点','Nodes']); more.hidden=!view.more;
      host.querySelector('.gmap-warnings').innerHTML=model.warnings.length?'<details><summary>'+label(['记录需要检查','Records to check'])+' · '+model.warnings.length+'</summary>'+model.warnings.map(x=>'<p data-nt>'+escape(x)+'</p>').join('')+'</details>':'';
      syncFull();
    }
    function setMode(next){const nextMode=normalizeMode(next);if(mode===nextMode)return;mode=nextMode;endDrag();render();}
    function setZoom(action,anchor){
      const before=zoom,centerX=(graph.scrollLeft||0)+(graph.clientWidth||0)/2,centerY=(graph.scrollTop||0)+(graph.clientHeight||0)/2;
      zoom=typeof action==='number'?zoomLevel(action):action==='reset'?1:zoomLevel(zoom+(action==='in'?.2:-.2));if(action==='reset')camera=defaultCamera();if(['reset','fit'].includes(action))pan={x:0,y:0};
      if(action==='fit'){
        const isWorld=model.kind==='archives'&&mode==='map',view=isWorld?worldVisible(model,{limit,query,selected}):mode==='map'?mindVisible(model,{limit,query,expanded,selected}):visible(model,{limit,query,focus}),shape=isWorld?worldLayout(model,view.nodes):layout(view.nodes,view.edges,mode,camera);
        zoom=zoomLevel(Math.min((graph.clientWidth||shape.width)/shape.width,(graph.clientHeight||shape.height)/shape.height));
      }
      if(wheelCanvas()&&!['reset','fit'].includes(action)){
        const x=anchor&&Number.isFinite(anchor.x)?anchor.x:(graph.clientWidth||0)/2,y=anchor&&Number.isFinite(anchor.y)?anchor.y:(graph.clientHeight||0)/2,ratio=zoom/before;
        pan={x:Math.max(-10000,Math.min(10000,x-(x+(graph.scrollLeft||0)-pan.x)*ratio)),y:Math.max(-10000,Math.min(10000,y-(y+(graph.scrollTop||0)-pan.y)*ratio))};
      }
      render();graph.scrollLeft=wheelCanvas()||['reset','fit'].includes(action)?0:Math.max(0,centerX*zoom/before-(graph.clientWidth||0)/2);graph.scrollTop=wheelCanvas()||['reset','fit'].includes(action)?0:Math.max(0,centerY*zoom/before-(graph.clientHeight||0)/2);
    }
    function reveal(nodeId){
      const parents=mindParents(model),seen=new Set();let key=nodeId;
      while(key&&!seen.has(key)){seen.add(key);expanded.add(key);key=parents.get(key)?.from;}
    }
    function toggle(nodeId,keyboard){
      if(!current())return;if(expanded.has(nodeId))expanded.delete(nodeId);else expanded.add(nodeId);render();
      if(keyboard){const el=Array.from(graph.querySelectorAll('[data-gmap-toggle]')).find(x=>x.dataset.gmapToggle===nodeId);if(el)el.focus({preventScroll:true});}
    }
    function select(nodeId, keyboard) {
      if(!current())return;
      const node=model.nodes.find(n=>n.id===nodeId);if(!node)return;
      selected=node.id;
      if(node.kind!=='file'){focus=node.id;if(mode!=='map')limit=8;}reveal(node.id);
      render();
      if(keyboard){const el=Array.from(graph.querySelectorAll('[data-gmap-node]')).find(x=>x.dataset.gmapNode===node.id);if(el)el.focus({preventScroll:true});}
      // 实体的来源文件显式列在右侧；只有点文件才读全文。
      const loadingText=label(['正在读取','Loading']);
      writeReading('<p class="hint">'+(win&&win.PaneSpirit&&typeof win.PaneSpirit.loading==='function'?win.PaneSpirit.loading(loadingText):escape(loadingText))+'</p>',false);reader.select(node);
    }
    const click=e=>{const b=e.target.closest('[data-gmap-toggle],[data-gmap-node],[data-gmap-home],[data-gmap-more],[data-gmap-mode],[data-gmap-zoom],[data-gmap-full],[data-gmap-notes],[data-gmap-record],[data-gmap-motion]');if(!b||!host.contains(b))return;
      if(b.hasAttribute('data-gmap-toggle')){if(Date.now()>=suppressClickUntil)toggle(b.dataset.gmapToggle);}
      else if(b.hasAttribute('data-gmap-node')){if(Date.now()>=suppressClickUntil)select(b.dataset.gmapNode,false);}
      else if(b.hasAttribute('data-gmap-home')){focus='';limit=8;expanded=new Set(model.nodes.filter(n=>n.kind==='project').map(n=>n.id));render();}
      else if(b.hasAttribute('data-gmap-more')){limit+=8;render();}
      else if(b.hasAttribute('data-gmap-mode'))setMode(b.dataset.gmapMode);
      else if(b.hasAttribute('data-gmap-zoom'))setZoom(b.dataset.gmapZoom);
      else if(b.hasAttribute('data-gmap-full'))toggleFull();
      else if(b.hasAttribute('data-gmap-motion')){motion=!motion;render();}
      else if(b.hasAttribute('data-gmap-notes')&&help.notes){const note=help.notes();if(note&&doc&&doc.fullscreenElement===component&&component.appendChild){noteNode=note;if(note.parentNode!==component)component.appendChild(note);}}
      else if(b.hasAttribute('data-gmap-record')&&help.openRecord){const node=model.nodes.find(n=>n.id===selected);if(node&&node.record&&node.record.record)help.openRecord(node.record);}};
    const input=e=>{if(e.target.matches('.gmap-search')){query=e.target.value;focus='';limit=8;render();}};
    const key=e=>{const b=e.target.closest('[data-gmap-toggle],[data-gmap-node]');if(b&&host.contains(b)&&(e.key==='Enter'||e.key===' ')){e.preventDefault();if(b.hasAttribute('data-gmap-toggle'))toggle(b.dataset.gmapToggle,true);else select(b.dataset.gmapNode,true);}};
    const escapeKey=e=>{if(e.key==='Escape'&&(fallback||fullPending||doc&&doc.fullscreenElement===component)){e.preventDefault();exitFull();}};
    const modeChange=e=>{if(current()){const next=help.overviewMode?help.overviewMode():e.detail&&e.detail.mode;preference=normalizeMode(next);setMode(next);}};
    function endPanelDrag(){const prior=panelDrag;panelDrag=null;if(prior&&readHandle.releasePointerCapture){try{readHandle.releasePointerCapture(prior.id);}catch(_){}}}
    const panelDown=e=>{if(!fullActive()||e.button!==0)return;applyPanel();panelDrag={id:e.pointerId,x:e.clientX,y:e.clientY,box:{...panelBox}};if(readHandle.setPointerCapture){try{readHandle.setPointerCapture(e.pointerId);}catch(_){}}e.preventDefault();};
    const panelMove=e=>{if(!panelDrag||panelDrag.id!==e.pointerId||!fullActive())return;panelBox={...panelDrag.box,x:panelDrag.box.x+e.clientX-panelDrag.x,y:panelDrag.box.y+e.clientY-panelDrag.y};applyPanel();e.preventDefault();};
    const panelUp=e=>{if(panelDrag&&panelDrag.id===e.pointerId)endPanelDrag();};
    const panelReset=()=>{panelBox=null;applyPanel();};
    const panelKey=e=>{if(!fullActive())return;const delta={ArrowLeft:[-12,0],ArrowRight:[12,0],ArrowUp:[0,-12],ArrowDown:[0,12]}[e.key];if(delta){e.preventDefault();applyPanel();panelBox.x+=delta[0];panelBox.y+=delta[1];applyPanel();}};
    function endPanelResize(){const prior=panelResize;panelResize=null;if(prior&&sizeHandle.releasePointerCapture){try{sizeHandle.releasePointerCapture(prior.id);}catch(_){}}}
    function resizePanel(w,h){
      if(!current())return;
      const maxWidth=fullActive()?Math.max(1,panelBounds().width-16):Math.max(180,(canvasLayout.clientWidth||800)-120);
      panelSize={w:Math.min(maxWidth,Math.max(180,Number.isFinite(w)?w:330)),h:Math.min(1200,Math.max(120,Number.isFinite(h)?h:420))};panelSized=true;
      if(fullActive()){applyPanel();panelBox={...panelBox,w:panelSize.w,h:panelSize.h};}
      applyPanel();
    }
    const sizeDown=e=>{if(e.button!==0||!current())return;applyPanel();const rect=!fullActive()&&readPanel.getBoundingClientRect?readPanel.getBoundingClientRect():null,size=fullActive()?panelBox:rect?{w:rect.width,h:rect.height}:panelSize;panelResize={id:e.pointerId,x:e.clientX,y:e.clientY,w:size.w,h:size.h};endPanelDrag();if(sizeHandle.setPointerCapture){try{sizeHandle.setPointerCapture(e.pointerId);}catch(_){}}e.preventDefault();};
    const sizeMove=e=>{if(!panelResize||panelResize.id!==e.pointerId)return;resizePanel(panelResize.w+e.clientX-panelResize.x,panelResize.h+e.clientY-panelResize.y);e.preventDefault();};
    const sizeUp=e=>{if(panelResize&&panelResize.id===e.pointerId)endPanelResize();};
    const sizeKey=e=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(!delta)return;e.preventDefault();const size=fullActive()?panelBox:panelSize,step=e.shiftKey?32:8;resizePanel(size.w+delta[0]*step,size.h+delta[1]*step);};
    function endDrag(){
      const prior=drag;drag=null;
      if(prior&&prior.captured&&graph.releasePointerCapture){try{graph.releasePointerCapture(prior.id);}catch(_){}}
      graph.classList.remove('dragging');
    }
    // 只在确实拖动后捕获，普通点击节点仍保留原目标和阅读行为。
    const pointerDown=e=>{if(!current()||e.button!==0)return;const node=e.target&&e.target.closest&&e.target.closest('[data-gmap-node],[data-gmap-toggle]');if(mode!=='model3d'&&node&&(node.hasAttribute('data-gmap-node')||node.hasAttribute('data-gmap-toggle')))return;drag={kind:mode==='model3d'?'rotate':'pan',id:e.pointerId,x:e.clientX,y:e.clientY,moved:false,captured:false};};
    const pointerMove=e=>{if(!drag||drag.id!==e.pointerId||!current())return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(!dx&&!dy)return;
      if(!drag.moved&&Math.abs(dx)+Math.abs(dy)<=3)return;
      drag.moved=true;if(!drag.captured&&graph.setPointerCapture){try{graph.setPointerCapture(e.pointerId);drag.captured=true;}catch(_){}}graph.classList.add('dragging');
      if(drag.kind==='rotate')camera=rotateCamera(camera,dx,dy);else pan={x:Math.max(-10000,Math.min(10000,pan.x+dx)),y:Math.max(-10000,Math.min(10000,pan.y+dy))};drag.x=e.clientX;drag.y=e.clientY;render();if(e.preventDefault)e.preventDefault();};
    const pointerUp=e=>{if(!drag||drag.id!==e.pointerId)return;if(drag.moved)suppressClickUntil=Date.now()+250;endDrag();};
    const wheel=e=>{
      if(!current()||!wheelCanvas()||!Number.isFinite(e.deltaY)||!e.deltaY)return;
      if(e.preventDefault)e.preventDefault();if(e.stopPropagation)e.stopPropagation();
      const rect=graph.getBoundingClientRect?graph.getBoundingClientRect():{left:0,top:0},unit=e.deltaMode===1?16:e.deltaMode===2?(graph.clientHeight||400):1,delta=Math.max(-240,Math.min(240,e.deltaY*unit));
      const anchor={x:Number.isFinite(e.clientX)?e.clientX-rect.left-(graph.clientLeft||0):(graph.clientWidth||0)/2,y:Number.isFinite(e.clientY)?e.clientY-rect.top-(graph.clientTop||0):(graph.clientHeight||0)/2};
      setZoom(zoom*Math.exp(-delta*.002),anchor);
    };
    host.addEventListener('click',click);host.addEventListener('input',input);host.addEventListener('keydown',key);
    graph.addEventListener('wheel',wheel,{passive:false});graph.addEventListener('pointerdown',pointerDown);graph.addEventListener('pointermove',pointerMove);graph.addEventListener('pointerup',pointerUp);graph.addEventListener('pointercancel',pointerUp);graph.addEventListener('lostpointercapture',pointerUp);
    readHandle.addEventListener('pointerdown',panelDown);readHandle.addEventListener('pointermove',panelMove);readHandle.addEventListener('pointerup',panelUp);readHandle.addEventListener('pointercancel',panelUp);readHandle.addEventListener('lostpointercapture',panelUp);readHandle.addEventListener('dblclick',panelReset);readHandle.addEventListener('keydown',panelKey);
    sizeHandle.addEventListener('pointerdown',sizeDown);sizeHandle.addEventListener('pointermove',sizeMove);sizeHandle.addEventListener('pointerup',sizeUp);sizeHandle.addEventListener('pointercancel',sizeUp);sizeHandle.addEventListener('lostpointercapture',sizeUp);sizeHandle.addEventListener('keydown',sizeKey);
    if(doc){doc.addEventListener('keydown',escapeKey);doc.addEventListener('fullscreenchange',syncFull);}
    const leave=()=>{if(!current())ctl.destroy();},pageLeave=()=>ctl.destroy();
    if(win){win.addEventListener('research-overview-mode',modeChange);win.addEventListener('hashchange',leave);win.addEventListener('pagehide',pageLeave);win.addEventListener('resize',applyPanel);}
    const ctl={update(next,helpers){
      if(!live)return ctl;
      const prior=model&&model.projectRoot,priorKind=model&&model.kind,priorScope=model&&model.scope;opts=next||opts;help=helpers||help;model=build(opts.kind,opts.data,opts);++revision;reader.invalidate();
      component.classList[wheelCanvas()?'add':'remove']('gmap-wheel-canvas');
      if(heightHandle){const adjustable=['blueprint','archives'].includes(model.kind);heightHandle.hidden=!adjustable;component.classList[adjustable?'add':'remove']('gmap-height-adjustable');
        if(adjustable){if(!heightControl)heightControl=mountHeightControl({target:canvasLayout,handle:heightHandle,projectRoot:model.projectRoot,scope:model.kind+':'+model.scope,isFullscreen:fullActive,isCurrent:current,onResize:applyPanel});else heightControl.update(model.projectRoot,model.kind+':'+model.scope);}
        else if(heightControl){heightControl.destroy();heightControl=null;canvasLayout.style.removeProperty&&canvasLayout.style.removeProperty('--overview-frame-height');delete canvasLayout.dataset.overviewSized;}
      }
      if(prior!==model.projectRoot||priorKind!==model.kind||priorScope!==model.scope){worldInitialFit=true;selected='';focus='';query='';limit=8;zoom=1;camera=defaultCamera();pan={x:0,y:0};endDrag();endPanelResize();panelSize={w:330,h:420};panelSized=false;canvasLayout.style.gridTemplateColumns='';readPanel.style.maxHeight='';readPanel.style.height='';preference=null;expanded=new Set(model.nodes.filter(n=>n.kind==='project').map(n=>n.id));animated=new Set();motion=true;panelBox=null;host.querySelector('.gmap-search').value='';if(prior!==undefined)exitFull();}
      if(help.overviewMode){const nextMode=normalizeMode(help.overviewMode());if(nextMode!==preference){preference=nextMode;mode=nextMode;}}
      if(!model.nodes.some(n=>n.id===selected))selected='';if(!model.nodes.some(n=>n.id===focus))focus='';
      expanded=new Set([...expanded].filter(key=>model.nodes.some(n=>n.id===key)));
      render();const chosen=model.nodes.find(n=>n.id===selected);
      if(chosen)reader.select(chosen);else writeReading('<p class="hint">'+label(['选择节点查看记录，选择文件在此阅读','Select a node for records or a file to read here'])+'</p>',false);
      return ctl;
    },state(){return {mode,zoom,camera:{...camera},pan:{...pan},selected,focus,query,limit,expanded:[...expanded],motion,panelSize:{...panelSize},panelBox:panelBox&&{...panelBox},frameHeight:heightControl&&heightControl.state().height,fullscreen:fullActive(),live};},destroy(){
      if(!live)return;live=false;reader.destroy();exitFull();endDrag();endPanelDrag();endPanelResize();host.removeEventListener('click',click);host.removeEventListener('input',input);host.removeEventListener('keydown',key);
      if(heightControl){heightControl.destroy();heightControl=null;}
      graph.removeEventListener('wheel',wheel);graph.removeEventListener('pointerdown',pointerDown);graph.removeEventListener('pointermove',pointerMove);graph.removeEventListener('pointerup',pointerUp);graph.removeEventListener('pointercancel',pointerUp);graph.removeEventListener('lostpointercapture',pointerUp);
      readHandle.removeEventListener('pointerdown',panelDown);readHandle.removeEventListener('pointermove',panelMove);readHandle.removeEventListener('pointerup',panelUp);readHandle.removeEventListener('pointercancel',panelUp);readHandle.removeEventListener('lostpointercapture',panelUp);readHandle.removeEventListener('dblclick',panelReset);readHandle.removeEventListener('keydown',panelKey);
      sizeHandle.removeEventListener('pointerdown',sizeDown);sizeHandle.removeEventListener('pointermove',sizeMove);sizeHandle.removeEventListener('pointerup',sizeUp);sizeHandle.removeEventListener('pointercancel',sizeUp);sizeHandle.removeEventListener('lostpointercapture',sizeUp);sizeHandle.removeEventListener('keydown',sizeKey);
      if(doc){doc.removeEventListener('keydown',escapeKey);doc.removeEventListener('fullscreenchange',syncFull);}
      if(win){win.removeEventListener('research-overview-mode',modeChange);win.removeEventListener('hashchange',leave);win.removeEventListener('pagehide',pageLeave);win.removeEventListener('resize',applyPanel);}
      mounted.delete(host);
    }};
    mounted.set(host,ctl);ctl.update(opts,help);return ctl;
  }
  return {build,visible,mindParents,mindVisible,worldVisible,worldLayout,clampPanel,previewURL,createReader,normalizeMode,zoomLevel,shortLabel,project3D,rotateCamera,layout,mount,mountHeightControl};
})();
if (typeof window !== 'undefined') window.GovMap=GovMap;
if (typeof module !== 'undefined' && module.exports) module.exports=GovMap;
