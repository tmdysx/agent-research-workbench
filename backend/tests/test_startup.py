"""首次打开必须等本项目真正能接HTTP；测试只用临时项目，不开用户的浏览器。"""
import asyncio
import json
import sys
import threading
from contextlib import asynccontextmanager

import pytest
import uvicorn
from fastapi.testclient import TestClient

import main


def test_slow_new_project_is_ready_on_first_browser_open(proj, monkeypatch):
    release = threading.Event()
    opened = threading.Event()
    stop = threading.Event()
    observations = []
    errors = []
    app = main.create_app(proj, global_keys=False, tasks=False)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def slow_start(application):
        await asyncio.to_thread(release.wait)
        async with original(application):
            yield

    app.router.lifespan_context = slow_start
    sock = main._bind(0)
    port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", timeout_graceful_shutdown=1))
    serving = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)

    def browser(address):
        try:
            with main._NO_PROXY.open(address + "api/ping", timeout=2) as response:
                ping = json.load(response)
            with main._NO_PROXY.open(address + "api/state", timeout=2) as response:
                state = json.load(response)
            with main._NO_PROXY.open(address, timeout=2) as response:
                page_status = response.status
            observations.append((address, ping, state, page_status))
        except Exception as error:
            errors.append(error)
        finally:
            opened.set()
        return True

    monkeypatch.setattr(main.webbrowser, "open", browser)
    waiting = threading.Thread(target=main._open_browser_when_ready,
                               args=(port, proj, stop), kwargs={"timeout": 15}, daemon=True)
    try:
        serving.start()
        waiting.start()
        assert not opened.wait(2.2), "超过旧计时的两秒，后台未就绪时仍不能打开网页"
        release.set()
        assert opened.wait(15), "项目就绪后应自动打开，无需刷新"
        waiting.join(2)
        assert not waiting.is_alive()
        assert not errors
        assert len(observations) == 1
        address, ping, state, page_status = observations[0]
        assert address == url
        assert ping["app"] == main.APP_ID and ping["root"] == str(proj.root)
        assert state["project"]["root"] == str(proj.root)
        assert isinstance(state["modules"], list) and state["modules"]
        assert page_status == 200
    finally:
        stop.set()
        release.set()
        server.should_exit = True
        waiting.join(3)
        serving.join(5)
        sock.close()
    assert not serving.is_alive()


@pytest.mark.parametrize("identity", [
    {"app": "other-app", "root": "same"},
    {"app": main.APP_ID, "root": "other-project"},
])
def test_other_application_or_project_does_not_open(proj, monkeypatch, capsys, identity):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            data = dict(identity)
            if data["root"] == "same":
                data["root"] = str(proj.root)
            return json.dumps(data).encode()

    monkeypatch.setattr(main._NO_PROXY, "open", lambda *args, **kwargs: Response())
    monkeypatch.setattr(main.webbrowser, "open", lambda *_: pytest.fail("不能打开别的服务"))
    assert not main._open_browser_when_ready(8770, proj, threading.Event(), timeout=0)
    assert "后台尚未就绪" in capsys.readouterr().err


def test_wait_is_cancelled_even_when_ping_finishes_successfully(proj, monkeypatch):
    stop = threading.Event()

    def ping(*_):
        stop.set()
        return True

    monkeypatch.setattr(main, "_already_running", ping)
    monkeypatch.setattr(main.webbrowser, "open", lambda *_: pytest.fail("退出后不能打开网页"))
    assert not main._open_browser_when_ready(8770, proj, stop)


def test_timeout_does_not_open_and_reports_the_url(proj, monkeypatch, capsys):
    monkeypatch.setattr(main, "_already_running", lambda *_: False)
    monkeypatch.setattr(main.webbrowser, "open", lambda *_: pytest.fail("超时不能假装就绪"))
    assert not main._open_browser_when_ready(8782, proj, threading.Event(), timeout=0)
    message = capsys.readouterr().err
    assert "http://127.0.0.1:8782/" in message and "启动错误或初始化进度" in message


