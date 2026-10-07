'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..'),html=fs.readFileSync(path.join(root,'模板.html'),'utf8');
function block(first,last){const a=html.indexOf(first),b=html.indexOf(last,a);assert.ok(a>=0&&b>a,first);return html.slice(a,b);}
const code=block('function guideAsset(','function guideRoutes(')
  +block('function guideRoutes(','function guideRouteButtons(')
  +block('function guideSafeUrl(','function guideCheckButton(')
  +block('function toolResourceCells(','function renderToolResourceGuide(');
const context={URL,console,encodeURIComponent,getLang:()=> 'zh',renderMd:text=>text,
  purl:value=>'files?path='+encodeURIComponent(value),esc:value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))};
vm.createContext(context);vm.runInContext(code,context);
const catalog=JSON.parse(fs.readFileSync(path.join(root,'工具库/安装指南/catalog.json'),'utf8')).items;
function walk(folder){return fs.readdirSync(folder,{withFileTypes:true}).flatMap(item=>{const file=path.join(folder,item.name);return item.isDirectory()?walk(file):[file];});}
function document(relative){const text=fs.readFileSync(path.join(root,relative),'utf8'),resources=[],seen=new Set();
  for(const match of text.matchAll(/(!?)\[[^\[\]\n]*\]\(<?([^\n]*?)>?\)/g)){
    const source=match[2].replace(/\s+["'][^"']*["']$/,'').trim().replace(/^<|>$/g,'');
    if(seen.has(source)||/^\w+:|^\/\/|^#/.test(source))continue;seen.add(source);
    const decoded=decodeURIComponent(source),target=path.posix.normalize(/^(工具库\/安装指南\/|品牌\/|插件\/)/.test(decoded)?decoded:path.posix.join(path.posix.dirname(relative),decoded));
    if(fs.existsSync(path.join(root,target)))resources.push({source,target,kind:match[1]?'image':'document'});
  }
  return{text,resources};
}

test('current catalog assets, guides and regional routes all survive the directory migration',()=>{
  let checked=0;
  for(const item of catalog){
    for(const field of ['image','logo','guide'])if(item[field]){
      assert.ok(fs.existsSync(path.join(root,item[field])),item[field]);
      assert.equal(context.guideSafePath(item[field]),true,item[field]);checked++;
      if(field!=='guide')assert.equal(context.guideAsset(item,field),context.purl(item[field]));
    }
    assert.equal(context.guideRoutes(item).length,(item.routes||[]).length,item.id);
    for(const route of item.routes||[]){assert.equal(context.guideSafePath(route.guide),true,route.guide);checked++;}
  }
  // A public package may omit third-party pictures while keeping every guide.
  assert.ok(checked>=catalog.length);
});

test('all existing local guide images render through the production Markdown renderer',()=>{
  const documents=walk(path.join(root,'工具库/安装指南')).filter(file=>file.endsWith('.md'));
  let images=0;
  for(const file of documents){const relative=path.relative(root,file).split(path.sep).join('/'),doc=document(relative);
    for(const match of doc.text.matchAll(/!\[[^\[\]\n]*\]\(<?([^\n]*?)>?\)/g)){
      const source=match[1].replace(/\s+["'][^"']*["']$/,'').trim().replace(/^<|>$/g,'');
      if(/^\w+:|^\/\/|^#/.test(source))continue;
      const decoded=decodeURIComponent(source),target=path.posix.normalize(/^(工具库\/安装指南\/|品牌\/|插件\/)/.test(decoded)?decoded:path.posix.join(path.posix.dirname(relative),decoded));
      assert.ok(fs.existsSync(path.join(root,target)),relative+' has a missing image '+source);
    }
    const rendered=context.renderToolGuide(doc);
    for(const resource of doc.resources.filter(r=>r.kind==='image')){
      assert.equal(context.guideSafePath(resource.target),true,relative+' -> '+resource.target);
      assert.ok(rendered.includes(context.esc(context.purl(resource.target))),relative+' should render '+resource.target);images++;
    }
  }
  assert.ok(images>0,'original illustrations should remain in the public guides');
});

test('repository and website cards display their current local pictures instead of missing-reference labels',()=>{
  for(const [relative,section,expected] of [['工具库/安装指南/参考/开源项目.md','s:oss',24],['工具库/安装指南/参考/网页链接.md','s:links',64]]){
    const doc=document(relative),parsed=context.toolResourceRecords(doc,section),guide=catalog.find(item=>item.section===section);
    assert.equal(parsed.items.length,expected);assert.equal(parsed.errors.length,0);
    for(const record of parsed.items){const picture=context.toolResourcePicture(record,doc);
      assert.equal(picture.missing,false,record.name);
      const card=context.toolResourceCard(record,doc,guide);
      assert.ok(card.includes(context.esc(record.url)),record.name+' keeps its official entry');
      if(record.image && !['-','—'].includes(record.image)){
        assert.ok(picture.url,record.name);assert.ok(card.includes(context.esc(picture.url)),record.name);
      }
      assert.equal(card.includes('图片引用无法读取'),false,record.name);
    }
  }
});

test('local source documents and the three explicit plugin guides remain navigable',()=>{
  for(const relative of ['插件/网页终端/安装指南.md','插件/PPT预览/安装指南.md','插件/剪辑/安装指南.md'])assert.equal(context.guideSafePath(relative),true);
  const doc={text:'[图源](来源.md)',resources:[{source:'来源.md',target:'工具库/安装指南/应用图片/来源.md',kind:'document'}]};
  assert.match(context.renderToolGuide(doc),/data-tool-doc="工具库\/安装指南\/应用图片\/来源.md"/);
});

test('remote assets, paths outside the approved roots and encoded traversal still fail',()=>{
  for(const value of [null,{},'https://example.com/logo.svg','//example.com/logo.svg','C:/secret.png','笔记/私人.png',
    '工具库/未批准/图.png','插件/别的插件/安装指南.md','工具库/安装指南/../秘密.png','工具库/安装指南/./图.svg',
    '工具库/安装指南/%2e%2e/秘密.svg','工具库/安装指南/a%2fb.svg','工具库/安装指南/a%5cb.svg',
    '工具库/安装指南/a\\b.svg','工具库/安装指南/图.svg?secret=1','工具库/安装指南/图.svg#fragment']){
    assert.equal(context.guideSafePath(value),false,String(value));assert.equal(context.guideAsset({image:value},'image'),'');
  }
});
