/* 世界树只读布局。角度、半径和高度仅用于显示，不表示业务依赖。
 * main::C… 为主干档；branch::枝-…::C… 为枝内果实档。
 * 时间边只表达保留下来的档之间的时间先后；缺失来源保留为幽灵点。
 */
const TAU = Math.PI * 2;
const NOW = '现在';

function angleOf(id) {
  let hash = 2166136261;
  for (let i = 0; i < id.length; i += 1) {
    hash ^= id.charCodeAt(i);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return (hash / 4294967296) * TAU;
}

function point(y, angle, radius) {
  const x = Math.cos(angle) * radius, z = Math.sin(angle) * radius;
  return { y, angle, radius, x, z, position: [x, y, z] };
}

/** 只按明确布尔检查报告结果；空检查不会变成通过。 */
export function describeChecks(record = {}) {
  const checks = record.checks;
  if (Array.isArray(checks)) {
    if (!checks.length) return { checkStatus: 'unchecked', checkLabel: '未检查' };
    if (checks.some(check => check?.ok === false)) {
      return { checkStatus: 'failed', checkLabel: '有检查未过' };
    }
    if (checks.every(check => check?.ok === true)) {
      return { checkStatus: 'passed', checkLabel: '检查全过' };
    }
    return { checkStatus: 'unverified', checkLabel: '检查结果不完整' };
  }
  // /api/timeline 只给档色，不带检查正文：保留其含义，不冒充逐条复跑。
  if (record.grade === '绿档') {
    return { checkStatus: 'recorded_passed', checkLabel: '记录为绿档' };
  }
  return { checkStatus: 'unchecked', checkLabel: '未提供检查结果' };
}

function archiveOrder(a, b) {
  const timeA = String(a.at || '').replace('T', ' ');
  const timeB = String(b.at || '').replace('T', ' ');
  if (timeA !== timeB) return timeA < timeB ? -1 : 1;
  const noA = /^C(\d+)$/.exec(a.code);
  const noB = /^C(\d+)$/.exec(b.code);
  if (noA && noB) return Number(noA[1]) - Number(noB[1]);
  return String(a.code).localeCompare(String(b.code));
}

/** 输入数组或已有 HTTP 返回的 {nodes}/{branches}，不修改输入对象。
 * 输出 position 的单位为模型世界单位，模型可按 height 缩放。
 * suppliedNow 仅说明“现在”来自接口；现在总是单独的实时端点，不是存档。
 */
export function buildTreeLayout(timeline, worldtree = []) {
  const timelineRows = Array.isArray(timeline) ? timeline : timeline?.nodes;
  const branchRows = Array.isArray(worldtree) ? worldtree : worldtree?.branches;
  if (!Array.isArray(timelineRows) || !Array.isArray(branchRows)) {
    throw new TypeError('需要 timeline.nodes 和 worldtree.branches 数组');
  }

  const nodes = [];
  const edges = [];
  const missing = [];
  const index = new Map();
  const seen = new Set();
  let suppliedNow = null;

  const archives = [];
  for (const record of timelineRows) {
    const code = String(record.code || '');
    if (code === NOW) {
      suppliedNow = record;
      continue;
    }
    if (!code || seen.has(code)) {
      missing.push({
        kind: code ? 'duplicate-checkpoint' : 'invalid-checkpoint',
        code,
        message: code ? '主干重复编号 ' + code + '，未生成第二个同号节点' : '存档记录缺少编号'
      });
      continue;
    }
    seen.add(code);
    archives.push(record);
  }
  archives.sort(archiveOrder);

  const add = node => {
    nodes.push(node);
    index.set(node.id, node);
    return node;
  };
  archives.forEach((record, i) => {
    const id = 'main::' + record.code;
    const node = add({
      ...record,
      ...point(1.45 + i * 1.05, angleOf(id), 1.15),
      ...describeChecks(record),
      id,
      kind: 'checkpoint',
      code: record.code,
      label: record.code + (record.name ? ' ' + record.name : ''),
      status: record.grade || '未标档色',
      settled: Boolean(record.settled),
      record,
      source: 'main'
    });
    if (i > 0) {
      // 这里的相邻只代表时间先后，与任务依赖、源代码继承都不同。
      edges.push({
        from: 'main::' + archives[i - 1].code,
        to: node.id,
        kind: 'time-order',
        meaning: '时间先后',
        isDependency: false
      });
    }
  });

  const nowRecord = suppliedNow || { code: NOW, name: '还没存的' };
  const nowY = archives.length ? 1.45 + archives.length * 1.05 : 2.5;
  const now = add({
    ...nowRecord,
    ...point(nowY, 0, 0),
    id: 'main::现在',
    kind: 'now',
    code: NOW,
    label: '现在 · 还没存的',
    status: '未存档',
    checkStatus: 'unchecked',
    checkLabel: '尚未存档',
    record: nowRecord,
    source: 'main',
    suppliedNow: Boolean(suppliedNow)
  });
  if (archives.length) {
    edges.push({
      from: 'main::' + archives[archives.length - 1].code,
      to: now.id,
      kind: 'time-order',
      meaning: '时间先后',
      isDependency: false
    });
  }

  const ghost = (code, branch, relation) => {
    const ref = String(code || '');
    const id = ref ? 'missing::main::' + ref : 'missing::' + branch + '::' + relation;
    missing.push({
      kind: relation === 'base' ? 'missing-base' : 'missing-merge-target',
      branch,
      code: ref,
      nodeId: id,
      message: relation === 'base'
        ? (ref ? '来源档 ' + ref + ' 当前不存在' : '分支未记录来源档')
        : (ref ? '合回档 ' + ref + ' 当前不存在' : '合并记录缺少 after')
    });
    if (index.has(id)) return index.get(id);
    return add({
      ...point(0.7, angleOf(id), 2.5),
      id,
      kind: 'missing',
      code: ref,
      label: ref ? ref + ' · 记录缺失' : '来源未记录',
      status: '缺失',
      checkStatus: 'unverified',
      checkLabel: '记录不可读',
      source: 'main',
      missing: true
    });
  };

  const branchSeen = new Set();
  const sortedBranches = branchRows.slice().sort((a, b) => String(a.code || '').localeCompare(String(b.code || '')));
  for (const record of sortedBranches) {
    const code = String(record.code || '');
    if (!code || branchSeen.has(code)) {
      missing.push({
        kind: code ? 'duplicate-branch' : 'invalid-branch',
        code,
        message: code ? '工作树重复编号 ' + code : '工作树记录缺少编号'
      });
      continue;
    }
    branchSeen.add(code);
    const baseCandidate = index.get('main::' + record.base);
    const base = baseCandidate?.kind === 'checkpoint' ? baseCandidate : ghost(record.base, code, 'base');
    const id = 'branch::' + code;
    const angle = angleOf(id);
    const branch = add({
      ...record,
      ...point(Math.max(1.7, base.y + 0.8), angle, 3.1),
      ...describeChecks(record),
      id,
      kind: 'branch',
      code,
      label: code + (record.name ? ' ' + record.name : ''),
      status: record.state || '状态未记录',
      record,
      source: code,
      baseId: base.id,
      missingBase: Boolean(base.missing)
    });
    edges.push({
      from: base.id,
      to: branch.id,
      kind: 'branch-origin',
      meaning: '从这一档长枝',
      missing: Boolean(base.missing)
    });

    if (record.fruit_checkpoint) {
      const fruitCode = String(record.fruit_checkpoint);
      const fruit = add({
        ...point(branch.y + 0.48, angle, 3.65),
        ...describeChecks(record),
        id: 'branch::' + code + '::' + fruitCode,
        kind: 'fruit',
        code: fruitCode,
        label: code + ' / ' + fruitCode,
        status: record.state === '结果了' ? '结果了' : '果实历史',
        record,
        source: code,
        branch: code
      });
      edges.push({
        from: branch.id,
        to: fruit.id,
        kind: 'fruit',
        meaning: '枝内果实档'
      });
    }

    // 只认明确的合并记录，不用名称、状态或时间猜主干落点。
    if (record.state === '合了' && !record.merged) {
      missing.push({
        kind: 'missing-merge-record',
        branch: code,
        message: '分支标为合了，但缺少合并来源记录，未连接主干落点'
      });
    }
    if (record.merged) {
      const after = record.merged.after;
      const targetCandidate = index.get('main::' + after);
      const target = targetCandidate?.kind === 'checkpoint' ? targetCandidate : ghost(after, code, 'merge');
      edges.push({
        from: branch.id,
        to: target.id,
        kind: 'merge',
        meaning: '合回这一档',
        missing: Boolean(target.missing),
        merge: record.merged
      });
    }
  }

  edges.forEach(edge => {
    edge.id = JSON.stringify([edge.kind, edge.from, edge.to]);
  });
  const bounds = {
    min: [
      Math.min(0, ...nodes.map(node => node.x)),
      0,
      Math.min(0, ...nodes.map(node => node.z))
    ],
    max: [
      Math.max(0, ...nodes.map(node => node.x)),
      Math.max(6, ...nodes.map(node => node.y + 1.2)),
      Math.max(0, ...nodes.map(node => node.z))
    ]
  };

  return {
    nodes,
    edges,
    bounds,
    warnings: missing,
    branches: nodes.filter(node => node.kind === 'branch'),
    height: Math.max(6, ...nodes.map(node => node.y + 1.2)),
    missing,
    checkpointCount: archives.length,
    branchCount: branchSeen.size,
    angleMeaning: '仅用于摆放，没有业务关系'
  };
}


/** 合并说明只读取明确的 after、fruit_checkpoint、demo，不根据同号档推断。
 * targetId 为主干档、现有缺失点或 null；null 表示只有“合了”状态，没有合并来源。
 * 回调 selection 永远指向原枝的果实，而不是主干同号 C 档。
 */
export function describeMerges(timeline, worldtree = []) {
  const timelineRows = Array.isArray(timeline) ? timeline : timeline?.nodes;
  const branchRows = Array.isArray(worldtree) ? worldtree : worldtree?.branches;
  if (!Array.isArray(timelineRows) || !Array.isArray(branchRows)) {
    throw new TypeError('需要 timeline.nodes 和 worldtree.branches 数组');
  }
  const archives = new Set(timelineRows.map(record => String(record.code || '')).filter(code => code && code !== NOW));
  const seen = new Set(), annotations = [];
  for (const record of branchRows.slice().sort((a,b) => String(a.code || '').localeCompare(String(b.code || '')))) {
    const branch = String(record.code || '');
    if (!branch || seen.has(branch)) continue;
    seen.add(branch);
    if (!record.merged && record.state !== '合了') continue;
    const after = String(record.merged?.after || '');
    const fruitCode = String(record.fruit_checkpoint || '');
    const demo = String(record.demo || '');
    const missingRecord = !record.merged;
    const missingTarget = missingRecord || !after || !archives.has(after);
    const targetId = missingRecord ? null : archives.has(after) ? 'main::' + after : after ? 'missing::main::' + after : 'missing::' + branch + '::merge';
    const id = JSON.stringify(['merge-annotation', branch, after, fruitCode]);
    const sourceId = fruitCode ? 'branch::' + branch + '::' + fruitCode : id;
    const shortDemo = demo ? Array.from(demo).slice(0,22).join('') + (Array.from(demo).length > 22 ? '…' : '') : 'Demo 未记录';
    const fruitLabel = branch + ' / ' + (fruitCode || '果实编号缺失');
    const targetLabel = missingRecord ? '合并来源记录缺失' : !after ? '合并落点缺失' : !archives.has(after) ? '合回档 ' + after + ' 缺失' : '合回 ' + after;
    const label = '合并果实 ' + fruitLabel + ' · ' + shortDemo;
    const fullLabel = '合并果实 ' + fruitLabel + ' · Demo：' + (demo || '未记录') + ' · ' + targetLabel;
    annotations.push({id, branch, after, fruitCode, demo, shortDemo, sourceId, targetId, missingTarget, missingRecord, missingFruit:!fruitCode, missingDemo:!demo, label, fullLabel, record,
      selection:{id:sourceId, kind:'fruit', code:fruitCode, branch, source:branch, record, status:record.state || '状态未记录', ...describeChecks(record), mergeTarget:after, missingFruit:!fruitCode}});
  }
  return annotations;
}

/** 显示层不画时间排序线或合并线；完整 edges 仍用于读取真实关系。 */
export function visibleTreeEdges(layout) {
  return (layout?.edges || []).filter(edge => edge.kind !== 'time-order' && edge.kind !== 'merge');
}
