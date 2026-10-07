/* Ordinary content files; reading never launches a tool or an employee. */
(function (global) {
  'use strict';
  const drafts = new Map();
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const keyOf = (root, module, path) => JSON.stringify([root, module, path]);
  const normalRoot = root => String(root || '').replace(/\\/g, '/').replace(/\/$/, '').toLowerCase();
  function putDraft(key, value, storage) {
    const snapshot = Object.assign({}, value);
    drafts.set(key, snapshot);
    try { storage && storage.setItem('content-draft:' + key, JSON.stringify(snapshot)); } catch (_) {}
  }
  function getDraft(key, storage) {
    if (drafts.has(key)) return drafts.get(key);
    try { const value = JSON.parse(storage && storage.getItem('content-draft:' + key) || 'null'); if (value && typeof value.text === 'string') return value; } catch (_) {}
    return null;
  }
  function dropDraft(key, storage) {
    drafts.delete(key);
    try { storage && storage.removeItem('content-draft:' + key); } catch (_) {}
  }
  function mount(host, options) {
    const o = options || {}, root = normalRoot(o.projectRoot), module = o.module;
    let disposed = false, serial = 0, pending = 0, workspace = null, editor = null, editorOrigin = '', preparing = null;
    const storage = o.storage === undefined ? global.sessionStorage : o.storage;
    const preparationKey = keyOf(root, module, '#preparing');
    const w = (zh, en) => o.language && o.language() === 'en' ? en : zh;
    const live = () => !disposed && host.isConnected && (!o.isCurrent || o.isCurrent());
    const base = 'api/content/' + encodeURIComponent(module);
    const q = selector => host.querySelector(selector);
    function message(text, bad) { if (live() && q('[data-cw-message]')) { q('[data-cw-message]').textContent = text; q('[data-cw-message]').classList.toggle('bad', !!bad); } }
    function capture() {
      if (!editor) {
        if (preparing) {
          const path = q('[data-cw-create-path]'), template = q('[data-cw-template]');
          if (path) preparing.path = path.value;
          if (template) preparing.template = template.value;
          putDraft(preparationKey, preparing, storage);
        }
        return;
      }
      const input = q('[data-cw-text]'), path = q('[data-cw-path]');
      if (input) editor.text = input.value;
      if (path && editor.isNew) editor.path = path.value.trim();
      const currentOrigin = keyOf(root, module, editor.path);
      if (editor.isNew && editorOrigin !== currentOrigin) { dropDraft(editorOrigin, storage); editorOrigin = currentOrigin; }
      const reason = q('[data-cw-reason]'); if (reason) editor.reason = reason.value;
      if (pending || edited(editor)) putDraft(editorOrigin, editor, storage);
      else dropDraft(editorOrigin, storage);
    }
    function edited(e) { return e.isNew || e.text !== e.original || (e.reason || '') !== (e.originalReason || ''); }
    function dirty() { capture(); return !!preparing || !!editor && edited(editor); }
    function bind(value) {
      if (!value || value.module !== module || normalRoot(value.project_root) !== root) throw new Error(w('收到的内容与当前项目不一致', 'Content does not match the current project'));
      return value;
    }
    async function request(method, url, body, ticket) {
      ++pending;
      const loading = o.beginRead && o.beginRead();
      try {
        const value = bind(await o.api(method, url, body));
        if (!live() || ticket !== serial) { if (o.dropRead) o.dropRead(loading); return null; }
        if (o.completeRead && !await o.completeRead(loading, () => live() && ticket === serial)) return null;
        return value;
      } catch (error) {
        if (live() && ticket === serial) {
          if (o.failRead) o.failRead(loading, error);
          message((error.status === 409 ? w('版本已改变，输入已保留；请对照最新文件后再保存。', 'The revision changed. Your input is retained; compare the latest file before saving. ') : '') + String(error.message || error), true);
        } else if (o.dropRead) o.dropRead(loading);
        return null;
      } finally { --pending; }
    }
    function shell() {
      const titles = {'文献':['学习工作台','Learning workspace'], '论文':['写作工作台','Writing workspace'], 'PPT':['演示工作台','Presentation workspace'], '测试':['测试工作台','Testing workspace'], '宣传片':['宣传片','Promo video']};
      const title = titles[module] || [module, module];
      host.innerHTML = '<div class="cw-page ' + (module === '测试' ? 'cw-test' : ['PPT','宣传片'].includes(module) ? 'cw-presentation' : 'cw-content') + '"><header class="cw-heading"><h1>' + esc(w(title[0], title[1])) + '</h1><div class="acts"><span data-cw-skills-wrap></span><button class="sbtn" data-cw-refresh>' + w('刷新', 'Refresh') + '</button>' + (module !== '文献' ? '<button class="sbtn" data-cw-config>' + w('编辑目录', 'Edit sections') + '</button>' : '') + '</div></header><p class="hint cw-message" role="status" aria-live="polite" data-cw-message></p><div data-cw-sections></div><div data-cw-editor></div></div>';
    }
    function skillEntry() {
      const entry = workspace && workspace.skill_entry;
      // Only the server's current module entry can become a reading shortcut.
      return entry && (module === '论文' || module === 'PPT') && entry.path === '技能/SKILL.md' && entry.readonly === true ? entry : null;
    }
    function renderSkillEntry() {
      const entry = skillEntry(), wrap = q('[data-cw-skills-wrap]');
      if (!wrap) return;
      wrap.innerHTML = entry ? '<button class="sbtn" data-cw-skills' + (entry.available === true && typeof o.openSkills === 'function' ? '' : ' disabled') + '>' + esc(w(entry.name, entry.en || entry.name)) + (entry.available === true ? '' : ' · ' + w('缺入口', 'Entry missing')) + '</button>' : '';
    }
    function sectionsHtml() {
      let sections = workspace.sections || [];
      if (module === '文献') sections = sections.filter(s => s.kind !== 'notes');
      if (o.section && o.section !== 'all' && !(module === '文献' && (workspace.sections || []).some(s => s.id === o.section && s.kind === 'notes'))) sections = sections.filter(s => s.id === o.section);
      return sections.map(s => {
        const title = w(s.title, s.en || s.title), files = s.files || [];
        const rows = files.map(f => '<li><div><span class="cw-name">' + esc(f.name) + '</span><small>' + esc(f.path) + (f.missing_original ? ' · ' + w('缺原文', 'Original missing') : f.unlinked_original ? ' · ' + w('未关联原文', 'Original unlinked') : f.original_unconfirmed ? ' · ' + w('原文未确认', 'Original unconfirmed') : '') + '</small></div><div class="acts">' + (f.reader_code ? '<button class="sbtn" data-cw-reader="' + esc(f.reader_code) + '">' + w('精读', 'Read') + '</button>' : '') + '<button class="sbtn" data-cw-file="' + esc(f.path) + '">' + w('打开', 'Open') + '</button>' + (f.editable ? '<button class="sbtn" data-cw-edit="' + esc(f.path) + '">' + w('编辑', 'Edit') + '</button>' : '') + '</div></li>').join('');
        return '<section class="cw-section"><header><h2>' + esc(title) + '</h2><div class="acts">' + (s.kind === 'downloads' ? '<button class="sbtn" data-cw-download>' + w('打开列表', 'Open list') + '</button>' : '') + (s.kind === 'documents' ? '<button class="sbtn" data-cw-new="' + esc(s.id) + '">' + w('新建', 'New') + '</button>' : '') + '</div></header><p class="cw-source">' + esc(s.folder || '') + '</p>' + (rows ? '<ul class="cw-files">' + rows + '</ul>' : '<p class="hint">' + w('暂无文件', 'No files yet') + '</p>') + '</section>';
      }).join('') || '<p class="hint">' + w('没有配置工作区；已有文件仍可从左侧打开。', 'No workspace configured. Existing files remain available in the file tree.') + '</p>';
    }
    async function refresh() {
      if (dirty() || pending) { message(w('先保存或取消当前编辑', 'Save or cancel the current edit first'), false); return; }
      const ticket = ++serial;
      const value = await request('GET', base, undefined, ticket);
      if (!value) return;
      workspace = value;
      renderSkillEntry();
      q('[data-cw-sections]').innerHTML = sectionsHtml();
      message((value.problems || []).map(p => typeof p === 'string' ? p : JSON.stringify(p)).join(' · '), !!(value.problems || []).length);
      const saved = getDraft(preparationKey, storage);
      if (!editor && !preparing && saved && saved.kind === 'preparation' && (!o.section || o.section === 'all' || o.section === saved.section)) {
        preparing = Object.assign({}, saved);
        renderPreparation();
        if (preparationValid()) message(w('已恢复未完成的新建；可继续编辑或取消。', 'Unfinished file preparation restored; continue or cancel.'));
      }
    }
    function renderEditor() {
      const e = editor, title = e.isNew ? w('新建文件', 'New file') : w('编辑文件', 'Edit file');
      const builtin = !e.isNew && global.BuiltinFiles ? global.BuiltinFiles.slot('资料/'+module+'/'+e.path) : '';
      q('[data-cw-editor]').innerHTML = '<section class="cw-editor"><header><h2>' + title + '</h2><div class="acts">'+builtin+'<button class="sbtn" data-cw-save>' + w('保存', 'Save') + '</button><button class="sbtn" data-cw-cancel>' + w('取消', 'Cancel') + '</button>' + (!e.isNew ? '<button class="sbtn" data-cw-latest>' + w('对照最新', 'Compare latest') + '</button>' : '') + '</div></header><label>' + w('文件路径', 'File path') + '<input data-cw-path value="' + esc(e.path) + '"' + (e.isNew ? '' : ' readonly') + '></label><textarea data-cw-text spellcheck="false" aria-label="' + w('文件内容', 'Document text') + '"></textarea><label>' + w('修改说明', 'Change reason') + '<input data-cw-reason value="' + esc(e.reason || '') + '"></label><details data-cw-compare hidden><summary>' + w('最新文件（输入保留在上方）', 'Latest file (your input remains above)') + '</summary><pre data-cw-latest-text></pre><button class="sbtn" data-cw-use-version>' + w('已完成对照，使用此版本保存我的输入', 'Compared; save my input against this revision') + '</button></details></section>';
      q('[data-cw-text]').value = e.text;
      q('[data-cw-text]').focus();
      if (q('[data-cw-editor]').scrollIntoView) q('[data-cw-editor]').scrollIntoView({block: 'nearest', behavior: 'auto'});
    }
    async function edit(path, isNew, template, fromPreparation) {
      if (pending || (!fromPreparation && dirty()) || (fromPreparation && !preparationValid())) { message(w('先保存或取消当前编辑', 'Save or cancel the current edit first')); return; }
      const ticket = ++serial;
      let doc = null;
      if (!isNew || template) doc = await request('GET', base + '/document?path=' + encodeURIComponent(template || path), undefined, ticket);
      if ((!isNew || template) && !doc || !live() || ticket !== serial) return;
      if (doc && doc.path !== (template || path)) { message(w('读取结果路径不匹配；输入仍已保留', 'Read path mismatch; input retained'), true); return; }
      if (!isNew && (!doc.editable || doc.path !== path)) { message(w('这个文件只能阅读', 'This file is read-only'), true); return; }
      if (preparing) { preparing = null; dropDraft(preparationKey, storage); }
      editorOrigin = keyOf(root, module, path);
      const old = getDraft(editorOrigin, storage);
      editor = {path: path, text: doc ? doc.text : '', original: isNew ? '' : doc.text, revision: isNew ? '' : doc.revision, isNew: !!isNew, reason: '', originalReason: ''};
      if (old) {
        editor.text = old.text; editor.reason = old.reason || '';
        if (old.isNew === !!isNew) { editor.path = old.path || path; editor.revision = old.revision; editor.original = old.original; editor.originalReason = old.originalReason || ''; }
        message(w('已恢复未保存输入；原版本改变时请先对照。', 'Unsaved input restored; compare first if the source revision changed.'));
      }
      renderEditor();
      capture();
    }
    function preparationSection() { return preparing && workspace && (workspace.sections || []).find(s => s.id === preparing.section && s.kind === 'documents'); }
    function preparationValid() {
      const section = preparationSection();
      return !!section && (!preparing.template || (section.templates || []).some(t => t.path === preparing.template));
    }
    function renderPreparation() {
      const section = preparationSection(), templates = section ? section.templates || [] : [];
      const unavailable = preparing.template && !templates.some(t => t.path === preparing.template);
      q('[data-cw-editor]').innerHTML = '<section class="cw-editor"><h2>' + w('新建文件', 'New file') + '</h2><label>' + w('模板', 'Template') + '<select data-cw-template>' + '<option value="">' + w('空白文件', 'Blank document') + '</option>' + (unavailable ? '<option value="' + esc(preparing.template) + '">' + esc(preparing.template) + ' · ' + w('已不可用', 'Unavailable') + '</option>' : '') + templates.map(t => '<option value="' + esc(t.path) + '">' + esc(t.name) + '</option>').join('') + '</select></label><label>' + w('文件路径', 'File path') + '<input data-cw-create-path value="' + esc(preparing.path) + '"></label><div class="acts"><button class="sbtn" data-cw-create>' + w('开始编辑', 'Start editing') + '</button><button class="sbtn" data-cw-cancel>' + w('取消', 'Cancel') + '</button></div></section>';
      q('[data-cw-template]').value = preparing.template || '';
      q('[data-cw-create]').disabled = !preparationValid();
      if (!preparationValid()) message(w('原目录或模板已不可用；准备内容已保留，请重新选模板或取消。', 'The previous section or template is unavailable. Preparation is retained; choose a template or cancel.'), true);
    }
    function createForm(id) {
      if (dirty() || pending) { message(w('先保存或取消当前编辑', 'Save or cancel the current edit first')); return; }
      const section = (workspace.sections || []).find(s => s.id === id);
      if (!section || section.kind !== 'documents') return;
      editor = null; editorOrigin = '';
      preparing = {kind:'preparation',text:'',section:id,path:section.folder + '/新文档.md',defaultPath:section.folder + '/新文档.md',template:'',pathCustom:false};
      renderPreparation(); capture();
    }
    function changeTemplate() {
      if (!preparing || editor) return;
      const section = preparationSection(), path = q('[data-cw-create-path]'), template = q('[data-cw-template]');
      if (!section || !path || !template) return;
      if (path.value !== preparing.defaultPath) preparing.pathCustom = true;
      preparing.template = template.value;
      const name = preparing.template ? preparing.template.split('/').pop() : '新文档.md';
      preparing.defaultPath = section.folder + '/' + name;
      if (!preparing.pathCustom) path.value = preparing.defaultPath;
      q('[data-cw-create]').disabled = !preparationValid();
      capture();
    }
    async function save() {
      if (!editor || pending || !live()) return;
      capture(); const e = editor, submitted = Object.assign({}, e), submittedOrigin = editorOrigin, ticket = ++serial;
      putDraft(submittedOrigin, submitted, storage);
      const button = q('[data-cw-save]'); button.disabled = true;
      const value = await request('POST', base + '/document', {path:submitted.path,text:submitted.text,revision:submitted.revision,reason:submitted.reason || w('网页手动编辑', 'Manual webpage edit'),project_root:o.projectRoot}, ticket);
      if (live() && ticket === serial && button.isConnected) button.disabled = false;
      if (!value) return;
      if (value.path !== submitted.path || typeof value.revision !== 'string') { capture(); message(w('保存结果不匹配；输入仍已保留', 'Save result mismatch; input retained'), true); return; }
      capture();
      const hasLaterInput = e.path !== submitted.path || e.text !== submitted.text || (e.reason || '') !== (submitted.reason || '');
      if (hasLaterInput) {
        if (e.path === submitted.path) {
          e.original = submitted.text; e.originalReason = submitted.reason || ''; e.revision = value.revision; e.isNew = false;
          delete e.latest;
        }
        dropDraft(submittedOrigin, storage);
        editorOrigin = keyOf(root, module, e.path);
        putDraft(editorOrigin, e, storage);
        const input = q('[data-cw-text]'), selection = input && [input.selectionStart, input.selectionEnd];
        renderEditor();
        if (selection && q('[data-cw-text]').setSelectionRange) q('[data-cw-text]').setSelectionRange(selection[0], selection[1]);
        message(w('已提交的内容已保存；后续输入仍未保存。', 'Submitted content saved; newer input remains unsaved.'));
      } else {
        dropDraft(submittedOrigin, storage); editor = null; q('[data-cw-editor]').innerHTML = '';
        await refresh(); message(w('已保存；agent 可读取同一文件', 'Saved; agents can read the same file'));
      }
      if (o.onSaved) o.onSaved(value);
    }
    async function compareLatest() {
      if (!editor || editor.isNew || pending) return;
      capture(); const path = editor.path, ticket = ++serial;
      const doc = await request('GET', base + '/document?path=' + encodeURIComponent(path), undefined, ticket);
      if (!doc || !editor || editor.path !== path || doc.path !== path) return;
      editor.latest = {text:doc.text,revision:doc.revision};
      q('[data-cw-compare]').hidden = false; q('[data-cw-compare]').open = true;
      q('[data-cw-latest-text]').textContent = doc.text;
    }
    function cancel() {
      if (pending) return;
      if (editor) dropDraft(editorOrigin, storage);
      if (preparing) dropDraft(preparationKey, storage);
      editor = null; preparing = null; ++serial; q('[data-cw-editor]').innerHTML = ''; message('');
    }
    function onInput(event) {
      if (!live()) return;
      if (event.target.matches('[data-cw-text],[data-cw-path],[data-cw-reason]')) capture();
      else if (event.target.matches('[data-cw-template]')) changeTemplate();
      else if (event.target.matches('[data-cw-create-path]') && preparing) { preparing.pathCustom = event.target.value !== preparing.defaultPath; capture(); }
    }
    function onChange(event) { if (live() && event.target.matches('[data-cw-template]')) changeTemplate(); }
    function onClick(event) {
      if (!live()) return;
      const b = event.target.closest('button'); if (!b || !host.contains(b)) return;
      if (b.hasAttribute('data-cw-skills')) {
        const entry = skillEntry();
        if (entry && entry.available === true && typeof o.openSkills === 'function') { capture(); o.openSkills(module); }
      }
      else if (b.dataset.cwFile !== undefined) { capture(); o.openFile(b.dataset.cwFile); }
      else if (b.dataset.cwReader !== undefined) { capture(); o.openReader(b.dataset.cwReader); }
      else if (b.hasAttribute('data-cw-download')) { capture(); o.openDownloads(); }
      else if (b.dataset.cwEdit !== undefined) edit(b.dataset.cwEdit, false);
      else if (b.dataset.cwNew !== undefined) createForm(b.dataset.cwNew);
      else if (b.hasAttribute('data-cw-refresh')) refresh();
      else if (b.hasAttribute('data-cw-config')) edit(workspace && workspace.config_file || '工作台/工作台.json', false);
      else if (b.hasAttribute('data-cw-save')) save();
      else if (b.hasAttribute('data-cw-latest')) compareLatest();
      else if (b.hasAttribute('data-cw-use-version') && editor && editor.latest && !pending) { capture(); editor.revision = editor.latest.revision; editor.original = editor.latest.text; putDraft(editorOrigin, editor, storage); message(w('已采用对照版本；点击保存提交你的输入', 'Comparison revision selected; Save to submit your input')); }
      else if (b.hasAttribute('data-cw-cancel')) cancel();
      else if (b.hasAttribute('data-cw-create')) {
        capture();
        if (!preparationValid()) { message(w('目录或模板已不可用，请重新选择或取消。', 'The section or template is unavailable; choose again or cancel.'), true); return; }
        const path = q('[data-cw-create-path]').value.trim(), template = q('[data-cw-template]').value;
        if (!path) { message(w('填写文件路径', 'Enter a file path'), true); return; }
        edit(path, true, template, true);
      }
    }
    shell(); host.addEventListener('click', onClick); host.addEventListener('input', onInput); host.addEventListener('change', onChange);
    const ready = refresh();
    return {ready, refresh, edit, save, compareLatest, cancel, isDirty:dirty, isBusy:()=>pending>0, destroy(){capture(); disposed=true; ++serial; host.removeEventListener('click',onClick);host.removeEventListener('input',onInput);host.removeEventListener('change',onChange);}, snapshot(){capture();return {module,root,workspace,editor:editor&&Object.assign({},editor),preparing:preparing&&Object.assign({},preparing),pending};}};
  }
  global.ContentWorkspace = {mount};
})(typeof window === 'undefined' ? globalThis : window);
