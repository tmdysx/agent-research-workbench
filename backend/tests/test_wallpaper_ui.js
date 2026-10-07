'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const crypto=require('node:crypto');
// The production block is extracted from the actual template after integration.
// TEMP staging can supply MH_WALLPAPER_SOURCE without changing production code.
const sourcePath=process.env.MH_WALLPAPER_SOURCE||path.join(__dirname,'../../模板.html'),full=fs.readFileSync(sourcePath,'utf8');
const start=full.indexOf('/* ================= 背景壁纸 Wallpaper：'),end=full.indexOf('/* ================= 背景壁纸 Wallpaper 结束 ================= */',start);
assert.ok(start>=0&&end>start,'Production wallpaper block must exist');const source=full.slice(start,end);
const samples={
  png:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNQKI4GAAGlAO+ALIDFAAAAAElFTkSuQmCC',
  jpeg:'/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDlqKKKo+bP/9k=',
  webp:'UklGRjIAAABXRUJQVlA4ICYAAABwAQCdASoBAAEAAUAmJaACdAFAAAD+8Jmg3/+YJ/7/f9/u4oAAAA=='
};
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
function image(kind='png',extra={}){const blob=new Blob([Buffer.from(samples[kind],'base64')],{type:extra.type===undefined?'image/'+kind:extra.type});
  Object.defineProperty(blob,'name',{value:extra.name||'chosen.'+kind});for(const [k,v]of Object.entries(extra))if(k!=='type'&&k!=='name')Object.defineProperty(blob,k,{value:v});return blob;}
function element(){return{attrs:new Map(),value:'',disabled:false,hidden:false,textContent:'',innerHTML:'',handlers:{},clicks:0,
  classList:{toggle(){},add(){},remove(){}},setAttribute(k,v){this.attrs.set(k,v);},getAttribute(k){return this.attrs.get(k)||null;},
  removeAttribute(k){this.attrs.delete(k);},addEventListener(k,h){this.handlers[k]=h;},click(){++this.clicks;},matches(){return false;}};}
