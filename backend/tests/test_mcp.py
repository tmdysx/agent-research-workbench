"""真起一个 MCP 进程，按标准协议调它——跟 Claude Code 调的是同一条路。"""
import sys
import shutil

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

import store
from conftest import BACKEND


async def _call(proj, calls, backend=BACKEND):
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(backend / "mcp_server.py"), "--project", str(proj.root)],
    )
    out = []
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w, client_info=Implementation(name="test-agent", version="0")) as s:
            await s.initialize()
            tools = {t.name for t in (await s.list_tools()).tools}
            assert tools == {"get_builtin_files", "get_governance", "migrate_governance", "read_governance_document", "write_governance_document", "get_overview", "add_module", "ask_human", "read_notes", "list_inbox", "suggest_sorting", "sort_inbox_item", "move_to_inbox", "list_tools", "list_tool_guides", "read_tool_guide",
                             "find_answer", "record_answer", "add_log", "read_log", "list_skills", "read_skill", "report_run", "review_delivery", "review_draft", "start_work", "next_task", "claim_task", "release_task", "who_is_working", "register_agent", "my_profile", "list_agents",
                             "move_to_trash", "restore_from_trash", "save_checkpoint", "list_checkpoints", "restore_checkpoint",
                             "world_tree", "grow_branch", "assign_to_branch", "bear_fruit", "branch_changes", "merge_branch", "cut_branch", "reject_fruit", "pick_fruit", "digest_material", "write_digest", "propose_rewrite", "review_rewrite",
                             "propose_tool", "propose_draft", "list_plugins", "list_repos", "read_repo", "read_repo_file", "write_repo_notes", "mark_goal", "deliver", "add_idea", "suggest_requirement", "add_download", "answer_person", "record_acceptance",
                             "configure_agent", "configure_automation", "open_employee_window", "next_action", "submit_execution_plan", "get_execution_plan", "review_execution_plan", "write_handover", "report_employee_runtime", "reassign_employee_work", "assign_employee_task",
                             "list_workflow_graphs", "read_workflow_graph", "validate_workflow_graph", "dry_run_workflow_graph", "save_workflow_graph", "configure_workflow_graph", "list_skill_catalog", "read_skill_entry", "get_work_package",
                             "get_content_workspace", "read_content_document", "write_content_document"}
            for name, args in calls:
                res = await s.call_tool(name, args)
                out.append(res.content[0].text)
    return out


def test_agent_writes_through_mcp(proj):
    add, again, ask, overview = anyio.run(_call, proj, [
        ("add_module", {"name": "技能地图", "one_line": "ARIS 技能依赖图", "en": "Skill Map"}),
        ("add_module", {"name": "技能地图"}),
        ("ask_human", {"question": "技能地图放 lane ② 还是 lane ③？"}),
        ("get_overview", {}),
    ])
    assert "资料/技能地图/" in add and "agent:test-agent" in add
    assert "没有重复加" in again
    assert "D-01" in ask
    assert "技能地图 Skill Map" in overview and "D-01" in overview and "蓝图" in overview
    assert (proj.materials / "技能地图").is_dir()
    assert not (proj.materials / "技能地图/内置").exists()          # 10-07 起新模块不再补 内置/
    c = store.connect(proj.db_path)
    m = store.find_module(c, "技能地图")
    assert (m["created_by"], m["source"], m["en"]) == ("agent:test-agent", "agent", "Skill Map")
    c.close()


def test_agent_reads_human_notes(proj):
    c = store.connect(proj.db_path)
    store.save_draft(c, "第二条清理候选留着")
    store.export_instruction(c, "# 给 agent 的指令\n把第一条挪进回收站")
    c.close()
    (notes,) = anyio.run(_call, proj, [("read_notes", {})])
    assert "第二条清理候选留着" in notes and "把第一条挪进回收站" in notes


def test_agent_looks_up_before_asking(proj):
    """人拍过板的事不许再问：先查；查到就自动答上记一条 Q；查不到才转给人。流水账不进笔记。"""
    c = store.connect(proj.db_path)
    q = store.ask_human(c, "论文图用 PNG 还是 PDF 格式导出？", by="agent:x")
    store.answer(c, q["code"], "论文图一律导出 PDF，矢量不糊")
    c.close()
    blocked, found, rec, asked = anyio.run(_call, proj, [
        ("ask_human", {"question": "论文图导出用 PDF 还是 PNG？"}),
        ("find_answer", {"question": "论文图导出用 PDF 还是 PNG？"}),
        ("record_answer", {"question": "论文图导出用 PDF 还是 PNG？", "answer": "导出 PDF", "used": "决定 A-01", "run": "W1-1"}),
        ("ask_human", {"question": "封面用什么颜色？", "checked": "决定 A-01 只管图的格式，不管颜色"}),
    ])
    assert "先别问" in blocked and "决定 A-01" in blocked               # 没说查过什么就问 → 退回去先看
    assert "决定 A-01" in found
    assert "Q1" in rec and "自动答上" in rec
    assert "D-02" in asked and "Q2" in asked
    import answers
    qs = {e["code"]: e for e in answers.read(proj)}
    assert qs["Q1"]["result"] == "自动答上" and qs["Q1"]["fields"]["用的"] == "决定 A-01" and qs["Q1"]["fields"]["运行"] == "W1-1"
    assert qs["Q2"]["result"] == "转给你了" and qs["Q2"]["fields"]["转成待拍板"] == "D-02"
    c = store.connect(proj.db_path)
    d = store.answer(c, "D-02", "封面用深蓝")
    assert answers.close_pending(c, proj, "D-02", d["code"], "封面用深蓝") == "Q2"
    c.close()
    q2 = {e["code"]: e for e in answers.read(proj)}["Q2"]
    assert q2["result"] == "你拍板了" and q2["fields"]["你拍板"].startswith("A-02")
    assert not (proj.root / "笔记" / "总览.md").exists()                 # 答疑跟笔记分开


