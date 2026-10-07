/* 玉树世界树的只读渲染层。真实关系只来自 layout.js，不读取或写入业务数据。
 * Three.js 固定复用项目的 0.186.1；所有依赖和模型均从本地载入。
 */
import * as THREE from '/lib/three/three.module.js';
import { GLTFLoader } from '/lib/three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from '/lib/three/addons/controls/OrbitControls.js';
import { buildTreeLayout, describeMerges, visibleTreeEdges } from './layout.js?v=20261003-notes-1';

const MODEL_URL = new URL('./精简模型.glb', import.meta.url);
const CSS = `
[data-jade-tree]{display:flex;flex-direction:column;position:relative;min-height:320px;height:var(--overview-frame-height,min(72vh,46rem));background:var(--plane);overflow:hidden}
[data-jade-tree]:fullscreen{height:100vh;min-height:0;width:100vw;max-height:none;border-radius:0}
[data-jade-tree]:fullscreen .jt-viewport{min-height:0}
[data-jade-tree]:fullscreen > #note{position:fixed;z-index:100}
[data-jade-tree]:fullscreen .overview-height-corner{display:none}
[data-jade-tree] .jt-tools{display:flex;gap:.4rem;align-items:center;flex-wrap:nowrap;padding:.55rem .7rem;border-bottom:1px solid var(--line);background:var(--card)}
[data-jade-tree] .jt-tools button{white-space:nowrap;font-size:.75rem}
[data-jade-tree] .jt-tools button[aria-pressed=true]{border-color:var(--accent);background:var(--accent);color:var(--onaccent)}
[data-jade-tree] .jt-viewport{position:relative;flex:1;min-height:0;background:var(--plane);overflow:hidden}
[data-jade-tree] canvas{display:block;width:100%;height:100%;outline:none;cursor:grab}
[data-jade-tree] canvas:active{cursor:grabbing}
[data-jade-tree] canvas:focus-visible{outline:.13rem solid var(--accent);outline-offset:-.2rem}
[data-jade-tree] .jt-labels{position:absolute;inset:0;pointer-events:none}
[data-jade-tree] .jt-label{position:absolute;pointer-events:auto;transform:translate(.7rem,-50%);border:1px solid var(--line);border-radius:.25rem;padding:.13rem .3rem;font:inherit;font-size:.65rem;white-space:nowrap;color:var(--fg);background:var(--card);opacity:.94;cursor:pointer;max-width:17rem;overflow:hidden;text-overflow:ellipsis}
[data-jade-tree] .jt-label[aria-pressed=true]{border-color:var(--accent);font-weight:600}
[data-jade-tree] .jt-label:focus-visible,[data-jade-tree] .jt-merge:focus-visible{outline:.12rem solid var(--accent)}
[data-jade-tree] .jt-merge{position:absolute;pointer-events:auto;transform:translateX(.7rem);padding:.1rem .25rem;border:1px solid var(--line);border-radius:.2rem;max-width:24rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg2);background:var(--card);font:inherit;font-size:.6rem;cursor:pointer;opacity:.95}
[data-jade-tree] .jt-merge[aria-pressed=true]{border-color:var(--accent)}
[data-jade-tree] .jt-bottom{display:flex;gap:.8rem;align-items:center;justify-content:space-between;background:var(--card);border-top:1px solid var(--line);padding:.45rem .7rem;font-size:.72rem;line-height:1.5}
[data-jade-tree] .jt-select{display:flex;gap:.35rem;align-items:center;white-space:nowrap}
[data-jade-tree] .jt-select select{max-width:22rem;min-width:11rem;font:inherit;font-size:.7rem;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:.25rem;padding:.22rem .35rem}
[data-jade-tree] .jt-summary{color:var(--muted)}
[data-jade-tree] .jt-warnings{color:var(--crit);font-size:.72rem;background:var(--card);padding:0 .7rem .4rem;max-height:4rem;overflow:auto}
[data-jade-tree] .jt-warnings:empty{display:none}
[data-jade-tree] .jt-selected{font-size:.72rem;background:var(--card);padding:.35rem .7rem;border-top:1px solid var(--line);color:var(--fg2);display:flex;flex-direction:column;gap:.3rem;max-height:7rem;overflow:auto}
[data-jade-tree] .jt-selected-head{display:flex;gap:.5rem;align-items:center}
[data-jade-tree] .jt-selected-merge{display:flex;gap:.5rem;align-items:center;white-space:normal;overflow-wrap:anywhere}
[data-jade-tree] .jt-selected-merge span{flex:1}
[data-jade-tree] .jt-selected button{flex-shrink:0;font-size:.7rem}
[data-jade-tree] .jt-selected:empty{display:none}
[data-jade-tree] .jt-loading{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:var(--muted);font-size:.8rem;background:var(--card);padding:.5rem .8rem;pointer-events:none}
[data-jade-tree] .en{font-size:.85em;opacity:.76;margin-left:.15rem}
[data-jade-tree] .jt-bottom,[data-jade-tree] .jt-warnings{padding-right:1.5rem}
`;

