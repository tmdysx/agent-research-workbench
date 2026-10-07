'use strict';
// Execute production controllers in a DOM VM. Browser layout is checked separately.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.resolve(__dirname,'../../小窗.js'),'utf8');
class Element{
  constructor(tag='div'){this.nodeType=1;this.tagName=tag.toUpperCase();this.children=[];this.parentNode=null;this.attributes=new Map();this.classes=new Set();this.style={setProperty(k,v){this[k]=v;},removeProperty(k){delete this[k];}};this.hidden=false;this.scrollTop=0;this.scrollLeft=0;this.value='';this.textContent='';this.events=new Map();this.box={left:0,top:0,width:400,height:550};this.classList={contains:k=>this.classes.has(k),toggle:(k,on)=>{if(on===undefined)on=!this.classes.has(k);on?this.classes.add(k):this.classes.delete(k);},add:k=>this.classes.add(k),remove:k=>this.classes.delete(k)};}
  set className(v){this.classes=new Set(v.split(/\s+/).filter(Boolean));}
  get className(){return [...this.classes].join(' ');}
  get parentElement(){return this.parentNode&&this.parentNode.nodeType===1?this.parentNode:null;}
  get isConnected(){let n=this;while(n.parentNode)n=n.parentNode;return n.connectedRoot===true;}
  appendChild(n){n.remove();n.parentNode=this;this.children.push(n);return n;}
  remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this);this.parentNode=null;}
  contains(n){return n===this||this.children.some(c=>c.contains(n));}
  matches(selector){return selector.split(',').some(s=>{s=s.trim();return s==='*'||s.startsWith('.')&&this.classes.has(s.slice(1))||s.startsWith('#')&&this.id===s.slice(1);});}
  closest(s){return this.matches(s)?this:this.parentElement&&this.parentElement.closest(s);}
  querySelectorAll(s){const out=[];for(const c of this.children){if(c.matches(s))out.push(c);out.push(...c.querySelectorAll(s));}return out;}
  querySelector(s){return this.querySelectorAll(s)[0]||null;}
  setAttribute(n,v){this.attributes.set(n,v);}
  getAttribute(n){return this.attributes.get(n)||null;}
  addEventListener(n,f){if(!this.events.has(n))this.events.set(n,new Set());this.events.get(n).add(f);}
  removeEventListener(n,f){if(this.events.has(n))this.events.get(n).delete(f);}
  dispatchEvent(e){if(!e.target)e.target=this;for(const f of this.events.get(e.type)||[])f(e);if(e.bubbles&&!e.stopped&&this.parentNode)this.parentNode.dispatchEvent(e);return true;}
  click(){this.dispatchEvent({type:'click',preventDefault(){},stopPropagation(){this.stopped=true;},bubbles:true});}
  focus(){this.ownerDocument.activeElement=this;}
  getBoundingClientRect(){const w=parseFloat(this.style['--ps-pane-width']||this.style.width)||this.box.width,h=parseFloat(this.style['--ps-pane-height']||this.style.height)||this.box.height;return {...this.box,width:this.hidden?0:w,height:this.hidden?0:h};}
}
function fixture(){
  const html=new Element('html');html.connectedRoot=true;const head=new Element('head'),body=new Element('body');html.appendChild(head);html.appendChild(body);
  const document={documentElement:html,head,body,readyState:'complete',fullscreenElement:null,activeElement:null,events:new Map(),createElement(tag){const n=new Element(tag);n.ownerDocument=document;return n;},querySelectorAll:s=>html.querySelectorAll(s),getElementById:id=>html.querySelector('#'+id),addEventListener:Element.prototype.addEventListener,removeEventListener:Element.prototype.removeEventListener,dispatchEvent:Element.prototype.dispatchEvent};
  head.ownerDocument=body.ownerDocument=html.ownerDocument=document;let project='C:/temporary/project-a',language='zh';const storage=new Map(),events=new Map(),microtasks=[],observers=[],external=[];
  class MutationObserver{constructor(callback){this.callback=callback;this.disconnected=false;observers.push(this);}observe(target,options){this.target=target;this.options=options;}disconnect(){this.disconnected=true;}deliver(records){if(!this.disconnected)this.callback(records);}}
  class CustomEvent{constructor(type,options){this.type=type;Object.assign(this,options);}}
  const window={document,location:{hash:'#/auto'},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},researchCurrentProjectRoot:()=>project,getLang:()=>language,MutationObserver,CustomEvent,queueMicrotask:f=>microtasks.push(f),getComputedStyle:n=>({position:n.style.position|| (n.classList.contains('ps-position-host')?'relative':'static'),display:n.hidden?'none':n.style.display||'block',visibility:n.classList.contains('ps-pane-collapsed')?'hidden':n.style.visibility||'visible'}),addEventListener(n,f){if(!events.has(n))events.set(n,new Set());events.get(n).add(f);},removeEventListener(n,f){if(events.has(n))events.get(n).delete(f);},fetch(...args){external.push(args);throw new Error('Network forbidden');},api(...args){external.push(args);throw new Error('Dispatch forbidden');}};
  vm.runInNewContext(source,{window,console,Promise,Set,Map,WeakSet,Array,String,JSON,encodeURI});
  function el(tag,cls,parent){const n=document.createElement(tag);n.className=cls||'';if(parent)parent.appendChild(n);return n;}
  function pane(kind='ad-aside',layout='ad-scene'){const parent=el('div',layout,body),p=el('aside',kind,parent);parent.box.width=1200;const input=el('input','',p);input.value='人的未保存输入';const scroll=el('section','',p);scroll.scrollTop=153;scroll.scrollLeft=21;const frame=el('iframe','',p);frame.src='http://127.0.0.1/real-existing-window';p.style.width='440px';p.style.height='580px';p.scrollTop=17;return {parent,p,input,scroll,frame};}
  function flush(){let count=0;while(microtasks.length){assert.ok(++count<10,'observer settles instead of looping');microtasks.shift()();}return count;}
  return {window,document,storage,events,observers,external,pane,el,flush,setProject:p=>project=p,setLanguage:l=>language=l,cleanup(){window.PaneSpirit.dispose();}};
}

