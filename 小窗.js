/* Collapse overview reading panes without replacing their DOM or terminal connection. */
(function (global) {
  'use strict';
  const KINDS=['gmap-reading','cmx-side','ad-aside','aag-reading','wfe-reading'];
  const SELECTOR=KINDS.map(k=>'.'+k).join(',');
  const controllers=new Map(),ignored=new WeakSet(),positionOwners=new WeakMap(),completions=new WeakMap(),pendingCompletions=new Set();
  let observer=null,started=false,queued=false,scanning=false;
  const doc=()=>global.document;
  const css=`
  .ps-position-host{position:relative}.ps-collapse-button{position:absolute;right:.45rem;top:.3rem;z-index:5;display:inline-block;border:1px solid var(--line);border-radius:.3rem;background:var(--card);color:var(--fg);font: .6875rem var(--font,system-ui);line-height:1.5;padding:.1rem .35rem;cursor:pointer;white-space:nowrap}.ps-collapse-button:hover,.ps-collapse-button:focus-visible,.ps-fire:hover,.ps-fire:focus-visible{border-color:var(--hover-gold);outline:1px solid var(--hover-gold);outline-offset:2px}.ps-pane-collapsed{visibility:hidden!important;position:absolute!important;pointer-events:none!important;width:var(--ps-pane-width)!important;height:var(--ps-pane-height)!important}.ps-layout-collapsed{grid-template-columns:minmax(0,1fr)!important;column-gap:0!important}.ps-fire{position:absolute;right:.6rem;top:.6rem;z-index:7;box-sizing:border-box;width:30px;height:30px;display:flex;align-items:center;justify-content:center;padding:2px;border:1px solid var(--hover-gold,var(--line));border-radius:.55rem;background:var(--card);color:var(--fg);cursor:pointer;box-shadow:0 .15rem .6rem var(--ring);line-height:1;visibility:visible!important;pointer-events:auto!important}.ps-fire[hidden]{display:none!important}.ps-fire img{display:block;width:min(var(--nav-icon-size,1.15rem),24px);height:min(var(--nav-icon-size,1.15rem),24px);pointer-events:none}.ps-fire:disabled{cursor:default}
  .ps-loading{display:inline-flex;align-items:center;gap:.35rem;min-height:1.35rem;vertical-align:middle;color:inherit}.ps-loading-fires{position:relative;display:inline-flex;align-items:flex-end;justify-content:center;gap:.12rem;flex:0 0 2.05rem;width:2.05rem;height:1.2rem}.ps-loading-fire{display:block;flex:0 0 .6rem;width:.6rem;height:1.05rem;overflow:visible;animation:ps-loading-hop 1.12s ease-in-out infinite;transform-origin:50% 100%;pointer-events:none}.ps-loading-jade{color:#6cae9f;animation-delay:0s;--ps-merge-x:.72rem}.ps-loading-violet{color:#9699cb;animation-delay:.16s;--ps-merge-x:0rem}.ps-loading-gold{color:#bda064;animation-delay:.32s;--ps-merge-x:-.72rem}.ps-loading-text{line-height:1.5}.ps-fire.ps-scanning img{animation:ps-scan-flicker .72s ease-in-out infinite;transform-origin:50% 100%}
  @keyframes ps-loading-hop{0%,62%,100%{transform:translateY(0)}28%{transform:translateY(-2px)}42%{transform:translateY(-.5px)}}@keyframes ps-scan-flicker{0%,100%{transform:translateY(0) scaleY(1)}35%{transform:translateY(-1px) scaleY(1.04)}70%{transform:translateY(.2px) scaleY(.97)}}
  .ps-loading-result{position:absolute;inset:0;margin:auto;display:block;width:1.05rem;height:1.05rem;opacity:0;pointer-events:none}.ps-completing .ps-loading-fire{animation:ps-loading-merge .3s ease-in-out forwards}.ps-completing .ps-loading-result{animation:ps-loading-result .3s ease-in-out forwards}.ps-loading-complete .ps-loading-fire{animation:none;opacity:0;transform:translateX(var(--ps-merge-x))}.ps-loading-complete .ps-loading-result{animation:none;opacity:1}
  @keyframes ps-loading-merge{0%{transform:translateX(0);opacity:1}80%{transform:translateX(var(--ps-merge-x));opacity:.35}100%{transform:translateX(var(--ps-merge-x));opacity:0}}@keyframes ps-loading-result{0%,55%{opacity:0}100%{opacity:1}}
  .ps-failing .ps-loading-fire{animation:ps-loading-fall .5s ease-out forwards;animation-delay:0s}.ps-loading-failed .ps-loading-fire{animation:ps-loading-hop 1.12s ease-in-out infinite;transform:translateY(0);opacity:1}.ps-loading-failed .ps-loading-result{display:none}
  @keyframes ps-loading-fall{0%{transform:translateX(calc(var(--ps-merge-x)*.28)) translateY(-3px)}45%{transform:translateX(0) translateY(0)}70%{transform:translateX(0) translateY(-2px)}100%{transform:translateX(0) translateY(0)}}
  @media(prefers-reduced-motion:reduce){.ps-loading-fire,.ps-fire.ps-scanning img,.ps-completing .ps-loading-fire,.ps-completing .ps-loading-result,.ps-failing .ps-loading-fire,.ps-loading-failed .ps-loading-fire{animation:none;transform:none}}
  `;
  function textEscape(text){return String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  // Only decorative SVGs move; the status text and its fixed-size container stay put.
  function loading(text){
    ensureCSS();const label=textEscape(text==null?'正在读取':text);
    const path='M8 17.5C4.3 15.2 2.3 12.5 4.1 9.5C5.6 7.3 7.4 5.7 7 2C10.5 5.1 8.3 8.2 9.2 10C10 9.3 10.3 8.2 10.1 7.1C13 10.6 12.3 14.7 8 17.5Z';
    const fires=['jade','violet','gold'].map(color=>'<svg xmlns="http://www.w3.org/2000/svg" class="ps-loading-fire ps-loading-'+color+'" viewBox="0 0 16 20" width="10" height="16" aria-hidden="true" focusable="false"><path d="'+path+'" fill="currentColor" fill-opacity=".15" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/></svg>').join('');
    return '<span class="ps-loading" role="status" aria-live="polite" aria-atomic="true"><span class="ps-loading-text">'+label+'</span><span class="ps-loading-fires" aria-hidden="true">'+fires+'</span></span>';
  }
  // The owner calls this only after receiving successful data, then rechecks its request guard.
  function complete(host){
    const loading=host&&typeof host.matches==='function'&&host.matches('.ps-loading')?host:host&&typeof host.querySelector==='function'?host.querySelector('.ps-loading'):null;
    const fires=loading&&loading.querySelector('.ps-loading-fires');
    if(!host||!host.isConnected||!loading||!loading.isConnected||!fires)return Promise.resolve(false);
    const previous=completions.get(loading);if(previous)return previous.kind==='failure'?Promise.resolve(false):previous.promise;
    let resolve;const promise=new Promise(r=>{resolve=r;});
    const image=doc().createElement('img');image.className='ps-loading-result';image.src='icons/精气神.svg';image.alt='';image.draggable=false;
    let fallback=false;image.addEventListener('error',()=>{if(fallback)return;fallback=true;image.src='pfiles/'+encodeURI('外观/图标/精气神.svg');});
    const record={kind:'success',host,loading,promise,image,done:false,timer:null,media:null};
    const owns=()=>host.isConnected&&loading.isConnected&&(host===loading||host.querySelector('.ps-loading')===loading)&&loading.contains(image);
    record.finish=function(ok){
      if(record.done)return;record.done=true;
      if(record.timer!==null&&typeof global.clearTimeout==='function')global.clearTimeout(record.timer);
      loading.removeEventListener('animationend',onEnd);if(typeof global.removeEventListener==='function')global.removeEventListener('research-motion-change',onAppMotion);if(record.media){if(typeof record.media.removeEventListener==='function')record.media.removeEventListener('change',onMotion);else if(typeof record.media.removeListener==='function')record.media.removeListener(onMotion);}
      pendingCompletions.delete(record);cls(loading,'ps-completing',false);
      if(ok&&owns())cls(loading,'ps-loading-complete',true);else{ok=false;image.remove();}
      resolve(ok);
    };
    const onEnd=e=>{if(e.target===image&&e.animationName==='ps-loading-result')record.finish(owns());};
    const onMotion=e=>{if(e.matches)record.finish(owns());};
    const onAppMotion=()=>{if(global.MiracleMotion&&!global.MiracleMotion.enabled())record.finish(owns());};
    completions.set(loading,record);pendingCompletions.add(record);fires.appendChild(image);
    try{if(typeof global.matchMedia==='function')record.media=global.matchMedia('(prefers-reduced-motion: reduce)');}catch(e){}
    if(record.media&&record.media.matches||global.MiracleMotion&&!global.MiracleMotion.enabled()){record.finish(true);return promise;}
    if(typeof global.addEventListener==='function')global.addEventListener('research-motion-change',onAppMotion);
    loading.addEventListener('animationend',onEnd);if(record.media){if(typeof record.media.addEventListener==='function')record.media.addEventListener('change',onMotion);else if(typeof record.media.addListener==='function')record.media.addListener(onMotion);}
    cls(loading,'ps-completing',true);
    // A single fallback for the success animation, never a timer that invents read success.
    if(typeof global.setTimeout==='function')record.timer=global.setTimeout(()=>record.finish(owns()),320);else record.finish(owns());
    return promise;
  }
  // An actual failed request settles its own three flames; this never reports success.
  function fail(host){
    const loading=host&&typeof host.matches==='function'&&host.matches('.ps-loading')?host:host&&typeof host.querySelector==='function'?host.querySelector('.ps-loading'):null;
    if(!host||!host.isConnected||!loading||!loading.isConnected||!loading.querySelector('.ps-loading-fires'))return Promise.resolve(false);
    const previous=completions.get(loading);if(previous&&previous.kind==='failure')return previous.promise;
    if(previous){if(!previous.done)previous.finish(false);if(previous.image)previous.image.remove();}
    cls(loading,'ps-completing',false);cls(loading,'ps-loading-complete',false);
    let resolve;const promise=new Promise(r=>{resolve=r;}),record={kind:'failure',host,loading,promise,done:false,timer:null,media:null};
    const owns=()=>host.isConnected&&loading.isConnected&&(host===loading||host.querySelector('.ps-loading')===loading);
    const onEnd=e=>{if(e.animationName==='ps-loading-fall'&&e.target.classList.contains('ps-loading-fire'))record.finish(owns());};
    const onMotion=e=>{if(e.matches)record.finish(owns());};
    const onAppMotion=()=>{if(global.MiracleMotion&&!global.MiracleMotion.enabled())record.finish(owns());};
    record.finish=function(ok){
      if(record.done)return;record.done=true;
      if(record.timer!==null&&typeof global.clearTimeout==='function')global.clearTimeout(record.timer);
      loading.removeEventListener('animationend',onEnd);if(typeof global.removeEventListener==='function')global.removeEventListener('research-motion-change',onAppMotion);
      if(record.media){if(typeof record.media.removeEventListener==='function')record.media.removeEventListener('change',onMotion);else if(typeof record.media.removeListener==='function')record.media.removeListener(onMotion);}
      pendingCompletions.delete(record);cls(loading,'ps-failing',false);ok=!!ok&&owns();if(ok)cls(loading,'ps-loading-failed',true);resolve(ok);
    };
    completions.set(loading,record);pendingCompletions.add(record);
    try{if(typeof global.matchMedia==='function')record.media=global.matchMedia('(prefers-reduced-motion: reduce)');}catch(e){}
    if(record.media&&record.media.matches||global.MiracleMotion&&!global.MiracleMotion.enabled()){record.finish(true);return promise;}
    if(typeof global.addEventListener==='function')global.addEventListener('research-motion-change',onAppMotion);
    loading.addEventListener('animationend',onEnd);if(record.media){if(typeof record.media.addEventListener==='function')record.media.addEventListener('change',onMotion);else if(typeof record.media.addListener==='function')record.media.addListener(onMotion);}
    cls(loading,'ps-failing',true);
    // Cleanup fallback for the failure animation, only after a real owner has called fail.
    if(typeof global.setTimeout==='function')record.timer=global.setTimeout(()=>record.finish(owns()),520);else record.finish(owns());
    return promise;
  }
  function kindOf(pane){return KINDS.find(k=>pane.classList.contains(k))||'';}
  function cls(el,name,on){if(el&&el.classList.contains(name)!==!!on)el.classList.toggle(name,!!on);}
  function style(el){try{return global.getComputedStyle?global.getComputedStyle(el):el.style||{};}catch(e){return el.style||{};}}
  function ownNode(node){return !!node&&node.nodeType===1&&(node.classList.contains('ps-collapse-button')||node.classList.contains('ps-fire')||!!node.closest('.ps-collapse-button,.ps-fire'));}
  function current(options){let project='',hash='',lang='zh';try{project=typeof options.projectRoot==='function'?options.projectRoot():typeof options.projectRoot==='string'?options.projectRoot:typeof global.researchCurrentProjectRoot==='function'?global.researchCurrentProjectRoot():'';}catch(e){}try{hash=typeof options.hash==='function'?options.hash():options.hash===undefined?global.location&&global.location.hash||'':options.hash;}catch(e){}try{lang=typeof options.lang==='function'?options.lang():typeof global.getLang==='function'?global.getLang():'zh';}catch(e){}return {project:String(project||''),hash:String(hash||''),lang:lang==='en'?'en':'zh'};}
  function ensureCSS(){const d=doc();if(!d||d.getElementById('pane-spirit-style'))return;const el=d.createElement('style');el.id='pane-spirit-style';el.textContent=css;(d.head||d.documentElement).appendChild(el);}
  function storageRead(key){try{return global.localStorage.getItem(key)==='1';}catch(e){return false;}}
  function storageWrite(key,value){try{global.localStorage.setItem(key,value?'1':'0');}catch(e){}}
  function componentHidden(pane){if(pane.hidden||pane.style&&pane.style.display==='none'||style(pane).visibility==='hidden'&&!pane.classList.contains('ps-pane-collapsed'))return true;for(let el=pane.parentElement;el;el=el.parentElement){if(el.hidden||style(el).display==='none'||style(el).visibility==='hidden')return true;}return false;}
  function paneFullscreen(pane){const full=doc().fullscreenElement;if(full&&pane.contains(full))return full;for(const child of pane.querySelectorAll('.ad-fs'))if(!componentHidden(child))return child;return null;}
  function visibleParent(pane){return paneFullscreen(pane)||pane.parentElement;}
  function captureScroll(pane){return [pane,...pane.querySelectorAll('*')].filter(el=>el.scrollTop||el.scrollLeft).map(el=>({el,top:el.scrollTop,left:el.scrollLeft}));}
  function otherUses(parent,except,collapsedOnly){return Array.from(controllers.values()).some(c=>c!==except&&!c.destroyed&&c.parent===parent&&(!collapsedOnly||c.collapsed&&!componentHidden(c.pane)));}
  function acquirePosition(parent){if(!parent)return;const owned=positionOwners.get(parent);if(owned){owned.count++;return;}const added=style(parent).position==='static'||!style(parent).position;positionOwners.set(parent,{count:1,added});if(added)cls(parent,'ps-position-host',true);}
  function releasePosition(parent){const owned=parent&&positionOwners.get(parent);if(!owned)return;if(--owned.count>0)return;if(owned.added)cls(parent,'ps-position-host',false);positionOwners.delete(parent);}
  function Controller(pane,options){
    this.pane=pane;this.options=options||{};this.kind=kindOf(pane);this.parent=null;this.buttonHost=null;this.collapsed=false;this.destroyed=false;this.scroll=[];this.key='';
    this.button=doc().createElement('button');this.button.type='button';this.button.className='ps-collapse-button';this.button.setAttribute('data-pane-spirit','collapse');
    this.token=doc().createElement('button');this.token.type='button';this.token.className='ps-fire';this.token.setAttribute('data-pane-spirit','restore');this.token.hidden=true;
    const img=doc().createElement('img');img.src='icons/精气神.svg';img.alt='';img.draggable=false;img.addEventListener('error',()=>{if(this.imageFallback)return;this.imageFallback=true;img.src='pfiles/'+encodeURI('外观/图标/精气神.svg');});this.token.appendChild(img);this.image=img;
    this.onButton=e=>{e.preventDefault();e.stopPropagation();this.collapse();};this.onToken=e=>{e.preventDefault();e.stopPropagation();this.restore();};this.button.addEventListener('click',this.onButton);this.token.addEventListener('click',this.onToken);
    controllers.set(pane,this);this.sync();
  }
  Controller.prototype.context=function(){return current(this.options);};
  Controller.prototype.measure=function(){const r=this.pane.getBoundingClientRect();if(r.width>0&&r.height>0){this.pane.style.setProperty('--ps-pane-width',r.width+'px');this.pane.style.setProperty('--ps-pane-height',r.height+'px');}};
  Controller.prototype.layout=function(){const parent=this.parent;if(!parent)return;const active=this.collapsed&&!componentHidden(this.pane)||otherUses(parent,this,true);cls(parent,'ps-layout-collapsed',active&&parent.matches('.gmap-layout,.ad-scene,.aag-scene,.wfe-scene'));};
  Controller.prototype.sync=function(){
    if(this.destroyed)return;const ctx=this.context(),key='mh-pane-spirit:'+JSON.stringify([ctx.project,ctx.hash,this.kind]);
    if(key!==this.key){if(this.collapsed){cls(this.pane,'ps-pane-collapsed',false);this.pane.style.removeProperty('--ps-pane-width');this.pane.style.removeProperty('--ps-pane-height');}this.key=key;this.collapsed=storageRead(key);if(this.collapsed){this.scroll=captureScroll(this.pane);this.measure();}}
    const parent=visibleParent(this.pane);
    if(parent!==this.parent){const old=this.parent;this.parent=parent;if(old&&!otherUses(old,this,false))cls(old,'ps-layout-collapsed',false);releasePosition(old);if(parent){acquirePosition(parent);parent.appendChild(this.token);}}
    const buttonHost=paneFullscreen(this.pane)||this.pane;
    if(buttonHost!==this.buttonHost){releasePosition(this.buttonHost);this.buttonHost=buttonHost;acquirePosition(buttonHost);}
    if(this.button.parentElement!==buttonHost)buttonHost.appendChild(this.button);
    cls(this.token,'ps-scanning',scanning);
    const text=ctx.lang==='en'?'Collapse':'收起',collapseTitle=ctx.lang==='en'?'Collapse reading pane':'收起阅读窗口',title=(scanning?(ctx.lang==='en'?'Scanning · ':'正在扫描 · '):'')+(ctx.lang==='en'?'Essence · Qi · Spirit · Expand reading pane':'精气神 · 展开阅读窗口');
    if(this.button.textContent!==text)this.button.textContent=text;if(this.button.title!==collapseTitle)this.button.title=collapseTitle;if(this.button.getAttribute('aria-label')!==collapseTitle)this.button.setAttribute('aria-label',collapseTitle);if(this.token.title!==title)this.token.title=title;if(this.token.getAttribute('aria-label')!==title)this.token.setAttribute('aria-label',title);
    const closed=componentHidden(this.pane);if(this.collapsed&&!closed&&!this.pane.classList.contains('ps-pane-collapsed'))this.measure();cls(this.pane,'ps-pane-collapsed',this.collapsed&&!closed);const hidden=!this.collapsed||closed;if(this.token.hidden!==hidden)this.token.hidden=hidden;this.layout();
  };
  Controller.prototype.collapse=function(){
    if(this.destroyed||this.collapsed||componentHidden(this.pane))return false;this.measure();this.scroll=captureScroll(this.pane);
    // The owner can return a terminal to watching before this pane becomes invisible.
    if(typeof this.options.onCollapse==='function')this.options.onCollapse(this.pane);
    if(typeof global.CustomEvent==='function')this.pane.dispatchEvent(new global.CustomEvent('research-pane-collapse',{bubbles:true,detail:{kind:this.kind}}));
    this.collapsed=true;storageWrite(this.key,true);this.sync();if(!this.token.hidden&&this.token.focus)this.token.focus({preventScroll:true});return true;
  };
  Controller.prototype.restore=function(){
    if(this.destroyed||!this.collapsed)return false;this.collapsed=false;storageWrite(this.key,false);this.sync();this.pane.style.removeProperty('--ps-pane-width');this.pane.style.removeProperty('--ps-pane-height');for(const p of this.scroll){if(p.el.isConnected&&(p.el===this.pane||this.pane.contains(p.el))){p.el.scrollTop=p.top;p.el.scrollLeft=p.left;}}this.scroll=[];if(!componentHidden(this.pane)&&this.button.focus)this.button.focus({preventScroll:true});return true;
  };
  Controller.prototype.dispose=function(){if(this.destroyed)return;this.destroyed=true;this.button.removeEventListener('click',this.onButton);this.token.removeEventListener('click',this.onToken);this.button.remove();this.token.remove();cls(this.pane,'ps-pane-collapsed',false);releasePosition(this.buttonHost);this.pane.style.removeProperty('--ps-pane-width');this.pane.style.removeProperty('--ps-pane-height');controllers.delete(this.pane);if(this.parent&&!otherUses(this.parent,this,true))cls(this.parent,'ps-layout-collapsed',false);releasePosition(this.parent);};
  function attach(pane,options){if(!pane||!kindOf(pane))return null;ignored.delete(pane);ensureCSS();let c=controllers.get(pane);if(c){if(options)c.options=options;c.sync();return c;}return new Controller(pane,options);}
  // A boolean comes from the owner's real scan state. No argument remains the DOM rescan API.
  function scan(active){if(typeof active==='boolean')scanning=active;const d=doc();if(!d)return scanning;for(const c of Array.from(controllers.values()))if(!c.pane.isConnected)c.dispose();for(const pane of d.querySelectorAll(SELECTOR)){if(!ignored.has(pane))attach(pane);}for(const c of controllers.values())c.sync();return scanning;}
  function schedule(){if(queued)return;queued=true;const run=()=>{queued=false;if(started)scan();};if(typeof global.queueMicrotask==='function')global.queueMicrotask(run);else Promise.resolve().then(run);}
  function relevant(record){const target=record.target;if(!target||ownNode(target))return false;if(record.type==='attributes')return target.matches&&target.matches(SELECTOR)||Array.from(controllers.values()).some(c=>target.contains&&target.contains(c.pane)||c.pane.contains(target)&&(target===c.buttonHost||target===c.parent||target.matches('.ad-terminal,.ad-fs')));if(record.type==='childList'){const changed=[...record.addedNodes,...record.removedNodes];if(changed.length&&changed.every(ownNode))return false;if(target.closest&&target.closest(SELECTOR))return true;return changed.some(n=>n.nodeType===1&&!ownNode(n)&&(n.matches(SELECTOR)||n.querySelector(SELECTOR)));}return false;}
  function boot(){if(started||!doc())return;started=true;ensureCSS();scan();if(typeof global.MutationObserver==='function'){observer=new global.MutationObserver(records=>{if(records.some(relevant))schedule();});observer.observe(doc().documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','style']});}global.addEventListener('hashchange',schedule);doc().addEventListener('fullscreenchange',schedule);}
  function dispose(pane){if(pane){ignored.add(pane);const c=controllers.get(pane);if(c)c.dispose();for(const r of Array.from(pendingCompletions))if(pane.contains(r.loading))r.finish(false);return;}started=false;queued=false;scanning=false;for(const r of Array.from(pendingCompletions))r.finish(false);if(observer){observer.disconnect();observer=null;}if(doc())doc().removeEventListener('fullscreenchange',schedule);if(global.removeEventListener)global.removeEventListener('hashchange',schedule);for(const c of Array.from(controllers.values()))c.dispose();}
  const api={attach,scan,loading,complete,fail,dispose,boot,Controller};global.PaneSpirit=api;if(typeof module==='object'&&module.exports)module.exports=api;
  if(doc()){if(doc().readyState==='loading')doc().addEventListener('DOMContentLoaded',boot,{once:true});else boot();}
})(typeof window==='object'?window:globalThis);
