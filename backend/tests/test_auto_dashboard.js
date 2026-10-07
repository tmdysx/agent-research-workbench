'use strict';
// Window dimensions affect only the local viewer, never the remote PTY.

// Exercise the actual exported model; no DOM, network, terminal or scheduling actions.
const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../../自动化面板.js');

test('viewer dimensions default to a larger scene and reject corrupt saved sizes', () => {
  assert.deepEqual(model.sceneSize(null, 1200), { height:640, width:420 });
  assert.deepEqual(model.sceneSize({height:NaN,width:Infinity}, 1200), { height:640, width:420 });
  const saved={height:850,width:480};
  assert.deepEqual(model.sceneSize(saved, 1200), saved);
  assert.deepEqual(saved,{height:850,width:480});
});

test('shrinking the local view retains a usable canvas and bounded reading width', () => {
  const size=model.sceneSize({height:-1,width:100000},800);
  assert.equal(size.height,440);assert.ok(size.width<=800*.65);
  assert.equal(model.sceneSize({height:100000,width:-1},800).height,1800);
  assert.equal(model.sceneSize({height:100000,width:-1},800).width,260);
});

test('floating pane clamps both axes and preserves finite geometry in ordinary and tiny viewports', () => {
  for (const v of [{ width: 1280, height: 800 }, { width: 240, height: 160 }, { width: 1, height: 1 }]) {
    const b = model.clampPane({ x: -900, y: 9999, width: 400, height: 600 }, v);
    assert.ok(Object.values(b).every(Number.isFinite));assert.ok(b.x >= 0 && b.y >= 0);assert.ok(b.x + b.width <= v.width);assert.ok(b.y + b.height <= v.height);
  }
  assert.ok(Object.values(model.clampPane({ x: NaN, y: Infinity }, {})).every(Number.isFinite));
});

const ROOT = 'C:/temporary-fixture/project-a';
const KEY = 'S1-1 S2-1';
function context() {
  return {
    online: true,
    errors: [],
    state: {
      project: { root: ROOT, name: 'Temporary project' },
      blueprint: [{ code: 'S1-1', name: 'Goal one' }, { code: 'S1-2', name: 'Goal two' }],
      module_blueprint: []
    },
    board: { items: [
      { key: KEY, goal: 'S1-1', sub: 'S2-1', who: 'agent:worker', col: '在做' },
      { key: 'S1-2 S2-1', goal: 'S1-2', sub: 'S2-1', who: 'agent:other', col: '能做' }
    ] },
    roster: [{ code: 'G1', name: 'worker' }, { code: 'G2', name: 'other' }],
    launch: {
      on: true,
      pause: '',
      status: [{ code: 'G1', status: 'running', current: { task: { goal: 'S1-1', sub: 'S2-1' } } }],
      windows: [{ id: 'w-1', title: 'Worker terminal', alive: true, agent_code: 'G1', project_root: ROOT }],
      plans: []
    },
    deliveries: []
  };
}

test('goals keeps the complete goal identity and retains a goal with zero tasks', () => {
  const result = model.goals({ blueprint: [
    { code: 'S1-1', name: 'Empty goal' }, { code: 'S1-2', name: 'Other goal' }
  ], module_blueprint: [{ code: 'module:fixture', name: 'Module goal', kind: 'module' }] },
  { items: [{ goal: 'S1-2', sub: 'S2-1' }, { goal: 'S1-3', goal_name: 'Board goal' }] });
  assert.deepEqual(result.map(goal => goal.key), ['S1-1', 'S1-2', 'module:fixture', 'S1-3']);
  assert.equal(result[0].name, 'Empty goal');
});

test('a project with no goals or tasks produces no invented goals', () => {
  assert.deepEqual(model.goals({}, { items: [] }), []);
  const ctx = context();
  ctx.state.blueprint = [];
  ctx.board.items = [];
  assert.deepEqual([...model.activity(ctx)], []);
});

test('same S2 number in different goals does not share an active node', () => {
  const ctx = context();
  assert.deepEqual([...model.activity(ctx)], [KEY]);
  assert.equal(model.activity(ctx).has('S1-2 S2-1'), false);
  assert.equal(model.taskKey({ current: { task: { goal: 'S1-2', sub: 'S2-1' } } }, ctx.launch, []), 'S1-2 S2-1');
});

