"""验收接续：本人已领优先、自动员工等待优先、历史顺序与权限互斥。"""
import pytest

import agents
import autolaunch
import claims
import deliveries
import dispatch
import store
import workorders


@pytest.fixture
def conn(proj):
    goal = proj.root / "治理/目标/S1-1 样板.md"
    goal.parent.mkdir(parents=True)
    text = ("# S1-1 样板\n\n**样板目标。**\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
            "| S2-1 | 〔程序〕修改文件 | 内容符合验收要求 | 待验收 |\n"
            "| S2-2 | 〔网页〕修改页面 | 页面符合验收要求 | 待验收 |\n")
    goal.write_text(text, encoding="utf-8")
    (goal.parent / "S1-2 另一目标.md").write_text(text.replace("S1-1 样板", "S1-2 另一目标"), encoding="utf-8")
    c = store.connect(proj.db_path)
    for name, fields in [("old", {}), ("auto", {"auto": True}), ("paused-auto", {"auto": True, "paused": True}),
                         ("reviewer", {"roles": ["验收"], "auto": True}), ("other", {"roles": ["验收"]})]:
        agents.create(c, proj, name, **fields)
    yield c
    c.close()


def _delivery(proj, n, name="old", *, state="等验收", goal="S1-1", sub="S2-1"):
    f = proj.root / deliveries.DIR / f"J{n} {goal} {sub}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"---\n编号: J{n}\n目标: {goal}\n小目标: {sub}\n状态: {state}\n谁: agent:{name}\n---\n\n# 实际临时交付\n", encoding="utf-8")
    return deliveries.get(proj, f"J{n}")


def _claim(conn, n, name="reviewer"):
    return claims.claim(conn, "验收", f"J{n}", "agent:" + name, [f"验收 J{n}"])


def test_continues_own_pending_review_before_auto_or_older_deliveries(proj, conn):
    _delivery(proj, 1)
    _delivery(proj, 2, "auto")
    _delivery(proj, 3)
    _claim(conn, 3)
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J3"
    assert [r["sub"] for r in claims.of(conn, "agent:reviewer")] == ["J3"]


def test_own_claim_is_only_continued_while_delivery_still_waits(proj, conn):
    _delivery(proj, 1, state="验收通过")
    _claim(conn, 1)
    _delivery(proj, 2, "auto")
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J2"
    assert deliveries.get(proj, "J1")["state"] == "验收通过"


def test_other_employee_held_review_is_not_taken_or_released(proj, conn):
    _delivery(proj, 1, "auto")
    _claim(conn, 1, "other")
    before = claims.of(conn, "agent:other")
    assert dispatch.review_job(conn, proj, "agent:reviewer") is None
    assert claims.of(conn, "agent:other") == before
    _delivery(proj, 2)
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J2"
    assert claims.of(conn, "agent:other") == before


def test_active_automatic_authors_take_priority_and_keep_fifo_within_group(proj, conn):
    _delivery(proj, 1)
    _delivery(proj, 2, "paused-auto")
    _delivery(proj, 4, "auto")
    _delivery(proj, 3, "auto")
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J3"
    assert claims.of(conn, "agent:reviewer")[0]["sub"] == "J3"


def test_manual_and_paused_automatic_authors_keep_original_history_order(proj, conn):
    _delivery(proj, 4)
    _delivery(proj, 3, "paused-auto")
    _delivery(proj, 2, "unknown-old-employee")
    _delivery(proj, 1)
    agents.update(conn, proj, "reviewer", {"auto": False}, by="人")
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J1"


def test_auto_priority_never_bypasses_scope_craft_self_or_failure_filter(proj, conn):
    _delivery(proj, 1)
    _delivery(proj, 2, "auto", goal="S1-2")
    _delivery(proj, 3, "auto", sub="S2-2")
    _delivery(proj, 4, "reviewer")
    _delivery(proj, 5, "auto")
    prof = agents.update(conn, proj, "reviewer", {"scope": ["S1-1"], "crafts": ["程序"]}, by="人")
    autolaunch.write_runner_state(proj, prof["code"], "ready", blocked=["review_delivery:J5"])
    assert dispatch.review_job(conn, proj, "agent:reviewer")["code"] == "J1"
    assert [r["sub"] for r in claims.of(conn, "agent:reviewer")] == ["J1"]


@pytest.mark.parametrize("pause", ["project", "employee"])
def test_paused_review_does_not_claim(proj, conn, pause):
    _delivery(proj, 1, "auto")
    if pause == "project":
        store._set_meta(conn, workorders.PAUSE, "人叫停")
    else:
        agents.update(conn, proj, "reviewer", {"paused": True}, by="人")
    assert dispatch.review_job(conn, proj, "agent:reviewer") is None
    assert claims.of(conn, "agent:reviewer") == []