def test_agent_checks_before_borrowing(proj):
    """真实 stdio 进程读取临时应用的示例卡，不依赖开发仓库收集的项目或插件。"""
    backend = proj.root / "backend"
    shutil.copytree(BACKEND, backend, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    repo = proj.root / "工具库" / "开源项目" / "O1 示例.md"
    repo.parent.mkdir(parents=True)
    repo.write_text("---\n编号: O1\n名字: synthetic-mcp\n许可证: AGPL-3.0\n"
                    "一句话: 临时测试项目，不含真实开发材料\n原件: 工具库/开源项目/原件/示例.zip\n---\n只借思路。\n", encoding="utf-8")
    plugin = proj.root / "插件" / "示例预览" / "插件.md"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("---\n名字: 示例预览\n一句话: 测试插件\n版本: 1\n---\n按示例安装。\n", encoding="utf-8")
    repos, one, nope, plugs = anyio.run(_call, proj, [("list_repos", {}), ("read_repo", {"code": "O1"}), ("read_repo", {"code": "O999"}), ("list_plugins", {})], backend)
    assert "O1 synthetic-mcp" in repos and "不许抄" in repos
    assert "红灯：只借思路" in one and nope.startswith("没有 O999")
    assert "示例预览" in plugs and "没启用" in plugs


def test_agent_moves_misplaced_material_back_to_the_intake_and_sorts_it(proj):
    """10-08：agent 能把放错的材料挪回外部资料入口（move_to_inbox），也能直接分拣（sort_inbox_item）；都要写原因、记着是谁。"""
    f = proj.materials / "文献" / "旧稿.md"
    f.parent.mkdir(parents=True)
    f.write_text("自己写的稿子", encoding="utf-8")
    (proj.materials / "论文").mkdir()
    moved, listed, sorted_, blue, empty = anyio.run(_call, proj, [
        ("move_to_inbox", {"path": "资料/文献/旧稿.md", "reason": "这是论文的稿子，放错到文献了"}),
        ("list_inbox", {}),
        ("sort_inbox_item", {"item": 1, "module": "论文", "reason": "是自己写的稿子"}),
        ("move_to_inbox", {"path": "资料/蓝图/x.md", "reason": "试试"}),
        ("sort_inbox_item", {"item": 1, "module": "论文", "reason": ""}),
    ])
    assert "已挪到外部资料入口" in moved and "#1" in moved and "sort_inbox_item(1" in moved
    assert "原位置" in listed and "旧稿.md" in listed
    assert "已放进 资料/论文/旧稿.md" in sorted_
    assert blue.startswith("没挪：") and empty.startswith("没放：")
    assert not f.exists() and (proj.materials / "论文" / "旧稿.md").read_text(encoding="utf-8") == "自己写的稿子"
    import journal
    es = [e for e in journal.read(proj) if e["by"] == "agent:test-agent"]
    assert [e["kind"] for e in es] == ["移到外部资料入口", "放进来"]
    assert "这是论文的稿子，放错到文献了" in es[0]["body"] and "是自己写的稿子" in es[1]["body"]


def test_agent_cannot_sort_into_governance_places(proj):
    """10-08：agent 放进 蓝图/戒律、模块根的 戒律.md、技能/ 会变成活的目标、规矩、技能——要人在网页上点。"""
    box = proj.materials / "_外部资料入口"
    box.mkdir(parents=True)
    for n in ("S1-9 新目标.md", "戒律.md", "SKILL.md"):
        (box / n).write_text("agent 丢进来的", encoding="utf-8")
    (proj.materials / "论文").mkdir()
    listed, blue, rules, skill = anyio.run(_call, proj, [
        ("list_inbox", {}),
        ("sort_inbox_item", {"item": 1, "module": "蓝图", "reason": "是个新目标"}),
        ("sort_inbox_item", {"item": 3, "module": "论文", "reason": "论文的规矩"}),          # 入口按名字登记：1 S1-9… 2 SKILL.md 3 戒律.md
        ("sort_inbox_item", {"item": 2, "module": "论文", "folder": "技能", "reason": "论文的做法"}),
    ])
    import intake
    import store
    c = store.connect(proj.db_path)
    names = {r["id"]: r["name"] for r in intake.waiting(c)}
    c.close()
    assert names == {1: "S1-9 新目标.md", 2: "SKILL.md", 3: "戒律.md"}, listed
    for out in (blue, rules, skill):
        assert out.startswith("没放：") and "让人在网页上点" in out, out
    assert sorted(x.name for x in box.iterdir()) == ["S1-9 新目标.md", "SKILL.md", "戒律.md"]
    assert not (proj.materials / "论文" / "戒律.md").exists() and not (proj.materials / "论文" / "技能").exists()