test('plan and delivery references resolve through their recorded full goal and sub', () => {
  const launch = { plans: [{ code: '施-1', goal: 'S1-2', sub: 'S2-1' }] };
  const deliveries = [{ code: 'J1', goal: 'S1-3', sub: 'S2-1' }];
  assert.equal(model.taskKey({ current: { construction_plan: { code: '施-1' } } }, launch, deliveries), 'S1-2 S2-1');
  assert.equal(model.taskKey({ current: { review: 'J1' } }, launch, deliveries), 'S1-3 S2-1');
  assert.equal(model.taskKey({ current: { draft: '施-1' } }, launch, deliveries), 'S1-2 S2-1');
});

test('a bare S2, missing current record or incomplete plan never invents a goal', () => {
  for (const current of [null, 'S2-1', {}, { task: 'S2-1' }, { task: { sub: 'S2-1' } }, { task: { goal: 'S1-1' } }]) {
    assert.equal(model.taskKey({ current }, { plans: [] }, []), '');
  }
  assert.equal(model.taskKey({ current: { review: 'J1' } }, { plans: [] }, [{ code: 'J1', sub: 'S2-1' }]), '');
});

for (const [label, change] of [
  ['offline', ctx => { ctx.online = false; }],
  ['a failed data request', ctx => { ctx.errors = ['launch request failed']; }],
  ['automatic dispatch disabled', ctx => { ctx.launch.on = false; }],
  ['a human pause', ctx => { ctx.launch.pause = 'Human paused work'; }],
  ['failed runner', ctx => { ctx.launch.status[0].status = 'failed'; }],
  ['waiting runner', ctx => { ctx.launch.status[0].status = 'waiting'; }],
  ['idle runner', ctx => { ctx.launch.status[0].status = 'idle'; }],
  ['no runner records', ctx => { ctx.launch.status = []; }],
  ['no terminal windows', ctx => { ctx.launch.windows = []; }],
  ['an exited terminal', ctx => { ctx.launch.windows[0].alive = false; }],
  ['no liveness confirmation', ctx => { delete ctx.launch.windows[0].alive; }],
  ['a window for a different project', ctx => { ctx.launch.windows[0].project_root = 'C:/temporary-fixture/project-b'; }],
  ['a window for a different employee', ctx => { ctx.launch.windows[0].agent_code = 'G2'; }],
  ['a missing current task', ctx => { ctx.launch.status[0].current = null; }],
  ['a current task absent from the board', ctx => { ctx.launch.status[0].current.task.sub = 'S2-99'; }]
]) {
  test(`activity remains static for ${label}`, () => {
    const ctx = context();
    change(ctx);
    assert.deepEqual([...model.activity(ctx)], []);
  });
}

test('a running record alone cannot animate without a matching living window', () => {
  const ctx = context();
  ctx.launch.windows[0] = { id: 'w-1', title: `G1 ${ROOT} ${KEY}`, command: `worker --project ${ROOT}`, alive: true };
  assert.deepEqual([...model.activity(ctx)], []);
});

test('empty employee identifiers are not an explicit employee association', () => {
  const ctx = context();
  ctx.launch.status[0].code = '';
  ctx.launch.windows[0].agent_code = '';
  assert.deepEqual([...model.activity(ctx)], []);
});

test('missing employee identifiers are not an explicit employee association', () => {
  const ctx = context();
  delete ctx.launch.status[0].code;
  delete ctx.launch.windows[0].agent_code;
  assert.deepEqual([...model.activity(ctx)], []);
});

test('empty project paths cannot animate even when both records contain the same empty string', () => {
  const ctx = context();
  ctx.state.project.root = '';
  ctx.launch.windows[0].project_root = '';
  assert.deepEqual([...model.activity(ctx)], []);
});

test('missing project paths cannot animate even when both records omit the path', () => {
  const ctx = context();
  delete ctx.state.project.root;
  delete ctx.launch.windows[0].project_root;
  assert.deepEqual([...model.activity(ctx)], []);
});

test('missing project metadata is handled as unknown and remains static', () => {
  const ctx = context();
  delete ctx.state.project;
  assert.deepEqual([...model.activity(ctx)], []);
});

test('eligible windows use explicit employee and project metadata, not title or command text', () => {
  const ctx = context();
  ctx.launch.windows.push(
    { id: 'spoof-title', title: `worker G1 ${ROOT}`, command: `worker --project ${ROOT}`, alive: true },
    { id: 'wrong-project', title: 'worker G1', agent_code: 'G1', project_root: 'C:/temporary-fixture/project-b', alive: true },
    { id: 'wrong-worker', title: 'worker G1', agent_code: 'G2', project_root: ROOT, alive: true }
  );
  assert.deepEqual(model.eligibleWindows(ctx, ctx.board.items[0]).map(window => window.id), ['w-1']);
});

