"""蓝图怎么看（蓝图 S2-1 大问题卡、S2-5 卡在哪、S2-6 按时间排；作者 10-01「蓝图定稿」）。"""
import os
import time

import bplook
import dispatch


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


S0 = ("# S0 终极目标\n\n**做一个试验。**\n\n## 两个大问题\n\n| 大问题 | 小问题 | 归到 |\n|---|---|---|\n"
      "| 一、会跑偏 | 没说清 | S1-1 说清 |\n| 二、接不上 | 换人 | S1-2 接上 |\n\n| S1 | 目标 |\n|---|---|\n| S1-1 说清 | 说 |\n| S1-2 接上 | 接 |\n")
HEAD = "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"


def _setup(proj):
    _w(proj.materials / "蓝图" / "S0 终极目标.md", S0)
    _w(proj.materials / "蓝图" / "S1-1 说清.md", "# S1-1 说清\n\n**说清。**\n\n规划：定稿 · 2026-10-01 · 作者：「定稿」\n\n" + HEAD
       + "| S2-1 | 甲 | 项目 需-1 | 看 | 做完（J3 默认通过） |\n| S2-2 | 乙 | 项目 需-1 | 看 | 没做 |\n| S2-3 | 丙 | 项目 需-1 | 看 | 在做 |\n| S2-4 | 丁 | 项目 需-2 | 看 | 没做 |\n")
    _w(proj.materials / "蓝图" / "S1-2 接上.md", "# S1-2 接上\n\n**接上。**\n\n" + HEAD + "| S2-1 | 戊 |  | 看 | 没做 |\n| S2-2 | 己 | 项目 需-2 | 看 | 以后 |\n")
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n"
       "| 需-1 | 说清楚 | 看得见 | 测试 | S1-1 | 源代码 |\n| 需-2 | 接得上 | 看得见 | 测试 | S1-1、S1-2 | 源代码 |\n")


def test_big_problem_cards_add_up_to_the_same_numbers_as_the_overview(proj):
    _setup(proj)
    rows = dispatch.plan_status(proj)
    cards = {c["big"]: c for c in bplook.big_cards(proj)}
    assert list(cards)[:2] == ["一、会跑偏", "二、接不上"]                    # 照 S0 表的顺序
    one = cards["一、会跑偏"]
    assert (one["blocks"], one["final"], one["done"], one["items"]) == (1, 1, 1, 4)
    for c in cards.values():                                                   # 跟自动化总览「离全自动还差什么」同一份数
        xs = [r for r in rows if r["code"] in {m["code"] for m in c["members"]}]
        assert c["items"] == sum(r["items"] for r in xs) and c["final"] == sum(bool(r["final"]) for r in xs)


def test_where_it_is_stuck_most_first_and_loose_items_last(proj):
    _setup(proj)
    s = bplook.stuck(proj)
    assert [(x["code"], len(x["left"])) for x in s] == [("需-1", 2), ("需-2", 1), ("", 1)]   # 需-1 压着两件排第一；「以后」不算
    assert s[-1]["func"] == "没写「为了」哪条需求" and s[-1]["left"][0]["goal"] == "S1-2"


def test_by_time_newest_change_first(proj):
    _setup(proj)
    old = time.time() - 86400
    os.utime(proj.materials / "蓝图" / "S1-2 接上.md", (old, old))
    tl = bplook.timeline(proj)
    assert len(tl) == 6 and tl[0]["goal"] == "S1-1" and tl[-1]["goal"] == "S1-2"     # 没进 git 的：用文件时间
    assert next(x for x in tl if x["code"] == "S2-1" and x["goal"] == "S1-1")["j"] == "J3"
