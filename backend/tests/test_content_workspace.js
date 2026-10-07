'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const code=fs.readFileSync(path.resolve(__dirname,'../../内容工作台.js'),'utf8');
class Node {
  constructor(){this.isConnected=true;this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.classList={toggle(){}};this.dataset={};this.nodes=new Map();}
  set innerHTML(value){this.html=value;for(const match of value.matchAll(/\b(data-cw-[a-z-]+)(?:\s+[^>]*?)?(?:>|\s)/g)){const key='['+match[1]+']';if(!this.nodes.has(key))this.nodes.set(key,new Node());}for(const attr of ['path','reason','create-path']){const m=value.match(new RegExp('data-cw-'+attr+' value="([^"]*)"'));if(m&&this.nodes.has('[data-cw-'+attr+']'))this.nodes.get('[data-cw-'+attr+']').value=m[1];}}
  get innerHTML(){return this.html;}
  querySelector(selector){for(const child of this.nodes.values())if(child.nodes.has(selector))return child.nodes.get(selector);return this.nodes.get(selector)||null;}
  addEventListener(type,fn){(this.listeners||(this.listeners=new Map())).set(type,fn);}removeEventListener(type,fn){if(this.listeners&&this.listeners.get(type)===fn)this.listeners.delete(type);}focus(){}scrollIntoView(){}contains(){return true;}
}
function fixture(handler,module='论文',overrides={}){
  const host=new Node(),memory=new Map(),storage={getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)};
  const ctx={Map,JSON,String,Object,encodeURIComponent,sessionStorage:storage};ctx.window=ctx;vm.runInNewContext(code,ctx);
  let active=true;
  const root='C:/fixture/one',workspace={module,project_root:root,config_file:'工作台/工作台.json',problems:[],sections:[{id:'intro',title:'引言',en:'Introduction',kind:'documents',folder:'正文/引言',templates:[],files:[]}]};
  const calls=[];
  const opts={module,projectRoot:root,storage,isCurrent:()=>active,language:()=>'zh',api:async(method,url,body)=>{calls.push({method,url,body});return handler?handler(method,url,body,workspace):method==='GET'&&url.endsWith('/论文')?workspace:{module,project_root:root,path:'正文/引言/a.md',text:'old',revision:'1'.repeat(64),editable:true};}};
  // The production URL percent-encodes module names.
  const original=opts.api;opts.api=(method,url,body)=>url==='api/content/'+encodeURIComponent(module)?Promise.resolve(workspace):original(method,url,body);
  Object.assign(opts,overrides);
  const ctl=ctx.ContentWorkspace.mount(host,opts);
  return {ctx,host,ctl,opts,calls,storage,workspace,leave(){active=false;}};
}
test('opening is a single read and does not dispatch or execute',async()=>{const f=fixture();await f.ctl.ready;assert.match(f.host.querySelector('[data-cw-sections]').innerHTML,/引言/);assert.equal(f.ctl.isDirty(),false);assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);});
test('saving binds project and exact original revision; draft survives conflict',async()=>{
 const f=fixture(async(method,url,body,w)=>{if(method==='POST'){const e=new Error('changed');e.status=409;throw e;}return {module:w.module,project_root:w.project_root,path:'正文/引言/a.md',text:'old',revision:'a'.repeat(64),editable:true};});
 await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);f.host.querySelector('[data-cw-text]').value='my change';await f.ctl.save();
 const save=f.calls.find(x=>x.method==='POST');assert.equal(save.body.project_root,'C:/fixture/one');assert.equal(save.body.revision,'a'.repeat(64));assert.equal(save.body.text,'my change');assert.equal(f.ctl.snapshot().editor.text,'my change');assert.match(f.host.querySelector('[data-cw-message]').textContent,/输入已保留/);assert.equal(f.ctl.isDirty(),true);
});
test('navigation during document read discards stale response',async()=>{
 let resolve;const f=fixture(()=>new Promise(r=>resolve=r));await f.ctl.ready;const pending=f.ctl.edit('正文/引言/a.md',false);f.leave();resolve({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/a.md',text:'old',revision:'a'.repeat(64),editable:true});await pending;assert.equal(f.ctl.snapshot().editor,null);
});
test('wrong project response cannot become editable content',async()=>{const f=fixture(()=>({module:'论文',project_root:'C:/fixture/two',path:'正文/引言/a.md',text:'foreign',revision:'a'.repeat(64),editable:true}));await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);assert.equal(f.ctl.snapshot().editor,null);assert.match(f.host.querySelector('[data-cw-message]').textContent,/项目不一致/);});
test('same project document draft restores with old revision instead of silently rebasing',async()=>{
 const f=fixture();await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);f.host.querySelector('[data-cw-text]').value='retained';f.ctl.destroy();
 const next=f.ctx.ContentWorkspace.mount(new Node(),Object.assign({},f.opts,{api:async(method,url)=>url.endsWith('/document?path='+encodeURIComponent('正文/引言/a.md'))?{module:'论文',project_root:'C:/fixture/one',path:'正文/引言/a.md',text:'newer',revision:'2'.repeat(64),editable:true}:f.workspace}));await next.ready;await next.edit('正文/引言/a.md',false);assert.equal(next.snapshot().editor.text,'retained');assert.equal(next.snapshot().editor.revision,'1'.repeat(64));assert.equal(next.isDirty(),true);
});
test('dirty editor prevents automatic refresh from replacing inputs',async()=>{const f=fixture();await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);f.host.querySelector('[data-cw-text]').value='unsaved';const n=f.calls.length;await f.ctl.refresh();assert.equal(f.calls.length,n);assert.equal(f.ctl.snapshot().editor.text,'unsaved');});
test('compare reads latest without changing retained text or original revision',async()=>{let n=0;const f=fixture(()=>({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/a.md',text:++n===1?'old':'newer',revision:n===1?'1'.repeat(64):'2'.repeat(64),editable:true}));await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);f.host.querySelector('[data-cw-text]').value='mine';await f.ctl.compareLatest();const e=f.ctl.snapshot().editor;assert.equal(e.text,'mine');assert.equal(e.revision,'1'.repeat(64));assert.equal(e.latest.revision,'2'.repeat(64));assert.equal(f.host.querySelector('[data-cw-latest-text]').textContent,'newer');});
test('new document uses empty revision and successful save drops its draft',async()=>{const f=fixture((method,url,body)=>({module:'论文',project_root:'C:/fixture/one',path:body.path,text:body.text,revision:'3'.repeat(64),editable:true}));await f.ctl.ready;await f.ctl.edit('正文/引言/new.md',true);f.host.querySelector('[data-cw-text]').value='new';await f.ctl.save();assert.equal(f.calls.find(x=>x.method==='POST').body.revision,'');assert.equal(f.ctl.snapshot().editor,null);});

function click(host,attr,value){
 const dataset={};if(value!==undefined)dataset[attr.replace(/^data-/,'').replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;
 const target={dataset,closest:()=>target,hasAttribute:name=>name===attr};host.listeners.get('click')({target});
}
function input(host,attr,value,type='input'){
 const target=host.querySelector('['+attr+']');target.value=value;target.matches=selector=>selector.split(',').includes('['+attr+']');host.listeners.get(type)({target});
}
async function settled(ctl){for(let i=0;i<20&&ctl.isBusy();i++)await Promise.resolve();assert.equal(ctl.isBusy(),false);}
function reMount(f,overrides){const host=new Node(),ctl=f.ctx.ContentWorkspace.mount(host,Object.assign({},f.opts,overrides));return {host,ctl};}

test('typing during save keeps newer text and rebases only to the saved submission',async()=>{
 let resolve;const f=fixture((method,url,body,w)=>method==='POST'?new Promise(r=>resolve=r):({module:w.module,project_root:w.project_root,path:'正文/引言/a.md',text:'old',revision:'1'.repeat(64),editable:true}));
 await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);input(f.host,'data-cw-text','submitted');const saving=f.ctl.save();
 input(f.host,'data-cw-text','typed after submission');resolve({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/a.md',revision:'3'.repeat(64)});await saving;
 const e=f.ctl.snapshot().editor;assert.equal(e.text,'typed after submission');assert.equal(e.original,'submitted');assert.equal(e.revision,'3'.repeat(64));assert.equal(f.ctl.isDirty(),true);
 assert.equal(f.calls.find(x=>x.method==='POST').body.text,'submitted');assert.match(f.host.querySelector('[data-cw-message]').textContent,/后续输入仍未保存/);
 f.ctl.destroy();const next=reMount(f);await next.ctl.ready;await next.ctl.edit('正文/引言/a.md',false);assert.equal(next.ctl.snapshot().editor.text,'typed after submission');assert.equal(next.ctl.snapshot().editor.revision,'3'.repeat(64));
});

test('a reason edited during save remains dirty and the next save uses the successful revision',async()=>{
 let resolve,n=0;const f=fixture((method,url,body,w)=>method==='POST'?(++n===1?new Promise(r=>resolve=r):{module:w.module,project_root:w.project_root,path:body.path,revision:'4'.repeat(64)}):{module:w.module,project_root:w.project_root,path:'正文/引言/a.md',text:'old',revision:'1'.repeat(64),editable:true});
 await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);input(f.host,'data-cw-text','submitted');input(f.host,'data-cw-reason','first reason');const saving=f.ctl.save();input(f.host,'data-cw-reason','newer reason');
 resolve({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/a.md',revision:'3'.repeat(64)});await saving;assert.equal(f.ctl.isDirty(),true);assert.equal(f.ctl.snapshot().editor.reason,'newer reason');
 await f.ctl.save();const posts=f.calls.filter(x=>x.method==='POST');assert.equal(posts[0].body.reason,'first reason');assert.equal(posts[1].body.reason,'newer reason');assert.equal(posts[1].body.revision,'3'.repeat(64));assert.equal(f.ctl.snapshot().editor,null);
});

test('new file becomes existing after save while retaining text entered during the request',async()=>{
 let resolve;const f=fixture((method,url,body)=>new Promise(r=>resolve=r));await f.ctl.ready;await f.ctl.edit('正文/引言/new.md',true);input(f.host,'data-cw-text','submitted');const saving=f.ctl.save();input(f.host,'data-cw-text','newer');
 resolve({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/new.md',revision:'3'.repeat(64)});await saving;const e=f.ctl.snapshot().editor;assert.equal(e.isNew,false);assert.equal(e.original,'submitted');assert.equal(e.text,'newer');assert.equal(e.revision,'3'.repeat(64));
 assert.match(f.host.querySelector('[data-cw-editor]').innerHTML,/data-cw-path[^>]+readonly/);assert.match(f.host.querySelector('[data-cw-editor]').innerHTML,/data-cw-latest/);
});

test('changing a new path during save keeps the second path new and does not attach its draft to the saved file',async()=>{
 let resolve;const f=fixture((method,url,body)=>new Promise(r=>resolve=r));await f.ctl.ready;await f.ctl.edit('正文/引言/first.md',true);input(f.host,'data-cw-text','first content');const saving=f.ctl.save();input(f.host,'data-cw-path','正文/引言/second.md');input(f.host,'data-cw-text','second content');
 resolve({module:'论文',project_root:'C:/fixture/one',path:'正文/引言/first.md',revision:'3'.repeat(64)});await saving;const e=f.ctl.snapshot().editor;assert.equal(e.path,'正文/引言/second.md');assert.equal(e.isNew,true);assert.equal(e.revision,'');assert.equal(e.original,'');
 const firstKey='content-draft:'+JSON.stringify(['c:/fixture/one','论文','正文/引言/first.md']),secondKey='content-draft:'+JSON.stringify(['c:/fixture/one','论文','正文/引言/second.md']);assert.equal(f.storage.getItem(firstKey),null);assert.equal(JSON.parse(f.storage.getItem(secondKey)).text,'second content');
});

test('renaming an unsaved new file immediately moves its draft before navigation',async()=>{
 const f=fixture();await f.ctl.ready;await f.ctl.edit('正文/引言/first.md',true);input(f.host,'data-cw-text','only second');input(f.host,'data-cw-path','正文/引言/second.md');f.ctl.destroy();
 const firstKey='content-draft:'+JSON.stringify(['c:/fixture/one','论文','正文/引言/first.md']);assert.equal(f.storage.getItem(firstKey),null);
 const next=reMount(f);await next.ctl.ready;await next.ctl.edit('正文/引言/second.md',true);assert.equal(next.ctl.snapshot().editor.text,'only second');assert.equal(next.ctl.snapshot().editor.path,'正文/引言/second.md');
});

test('new-file preparation blocks refresh and survives leaving the module until explicitly canceled',async()=>{
 const f=fixture();await f.ctl.ready;f.workspace.sections[0].templates=[{path:'工作台/模板/引言.md',name:'引言'}];click(f.host,'data-cw-new','intro');input(f.host,'data-cw-template','工作台/模板/引言.md','change');input(f.host,'data-cw-create-path','正文/引言/自定义.md');
 const form=f.host.querySelector('[data-cw-editor]').innerHTML;await f.ctl.refresh();assert.equal(f.ctl.isDirty(),true);assert.equal(f.host.querySelector('[data-cw-editor]').innerHTML,form);
 f.ctl.destroy();const next=reMount(f);await next.ctl.ready;assert.equal(next.ctl.snapshot().preparing.template,'工作台/模板/引言.md');assert.equal(next.host.querySelector('[data-cw-create-path]').value,'正文/引言/自定义.md');assert.equal(next.ctl.isDirty(),true);
 click(next.host,'data-cw-cancel');assert.equal(next.ctl.isDirty(),false);next.ctl.destroy();const clean=reMount(f);await clean.ctl.ready;assert.equal(clean.ctl.snapshot().preparing,null);
});

test('opening preparation from a clean editor transfers draft capture to the new form',async()=>{
 const f=fixture();await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);assert.equal(f.ctl.isDirty(),false);click(f.host,'data-cw-new','intro');input(f.host,'data-cw-create-path','正文/引言/from-clean.md');assert.equal(f.ctl.snapshot().editor,null);f.ctl.destroy();
 const next=reMount(f);await next.ctl.ready;assert.equal(next.ctl.snapshot().preparing.path,'正文/引言/from-clean.md');assert.equal(next.ctl.isDirty(),true);
});

test('prepared file is isolated by project root even when both projects have the same module and section',async()=>{
 const f=fixture();await f.ctl.ready;click(f.host,'data-cw-new','intro');input(f.host,'data-cw-create-path','正文/引言/项目一.md');f.ctl.destroy();
 const w=JSON.parse(JSON.stringify(f.workspace));w.project_root='C:/fixture/two';const other=reMount(f,{projectRoot:w.project_root,api:async()=>w});await other.ctl.ready;assert.equal(other.ctl.snapshot().preparing,null);assert.equal(other.ctl.isDirty(),false);
 const same=reMount(f,{projectRoot:'C:\\fixture\\ONE\\'});await same.ctl.ready;assert.equal(same.ctl.snapshot().preparing.path,'正文/引言/项目一.md');
});

test('template selection uses its real extension while preserving a manually chosen path',async()=>{
 const f=fixture();await f.ctl.ready;f.workspace.sections[0].templates=[{path:'工作台/模板/检查脚本.py',name:'检查脚本'},{path:'工作台/模板/样板.csv',name:'样板'}];click(f.host,'data-cw-new','intro');
 input(f.host,'data-cw-template','工作台/模板/检查脚本.py','change');assert.equal(f.host.querySelector('[data-cw-create-path]').value,'正文/引言/检查脚本.py');
 input(f.host,'data-cw-template','工作台/模板/样板.csv','change');assert.equal(f.host.querySelector('[data-cw-create-path]').value,'正文/引言/样板.csv');
 input(f.host,'data-cw-create-path','正文/引言/my-file.py');input(f.host,'data-cw-template','工作台/模板/检查脚本.py','change');assert.equal(f.host.querySelector('[data-cw-create-path]').value,'正文/引言/my-file.py');
});

test('a template response with another path is refused without losing the prepared selection',async()=>{
 const f=fixture((method,url,body,w)=>({module:w.module,project_root:w.project_root,path:'工作台/模板/别的.md',text:'foreign template',revision:'1'.repeat(64),editable:false}));await f.ctl.ready;
 f.workspace.sections[0].templates=[{path:'工作台/模板/引言.md',name:'引言'}];click(f.host,'data-cw-new','intro');input(f.host,'data-cw-template','工作台/模板/引言.md','change');click(f.host,'data-cw-create');await settled(f.ctl);
 assert.equal(f.ctl.snapshot().editor,null);assert.equal(f.ctl.snapshot().preparing.template,'工作台/模板/引言.md');assert.match(f.host.querySelector('[data-cw-message]').textContent,/路径不匹配/);assert.equal(f.ctl.isDirty(),true);
});

test('a valid prepared template becomes an editable new copy rather than modifying the template',async()=>{
 const f=fixture((method,url,body,w)=>({module:w.module,project_root:w.project_root,path:'工作台/模板/检查脚本.py',text:'print("check")',revision:'1'.repeat(64),editable:false}));await f.ctl.ready;f.workspace.sections[0].templates=[{path:'工作台/模板/检查脚本.py',name:'检查脚本'}];
 click(f.host,'data-cw-new','intro');input(f.host,'data-cw-template','工作台/模板/检查脚本.py','change');click(f.host,'data-cw-create');await settled(f.ctl);const e=f.ctl.snapshot().editor;
 assert.equal(e.path,'正文/引言/检查脚本.py');assert.equal(e.text,'print("check")');assert.equal(e.isNew,true);assert.equal(e.revision,'');assert.equal(f.ctl.snapshot().preparing,null);assert.equal(f.calls.filter(x=>x.method==='POST').length,0);
});

test('a removed prepared template is shown as unavailable and cannot start until deliberately changed',async()=>{
 const f=fixture();await f.ctl.ready;f.workspace.sections[0].templates=[{path:'工作台/模板/引言.md',name:'引言'}];click(f.host,'data-cw-new','intro');input(f.host,'data-cw-template','工作台/模板/引言.md','change');f.ctl.destroy();f.workspace.sections[0].templates=[];
 const next=reMount(f);await next.ctl.ready;assert.equal(next.host.querySelector('[data-cw-create]').disabled,true);assert.match(next.host.querySelector('[data-cw-message]').textContent,/已不可用/);click(next.host,'data-cw-create');assert.equal(next.ctl.snapshot().editor,null);
 input(next.host,'data-cw-template','','change');assert.equal(next.host.querySelector('[data-cw-create]').disabled,false);click(next.host,'data-cw-create');await settled(next.ctl);assert.equal(next.ctl.snapshot().editor.isNew,true);
});

test('unconfirmed original is distinguished from missing or unlinked original in both languages',async()=>{
 const f=fixture();await f.ctl.ready;f.workspace.sections[0].files=[{name:'example',path:'解读/示例.md',original_unconfirmed:true}];await f.ctl.refresh();const zh=f.host.querySelector('[data-cw-sections]').innerHTML;assert.match(zh,/原文未确认/);assert.doesNotMatch(zh,/缺原文|未关联原文/);
 const en=reMount(f,{language:()=>'en'});await en.ctl.ready;assert.match(en.host.querySelector('[data-cw-sections]').innerHTML,/Original unconfirmed/);
});


test('PPT uses its two configured folders and English presentation heading',async()=>{
 const f=fixture(undefined,'PPT',{language:()=> 'en'});
 const config=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../资料/PPT/工作台/工作台.json'),'utf8'));
 f.workspace.sections=config.sections.map(s=>({...s,files:[]}));await f.ctl.ready;
 assert.match(f.host.innerHTML,/cw-presentation/);assert.match(f.host.innerHTML,/Presentation workspace/);
 assert.deepEqual(f.workspace.sections.map(s=>s.folder),['材料','导出']);
 for(const s of config.sections)assert.match(f.host.querySelector('[data-cw-sections]').innerHTML,new RegExp(s.en));
 assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);
});
test('a real read-only module skill entry opens its declared module without writing',async()=>{
 const opened=[],f=fixture(undefined,'论文',{openSkills:m=>opened.push(m)});
 f.workspace.skill_entry={path:'技能/SKILL.md',name:'论文技能',en:'Paper skills',readonly:true,available:true};await f.ctl.ready;
 assert.match(f.host.querySelector('[data-cw-skills-wrap]').innerHTML,/论文技能/);
 click(f.host,'data-cw-skills');assert.deepEqual(opened,['论文']);assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);
});
test('a missing skill entry reports the gap and cannot open or create it',async()=>{
 const opened=[],f=fixture(undefined,'PPT',{openSkills:m=>opened.push(m)});
 f.workspace.skill_entry={path:'技能/SKILL.md',name:'PPT技能',readonly:true,available:false};await f.ctl.ready;
 assert.match(f.host.querySelector('[data-cw-skills-wrap]').innerHTML,/disabled/);assert.match(f.host.querySelector('[data-cw-skills-wrap]').innerHTML,/缺入口/);
 click(f.host,'data-cw-skills');assert.deepEqual(opened,[]);assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);
});
test('a foreign or writable skill shortcut is never promoted into a module entry',async()=>{
 for(const entry of [{path:'../其他/技能/SKILL.md',readonly:true,available:true},{path:'技能/SKILL.md',readonly:false,available:true}]){
  const opened=[],f=fixture(undefined,'PPT',{openSkills:m=>opened.push(m)});f.workspace.skill_entry=entry;await f.ctl.ready;
  assert.equal(f.host.querySelector('[data-cw-skills-wrap]').innerHTML,'');click(f.host,'data-cw-skills');assert.deepEqual(opened,[]);
 }
});
test('following a skill shortcut preserves the current document draft',async()=>{
 const opened=[],f=fixture(undefined,'论文',{openSkills:m=>opened.push(m)});
 f.workspace.skill_entry={path:'技能/SKILL.md',name:'论文技能',readonly:true,available:true};await f.ctl.ready;await f.ctl.edit('正文/引言/a.md',false);
 input(f.host,'data-cw-text','尚未保存的写作');click(f.host,'data-cw-skills');assert.deepEqual(opened,['论文']);
 f.ctl.destroy();const next=reMount(f);await next.ctl.ready;await next.ctl.edit('正文/引言/a.md',false);assert.equal(next.ctl.snapshot().editor.text,'尚未保存的写作');
 assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);
});

test('literature hides the legacy dedicated-notes card without changing its records',async()=>{
 const f=fixture(null,'文献');await f.ctl.ready;
 f.workspace.sections=[['downloads','下载列表'],['reading','精读'],['originals','原文'],['notes','专属笔记']].map(([kind,title])=>({id:kind,kind,title,folder:'',files:[],templates:[]}));
 const before=JSON.stringify(f.workspace);await f.ctl.refresh();
 const html=f.host.querySelector('[data-cw-sections]').innerHTML;
 for(const title of ['下载列表','精读','原文'])assert.ok(html.includes(title));
 assert.ok(!html.includes('专属笔记'));assert.equal(JSON.stringify(f.workspace),before);assert.equal(f.calls.filter(x=>x.method!=='GET').length,0);
});

test('legacy literature notes deep link falls back to the three current sections',async()=>{
 const f=fixture(null,'文献',{section:'notes'});await f.ctl.ready;
 f.workspace.sections=[['downloads','下载列表'],['reading','精读'],['originals','原文'],['notes','专属笔记']].map(([kind,title])=>({id:kind,kind,title,files:[]}));
 await f.ctl.refresh();const html=f.host.querySelector('[data-cw-sections]').innerHTML;
 for(const title of ['下载列表','精读','原文'])assert.ok(html.includes(title));assert.ok(!html.includes('专属笔记'));
});