test('historical exited windows may be read as records without contributing animation', () => {
  const ctx = context();
  ctx.launch.windows[0].alive = false;
  assert.deepEqual(model.eligibleWindows(ctx, ctx.board.items[0]).map(window => window.id), ['w-1']);
  assert.deepEqual([...model.activity(ctx)], []);
});

test('an unassigned or unknown employee has no inferred task window', () => {
  const ctx = context();
  assert.deepEqual(model.eligibleWindows(ctx, null), []);
  assert.deepEqual(model.eligibleWindows(ctx, { who: '' }), []);
  assert.deepEqual(model.eligibleWindows(ctx, { who: 'agent:unknown' }), []);
  assert.deepEqual(model.eligibleWindows(ctx, { who: 'agent:G1' }).map(window => window.id), ['w-1']);
});

test('eligible windows do not treat an empty project root as a matching project', () => {
  const ctx = context();
  ctx.state.project.root = '';
  ctx.launch.windows[0].project_root = '';
  assert.deepEqual(model.eligibleWindows(ctx, ctx.board.items[0]), []);
});

test('eligible windows handle missing project metadata as an unknown association', () => {
  const ctx = context();
  delete ctx.state.project;
  assert.deepEqual(model.eligibleWindows(ctx, ctx.board.items[0]), []);
});

test('overview mode accepts only the three supported values', () => {
  for (const value of ['map', 'flow', 'model3d']) assert.equal(model.overviewMode(value), value);
  for (const value of [undefined, null, 'city', '__proto__', {}]) assert.equal(model.overviewMode(value), 'map');
});

for (const mode of ['map', 'flow', 'model3d']) test(`${mode} retains complete node identities and only goal membership edges`, () => {
  const gs = [{ key: 'S1-1', name: 'First' }, { key: 'S1-2', name: 'Empty' }];
  const tasks = [{ key: 'S1-1 S2-1', goal: 'S1-1' }, { key: 'S1-2 S2-1', goal: 'S1-2' }];
  const layout = model.overviewLayout(mode, gs, 'S1-1', tasks);
  assert.deepEqual(layout.nodes.map(n => n.id), ['project:root', 'goal:S1-1', 'goal:S1-2', 'task:S1-1 S2-1']);
  assert.deepEqual(layout.edges, [{ from: 'project:root', to: 'goal:S1-1' },
    { from: 'project:root', to: 'goal:S1-2' }, { from: 'goal:S1-1', to: 'task:S1-1 S2-1' }]);
  assert.equal(layout.edges.some(e => e.from.startsWith('task:')), false);
  assert.ok(Number.isFinite(layout.H));
  if (mode === 'model3d') {
    const heights = layout.nodes.map(n => n.world.y);
    assert.deepEqual(heights, [-210, 0, 0, 200]);
    assert.ok(layout.nodes.every(n => Object.values(n.world).every(Number.isFinite)));
  }
});

test('unknown selected goal creates no task parent or invented task relation', () => {
  const layout = model.overviewLayout('model3d', [{ key: 'S1-1' }], 'unknown', [{ key: 'unknown S2-1', goal: 'unknown' }]);
  assert.equal(layout.nodes.filter(n => n.kind === 'task').length, 0);
  assert.equal(layout.edges.length, 1);
});

test('empty ordinary projects have finite layouts without invented goals in every mode', () => {
  for (const mode of ['map', 'flow', 'model3d']) {
    const layout = model.overviewLayout(mode, [], '', []);
    assert.equal(layout.nodes.length, 1); assert.deepEqual(layout.edges, []); assert.ok(Number.isFinite(layout.H));
  }
});

test('3D projection responds to rotation and distance without nonfinite coordinates', () => {
  const point = { x: 100, y: 40, z: 80 };
  const a = model.projectPoint(point, { yaw: 0, pitch: 0, distance: 850 });
  const rotated = model.projectPoint(point, { yaw: .7, pitch: .3, distance: 850 });
  const closer = model.projectPoint(point, { yaw: 0, pitch: 0, distance: 500 });
  assert.notEqual(a.x, rotated.x); assert.notEqual(a.y, rotated.y); assert.ok(closer.scale > a.scale);
  assert.ok(Object.values(model.projectPoint({ x: Infinity, y: NaN, z: 0 }, {})).every(Number.isFinite));
});