function harness(existing=new Map()){
  const e={root:'C:/Projects/Alpha',lang:'both',records:existing,writes:[],reads:[],requests:[],images:[],urls:new Map(),revoked:[],decodeQueue:[],
    fetchQueue:[],readError:false,writeError:false,openError:false,holdWrites:false,pendingWrites:[],aborts:0,box:null};
  const png=Buffer.from(samples.png,'base64');e.manifest={version:1,wallpapers:['02','03','04','05','06'].map(id=>({id,path:'外观/壁纸/'+id+' 样例.png',title:'样例 '+id,title_en:'Sample '+id,sha256:crypto.createHash('sha256').update(png).digest('hex'),bytes:png.length}))};
  const style={backgroundImage:'',props:new Map(),setProperty(k,v){this.props.set(k,v);},removeProperty(k){if(k==='background-image')this.backgroundImage='';else this.props.delete(k);}};
  const body=element();body.style=style;let urlSeq=0,created=false;
  const db={objectStoreNames:{contains(){return created;}},createObjectStore(){created=true;},close(){},transaction(store,mode){
    assert.equal(store,'wallpapers');const tx={done:false,aborted:false,abort(){if(this.done)throw Error('complete');if(this.aborted)return;this.aborted=true;++e.aborts;queueMicrotask(()=>this.onabort&&this.onabort());},
      objectStore(){return{get(root){const request={};e.reads.push(root);queueMicrotask(()=>{
        if(e.readError){tx.abort();return;}if(tx.aborted)return;request.result=e.records.get(root);if(request.onsuccess)request.onsuccess();
        queueMicrotask(()=>{if(tx.aborted)return;tx.done=true;if(tx.oncomplete)tx.oncomplete();});});return request;},
        put(record){assert.equal(mode,'readwrite');const finish=()=>{if(tx.aborted)return;if(e.writeError){tx.abort();return;}
          e.writes.push({record,previousBackground:style.backgroundImage});e.records.set(record.projectRoot,record);tx.done=true;if(tx.oncomplete)tx.oncomplete();};
          if(e.holdWrites)e.pendingWrites.push(finish);else queueMicrotask(finish);return{};}};}};return tx;}};
  const context={console,Blob,Uint8Array,WeakSet,Set,TextDecoder,crypto:crypto.webcrypto,queueMicrotask,indexedDB:{open(name,version){assert.equal(name,'miracle-harness-wallpapers-v1');assert.equal(version,1);const request={};
    queueMicrotask(()=>{if(e.openError){if(request.onerror)request.onerror();return;}request.result=db;if(!created&&request.onupgradeneeded)request.onupgradeneeded();if(request.onsuccess)request.onsuccess();});return request;}},
    URL:{createObjectURL(blob){const url='blob:http://127.0.0.1/mock-'+(++urlSeq);e.urls.set(url,blob);return url;},revokeObjectURL(url){e.revoked.push(url);e.urls.delete(url);}},
    Image:class{constructor(){this.naturalWidth=1;this.naturalHeight=1;this.pending=e.decodeQueue.shift();}set src(url){assert.ok(e.urls.has(url),'Only a verified own blob URL can enter decoder');e.images.push(url);}decode(){return this.pending?this.pending.promise:Promise.resolve();}},
    document:{body,getElementById(){return e.box;}},getLang:()=>e.lang,researchCurrentProjectRoot:()=>e.root,
    fetch:async(url,options)=>{e.requests.push({url,options});const pending=e.fetchQueue.shift();if(pending)return pending.promise;
      const bytes=Uint8Array.from(decodeURIComponent(url)==='pfiles/外观/壁纸/清单.json'?Buffer.from(JSON.stringify(e.manifest)):png);return{ok:true,headers:{get(){return String(bytes.length);}},arrayBuffer:async()=>bytes.buffer};},
    localStorage:{getItem(){throw Error('Wallpaper must not read localStorage');},setItem(){throw Error('Wallpaper must not save large images to localStorage');}}};
  context.window=context;vm.createContext(context);vm.runInContext(source,context,{filename:sourcePath});
  e.api=context.researchWallpaper;e.context=context;e.body=body;e.state=()=>JSON.parse(JSON.stringify(e.api.inspect()));e.releaseWrites=()=>{e.holdWrites=false;for(const finish of e.pendingWrites.splice(0))finish();};
  e.attachUI=()=>{const selectors=['[data-wallpaper-action="none"]','[data-wallpaper-action="choose"]','[data-wallpaper-action="enable"]','[data-wallpaper-file]',
    '[data-wallpaper-strength]','[data-wallpaper-output]','[data-wallpaper-preview]','[data-wallpaper-status]','[data-wallpaper-drop]','[data-wallpaper-builtins]',...['02','03','04','05','06'].map(id=>'[data-wallpaper-builtin="'+id+'"]')];
    e.controls=new Map(selectors.map(s=>[s,element()]));const box=element();box.querySelector=s=>e.controls.get(s)||null;box.contains=()=>true;e.box=box;context.wallpaperSettingsReady();return box;};
  return e;
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function until(predicate){for(let i=0;i<30&&!predicate();++i)await tick();assert.ok(predicate(),'Expected pending production operation');}
function record(root,extra={}){return{v:1,projectRoot:root,enabled:true,strength:12,builtinId:'',blob:image(),name:'old.png',...extra};}
function drop(files,extra={}){return{prevented:false,stopped:false,preventDefault(){this.prevented=true;},stopPropagation(){this.stopped=true;},
  dataTransfer:{files,items:files.map(()=>({kind:'file',webkitGetAsEntry:()=>({isDirectory:false})})),getData:()=>'',...extra}};}

test('default none performs zero image requests, creates no object URL, does not write or mutate body',async()=>{
  const e=harness();await e.api.syncProject();await e.api.syncProject();assert.equal(e.state().enabled,false);assert.equal(e.state().strength,12);
  assert.equal(e.requests.length,0);assert.equal(e.images.length,0);assert.equal(e.urls.size,0);assert.equal(e.writes.length,0);assert.equal(e.reads.length,1);
  assert.equal(e.body.style.backgroundImage,'');assert.equal(e.body.getAttribute('data-mh-wallpaper'),null);
  const html=e.context.wallpaperChoices();assert.match(html,/min="0" max="100"/);assert.match(html,/20 MiB/);assert.doesNotMatch(html,/<img[^>]+\ssrc=/);assert.doesNotMatch(html,/https?:\/\//);
  assert.match(html,/data-wallpaper-builtins/);assert.doesNotMatch(html,/data-wallpaper-builtin="01"/);
});
test('PNG, JPEG and WebP are signature checked and decoded; one root Blob record commits before apply',async()=>{
  const e=harness();await e.api.syncProject();for(const kind of ['png','jpeg','webp']){
    const old=e.body.style.backgroundImage;assert.equal(await e.api.chooseFile(image(kind)),true);const saved=e.records.get(e.root);
    assert.equal(saved.blob.type,'image/'+kind);assert.equal(saved.enabled,true);assert.equal(saved.builtinId,'');assert.equal(saved.projectRoot,e.root);
    assert.equal(saved.dataURL,undefined);assert.equal(saved.imageURL,undefined);assert.equal(e.writes.at(-1).previousBackground,old);
    assert.ok(e.body.style.backgroundImage.includes(e.state().imageURL));assert.match(e.body.style.backgroundImage,/var\(--plane\)/);
  }assert.equal(e.requests.length,0);assert.equal(e.urls.size,1);assert.equal(e.revoked.length,2);
});
test('SVG, HTML, URL bytes, lying MIME and oversized files never replace the previous wallpaper',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const old=e.state(),bg=e.body.style.backgroundImage,writes=e.writes.length,images=e.images.length;
  for(const data of ['<svg onload="evil()"></svg>','<!doctype html>','https://example.org/image.png'])assert.equal(await e.api.chooseFile(new Blob([data],{type:'image/png'})),false);
  assert.equal(await e.api.chooseFile(image('png',{type:'image/webp'})),false);
  let read=false;assert.equal(await e.api.chooseFile(image('png',{size:20*1024*1024+1,arrayBuffer:async()=>{read=true;}})),false);assert.equal(read,false);
  assert.equal(e.state().imageURL,old.imageURL);assert.equal(e.body.style.backgroundImage,bg);assert.equal(e.writes.length,writes);assert.equal(e.images.length,images);
});
test('native decode failure releases the candidate object URL, keeps the old image and does not persist',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const old=e.state().imageURL,writes=e.writes.length;
  const wait=deferred();e.decodeQueue.push(wait);const pending=e.api.chooseFile(image('webp'));await until(()=>e.images.length===2);wait.reject(Error('decode'));
  assert.equal(await pending,false);assert.equal(e.state().imageURL,old);assert.equal(e.urls.size,1);assert.equal(e.writes.length,writes);assert.equal(e.state().message,'decode');
});
test('native chooser cancel changes no settings, no persisted data and no object URLs',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const before=e.state(),writes=e.writes.length;
  assert.equal(await e.api.chooseFile(null),false);assert.deepEqual(e.state(),before);assert.equal(e.writes.length,writes);assert.equal(e.revoked.length,0);
});
test('storage quota/transaction failure preserves previous image, preview, intensity and committed record',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());e.attachUI();const old=e.state(),saved=e.records.get(e.root),bg=e.body.style.backgroundImage;e.writeError=true;
  assert.equal(await e.api.chooseFile(image('webp')),false);assert.equal(await e.api.editPreference({strength:100}),false);assert.equal(await e.api.editPreference({enabled:false}),false);
  for(const k of ['imageURL','name','strength','enabled'])assert.equal(e.state()[k],old[k]);assert.equal(e.records.get(e.root),saved);assert.equal(e.body.style.backgroundImage,bg);
  assert.equal(e.controls.get('[data-wallpaper-preview]').getAttribute('src'),old.imageURL);assert.equal(e.controls.get('[data-wallpaper-strength]').value,'12');
  assert.equal(e.urls.size,1);assert.equal(e.state().message,'storage');
});
test('disable keeps selected image; restore revalidates Blob, then enable and 0–100 strength persist',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const selected=e.state().imageURL;
  assert.equal(await e.api.editPreference({strength:0}),true);assert.equal(await e.api.editPreference({enabled:false}),true);assert.equal(e.body.style.backgroundImage,'');assert.ok(e.urls.has(selected));
  const other=harness(e.records);await other.api.syncProject();assert.equal(other.state().enabled,false);assert.equal(other.state().strength,0);assert.equal(other.images.length,1);
  assert.equal(await other.api.editPreference({enabled:true}),true);assert.equal(await other.api.editPreference({strength:100}),true);assert.equal(other.body.style.props.get('--mh-wallpaper-strength'),'100%');
  const writes=other.writes.length;for(const n of [-1,101,NaN,10.5])assert.equal(await other.api.editPreference({strength:n}),false);
  assert.equal(await other.api.editPreference({imageURL:'https://example.org/x.png'}),false);assert.equal(await other.api.editPreference({enabled:'yes'}),false);assert.equal(other.writes.length,writes);
});
test('same-origin project isolation: new root defaults to none; returning restores only its own record',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const first=e.state().imageURL;
  e.root='C:/Projects/Beta';await e.api.syncProject();assert.equal(e.state().imageURL,'');assert.equal(e.state().enabled,false);assert.equal(e.body.style.backgroundImage,'');assert.ok(e.revoked.includes(first));assert.equal(e.records.has(e.root),false);
  await e.api.chooseFile(image('webp'));assert.equal(e.records.size,2);e.root='C:/Projects/Alpha';await e.api.syncProject();assert.equal(e.state().name,'chosen.png');assert.equal(e.state().enabled,true);assert.equal(e.urls.size,1);
});
test('file decode from the previous project cannot persist or apply after root changes',async()=>{
  const e=harness();await e.api.syncProject();const wait=deferred();e.decodeQueue.push(wait);const pending=e.api.chooseFile(image());await until(()=>e.images.length===1);
  e.root='C:/Projects/Beta';await e.api.syncProject();wait.resolve();assert.equal(await pending,false);assert.equal(e.writes.length,0);assert.equal(e.urls.size,0);assert.equal(e.body.style.backgroundImage,'');
});
test('latest chooser wins; disabling cancels a pending decode and keeps its last committed image',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());const a=deferred();e.decodeQueue.push(a);const first=e.api.chooseFile(image('jpeg'));await until(()=>e.images.length===2);
  await e.api.chooseFile(image('webp'));const newest=e.state().imageURL;a.resolve();assert.equal(await first,false);assert.equal(e.state().imageURL,newest);
  const b=deferred();e.decodeQueue.push(b);const second=e.api.chooseFile(image('jpeg'));await until(()=>e.images.length===4);
  assert.equal(await e.api.editPreference({enabled:false}),true);b.resolve();assert.equal(await second,false);assert.equal(e.state().enabled,false);assert.equal(e.state().imageURL,newest);assert.equal(e.urls.size,1);
});
test('a write transaction in flight is aborted on project change; no stale record commits',async()=>{
  const e=harness();await e.api.syncProject();e.holdWrites=true;const pending=e.api.chooseFile(image());await until(()=>e.pendingWrites.length===1);
  assert.equal(e.body.style.backgroundImage,'');e.root='C:/Projects/Beta';await e.api.syncProject();e.releaseWrites();assert.equal(await pending,false);
  assert.equal(e.writes.length,0);assert.equal(e.records.size,0);assert.equal(e.urls.size,0);assert.equal(e.aborts,1);
});
test('stored records must match root/version/types/strength, and custom blobs must re-pass signature/decode',async()=>{
  const root='C:/Projects/Alpha';const bad=[record(root,{projectRoot:'C:/Projects/Other'}),record(root,{v:99}),record(root,{strength:101}),record(root,{enabled:'yes'}),
    record(root,{blob:'https://example.org/a.png'}),record(root,{blob:new Blob(['<svg>'],{type:'image/png'})}),record(root,{builtinId:'__proto__',blob:null}),record(root,{blob:null}),record(root,{builtinId:'02'})];
  for(const raw of bad){const e=harness(new Map([[root,raw]]));await e.api.syncProject();assert.equal(e.state().enabled,false);assert.equal(e.body.style.backgroundImage,'');assert.equal(e.requests.length,0);assert.equal(e.images.length,0);assert.equal(e.records.get(root),raw);}
  const e=harness(new Map([[root,record(root)]])),wait=deferred();e.decodeQueue.push(wait);const pending=e.api.syncProject();await until(()=>e.images.length===1);wait.reject(Error('invalid'));
  await pending;assert.equal(e.state().enabled,false);assert.equal(e.urls.size,0);assert.equal(e.state().message,'restore');assert.equal(e.writes.length,0);
});
test('late restore releases its URL after another project connects; restore never writes',async()=>{
  const root='C:/Projects/Alpha',e=harness(new Map([[root,record(root)]])),wait=deferred();e.decodeQueue.push(wait);const pending=e.api.syncProject();await until(()=>e.images.length===1);
  e.root='C:/Projects/Beta';await e.api.syncProject();wait.resolve();await pending;assert.equal(e.state().root,e.root);assert.equal(e.state().imageURL,'');assert.equal(e.urls.size,0);assert.equal(e.writes.length,0);
});
test('built-ins are explicit fixed same-origin requests; storage contains only ID with no image Blob/URL',async()=>{
  const e=harness();await e.api.syncProject();for(const id of ['02','03','04','05','06']){
    assert.equal(await e.api.chooseBuiltin(id),true);const saved=e.records.get(e.root),req=e.requests.at(-1);
    assert.equal(saved.builtinId,id);assert.equal(saved.blob,null);assert.equal(saved.imageURL,undefined);assert.equal(saved.dataURL,undefined);assert.equal(e.state().builtinId,id);
    assert.match(req.url,/^pfiles\//);assert.match(decodeURIComponent(req.url),new RegExp('外观/壁纸/'+id+' '));assert.equal(req.options.mode,'same-origin');assert.equal(req.options.redirect,'error');
  }assert.equal(e.urls.size,1);const before=e.requests.length;for(const id of ['01','http://evil.test/a','../secret','constructor'])assert.equal(await e.api.chooseBuiltin(id),false);assert.equal(e.requests.length,before);
  const restored=harness(e.records);await restored.api.syncProject();assert.equal(restored.state().builtinId,'06');assert.equal(restored.requests.length,2);assert.equal(restored.writes.length,0);
});
test('late built-in fetch cannot create a decoder URL, write or alter another project',async()=>{
  const e=harness();await e.api.syncProject();await e.api.loadManifest();const wait=deferred();e.fetchQueue.push(wait);const pending=e.api.chooseBuiltin('03');await until(()=>e.requests.length===2);
  e.root='C:/Projects/Beta';await e.api.syncProject();const bytes=Uint8Array.from(Buffer.from(samples.png,'base64'));wait.resolve({ok:true,headers:{get(){return String(bytes.length);}},arrayBuffer:async()=>bytes.buffer});
  assert.equal(await pending,false);assert.equal(e.images.length,0);assert.equal(e.writes.length,0);assert.equal(e.urls.size,0);
});
test('failed built-in fetch, oversized response or corrupted signature preserve old image',async()=>{
  const e=harness();await e.api.syncProject();await e.api.loadManifest();await e.api.chooseFile(image());const old=e.state().imageURL,writes=e.writes.length;
  for(const response of [{ok:false},{ok:true,headers:{get:()=>String(21*1024*1024)}},{ok:true,headers:{get:()=>null},arrayBuffer:async()=>Buffer.from('<svg>').buffer}]){
    const wait=deferred();e.fetchQueue.push(wait);const pending=e.api.chooseBuiltin('02');wait.resolve(response);assert.equal(await pending,false);assert.equal(e.state().imageURL,old);
  }assert.equal(e.writes.length,writes);assert.equal(e.urls.size,1);
});
test('only one local file is accepted by the wallpaper drop zone; URLs, directories and multiple files are rejected',async()=>{
  const e=harness();await e.api.syncProject();const valid=drop([image()]);assert.equal(await e.api.receiveDrop(valid),true);assert.equal(valid.prevented,true);assert.equal(valid.stopped,true);
  const old=e.state().imageURL,writes=e.writes.length;for(const event of [drop([image(),image('webp')]),drop([],{getData:()=> 'https://example.org/x.png'}),
    drop([image()],{items:[{kind:'file',webkitGetAsEntry:()=>({isDirectory:true})}]}),drop([image()],{items:[{kind:'string'}]})]){
    assert.equal(await e.api.receiveDrop(event),false);assert.equal(event.prevented,true);assert.equal(event.stopped,true);
  }assert.equal(e.state().imageURL,old);assert.equal(e.writes.length,writes);assert.equal(e.requests.length,0);
});
test('storage disabled/read error and no project do not inherit images or write an unscoped record',async()=>{
  const e=harness();e.readError=true;await e.api.syncProject();assert.equal(e.state().enabled,false);assert.equal(e.images.length,0);
  e.readError=false;await e.api.chooseFile(image());e.root='';await e.api.syncProject();const writes=e.writes.length;assert.equal(await e.api.chooseFile(image()),false);
  assert.equal(e.body.style.backgroundImage,'');assert.equal(e.urls.size,0);assert.equal(e.writes.length,writes);assert.equal(e.state().message,'project');
  const denied=harness();denied.openError=true;await denied.api.syncProject();assert.equal(denied.state().enabled,false);assert.equal(denied.state().message,'storage');
});
test('settings bind once with accessible file chooser/drop keyboard; English and preview stay in the appearance section',async()=>{
  const e=harness();await e.api.syncProject();e.attachUI();const handlers={...e.box.handlers};e.context.wallpaperSettingsReady();for(const k of Object.keys(handlers))assert.equal(e.box.handlers[k],handlers[k]);
  assert.equal(e.controls.get('[data-wallpaper-preview]').getAttribute('src'),null);await e.api.chooseFile(image());assert.equal(e.controls.get('[data-wallpaper-preview]').hidden,false);
  assert.equal(e.controls.get('[data-wallpaper-strength]').disabled,false);await e.api.editPreference({enabled:false});assert.equal(e.controls.get('[data-wallpaper-action="enable"]').hidden,false);
  const zone=e.controls.get('[data-wallpaper-drop]');zone.handlers.keydown({key:'Enter',preventDefault(){}});assert.equal(e.controls.get('[data-wallpaper-file]').clicks,1);
  assert.equal(e.box.handlers.drop,undefined,'No global/settings-wide drop interception');e.lang='en';e.context.wallpaperSettingsReady();const html=e.context.wallpaperChoices();
  assert.match(html,/Background wallpaper/);assert.match(html,/Custom images up to 20 MiB/);assert.doesNotMatch(html,/背景壁纸/);assert.equal(e.controls.get('[data-wallpaper-status]').textContent,'No wallpaper enabled');
});
test('ordinary manifest determines available cards; source metadata is never used as a download path',async()=>{
  const e=harness();await e.api.syncProject();const added={...e.manifest.wallpapers[0],id:'07',path:'外观/壁纸/07 自定义.png',title:'<img src=x onerror=evil()>',title_en:'Custom & safe',source:'C:/Authors/private/secret.png'};
  e.manifest.wallpapers.push(added);e.attachUI();await e.api.loadManifest();assert.equal(e.requests.length,1,'Settings reads only the JSON list');assert.equal(e.images.length,0);
  const html=e.controls.get('[data-wallpaper-builtins]').innerHTML;assert.match(html,/data-wallpaper-builtin="07"/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img src=x/);
  assert.equal(await e.api.chooseBuiltin('07'),true);assert.equal(e.requests.length,2);assert.equal(decodeURIComponent(e.requests[1].url),'pfiles/外观/壁纸/07 自定义.png');
  assert.equal(e.records.get(e.root).builtinId,'07');assert.ok(e.requests.every(r=>!r.url.includes('secret')));
});
test('manifest rejects remote, SVG, escaped or traversing paths, duplicate identity and incomplete provenance',async()=>{
  const invalid=[{path:'https://evil.test/a.png'},{path:'外观/壁纸/../a.png'},{path:'外观/壁纸/%2e%2e/a.png'},
    {path:'外观/壁纸/..\\a.png'},{path:'/外观/壁纸/a.png'},{path:'外观/壁纸/nested/a.png'},{path:'外观/壁纸/a.svg'},
    {path:'外观/壁纸/a.png?x=1'},{id:'../02'},{sha256:'bad'},{bytes:0},{title_en:''}];
  for(const update of invalid){const e=harness();await e.api.syncProject();Object.assign(e.manifest.wallpapers[0],update);
    assert.equal(await e.api.chooseBuiltin('02'),false);assert.equal(e.requests.length,1);assert.equal(e.images.length,0);assert.equal(e.urls.size,0);assert.equal(e.writes.length,0);}
  for(const type of ['id','path']){const e=harness();await e.api.syncProject();e.manifest.wallpapers[1][type]=e.manifest.wallpapers[0][type];
    assert.equal(await e.api.chooseBuiltin('02'),false);assert.equal(e.requests.length,1);assert.equal(e.images.length,0);}
});
test('built-in bytes and SHA256 must both match before decoder or saved ID can change',async()=>{
  for(const update of [{bytes:999},{sha256:'0'.repeat(64)}]){const e=harness();await e.api.syncProject();await e.api.chooseFile(image());
    const old=e.state().imageURL,writes=e.writes.length;Object.assign(e.manifest.wallpapers[0],update);assert.equal(await e.api.chooseBuiltin('02'),false);
    assert.equal(e.state().imageURL,old);assert.equal(e.images.length,1);assert.equal(e.writes.length,writes);assert.equal(e.urls.size,1);}
});
test('late manifest cannot replace the current project cards or supply the old project asset',async()=>{
  const e=harness();await e.api.syncProject();const wait=deferred();e.fetchQueue.push(wait);const pending=e.api.loadManifest();await until(()=>e.requests.length===1);
  const oldManifest={version:1,wallpapers:[{...e.manifest.wallpapers[0],title:'Old project',title_en:'Old project'}]};
  e.root='C:/Projects/Beta';await e.api.syncProject();e.manifest.wallpapers[0].title='新项目';const fresh=await e.api.loadManifest();assert.equal(fresh['02'].title,'新项目');
  const bytes=Uint8Array.from(Buffer.from(JSON.stringify(oldManifest)));wait.resolve({ok:true,headers:{get(){return String(bytes.length);}},arrayBuffer:async()=>bytes.buffer});
  assert.equal(await pending,null);e.attachUI();assert.match(e.controls.get('[data-wallpaper-builtins]').innerHTML,/新项目/);assert.doesNotMatch(e.controls.get('[data-wallpaper-builtins]').innerHTML,/Old project/);
  assert.equal(e.images.length,0);assert.equal(e.writes.length,0);
});
test('a valid built-in larger than 2 MiB stays out of browser persistence; actual bytes/hash are checked',async()=>{
  const e=harness();await e.api.syncProject();const bytes=new Uint8Array(2294026);bytes.set(Buffer.from(samples.png,'base64'));
  e.manifest.wallpapers[1].bytes=bytes.length;e.manifest.wallpapers[1].sha256=crypto.createHash('sha256').update(bytes).digest('hex');await e.api.loadManifest();
  const wait=deferred();e.fetchQueue.push(wait);const pending=e.api.chooseBuiltin('03');wait.resolve({ok:true,headers:{get:()=>String(bytes.length)},arrayBuffer:async()=>bytes.buffer});
  assert.equal(await pending,true);assert.equal(e.records.get(e.root).builtinId,'03');assert.equal(e.records.get(e.root).blob,null);assert.equal(e.records.get(e.root).dataURL,undefined);
});
test('bounded streaming cancels an oversized response and releases the reader before any decode',async()=>{
  const e=harness();await e.api.syncProject();await e.api.loadManifest();let cancelled=0,released=0,read=0;
  const wait=deferred();e.fetchQueue.push(wait);const pending=e.api.chooseBuiltin('02');
  wait.resolve({ok:true,headers:{get:()=>null},body:{getReader:()=>({read:async()=>({done:false,value:new Uint8Array((++read===1?20:1)*1024*1024)}),
    cancel:async()=>{++cancelled;},releaseLock(){++released;}})}});
  assert.equal(await pending,false);assert.equal(cancelled,1);assert.equal(released,1);assert.equal(read,2);assert.equal(e.images.length,0);assert.equal(e.writes.length,0);
});
test('missing IndexedDB rejects persistence, releases a candidate and leaves default background unchanged',async()=>{
  const e=harness();e.context.indexedDB=undefined;await e.api.syncProject();assert.equal(e.state().message,'storage');
  assert.equal(await e.api.chooseFile(image()),false);assert.equal(e.state().enabled,false);assert.equal(e.urls.size,0);assert.equal(e.writes.length,0);assert.equal(e.body.style.backgroundImage,'');
});

 test('zero and 100 restore exactly, fullscreen uses inherited background, and disabled clears both',async()=>{
  const e=harness();await e.api.syncProject();await e.api.chooseFile(image());
  for(const strength of [0,100]){assert.equal(await e.api.editPreference({strength}),true);const reopened=harness(e.records);await reopened.api.syncProject();assert.equal(reopened.state().strength,strength);assert.equal(reopened.body.style.props.get('--mh-wallpaper-strength'),strength+'%');assert.match(reopened.body.style.props.get('--mh-wallpaper-background'),/linear-gradient.*blob:/);}
  assert.equal(await e.api.editPreference({enabled:false}),true);assert.equal(e.body.style.props.has('--mh-wallpaper-background'),false);
});
test('real template shares wallpaper with native and fallback fullscreen without changing text opacity',()=>{
  const template=fs.readFileSync(path.join(__dirname,'../../模板.html'),'utf8');
  assert.match(template,/body\[data-mh-wallpaper="on"\] :is\(:fullscreen,\.pvfs,\.rdfs,\.gmap-fs,\.cmx-fs,\.ad-fs,\.wt-fs\).*background-image:var\(--mh-wallpaper-background\)/);
  const css=template.match(/body\[data-mh-wallpaper="on"\] :is\(:fullscreen[^}]+}/)[0];assert.doesNotMatch(css,/(?:^|[;{])\s*(?:opacity|pointer-events|z-index|position)\s*:/);assert.match(css,/:not\(video\):not\(img\):not\(iframe\)/);
});