@pytest.mark.parametrize("reload", [True, False])
@pytest.mark.parametrize("no_browser", [True, False])
@pytest.mark.parametrize("failure", [True, False])
def test_main_startup_modes_share_readiness_and_cancel_on_exit(proj, monkeypatch, reload, no_browser, failure):
    waits = []
    stops = []
    runs = []
    args = ["main.py", "--project", str(proj.root)]
    if not reload:
        args.append("--no-reload")
    if no_browser:
        args.append("--no-browser")
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(main, "_running_port", lambda *_: None)
    monkeypatch.setattr(main, "_no_quick_edit", lambda: None)
    monkeypatch.setattr(main.webbrowser, "open", lambda *_: pytest.fail("必须通过就绪检查"))

    class Socket:
        def getsockname(self):
            return ("127.0.0.1", 8784)

        def close(self):
            pass

    monkeypatch.setattr(main, "_bind", lambda *_: Socket())

    def start(port, project, *, url=None):
        waits.append((port, project, url))
        stop = threading.Event()
        stops.append(stop)
        return stop

    monkeypatch.setattr(main, "_start_browser_when_ready", start)

    def run(*args, **kwargs):
        runs.append(True)
        assert len(waits) == (0 if no_browser else 1)
        assert not stops or not stops[0].is_set()
        if failure:
            raise RuntimeError("测试启动失败")

    def create(project, **kwargs):
        assert not kwargs.get("open_url"), "lifespan不能再另开一个浏览器计时器"
        return object()

    monkeypatch.setattr(main, "create_app", create)
    monkeypatch.setattr(main, "_supervise", run)
    monkeypatch.setattr(main.uvicorn, "Config", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.uvicorn, "Server", lambda *_: type("Runner", (), {"run": staticmethod(run)})())
    if failure:
        with pytest.raises(RuntimeError, match="测试启动失败"):
            main.main()
    else:
        main.main()
    assert len(runs) == 1
    assert all(stop.is_set() for stop in stops)
    assert not main._server_file(proj).exists()


def test_existing_project_opens_directly_without_new_wait(proj, monkeypatch):
    opened = []
    monkeypatch.setattr(sys, "argv", ["main.py", "--project", str(proj.root)])
    monkeypatch.setattr(main, "_no_quick_edit", lambda: None)
    monkeypatch.setattr(main, "_running_port", lambda *_: 8788)
    monkeypatch.setattr(main.webbrowser, "open", opened.append)
    monkeypatch.setattr(main, "_start_browser_when_ready", lambda *_: pytest.fail("已有服务无需再启动"))
    main.main()
    assert opened == ["http://127.0.0.1:8788/"]


def test_standalone_lifespan_browser_wait_is_cancelled(proj, monkeypatch):
    calls = []
    stop = threading.Event()

    def start(port, project, *, url=None):
        calls.append((port, project, url))
        return stop

    monkeypatch.setattr(main, "_start_browser_when_ready", start)
    app = main.create_app(proj, open_url="http://127.0.0.1:8790/", global_keys=False, tasks=False)
    with TestClient(app) as client:
        assert client.get("/api/ping").status_code == 200
        assert calls == [(8790, proj, "http://127.0.0.1:8790/")]
        assert not stop.is_set()
    assert stop.is_set()


def test_failed_hotkey_startup_never_leaves_a_browser_wait(proj, monkeypatch):
    cleaned = []

    class Hotkeys:
        def __init__(self, callback):
            pass

        def apply(self, settings):
            raise RuntimeError("测试快捷键初始化失败")

        def stop(self):
            cleaned.append(True)

    monkeypatch.setattr(main.capture, "available", lambda: True)
    monkeypatch.setattr(main.hotkeys, "Hotkeys", Hotkeys)
    monkeypatch.setattr(main, "_start_browser_when_ready",
                        lambda *args, **kwargs: pytest.fail("初始化失败不能开始等待浏览器"))
    app = main.create_app(proj, open_url="http://127.0.0.1:8790/", global_keys=True, tasks=False)
    with pytest.raises(RuntimeError, match="测试快捷键初始化失败"):
        with TestClient(app):
            pass
    assert cleaned == [True]