function button(text, en, action, pressed) {
  const element = document.createElement('button');
  element.type = 'button'; element.className = 'sbtn'; element.dataset.action = action;
  element.append(document.createTextNode(text + ' '));
  const english = document.createElement('span');english.className='en';english.textContent=en;element.append(english);
  if (pressed !== undefined) element.setAttribute('aria-pressed', String(pressed));
  return element;
}

/** Reparent the existing notes element; never clone its fields or write to its storage. */
export function createNotesPortal(noteElement, owner) {
  const valid = noteElement instanceof Element && owner instanceof Element && noteElement !== owner && !noteElement.contains(owner);
  let placeholder = null, originalParent = null;
  function prepare() {
    if (!valid || placeholder) return;
    originalParent = noteElement.parentNode;
    if (!originalParent) return;
    placeholder = document.createComment('world-tree-notes-original-position');
    originalParent.insertBefore(placeholder, noteElement);
  }
  function mount() { if (!valid) return; prepare(); owner.append(noteElement); }
  function restore() {
    if (!valid || !placeholder) return;
    if (placeholder.parentNode?.isConnected) placeholder.parentNode.replaceChild(noteElement, placeholder);
    else (originalParent?.isConnected ? originalParent : document.body).append(noteElement);
    placeholder = null; originalParent = null;
  }
  return {prepare, mount, restore, snapshot:()=>({available:valid, ported:valid && noteElement.parentNode === owner, placeholder:Boolean(placeholder)})};
}

/** Only an explicit Open button may navigate; exiting this tree's fullscreen must succeed first. */
export async function openJadeTreeRecord(owner, selection, {onSelect, reportWarning = () => {}, isDisposed = () => false} = {}) {
  if(isDisposed())return false;
  if(document.fullscreenElement===owner){
    try{await document.exitFullscreen();}
    catch(error){reportWarning('无法退出全屏，仍留在世界树：'+error.message,error);return false;}
    if(document.fullscreenElement===owner){reportWarning('浏览器未退出世界树全屏，仍留在当前树');return false;}
  }
  if(isDisposed())return false;
  await onSelect(selection);return true;
}