// Share the DOM fixture without registering the pane suite twice when another test imports it.
module.exports={fixture};
if(require.main===module){
test('collapse releases the layout column and restores the same input, scroll, size and iframe references',()=>{
  const f=fixture();try{const {parent,p,input,scroll,frame}=f.pane(),c=f.window.PaneSpirit.attach(p),width=p.style.width,height=p.style.height;let events=0;parent.addEventListener('research-pane-collapse',()=>events++);c.button.click();assert.equal(c.collapsed,true);assert.ok(parent.classList.contains('ps-layout-collapsed'));assert.ok(p.classList.contains('ps-pane-collapsed'));assert.equal(p.hidden,false);assert.equal(c.token.hidden,false);assert.equal(p.style['--ps-pane-width'],'440px');assert.equal(p.style.width,width);assert.equal(p.style.height,height);assert.equal(p.children.find(n=>n.tagName==='INPUT'),input);assert.ok(p.contains(input)&&p.contains(frame));assert.equal(input.value,'人的未保存输入');scroll.scrollTop=0;c.token.click();assert.equal(events,1);assert.equal(c.collapsed,false);assert.ok(!parent.classList.contains('ps-layout-collapsed'));assert.ok(!p.classList.contains('ps-pane-collapsed'));assert.equal(scroll.scrollTop,153);assert.equal(scroll.scrollLeft,21);assert.equal(p.scrollTop,17);assert.equal(p.style.width,width);assert.equal(p.style.height,height);assert.equal(input.value,'人的未保存输入');assert.equal(p.children.find(n=>n.tagName==='IFRAME'),frame);assert.equal(frame.src,'http://127.0.0.1/real-existing-window');assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('collapse event bubbles before hiding the pane and optional owner callback executes only once',()=>{
  const f=fixture();try{const {parent,p}=f.pane();let callback=0,event=0;const c=f.window.PaneSpirit.attach(p,{onCollapse:()=>{callback++;assert.ok(!p.classList.contains('ps-pane-collapsed'));}});parent.addEventListener('research-pane-collapse',()=>{event++;assert.ok(!p.classList.contains('ps-pane-collapsed'));});assert.equal(c.collapse(),true);assert.equal(c.collapse(),false);assert.equal(callback,1);assert.equal(event,1);assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('same pane content replacement reuses the controller and reinserts its button without duplicating listeners',()=>{
  const f=fixture();try{const {p}=f.pane('cmx-side','cmx-stage'),c=f.window.PaneSpirit.attach(p);for(const child of [...p.children])child.remove();const newInput=f.el('input','',p);newInput.value='新节点的正文';f.observers[0].deliver([{type:'childList',target:p,addedNodes:[newInput],removedNodes:[c.button]}]);assert.equal(f.flush(),1);const again=f.window.PaneSpirit.attach(p);assert.equal(c,again);assert.equal(p.querySelectorAll('.ps-collapse-button').length,1);assert.equal(c.button.events.get('click').size,1);assert.equal(newInput.value,'新节点的正文');c.button.click();assert.equal(c.collapsed,true);}finally{f.cleanup();}
});
test('component hidden state is independent and the token never revives a closed pane',()=>{
  const f=fixture();try{const {p,parent}=f.pane('cmx-side','cmx-stage'),c=f.window.PaneSpirit.attach(p);c.collapse();p.hidden=true;c.sync();assert.equal(c.collapsed,true);assert.equal(c.token.hidden,true);assert.equal(p.hidden,true);assert.ok(!p.classList.contains('ps-pane-collapsed'));p.hidden=false;c.sync();assert.equal(c.token.hidden,false);assert.ok(p.classList.contains('ps-pane-collapsed'));c.restore();assert.equal(p.hidden,false);p.hidden=true;assert.equal(c.collapse(),false);assert.equal(c.token.hidden,true);assert.ok(!parent.classList.contains('ps-layout-collapsed'));}finally{f.cleanup();}
});
test('a stored collapsed preference waits for an initially closed source pane to open before hiding it',()=>{
  const f=fixture();try{const key='mh-pane-spirit:'+JSON.stringify(['C:/temporary/project-a','#/auto','cmx-side']);f.storage.set(key,'1');const {p}=f.pane('cmx-side','cmx-stage');p.hidden=true;const c=f.window.PaneSpirit.attach(p);assert.equal(c.collapsed,true);assert.equal(c.token.hidden,true);assert.ok(!p.classList.contains('ps-pane-collapsed'));p.hidden=false;c.sync();assert.equal(c.token.hidden,false);assert.equal(p.style['--ps-pane-width'],'440px');}finally{f.cleanup();}
});
test('collapse preferences isolate project, page hash and window type, and return on revisiting',()=>{
  const f=fixture();try{const {p}=f.pane(),c=f.window.PaneSpirit.attach(p);c.collapse();f.setProject('C:/temporary/project-b');c.sync();assert.equal(c.collapsed,false);f.setProject('C:/temporary/project-a');c.sync();assert.equal(c.collapsed,true);f.window.location.hash='#/m/蓝图';c.sync();assert.equal(c.collapsed,false);f.window.location.hash='#/auto';c.sync();assert.equal(c.collapsed,true);const other=f.pane('wfe-reading','wfe-scene'),d=f.window.PaneSpirit.attach(other.p);assert.equal(d.collapsed,false);}finally{f.cleanup();}
});
test('normal and fullscreen token stays inside the pane owner rather than the document body',()=>{
  const f=fixture();try{const {p,parent}=f.pane('aag-reading','aag-scene'),full=f.el('section','aag-fs',f.document.body);full.appendChild(parent);f.document.fullscreenElement=full;const c=f.window.PaneSpirit.attach(p);c.collapse();assert.ok(full.contains(c.token));assert.equal(c.token.parentNode,parent);assert.equal(c.token.hidden,false);f.document.fullscreenElement=null;c.sync();assert.equal(c.token.parentNode,parent);}finally{f.cleanup();}
});
test('owner terminal fullscreen changes during collapse use the current fullscreen container',()=>{
  const f=fixture();try{const {p,parent,frame,input}=f.pane(),terminal=f.el('section','ad-terminal',p);terminal.appendChild(frame);f.document.fullscreenElement=terminal;const c=f.window.PaneSpirit.attach(p,{onCollapse:()=>{f.document.fullscreenElement=null;}}),button=c.button;assert.equal(c.token.parentNode,terminal);assert.equal(button.parentNode,terminal);button.click();assert.equal(c.button,button);assert.equal(button.parentNode,p);assert.equal(c.token.parentNode,parent);assert.equal(c.token.hidden,false);assert.equal(terminal.isConnected,true);assert.equal(frame.parentNode,terminal);assert.equal(input.value,'人的未保存输入');assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('CSS enlarged terminal carries the same collapse button and flame, then returns both on owner exit',()=>{
  const f=fixture();try{const {p,parent,frame}=f.pane(),terminal=f.el('section','ad-terminal',p);terminal.appendChild(frame);const c=f.window.PaneSpirit.attach(p),button=c.button;assert.equal(button.parentNode,p);terminal.classList.add('ad-fs');f.observers[0].deliver([{type:'attributes',target:terminal,attributeName:'class'}]);assert.equal(f.flush(),1);assert.equal(button.parentNode,terminal);assert.equal(c.token.parentNode,terminal);p.addEventListener('research-pane-collapse',()=>{terminal.classList.remove('ad-fs');});button.click();assert.equal(c.collapsed,true);assert.equal(button.parentNode,p);assert.equal(c.token.parentNode,parent);assert.equal(c.token.hidden,false);c.token.click();assert.equal(c.collapsed,false);assert.equal(c.button,button);assert.equal(frame.parentNode,terminal);assert.equal(frame.src,'http://127.0.0.1/real-existing-window');assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('native fullscreen change moves the same button without binding another pane or opening closed children',()=>{
  const f=fixture();try{const {p}=f.pane(),terminal=f.el('section','ad-terminal',p),other=f.pane('wfe-reading','wfe-scene'),c=f.window.PaneSpirit.attach(p),d=f.window.PaneSpirit.attach(other.p),button=c.button;f.document.fullscreenElement=terminal;f.document.dispatchEvent({type:'fullscreenchange'});f.flush();assert.equal(button.parentNode,terminal);assert.equal(d.button.parentNode,other.p);assert.equal(d.token.parentNode,other.parent);f.document.fullscreenElement=null;f.document.dispatchEvent({type:'fullscreenchange'});f.flush();assert.equal(button.parentNode,p);terminal.classList.add('ad-fs');terminal.hidden=true;c.sync();assert.equal(button.parentNode,p);assert.equal(terminal.hidden,true);p.hidden=true;c.sync();assert.equal(c.collapse(),false);assert.equal(c.token.hidden,true);assert.equal(p.hidden,true);assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('language updates accessible labels without adding text to the small flame token',()=>{
  const f=fixture();try{const {p}=f.pane(),c=f.window.PaneSpirit.attach(p);assert.equal(c.token.getAttribute('aria-label'),'精气神 · 展开阅读窗口');assert.equal(c.button.textContent,'收起');f.setLanguage('en');c.sync();assert.equal(c.button.textContent,'Collapse');assert.ok(c.token.title.includes('Expand reading pane'));assert.equal(c.token.textContent,'');assert.equal(c.image.alt,'');assert.equal(c.image.draggable,false);}finally{f.cleanup();}
});
test('only local SVG paths are used and image fallback is attempted at most once',()=>{
  const f=fixture();try{const {p}=f.pane(),c=f.window.PaneSpirit.attach(p);assert.equal(c.image.src,'icons/精气神.svg');c.image.dispatchEvent({type:'error'});assert.equal(decodeURI(c.image.src),'pfiles/外观/图标/精气神.svg');const after=c.image.src;c.image.dispatchEvent({type:'error'});assert.equal(c.image.src,after);assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('removing a component disposes its controls and restores layout without leaked click listeners',()=>{
  const f=fixture();try{const {p,parent}=f.pane(),c=f.window.PaneSpirit.attach(p);c.collapse();p.remove();f.window.PaneSpirit.scan();assert.equal(c.destroyed,true);assert.equal(c.token.parentNode,null);assert.equal(c.button.parentNode,null);assert.equal(c.token.events.get('click').size,0);assert.equal(c.button.events.get('click').size,0);assert.ok(!parent.classList.contains('ps-layout-collapsed'));}finally{f.cleanup();}
});
test('explicit dispose does not silently reattach the same pane on the next automatic scan',()=>{
  const f=fixture();try{const {p}=f.pane(),c=f.window.PaneSpirit.attach(p);f.window.PaneSpirit.dispose(p);f.window.PaneSpirit.scan();assert.equal(c.destroyed,true);assert.equal(p.querySelectorAll('.ps-collapse-button').length,0);const next=f.window.PaneSpirit.attach(p);assert.notEqual(next,c);assert.equal(p.querySelectorAll('.ps-collapse-button').length,1);}finally{f.cleanup();}
});
test('mutation scans are coalesced and own controls do not schedule a self-triggering loop',()=>{
  const f=fixture();try{const {p}=f.pane(),c=f.window.PaneSpirit.attach(p),o=f.observers[0],input=f.el('input','',p);for(let i=0;i<5;i++)o.deliver([{type:'childList',target:p,addedNodes:[input],removedNodes:[]}]);assert.equal(f.flush(),1);o.deliver([{type:'childList',target:p,addedNodes:[c.button],removedNodes:[]}]);o.deliver([{type:'attributes',target:c.token,attributeName:'hidden'}]);o.deliver([{type:'childList',target:c.button,addedNodes:[],removedNodes:[]}]);assert.equal(f.flush(),0);}finally{f.cleanup();}
});
test('unrelated task graph redraws and runtime data changes are ignored by the UI observer',()=>{
  const f=fixture();try{const svg=f.el('svg','unrelated-world',f.document.body),node=f.el('g','runtime-node',svg),o=f.observers[0];o.deliver([{type:'childList',target:svg,addedNodes:[node],removedNodes:[]}]);o.deliver([{type:'attributes',target:node,attributeName:'class'}]);assert.equal(f.flush(),0);assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('all supported pane types are attached once and global dispose stops observers and page listeners',()=>{
  const f=fixture();try{for(const [kind,layout]of [['gmap-reading','gmap-layout'],['cmx-side','cmx-stage'],['ad-aside','ad-scene'],['aag-reading','aag-scene'],['wfe-reading','wfe-scene']])f.pane(kind,layout);f.window.PaneSpirit.scan();f.window.PaneSpirit.scan();assert.equal(f.document.querySelectorAll('.ps-collapse-button').length,5);assert.equal(f.document.querySelectorAll('.ps-fire').length,5);f.window.PaneSpirit.dispose();assert.equal(f.observers[0].disconnected,true);assert.equal(f.events.get('hashchange').size,0);assert.equal(f.document.events.get('fullscreenchange').size,0);assert.equal(f.document.querySelectorAll('.ps-fire').length,0);}finally{f.cleanup();}
});
test('multiple panes sharing a parent release only their own position and column controls',()=>{
  const f=fixture();try{const {p,parent}=f.pane(),second=f.el('aside','wfe-reading',parent),a=f.window.PaneSpirit.attach(p),b=f.window.PaneSpirit.attach(second);a.collapse();b.collapse();a.dispose();assert.ok(parent.classList.contains('ps-position-host'));assert.ok(parent.classList.contains('ps-layout-collapsed'));b.restore();assert.ok(!parent.classList.contains('ps-layout-collapsed'));b.dispose();assert.ok(!parent.classList.contains('ps-position-host'));}finally{f.cleanup();}
});
test('real scan activity only changes the flame state and preserves collapsed input, size and terminal identity',()=>{
  const f=fixture();try{const {p,parent,frame,input,scroll}=f.pane(),c=f.window.PaneSpirit.attach(p);c.collapse();const button=c.button,token=c.token,image=c.image,tokenParent=token.parentNode,rect=token.getBoundingClientRect(),paneWidth=p.style['--ps-pane-width'];assert.equal(f.window.PaneSpirit.scan(true),true);assert.ok(token.classList.contains('ps-scanning'));assert.ok(token.title.startsWith('正在扫描'));assert.equal(c.button,button);assert.equal(c.token,token);assert.equal(c.image,image);assert.equal(token.parentNode,tokenParent);assert.equal(tokenParent,parent);assert.deepEqual(token.getBoundingClientRect(),rect);assert.equal(p.style['--ps-pane-width'],paneWidth);assert.equal(input.value,'人的未保存输入');assert.equal(p.children.find(n=>n.tagName==='INPUT'),input);assert.ok(p.contains(input)&&p.contains(frame));assert.equal(f.window.PaneSpirit.scan(false),false);assert.ok(!token.classList.contains('ps-scanning'));assert.equal(token.title,'精气神 · 展开阅读窗口');c.restore();assert.equal(scroll.scrollTop,153);assert.equal(frame.src,'http://127.0.0.1/real-existing-window');assert.equal(f.external.length,0);}finally{f.cleanup();}
});
test('scan state survives native fullscreen moves without replacing the button or window',()=>{
  const f=fixture();try{const {p,parent,frame}=f.pane(),terminal=f.el('section','ad-terminal',p),c=f.window.PaneSpirit.attach(p);terminal.appendChild(frame);const token=c.token,button=c.button;f.window.PaneSpirit.scan(true);f.document.fullscreenElement=terminal;f.document.dispatchEvent({type:'fullscreenchange'});f.flush();assert.equal(c.token,token);assert.equal(c.button,button);assert.equal(token.parentNode,terminal);assert.ok(token.classList.contains('ps-scanning'));f.document.fullscreenElement=null;f.document.dispatchEvent({type:'fullscreenchange'});f.flush();assert.equal(token.parentNode,parent);assert.equal(button.parentNode,p);assert.equal(frame.parentNode,terminal);assert.equal(f.window.PaneSpirit.scan(),true);assert.equal(f.external.length,0);}finally{f.cleanup();}
});
function loadingHost(f){
  const host=f.el('div','',f.document.body),loading=f.el('span','ps-loading',host),text=f.el('span','ps-loading-text',loading),fires=f.el('span','ps-loading-fires',loading);
  text.textContent='Reading';for(const color of ['jade','violet','gold'])f.el('svg','ps-loading-fire ps-loading-'+color,fires);
  return{host,loading,text,fires};
}
function animationTimers(f){
  const timers=new Map();let next=0;f.window.setTimeout=(fn,ms)=>{const id=++next;timers.set(id,{fn,ms});return id;};f.window.clearTimeout=id=>timers.delete(id);return timers;
}
test('an actual failure cancels a success merge, settles three flames once and releases owned listeners',async()=>{
  const f=fixture();try{const timers=animationTimers(f),{host,loading,fires}=loadingHost(f),success=f.window.PaneSpirit.complete(host),image=loading.querySelector('.ps-loading-result');
    const failure=f.window.PaneSpirit.fail(host);assert.equal(await success,false);assert.equal(image.isConnected,false);assert.ok(loading.classList.contains('ps-failing'));
    assert.equal(f.window.PaneSpirit.fail(host),failure);fires.children[0].dispatchEvent({type:'animationend',animationName:'ps-loading-fall',bubbles:true});
    assert.equal(await failure,true);assert.ok(loading.classList.contains('ps-loading-failed'));assert.ok(!loading.classList.contains('ps-completing'));assert.ok(!loading.classList.contains('ps-loading-complete'));
    assert.equal(await f.window.PaneSpirit.complete(host),false);assert.equal(timers.size,0);assert.equal(f.events.get('research-motion-change').size,0);assert.equal(f.external.length,0);
  }finally{f.cleanup();}
});
test('failure ownership rejects a replaced loader and dispose cancels pending settlement without affecting the new owner',async()=>{
  const f=fixture();try{const timers=animationTimers(f),a=loadingHost(f),failure=f.window.PaneSpirit.fail(a.host);a.loading.remove();
    const replacement=f.el('span','ps-loading',a.host),fires=f.el('span','ps-loading-fires',replacement);f.el('svg','ps-loading-fire',fires);
    a.fires.children[0].dispatchEvent({type:'animationend',animationName:'ps-loading-fall',bubbles:true});assert.equal(await failure,false);assert.ok(!replacement.classList.contains('ps-loading-failed'));
    const next=f.window.PaneSpirit.fail(a.host);f.window.PaneSpirit.dispose(a.host);assert.equal(await next,false);assert.equal(timers.size,0);assert.equal(f.events.get('research-motion-change').size,0);
  }finally{f.cleanup();}
});
test('app motion off and system reduce settle failure immediately; changing app motion cancels a running fall',async()=>{
  for(const mode of ['app','system','change']){const f=fixture();try{const timers=animationTimers(f),{host,loading}=loadingHost(f);let enabled=mode!=='app';
      f.window.MiracleMotion={enabled:()=>enabled};if(mode==='system')f.window.matchMedia=()=>({matches:true});
      const pending=f.window.PaneSpirit.fail(host);if(mode==='change'){assert.equal(timers.size,1);enabled=false;for(const fn of [...f.events.get('research-motion-change')])fn({type:'research-motion-change'});}
      assert.equal(await pending,true);assert.ok(loading.classList.contains('ps-loading-failed'));assert.ok(!loading.classList.contains('ps-failing'));assert.equal(timers.size,0);assert.equal(f.external.length,0);
    }finally{f.cleanup();}}
});
test('success completes through the original owned event while a detached failure cannot act on another host',async()=>{
  const f=fixture();try{const timers=animationTimers(f),{host,loading}=loadingHost(f),pending=f.window.PaneSpirit.complete(host),image=loading.querySelector('.ps-loading-result');
    image.dispatchEvent({type:'animationend',animationName:'ps-loading-result',bubbles:true});assert.equal(await pending,true);assert.ok(loading.classList.contains('ps-loading-complete'));
    const detached=loadingHost(f);detached.host.remove();assert.equal(await f.window.PaneSpirit.fail(detached.host),false);assert.equal(timers.size,0);assert.equal(f.external.length,0);
  }finally{f.cleanup();}
});
}
