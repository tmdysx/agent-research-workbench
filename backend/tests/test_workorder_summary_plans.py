"""Request-local plan reuse preserves full readiness and fresh subsequent reads."""
import copy

import pytest

import governance
import readiness
import store
import workorders
from test_autopilot import _setup


def _orders(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    conn = store.connect(proj.db_path)
    for n in range(3):
        wo = workorders.create(conn, proj, f"模拟开工单 {n}", ["S1-1"])
        if n == 1:
            wo["materials"] = ["资料/文献/缺少的材料.md"]
            workorders._write(proj, wo)
        if n == 2:
            wo["stored"] = "搁置"
            workorders._write(proj, wo)
    return conn


def _legacy_summary(conn, proj):
    rows = []
    for wo in workorders.list_all(proj):
        panel = readiness.panel(conn, proj, wo)
        lamp = max((d["lamp"] for d in panel["devices"]),
                   key=lambda value: readiness._RANK[value], default="ok")
        rows.append({"code": wo["code"], "name": wo["name"],
                     "state": workorders.state(proj, wo), "lamp": lamp,
                     "green": panel["green"], "total": panel["total"], "ready": panel["ready"]})
    running = workorders.running(proj)
    return {"items": rows, "running": running["code"] if running else None}


def test_summary_same_rows_with_one_plan_scan(proj, monkeypatch, tmp_path):
    conn = _orders(proj, monkeypatch, tmp_path)
    original = governance.plan_records
    calls = []
    def scan(project):
        calls.append(project.root)
        return original(project)
    monkeypatch.setattr(governance, "plan_records", scan)
    try:
        expected = _legacy_summary(conn, proj)
        assert len(calls) == 3
        calls.clear()
        assert workorders.summary(conn, proj) == expected
        assert calls == [proj.root]
    finally:
        conn.close()


def test_panel_keeps_full_result_and_empty_snapshot(proj, monkeypatch, tmp_path):
    conn = _orders(proj, monkeypatch, tmp_path)
    try:
        wo = workorders.list_all(proj)[0]
        records = [{"code": "P1", "goals": ["S1-1"], "modules": []},
                   {"code": "P2", "goals": ["S1-99"], "modules": []}]
        monkeypatch.setattr(governance, "plan_records", lambda project: copy.deepcopy(records))
        direct = readiness.panel(conn, proj, wo)
        assert direct == readiness.panel(conn, proj, wo, all_plans=copy.deepcopy(records))
        def unexpected(project):
            pytest.fail("explicit empty snapshot must not rescan")
        monkeypatch.setattr(governance, "plan_records", unexpected)
        empty = readiness.panel(conn, proj, wo, all_plans=[])
        assert empty["plans"] == []
        assert {k: v for k, v in empty.items() if k != "plans"} == {
            k: v for k, v in direct.items() if k != "plans"}
    finally:
        conn.close()


def test_next_summary_and_detail_read_fresh_plans(proj, monkeypatch, tmp_path):
    conn = _orders(proj, monkeypatch, tmp_path)
    current = [{"code": "P1", "goals": ["S1-1"], "modules": []}]
    scanned, supplied = [], []
    original_panel = readiness.panel
    def scan(project):
        scanned.append(project.root)
        return copy.deepcopy(current)
    def panel(connection, project, wo, **kwargs):
        result = original_panel(connection, project, wo, **kwargs)
        supplied.append(copy.deepcopy(result["plans"]))
        return result
    monkeypatch.setattr(governance, "plan_records", scan)
    monkeypatch.setattr(readiness, "panel", panel)
    try:
        workorders.summary(conn, proj)
        assert len(scanned) == 1 and all(p[0]["code"] == "P1" for p in supplied)
        current[0]["code"] = "P2"
        supplied.clear()
        workorders.summary(conn, proj)
        assert len(scanned) == 2 and all(p[0]["code"] == "P2" for p in supplied)
        current[0]["code"] = "P3"
        assert workorders.detail(conn, proj, "K1")["panel"]["plans"][0]["code"] == "P3"
        assert len(scanned) == 3
    finally:
        conn.close()


def test_empty_summary_skips_scan_and_scan_errors_are_not_hidden(proj, monkeypatch):
    conn = store.connect(proj.db_path)
    def fail(project):
        raise ValueError("synthetic plan parsing failure")
    monkeypatch.setattr(governance, "plan_records", fail)
    try:
        assert workorders.summary(conn, proj) == {"items": [], "running": None}
        monkeypatch.setattr(workorders, "list_all", lambda project: [{"code": "K1"}])
        with pytest.raises(ValueError, match="synthetic plan parsing failure"):
            workorders.summary(conn, proj)
    finally:
        conn.close()