/** The caller owns refresh scheduling and passes records from the existing APIs. */
export async function createJadeTree(host, options = {}) {
  if (!(host instanceof Element)) throw new TypeError('缺少世界树显示区域');
  const {nodes = [], branches = [], onSelect = () => {}, onStatus = () => {}, signal, activeSelected = null, noteElement = null, onNotes = null} = options;
  if (signal?.aborted) throw new DOMException('世界树载入已取消', 'AbortError');
  let disposed=false, layout=null, dynamic=null, frame=0, needsRender=true, selected=activeSelected, hovered=null, state='loading', modelLoaded=false;
  let lastTime=performance.now(), firstFit=true, labelsVisible=true, templates=null, mergeAnnotations=[], selectedMerge=null, fullscreenView=null, isFullscreen=false;
  const unbind=[], assetsGeometries=new Set(), assetsMaterials=new Set(), ownedMaterials=new Set();
  const selectedRoots=new Map(), labelEntries=[], runtimeWarnings=[];let fullscreenAttempts=0,fullscreenRequestContext=null;
  const aborter=new AbortController();
  const own=document.createElement('div');own.dataset.jadeTree='';
  const notesPortal=createNotesPortal(noteElement,own);
  const style=document.createElement('style');style.textContent=CSS;own.append(style);
  const tools=document.createElement('div');tools.className='jt-tools';
  [['front','正面','Front'],['side','侧面','Side'],['back','背面','Back'],['rotate','旋转','Rotate'],['labels','标签','Labels'],['fullscreen','全屏','Full screen'],['notes','笔记','Notes']].forEach(([action,zh,en])=>tools.append(button(zh,en,action,action==='front'||action==='labels')));
  own.append(tools);
  const fullscreenButton=tools.querySelector('[data-action=fullscreen]');
  const notesButton=tools.querySelector('[data-action=notes]');notesButton.disabled=typeof onNotes!=='function';
  const viewport=document.createElement('div');viewport.className='jt-viewport';
  const labelLayer=document.createElement('div');labelLayer.className='jt-labels';viewport.append(labelLayer);
  const loading=document.createElement('div');loading.className='jt-loading';loading.textContent='载入玉树 Loading jade tree';viewport.append(loading);own.append(viewport);
  const selectedLine=document.createElement('div');selectedLine.className='jt-selected';own.append(selectedLine);
  const bottom=document.createElement('div');bottom.className='jt-bottom';
  const summary=document.createElement('span');summary.className='jt-summary';summary.setAttribute('role','status');bottom.append(summary);
  const selectLabel=document.createElement('label');selectLabel.className='jt-select';selectLabel.append(document.createTextNode('选择节点 '));
  const english=document.createElement('span');english.className='en';english.textContent='Select node';selectLabel.append(english);
  const select=document.createElement('select');select.setAttribute('aria-label','选择世界树记录 Select a world tree record');selectLabel.append(select);bottom.append(selectLabel);own.append(bottom);
  const warnings=document.createElement('div');warnings.className='jt-warnings';warnings.setAttribute('role','status');own.append(warnings);
  host.append(own);
  let heightControl=null;
  if(typeof options.mountHeightControl==='function'){
    const corner=document.createElement('button');corner.type='button';corner.className='overview-height-corner';corner.dataset.jtHeight='';corner.title='调整总览高度 Resize overview height';corner.setAttribute('aria-label','拖动或用上下方向键调整玉树高度 Drag or use up/down keys to resize jade tree height');corner.innerHTML='<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 10 10 3M7 10 10 7" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>';own.append(corner);
    heightControl=options.mountHeightControl({target:own,handle:corner,projectRoot:options.projectRoot,scope:'archives:jade3d',isFullscreen:()=>document.fullscreenElement===own,isCurrent:()=>!disposed&&own.isConnected});
  }

  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(38,1,.01,500);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.06;
  viewport.insertBefore(renderer.domElement,viewport.firstChild);renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label','玉树模型，拖动旋转，滚轮缩放 Jade tree model');
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.09;controls.autoRotateSpeed=.35;controls.maxPolarAngle=Math.PI*.52;
  controls.enablePan=true;
  const hemi=new THREE.HemisphereLight(0xf3faff,0x88755a,2);scene.add(hemi);
  const key=new THREE.DirectionalLight(0xffefd0,3.3);key.position.set(-7,16,10);scene.add(key);
  const rim=new THREE.DirectionalLight(0xc9e5ff,2.7);rim.position.set(8,9,-8);scene.add(rim);
  const fill=new THREE.DirectionalLight(0xffffff,.7);fill.position.set(2,1,8);scene.add(fill);
  const envScene=new THREE.Scene();envScene.background=new THREE.Color(0xdbe6e8);
  const envGeometries=[],envMaterials=[];
  for(const [x,y,z,color,rotation] of [[-8,8,0,0xfff2dc,Math.PI/2],[8,5,0,0xe6f3ff,-Math.PI/2],[0,10,-8,0xffffff,0]]){
    const geometry=new THREE.PlaneGeometry(12,16),material=new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide});envGeometries.push(geometry);envMaterials.push(material);
    const panel=new THREE.Mesh(geometry,material);panel.position.set(x,y,z);panel.rotation.y=rotation;envScene.add(panel);
  }
  const pmrem=new THREE.PMREMGenerator(renderer);const environment=pmrem.fromScene(envScene,.06);scene.environment=environment.texture;scene.environmentIntensity=.85;
  pmrem.dispose();envGeometries.forEach(x=>x.dispose());envMaterials.forEach(x=>x.dispose());

  function bind(target,type,handler,settings){target.addEventListener(type,handler,settings);unbind.push(()=>target.removeEventListener(type,handler,settings));}
  function css(variable,fallback){return getComputedStyle(document.documentElement).getPropertyValue(variable).trim()||fallback;}
  function material(color,other={}){const mat=new THREE.MeshStandardMaterial({color,roughness:.32,metalness:.68,...other});ownedMaterials.add(mat);return mat;}
  const bronze=material(0x657d78),gold=material(0xb48b47,{roughness:.28,metalness:.82});
  const good=material(css('--good','#0ca30c'),{roughness:.36,metalness:.15});
  const warn=material(css('--warn','#fab219'),{roughness:.36,metalness:.15});
  const muted=material(css('--muted','#6b6b6b'),{roughness:.55,metalness:.15});
  const bad=material(css('--crit','#d03b3b'),{roughness:.42,metalness:.1});
  const nodeIndex=()=>new Map((layout?.nodes||[]).map(n=>[n.id,n]));
  // 混合编号的尾部，让相邻 C 号也展开在树冠各侧；只影响摆放，不代表业务关系。
  const displayAngle=id=>{let h=2166136261;for(const char of id){h^=char.charCodeAt(0);h=Math.imul(h,16777619);}h^=h>>>16;h=Math.imul(h,0x85ebca6b);h^=h>>>13;h=Math.imul(h,0xc2b2ae35);h^=h>>>16;return(h>>>0)/4294967296*Math.PI*2;};
  const vector=n=>n.kind==='checkpoint'?new THREE.Vector3(Math.cos(displayAngle(n.id))*2.65,n.y,Math.sin(displayAngle(n.id))*2.65):new THREE.Vector3(n.x*(n.kind==='branch'||n.kind==='fruit'?1.18:1),n.y,n.z*(n.kind==='branch'||n.kind==='fruit'?1.18:1));
  const statusMaterial=n=>n.kind==='missing'||n.checkStatus==='failed'?bad:n.status==='砍了'||n.status==='合了'||n.status==='果实历史'?muted:n.checkStatus==='passed'||n.checkStatus==='recorded_passed'?good:warn;

  function resourceDispose(root){
    if(!root)return;const geometries=new Set(),materials=new Set();
    root.traverse(object=>{if(object.geometry&&!assetsGeometries.has(object.geometry))geometries.add(object.geometry);for(const mat of Array.isArray(object.material)?object.material:object.material?[object.material]:[])if(!assetsMaterials.has(mat)&&!ownedMaterials.has(mat))materials.add(mat);});
    geometries.forEach(x=>x.dispose());materials.forEach(x=>x.dispose());
  }
  function cloneAsset(name,parent,height,position){
    const original=templates[name];if(!original)return null;
    const clone=original.clone(true);clone.position.set(0,0,0);clone.quaternion.identity();clone.scale.set(1,1,1);clone.updateMatrixWorld(true);
    const box=new THREE.Box3().setFromObject(clone),size=box.getSize(new THREE.Vector3());
    if(height)clone.scale.multiplyScalar(height/Math.max(size.y,.001));
    if(position)clone.position.copy(position);parent.add(clone);return clone;
  }
  function cylinder(parent,y0,y1,radius,mat){if(y1<=y0)return null;const mesh=new THREE.Mesh(new THREE.CylinderGeometry(radius*.78,radius,y1-y0,24),mat);mesh.position.y=(y0+y1)/2;parent.add(mesh);return mesh;}
  function tube(parent,points,radius,mat,dashed=false){
    const curve=new THREE.CatmullRomCurve3(points);
    if(dashed){const geometry=new THREE.BufferGeometry().setFromPoints(curve.getPoints(28));const lineMat=new THREE.LineDashedMaterial({color:css('--crit','#d03b3b'),dashSize:.12,gapSize:.09,transparent:true,opacity:.65});const line=new THREE.Line(geometry,lineMat);line.computeLineDistances();parent.add(line);return line;}
    const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,28,radius,8,false),mat);parent.add(mesh);return mesh;
  }
  function safeSelection(n){return {id:n.id,kind:n.kind,code:n.code,branch:n.branch||(n.kind==='branch'?n.code:n.kind==='fruit'?n.source:undefined),source:n.source,record:n.record,status:n.status,checkStatus:n.checkStatus};}
  function mergeDetail(annotation, parent) {
    const row=document.createElement('div');row.className='jt-selected-merge';
    const text=document.createElement('span');text.textContent=annotation.fullLabel;row.append(text);
    const open=button('查看果实','Open fruit','open-merge-fruit');open.title=annotation.fullLabel;
    open.addEventListener('click',()=>explicitOpen(annotation.selection));row.append(open);parent.append(row);
  }
  function showSelected(){
    selectedLine.replaceChildren();const n=nodeIndex().get(selected);select.value=n?n.id:'';
    labelEntries.forEach(entry=>{entry.element.setAttribute('aria-pressed',String(entry.node.id===selected));entry.element.textContent=entry.node.id===selected||entry.node.id===hovered?entry.node.label+' · '+entry.node.status:shortLabel(entry.node);for(const annotation of entry.annotations||[])annotation.element.setAttribute('aria-pressed',String(annotation.record.id===selectedMerge));});
    selectedRoots.forEach((root,id)=>{const ring=root.getObjectByName('status-ring');if(ring)ring.scale.setScalar(id===selected?1.22:1);});
    if(n){
      const head=document.createElement('div');head.className='jt-selected-head';
      const detail=document.createElement('span');detail.textContent=n.label+' · '+n.status+' · '+n.checkLabel+(n.settled?' · 安全点已定性':'')+(n.kind==='fruit'?' · 枝内存档':'')+(n.missingBase?' · 来源档缺失':'');head.append(detail);
      if(n.kind!=='missing'){const open=button('打开记录','Open record','open-selected');open.addEventListener('click',()=>explicitOpen(safeSelection(n)));head.append(open);}
      selectedLine.append(head);
      const related=mergeAnnotations.filter(annotation=>annotation.targetId===n.id||(n.kind==='fruit'&&annotation.sourceId===n.id));
      for(const annotation of related)mergeDetail(annotation,selectedLine);
      if(n.kind==='fruit'&&!related.length&&n.record?.demo){const text=document.createElement('span');text.textContent='Demo：'+n.record.demo;selectedLine.append(text);}
    }
    const annotation=mergeAnnotations.find(item=>item.id===selectedMerge);
    if(annotation&&(!n||annotation.targetId!==n.id&&annotation.sourceId!==n.id))mergeDetail(annotation,selectedLine);
    needsRender=true;
  }
  function choose(id){const n=nodeIndex().get(id);if(!n)return;selected=id;selectedMerge=null;showSelected();}
  function chooseMerge(annotation){selectedMerge=annotation.id;selected=nodeIndex().has(annotation.sourceId)?annotation.sourceId:annotation.targetId;showSelected();}
  function cameraFit(angle=0,elevation=null){
    if(!layout)return;
    const bounds=new THREE.Box3().setFromObject(dynamic);const size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());
    const vertical=THREE.MathUtils.degToRad(camera.fov),horizontal=2*Math.atan(Math.tan(vertical/2)*camera.aspect);
    const distance=Math.max(size.y/2/Math.tan(vertical/2),Math.max(size.x,size.z)/2/Math.tan(horizontal/2))*1.12;
    const pitch=elevation===null?Math.atan2(size.y*.04,distance):THREE.MathUtils.clamp(elevation,-.03,Math.PI*.48);
    const flat=Math.cos(pitch)*distance;camera.position.set(center.x+Math.sin(angle)*flat,center.y+Math.sin(pitch)*distance,center.z+Math.cos(angle)*flat);controls.target.copy(center);
    controls.minDistance=Math.max(1,size.y*.22);controls.maxDistance=Math.max(30,size.y*5);camera.near=Math.max(.005,size.y/5000);camera.far=Math.max(100,size.y*40);camera.updateProjectionMatrix();controls.update();needsRender=true;
  }
  function shortLabel(node){return node.kind==='fruit'?node.source+' / '+node.code:node.kind==='now'?'现在 · 未存档':node.kind==='missing'?(node.code||'来源')+' · 缺失':node.code;}
  function labelFor(node,root){
    const element=document.createElement('button');element.type='button';element.className='jt-label';element.dataset.nodeId=node.id;element.textContent=shortLabel(node);element.title=node.label+' · '+node.status+' · '+node.checkLabel;element.setAttribute('aria-pressed',String(node.id===selected));
    element.addEventListener('click',()=>choose(node.id));element.addEventListener('pointerenter',()=>{hovered=node.id;showSelected();});element.addEventListener('pointerleave',()=>{hovered=null;showSelected();});element.addEventListener('focus',()=>{hovered=node.id;showSelected();});element.addEventListener('blur',()=>{hovered=null;showSelected();});labelLayer.append(element);labelEntries.push({element,node,position:vector(node).add(new THREE.Vector3(0,node.kind==='now'?.5:.3,0))});
    root.userData.worldTreeNodeId=node.id;root.traverse(object=>{object.userData.worldTreeNodeId=node.id;});selectedRoots.set(node.id,root);
  }
  function rebuild(nextNodes,nextBranches){
    if(disposed)return;
    const nextLayout=buildTreeLayout(nextNodes,nextBranches);
    mergeAnnotations=describeMerges(nextNodes,nextBranches);
    if(dynamic){scene.remove(dynamic);resourceDispose(dynamic);}dynamic=new THREE.Group();scene.add(dynamic);layout=nextLayout;
    labelEntries.splice(0);selectedRoots.clear();labelLayer.replaceChildren();select.replaceChildren();
    const empty=document.createElement('option');empty.value='';empty.textContent='选择节点 Select node';select.append(empty);
    const now=layout.nodes.find(n=>n.kind==='now');const treeTop=now?.y??Math.max(2.5,layout.height-1.2);
    const base=cloneAsset('asset_base',dynamic,1.45,new THREE.Vector3(0,0,0));
    const baseSize=base?new THREE.Box3().setFromObject(base).getSize(new THREE.Vector3()):new THREE.Vector3(5,1,5);
    cylinder(dynamic,.7,treeTop,.19,bronze);
    const helix=[];for(let i=0;i<=96;i++){const t=i/96,angle=t*Math.PI*5;helix.push(new THREE.Vector3(Math.cos(angle)*.205,.8+t*Math.max(treeTop-.9,.5),Math.sin(angle)*.205));}tube(dynamic,helix,.018,gold);
    // 鸟、龙、飘带只作造型，不参与记录计数、关系或点击。
    cloneAsset('asset_dragon',dynamic,Math.min(6,treeTop*.66),new THREE.Vector3(0,Math.max(2.1,treeTop*.45),0));
    cloneAsset('asset_birds',dynamic,Math.min(4.8,treeTop*.42),new THREE.Vector3(0,treeTop*.64,0));
    const ribbons=cloneAsset('asset_ribbons',dynamic,Math.min(2.3,treeTop*.23),new THREE.Vector3(0,1.8,0));if(ribbons)ribbons.scale.multiplyScalar(Math.min(1.15,Math.max(.8,baseSize.x/5)));
    for(const n of layout.nodes){
      const root=new THREE.Group();dynamic.add(root);root.position.copy(vector(n));
      if(n.kind==='now'){cloneAsset('asset_crown',root,1.35,new THREE.Vector3());}
      else if(n.kind==='missing'){const ghost=new THREE.Mesh(new THREE.OctahedronGeometry(.15,0),new THREE.MeshBasicMaterial({color:css('--crit','#d03b3b'),wireframe:true,transparent:true,opacity:.7}));root.add(ghost);}
      else {cloneAsset('asset_lotus',root,n.kind==='checkpoint'?.92:n.kind==='fruit'?.88:.65,new THREE.Vector3());const ring=new THREE.Mesh(new THREE.TorusGeometry(n.kind==='branch'?.23:.31,.015,6,32),statusMaterial(n));ring.rotation.x=Math.PI/2;ring.name='status-ring';root.add(ring);}
      if(n.kind==='checkpoint'){const tip=vector(n);tube(dynamic,[new THREE.Vector3(0,n.y-.38,0),new THREE.Vector3(tip.x*.5,n.y-.32,tip.z*.5),tip],.055,gold);const band=new THREE.Mesh(new THREE.TorusGeometry(.2,.022,6,28),gold);band.rotation.x=Math.PI/2;band.position.y=n.y-.35;dynamic.add(band);}
      labelFor(n,root);
      const option=document.createElement('option');option.value=n.id;option.textContent=n.label+' · '+n.status;select.append(option);
    }
    const index=nodeIndex();
    for(const edge of visibleTreeEdges(layout)){
      // 时间线通过主干短枝呈现；合并保留文字与真实关系，不绘连线。
      const from=index.get(edge.from),to=index.get(edge.to);if(!from||!to)continue;
      const p0=vector(from).add(new THREE.Vector3(0,.12,0)),p2=vector(to);
      const p1=p0.clone().lerp(p2,.5);p1.y+=.12;
      tube(dynamic,[p0,p1,p2],edge.kind==='fruit'?.022:.037,gold,Boolean(edge.missing)||from.status==='砍了'||to.status==='砍了');
    }
    for(const entry of labelEntries){
      entry.annotations=[];
      for(const annotation of mergeAnnotations.filter(item=>item.targetId===entry.node.id)){
        const element=document.createElement('button');element.type='button';element.className='jt-merge';element.dataset.mergeId=annotation.id;element.textContent=annotation.label;element.title=annotation.fullLabel;element.setAttribute('aria-label',annotation.fullLabel);element.setAttribute('aria-pressed',String(annotation.id===selectedMerge));
        element.addEventListener('click',()=>chooseMerge(annotation));labelLayer.append(element);entry.annotations.push({element,record:annotation});
      }
    }
    warnings.replaceChildren();for(const item of layout.missing){const line=document.createElement('div');line.textContent=(item.branch?item.branch+' · ':'')+item.message;warnings.append(line);}
    for(const annotation of mergeAnnotations){
      if(annotation.targetId&&index.has(annotation.targetId))continue;
      const line=document.createElement('div');line.textContent=annotation.fullLabel+' ';const open=button('查看果实','Open fruit','open-merge-fruit');open.addEventListener('click',()=>{chooseMerge(annotation);explicitOpen(annotation.selection);});line.append(open);warnings.append(line);
    }
    paintRuntimeWarnings();
    if(selectedMerge&&!mergeAnnotations.some(item=>item.id===selectedMerge))selectedMerge=null;
    const fruitCount=layout.nodes.filter(n=>n.kind==='fruit').length;
    summary.textContent=layout.checkpointCount+' 档 Checkpoints · '+layout.branchCount+' 枝 Branches · '+fruitCount+' 果实 Fruits · 现在未存档';
    if(!index.has(selected))selected=null;showSelected();
    camera.far=Math.max(100,layout.height*40);camera.updateProjectionMatrix();
    if(firstFit){cameraFit(0);firstFit=false;}else needsRender=true;
    onStatus({state:'ready',message:'真实存档节点已更新',snapshot:snapshot()});
  }
  const projected=new THREE.Vector3();
  function updateLabels(){
    for(const entry of labelEntries){
      projected.copy(entry.position).project(camera);const visible=labelsVisible&&projected.z>=-1&&projected.z<=1&&Math.abs(projected.x)<1.1&&Math.abs(projected.y)<1.1;
      entry.element.hidden=!visible;
      const left=((projected.x+1)*.5*viewport.clientWidth),top=((1-projected.y)*.5*viewport.clientHeight);
      if(visible){entry.element.style.left=left+'px';entry.element.style.top=top+'px';}
      for(const [i,annotation] of (entry.annotations||[]).entries()){
        annotation.element.hidden=!visible;
        if(visible){annotation.element.style.left=left+'px';annotation.element.style.top=(top+12+i*20)+'px';}
      }
    }
  }
  function snapshot(){return {state,modelLoaded,modelURL:MODEL_URL.href,checkpoints:layout?.checkpointCount||0,branches:layout?.branchCount||0,fruits:layout?.nodes.filter(n=>n.kind==='fruit').length||0,now:layout?.nodes.filter(n=>n.kind==='now').length||0,missing:layout?.missing||[],selected,selectedMerge,ids:layout?.nodes.map(n=>n.id)||[],height:layout?.height||0,frameHeight:heightControl?.state().height??null,camera:{position:camera.position.toArray(),target:controls.target.toArray()},nodes:layout?.nodes.map(n=>({id:n.id,kind:n.kind,code:n.code,source:n.source,position:vector(n).toArray(),layoutPosition:[n.x,n.y,n.z],status:n.status,checkStatus:n.checkStatus}))||[],mergeAnnotations:mergeAnnotations.map(({id,branch,after,fruitCode,demo,targetId,sourceId,missingTarget,missingFruit,missingRecord})=>({id,branch,after,fruitCode,demo,targetId,sourceId,missingTarget,missingFruit,missingRecord})),mergeLines:0,fullscreen:document.fullscreenElement===own,fullscreenAttempts,runtimeWarnings:runtimeWarnings.map(item=>({message:item.message,details:item.details})),notes:notesPortal.snapshot(),frames:renderer.info.render.frame,disposed};}
  function captureView(){const offset=camera.position.clone().sub(controls.target);return {position:camera.position.clone(),target:controls.target.clone(),zoom:camera.zoom,autoRotate:controls.autoRotate,angle:Math.atan2(offset.x,offset.z),elevation:Math.atan2(offset.y,Math.hypot(offset.x,offset.z))};}
  function restoreView(saved){
    if(!saved)return;
    // Flush damping through the public controls API before restoring the exact saved pose.
    const damping=controls.enableDamping;controls.enableDamping=false;controls.autoRotate=false;controls.update();
    camera.position.copy(saved.position);camera.zoom=saved.zoom;controls.target.copy(saved.target);camera.updateProjectionMatrix();controls.update();controls.enableDamping=damping;controls.autoRotate=saved.autoRotate;
    tools.querySelector('[data-action=rotate]').setAttribute('aria-pressed',String(controls.autoRotate));needsRender=true;
  }
  function fullscreenLabel(){
    const active=document.fullscreenElement===own;fullscreenButton.replaceChildren(document.createTextNode(active?'退出全屏 ':'全屏 '));const en=document.createElement('span');en.className='en';en.textContent=active?'Exit full screen':'Full screen';fullscreenButton.append(en);fullscreenButton.setAttribute('aria-pressed',String(active));
  }
  function paintRuntimeWarnings(){
    for(const previous of warnings.querySelectorAll('[data-jt-warning]'))previous.remove();
    for(const item of runtimeWarnings){const line=document.createElement('div');line.dataset.jtWarning='';line.setAttribute('role','alert');line.textContent=item.message;line.title=JSON.stringify(item.details);warnings.append(line);}
    if(runtimeWarnings.length)warnings.scrollTop=warnings.scrollHeight;
  }
  function reportFullscreenWarning(message,error){
    if(disposed)return;
    const details={errorName:error?.name||'',errorMessage:error?.message||'',fullscreenEnabled:document.fullscreenEnabled,fullscreenElement:document.fullscreenElement?.tagName||null,elementConnected:own.isConnected,userActivation:globalThis.navigator?.userActivation?.isActive??null,requestContext:fullscreenRequestContext,attempt:fullscreenAttempts};
    const visible=message+(error?.name?' · '+error.name:'');runtimeWarnings.push({message:visible,details});if(runtimeWarnings.length>5)runtimeWarnings.shift();paintRuntimeWarnings();onStatus({state:'warning',message:visible,details,snapshot:snapshot()});
  }
  function explicitOpen(selection){return openJadeTreeRecord(own,selection,{onSelect,reportWarning:reportFullscreenWarning,isDisposed:()=>disposed});}
  async function toggleFullscreen(){
    fullscreenAttempts++;own.dataset.fullscreenAttempts=String(fullscreenAttempts);
    const policy=document.permissionsPolicy||document.featurePolicy;fullscreenRequestContext={userActivation:globalThis.navigator?.userActivation?.isActive??null,fullscreenEnabled:document.fullscreenEnabled,elementConnected:own.isConnected,documentFocused:document.hasFocus(),policyAllowsFullscreen:typeof policy?.allowsFeature==='function'?policy.allowsFeature('fullscreen'):null};
    if(document.fullscreenElement===own){try{await document.exitFullscreen();if(document.fullscreenElement===own)reportFullscreenWarning('浏览器未退出世界树全屏');}catch(error){reportFullscreenWarning('无法退出全屏：'+error.message,error);}return;}
    if(document.fullscreenElement){reportFullscreenWarning('当前其他区域处于全屏，请先退出');return;}
    if(typeof own.requestFullscreen!=='function'){reportFullscreenWarning('当前浏览器不能进入全屏（requestFullscreen 不可用）');return;}
    fullscreenView=captureView();notesPortal.prepare();
    try{await own.requestFullscreen();if(!disposed&&document.fullscreenElement!==own){fullscreenView=null;notesPortal.restore();reportFullscreenWarning('浏览器没有进入世界树全屏');}}
    catch(error){fullscreenView=null;notesPortal.restore();reportFullscreenWarning('无法进入全屏：'+error.message,error);}
  }
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let pointerDown=null;
  function hit(event){const rect=renderer.domElement.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const found=raycaster.intersectObjects([...selectedRoots.values()],true)[0];return found?.object.userData.worldTreeNodeId;}
  bind(renderer.domElement,'pointerdown',event=>{if(event.button===0)pointerDown={x:event.clientX,y:event.clientY,id:event.pointerId};});
  bind(renderer.domElement,'pointerup',event=>{const start=pointerDown;pointerDown=null;if(start&&start.id===event.pointerId&&Math.hypot(event.clientX-start.x,event.clientY-start.y)<4){const id=hit(event);if(id)choose(id);}});
  bind(renderer.domElement,'pointercancel',()=>pointerDown=null);
  bind(renderer.domElement,'pointermove',event=>{if(!pointerDown){const id=hit(event);renderer.domElement.style.cursor=id?'pointer':'grab';if(hovered!==(id||null)){hovered=id||null;showSelected();}}});
  bind(renderer.domElement,'pointerleave',()=>{hovered=null;showSelected();});
  bind(renderer.domElement,'keydown',event=>{if(event.key==='Escape'&&document.fullscreenElement!==own){selected=null;selectedMerge=null;showSelected();}});
  bind(select,'change',()=>choose(select.value));
  bind(tools,'click',event=>{const clicked=event.target.closest('[data-action]');if(!clicked)return;const action=clicked.dataset.action;
    if(['front','side','back'].includes(action)){controls.autoRotate=false;cameraFit(action==='side'?Math.PI/2:action==='back'?Math.PI:0);tools.querySelectorAll('[data-action]').forEach(b=>{if(['front','side','back','rotate'].includes(b.dataset.action))b.setAttribute('aria-pressed',String(b===clicked));});}
    else if(action==='rotate'){controls.autoRotate=!controls.autoRotate;clicked.setAttribute('aria-pressed',String(controls.autoRotate));needsRender=true;}
    else if(action==='labels'){labelsVisible=!labelsVisible;clicked.setAttribute('aria-pressed',String(labelsVisible));needsRender=true;}
    else if(action==='fullscreen'){toggleFullscreen();}
    else if(action==='notes'){if(typeof onNotes==='function')onNotes();}
  });
  controls.addEventListener('change',()=>needsRender=true);
  const resize=()=>{if(disposed)return;const width=viewport.clientWidth,height=viewport.clientHeight;if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();needsRender=true;};
  const observer=new ResizeObserver(resize);observer.observe(viewport);resize();
  bind(document,'fullscreenchange',()=>{
    const active=document.fullscreenElement===own;fullscreenLabel();
    heightControl?.sync();
    if(active&&!isFullscreen){isFullscreen=true;notesPortal.mount();resize();if(fullscreenView)cameraFit(fullscreenView.angle,fullscreenView.elevation);}
    else if(!active&&isFullscreen){isFullscreen=false;notesPortal.restore();resize();restoreView(fullscreenView);fullscreenView=null;}
  });
  fullscreenLabel();
  const mutationObserver=new MutationObserver(()=>{if(disposed)return;scene.background=new THREE.Color(css('--plane','#fafafa'));needsRender=true;});mutationObserver.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme','data-skin','style']});
  scene.background=new THREE.Color(css('--plane','#fafafa'));
  function tick(time){if(disposed)return;const delta=Math.min(.1,Math.max(0,(time-lastTime)/1000));lastTime=time;const changed=controls.update(delta);if(needsRender||changed||controls.autoRotate){renderer.render(scene,camera);updateLabels();needsRender=false;}frame=requestAnimationFrame(tick);}
  function dispose(){
    if(disposed)return;disposed=true;state='disposed';heightControl?.destroy();notesPortal.restore();if(document.fullscreenElement===own&&typeof document.exitFullscreen==='function'){notesPortal.prepare();document.exitFullscreen().then(()=>notesPortal.restore(),()=>notesPortal.restore());}aborter.abort();cancelAnimationFrame(frame);observer.disconnect();mutationObserver.disconnect();unbind.forEach(fn=>fn());controls.dispose();resourceDispose(dynamic);ownedMaterials.forEach(x=>x.dispose());assetsGeometries.forEach(x=>x.dispose());assetsMaterials.forEach(x=>x.dispose());environment.dispose();renderer.dispose();own.remove();
  }
  if(signal)bind(signal,'abort',dispose,{once:true});
  onStatus({state:'loading',message:'载入玉树模型'});
  try{
    const response=await fetch(MODEL_URL,{signal:aborter.signal});if(!response.ok)throw new Error('模型文件载入失败 HTTP '+response.status);
    const gltf=await new GLTFLoader().parseAsync(await response.arrayBuffer(),'');
    if(disposed){gltf.scene.traverse(o=>{o.geometry?.dispose();for(const mat of Array.isArray(o.material)?o.material:o.material?[o.material]:[])mat.dispose();});throw new DOMException('世界树载入已取消','AbortError');}
    gltf.scene.traverse(o=>{if(o.geometry)assetsGeometries.add(o.geometry);for(const mat of Array.isArray(o.material)?o.material:o.material?[o.material]:[])assetsMaterials.add(mat);});
    templates={};for(const name of ['asset_base','asset_crown','asset_birds','asset_dragon','asset_ribbons','asset_lotus']){const asset=gltf.scene.getObjectByName(name);if(asset)templates[name]=asset;}
    if(!templates.asset_lotus||!templates.asset_crown)throw new Error('模型缺少莲花节点或顶部冠珠模板');
    modelLoaded=true;state='ready';loading.remove();rebuild(nodes,branches);frame=requestAnimationFrame(tick);
    return {update:rebuild,dispose,snapshot};
  }catch(error){if(!disposed){state='error';onStatus({state:'error',message:error.message});dispose();}throw error;}
}
