/* 代码地图（S1-1 S2-21）：源代码整个铺成一张能飞的地图——每个文件一块，块里按栏排真代码，远看是按语法上色的细线，拉近是能读的字。
   作者 10-02 发来 Rik Arends 的 3D 代码浏览器截图：「我想做的可视化是这个」；「不需要看他的代码，完全可以自己设计把这些功能实现」。
   自己设计的几样：
   - 摆法：文件夹套文件夹的方块图（squarified treemap），文件面积跟行数走；块里的代码像报纸那样分栏，全图字差不多一样大
   - 远近三档：远看贴每个文件先画好的小图（细线）；再近直接画细线；够近了画字和行号。只画屏幕上看得见的块
   - 边看边加载：文件全文看到才去取（同时最多 6 个），取过的留着；留得太多把最久没看的丢掉
   - 上色四档：按类型 · 最近改过 · 改得多（git 记录）· 没交的改动（改了的行在左边标出来）
   - 找一个词、点函数看谁用到它（画线连过去）
   - 斜着看：整张图用 CSS 3D 倾斜、能转；点、拖、滚轮都按倾斜反算回图上的位置
   - 重要性金字塔（S1-1 S2-24；作者 10-03「我想用重要性来分……最重要的核心代码放最上面，这样依次往下；有个切换按钮也没关系；
     我需要这个是通用的内置模块」）：后台现算每个文件被几个别的文件用到、是不是入口、几个测试守着（codemap.importance），
     分几层，3D 台阶（three.js）：最重要的那层最高最小在顶上，越往下越宽；每个文件是台面上的一块，顶面贴它的代码。
     切换：重要性金字塔 · 文件夹台阶（外层的文件在上）· 改动热度（改得越多越高）· 平铺地图（原来那张，读代码用）。
     全屏：按钮或 F，Esc 退出，镜头不变
   网页（模板.html 的 showCodemap）调 CodeMap.mount(el, {module, api, open})，拿回 {module, ready, alive, refresh, destroy}；ready 是第一次目录读取的实际结果，不会拒绝。 */
