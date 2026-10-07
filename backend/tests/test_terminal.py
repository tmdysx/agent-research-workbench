"""网页终端（项目 需-23；S1-11 S2-6 插件能挂一页 · S1-8 S2-47 终端后台 · S2-48 那一页）：
作者 10-02「就不能在网页端展示这个吗？」选了「网页里直接嵌终端」；「我觉得你应该自己先做那个终端镶嵌的任务，这样好监管」。"""
import asyncio
import json
import queue
import sys
import textwrap
import time

import pytest
from fastapi.testclient import TestClient

import agents
import plugins
import store
from project import CODE_DIR

sys.path.insert(0, str(CODE_DIR / "插件" / "网页终端"))
import server  # noqa: E402


class FakePty:
    """假的 PowerShell：打进去什么，就回「回声：什么」。"""

    def __init__(self):
        self.q, self.alive = queue.Queue(), True
        self.writes, self.resizes = [], []
        self.q.put("PS> ")

    def read(self, n):
        try:
            return self.q.get(timeout=0.05)
        except queue.Empty:
            return ""

    def write(self, s):
        self.writes.append(s)
        self.q.put("回声：" + s)

    def isalive(self):
        return self.alive

    def setwinsize(self, rows, cols):
        self.resizes.append((rows, cols))
        self.size = (rows, cols)

    def terminate(self, force=False):
        self.alive = False