(function () {
  'use strict';
  const CW = 0.6, LH = 1.25, COLC = 100, GUT = 6, GAP = 3;      // 一个字宽 0.6、行高 1.25（字号 1）；一栏 100 个字宽，左边 6 个字宽放行号，栏间空 3 个
  const HEAD = 4.4, FHEAD = 8, FPAD = 1.4, GAPF = 0.7;            // 文件名那条高 · 文件夹名那条高 · 文件夹内边 · 块和块之间
  const COLW = (GUT + COLC) * CW, STEP = (GUT + COLC + GAP) * CW;
  const FONT = 'Consolas,"Cascadia Mono","Microsoft YaHei",monospace';
  const KW = {
    py: new Set('def class return if elif else for while in not and or is None True False import from as with try except finally raise lambda yield async await pass break continue global nonlocal del assert self'.split(' ')),
    js: new Set('function return if else for while const let var new this class extends import export from of in typeof instanceof null undefined true false async await try catch finally throw switch case default break continue do delete void yield static get set'.split(' '))
  };
  KW.html = KW.js;
  const TINT = { py: '#3b82f6', js: '#f59e0b', html: '#f97316', css: '#a855f7', json: '#14b8a6', conf: '#14b8a6', md: '#94a3b8', bat: '#64748b', sh: '#64748b', sql: '#0ea5e9', text: '#94a3b8' };
  const LANGNAME = { py: 'Python', js: 'JavaScript', html: '网页（HTML + 程序）', css: '样式', json: '配置（JSON）', conf: '配置', md: '文字', bat: '启动器', sh: '脚本', sql: 'SQL', text: '其它' };
  const MODES = [['lang', '按类型'], ['recent', '最近改过'], ['churn', '改得多'], ['diff', '没交的改动']];
  const VIEWS = [['flat', '平铺地图'], ['flow', '依赖线图'], ['pyr', '重要性金字塔'], ['fold', '文件夹台阶'], ['heat', '改动热度']];
  function overviewView(mode) { return mode === 'flow' ? 'flow' : mode === 'model3d' ? 'pyr' : 'flat'; }
  function overviewMode(module) { try { return typeof window.researchOverviewMode === 'function' ? window.researchOverviewMode(module || '源代码') : 'map'; } catch (_) { return 'map'; } }
  function clampPane(box, viewport) {
    const n = function (v, f) { return Number.isFinite(v) ? v : f; }, W = Math.max(1, n(viewport.width, 1024)), H = Math.max(1, n(viewport.height, 768)), gap = Math.min(8, W / 4, H / 4);
    const width = Math.min(W - gap * 2, Math.max(1, n(box.width, 320))), height = Math.min(H - gap * 2, Math.max(1, n(box.height, 500)));
    return { x: Math.max(gap, Math.min(n(box.x, gap), W - gap - width)), y: Math.max(gap, Math.min(n(box.y, gap), H - gap - height)), width: width, height: height };
  }

  function css() {
    if (document.getElementById('cmxCss')) return;
    const st = document.createElement('style');
    st.id = 'cmxCss';
    st.textContent = '.cmx-bar{display:flex;flex-wrap:nowrap;gap:8px;align-items:center;margin:0 0 10px;min-width:0;overflow-x:auto}.cmx-bar>*{flex-shrink:0}.cmx-bar .cmx-stat{margin-left:auto;white-space:nowrap}'
      + '.cmx-bar input[type=search],.cmx-bar select{font:inherit;font-size:.8125rem;padding:5px 10px;border:1px solid var(--ring);border-radius:8px;background:var(--card);color:var(--fg)}.cmx-bar input[type=search]{width:15rem;min-width:9rem;flex-shrink:1}'
      + '.cmx-seg{display:inline-flex;border:1px solid var(--ring);border-radius:8px;overflow:hidden}'
      + '.cmx-seg button{font:inherit;font-size:.75rem;padding:4px 10px;border:0;background:var(--card);color:var(--fg2);cursor:pointer}'
      + '.cmx-seg button+button{border-left:1px solid var(--ring)}.cmx-seg button.on{background:var(--accent);color:var(--onaccent)}'
      + '.cmx-stat{font-size:.75rem;color:var(--muted);font-variant-numeric:tabular-nums}'
      + '.cmx-stage{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:12px;background:var(--plane);perspective:1100px;user-select:none}'
      + '.cmx-world{position:absolute;transform-origin:50% 50%;transition:transform .35s ease}.cmx-world.drag{transition:none}'
      + '.cmx-world canvas{display:block;cursor:grab}.cmx-world canvas.grab{cursor:grabbing}'
      + '.cmx-side{position:absolute;top:10px;right:10px;bottom:10px;width:19rem;display:flex;flex-direction:column;overflow:hidden;user-select:text;background:var(--card);border:1px solid var(--ring);border-radius:10px;padding:0;font-size:.8125rem;box-shadow:0 6px 24px rgba(0,0,0,.12)}.cmx-pane-body{padding:12px 14px;overflow:auto;flex:1;min-height:0;overflow-wrap:anywhere}'
      + '.cmx-side h4{margin:0 0 2px;font-size:.9375rem;word-break:break-all}.cmx-side .p{font-family:var(--mono);font-size:.6875rem;color:var(--muted);word-break:break-all}'
      + '.cmx-side .says{margin:8px 0;color:var(--fg2)}.cmx-side .kv{color:var(--muted);font-size:.75rem;margin:4px 0 8px}'
      + '.cmx-side .acts{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.cmx-side h5{margin:12px 0 4px;font-size:.75rem;color:var(--muted);font-weight:600}'
      + '.cmx-side .row{display:flex;gap:6px;align-items:baseline;padding:2px 4px;border-radius:6px;cursor:pointer}.cmx-side .row:hover{background:var(--lane2)}'
      + '.cmx-side .row.on{background:var(--lane2);box-shadow:inset 2px 0 0 var(--accent)}'
      + '.cmx-side .row b{font-family:var(--mono);font-weight:500;font-size:.75rem;word-break:break-all}.cmx-side .row .n{margin-left:auto;color:var(--muted);font-size:.6875rem;white-space:nowrap}'
      + '.cmx-side .row .t{font-family:var(--mono);font-size:.6875rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}'
      + '.cmx-side .x{position:absolute;top:6px;right:8px;border:0;background:none;color:var(--muted);font-size:1rem;cursor:pointer}'
      + '.cmx-pane-handle{display:none;cursor:move;touch-action:none;user-select:none;font-size:.75rem;color:var(--muted);padding:4px 22px 8px 0;border-bottom:1px solid var(--line);margin-bottom:8px}.cmx-side.cmx-pane-floating .cmx-pane-handle{display:block}.cmx-pane-handle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}'
      + '.cmx-pane-size{align-self:flex-end;flex-shrink:0;width:1.6rem;height:1.35rem;border:0;background:transparent;color:var(--muted);font:.9rem var(--font,system-ui);cursor:nwse-resize;touch-action:none;user-select:none}.cmx-pane-size:hover,.cmx-pane-size:focus-visible{color:var(--hover-gold,var(--accent));outline:1px solid var(--hover-gold,var(--accent));outline-offset:-2px}'
      + '.cmx-side[hidden]{display:none}.cmx-side.cmx-pane-floating .cmx-pane-handle{flex-shrink:0;padding:.45rem .75rem;margin:0}'
      + '.cmx-legend{position:absolute;left:10px;bottom:10px;background:var(--card);border:1px solid var(--ring);border-radius:8px;padding:6px 10px;font-size:.6875rem;color:var(--fg2);display:flex;gap:10px;flex-wrap:wrap;max-width:60%}'
      + '.cmx-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px;vertical-align:-1px}'
      + '.cmx-tip{position:absolute;pointer-events:none;background:var(--fg);color:var(--plane);font-size:.6875rem;padding:3px 8px;border-radius:6px;white-space:nowrap;display:none;z-index:2}'
      + '.cmx-load{position:absolute;right:12px;top:10px;font-size:.6875rem;color:var(--muted)}'
      + '.cmx-3d{position:absolute;inset:0}.cmx-3d canvas{display:block;outline:none;cursor:grab}.cmx-3d canvas.grab{cursor:grabbing}'
      + '.cmx-tiers{position:absolute;inset:0;pointer-events:none;overflow:hidden}'
      + '.cmx-tiers div{position:absolute;transform:translate(-100%,-50%);font-size:.6875rem;font-weight:600;color:var(--fg);background:var(--card);border:1px solid var(--ring);border-radius:6px;padding:1px 7px;white-space:nowrap;opacity:.92}'
      + '.cmx-tiers div span{color:var(--muted);font-weight:400;margin-left:4px}'
      + '.cmx-root:fullscreen,.cmx-root.cmx-fs{background:var(--plane);padding:12px;overflow:auto;box-sizing:border-box}.cmx-root.cmx-fs{position:fixed;inset:0;z-index:10000;width:100%;height:100%;margin:0;max-width:none}.cmx-root:fullscreen .cmx-stage,.cmx-root.cmx-fs .cmx-stage{border-radius:8px}'
      + '.cmx-why{font-size:.75rem;margin:4px 0 8px;color:var(--fg2)}';
    document.head.appendChild(st);
  }

  // ---------------------------------------------------------------- 摆：方块图
  function squarify(items, x, y, w, h, place) {          // items 已按面积从大到小、面积总和 = w × h
    let row = [], i = 0;
    const worst = function (r, side) {
      let s = 0, mx = 0, mn = Infinity;
      r.forEach(function (it) { s += it.v; mx = Math.max(mx, it.v); mn = Math.min(mn, it.v); });
      return Math.max(side * side * mx / (s * s), s * s / (side * side * mn));
    };
    const flush = function () {
      const s = row.reduce(function (a, it) { return a + it.v; }, 0);
      if (w >= h) {                                       // 竖着一列放在左边
        const cw = s / h; let yy = y;
        row.forEach(function (it) { const hh = it.v / cw; place(it, x, yy, cw, hh); yy += hh; });
        x += cw; w -= cw;
      } else {                                            // 横着一行放在上边
        const rh = s / w; let xx = x;
        row.forEach(function (it) { const ww = it.v / rh; place(it, xx, y, ww, rh); xx += ww; });
        y += rh; h -= rh;
      }
      row = [];
    };
    while (i < items.length) {
      const side = Math.min(w, h), next = row.concat([items[i]]);
      if (!row.length || worst(row, side) >= worst(next, side)) { row = next; i++; } else flush();
    }
    if (row.length) flush();
  }

  function fitCols(n, W, H) {                            // 这么多行塞进 W × H：字号最大多少、一栏几行、几栏
    const ok = function (s) {
      const L = Math.floor(H / (LH * s));
      if (L < 1) return false;
      const cols = Math.ceil(n / L);
      return cols * COLW * s + (cols - 1) * GAP * CW * s <= W;
    };
    let lo = 0.02, hi = 1.15;
    if (ok(hi)) lo = hi;
    else for (let k = 0; k < 24; k++) { const m = (lo + hi) / 2; if (ok(m)) lo = m; else hi = m; }
    const L = Math.max(1, Math.floor(H / (LH * lo)));
    return { s: lo, L: L, cols: Math.max(1, Math.ceil(n / L)) };
  }

  function build(files) {                                // 文件 → 文件夹树 → 摆好
    const root = { name: '', path: '', kids: {}, files: [], root: true };
    if (!files.length) return { root: root, folders: [], files: [], W: 800, H: 500 };
    files.forEach(function (f) {
      let node = root;
      (f.dir ? f.dir.split('/') : []).forEach(function (part, i, all) {
        node.kids[part] = node.kids[part] || { name: part, path: all.slice(0, i + 1).join('/'), kids: {}, files: [] };
        node = node.kids[part];
      });
      node.files.push(f);
    });
    const weigh = function (node) {
      let s = 0;
      node.list = [];
      Object.keys(node.kids).forEach(function (k) { const c = node.kids[k]; weigh(c); s += c.wt; node.list.push(c); });
      node.files.forEach(function (f) {
        const base = Math.max(f.lines, 8) * LH * COLW * 1.12;
        f.wt = base + HEAD * Math.sqrt(base) * 1.3;
        s += f.wt; node.list.push(f);
      });
      node.wt = node.root ? s : s + (FHEAD + 2 * FPAD) * Math.sqrt(s) * 1.25;
    };
    weigh(root);
    const folders = [], all = [];
    const lay = function (node, x, y, w, h, depth) {
      Object.assign(node, { x: x, y: y, w: w, h: h, depth: depth });
      if (!node.root) folders.push(node);
      const top = node.root ? 0 : FHEAD, pad = node.root ? 0 : FPAD;
      const ix = x + pad, iy = y + top, iw = Math.max(w - 2 * pad, 0.5), ih = Math.max(h - top - pad, 0.5);
      const items = node.list.slice().sort(function (a, b) { return b.wt - a.wt; });
      const sum = items.reduce(function (a, it) { return a + it.wt; }, 0) || 1, k = iw * ih / sum;
      squarify(items.map(function (it) { return { it: it, v: it.wt * k }; }), ix, iy, iw, ih, function (o, x0, y0, w0, h0) {
        const g = Math.min(GAPF, w0 / 6, h0 / 6);
        if (o.it.kids) lay(o.it, x0 + g, y0 + g, w0 - 2 * g, h0 - 2 * g, depth + 1);
        else layFile(o.it, x0 + g, y0 + g, w0 - 2 * g, h0 - 2 * g);
      });
    };
    const layFile = function (f, x, y, w, h) {
      const head = Math.min(HEAD, h * 0.3), pad = Math.min(0.8, w / 20);
      Object.assign(f, { x: x, y: y, w: w, h: h, head: head, cx: x + pad, cy: y + head, cw: Math.max(w - 2 * pad, 0.1), ch: Math.max(h - head - pad, 0.1) });
      Object.assign(f, fitCols(Math.max(f.lines, 1), f.cw, f.ch));
      all.push(f);
    };
    const W = Math.sqrt(root.wt * 1.6), H = root.wt / W;
    lay(root, 0, 0, W, H, 0);
    return { root: root, folders: folders, files: all, W: W, H: H };
  }

  // users is a recorded, sometimes truncated API field: user -> referenced file.
  function buildFlow(files) {
    const by = new Map(files.map(f => [f.rel, f])), edges = [], seen = new Set(), degree = new Map(), levels = new Map(), out = new Map();
    files.forEach(f => { degree.set(f.rel, 0); out.set(f.rel, []); });
    files.forEach(f => (Array.isArray(f.users) ? f.users : []).forEach(user => {
      const key = user + '\0' + f.rel;
      if (!by.has(user) || seen.has(key)) return;
      seen.add(key); edges.push({ from: user, to: f.rel });
      out.get(user).push(f.rel); degree.set(f.rel, degree.get(f.rel) + 1);
    }));
    const queue = files.filter(f => degree.get(f.rel) === 0).map(f => f.rel);
    queue.forEach(rel => levels.set(rel, 0));
    for (let i = 0; i < queue.length; i++) out.get(queue[i]).forEach(rel => {
      levels.set(rel, Math.max(levels.get(rel) || 0, levels.get(queue[i]) + 1));
      degree.set(rel, degree.get(rel) - 1); if (!degree.get(rel)) queue.push(rel);
    });
    const cycleColumn = Math.max(0, ...levels.values()) + 1, rows = new Map(), nodes = [];
    files.forEach(f => {
      const column = degree.get(f.rel) ? cycleColumn : levels.get(f.rel) || 0, row = rows.get(column) || 0;
      rows.set(column, row + 1); nodes.push({ rel: f.rel, file: f, x: 30 + column * 280, y: 30 + row * 72, w: 220, h: 48 });
    });
    return { files: nodes, edges: edges, byRel: new Map(nodes.map(n => [n.rel, n])),
      W: Math.max(800, (Math.max(0, ...rows.keys()) + 1) * 280 + 20), H: Math.max(500, Math.max(0, ...rows.values()) * 72 + 60),
      truncated: files.filter(f => Array.isArray(f.users) && f.fan_in > f.users.length).length,
      unknown: files.filter(f => !Array.isArray(f.users)).length };
  }

  // ---------------------------------------------------------------- 认字：一行一行切成带颜色的段
  function cells(s) {                                    // 每个字前面有几个字宽（中文、全角算 2 个）
    const c = new Int32Array(s.length + 1);
    for (let i = 0; i < s.length; i++) {
      const k = s.charCodeAt(i);
      c[i + 1] = c[i] + (k >= 0xDC00 && k <= 0xDFFF ? 0 : k > 0x2E7F ? 2 : 1);
    }
    return c;
  }
  function tokenize(lines, lang) {
    const kw = KW[lang] || null, hashCom = lang === 'py' || lang === 'sh' || lang === 'conf';
    const slash = lang === 'js' || lang === 'html' || lang === 'css', html = lang === 'html';
    let st = 0;                                          // 1 /* */ · 2 """ · 3 ''' · 4 <!-- --> · 5 ` `
    return lines.map(function (s) {
      const t = [], c = cells(s), n = s.length;
      let i = 0, plain = -1, prevDef = false;
      const push = function (a, b, cls) {
        if (plain >= 0) { t.push(plain, a, c[plain], c[a], 0); plain = -1; }
        if (b > a) t.push(a, b, c[a], c[b], cls);
      };
      const closeTo = function (end, cls) {
        const j = s.indexOf(end, i);
        const b = j < 0 ? n : j + end.length;
        push(i, b, cls); i = b;
        return j >= 0;
      };
      if (lang === 'md' && /^\s*#/.test(s)) { if (n) t.push(0, n, 0, c[n], 1); return t; }
      if (lang === 'bat' && /^\s*(rem\b|::)/i.test(s)) { if (n) t.push(0, n, 0, c[n], 3); return t; }
      while (i < n) {
        if (st === 1) { if (closeTo('*/', 3)) st = 0; continue; }
        if (st === 2) { if (closeTo('"""', 2)) st = 0; continue; }
        if (st === 3) { if (closeTo("'''", 2)) st = 0; continue; }
        if (st === 4) { if (closeTo('-->', 3)) st = 0; continue; }
        if (st === 5) { if (closeTo('`', 2)) st = 0; continue; }
        const ch = s[i];
        if (ch === ' ') { if (plain >= 0) push(i, i, 0); i++; continue; }
        if ((hashCom && ch === '#') || (slash && ch === '/' && s[i + 1] === '/' && lang !== 'css') || (lang === 'sql' && ch === '-' && s[i + 1] === '-')) { push(i, n, 3); i = n; break; }
        if (slash && ch === '/' && s[i + 1] === '*') { st = 1; push(i, i + 2, 3); i += 2; continue; }
        if (html && s.startsWith('<!--', i)) { st = 4; push(i, i + 4, 3); i += 4; continue; }
        if (lang === 'py' && (s.startsWith('"""', i) || s.startsWith("'''", i))) { st = s[i] === '"' ? 2 : 3; push(i, i + 3, 2); i += 3; continue; }
        if (ch === '`' && slash) { st = 5; push(i, i + 1, 2); i++; continue; }
        if (ch === '"' || ch === "'") {
          let j = i + 1;
          while (j < n && s[j] !== ch) j += s[j] === '\\' ? 2 : 1;
          push(i, Math.min(j + 1, n), 2); i = Math.min(j + 1, n); continue;
        }
        if (html && ch === '<' && /[A-Za-z\/!]/.test(s[i + 1] || '')) {
          const m = /^<\/?[A-Za-z][\w-]*/.exec(s.slice(i));
          if (m) { push(i, i + m[0].length, 6); i += m[0].length; continue; }
        }
        if (/[0-9]/.test(ch) && !(plain >= 0 && /[\w$]/.test(s[i - 1] || ''))) {
          const m = /^[0-9][0-9a-fA-FxX._]*/.exec(s.slice(i));
          push(i, i + m[0].length, 4); i += m[0].length; continue;
        }
        if (/[A-Za-z_$]/.test(ch)) {
          const m = /^[A-Za-z_$][\w$]*/.exec(s.slice(i)), w = m[0], b = i + w.length;
          let cls = 0;
          if (kw && kw.has(w)) cls = 1;
          else if (prevDef || /^\s*\(/.test(s.slice(b, b + 3))) cls = 5;
          prevDef = w === 'def' || w === 'class' || w === 'function';
          if (cls) push(i, b, cls); else if (plain < 0) plain = i;
          i = b; continue;
        }
        if (plain < 0) plain = i;
        i++;
      }
      if (plain >= 0) push(n, n, 0);
      return t;
    });
  }

  // ---------------------------------------------------------------- 颜色：跟着网页的亮 / 暗
  function palette() {
    const v = function (k) { return getComputedStyle(document.documentElement).getPropertyValue(k).trim(); };
    const card = v('--card') || '#fff';
    const dark = (function (hex) {
      const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(hex);
      return m ? (parseInt(m[1], 16) * 0.3 + parseInt(m[2], 16) * 0.59 + parseInt(m[3], 16) * 0.11) < 128 : false;
    })(card);
    return {
      dark: dark, plane: v('--plane') || '#fafafa', card: card, fg: v('--fg') || '#171717', muted: v('--muted') || '#6b6b6b',
      line: v('--line') || '#ebebeb', accent: dark ? '#7cb4ff' : '#2563eb',
      tok: dark ? ['#cfcfcf', '#c4a5ff', '#7ee787', '#7d8590', '#ffa657', '#79c0ff', '#f0b45a']
        : ['#3d3d3d', '#7c3aed', '#0a7d32', '#9a9a9a', '#c2410c', '#1d4ed8', '#b45309'],
      folder: dark ? 'rgba(255,255,255,.035)' : 'rgba(0,0,0,.035)', folderLine: dark ? 'rgba(255,255,255,.12)' : 'rgba(0,0,0,.12)',
      hit: dark ? 'rgba(250,178,25,.35)' : 'rgba(250,178,25,.45)', diff: { 加: '#0ca30c', 改: '#fab219', 删: '#d03b3b', 新: '#0ca30c' }
    };
  }

  // ---------------------------------------------------------------- 挂上
  function mount(el, opts) {
    css();
    const api = opts.api, mod = opts.module;
    el.classList.add('cmx-root');
    el.innerHTML = '<div class="cmx-bar"><input type="search" aria-label="搜索代码 Search code" placeholder="找一个词：文件名或代码里的，回车飞过去">'
      + '<select data-cmx-color aria-label="代码着色 Code coloring">'+MODES.map(function (m) { return '<option value="'+m[0]+'">'+m[1]+'</option>'; }).join('')+'</select>'
      + '<span class="cmx-seg"><button data-act="zoom-out" aria-label="缩小 Zoom out">−</button><button data-act="zoom-in" aria-label="放大 Zoom in">+</button><button data-act="fit" title="快捷键 0">全景</button><button class="sticky-shortcut" data-act="notes" aria-label="便签 Sticky note" title="便签 Sticky note">' + (opts.notesIcon?opts.notesIcon():'') + '便签 Sticky note</button><button data-act="full" title="快捷键 F；Esc 退出">全屏</button></span>'
      + '<span class="cmx-stat"></span></div>'
      + '<div class="cmx-stage"><div class="cmx-world"><canvas tabindex="0"></canvas></div><div class="cmx-3d" hidden></div><div class="cmx-tiers" hidden></div>'
      + '<div class="cmx-legend"></div><div class="cmx-tip"></div><div class="cmx-load"></div><div class="cmx-side" hidden></div></div>';
    const stage = el.querySelector('.cmx-stage'), world = el.querySelector('.cmx-world'), cv = el.querySelector('canvas'), ctx = cv.getContext('2d');
    const side = el.querySelector('.cmx-side'), tip = el.querySelector('.cmx-tip'), legend = el.querySelector('.cmx-legend'), stat = el.querySelector('.cmx-stat');
    const loadNote = el.querySelector('.cmx-load'), q = el.querySelector('input[type=search]');
    const holder3 = el.querySelector('.cmx-3d'), tiersEl = el.querySelector('.cmx-tiers'), tiltBtn = el.querySelector('[data-act=tilt]');
    let P = palette(), map = null, byRel = {}, files = [], cam = { x: 0, y: 0, z: 1 }, fitZ = 1;
    let W = 0, H = 0, dpr = 1, dirty = true, alive = true, raf = 0, mode = 'lang', tilt = null, view = overviewView(overviewMode(mod)), T3 = null, flow = null;
    const cameras = {}; let fsSerial = 0, fsPending = false, fsWanted = false;
    let loadSerial = 0, readySettled = false, resolveReady;
    const ready = new Promise(function (resolve) { resolveReady = resolve; });
    function settleReady(result) { if (!readySettled) { readySettled = true; resolveReady(result); } }
    function closedRead() { return { ok: false, module: mod, status: 'destroyed', destroyed: true, error: '代码地图已关闭' }; }
    function inactiveRead(serial) {
      if (!alive || !document.body.contains(cv)) { if (alive) destroy(); return closedRead(); }
      if (serial !== loadSerial) return { ok: false, module: mod, status: 'stale', stale: true, error: '本次读取已被新读取替代' };
      return null;
    }
    let paneStyle = null, paneBox = null, paneDrag = null, paneResize = null, paneSize = { width: 304, height: 520 }, paneSized = false, paneParent = null, paneNext = null, paneRect = null, noteElement = null, noteZ = '';
    function is2d() { return view === 'flat' || view === 'flow'; }
    function bounds() { return view === 'flow' ? flow : map; }
    let sel = null, selLine = 0, hover = null, defs = [], uses = null, search = null, hitIdx = -1, diff = {}, git = false, now = Date.now() / 1000;
    const queue = [], loading = new Set();
    let frame = 0, memLines = 0;
    const stats = { frames: 0, ms: 0 };                   // 画了几帧、上一帧花了几毫秒（查卡不卡用）

    // ---- 大小
    function size() {
      const top = stage.getBoundingClientRect().top;
      const sh = Math.max(420, Math.round(innerHeight - Math.max(top, 0) - 14));
      stage.style.height = sh + 'px';
      const sw = stage.clientWidth;
      const k = tilt && view !== 'flow' ? 1.7 : 1;       // 依赖线图使用平面坐标；保留原地图倾斜
      W = Math.round(sw * k); H = Math.round(sh * k);
      dpr = tilt && view !== 'flow' ? 1 : Math.min(window.devicePixelRatio || 1, 2);
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      cv.style.width = W + 'px'; cv.style.height = H + 'px';
      world.style.left = Math.round((sw - W) / 2) + 'px'; world.style.top = Math.round((sh - H) / 2) + 'px';
      world.style.width = W + 'px'; world.style.height = H + 'px';
      if (bounds()) fitZ = Math.min(W / bounds().W, H / bounds().H) * 0.94;
      if (T3) { T3.renderer.setSize(sw, sh); T3.camera.aspect = sw / sh; T3.camera.updateProjectionMatrix(); redraw3(); }
      redraw();
    }
    function setTilt() {
      world.style.transform = tilt ? 'rotateX(' + tilt.a + 'deg) rotateZ(' + tilt.r + 'deg)' : '';
    }

    // ---- 屏幕上的点 → 画布上的点（斜着看时按倾斜反算）→ 图上的点
    function toCanvas(ev) {
      const r = stage.getBoundingClientRect();
      const X = ev.clientX - r.left - r.width / 2, Y = ev.clientY - r.top - r.height / 2;
      if (!tilt || view === 'flow') return { x: X + W / 2, y: Y + H / 2 };
      const Pp = 1100, a = tilt.a * Math.PI / 180, rr = tilt.r * Math.PI / 180;
      const v1 = Y * Pp / (Pp * Math.cos(a) + Y * Math.sin(a));
      const u1 = X * (Pp - v1 * Math.sin(a)) / Pp;
      const u = u1 * Math.cos(rr) + v1 * Math.sin(rr), v = -u1 * Math.sin(rr) + v1 * Math.cos(rr);
      return { x: u + W / 2, y: v + H / 2 };
    }
    function toWorld(p) { return { x: (p.x - W / 2) / cam.z + cam.x, y: (p.y - H / 2) / cam.z + cam.y }; }
    function sx(x) { return (x - cam.x) * cam.z + W / 2; }
    function sy(y) { return (y - cam.y) * cam.z + H / 2; }

    function tick(fn) {                                  // 下一帧：浏览器不给动画帧（窗口在后面）就用 40 毫秒的计时器顶上
      let done = false, h = 0, r = 0;
      const go = function () { if (done) return; done = true; clearTimeout(h); cancelAnimationFrame(r); fn(performance.now()); };
      r = requestAnimationFrame(go); h = setTimeout(go, 40);
    }
    function redraw() { dirty = true; if (!raf) { raf = 1; tick(draw); } }

    // ---- 取全文：看得见的才取，同时最多 6 个
    function need(f) {
      f.seen = frame;
      if (f.toks || loading.has(f.rel) || f.failed || queue.indexOf(f) >= 0) return;
      queue.push(f);
      pump();
    }
    function pump() {
      while (loading.size < 6 && queue.length) {
        const f = queue.shift();
        loading.add(f.rel);
        api('GET', 'api/codemap/text?path=' + encodeURIComponent(f.rel)).then(function (d) {
          f.text = d.lines; f.toks = tokenize(d.lines, f.lang); f.mini = null;
          memLines += d.lines.length;
          if (T3 && T3.byRel[f.rel]) { T3.dirty.add(f.rel); redraw3(); }
          if (memLines > 400000) evict();
        }).catch(function () { f.failed = true; }).then(function () {
          loading.delete(f.rel);
          loadNote.textContent = loading.size || queue.length ? '取着 ' + (loading.size + queue.length) + ' 个文件…' : '';
          if (alive) { redraw(); pump(); }
        });
      }
      loadNote.textContent = loading.size || queue.length ? '取着 ' + (loading.size + queue.length) + ' 个文件…' : '';
    }
    function evict() {                                   // 留得太多：最久没看的丢掉全文和小图，再看到再取
      files.filter(function (f) { return f.toks && f !== sel; }).sort(function (a, b) { return a.seen - b.seen; }).some(function (f) {
        memLines -= f.text.length; f.text = f.toks = f.mini = null;
        return memLines < 250000;
      });
    }

    // ---- 每个文件先画好的小图（远看贴这个）
    function mini(f) {
      if (f.mini) return f.mini;
      const k = 1.4 / (LH * f.s);                         // 小图里一行 1.4 像素
      const c = document.createElement('canvas');
      c.width = Math.max(1, Math.min(4096, Math.ceil(f.cw * k))); c.height = Math.max(1, Math.min(4096, Math.ceil(f.ch * k)));
      const g = c.getContext('2d'), cwk = CW * f.s * k, lh = LH * f.s * k;
      for (let i = 0; i < f.toks.length; i++) {
        const col = Math.floor(i / f.L), row = i % f.L, t = f.toks[i];
        const x0 = col * STEP * f.s * k + GUT * cwk, y0 = row * lh + lh * 0.2;
        for (let j = 0; j < t.length; j += 5) {
          if (t[j + 2] >= COLC) break;
          g.fillStyle = P.tok[t[j + 4]];
          g.fillRect(x0 + t[j + 2] * cwk, y0, (Math.min(t[j + 3], COLC) - t[j + 2]) * cwk, lh * 0.62);
        }
      }
      f.mini = c;
      return c;
    }

    function tint(f) {
      if (mode === 'lang') return [TINT[f.lang] || TINT.text, 0.16];
      if (mode === 'recent') {
        const d = (now - f.mtime) / 86400;
        return d < 1 ? ['#ef4444', 0.32] : d < 3 ? ['#f97316', 0.26] : d < 7 ? ['#f59e0b', 0.2] : d < 30 ? ['#eab308', 0.1] : null;
      }
      if (mode === 'churn') return f.commits ? ['#6366f1', Math.min(0.42, 0.06 + Math.log(1 + f.commits) / 9)] : null;
      if (mode === 'diff') return diff[f.rel] ? ['#fab219', 0.22] : null;
      return null;
    }
    function lineXY(f, i) {                               // 第 i 行（从 0 数）在图上的左上角
      const col = Math.floor(i / f.L), row = i % f.L;
      return { x: f.cx + col * STEP * f.s, y: f.cy + row * LH * f.s };
    }

    // ---- 画一帧：只画看得见的
    function draw() {
      raf = 0;
      if (!alive || !dirty || !map || !is2d()) return;
      if (view === 'flow') { drawFlow(); return; }
      dirty = false; frame++;
      const t0 = performance.now();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = P.plane; ctx.fillRect(0, 0, W, H);
      const vx0 = cam.x - W / 2 / cam.z, vy0 = cam.y - H / 2 / cam.z, vx1 = cam.x + W / 2 / cam.z, vy1 = cam.y + H / 2 / cam.z;
      const vis = function (o) { return o.x < vx1 && o.x + o.w > vx0 && o.y < vy1 && o.y + o.h > vy0; };
      const z = cam.z;
      map.folders.forEach(function (d) {                  // 文件夹：底色、框、名字
        if (!vis(d)) return;
        const x = sx(d.x), y = sy(d.y), w = d.w * z, h = d.h * z;
        if (w < 2) return;
        ctx.fillStyle = P.folder; ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = P.folderLine; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
        const fs = Math.min(FHEAD * 0.55 * z, 26);
        if (fs >= 7) {
          ctx.fillStyle = P.muted; ctx.font = '600 ' + fs + 'px system-ui,"Microsoft YaHei",sans-serif'; ctx.textBaseline = 'middle';
          ctx.fillText(d.name + '/', x + FPAD * z + 2, y + FHEAD * z / 2, Math.max(w - 8, 10));
        }
      });
      if (tilt) {                                         // 斜着看：文件块底下一道影子，有点立体
        ctx.fillStyle = P.dark ? 'rgba(0,0,0,.55)' : 'rgba(0,0,0,.12)';
        map.files.forEach(function (f) { if (vis(f)) ctx.fillRect(sx(f.x) + 3, sy(f.y) + 4, f.w * z, f.h * z); });
      }
      const hitsBy = search ? search.by : null;
      map.files.forEach(function (f) {
        if (!vis(f)) return;
        const x = sx(f.x), y = sy(f.y), w = f.w * z, h = f.h * z;
        ctx.fillStyle = P.card; ctx.fillRect(x, y, w, h);
        const tn = tint(f);
        if (tn) { ctx.globalAlpha = tn[1]; ctx.fillStyle = tn[0]; ctx.fillRect(x, y, w, h); ctx.globalAlpha = 1; }
        if (w < 3 || h < 3) return;
        const lh = LH * f.s * z;                          // 这一块里一行多高（像素）
        if (lh > 0.25) need(f);
        if (f.toks) {
          if (lh < 2.6) {                                 // 远：贴小图
            const m = mini(f);
            ctx.globalAlpha = 0.95;
            ctx.drawImage(m, sx(f.cx), sy(f.cy), m.width / (1.4 / (LH * f.s)) * z, m.height / (1.4 / (LH * f.s)) * z);
            ctx.globalAlpha = 1;
          } else drawLines(f, lh, vy0, vy1, vx0, vx1);
        } else if (lh > 0.25) {                           // 还没取到：淡淡的横纹占位
          ctx.fillStyle = P.line;
          for (let yy = sy(f.cy); yy < sy(f.cy + f.ch); yy += Math.max(lh * 2, 3)) ctx.fillRect(sx(f.cx), yy, f.cw * z * 0.6, Math.max(lh * 0.6, 1));
        }
        if (mode === 'diff' && diff[f.rel] && lh > 0.25) diff[f.rel].forEach(function (m) {   // 没交的改动：那几行左边一道色条
          ctx.fillStyle = P.diff[m[2]] || P.diff.改;
          for (let i = m[0] - 1; i < Math.min(m[0] - 1 + m[1], f.lines); i++) {
            const p = lineXY(f, i);
            if (p.y > vy1 || p.y + LH * f.s < vy0) continue;
            ctx.fillRect(sx(p.x), sy(p.y), Math.max(GUT * CW * f.s * z * 0.4, 2), Math.max(lh, 1));
          }
        });
        if (hitsBy && hitsBy[f.rel]) hitsBy[f.rel].forEach(function (n) {   // 找到的那几行：黄底
          const p = lineXY(f, n - 1);
          ctx.fillStyle = P.hit; ctx.fillRect(sx(p.x), sy(p.y), Math.max(COLW * f.s * z, 2), Math.max(lh, 1.5));
        });
        const hs = Math.min(f.head * 0.62 * z, 20);       // 文件名
        if (hs >= 6.5 && w > 24) {
          ctx.fillStyle = P.fg; ctx.font = '600 ' + hs + 'px system-ui,"Microsoft YaHei",sans-serif'; ctx.textBaseline = 'middle';
          ctx.fillText(f.name, x + 4, y + f.head * z / 2, w - 8);
          if (hs >= 10 && w > 160) {
            ctx.fillStyle = P.muted; ctx.font = (hs * 0.75) + 'px system-ui,sans-serif'; ctx.textAlign = 'right';
            ctx.fillText(f.lines + '', x + w - 4, y + f.head * z / 2); ctx.textAlign = 'left';
          }
        }
        const lit = (search && search.names.has(f.rel)) || f === sel || (uses && uses.files.has(f.rel));
        if (lit || f === hover) {
          ctx.strokeStyle = f === sel ? P.accent : lit ? '#fab219' : P.muted; ctx.lineWidth = f === sel || lit ? 2 : 1;
          ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
        }
      });
      if (sel && selLine) {                               // 选中的那一行
        const p = lineXY(sel, selLine - 1);
        ctx.strokeStyle = P.accent; ctx.lineWidth = 1.5;
        ctx.strokeRect(sx(p.x), sy(p.y), COLW * sel.s * z, Math.max(LH * sel.s * z, 2));
      }
      drawLabels(vis);
      if (uses && uses.from) drawArcs();
      stats.frames++; stats.ms = Math.round((performance.now() - t0) * 10) / 10;
    }

    let MONO = 0;
    function mono() {                                    // 等宽字一个字宽是字号的几倍（量一次）：字号按它算，字正好落在格子里不留缝
      if (!MONO) { ctx.font = '100px ' + FONT; MONO = ctx.measureText('0123456789').width / 1000 || 0.55; }
      return MONO;
    }
    function drawLines(f, lh, vy0, vy1, vx0, vx1) {       // 近：直接画细线，再近画字和行号
      const textMode = lh >= 7, cwp = CW * f.s * cam.z;
      if (textMode) { const fs = cwp / mono(); ctx.font = fs + 'px ' + FONT; ctx.textBaseline = 'top'; }
      for (let col = 0; col < f.cols; col++) {
        const cx0 = f.cx + col * STEP * f.s;
        if (cx0 > vx1 || cx0 + COLW * f.s < vx0) continue;
        const r0 = Math.max(0, Math.floor((vy0 - f.cy) / (LH * f.s))), r1 = Math.min(f.L - 1, Math.ceil((vy1 - f.cy) / (LH * f.s)));
        const px = sx(cx0), gut = GUT * cwp;
        if (textMode) { ctx.save(); ctx.beginPath(); ctx.rect(px, sy(f.cy), COLW * f.s * cam.z, f.ch * cam.z); ctx.clip(); }   // 长行（中文多的）不压到下一栏
        for (let r = r0; r <= r1; r++) {
          const i = col * f.L + r;
          if (i >= f.toks.length) break;
          const t = f.toks[i], y = sy(f.cy + r * LH * f.s);
          if (textMode && lh >= 9) {
            ctx.fillStyle = P.muted; ctx.globalAlpha = 0.6; ctx.textAlign = 'right';
            ctx.fillText(String(i + 1), px + gut - cwp, y + lh * 0.1); ctx.textAlign = 'left'; ctx.globalAlpha = 1;
          }
          for (let j = 0; j < t.length; j += 5) {
            if (t[j + 2] >= COLC) break;
            ctx.fillStyle = P.tok[t[j + 4]];
            if (textMode) {
              let s = f.text[i].slice(t[j], t[j + 1]);
              if (t[j + 3] > COLC) s = s.slice(0, Math.max(COLC - t[j + 2], 1));
              ctx.fillText(s, px + gut + t[j + 2] * cwp, y + lh * 0.1);
            } else ctx.fillRect(px + gut + t[j + 2] * cwp, y + lh * 0.22, (Math.min(t[j + 3], COLC) - t[j + 2]) * cwp, lh * 0.56);
          }
        }
        if (textMode) ctx.restore();
      }
    }

    function pill(text, x, y, maxW, size, center) {      // 远看也认得出：一小块底色上写名字
      ctx.font = '600 ' + size + 'px system-ui,"Microsoft YaHei",sans-serif'; ctx.textBaseline = 'middle';
      const w = Math.min(ctx.measureText(text).width + size, maxW), h = size * 1.6;
      const x0 = center ? x - w / 2 : x, y0 = center ? y - h / 2 : y;
      ctx.globalAlpha = 0.88; ctx.fillStyle = P.card; ctx.fillRect(x0, y0, w, h); ctx.globalAlpha = 1;
      ctx.fillStyle = P.fg; ctx.fillText(text, x0 + size / 2, y0 + h / 2, w - size);
    }
    function drawLabels(vis) {
      const z = cam.z;
      map.files.forEach(function (f) {
        if (!vis(f) || Math.min(f.head * 0.62 * z, 20) >= 6.5) return;
        const w = f.w * z, h = f.h * z;
        if (w >= 90 && h >= 36) pill(f.name, sx(f.x) + 3, sy(f.y) + 3, w - 6, 11, false);
      });
      map.folders.forEach(function (d) {
        if (!vis(d) || FHEAD * 0.55 * z >= 7) return;
        const w = d.w * z, h = d.h * z;
        if (w >= 150 && h >= 90) pill(d.name + '/', sx(d.x) + w / 2, sy(d.y) + h / 2, w - 10, Math.min(13 + Math.sqrt(w * h) / 60, 22), true);
      });
    }

    function drawArcs() {                                 // 谁用到它：从定义那行画弧线连到每个用到的地方
      const a = byRel[uses.from.rel];
      if (!a) return;
      const pa = lineXY(a, uses.from.line - 1), ax = sx(pa.x + COLW * a.s / 2), ay = sy(pa.y);
      ctx.strokeStyle = P.accent; ctx.fillStyle = P.accent; ctx.lineWidth = 1.5; ctx.globalAlpha = 0.75;
      uses.hits.forEach(function (h) {
        const b = byRel[h.rel];
        if (!b) return;
        const pb = lineXY(b, h.line - 1), bx = sx(pb.x + COLW * b.s / 2), by = sy(pb.y);
        const mx = (ax + bx) / 2, my = Math.min(ay, by) - Math.max(30, Math.hypot(bx - ax, by - ay) * 0.25);
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.quadraticCurveTo(mx, my, bx, by); ctx.stroke();
        ctx.beginPath(); ctx.arc(bx, by, 3, 0, 7); ctx.fill();
      });
      ctx.beginPath(); ctx.arc(ax, ay, 5, 0, 7); ctx.fill();
      ctx.globalAlpha = 1;
    }

    // ---- 镜头：飞过去
    let fly = null;
    function flyTo(x, y, z) {
      const from = { x: cam.x, y: cam.y, z: cam.z }, t0 = performance.now(), dur = 520;
      z = Math.max(fitZ * 0.5, Math.min(z, 60));
      fly = function (t) {
        const k = Math.min(1, (t - t0) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        const lz = Math.exp(Math.log(from.z) + (Math.log(z) - Math.log(from.z)) * e);
        cam.x = from.x + (x - from.x) * e; cam.y = from.y + (y - from.y) * e; cam.z = lz;
        redraw();
        if (k < 1 && alive) tick(fly); else fly = null;
      };
      tick(fly);
    }
    function flyFile(f) { const n = view === 'flow' && flow ? flow.byRel.get(f.rel) : f; if (n) flyTo(n.x + n.w / 2, n.y + n.h / 2, Math.min(W / n.w, H / n.h) * 0.85); }
    function flyLine(f, n) {
      const p = lineXY(f, n - 1);
      flyTo(p.x + COLW * f.s / 2, p.y, 15 / (LH * f.s));
    }
    function fitAll() { const b = bounds(); if (b) flyTo(b.W / 2, b.H / 2, fitZ); }
    function drawFlow() {
      dirty = false;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);ctx.fillStyle = P.plane;ctx.fillRect(0, 0, W, H);
      if (!flow) return;
      flow.edges.forEach(e => {
        const a = flow.byRel.get(e.from), b = flow.byRel.get(e.to), x1 = sx(a.x + a.w), y1 = sy(a.y + a.h / 2), x2 = sx(b.x), y2 = sy(b.y + b.h / 2);
        const mid = e.from === e.to ? sx(a.x + a.w + 24) : (x1 + x2) / 2;
        ctx.strokeStyle = sel && (sel.rel === e.from || sel.rel === e.to) ? P.accent : P.muted;ctx.lineWidth = 1.3;
        ctx.beginPath();ctx.moveTo(x1, y1);ctx.lineTo(mid, y1);ctx.lineTo(mid, y2);ctx.lineTo(x2, y2);ctx.stroke();
        ctx.fillStyle = ctx.strokeStyle;ctx.beginPath();ctx.moveTo(x2, y2);ctx.lineTo(x2 - 5, y2 - 3);ctx.lineTo(x2 - 5, y2 + 3);ctx.closePath();ctx.fill();
      });
      flow.files.forEach(n => {
        const x = sx(n.x), y = sy(n.y), w = n.w * cam.z, h = n.h * cam.z, f = n.file;
        if (x + w < 0 || x > W || y + h < 0 || y > H) return;
        ctx.fillStyle = P.card;ctx.fillRect(x, y, w, h);ctx.strokeStyle = sel === f || hover === f ? P.accent : P.line;ctx.lineWidth = sel === f ? 2 : 1;ctx.strokeRect(x, y, w, h);
        if (cam.z < 0.15) return;
        ctx.fillStyle = P.fg;ctx.font = Math.max(8, Math.min(15, 13 * cam.z)) + 'px system-ui,"Microsoft YaHei",sans-serif';ctx.textBaseline = 'middle';
        ctx.fillText(f.name, x + 8 * cam.z, y + 17 * cam.z, Math.max(w - 16 * cam.z, 1));
        ctx.fillStyle = P.muted;ctx.font = Math.max(7, Math.min(12, 10 * cam.z)) + 'px system-ui,"Microsoft YaHei",sans-serif';
        ctx.fillText((f.dir || '根目录') + ' · ' + f.lines + ' 行', x + 8 * cam.z, y + 35 * cam.z, Math.max(w - 16 * cam.z, 1));
      });
    }

    // ---- 点到了什么
    function pick(ev) {
      const w = toWorld(toCanvas(ev));
      if (view === 'flow') { const n = flow && flow.files.find(n => w.x >= n.x && w.x <= n.x + n.w && w.y >= n.y && w.y <= n.y + n.h); return { w: w, file: n && n.file, line: 0 }; }
      const f = map.files.find(function (f) { return w.x >= f.x && w.x <= f.x + f.w && w.y >= f.y && w.y <= f.y + f.h; });
      if (!f) return { w: w, folder: map.folders.slice().reverse().find(function (d) { return w.x >= d.x && w.x <= d.x + d.w && w.y >= d.y && w.y <= d.y + d.h; }) };
      let line = 0;
      if (w.y >= f.cy && w.x >= f.cx) {
        const col = Math.floor((w.x - f.cx) / (STEP * f.s)), row = Math.floor((w.y - f.cy) / (LH * f.s));
        if (row < f.L && col < f.cols) { const i = col * f.L + row; if (i < f.lines) line = i + 1; }
      }
      return { w: w, file: f, line: line };
    }

    // ---- 右边：选中的文件
    function pickFile(f, line) {
      sel = f; selLine = line || 0;
      uses = null;
      side.hidden = false;
      paintSide();
      api('GET', 'api/codemap/defs?path=' + encodeURIComponent(f.rel)).then(function (d) {
        if (sel !== f) return;
        defs = d.defs;
        paintSide();
        const hit = selLine && defs.find(function (x) { return x.line === selLine; });
        if (hit) showUses(hit);
      }).catch(function () {});
      redraw();
    }
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function paintSide() {
      if (!sel) { side.hidden = true; return; }
      const f = sel, m = diff[f.rel];
      side.innerHTML = '<div class="cmx-pane-handle" data-cmx-drag tabindex="0" role="button" aria-label="拖动详情 Drag details">详情 Details</div><div class="cmx-pane-body"><button class="x" data-x title="收起（Esc）">×</button><h4>' + esc(f.name) + '</h4><div class="p">' + esc(f.rel) + '</div>'
        + (f.says ? '<div class="says">' + esc(f.says) + '</div>' : '<div class="says" style="color:var(--muted)">（开头没写说明）</div>')
        + '<div class="kv">' + f.lines + ' 行 · ' + (LANGNAME[f.lang] || f.lang)
        + (git ? (f.commits ? ' · 改过 ' + f.commits + ' 次 · 最后 ' + esc(f.who.replace(/^agent:/, '')) + ' ' + esc(f.at.slice(5)) : ' · 还没进 git 记账') : '')
        + (m ? ' · 没交的改动 ' + m.length + ' 处' : '') + (selLine ? ' · 第 ' + selLine + ' 行' : '') + '</div>'
        + whyLine(f)
        + '<div class="acts"><button class="sbtn" data-open>打开</button><button class="sbtn" data-flyfile>飞过去</button>'
        + (view !== 'flat' ? '<button class="sbtn" data-read title="切到平铺地图，拉近到能读的字">读代码</button>' : '') + '</div>'
        + (uses ? '<h5>用到「' + esc(uses.word) + '」的地方 · ' + uses.hits.length + (uses.more ? '+' : '') + ' 处</h5>'
          + (uses.hits.length ? uses.hits.map(function (h, i) {
            return '<div class="row" data-use="' + i + '"><b>' + esc(h.rel.split('/').pop()) + '</b><span class="n">' + h.line + '</span></div><div class="row" data-use="' + i + '"><span class="t">' + esc(h.text) + '</span></div>';
          }).join('') : '<div class="kv">别处没用到</div>') : '')
        + '<h5>函数和类 · ' + defs.length + '（点一个看谁用到它）</h5>'
        + (defs.length ? defs.map(function (d, i) {
          return '<div class="row' + (uses && uses.from.line === d.line && uses.from.rel === f.rel ? ' on' : '') + '" data-def="' + i + '"><b>' + esc(d.name) + '</b><span class="n">' + d.kind + ' · ' + d.line + '</span></div>';
          }).join('') : '<div class="kv">' + (KW[f.lang] ? '没找到' : '这种文件不分函数') + '</div>')
        + '</div><button type="button" class="cmx-pane-size" data-cmx-size aria-label="拖动或用方向键调整阅读窗大小 Drag or use arrow keys to resize reading pane" title="调整大小 Resize">↘</button>';
      syncPane();
    }
    function showUses(d) {
      api('GET', 'api/modules/' + encodeURIComponent(mod) + '/codemap/uses?word=' + encodeURIComponent(d.name) + '&path=' + encodeURIComponent(sel.rel) + '&line=' + d.line).then(function (r) {
        uses = { word: d.name, hits: r.hits, more: r.more, from: { rel: sel.rel, line: d.line }, files: new Set(r.hits.map(function (h) { return h.rel; })) };
        selLine = d.line;
        paintSide(); redraw(); redraw3();
      }).catch(function (e) { if (opts.toast) opts.toast(e.message); });
    }
    side.addEventListener('click', function (e) {
      const t = e.target;
      if (t.closest('[data-x]')) { sel = null; uses = null; selLine = 0; paintSide(); redraw(); return; }
      if (t.closest('[data-open]') && sel) { opts.open(sel.path, selLine); return; }
      if (t.closest('[data-flyfile]') && sel) { if (is2d()) flyFile(sel); else fly3(sel); return; }
      if (t.closest('[data-read]') && sel) { readFile(sel, selLine); return; }
      const dv = t.closest('[data-def]');
      if (dv) { const d = defs[+dv.dataset.def]; if (view === 'flat') flyLine(sel, d.line); showUses(d); return; }
      const uv = t.closest('[data-use]');
      if (uv && uses) { const h = uses.hits[+uv.dataset.use], f = byRel[h.rel]; if (f) { if (view === 'flat') flyLine(f, h.line); else if (view === 'flow') flyFile(f); else fly3(f); } }
    });

    // ---- 图例
    function paintLegend() {
      const sw = function (c, a) { return '<i style="background:' + c + ';opacity:' + Math.max(a * 2.6, 0.35) + '"></i>'; };
      let h = '';
      if (mode === 'lang') {
        const seen = {};
        files.forEach(function (f) { seen[f.lang] = (seen[f.lang] || 0) + f.lines; });
        h = Object.keys(seen).sort(function (a, b) { return seen[b] - seen[a]; }).map(function (l) { return '<span>' + sw(TINT[l] || TINT.text, 0.16) + esc(LANGNAME[l] || l) + '</span>'; }).join('');
      } else if (mode === 'recent') h = '<span>' + sw('#ef4444', .32) + '今天</span><span>' + sw('#f97316', .26) + '三天内</span><span>' + sw('#f59e0b', .2) + '一周内</span><span>' + sw('#eab308', .1) + '一个月内</span>';
      else if (mode === 'churn') h = git ? '<span>' + sw('#6366f1', .1) + '改得少</span><span>' + sw('#6366f1', .42) + '改得多</span><span>（git 记账里改过几次）</span>' : '<span>这个项目没开 git 记账</span>';
      else {
        const n = Object.keys(diff).filter(function (r) { return byRel[r]; }).length;
        h = git ? '<span>' + sw(P.diff.加, .4) + '加的行</span><span>' + sw(P.diff.改, .4) + '改的行</span><span>' + sw(P.diff.删, .4) + '删了的地方</span><span>' + n + ' 个文件有没交的改动</span>' : '<span>这个项目没开 git 记账</span>';
      }
      legend.innerHTML = h;
    }

    // ---- 找
    let qt = 0;
    q.addEventListener('input', function () { clearTimeout(qt); qt = setTimeout(runSearch, 300); });
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && view !== 'flat') {             // 3D 里回车：一个个文件飞过去
        e.preventDefault();
        const rels = search ? Array.from(new Set(Array.from(search.names).concat(search.hits.map(function (h) { return h.rel; })))) : [];
        if (rels.length) { hitIdx = (hitIdx + 1) % rels.length; const f = byRel[rels[hitIdx]]; if (f) { if (view === 'flow') flyFile(f); else fly3(f); pickFile(f, 0); } }
        return;
      }
      if (e.key === 'Enter') { e.preventDefault(); if (search && search.hits.length) { hitIdx = (hitIdx + 1) % search.hits.length; const h = search.hits[hitIdx], f = byRel[h.rel]; if (f) { flyLine(f, h.line); pickFile(f, h.line); } } else if (search && search.names.size) flyFile(byRel[Array.from(search.names)[0]]); }
      if (e.key === 'Escape') { q.value = ''; runSearch(); }
    });
    function runSearch() {
      const v = q.value.trim();
      hitIdx = -1;
      if (!v) { search = null; paintStat(); redraw(); redraw3(); return; }
      api('GET', 'api/modules/' + encodeURIComponent(mod) + '/codemap/search?q=' + encodeURIComponent(v)).then(function (d) {
        if (q.value.trim() !== v) return;
        const by = {};
        d.hits.forEach(function (h) { (by[h.rel] = by[h.rel] || []).push(h.line); });
        search = { q: v, hits: d.hits, by: by, names: new Set(d.names), more: d.more };
        paintStat(); redraw(); redraw3();
        if (view !== 'flat') { const first = d.names[0] || (d.hits[0] && d.hits[0].rel); if (first && byRel[first]) { if (view === 'flow') flyFile(byRel[first]); else fly3(byRel[first]); } }
      }).catch(function () {});
    }
    function paintStat() {
      const lines = files.reduce(function (a, f) { return a + f.lines; }, 0);
      stat.textContent = search ? '「' + search.q + '」' + search.hits.length + (search.more ? '+' : '') + ' 处 · ' + Object.keys(search.by).length + ' 个文件' + (search.names.size ? ' · 文件名对上 ' + search.names.size + ' 个' : '') + (search.hits.length ? ' · 回车一处处飞过去' : '')
        : files.length + ' 个文件 · ' + lines + ' 行' + (view === 'flow' && flow ? ' · ' + flow.edges.length + ' 条已记录依赖' + (flow.truncated ? ' · ' + flow.truncated + ' 个引用列表已截断' : '') : T3 && !is2d() && T3.tiers ? ' · ' + T3.tiers.length + ' 层' : '');
    }

    // ---- 鼠标、键盘
    let drag = null;
    cv.addEventListener('wheel', function (e) {
      e.preventDefault();
      const p = toCanvas(e), before = toWorld(p);
      cam.z = Math.max(fitZ * 0.5, Math.min(cam.z * Math.exp(-e.deltaY * 0.0016), 60));
      const after = toWorld(p);
      cam.x += before.x - after.x; cam.y += before.y - after.y;
      redraw();
    }, { passive: false });
    cv.addEventListener('contextmenu', function (e) { if (tilt) e.preventDefault(); });
    cv.addEventListener('mousedown', function (e) {
      cv.focus();
      drag = { x: e.clientX, y: e.clientY, p: toCanvas(e), btn: e.button, moved: false, shift: e.shiftKey };
      cv.classList.add('grab'); world.classList.add('drag');
    });
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    function onMove(e) {
      if (!alive) return;
      if (!drag) { hoverAt(e); return; }
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 3) drag.moved = true;
      if (tilt && view !== 'flow' && (drag.btn === 2 || drag.shift)) {
        tilt.r += (e.clientX - drag.x) * 0.3; tilt.a = Math.max(0, Math.min(68, tilt.a - (e.clientY - drag.y) * 0.25));
        drag.x = e.clientX; drag.y = e.clientY; setTilt(); return;
      }
      const p = toCanvas(e);
      cam.x -= (p.x - drag.p.x) / cam.z; cam.y -= (p.y - drag.p.y) / cam.z;
      drag.p = p; drag.x = e.clientX; drag.y = e.clientY;
      redraw();
    }
    function onUp(e) {
      if (!drag) return;
      const d = drag;
      drag = null; cv.classList.remove('grab'); world.classList.remove('drag');
      if (!d.moved && d.btn === 0 && e.target === cv) {
        const h = pick(e);
        if (h.file) pickFile(h.file, cam.z * LH * h.file.s >= 7 ? h.line : 0);
        else { sel = null; uses = null; selLine = 0; paintSide(); redraw(); }
      }
    }
    cv.addEventListener('dblclick', function (e) {
      const h = pick(e);
      if (view === 'flow') { if (h.file) readFile(h.file, 0); else fitAll(); return; }
      if (h.file) { if (cam.z * LH * h.file.s >= 4 && h.line) flyLine(h.file, h.line); else flyFile(h.file); }
      else if (h.folder) flyTo(h.folder.x + h.folder.w / 2, h.folder.y + h.folder.h / 2, Math.min(W / h.folder.w, H / h.folder.h) * 0.9);
      else fitAll();
    });
    cv.addEventListener('mouseleave', function () { tip.style.display = 'none'; if (hover) { hover = null; redraw(); } });
    function hoverAt(e) {
      if (e.target !== cv || !map) return;
      const h = pick(e), r = stage.getBoundingClientRect();
      if (h.file !== hover) { hover = h.file || null; redraw(); }
      if (!h.file) { tip.style.display = 'none'; return; }
      tip.textContent = h.file.rel + ' · ' + h.file.lines + ' 行' + (h.line && cam.z * LH * h.file.s >= 4 ? ' · 第 ' + h.line + ' 行' : '');
      tip.style.display = 'block';
      tip.style.left = Math.min(e.clientX - r.left + 14, r.width - tip.offsetWidth - 6) + 'px';
      tip.style.top = (e.clientY - r.top + 16) + 'px';
    }
    cv.addEventListener('keydown', function (e) {
      const k = e.key, step = 80 / cam.z;
      if (k === '+' || k === '=') cam.z = Math.min(cam.z * 1.25, 60);
      else if (k === '-') cam.z = Math.max(cam.z / 1.25, fitZ * 0.5);
      else if (k === '0') { fitAll(); return; }
      else if (k === 'ArrowLeft') cam.x -= step; else if (k === 'ArrowRight') cam.x += step;
      else if (k === 'ArrowUp') cam.y -= step; else if (k === 'ArrowDown') cam.y += step;
      else if (k === 'Escape') { if (fsPending || el.classList.contains('cmx-fs') || document.fullscreenElement === el) return; sel = null; uses = null; selLine = 0; paintSide(); }
      else if (k === '/') { q.focus(); }
      else return;
      e.preventDefault(); redraw();
    });
    el.querySelector('.cmx-bar').addEventListener('click', function (e) {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.view) { setView(b.dataset.view); return; }
      if (b.dataset.mode) {
        mode = b.dataset.mode;
        el.querySelectorAll('[data-mode]').forEach(function (x) { x.classList.toggle('on', x === b); });
        if (mode === 'diff') loadDiff();
        try { localStorage.setItem('tpl_cmap_mode', mode); } catch (_) {}
        paintLegend(); redraw(); retint3();
      } else if (b.dataset.act === 'full') fullscreen();
      else if (b.dataset.act === 'notes') openNotes();
      else if (b.dataset.act === 'zoom-in' || b.dataset.act === 'zoom-out') zoom(b.dataset.act === 'zoom-in' ? 1.2 : 1 / 1.2);
      else if (b.dataset.act === 'fit') { if (is2d()) fitAll(); else home3(true); }
      else if (b.dataset.act === 'tilt') {
        tilt = tilt ? null : { a: 48, r: -12 };
        b.classList.toggle('on', !!tilt);
        setTilt(); size();
      }
    });
    const colorSelect = el.querySelector('[data-cmx-color]');
    function changeColor() { const m = colorSelect.value;if (!MODES.some(function (x) { return x[0] === m; })) return;mode = m;if (mode === 'diff') loadDiff();try { localStorage.setItem('tpl_cmap_mode', mode); } catch (_) {} paintLegend();redraw();retint3(); }
    if (colorSelect) colorSelect.addEventListener('change', changeColor);
    function onResize() { if (alive) { size();positionPane();applyPaneSize(); } }
    window.addEventListener('resize', onResize);
    const onTheme = function () {                       // 换了亮 / 暗：颜色真变了才重画小图
      const np = palette();
      if (np.card === P.card && np.fg === P.fg) return;
      P = np; files.forEach(function (f) { f.mini = null; }); redraw(); retint3();
    };
    const themeWatch = new MutationObserver(onTheme);
    themeWatch.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
    const mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : null;
    const onMq = onTheme;
    if (mq && mq.addEventListener) mq.addEventListener('change', onMq);

    function loadDiff() {
      return api('GET', 'api/codemap/diff').then(function (d) { diff = d.marks || {}; paintLegend(); paintSide(); redraw(); retint3(); }).catch(function () {});
    }

    // ---------------------------------------------------------------- 3D 台阶（S1-1 S2-24）
    function whyLine(f) {                                // 这个文件为什么在这一层
      if (f.fan_in === undefined) return '';
      const bits = [];
      bits.push(f.fan_in ? '被 ' + f.fan_in + ' 个文件用到' : '没有别的文件用到它');
      if (f.entry) bits.push('是入口');
      if (f.tests) bits.push(f.tests + ' 个测试守着');
      if (f.is_test) bits.push('它是测试');
      const tier = T3 && T3.tierOf ? T3.tierOf[f.rel] : null;
      return '<div class="cmx-why">' + (tier ? '<b>' + esc(tier) + '</b> · ' : '') + esc(bits.join(' · '))
        + (f.users && f.users.length ? '<div class="p">用到它的：' + esc(f.users.map(function (u) { return u.split('/').pop(); }).join('、')) + (f.fan_in > f.users.length ? ' 等' : '') + '</div>' : '') + '</div>';
    }
    function rank(v) {                                    // 分层：从上到下，每层一组文件
      const fs = files.slice();
      if (!fs.length) return [];
      if (v === 'fold') {                                 // 文件夹台阶：外层（离模块根近）的在上
        const depth = function (f) { return f.dir ? f.dir.split('/').length : 0; };
        const ds = Array.from(new Set(fs.map(depth))).sort(function (a, b) { return a - b; }), cap = ds.slice(0, 6);
        const ts = cap.map(function (d, i) { return { files: [], name: i === cap.length - 1 && ds.length > cap.length ? '再往里的' : i === 0 ? '最外层' : '往里第 ' + i + ' 层' }; });
        fs.forEach(function (f) { let i = cap.indexOf(depth(f)); if (i < 0) i = cap.length - 1; ts[i].files.push(f); });
        ts.forEach(function (t) { t.files.sort(function (a, b) { return (b.score || 0) - (a.score || 0); }); });
        return ts.filter(function (t) { return t.files.length; });
      }
      const key = v === 'heat' ? function (f) { return git ? f.commits * 1e10 + f.mtime : f.mtime; } : function (f) { return (f.score || 0) * 1e10 + f.lines; };
      fs.sort(function (a, b) { return key(b) - key(a); });
      const n = fs.length, T = Math.max(2, Math.min(6, Math.round(Math.sqrt(n) / 2)));
      const names = v === 'heat' ? ['改得最多', '改得多', '常改', '偶尔改', '很少改', '几乎不改'] : ['最核心', '核心', '常用', '一般', '外围', '最底下'];
      const ts = [];
      let from = 0;
      for (let k = 0; k < T; k++) {
        const to = k === T - 1 ? n : Math.max(from + 1, Math.round(n * Math.pow((k + 1) / T, 2)));
        ts.push({ files: fs.slice(from, to), name: k === T - 1 ? names[5] : names[Math.min(k, 4)] });
        from = to;
      }
      return ts.filter(function (t) { return t.files.length; });
    }
    function wt3(f) { return Math.pow(Math.max(f.lines, 8), 0.6); }
    function layout3(ts) {                                // 每层一个方台，越往下越大；文件铺在露出来的那一圈（最顶层铺满）
      const total = files.reduce(function (a, f) { return a + wt3(f); }, 0), minRing = Math.sqrt(total) * 0.05, m = minRing * 0.12;
      let cum = 0, prev = 0;
      ts.forEach(function (t, k) {
        const w = t.files.reduce(function (a, f) { return a + wt3(f); }, 0);
        cum += w;
        let S = Math.sqrt(cum * 1.3);
        if (k > 0) S = Math.max(S, prev + 2 * minRing);
        const a = prev, b = S, rects = k === 0 ? [{ x: -b / 2, z: -b / 2, w: b, d: b }]
          : [{ x: -b / 2, z: a / 2, w: b, d: (b - a) / 2 }, { x: a / 2, z: -a / 2, w: (b - a) / 2, d: a }, { x: -b / 2, z: -a / 2, w: (b - a) / 2, d: a }, { x: -b / 2, z: -b / 2, w: b, d: (b - a) / 2 }];
        const area = rects.reduce(function (s, r) { return s + r.w * r.d; }, 0);
        rects.forEach(function (r) { r.cap = r.w * r.d / area * w; r.items = []; });
        t.files.forEach(function (f) {                    // 重要的先放，前面那条先满
          const x = wt3(f);
          const r = rects.find(function (r) { return r.cap >= x * 0.5; }) || rects.reduce(function (p, r) { return r.cap > p.cap ? r : p; });
          r.cap -= x; r.items.push(f);
        });
        rects.forEach(function (r) {
          if (!r.items.length) return;
          const iw = Math.max(r.w - 2 * m, 0.01), id = Math.max(r.d - 2 * m, 0.01);
          const sum = r.items.reduce(function (s, f) { return s + wt3(f); }, 0), kk = iw * id / sum;
          squarify(r.items.slice().sort(function (p, q) { return wt3(q) - wt3(p); }).map(function (f) { return { it: f, v: wt3(f) * kk }; }), r.x + m, r.z + m, iw, id,
            function (o, x0, z0, w0, d0) { o.it.p3 = { x: x0, z: z0, w: w0, d: d0, tier: k }; });
        });
        t.S = S; prev = S;
      });
      return ts;
    }
    function hexMix(a, b, t) {                            // 两个颜色按 t 混
      const p = function (h) { const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(h) || [0, 'cc', 'cc', 'cc']; return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)]; };
      const x = p(a), y = p(b);
      return '#' + x.map(function (v, i) { return Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0'); }).join('');
    }
    function paintTop(f, cv2) {                           // 顶面：文件名一条 + 代码细线（按块的长宽分栏）
      const g = cv2.getContext('2d'), cw = cv2.width, chh = cv2.height;
      g.fillStyle = P.card; g.fillRect(0, 0, cw, chh);
      const tn = tint(f);
      if (tn) { g.globalAlpha = tn[1]; g.fillStyle = tn[0]; g.fillRect(0, 0, cw, chh); g.globalAlpha = 1; }
      const hh = Math.max(Math.min(chh * 0.12, cw * 0.12), Math.min(chh, 12));
      g.fillStyle = P.dark ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.05)'; g.fillRect(0, 0, cw, hh);
      g.fillStyle = P.fg; g.font = '600 ' + Math.max(hh * 0.62, 6) + 'px system-ui,"Microsoft YaHei",sans-serif'; g.textBaseline = 'middle';
      g.fillText(f.name, hh * 0.3, hh / 2, cw - hh * 0.6);
      if (f.toks) {
        const lay = fitCols(Math.max(f.lines, 1), cw - 4, chh - hh - 3), sc = lay.s, cwk = CW * sc, lh = LH * sc;
        for (let i = 0; i < f.toks.length; i++) {
          const col = Math.floor(i / lay.L), row = i % lay.L, t = f.toks[i];
          const x0 = 2 + col * STEP * sc + GUT * cwk, y0 = hh + 2 + row * lh + lh * 0.2;
          for (let j = 0; j < t.length; j += 5) {
            if (t[j + 2] >= COLC) break;
            g.fillStyle = P.tok[t[j + 4]];
            g.fillRect(x0 + t[j + 2] * cwk, y0, (Math.min(t[j + 3], COLC) - t[j + 2]) * cwk, Math.max(lh * 0.62, 0.35));
          }
        }
      } else {
        g.fillStyle = P.line;
        for (let y = hh + 4; y < chh - 2; y += 5) g.fillRect(4, y, (cw - 8) * (0.35 + 0.4 * ((y * 7) % 10) / 10), 2);
      }
    }
    function loadThree() {
      if (window.__THREE) return Promise.resolve(window.__THREE);
      return import(new URL('lib/three/three.module.js', document.baseURI).href).then(function (m) { window.__THREE = m; return m; });
    }
    function setView(v) {
      if (!VIEWS.some(function (x) { return x[0] === v; })) return;
      if (v === view) return;
      if (is2d()) cameras[view] = Object.assign({}, cam);
      fly = null;
      view = v;
      try { localStorage.setItem('tpl_cmap_shape', v); } catch (_) {}
      paintViewBar();
      size();
      if (is2d()) { const b = bounds(); if (b) cam = cameras[v] || { x: b.W / 2, y: b.H / 2, z: fitZ }; redraw(); return; }
      build3(false);
    }
    function paintViewBar() {
      el.querySelectorAll('[data-view]').forEach(function (x) { x.classList.toggle('on', x.dataset.view === view); });
      el.dataset.overviewMode = view === 'flow' ? 'flow' : view === 'flat' ? 'map' : 'model3d';
      const flat = is2d();
      world.hidden = !flat; holder3.hidden = flat; tiersEl.hidden = flat;if (tiltBtn) tiltBtn.hidden = !flat;
      if (view === 'flow') { if (tiltBtn) tiltBtn.hidden = true;world.style.transform = ''; } else setTilt();
      if (!flat) { tip.style.display = 'none'; }
      paintSide(); paintStat();
    }
    function build3(home) {                               // 摆 3D：第一次先把 three.js 拿来
      if (!map) return;
      loadThree().then(function (THREE) {
        if (!alive || is2d()) return;
        if (!T3) T3 = make3(THREE);
        T3.rebuild(layout3(rank(view)), home);
        paintStat(); paintSide();
      }).catch(function (e) {
        if (!alive || is2d()) return;
        holder3.innerHTML = '<div style="padding:24px;color:var(--muted)">3D 用不了（' + esc(e.message || e) + '），先看平铺地图</div>';
      });
    }
    function redraw3() { if (T3) T3.redraw(); }
    function retint3() { if (T3) T3.retint(); }
    function fly3(f) { if (T3) T3.fly(f); }
    function home3(anim) { if (T3) T3.home(anim); }
    function zoom(factor) { if (is2d()) { cam.z = Math.max(fitZ * 0.5, Math.min(cam.z * factor, 60)); redraw(); } else if (T3) T3.zoom(factor); }
    function readFile(f, line) {                          // 3D 里看中一个，到平铺地图拉近读
      setView('flat');
      setTimeout(function () { if (line) flyLine(f, line); else flyFile(f); pickFile(f, line || 0); }, 60);
    }
    function make3(THREE) {
      const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(stage.clientWidth, stage.clientHeight);
      renderer.domElement.tabIndex = 0;
      holder3.innerHTML = ''; holder3.appendChild(renderer.domElement);
      const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(42, stage.clientWidth / Math.max(stage.clientHeight, 1), 0.1, 100000);
      const hemi = new THREE.HemisphereLight(0xffffff, 0x8a8070, 1.6), sun = new THREE.DirectionalLight(0xffffff, 1.5);
      scene.add(hemi); scene.add(sun);
      const group = new THREE.Group(), arcs = new THREE.Group();
      scene.add(group); scene.add(arcs);
      const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
      const orb = { az: 0.62, pol: 0.98, dist: 100, tx: 0, ty: 0, tz: 0 };
      const S = { renderer: renderer, camera: camera, tiers: null, byRel: {}, meshes: [], dirty: new Set(), tierOf: {}, painted: 0, frames: 0, base: 1, hTier: 1 };
      let raf3 = 0, fly = null, hov = null, arcsKey = '', drag = null, labelEls = [];
      function placeCam() {
        const sp = Math.sin(orb.pol);
        camera.position.set(orb.tx + orb.dist * sp * Math.sin(orb.az), orb.ty + orb.dist * Math.cos(orb.pol), orb.tz + orb.dist * sp * Math.cos(orb.az));
        camera.lookAt(orb.tx, orb.ty, orb.tz);
        sun.position.set(camera.position.x + S.base * 0.4, camera.position.y + S.base, camera.position.z + S.base * 0.2);
      }
      function clear() {
        group.children.slice().forEach(function (o) {
          group.remove(o);
          if (o.geometry) o.geometry.dispose();
          (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) { if (m) { if (m.map) m.map.dispose(); m.dispose(); } });
        });
        S.meshes = []; S.byRel = {}; S.tierOf = {};
      }
      S.rebuild = function (ts, home) {
        clear();
        S.tiers = ts;
        const T = ts.length, base = ts.length ? ts[T - 1].S : 1, hT = base * 0.065;
        S.base = base; S.hTier = hT;
        scene.background = new THREE.Color(P.plane);
        const stone = P.dark ? '#2b3038' : '#e7e1d3';
        ts.forEach(function (t, k) {                      // 台子：上面的小、高
          const h = (T - k) * hT, side = t.S + base * 0.012;
          const box = new THREE.Mesh(new THREE.BoxGeometry(side, h, side), new THREE.MeshLambertMaterial({ color: hexMix(stone, P.dark ? '#000000' : '#ffffff', k * 0.06) }));
          box.position.set(0, h / 2, 0);
          group.add(box);
          t.top = h;
          t.files.forEach(function (f) { S.tierOf[f.rel] = '第 ' + (k + 1) + ' 层 · ' + t.name; });
        });
        const area = ts.reduce(function (a, t) { return a + t.files.reduce(function (b, f) { return b + (f.p3 ? f.p3.w * f.p3.d : 0); }, 0); }, 0) || 1;
        ts.forEach(function (t) {
          t.files.forEach(function (f) {
            const p = f.p3;
            if (!p) return;
            const g = Math.min(p.w, p.d) * 0.07, w = Math.max(p.w - g, p.w * 0.5), d = Math.max(p.d - g, p.d * 0.5), hb = hT * 0.24;
            const px = Math.sqrt(9e6 * p.w * p.d / area);
            const cv2 = document.createElement('canvas');
            cv2.width = Math.max(24, Math.min(1024, Math.round(px * Math.sqrt(p.w / p.d))));
            cv2.height = Math.max(24, Math.min(1024, Math.round(px * Math.sqrt(p.d / p.w))));
            const tex = new THREE.CanvasTexture(cv2);
            tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
            const tn = tint(f), sideCol = tn ? hexMix(P.card, tn[0], Math.min(tn[1] * 3, 0.85)) : P.card;
            const sideM = new THREE.MeshLambertMaterial({ color: sideCol }), topM = new THREE.MeshLambertMaterial({ map: tex });
            const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, hb, d), [sideM, sideM, topM, sideM, sideM, sideM]);
            mesh.position.set(p.x + p.w / 2, t.top + hb / 2, p.z + p.d / 2);
            mesh.userData = { f: f, cv: cv2, tex: tex, side: sideM, top: topM, hb: hb };
            group.add(mesh); S.meshes.push(mesh); S.byRel[f.rel] = mesh;
            S.dirty.add(f.rel);
          });
        });
        labelEls = ts.map(function (t) { const d = document.createElement('div'); d.innerHTML = esc(t.name) + '<span>' + t.files.length + '</span>'; return d; });
        tiersEl.innerHTML = ''; labelEls.forEach(function (d) { tiersEl.appendChild(d); });
        arcsKey = '';
        ts.forEach(function (t) { t.files.forEach(function (f) { need(f); }); });   // 重要的先取全文
        if (home || !S.homed) S.home(false);
        S.redraw();
      };
      S.home = function (anim) {
        const to = { az: 0.62, pol: 0.95, dist: S.base * 1.3, tx: 0, ty: S.tiers ? S.tiers.length * S.hTier * 0.35 : 0, tz: 0 };
        S.homed = true;
        if (anim) go(to); else { Object.assign(orb, to); placeCam(); S.redraw(); }
      };
      function go(to) {                                   // 镜头慢慢过去
        const from = Object.assign({}, orb), t0 = performance.now(), dur = 600;
        let daz = to.az - from.az;
        while (daz > Math.PI) daz -= 2 * Math.PI;
        while (daz < -Math.PI) daz += 2 * Math.PI;
        fly = function (t) {
          const k = Math.min(1, (t - t0) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
          orb.az = from.az + daz * e; orb.pol = from.pol + (to.pol - from.pol) * e;
          orb.dist = Math.exp(Math.log(from.dist) + (Math.log(to.dist) - Math.log(from.dist)) * e);
          orb.tx = from.tx + (to.tx - from.tx) * e; orb.ty = from.ty + (to.ty - from.ty) * e; orb.tz = from.tz + (to.tz - from.tz) * e;
          placeCam(); S.redraw();
          if (k < 1 && alive && T3 === S) tick(fly); else fly = null;
        };
        tick(fly);
      }
      S.fly = function (f) {
        const m = S.byRel[f.rel];
        if (!m) return;
        const p = f.p3, r = Math.max(p.w, p.d);
        go({ az: orb.az, pol: Math.min(orb.pol, 0.9), dist: Math.max(r * 2.2, S.base * 0.08), tx: m.position.x, ty: m.position.y, tz: m.position.z });
      };
      S.zoom = function (factor) { fly = null; orb.dist = Math.max(S.base * 0.02, Math.min(S.base * 5, orb.dist / factor)); placeCam(); S.redraw(); };
      S.cameraState = function () { return Object.assign({}, orb); };
      S.retint = function () {
        if (!S.tiers) return;
        scene.background = new THREE.Color(P.plane);
        S.meshes.forEach(function (m) {
          const f = m.userData.f, tn = tint(f);
          m.userData.side.color.set(tn ? hexMix(P.card, tn[0], Math.min(tn[1] * 3, 0.85)) : P.card);
          S.dirty.add(f.rel);
        });
        S.redraw();
      };
      S.redraw = function () { if (!raf3) { raf3 = 1; tick(render); } };
      function lit(f) {                                   // 这一块该不该亮、亮什么颜色
        if (sel && f === sel) return P.accent;
        if (search && (search.names.has(f.rel) || search.by[f.rel])) return '#fab219';
        if (uses && uses.files.has(f.rel)) return '#f97316';
        if (hov === f) return P.dark ? '#555555' : '#bbbbbb';
        return null;
      }
      function render() {
        raf3 = 0;
        if (!alive || T3 !== S || is2d()) return;
        let n = 0;
        for (const rel of S.dirty) {                      // 一帧最多重画 12 个顶面，取全文时也不卡
          const m = S.byRel[rel];
          S.dirty.delete(rel);
          if (!m) continue;
          paintTop(m.userData.f, m.userData.cv); m.userData.tex.needsUpdate = true; S.painted++;
          if (++n >= 12) break;
        }
        S.meshes.forEach(function (m) {
          const c = lit(m.userData.f);
          m.userData.top.emissive.set(c || '#000000'); m.userData.top.emissiveIntensity = c ? 0.32 : 0;
          m.userData.side.emissive.set(c || '#000000'); m.userData.side.emissiveIntensity = c ? 0.55 : 0;
        });
        const key = uses && uses.from ? uses.from.rel + '#' + uses.from.line + '#' + uses.hits.length : '';
        if (key !== arcsKey) {                            // 谁用到它：从它那块拉弧线到用到的每一块
          arcsKey = key;
          arcs.children.slice().forEach(function (o) { arcs.remove(o); o.geometry.dispose(); o.material.dispose(); });
          const a = key && S.byRel[uses.from.rel];
          if (a) {
            const seen = new Set();
            uses.hits.forEach(function (h) {
              const b = S.byRel[h.rel];
              if (!b || b === a || seen.has(h.rel)) return;
              seen.add(h.rel);
              const p0 = a.position.clone(), p2 = b.position.clone();
              p0.y += a.userData.hb; p2.y += b.userData.hb;
              const mid = p0.clone().add(p2).multiplyScalar(0.5);
              mid.y = Math.max(p0.y, p2.y) + p0.distanceTo(p2) * 0.45 + S.hTier;
              const pts = new THREE.QuadraticBezierCurve3(p0, mid, p2).getPoints(32);
              arcs.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: P.accent })));
            });
          }
        }
        renderer.render(scene, camera);
        S.frames++;
        const r = renderer.domElement.getBoundingClientRect(), v = new THREE.Vector3();
        (S.tiers || []).forEach(function (t, k) {         // 层名：贴在每层台子前左角
          const d = labelEls[k];
          if (!d) return;
          v.set(-t.S / 2, t.top, t.S / 2).project(camera);
          if (v.z > 1) { d.style.display = 'none'; return; }
          d.style.display = '';
          d.style.left = ((v.x + 1) / 2 * r.width - 6) + 'px'; d.style.top = ((1 - v.y) / 2 * r.height) + 'px';
        });
        if (S.dirty.size) S.redraw();
      }
      function hit(ev) {
        const r = renderer.domElement.getBoundingClientRect();
        ndc.set((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1);
        ray.setFromCamera(ndc, camera);
        const got = ray.intersectObjects(S.meshes, false)[0];
        return got ? got.object.userData.f : null;
      }
      const cvs = renderer.domElement;
      cvs.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      cvs.addEventListener('mousedown', function (e) {
        cvs.focus();
        drag = { x: e.clientX, y: e.clientY, btn: e.button, shift: e.shiftKey, moved: false };
        cvs.classList.add('grab');
      });
      function move3(e) {
        if (!alive || T3 !== S || is2d()) return;
        if (!drag) {
          if (e.target !== cvs) return;
          const f = hit(e), r = stage.getBoundingClientRect();
          if (f !== hov) { hov = f; S.redraw(); }
          if (!f) { tip.style.display = 'none'; return; }
          tip.textContent = f.rel + ' · ' + f.lines + ' 行 · ' + (S.tierOf[f.rel] || '') + (f.fan_in !== undefined ? ' · 被 ' + f.fan_in + ' 个文件用到' : '');
          tip.style.display = 'block';
          tip.style.left = Math.min(e.clientX - r.left + 14, r.width - tip.offsetWidth - 6) + 'px';
          tip.style.top = (e.clientY - r.top + 16) + 'px';
          return;
        }
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
        drag.x = e.clientX; drag.y = e.clientY;
        if (drag.btn === 2 || drag.shift) {               // 右键（或 Shift）拖：平移
          const k = orb.dist * 0.0016, ca = Math.cos(orb.az), sa = Math.sin(orb.az);
          orb.tx -= (dx * ca + dy * sa) * k; orb.tz -= (-dx * sa + dy * ca) * k;
        } else {                                          // 左键拖：转
          orb.az -= dx * 0.006; orb.pol = Math.max(0.12, Math.min(1.5, orb.pol - dy * 0.005));
        }
        placeCam(); S.redraw();
      }
      function up3(e) {
        if (!drag) return;
        const d = drag;
        drag = null; cvs.classList.remove('grab');
        if (!d.moved && d.btn === 0 && e.target === cvs) {
          const f = hit(e);
          if (f) pickFile(f, 0); else { sel = null; uses = null; selLine = 0; paintSide(); }
          S.redraw();
        }
      }
      window.addEventListener('mousemove', move3);
      window.addEventListener('mouseup', up3);
      cvs.addEventListener('wheel', function (e) {
        e.preventDefault();
        orb.dist = Math.max(S.base * 0.02, Math.min(S.base * 5, orb.dist * Math.exp(e.deltaY * 0.0012)));
        placeCam(); S.redraw();
      }, { passive: false });
      cvs.addEventListener('dblclick', function (e) {
        const f = hit(e);
        if (f) readFile(f, 0); else S.home(true);
      });
      cvs.addEventListener('keydown', function (e) {
        const k = e.key;
        if (k === 'ArrowLeft') orb.az += 0.12; else if (k === 'ArrowRight') orb.az -= 0.12;
        else if (k === 'ArrowUp') orb.pol = Math.max(0.12, orb.pol - 0.08); else if (k === 'ArrowDown') orb.pol = Math.min(1.5, orb.pol + 0.08);
        else if (k === '+' || k === '=') orb.dist = Math.max(S.base * 0.02, orb.dist / 1.2);
        else if (k === '-') orb.dist = Math.min(S.base * 5, orb.dist * 1.2);
        else if (k === '0') { S.home(true); return; }
        else if (k === 'Escape') { if (fsPending || el.classList.contains('cmx-fs') || document.fullscreenElement === el) return; sel = null; uses = null; selLine = 0; paintSide(); }
        else if (k === '/') { q.focus(); }
        else return;
        e.preventDefault(); placeCam(); S.redraw();
      });
      S.dispose = function () {
        window.removeEventListener('mousemove', move3); window.removeEventListener('mouseup', up3);
        clear(); renderer.dispose();
      };
      return S;
    }
    function viewport() { return { width: window.innerWidth, height: window.innerHeight }; }
    function positionPane() {
      if (!paneBox) return;paneBox = clampPane(paneBox, viewport());
      Object.assign(side.style, { position: 'fixed', left: paneBox.x + 'px', top: paneBox.y + 'px', right: 'auto', bottom: 'auto', width: paneBox.width + 'px', height: paneBox.height + 'px', maxWidth: 'none', maxHeight: 'none', margin: '0', zIndex: '3' });
    }
    function applyPaneSize() {
      if (paneBox || !paneSized) return;
      const bounds = { width: stage.clientWidth || 1000, height: stage.clientHeight || 600 }, b = clampPane({ x: 8, y: 8, width: paneSize.width, height: paneSize.height }, bounds);
      Object.assign(side.style, { width: b.width + 'px', height: b.height + 'px', bottom: 'auto', maxWidth: 'none', maxHeight: 'none' });
    }
    function resizePane(width, height) {
      if (!alive) return;
      paneSize = { width: Math.min(960, Math.max(180, Number.isFinite(width) ? width : 304)), height: Math.min(1200, Math.max(120, Number.isFinite(height) ? height : 520)) };paneSized = true;
      if (paneBox) { paneBox.width = paneSize.width;paneBox.height = paneSize.height;positionPane(); }else applyPaneSize();
    }
    function restorePane() {
      if (paneStyle) { Object.keys(paneStyle).forEach(function (k) { side.style[k] = paneStyle[k]; });side.classList.remove('cmx-pane-floating'); }
      if (paneParent && side.parentNode !== paneParent) { if (paneNext && paneNext.parentNode === paneParent) paneParent.insertBefore(side, paneNext);else paneParent.appendChild(side); }
      paneStyle = paneBox = paneDrag = paneResize = paneParent = paneNext = paneRect = null;applyPaneSize();
    }
    function syncPane() {
      const active = alive && fsWanted && (document.fullscreenElement === el || el.classList.contains('cmx-fs'));
      if (!active) { restorePane();return; }if (side.hidden || paneBox) return;
      const r = paneRect || side.getBoundingClientRect(), v = viewport();paneStyle = {};
      ['position','left','top','right','bottom','width','height','maxWidth','maxHeight','margin','zIndex'].forEach(function (k) { paneStyle[k] = side.style[k] || ''; });
      paneParent = side.parentNode;paneNext = side.nextSibling;el.appendChild(side);side.classList.add('cmx-pane-floating');
      const width = paneSized ? paneSize.width : r.width || 304, height = paneSized ? paneSize.height : r.height || 520;
      paneBox = { x: (v.width || 1024) - width - 16, y: 64, width: width, height: height };positionPane();
    }
    function onPaneDown(e) {
      if (e.button !== 0 || !alive) return;
      const grip = e.target.closest('[data-cmx-size]');
      if (grip && side.contains(grip)) {
        const r = paneBox || side.getBoundingClientRect();paneDrag = null;paneResize = { id: e.pointerId, x: e.clientX, y: e.clientY, width: r.width, height: r.height };e.preventDefault();e.stopPropagation();return;
      }
      const handle = e.target.closest('[data-cmx-drag]');if (e.button !== 0 || !paneBox || !handle || !side.contains(handle)) return;
      e.preventDefault();e.stopPropagation();paneDrag = { x: e.clientX, y: e.clientY, px: paneBox.x, py: paneBox.y };if (handle.setPointerCapture) handle.setPointerCapture(e.pointerId);
    }
    function onPaneMove(e) { if (paneResize) { if (paneResize.id != null && paneResize.id !== e.pointerId) return;resizePane(paneResize.width + e.clientX - paneResize.x, paneResize.height + e.clientY - paneResize.y);return; }if (!paneDrag || !paneBox) return;paneBox.x = paneDrag.px + e.clientX - paneDrag.x;paneBox.y = paneDrag.py + e.clientY - paneDrag.y;positionPane(); }
    function onPaneUp(e) { if (paneResize && e && paneResize.id != null && paneResize.id !== e.pointerId) return;paneDrag = paneResize = null; }
    function onPaneKey(e) {
      if (e.target.matches('[data-cmx-size]') && ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].indexOf(e.key) >= 0) {
        e.preventDefault();const step = e.shiftKey ? 32 : 8, r = paneBox || (paneSized ? paneSize : side.getBoundingClientRect());resizePane(r.width + (e.key === 'ArrowRight' ? step : e.key === 'ArrowLeft' ? -step : 0), r.height + (e.key === 'ArrowDown' ? step : e.key === 'ArrowUp' ? -step : 0));return;
      }
      if (!paneBox || !e.target.matches('[data-cmx-drag]') || ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].indexOf(e.key) < 0) return;
      e.preventDefault();const step = e.shiftKey ? 32 : 8;paneBox.x += e.key === 'ArrowRight' ? step : e.key === 'ArrowLeft' ? -step : 0;paneBox.y += e.key === 'ArrowDown' ? step : e.key === 'ArrowUp' ? -step : 0;positionPane();
    }
    function openNotes() {
      if (typeof opts.notes !== 'function') return;const note = opts.notes();if (!note || !(document.fullscreenElement === el || el.classList.contains('cmx-fs'))) return;
      if (noteElement !== note) { returnNote();noteElement = note;noteZ = note.style.zIndex || ''; }placeNote();
    }
    function placeNote() { if (!noteElement) return;if (document.fullscreenElement === el && !el.contains(noteElement)) el.appendChild(noteElement);noteElement.style.zIndex = '10001'; }
    function returnNote() {
      const note = noteElement || (typeof document.getElementById === 'function' ? document.getElementById('note') : null);
      if (note && el.contains(note)) document.body.appendChild(note);
      if (noteElement) { noteElement.style.zIndex = noteZ;noteElement = null;noteZ = ''; }
    }
    function leaveFull() {
      fsSerial++;fsWanted = false;fsPending = false;el.classList.remove('cmx-fs');returnNote();restorePane();
      if (document.fullscreenElement === el && document.exitFullscreen) { try { Promise.resolve(document.exitFullscreen()).catch(function () {}); } catch (_) {} }
      onFs();
    }
    async function fullscreen() {                         // 保留原舞台/相机，失败时固定铺满
      if (!alive) return;
      if (fsWanted || document.fullscreenElement === el || el.classList.contains('cmx-fs')) { leaveFull(); return; }
      if (!side.hidden) paneRect = side.getBoundingClientRect();
      const serial = ++fsSerial;fsWanted = true;fsPending = true;
      try { if (el.requestFullscreen) await el.requestFullscreen(); } catch (_) {}
      if (!alive || serial !== fsSerial) {
        if (!fsWanted && document.fullscreenElement === el && document.exitFullscreen) { try { await document.exitFullscreen(); } catch (_) {} }
        return;
      }
      fsPending = false;
      if (document.fullscreenElement !== el) el.classList.add('cmx-fs');
      onFs();
    }
    function onFs() {
      if (document.fullscreenElement === el) el.classList.remove('cmx-fs');
      else if (document.fullscreenElement) { fsSerial++;fsPending = false;fsWanted = false;el.classList.remove('cmx-fs'); }
      else if (!fsPending && !el.classList.contains('cmx-fs')) fsWanted = false;
      const on = document.fullscreenElement === el || el.classList.contains('cmx-fs'), b = el.querySelector('[data-act=full]');
      if (b) { b.classList.toggle('on', on); b.textContent = on ? '退出全屏' : '全屏'; }
      if (on && fsWanted && alive) { syncPane();placeNote(); }else { returnNote();restorePane(); }
      if (alive) size();
    }
    function onKeyF(e) {
      if ((e.key === 'f' || e.key === 'F') && !e.ctrlKey && !e.metaKey && !e.altKey && !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) { e.preventDefault(); fullscreen(); }
    }
    function onEscape(e) { if (e.key === 'Escape' && (fsWanted || el.classList.contains('cmx-fs') || document.fullscreenElement === el)) leaveFull(); }
    function onOverview() { setView(overviewView(overviewMode(mod))); }
    document.addEventListener('fullscreenchange', onFs);
    el.addEventListener('keydown', onKeyF);
    window.addEventListener('keydown', onEscape);window.addEventListener('research-overview-mode', onOverview);
    side.addEventListener('pointerdown', onPaneDown);side.addEventListener('keydown', onPaneKey);window.addEventListener('pointermove', onPaneMove);window.addEventListener('pointerup', onPaneUp);window.addEventListener('pointercancel', onPaneUp);

    // ---- 拿目录、摆好
    function load(keepCam) {
      if (!alive) return Promise.resolve(closedRead());
      const serial = ++loadSerial;
      let request;
      try { request = api('GET', 'api/modules/' + encodeURIComponent(mod) + '/codemap/files'); }
      catch (error) { return Promise.reject(error); }
      return Promise.resolve(request).then(function (d) {
        const inactive = inactiveRead(serial); if (inactive) return inactive;
        const old = byRel;
        now = Date.now() / 1000; git = d.git;
        files = d.files.map(function (f) {
          const o = old[f.rel];
          if (o && o.mtime === f.mtime && o.lines === f.lines && o.toks) { f.text = o.text; f.toks = o.toks; }   // 没变的留着全文
          return f;
        });
        byRel = {};
        files.forEach(function (f) { byRel[f.rel] = f; });
        map = build(files);
        flow = buildFlow(files);
        if (sel) sel = byRel[sel.rel] || null;
        memLines = files.reduce(function (a, f) { return a + (f.text ? f.text.length : 0); }, 0);
        const b = bounds();fitZ = Math.min(W / b.W, H / b.H) * 0.94;
        if (!keepCam) { cam = { x: b.W / 2, y: b.H / 2, z: fitZ }; }
        paintStat(); paintLegend(); paintSide();
        if (mode === 'diff' || keepCam) loadDiff();
        redraw();
        if (!is2d()) build3(!keepCam);
        return { ok: true, module: mod };
      });
    }
    try { const m = localStorage.getItem('tpl_cmap_mode'); if (m && MODES.some(function (x) { return x[0] === m; })) { mode = m;if (colorSelect) colorSelect.value = m; } } catch (_) {}
    if (typeof window.researchOverviewMode !== 'function') { try { const v = localStorage.getItem('tpl_cmap_shape'); if (v && VIEWS.some(function (x) { return x[0] === v; })) view = v; } catch (_) {} }
    paintViewBar();
    size();
    const firstSerial = loadSerial + 1;
    load(false).then(function (result) {
      const inactive = inactiveRead(firstSerial);
      if (inactive || !result.ok) { settleReady(inactive || result); return; }
      if (mode === 'diff') loadDiff();
      settleReady(result);
    }).catch(function (error) {
      settleReady(inactiveRead(firstSerial) || { ok: false, module: mod, status: 'error', error: String(error && error.message || error || '代码地图读取失败') });
    });

    function destroy() {
      alive = false;
      settleReady(closedRead());
      leaveFull();clearTimeout(qt);clearInterval(guard);
      document.removeEventListener('fullscreenchange', onFs); el.removeEventListener('keydown', onKeyF);
      window.removeEventListener('keydown', onEscape);window.removeEventListener('research-overview-mode', onOverview);
      side.removeEventListener('pointerdown', onPaneDown);side.removeEventListener('keydown', onPaneKey);window.removeEventListener('pointermove', onPaneMove);window.removeEventListener('pointerup', onPaneUp);window.removeEventListener('pointercancel', onPaneUp);if (colorSelect) colorSelect.removeEventListener('change', changeColor);
      if (T3) { T3.dispose(); T3 = null; }
      window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); window.removeEventListener('resize', onResize);
      themeWatch.disconnect();
      if (mq && mq.removeEventListener) mq.removeEventListener('change', onMq);
    }
    const ctl = {
      module: mod,
      ready: ready,
      alive: function () { if (alive && !document.body.contains(cv)) destroy(); return alive; },
      refresh: function () { return load(true); },
      stats: function () {
        return Object.assign({ z: cam.z, fitZ: fitZ, loaded: files.filter(function (f) { return f.toks; }).length, files: files.length, view: view,
          camera: Object.assign({}, cam), camera3: T3 ? T3.cameraState() : null, selected: sel ? sel.rel : '', dependencies: flow ? flow.edges.length : 0,
          paneSize: Object.assign({}, paneSize), paneBox: paneBox ? Object.assign({}, paneBox) : null,
          tiers: T3 && T3.tiers ? T3.tiers.map(function (t) { return t.files.length; }) : null, painted: T3 ? T3.painted : 0, frames3: T3 ? T3.frames : 0 }, stats);
      },
      _view: function (v) { setView(v); }, _top: function () { return T3 && T3.tiers ? T3.tiers[0].files.map(function (f) { return f.rel; }) : []; },
      _probe: function (rel) { const f = byRel[rel]; return f ? { u: (f.x + f.w / 2 - cam.x) * cam.z, v: (f.y + f.h / 2 - cam.y) * cam.z } : null; },   // 查验用：这个文件的中心在画布上离中心多远
      _fly: function (rel, line) { const f = byRel[rel]; if (f) { if (line) flyLine(f, line); else flyFile(f); } }, _pick: function (rel, line) { const f = byRel[rel]; if (f) pickFile(f, line); },   // 文件变了：重摆、留着镜头；改过的文件下回看到再取
      destroy: destroy
    };
    const guard = setInterval(function () { if (!document.body.contains(cv)) { destroy(); clearInterval(guard); } }, 2000);   // 换页了：自己收摊
    return ctl;
  }

  css();                                               // 样式先放上：「清单」那档的两档切换也用它
  window.CodeMap = { mount: mount, _build: build, _flow: buildFlow, _overviewView: overviewView, _clampPane: clampPane, _tokenize: tokenize };
})();