def _wait(fn, limit=3.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        v = fn()
        if v:
            return v
        time.sleep(0.05)
    return fn()


def test_windows_keep_their_own_output_and_need_the_token(tmp_path):
    app = server.create("令牌", 8790, str(tmp_path), spawn=lambda argv, **k: FakePty())
    with TestClient(app) as c:
        assert c.get("/ping").status_code == 403 and c.get("/", params={"t": "错的"}).status_code == 403
        assert c.get("/ping", params={"t": "令牌"}).json()["app"] == "网页终端"
        a = c.post("/api/terms", params={"t": "令牌"}, json={"title": "G5 sonnet", "cmd": "开工A"}).json()
        b = c.post("/api/terms", params={"t": "令牌"}, json={"title": "空的"}).json()
        assert [x["title"] for x in c.get("/api/terms", params={"t": "令牌"}).json()["items"]] == ["G5 sonnet", "空的"]
        head = {"origin": "http://127.0.0.1:8790"}
        with c.websocket_connect(f"/ws/{a['id']}?t=令牌", headers=head) as ws:
            first = ws.receive_text()
            got = first + ("" if "开工A" in first else ws.receive_text())
            assert "开工A" in got                           # 开工的话打进去了
            ws.send_json({"i": "dir\r"})
            assert "dir" in _wait(lambda: ws.receive_text())
            ws.send_json({"r": [100, 40]})
        with c.websocket_connect(f"/ws/{b['id']}?t=令牌", headers=head) as ws:
            assert "开工A" not in ws.receive_text()         # 两个窗口不串
        with c.websocket_connect(f"/ws/{a['id']}?t=令牌", headers=head) as ws:
            assert "dir" in ws.receive_text()               # 断了再连：之前的输出还在
        for bad in ({"origin": "http://evil.example"}, None):
            url = f"/ws/{a['id']}?t=令牌" if bad else f"/ws/{a['id']}?t=错的"
            with pytest.raises(Exception):                  # 别的网站、没令牌：连不上
                with c.websocket_connect(url, headers=bad or head) as ws:
                    ws.receive_text()
        assert c.post(f"/api/terms/{b['id']}/close", params={"t": "令牌"}).json() == {"ok": True}
        assert len(c.get("/api/terms", params={"t": "令牌"}).json()["items"]) == 1


def test_a_real_powershell_window(tmp_path):
    pytest.importorskip("winpty")
    import asyncio
    loop = asyncio.new_event_loop()
    t = server.Term("真的", str(tmp_path), "Write-Output ('he' + 'llo')", loop)
    try:
        def seen():
            loop.run_until_complete(asyncio.sleep(0.1))
            return "hello" in t.history()
        assert _wait(seen, 20)
    finally:
        t.close()
        loop.close()


def test_a_plugin_can_hang_a_page_and_outlive_the_core(proj, tmp_path):
    d = tmp_path / "插件"
    (d / "小页").mkdir(parents=True)
    (d / "小页" / "插件.md").write_text("---\n名字: 小页\n一句话: 试\n页面: 小页\n启动: {python} serve.py {端口} {令牌}\n端口: 18790\n---\n", encoding="utf-8")
    (d / "小页" / "serve.py").write_text(textwrap.dedent('''
        import http.server, os, sys, threading
        port, token = int(sys.argv[1]), sys.argv[2]
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                ok = self.path == "/ping?t=" + token
                self.send_response(200 if ok else 403); self.end_headers(); self.wfile.write(b"{}")
            def do_POST(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
                threading.Timer(0.2, lambda: os._exit(0)).start()
            def log_message(self, *a): pass
        http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
    '''), encoding="utf-8")
    c = store.connect(proj.db_path)
    store.migrate(c)
    assert [x["name"] for x in plugins.pages(d)] == ["小页"]
    with pytest.raises(RuntimeError, match="还没启用"):
        plugins.open_page(c, proj, "小页", d)              # 只有人点「启用」了才开
    plugins.set_enabled(c, "小页", True, d)
    try:
        o = plugins.open_page(c, proj, "小页", d)
        assert o["running"] and o["url"].startswith("http://127.0.0.1:") and "?t=" in o["url"]
        again = plugins.open_page(c, proj, "小页", d)    # 在跑就接上，不另起
        assert again["url"] == o["url"]
        assert plugins.page_status(proj, "小页", d)["running"]
    finally:
        plugins.close_page(proj, "小页", d)
    assert _wait(lambda: not plugins.page_status(proj, "小页", d)["running"])
    c.close()


def test_start_scripts_follow_the_profile(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    agents.create(c, proj, "sonnet", "写代码的", by="人", program="Claude Code（Sonnet 5.5）")
    agents.create(c, proj, "codex", "写代码的", by="人", program="Codex（gpt-6-astra）")
    agents.create(c, proj, "怪的", "空白", by="人", program="某某工具")
    s = agents.launcher(proj, "sonnet")
    text = (proj.index_dir / "开工" / s["path"].split("/")[-1]).read_text(encoding="utf-8-sig")
    assert "& 'claude' '--model' 'sonnet' '--permission-mode' 'auto'" in text and "你叫 sonnet" in text and "模型 Sonnet 5.5" in text
    assert s["cmd"].startswith("& '") and s["title"].endswith("sonnet")
    x = agents.launcher(proj, "codex")
    text = (proj.index_dir / "开工" / x["path"].split("/")[-1]).read_text(encoding="utf-8-sig")
    assert "employee_runner.py" in text and "'--agent' 'codex'" in text and x["model"] == "gpt-6-astra" and "Start-Sleep" not in text
    with pytest.raises(store.Refused, match="认不出是哪家"):
        agents.launcher(proj, "怪的")
    c.close()


def test_auto_start_opens_windows_for_agents_holding_work(proj, monkeypatch):
    """全自动开工（S1-8 S2-50；作者 10-02「自动化就是要全自动，不需要我点，你全权授权」）。"""
    import autolaunch
    import claims
    import dispatch
    c = store.connect(proj.db_path)
    store.migrate(c)
    agents.create(c, proj, "claude-code", "规划的", by="人", program="Claude Code（Opus 5.5）", auto=True)  # Claude 本轮不自动运行
    agents.create(c, proj, "sonnet", "写代码的", by="人", program="Codex（gpt-6-astra）", auto=True)        # 旧员工交给 Codex
    agents.create(c, proj, "codex", "写代码的", by="人", program="Codex（gpt-6-astra）", auto=True)
    agents.create(c, proj, "astra#2", "写代码的", by="人", program="Codex（gpt-6-astra）", auto=True)
    agents.create(c, proj, "闲着的", "写代码的", by="人", program="Codex（gpt-6-astra）", auto=True)
    for who, sub in (("claude-code", "S2-1"), ("sonnet", "S2-2"), ("codex", "S2-3"), ("astra#2", "S2-4")):
        claims.claim(c, "S1-8", sub, who, [f"S1-8 {sub}"])

    def next_job(conn, p, who):
        row = next((r for r in claims.active(conn) if agents.short(r["agent"]) == agents.short(who)), None)
        return {"action": "execute", "task": {"goal": row["goal"], "sub": row["sub"]}} if row else {"action": "idle", "task": None}

    monkeypatch.setattr(dispatch, "next_task", next_job)
    wins, posted = [{"title": "G3 codex", "alive": True}], []
    posted_metadata = []

    def call(m, path, body=None):
        if m == "POST":
            posted.append(body["title"])
            posted_metadata.append(body)
            wins.append({"title": body["title"], "alive": True})
            return {"id": "x"}
        return {"items": list(wins)}
    assert autolaunch.tick(c, proj, now=1000, call=call) == []                  # 开关关着：不开
    autolaunch.set_settings(c, on=True, max_=3)
    got = autolaunch.tick(c, proj, now=1000, call=call)
    assert posted == ["G2 sonnet", "G4 astra#2"] and got[0] == "G2 sonnet：S1-8 S2-2"   # Claude 不开、已有窗口的不重开、无待办的不开
    assert [(w['agent_code'], w['task_key'], w['project_root']) for w in posted_metadata] == [
        ('G2', 'S1-8 S2-2', str(proj.root.resolve())), ('G4', 'S1-8 S2-4', str(proj.root.resolve()))]
    assert autolaunch.tick(c, proj, now=1100, call=call) == []                  # 都有窗口了
    wins[:] = [w for w in wins if w["title"] != "G2 sonnet"]                   # sonnet 的窗口关了
    assert autolaunch.tick(c, proj, now=1300, call=call) == []                  # 10 分钟内不重开
    assert autolaunch.tick(c, proj, now=1700, call=call) == ["G2 sonnet：S1-8 S2-2"]
    autolaunch.set_settings(c, max_=1)
    wins[:] = [{"title": "G3 codex", "alive": True}]
    assert autolaunch.tick(c, proj, now=9999, call=call) == []                  # 满了（已经开着 1 个）不再开
    assert [r["who"] for r in autolaunch.recent(c)][:1] == ["G2"]
    with pytest.raises(store.Refused):
        autolaunch.set_settings(c, max_=50)
    c.close()


def _frame(ws, kind):
    for _ in range(30):
        frame = ws.receive_json()
        if frame.get('type') == kind:
            return frame
    raise AssertionError('没有收到 ' + kind)


def test_watch_rejects_input_and_resize_but_keeps_live_output(tmp_path):
    processes = []
    def spawn(*a, **k):
        pty = FakePty()
        processes.append(pty)
        return pty
    app = server.create('token', 8790, str(tmp_path), spawn=spawn)
    with TestClient(app) as c:
        ping = c.get('/ping?t=token').json()
        assert ping['protocol'] == 2 and ping['capabilities']['watch']
        info = c.post('/api/terms?t=token', json={'title':'G99 旧标题不代表关联'}).json()
        assert info['agent_code'] == info['task_key'] == ''
        assert (info['cols'], info['rows']) == (120,30)
        head = {'origin':'http://127.0.0.1:8790'}
        with c.websocket_connect(f"/ws/{info['id']}?t=token&view=1&v=2", headers=head) as watch:
            history = _frame(watch,'history')
            assert (history['cols'],history['rows']) == (120,30)
            watch.send_json({'i':'SHOULD-NOT-RUN\r'})
            assert _frame(watch,'denied')['operation'] == 'input'
            watch.send_json({'r':[35,9]})
            assert _frame(watch,'denied')['operation'] == 'resize'
            assert processes[0].writes == processes[0].resizes == []
            with c.websocket_connect(f"/ws/{info['id']}?t=token&v=2",headers=head) as control:
                _frame(control,'history')
                control.send_json({'r':[100,40]})
                assert _frame(watch,'size') == {'type':'size','cols':100,'rows':40}
                control.send_json({'i':'REAL-CONTROL\r'})
                output = _frame(watch,'output')
                assert 'REAL-CONTROL' in output['data'] and output['seq'] > history['seq']
                control.send_json({'r':['bad',0]})
                control.send_json({'type':'ping'})
                _frame(control,'pong')
            assert processes[0].resizes == [(40,100)]
            assert processes[0].writes == ['REAL-CONTROL\r']
        with c.websocket_connect(f"/ws/{info['id']}?t=token&view=1&v=2",headers=head) as again:
            replay = _frame(again,'history')
            assert replay['data'].count('REAL-CONTROL') == 1
            assert (replay['cols'],replay['rows']) == (100,40)
        assert c.get('/api/terms?t=token').json()['items'][0]['cols'] == 100


def test_window_metadata_is_explicit_and_project_scoped(tmp_path):
    processes = []
    def spawn(*a, **k):
        processes.append(FakePty())
        return processes[-1]
    app = server.create('token',8790,str(tmp_path),spawn=spawn)
    with TestClient(app) as c:
        body = {'title':'可自定义标题','agent_code':'G7','task_key':'S1-8 S2-50','project_root':str(tmp_path)}
        info = c.post('/api/terms?t=token',json=body).json()
        assert {k:info[k] for k in ('agent_code','task_key','project_root')} == {
            'agent_code':'G7','task_key':'S1-8 S2-50','project_root':str(tmp_path.resolve())}
        assert c.get('/api/terms?t=token').json()['items'] == [info]
        assert c.post('/api/terms?t=token',json=body | {'project_root':str(tmp_path / 'other')}).status_code == 403
        for bad in ({'agent_code':'not-an-agent'},{'task_key':'S1-8\nS2-50'},{'project_root':'bad\x00path'}):
            assert c.post('/api/terms?t=token',json=body | bad).status_code == 422
        assert len(processes) == 1


def test_history_and_output_are_serial_even_when_history_send_is_slow(tmp_path):
    class SilentPty(FakePty):
        def __init__(self):
            super().__init__()
            self.q.get_nowait()
    class SlowSocket:
        def __init__(self):
            self.entered, self.release = asyncio.Event(), asyncio.Event()
            self.messages = []
        async def send_text(self, data):
            if not self.messages:
                self.entered.set()
                await self.release.wait()
            self.messages.append(json.loads(data))
        async def close(self, code=1000):
            pass
    async def scenario():
        t = server.Term('fake',str(tmp_path),'',asyncio.get_running_loop(),spawn=lambda *a,**k:SilentPty())
        links = []
        try:
            t._push('before')
            socket = SlowSocket()
            links.append(t.attach(socket,structured=True))
            await asyncio.wait_for(socket.entered.wait(),1)
            t._push('during-1')
            t._push('during-2')
            socket.release.set()
            for _ in range(20):
                if len(socket.messages) == 3: break
                await asyncio.sleep(.01)
            assert [m['data'] for m in socket.messages] == ['before','during-1','during-2']
            assert [m['seq'] for m in socket.messages] == [1,2,3]
            second = SlowSocket()
            second.release.set()
            links.append(t.attach(second,structured=True))
            t._push('after')
            for _ in range(20):
                if len(second.messages) == 2: break
                await asyncio.sleep(.01)
            assert [m['type'] for m in second.messages] == ['history','output']
            assert second.messages[0]['data'] == 'beforeduring-1during-2'
            assert second.messages[1]['data'] == 'after'
        finally:
            t.close()
            for link in links:
                link.sender.cancel()
                try: await link.sender
                except asyncio.CancelledError: pass
    asyncio.run(scenario())


def test_launcher_metadata_does_not_claim_or_guess_multiple_tasks(proj):
    import autolaunch
    import claims
    c = store.connect(proj.db_path)
    store.migrate(c)
    try:
        a = agents.create(c,proj,'window-worker','施工',by='人',program='Codex')
        who = agents.actor(a['name'])
        empty = autolaunch.window_metadata(c,proj,a)
        assert empty['agent_code'] == a['code'] and empty['task_key'] == ''
        assert claims.of(c,who) == []
        claims.claim(c,'S1-8','S2-50',a['name'],['one'])  # 旧认领曾直接保存名字，仍属这名明确员工
        assert autolaunch.window_metadata(c,proj,a)['task_key'] == 'S1-8 S2-50'
        claims.claim(c,'S1-1','S2-30',who,['two'])
        assert autolaunch.window_metadata(c,proj,a)['task_key'] == ''
        got = {'construction_plan':{'goal':'S1-1','sub':'S2-30','code':'施-1'}}
        assert autolaunch.window_metadata(c,proj,a,got)['task_key'] == 'S1-1 S2-30'
        assert len(claims.active(c)) == 2
    finally:
        c.close()


def test_mcp_manual_window_passes_same_explicit_metadata(proj,monkeypatch):
    import autolaunch
    import automation_mcp
    import claims
    c = store.connect(proj.db_path)
    store.migrate(c)
    boss = agents.create(c,proj,'window-boss','统筹',by='人',program='Codex')
    worker = agents.create(c,proj,'window-worker','施工',by='人',program='Codex')
    claims.claim(c,'S1-8','S2-50',agents.actor(worker['name']),['module'])
    f = proj.root/'治理/计划/S0 总体/P1 · 授权.md'
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text('> 授权：作者本次明确批准开窗\n> 授权操作者：window-boss\n> 授权对象：' + worker['code'] + '\n',encoding='utf-8')
    rel = f.relative_to(proj.root).as_posix()
    class Registry:
        def __init__(self): self.tools = {}
        def tool(self):
            def add(fn): self.tools[fn.__name__] = fn; return fn
            return add
    registry, posted = Registry(), []
    monkeypatch.setattr(plugins,'open_page',lambda *a,**k:None)
    monkeypatch.setattr(autolaunch,'windows',lambda *a,**k:[])
    monkeypatch.setattr(agents,'launcher',lambda *a,**k:{'cmd':'inert script'})
    def send(p,method,path,body): posted.append(body); return body | {'id':'abcd1234'}
    monkeypatch.setattr(autolaunch,'_call',send)
    automation_mcp.attach(registry,proj,lambda:store.connect(proj.db_path),lambda ctx,agent:agents.actor(boss['name']),configuration_authorization=rel)
    out = json.loads(registry.tools['open_employee_window'](worker['code'],rel))
    assert out['agent_code'] == worker['code'] and out['task_key'] == 'S1-8 S2-50'
    assert out['project_root'] == str(proj.root.resolve()) and len(posted) == 1
    assert out['cmd'] == 'inert script'
    c.close()
