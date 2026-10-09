"""给 agent 的接口（标准 MCP）：看全貌、读笔记、问问题、报每一圈都走这里，哪家 agent 都能接。

一份应用只管一个项目：项目 = 应用自己这个文件夹，跟网页一致。
开新项目用 新项目.bat 复制一份干净的应用，里面的 .mcp.json 用相对路径，直接能用。

agent 能做的：看全貌、加模块、向人提问、读人的笔记、给外部资料入口的文件写分拣候选或直接分拣（写原因）、把放错的材料挪回入口。
不能删、不能改状态——删由人写进笔记交给 agent，agent 用 move_to_trash 挪进回收站；做没做完由人验。
"""
from __future__ import annotations

import argparse
import re
import json

from mcp.server.fastmcp import Context, FastMCP

import agents
import answers
import supervise
import blueprint
import board
import claims
import dispatch
import deliveries
import downloads
import files
import content_modules
import intake
import journal
import notebook
import project as proj
import ideas
import library
import readiness
import requirements
import workorders
import runs
import store
import tools
import tool_guides
import skills
import snapshot
import trash
from project import Project, resolve

WORD = {"ok": "齐了", "warn": "不够", "todo": "在做", "bad": "还没开始"}

RULES = """这是本地长程项目治理辅助工具，工作由 agent 执行。网页与 MCP 共用治理文件。
- 接手先读 AGENTS.md、get_overview；具体内容用 get_governance（goal/module/requirement/all）读取全文、来源和关联。
- 目标、需求、戒律、任务、计划集中在 治理/；模块是承接者。需求可以先于模块存在，并关联多个模块。关联未确认就明确缺项，不猜。
- 按人的本次授权修改正文：先 read_governance_document 取得 revision，再 write_governance_document 原样传回 revision；新文件用空版本。冲突时重新读并合并，不覆盖别人的输入。
- 总方向、需求和规则由人定；人明确要求的修改可以执行，不重复索要确认。未授权的新方向用 add_idea 记原话、suggest_requirement 提候选。
- 做着做着想加一件任务、一条需求：用 propose_draft 放进草稿区（人在蓝图「草稿区」点「行」才进正式的任务表 / 需求表，编号程序排），不直接往表里加行。
- 做事按目标 → 计划 → 戒律：先在 治理/计划/<目标>/ 保存 P号 · 日期 · 标题.md；保留旧编号范围、原文和来源。头一行写目标、戒律、工具、模块、状态。
- 模块材料在 资料/<模块>/，有模块专属技能先读；新模块用 add_module。通用模块用 get_overview 返回的 common: key。
- 改核心前 claim_task("核心") 拿锁，拿锁时程序照设置自动存一档（设置 → 存档；关着就自己 save_checkpoint），改后 add_log kind 改了核心。测试只碰临时项目。
- 做完照「怎么验」自验并 deliver：检查全过就默认通过、算做完（作者 09-30：「验收一律默认通过」），有没过的检查停在待你验收；人随时能打回。不交付不能自己标做完；人在对话里说验收才用 record_acceptance 照原话记。
- 日志和人的笔记分开；人的笔记只增，机器记事用 add_log；自动运行每圈 report_run。开工单、交付、答疑继续各自保存。
- 开工单目标和本次工作不相符就不绑定；自动执行遵守开工单范围、圈数、失败上限和停止条件。没有有效开工单或被叫停就停止自动转圈。
- 问题先 find_answer 查人的旧决定，查到写清依据并 record_answer；没有才 ask_human，继续不依赖答案的工作。
- 文件不越出授权范围；删搬通过回收站。外部材料只经外部资料入口；公开发布、花钱、装软件遵守人的授权和项目戒律。
- 第一次来先报到：register_agent（名字、用的哪家、一句话），拿编号 G 和档案（自动化/agent/）；没报到领不到活。有档案的照档案来：只领「管哪些」里的、不碰「不碰」的，「改核心：不能」的拿不到核心锁，照「交代」做事；职责变了用 my_profile 改自己的（改核心那格只有人改）。
- 自动推进和几个 agent 一起干，照 自动化/协议.md：start_work 开工（没在跑的单就自己开一张，不用人点）→ next_task 领一件 → 写计划 → 做 → 照「怎么验」验 → deliver（检查全过默认通过、自动放手、本机 git 记一次）→ 再 next_task；改核心前 claim_task("核心") 拿锁。同一个 agent 程序开了几个一起干时，每个在这些工具里写不一样的 agent 名字（如 claude-code#2）。只在「彻底删除、公开发布」「改方向（S0、S1、需求、戒律正文）」这两类停：记下来、跳过这件接着做别的。
- 借别人的东西先查（工具 S2-8）：要抄开源项目的代码前 read_repo 看「能不能借」——红灯（GPL / AGPL / 没许可证）只借思路、不抄代码（工-1）；要用插件先 list_plugins 看装没装、怎么装；装程序、装插件先问人（工-3）。
- 技能就在项目里，不用装：项目根 AGENTS.md 有技能目录，list_skills 看、read_skill 读全文；开始一件事前先看有没有用得上的，有就照它做。
- 网页会自己盯着项目（监管）：没拿锁改核心、删东西没进回收站、改了人的笔记、改了方向文件、改了没人领着的模块，都会被记下；拿不准的它会去问人。你领活、报一圈、交付时，返回里的「监管提醒」照着改，不用停下来。
- 走之前写一份交接单：自动化/交接/H<号> · 年-月-日 · 你的名字.md（格式见技能「自动化科研交互界面」）；来了先读最新的那张。
- 普通接手不迁移。作者明确要求集中治理时先存一档，再 migrate_governance；检查冲突、清单与旧链接。
"""


_LAST = {"agent": ""}             # 这条连接上最近一次报的名字（报到、或调工具时写的 agent）
_BOUND = ""                       # 网页员工的专用 MCP 进程只允许这个身份
_CONFIG_AUTH = ""
_RUNNER_CONTROL = False


def me(ctx, agent: str = "") -> str:
    """这次是谁：给了 agent 就用它（同一个 Claude Code 开的几个 agent 共用一条连接，靠它分清），并记下来；不然照 who。"""
    a = " ".join((agent or "").split())[:40]
    if _BOUND and a and agents.short(a) != _BOUND:
        raise store.Refused("这条员工连接不能冒用其他员工身份")
    if a:
        _LAST["agent"] = a if a.startswith("agent:") else f"agent:{a}"
        return _LAST["agent"]
    return who(ctx)


def who(ctx: Context | None) -> str:
    """记是谁做的：这条连接上报过名字的就用它（10-01 Codex 写的日志记成了「codex-mcp-client」）；
    没报过的用连接自报的名字（Claude Code 报 claude-code；Codex 报 codex-mcp-client，去掉后缀算 codex）。"""
    if _BOUND:
        return agents.actor(_BOUND)
    if _LAST["agent"]:
        return _LAST["agent"]
    try:
        name = ctx.session.client_params.clientInfo.name
    except Exception:
        return "agent"
    return "agent:" + re.sub(r"-mcp-client$", "", name)


def build(project: Project) -> FastMCP:
    mcp = FastMCP("research-console", instructions=RULES)

    def conn():
        return store.connect(project.db_path)

    def _latest_handover() -> str:
        """自动化/交接/ 里最新的一张交接单（按修改时间），从项目根算的路径；没有就空。"""
        d = project.root / "自动化" / "交接"
        try:
            hs = sorted((x for x in d.glob("*.md") if x.is_file()), key=lambda x: x.stat().st_mtime)
        except OSError:
            return ""
        return hs[-1].relative_to(project.root).as_posix() if hs else ""

    @mcp.tool()
    def get_overview() -> str:
        """看项目全貌（低清照片）：有哪些模块、各有多少文件、蓝图进度、等人拍板的问题、人最近的决定。接手项目先调这个。"""
        c = conn()
        try:
            s = store.get_state(c, project)
        finally:
            c.close()
        p = s["project"]
        import digest
        now_t, now_h = digest.now_text(project)                # 「项目现在的样子」放最前面（S1-8 S2-62）：先读它，不用翻全部日志
        out = [f"# {p['name']}", p["one_line"] or "", f"项目根：{p['root']}", ""]
        if now_t:
            out += [f"## 项目现在的样子（{digest.NOW}，{now_h.get('什么时候', '')} {now_h.get('谁写的', '')} 写的；先读这段）", "",
                    now_t.split("\n\n", 1)[-1] if now_t.startswith("# ") else now_t, ""]
        out += ["## 进门先读", "- 项目根 AGENTS.md：规矩、东西在哪、技能目录"]
        h = _latest_handover()
        if h:
            out.append(f"- 上一个 agent 留的交接单：{h}——先读，接着它往下做")
        sk = skills.catalog(project)
        if sk:
            out.append("- 项目自带的技能（不用装，read_skill 读全文照做）：" + "；".join(
                k["name"] + (f"（{k['module']} 模块）" if k["module"] else "") + f" {k['path']}" for k in sk))
        c = conn()
        try:
            busy = claims.active(c)
        finally:
            c.close()
        out.insert(out.index("## 进门先读") + 1, "- 第一次来先报到：register_agent（名字、用的哪家、一句话），拿编号和档案；已经有档案的读 my_profile 照着做")
        out += ["", "## 谁在干什么（自动化/协议.md；next_task 领活，同一件、同一条道只给一个人；名册见 list_agents）"]
        out += [f"- {r['agent']}：{(r['goal'] + ' ' + r['sub']).strip()} {r['what']}（道：{'、'.join(r['lanes'])}；{r['idle'] // 60} 分钟前有动静）"
                for r in busy] or ["- 没人领着"]
        out += ["", "## 模块（资料/ 下每个文件夹一个）"]
        for m in s["modules"]:
            by = "" if m["source"] == "default" else f"（{m['created_by']}）"
            link = f"，挂了 {len(m['links'])} 个链接" if m["links"] else ""
            desc = f"：{m['one_line']}" if m["one_line"] else ""
            en = f" {m['en']}" if m["en"] else ""
            sk = f" · 专属技能 资料/{m['name']}/技能/SKILL.md（进这个模块干活先读）" if (project.materials / m["name"] / "技能" / "SKILL.md").is_file() else ""
            out.append(f"- {m['name']}{en}{by} · {m['files']} 个文件{link}{desc}{sk}")
        if s["blueprint"]:
            n = s["counts"]
            out += ["", "## 蓝图（目标金字塔；以返回的源文件位置为准）"]
            if s["s0"]:
                out.append(f"S0 {s['s0']['name']}：{s['s0']['one_line']}")
            out.append("底下的 S2：" + " · ".join(f"{WORD[k]} {n[k]}" for k in ("ok", "warn", "todo", "bad")))
            out += [f"- [{WORD[b['status']]}] {b['code']} {b['name']}：{b['one_line']}（S2 做完 {b['done']}/{b['total']}，{b['file']}）"
                    for b in s["blueprint"]]
        if s["problems"]:
            out += ["", "## 要看一下的"] + [f"- {x}" for x in s["problems"]]
        scene = s["panorama"]
        out += ['', f"## 集中治理：需求 {len(scene['requirements'])} 条，未分配模块 {len(scene['unassigned'])} 条",
                '需求先在蓝图明确，再由模块承接；用 get_governance 读全文、关联和来源。正文修改先 read_governance_document，再携带 revision 调 write_governance_document。']
        out += [f"- 未分配 {q['key']}：{q['func']}；验收：{q['effect']}；来源 {q['file']}" for q in scene['unassigned']]
        out += ["", "## 蓝图的能力层级（由上到下；不是任务依赖）"]
        module_labels = {m["key"]: ("通用/" if m["kind"] == "common" else "") + m["name"] for m in scene["modules"]}
        out += [f"- {layer['name']}：" + "、".join(module_labels[key] for key in layer["modules"]) for layer in scene["layers"]]
        out += ["", "## 目标与模块的明确关联（与网页蓝图共用）"]
        for g in scene["goals"]:
            out.append(f"- {g['code']} → {'、'.join(module_labels[key] for key in g['related_modules']) or '未关联'}；做完 {g['counts']['done']}，待你验收 {g['counts']['pending']}")
        for m in scene["modules"]:
            out.append(f"- 模块 {module_labels[m['key']]} → {'、'.join(m['goals']) or '未关联'}" + (f"；{'、'.join(m['missing'])}" if m["missing"] else ""))
            out += [f"  - {x}" for x in m["relation_notes"]]
            out += [f"  - 本模块任务 {x['code']}：{x['what']}（{x['text']}）" for x in m["tasks"]]
            out += [f"  - 计划 {x['path']}" for x in m["plans"]]
        for r in scene["relations"]:
            out.append(f"- 来源 {r['goal']} ↔ {module_labels[r['module']]}：" + "；".join(f"{x['file']} · {x['field']}" for x in r["sources"]))
        if scene["status"]["save"]:
            sv = scene["status"]["save"]
            out.append(f"最近存档：{sv['code']} {sv['name']}")
        out += ["", "## 等人拍板"]
        out += [f"- {q['code']} {q['text']}（{q['created_by']} 问的）" for q in s["pending"]] or ["- 没有"]
        out += ["", "## 人最近的决定"]
        out += [f"- {d['code']} {d['text']}（回答 {d['ref']}：{d['detail']}）" for d in s["decisions"][:10]] or ["- 还没有"]
        a = s["auto_settings"]
        out += ["", "## 自动化", f"档位 {a['level']}：{a['level_text']} · 每次最多 {a['rounds']} 圈"]
        out += [f"- 工作流 {w['code']} {w['name']}：{w['one_line']}（卡片 {w['file'] if w.get('project') else '自动化/工作流/' + w['file']}）" for w in runs.list_workflows(project=project)]
        if s["auto"]:
            r = s["auto"]
            out.append(f"- 最近一次：{r['code']} · {r['status']} · 第 {r['round']} 圈" + (f" · 在做 {r['goal']}" if r["goal"] else ""))
        wo = workorders.running(project)
        c = conn()
        try:
            pnl = readiness.panel(c, project, wo) if wo else None
        finally:
            c.close()
        if wo is None:
            out += ["", "## 开工单（网页「自动化」页；人「交给 agent」了才转）",
                    "没有在跑的开工单 —— 不要转圈；report_run 记不上「在跑」"]
            out += [f"- 备料：{w['code']} {w['name']}（目标 {'、'.join(w['target']) or '没选'}；文件 自动化/开工单/{w['file']}）"
                    for w in workorders.list_all(project) if w["stored"] == "备料"]
        else:
            n = wo["notes"]
            out += ["", f"## 在跑的开工单：{wo['code']} {wo['name']}（自动化/开工单/{wo['file']}）",
                    f"{wo['started']} 交给 agent · 档 {wo['level']} · 每次最多 {wo['rounds']} 圈 · 同一件失败 {wo['fails']} 次就停",
                    f"要做成：{wo['product'] or '（没写）'}",
                    f"目标：{'、'.join(wo['target'])}（只做这些）"]
            for m in dict.fromkeys(readiness.split_target(x)[0] for x in wo["target"]):   # 同一个模块只写一遍
                r = requirements.read(project, m)
                if r:
                    v = requirements.view(project, m)
                    out += [f"「{m}」的需求（{r['file']}；要装成：{r['one_line']}）——施工照它走："]
                    out += [f"- {q['code']} 功能：{q['func']}｜效果：{q['effect']}｜现在：{q['state']}" for q in v["reqs"]]
                if (project.materials / m / "技能" / "SKILL.md").is_file():
                    out.append(f"「{m}」的专属技能：资料/{m}/技能/SKILL.md——先读，这个模块的东西照它做")
            out += ["要做的几件（只做这些）："]
            out += [f"- {x['goal']} {x['code']} {x['what']}" + (f"｜为了：{'、'.join(x['for'])}" if x.get("for") else "")
                    + f"｜怎么验：{x['how'] or '（没写，先在计划里写清）'}｜现在：{x['text']}" for x in pnl["items"]]
            out += ["戒律（从上到下，下层只能更严）：" + " → ".join(
                        (r["text"] if r["layer"] == "这张单" else r["file"]) + f"（{r['layer']}）" for r in pnl["rules"] if r["exists"]),
                    f"模块：{'、'.join(wo['modules']) or '（没列）'}",
                    f"工具：{'、'.join(wo['tools']) or '（没列）'}（照卡调；list_tools 看全）",
                    f"材料：{'、'.join(wo['materials']) or '（没列）'}",
                    f"存档：{'、'.join(wo['saves']) or '（没列）'}"]
            out += [f"交代 · {k}：{' / '.join(x.strip() for x in n[k].splitlines() if x.strip())}" for k in workorders.NOTES if n.get(k)]
            red = [f"{d['name']}：{d['summary']}" for d in pnl["devices"] if d["lamp"] != "ok"]
            out += ["还不是绿的：" + ("没有" if not red else "；".join(red))]
        pending = deliveries.pending(project)
        if pending:
            out.append(f"交付单等人验收：{pending} 张（自动化/交付/）")
        c = conn()
        try:
            asked = [q for q in store.list_asked(c) if not q["closed_at"]]
        finally:
            c.close()
        if asked:
            out += ["", f"## 你问 agent：{len(asked)} 条等你答（先答再干活，用 answer_person）"]
            out += [f"- {q['code']} {q['text']}" + (f"（出处：{q['detail']}）" if q["detail"] else "") for q in asked[:20]]
        wait = downloads.pending(project)
        if wait:
            out += ["", f"## 下载清单：{len(wait)} 篇还没下好（资料/<模块>/下载清单.md；下好的在 资料/<模块>/原文/）"]
            out += [f"- {m} {x['code']} {x['title']}（{x['state']}）" for m, x in wait[:15]]
        todo = ideas.pending(project)
        if todo:
            out += ["", f"## 想法：{len(todo)} 个还没定去向（资料/想法/想法.md；suggest_requirement 给候选）"]
            out += [f"- {x['code']}（关于 {x['about']}）{x['text']}" for x in todo[:20]]
        return "\n".join(out)

    @mcp.tool()
    def get_governance(kind: str = "all", key: str = "") -> str:
        """读集中治理详情。kind: all / goal / module / requirement；key: S1 编号、模块 key 或需求唯一 key。返回同网页的全文、来源、关联、适用戒律和执行记录。"""
        import governance
        import json
        try:
            return json.dumps(governance.detail(project, kind, key), ensure_ascii=False, indent=2)
        except ValueError as e:
            return f'没找到：{e}'

    @mcp.tool()
    def read_governance_document(path: str) -> str:
        """读取治理正文和 revision；写之前先读。支持旧路径。"""
        import governance, json
        try:
            return json.dumps(governance.read_document(project, path), ensure_ascii=False)
        except ValueError as e:
            return f'没读到：{e}'

    @mcp.tool()
    def get_content_workspace(module: str) -> str:
        """只读文献、论文或测试工作台的文件来源；不扫描或创建文献条目，不新建索引。"""
        try:
            return json.dumps(content_modules.workspace(project, module), ensure_ascii=False)
        except (ValueError, OSError) as e:
            return f'没读到：{e}'

    @mcp.tool()
    def get_builtin_files(path: str = '') -> str:
        """只读文件内置状态或完整人工标记列表，与网页同源；锁是新建继承，不是禁止编辑。普通文件正本为项目根内置标记.json，存档保存当时标记。"""
        import builtin, file_actions
        try:
            data = file_actions.builtin_status(project, path) if path else builtin.list_marks(project.root)
            return json.dumps(data, ensure_ascii=False)
        except (ValueError, OSError) as e:
            return f'没读到：{e}'

    @mcp.tool()
    def read_content_document(module: str, path: str) -> str:
        """读取论文/测试正文和完整 SHA revision；已声明的内置模板只读。路径从模块开始。"""
        try:
            return json.dumps(content_modules.read_document(project, module, path), ensure_ascii=False)
        except (ValueError, OSError) as e:
            return f'没读到：{e}'

    @mcp.tool()
    def write_content_document(module: str, path: str, text: str, revision: str, project_root: str,
                               reason: str = '', agent: str = '', ctx: Context | None = None) -> str:
        """按人的授权保存论文/测试正文。空 revision 只能新建；更新核对完整版本并留下旧稿/身份/来源日志，不代表任务验收。"""
        actor = me(ctx, agent)
        c = conn()
        try:
            return json.dumps(content_modules.write_document(c, project, module, path, text, revision,
                              project_root, by=actor, source='mcp', reason=reason), ensure_ascii=False)
        except (ValueError, OSError, store.Refused) as e:
            return f'没保存：{e}'
        finally:
            c.close()

    @mcp.tool()
    def write_governance_document(path: str, text: str, revision: str, reason: str, ctx: Context | None = None) -> str:
        """按本次授权修改治理文件。先读到 revision 后原样传回；新文件传空字符串。并发冲突拒绝覆盖，写入自动记录 agent 身份；不能自行标做完。"""
        import governance, json
        c = conn()
        try:
            return json.dumps(governance.save_document(c, project, path, text, revision, by=who(ctx), reason=reason), ensure_ascii=False)
        except (ValueError, store.Refused) as e:
            return f'没保存：{e}'
        finally:
            c.close()

    @mcp.tool()
    def migrate_governance(request: str, ctx: Context | None = None) -> str:
        """只在人明确要求集中治理后用；先 save_checkpoint 存一档。复制校验后原件进回收站，冲突保留双方。request 记人的迁移要求。"""
        import governance_paths
        import json
        if not request.strip():
            return '没迁移：需要记录人的迁移要求'
        c = conn()
        try:
            return json.dumps(governance_paths.migrate(c, project, by=who(ctx), request=request), ensure_ascii=False)
        finally:
            c.close()

    @mcp.tool()
    def add_idea(text: str, about: str = "整个项目", source: str = "对话", ctx: Context | None = None) -> str:
        """人说了一个新想法（要什么功能、什么效果、什么规矩）：先记进想法表（资料/想法/想法.md），编号 想-n。
        text: 人的原话（别改写）
        about: 关于哪个模块（模块名），整个项目就写「整个项目」
        source: 从哪来，如「对话 09-27」「笔记 总-031」"""
        c = conn()
        try:
            x = ideas.add(c, project, text, source=source, about=about, by=who(ctx))
        except store.Refused as e:
            return f"没记上：{e}"
        finally:
            c.close()
        return f"记了 {x['code']}（关于 {x['about']}）。要整理去向就用 suggest_requirement 给候选，人在网页「想法」里点。"

    @mcp.tool()
    def answer_person(code: str, answer: str, ctx: Context | None = None) -> str:
        """答人问你的问题（网页「问答 · 你问 agent」里的 问-01 这种）。先答再干活。
        code: 问题编号，如「问-01」；answer: 答案（人话；写清依据：哪份文件、哪一页；不会就直说不会，不编）"""
        c = conn()
        try:
            a = store.answer_person(c, code, answer, by=who(ctx))
        except store.Refused as e:
            return f"没写上：{e}"
        finally:
            c.close()
        return f"答了 {code}（{a['code']}），人在网页「问答」里看得到。"

    @mcp.tool()
    def record_acceptance(code: str, said: str, ctx: Context | None = None) -> str:
        """人在对话里说了验收（「验收」「可以」「J3 没问题」）：照他的原话记下，那件变「做完」。只在人真说了的时候用。
        code: 交付单编号，如「J3」；said: 人的原话"""
        c = conn()
        try:
            j = deliveries.accept_by_word(c, project, code, said, agent=who(ctx))
        except store.Refused as e:
            return f"没记上：{e}"
        finally:
            c.close()
        return f"记上了：{code}（{j['goal']} {j['sub']}）验收通过，写明是人在对话里说的。"

    @mcp.tool()
    def add_download(title: str, url: str = "", doi: str = "", why: str = "", module: str = "文献",
                     authors: str = "", year: str = "", venue: str = "", note: str = "", ctx: Context | None = None) -> str:
        """要一篇论文（PDF）但你没法下 / 不该自己下：排进那个模块的下载清单，人在网页上点链接下，开放获取的程序直接下。
        title: 标题；url: 你找到的链接（论文页、PDF、arXiv）；doi: 有就写（程序会去找合法的免费版）
        why: 为什么要这篇（为了哪条需求、哪件事）；module: 放进哪个模块，默认「文献」
        authors / year / venue: 作者（前两个，多的写「等」）、年、期刊或会议——知道就写，不知道有 DOI 的程序会去 OpenAlex 补
        note: 备注（比如「是书，不必下 PDF」「软件手册，到官网取引用格式」）
        只写合法来源的链接（出版社、arXiv、开放获取），不写盗版站。"""
        c = conn()
        try:
            x = downloads.add(c, project, module, title=title, url=url, doi=doi, why=why, by=who(ctx),
                              authors=authors, year=year, venue=venue, note=note)
        except store.Refused as e:
            return f"没排进去：{e}"
        finally:
            c.close()
        return (f"排进了 {module} 的下载清单：{x['code']} {x['title']}。下好了会放在 资料/{module}/原文/，"
                f"get_overview 里能看到还剩几篇没下。先做不依赖它的事。")

    @mcp.tool()
    def suggest_requirement(idea: str, candidates: list[dict], ctx: Context | None = None) -> str:
        """给一个想法写 1~3 个去向候选（把握大的在前），人在网页「想法」里点一个才算。每个候选一定带 reason（一句理由）：
        - 先于模块的共享需求：{"to": "需求", "goals": ["S1-1"], "modules": [], "func": "需求", "effect": "验收标准", "reason": "依据"}；modules 可以列多个模块 key。
        - 新的模块需求：{"to": "需求", "module": "文献", "func": "要什么功能", "effect": "要什么效果（打开能看见什么）", "reason": …}
        - 补进已有的一条：{"to": "需求", "module": "文献", "req": "需-2", "add": "补什么", "reason": …}
        - 模块戒律：{"to": "戒律", "module": "文献", "rule": "不许做什么（一行）", "reason": …}
        - 总的那层（只标去向、请人亲自改）：{"to": "总的", "what": "S0 / S1 / 通用戒律 / 项目戒律", "text": "想怎么改", "reason": …}
        idea: 想法编号，如「想-3」"""
        c = conn()
        try:
            x = ideas.suggest(c, project, idea, candidates, by=who(ctx))
        except store.Refused as e:
            return f"没写上：{e}"
        finally:
            c.close()
        return f"给 {idea} 写了 {len(x['candidates'])} 个候选：" + "；".join(ideas.describe(k) for k in x["candidates"]) + "。等人在网页上点。"

    @mcp.tool()
    def propose_tool(name: str, one_line: str, why: str, install: str, check: str = "", how: str = "",
                     kind: str = "外部工具", ctx: Context | None = None) -> str:
        """缺工具时用：你上网找到合适的工具，写一张新卡（下一个 T 号，状态「待你装」），并自动请人装（进网页「问答」）。
        **你不要自己装**——装软件是人的事。写完这件标「等工具」（mark_goal），去做下一件；人装好了卡上的「待你装」会去掉。
        name: 工具名，如「pdf.js」
        one_line: 一句话它干什么
        why: 为什么要它（做哪件 S2 要用、不用它会怎样；有别的选择就写为什么选它，注意许可证能不能开源）
        install: 人照着装的步骤或命令（从哪下载、放到哪、多大）
        check: 装好以后查一下的命令（只读，如「latexmk -v」；放进项目的库可以不写）
        how: 装好以后怎么调
        kind: 技术栈（项目拿它做东西）/ 外部工具（做的时候调的程序）"""
        by = who(ctx)
        try:
            t = tools.propose(name, one_line=one_line, why=why, install=install, check_cmd=check, how=how, kind=kind, by=by, lib=project.root / "工具库")
        except ValueError as e:
            return f"没写卡：{e}"
        c = conn()
        try:
            q = store.ask_human(c, f"请你装 {t['code']} {t['name']}：{one_line}", by=by,
                                context=f"为什么要：{why}\n怎么装：{install}\n装好了在「工具」页点「装好了」。")
        finally:
            c.close()
        return f"写好了卡 {t['code']}（工具库/{t['file']}，待你装），也请人装了（{q['code']}）。这件先标「等工具」，去做别的。"

    @mcp.tool()
    def propose_draft(kind: str, where: str, fields: dict, reason: str, agent: str = "", revise: str = "", ctx: Context | None = None) -> str:
        """起草一条任务或需求，放进草稿区（治理/草稿/草-<号>.md），正式文件不动；人在蓝图「草稿区」点「行」才收进去，编号程序排（蓝图 S2-4）。
        kind: 「任务」或「需求」
        where: 任务放哪：S1 编号（「S1-8」）或模块名（「文献」）；需求放哪：「项目」或模块名
        fields: 任务 {"做什么": …, "为了": "项目 需-3 / 需-2", "怎么验": 机器能查的}；
                需求 {"要什么功能": …, "要什么效果": 打开能看见什么, "来自": 原话和日期, "关联目标": "S1-8"（只给项目）, "承接模块": "文献"（只给项目）}
        reason: 一句理由：为什么要加这一条
        revise: 你写的草稿被审核打回了，照理由改同一张就写它的编号（「草-3」），fields 只给改了的格，reason 写改了什么；kind、where 照原来的
        有审核的 agent 时，草稿先给它审（准 / 打回），三轮还不过交给人；人随时能点「行」（S1-8 S2-40）"""
        import drafts
        if revise.strip():
            try:
                d = drafts.revise(project, revise.strip(), fields, reason, by=me(ctx, agent))
            except store.Refused as e:
                return f"没改上：{e}"
            return f"{d['code']} 改好了，再给审核的 agent 审（第 {drafts.rounds(d) + 1} 轮）。不用等，接着做别的。"
        try:
            d = drafts.propose(project, kind, where, fields, reason, by=me(ctx, agent))
        except store.Refused as e:
            return f"没放进草稿区：{e}"
        c = conn()
        try:
            with store.tx(c):
                store.log(c, me(ctx, agent), "起草", d["code"], f"{kind} · {d['where']}")
        finally:
            c.close()
        return f"{d['code']} 放进草稿区了（{d['file']}）：{kind} · 放到 {d['where']}。等人在蓝图「草稿区」点「行」才进正式文件，不用等，接着做别的。"

    @mcp.tool()
    def mark_goal(goal: str, sub: str, status: str, note: str = "", ctx: Context | None = None) -> str:
        """改蓝图里一件 S2 的状态（那张表最后一格）。
        goal: 目标，如「S1-10」，模块蓝图就写模块名「文献」；sub: 那一件，如「S2-3」
        status: 在做 / 等工具 / 等你 / 待你验收 / 等 S2-3（卡在别的件后面：「等 S2-3」「等 S1-8 S2-25」，那件做完了自动能领）——**「做完」只有人能标**；做完了用 deliver 交单
        note: 补一句（为什么等、卡在哪）"""
        allowed = ("在做", "等工具", "等你", "待你验收")
        if status not in allowed and not blueprint.waits_on(goal, status):
            return f"没改：状态只能是 {' / '.join(allowed)}；「做完」只有人在网页上验收时标。"
        text = status + (f"（{' '.join(note.split())}）" if note.strip() else "")
        c = conn()
        try:
            old = blueprint.set_status(project, goal, sub, text)
            with store.tx(c):
                store.log(c, who(ctx), "改目标状态", f"{goal} {sub}", text)
        except ValueError as e:
            return f"没改：{e}"
        finally:
            c.close()
        return f"{goal} {sub}：「{old}」→「{text}」。"

    @mcp.tool()
    def deliver(goal: str, sub: str, did: str, checks: list[dict], files: list[str] | None = None,
                checkpoint: str = "", run: str = "", plan: str = "", agent: str = "", ctx: Context | None = None) -> str:
        """做完一件、照「怎么验」验过了：交一张交付单（自动化/交付/J…）。交了自动放手、在本机 git 记一次（agent 写你的名字）。每条检查都过了就默认通过（作者 09-30：「验收一律默认通过」），
        显式启用checks-pass交付策略时，非空检查中的ok必须全部为布尔true才自动完成并接续，失败直接打回返工。人随时能打回。未配置策略的项目保留原独立验收或默认验收流程。
        checkpoint 填动手前存的那一档（拿核心锁时自动存的、或自己 save_checkpoint 存的）。交完照设置会再自动存一档。
        goal / sub: 如「S1-10」「S2-3」；模块蓝图的写「文献」「S2-3」
        did: 做了什么（人能看懂的几句话）
        checks: 怎么验的，每条 {"name": "打开 L1 翻到第 3 页", "ok": true, "detail": "右边是第 3 页译文"}——没验过不许交
        files: 东西在哪，从项目根写，如 ["资料/文献/L1 …/译文.md"]
        run: 这一次的日志编号，如 W1-3.2；plan: 用的计划，如「计划/S1-10 …/P1 · 2026-09-29 · ….md」"""
        c = conn()
        try:
            j = deliveries.deliver(c, project, goal=goal, sub=sub, did=did, checks=checks, files=files,
                                   checkpoint=checkpoint, run=run, plan=plan, by=me(ctx, agent))
            snapshot.auto_save(c, project, "on_deliver", name=f"交了 {j['code']}", by=me(ctx, agent), checks=checks,
                               why=f"{j['code']} {goal} {sub}：{did}"[:200])   # 照设置交付后自动存一档（S1-8 S2-59）
            warn = supervise.reminder_text(c, me(ctx, agent))
        except (store.Refused, ValueError) as e:
            return f"没交：{e}"
        finally:
            c.close()
        if j['state'] == '待你验收' and deliveries.independent_pending(project, j):
            return (f"交了 {j['code']}，有没过的检查，状态仍为「待你验收」；独立验收员工将复查并打回，"
                    "修好重新交付后再独立复跑，原失败检查不能直接判通过。" + warn)
        if j["state"] == "等验收":
            if deliveries.self_checks_failed(j):
                return (f"交了 {j['code']}，自查有失败，等独立验收员工复查并打回；修好重新交付后再独立复跑。"
                        f"{goal} {sub} 现在是「待验收（{j['code']}）」；原失败检查不能直接判通过。" + warn)
            return (f"交了 {j['code']}，检查全过，等验收的 agent 复跑（{deliveries.last_note(j).split('（', 1)[-1].rstrip('）')}）："
                    f"{goal} {sub} 现在是「待验收（{j['code']}）」，过了算做完，没过会回到你手里。不用等，接着做下一件。" + warn)
        if j["state"] == "验收通过":
            return f"交了 {j['code']}，检查全过，默认通过：{goal} {sub} 现在是「做完（{j['code']} 默认通过）」。人不满意会打回，打回的回到「在做」。" + warn
        if j["state"] == "打回":
            return (f"交了 {j['code']}，自查未全部通过，已自动打回返工；{goal} {sub} 现在是「在做」。"
                    "请修复后实际复验并重新交付，失败或未测的检查不能报通过。" + warn)
        return f"交了 {j['code']}（有没过的检查，{goal} {sub} 停在「待你验收（{j['code']}）」），人在网页「自动化 → 交付」里点，或者在对话里说了（你用 record_acceptance 照原话记）。不用等，接着做下一件。" + warn

    @mcp.tool()
    def review_draft(code: str, ok: bool, why: str, agent: str = "", ctx: Context | None = None) -> str:
        """审核（岗位写着「审核」的 agent 用；next_task 会先把等审的草稿给你）：看草稿区里别人起草的任务、需求。
        ok=true 准（写为什么准）；ok=false 打回（写清哪里不行、怎么改），回到写的人手里改，三轮还不过交给人。不审自己写的；不改草稿、不改正式文件。"""
        import drafts
        try:
            d = drafts.review(project, code, ok, why, by=me(ctx, agent))
        except store.Refused as e:
            return f"没记上：{e}"
        c = conn()
        try:
            claims.release(c, "审核", code, note="审完")
            with store.tx(c):
                store.log(c, me(ctx, agent), "审核", code, ("准：" if ok else "打回：") + why[:60])
        finally:
            c.close()
        return (f"{code} 准了：草稿区写着你审过，等人点「行」收进去。" if ok else
                f"{code} 打回了（第 {drafts.rounds(d)} 轮）：写的人下次 next_task 先拿到它改。") + "接着 next_task 拿下一张。"

    @mcp.tool()
    def review_delivery(code: str, ok: bool, notes: str, checks: list[dict] | None = None, agent: str = "",
                        ctx: Context | None = None) -> str:
        """验收（岗位写着「验收」的 agent 用；next_task 会先把等验收的交付单给你）：照交付单上的检查自己再跑一遍、看东西在不在、对不对。
        ok=true 过了 → 那件算做完；ok=false 没过 → 打回，回到原来干活的手里。notes：看到了什么（没过写清哪条、实际看到什么）；
        checks：你复跑的每条 {"name", "ok", "detail"}。不验自己干的；不改别人做的东西。"""
        c = conn()
        try:
            j = deliveries.review(c, project, code, ok, notes, by=me(ctx, agent), checks=checks)
        except store.Refused as e:
            return f"没记上：{e}"
        finally:
            c.close()
        return (f"{code} 验收过了：{j['goal']} {j['sub']} 算做完。" if ok else
                f"{code} 打回了：{j['goal']} {j['sub']} 回到「在做」，原来干活的下次 next_task 先拿到它。") + "接着 next_task 拿下一张。"

    @mcp.tool()
    def report_run(workflow: str, goal: str, did: str, result: str, status: str = "在跑", next_step: str = "",
                   run: str = "", agent: str = "", ctx: Context | None = None) -> str:
        """跑工作流时，每走完一圈报一次（也算你还在做：领着的件续上，不会被当成放手）：记进自动化日志（自动化/日志/，跟人的笔记分开），网页「自动化」页和总览顶上跟着变。

        workflow: 哪条工作流，如 W1
        run: 这是第几次，如 W1-3；开始新的一次就空着（会给你新编号）
        goal: 在做哪个目标，如「S1-5 S2-2」
        did / result / next_step: 这一圈做了什么、结果、下一步
        status: 在跑 / 停了等你 / 跑完待验收 / 失败停了——不是「在跑」就表示这一次停下了"""
        c = conn()
        try:
            r = runs.report(c, project, workflow, by=me(ctx, agent), run=run, goal=goal, did=did, result=result,
                            status=status, next_step=next_step)
            claims.beat(c, me(ctx, agent))
            warn = supervise.reminder_text(c, me(ctx, agent))
        except store.Refused as e:
            return f"没记上：{e}"
        finally:
            c.close()
        more = "" if status != "在跑" else f"接着下一圈时 run 填 {r['run']}。"
        return f"已记 {r['code']}（{status}）。{more}" + warn

    @mcp.tool()
    def list_workflow_graphs() -> str:
        """读取本项目可编辑工作流、启用快照与停用守卫；不启动员工。"""
        import workflow_graph
        return json.dumps(workflow_graph.list_all(project), ensure_ascii=False)

    @mcp.tool()
    def read_workflow_graph(code: str) -> str:
        """读取 W 图的普通文件全文、最新草稿版本和独立的启用快照版本。"""
        import workflow_graph
        return json.dumps(workflow_graph.read(project, code), ensure_ascii=False)

    @mcp.tool()
    def validate_workflow_graph(graph: dict) -> str:
        """只读检查任务、员工、独立审核验收和分支条件；不认领、不执行图代码。"""
        import workflow_graph
        return json.dumps(workflow_graph.validate(project, graph), ensure_ascii=False)

    @mcp.tool()
    def dry_run_workflow_graph(graph: dict) -> str:
        """只读演练真实记录会走哪些节点，不调用 next_task、不派活或开窗。"""
        import workflow_graph
        c = conn()
        try:
            return json.dumps(workflow_graph.dry_run(c, project, graph), ensure_ascii=False)
        finally:
            c.close()

    @mcp.tool()
    def save_workflow_graph(name: str, graph: dict, code: str = "", revision: str = "", agent: str = "", ctx: Context | None = None) -> str:
        """保存或修订项目私有 W 草稿；修改带旧 revision。保存不会启用，也不能自行提权或开工。"""
        import workflow_graph
        caller = me(ctx, agent)
        agents.require(project, caller)
        c = conn()
        try:
            return json.dumps(workflow_graph.save(c, project, code, name, graph, revision, by=caller), ensure_ascii=False)
        finally:
            c.close()

    def _task_text(t: dict) -> str:
        return (f"{t['goal']} {t['sub']}：{t['what']}\n- 怎么验：{t['how'] or '（没写：先写进计划）'}"
                + (f"\n- 为了：{'、'.join(t['for'])}" if t["for"] else "") + f"\n- 占的道：{'、'.join(t['lanes'])}\n- 在哪：{t['file']}")

    @mcp.tool()
    def start_work(target: list[str] | None = None, name: str = "", agent: str = "", resume: bool = False,
                   ctx: Context | None = None) -> str:
        """一站式自动推进的开头：有在跑的开工单就加入它；没有就照蓝图自己开一张、自己开工（档 2，不用人点）。
        target：想做哪几件，如 ["S1-11 S2-2", "文献 S2-6"]；不写就挑蓝图里第一个有「写了怎么验、还没做完」的件的目标。
        agent：你的名字——同一个 agent 程序开了几个一起干时，每个写不一样的（如 claude-code#2）；不写用连接自报的名字。
        resume：人在网页上叫停过，就不自己开新单；只有人在对话里让你开工时才带 resume=true。
        开不了（灯有红）会写清缺什么。之后用 next_task 领活。"""
        c = conn()
        try:
            got = dispatch.start_work(c, project, me(ctx, agent), target=target, name=name, resume=resume)
        except store.Refused as e:
            return f"没开工：{e}"
        finally:
            c.close()
        wo = got["wo"]
        return (f"{'加入' if got['joined'] else '自己开了'} {wo['code']} {wo['name']}（在跑；目标 {'、'.join(wo['target'])}）。"
                "接着调 next_task 领一件。")

    @mcp.tool()
    def next_task(agent: str = "", ctx: Context | None = None) -> str:
        """给我下一件并领走（没有在跑的开工单会先自己开一张）。同一件同一时间只给一个人，同一个模块同一时间只给一个人。
        拿到以后：写计划 → 做 → 照「怎么验」验 → deliver（检查全过默认通过；交了自动放手、本机 git 记一次）→ 再调 next_task。
        改核心（backend/、模板.html、界面脚本、启动器）前先 claim_task("核心") 拿锁。agent：你的名字，见 start_work。
        你是别人的上级、下面的人卡住了，返回最前面先写「叫你是因为……」（S1-8 S2-36）。"""
        name = me(ctx, agent)
        c = conn()
        try:
            wake = agents.wake_text(c, project, name)
        finally:
            c.close()
        return wake + _next_task(name)

    def _next_task(name: str) -> str:
        c = conn()
        try:
            got = dispatch.next_task(c, project, name)
        except store.Refused as e:
            return f"没领到：{e}"
        finally:
            c.close()
        if got.get("action") in ("stopped", "waiting", "submit_plan", "review_plan"):
            return json.dumps(got, ensure_ascii=False) + "\n按 action 调 submit_execution_plan / review_execution_plan；waiting 或 stopped 时退出本轮，外层运行器会等条件改变再唤醒。"
        if got.get("draft"):                                # 审核的岗位：先审草稿（S1-8 S2-40）
            d = got["draft"]
            rows = "\n".join(f"- {k}：{v}" for k, v in d["fields"].items())
            past = "\n".join(f"- {r['at']} · {r['by']} · {r['act']}：{r['why']}" for r in d.get("reviews") or [])
            goal = d["where"] if d["kind"] == "任务" else ""
            return (f"{name} 领到审核：{d['code']}（{d['kind']} · 放到 {d['where']}，{agents.short(d['by'])} 写的）。\n"
                    "看它：为了哪条需求对不对、「怎么验」机器查不查得了、有没有跑出 S0 和这块目标的方向、跟已有的件重没重。"
                    f"审完调 review_draft(code=\"{d['code']}\", ok=true 或 false, why=\"理由\")：准写为什么准；打回写清哪里不行、怎么改。不改它、不改正式文件。\n\n"
                    f"理由：{d['reason']}\n{rows}" + (f"\n\n以前几轮：\n{past}" if past else "")
                    + (("\n\n" + board.goal_text(project, goal)) if goal else ""))
        if got.get("plan"):                                 # 规划的岗位：先改被打回的草稿，再补还缺东西的块
            pj = got["plan"]
            if pj["kind"] == "改草稿":
                d = pj["draft"]
                last = d["reviews"][-1]
                return (f"{name}：你写的 {d['code']}（{d['kind']} · {d['where']}）被 {last['by']} 打回了：{last['why']}\n"
                        f"照理由改同一张：propose_draft(kind=\"{d['kind']}\", where=\"{d['where']}\", revise=\"{d['code']}\", fields={{改了的格}}, reason=\"改了什么\")。")
            r = pj["row"]
            return (f"{name} 领到规划：{r['code']}{' ' + r['name'].replace(r['code'], '').strip() if r['name'] != r['code'] else ''}（还没定稿）还缺：{'；'.join(r['missing'])}。\n"
                    "缺任务的照需求起草任务（propose_draft kind=任务，写清做什么、为了哪条需求、怎么验——验要机器查得了）；缺需求的起草需求；"
                    "别的（戒律、格式）写进计划或 ask_human。只起草，不改正式文件；起草完了再 next_task。\n\n" + board.goal_text(project, r["code"]))
        if got.get("review"):                               # 验收的岗位：先给验收活（S1-8 S2-39）
            j = got["review"]
            return (f"{name} 领到验收：{j['code']}（{j['goal']} {j['sub']} {j['what']}，{agents.short(j['by'])} 交的）。\n"
                    f"照下面「怎么验的」自己再跑一遍，看「东西在哪」那几样在不在、对不对；验完调 review_delivery(code=\"{j['code']}\", ok=true 或 false, "
                    "notes=\"看到了什么\", checks=[{name, ok, detail}])。没过写清哪条、实际看到什么；不改别人做的东西。\n\n"
                    + j["body"][:4000] + "\n\n" + board.why_text(project, j["goal"], j["sub"]))
        wo = got["wo"]
        put = f"（{'、'.join(got['done'])} 没有能做的了，放下了）" if got["done"] else ""
        if got["task"] is None:
            return f"没有给你的了{put}：{got['reason']}。可以停下写交接单，或者过一会儿再领。"
        prof = agents.find(project, name)
        c = conn()
        try:
            warn = supervise.reminder_text(c, name)
        finally:
            c.close()
        t = got["task"]
        return (f"{name} 领到（{wo['code']} {wo['name']}）{put}{'：' + got['reason'] if got['reason'] else ''}\n"
                + _task_text(t) + "\n\n" + board.why_text(project, t["goal"], t["sub"])
                + ("\n\n## 你的档案\n" + agents.brief_text(prof) if prof else "") + warn)

    @mcp.tool()
    def claim_task(goal: str, sub: str = "", agent: str = "", ctx: Context | None = None) -> str:
        """领指定的一件：goal 如「S1-11」「文献」，sub 如「S2-2」。goal 写「核心」是拿核心锁（改 backend/、模板.html 这些之前拿，一次一个人；交付时自动放）。
        别人在做这件、或这件的道上有别人：领不到，会写清是谁。agent：你的名字，见 start_work。"""
        name = me(ctx, agent)
        c = conn()
        try:
            if workorders.paused(c):
                raise store.Refused("人已叫停，不再领取任务或核心锁")
            if goal.strip() == claims.CORE:
                import workflow_graph, autolaunch
                with autolaunch._file_lock(project, "工作流图"):
                    a = agents.require(project, name)
                    held = [r for r in claims.of(c, name) if r["goal"] not in (claims.CORE, "审核", "验收", "施工审核", "规划")]
                    bound = workflow_graph.employee_bindings(project, name)
                    if a.get("plan_required") or bound or any(workflow_graph.requires_plan(project, r["goal"], r["sub"]) for r in held):
                        import construction_plans as cp
                        if not held:
                            raise store.Refused("先领施工任务并提交计划，审过才可拿核心锁")
                        if bound and not any(r["goal"] == b["goal"] and r["sub"] == b["sub"] for r in held for b in bound):
                            raise store.Refused("先领取流程绑定的施工任务并通过计划审核，再拿核心锁")
                        for r in held:
                            cp.require_approved(project, r["goal"], r["sub"], name)
                    had = claims.holds_core(c, name)
                    r = agents.take_core(c, project, name, sub)
                if not had:                                  # 新拿到核心锁：照设置自动存一档（S1-8 S2-59；续锁不重复存）
                    snapshot.auto_save(c, project, "on_core", name=f"改核心前 {agents.short(name)}", by=name,
                                       why=f"{name} 拿了核心锁" + (f"：{sub}" if sub else ""))
            else:
                prof = agents.require(project, name)
                g = blueprint.find(blueprint.pyramid(project), goal.strip())
                x = next((x for x in g["subs"] if x["code"] == sub.strip()), None) if g else None
                if x is None:
                    return f"没领到：蓝图里没有 {goal} {sub}"
                why = (dispatch._work_reason(project, prof, g, x)
                       if prof.get('auto') or prof.get('plan_required') or __import__('workflow_graph').requires_plan(project, g['code'], x['code']) else agents.allows_reason(prof, g, x))
                if why:
                    return "没领到：" + why
                r = claims.claim(c, g["code"], x["code"], name, claims.lanes_of(g, x), x["what"])
                why = __import__('workflow_graph').worker_reason(project, prof, g, x)
                if why:
                    claims.release(c, g["code"], x["code"], name, "流程准入复核未通过：" + why)
                    return "没领到：" + why
        except store.Refused as e:
            return f"没领到：{e}"
        finally:
            c.close()
        done = f"{name} 领了 {(r['goal'] + ' ' + r['sub']).strip()}（道：{'、'.join(r['lanes'])}）。2 小时没动静会自动放手。"
        return done if goal.strip() == claims.CORE else done + "\n\n" + board.why_text(project, r["goal"], r["sub"])

    @mcp.tool()
    def release_task(goal: str, sub: str = "", note: str = "", agent: str = "", for_agent: str = "", ctx: Context | None = None) -> str:
        """放手：不做了、做不下去、要换人（note 写为什么，下一个接手的看得到）。交付会自动放手，不用再调。goal 写「核心」是放核心锁。
        for_agent：你是它的上级、它领着这件半小时没动静了，写它的编号让它放手，件回到能做（S1-8 S2-36）。"""
        name = me(ctx, agent)
        c = conn()
        if for_agent.strip():
            try:
                what = agents.release_for(c, project, name, for_agent.strip(), goal.strip(), sub.strip(), note)
            except store.Refused as e:
                return f"没放：{e}"
            finally:
                c.close()
            return f"让 {for_agent} 放手了：{what} 回到能做，别人能领。"
        try:
            ok = claims.release(c, goal.strip(), sub.strip(), name, note)
        finally:
            c.close()
        return f"放了 {goal} {sub}".strip() + "。" if ok else f"没放：{goal} {sub} 不是 {name} 领着的"

    @mcp.tool()
    def who_is_working() -> str:
        """谁在干什么：在跑的开工单、每个 agent 领着哪件、占着哪条道、多久没动静（2 小时没动静的算放手了）。"""
        c = conn()
        try:
            busy = claims.active(c)
        finally:
            c.close()
        wo = workorders.running(project)
        out = [f"在跑的开工单：{wo['code']} {wo['name']}（目标 {'、'.join(wo['target'])}）" if wo else "没有在跑的开工单（start_work 能自己开）"]
        out += [f"- {r['agent']}：{(r['goal'] + ' ' + r['sub']).strip()} {r['what']}（道：{'、'.join(r['lanes'])}；{r['since'][5:16].replace('T', ' ')} 领的，{r['idle'] // 60} 分钟前有动静）"
                for r in busy] or ["- 没人领着"]
        return "\n".join(out)

    @mcp.tool()
    def register_agent(name: str, program: str = "", line: str = "", ctx: Context | None = None) -> str:
        """报到（第一次来这个项目先调）：拿编号 G 和档案（自动化/agent/G… 名字.md）。没报到领不到活。
        name：你调接口时用的名字（如 codex、claude-code#2），以后 next_task 这些的 agent 都写它；同名再来接上原来那份。
        program：你是哪家的（Claude Code、Codex、Cursor、通义灵码……）；line：一句话，你打算干什么 / 擅长什么。
        人可能已经给你建好了档案、写了管哪些和交代：报到后照着做。"""
        c = conn()
        try:
            if _BOUND and agents.short(name or who(ctx)) != agents.short(_BOUND):
                raise store.Refused("报到名字必须与本窗口绑定的员工一致")
            got = agents.register(c, project, name or who(ctx), program, line)
        except store.Refused as e:
            return f"没报上：{e}"
        finally:
            c.close()
        a = got["agent"]
        _LAST["agent"] = agents.actor(a["name"])              # 这条连接后面没带名字的，都记在它名下
        return (f"{'报到了' if got['new'] else '接上原来的档案'}：{a['code']} {a['name']}（{agents.DIR.as_posix()}/{a['file']}）。"
                f"以后调 next_task 这些时 agent 写「{a['name']}」。\n\n" + agents.brief_text(a))

    @mcp.tool()
    def my_profile(agent: str = "", changes: dict | None = None, why: str = "", ctx: Context | None = None) -> str:
        """看 / 改自己的档案。不带 changes 是看；带了是改（只改带上的），「变迁」会记一行谁改的、为什么。
        能改的：program 用什么 · line 一句话 · scope 管哪些（模块名或目标编号，「、」隔开；空 = 都能领）· avoid 不碰 · skills 技能 ·
        opener 开工的话 · brief 交代（正文）。core（改核心）、roles（岗位）、level（等级）、boss（上级）只有人能改。职责跟着项目变了就改，why 写为什么。"""
        name = me(ctx, agent)
        if not changes:
            a = agents.find(project, name)
            if a is None:
                return f"「{agents.short(name)}」还没报到：先调 register_agent"
            return agents.brief_text(a) + "\n\n变迁：\n" + "\n".join(f"- {x}" for x in a["history"])
        c = conn()
        try:
            a = agents.update(c, project, name, changes, by=name, why=why)
        except store.Refused as e:
            return f"没改：{e}"
        finally:
            c.close()
        return f"改好了，{a['code']} 的「变迁」多了一行：{a['history'][-1]}"

    @mcp.tool()
    def list_agents() -> str:
        """名册：有档案的、来过没报到的，一人一行——编号、用什么、岗位、等级、上级、管哪些、灯（在干活 / 停了 / 空着）、领着哪件、交过几件。"""
        c = conn()
        try:
            rows = agents.roster(c, project)
        finally:
            c.close()
        out = []
        for r in rows:
            held = "、".join(f"{h['goal']} {h['sub']}".strip() for h in r["holding"]) or "没领活"
            out.append(f"- {r['code'] or '（没报到）'} {r['name']}" + (f"（{r['program']}）" if r["program"] else "")
                       + (f" · {'、'.join(r['roles'])} · {r['level']} · 上级 {'人' if r['boss'] == agents.HUMAN else r['boss']}" if r["registered"] else "")
                       + f" · {r['lamp']} · {held}"
                       + (f" · 管 {'、'.join(r['scope'])}" if r["scope"] else "") + (f" · 不碰 {'、'.join(r['avoid'])}" if r["avoid"] else "")
                       + (" · 改核心：不能" if r["core"] == agents.NO else "") + f" · 交过 {len(r['delivered'])} 件")
        return "\n".join(out) or "还没有 agent 报到过"

    @mcp.tool()
    def add_module(name: str, one_line: str = "", en: str = "", ctx: Context | None = None) -> str:
        """加一个模块：建 资料/<name>/ 文件夹，网页中间那条多一个标签，记下是你加的。

        name: 模块名（就是文件夹名），40 字以内，不能有 \\ / : * ? " < > |
        one_line: 一句话说它装什么
        en: 英文名，网页上跟在中文名后面，如 Experiments
        """
        by = who(ctx)
        c = conn()
        try:
            m = store.add_module(c, project, name, by=by, source="agent", one_line=one_line, en=en)
            journal.add(c, project, f"新建模块「{m['name']}」" + (f"：{one_line}" if one_line else ""), by=by, kind="新建模块", scope=m["name"])
        except store.Duplicate as e:
            return f"没有重复加：已经有模块「{e.existing['name']}」了。"
        except store.Refused as e:
            return f"没加上：{e}"
        finally:
            c.close()
        return f"已加模块「{m['name']}」，文件夹是 资料/{m['name']}/，记为 {by} 加的。东西放进这个文件夹，网页上就看得见。"

    def _hits_text(hits) -> str:
        return "\n".join(f"{i}. [{h['src']}] {h['text']}" for i, h in enumerate(hits, 1))

    @mcp.tool()
    def find_answer(question: str) -> str:
        """有问题先调这个：在人拍过的板（决定 A-xx）、戒律、计划、蓝图、人的笔记里找有没有已经答过的。
        人说过的话不用再问第二遍。找到了就照做，并用 record_answer 记一条；都不管用，再 ask_human。"""
        c = conn()
        try:
            hits = answers.find(c, project, question)
        finally:
            c.close()
        if not hits:
            return "记录里没找到相关的。要人定就 ask_human，checked 写「find_answer 没找到」。"
        return ("可能已经答过（按相关程度排）：\n" + _hits_text(hits) +
                "\n\n判断一下：如果有一条已经回答了你的问题 → 照它做，调 record_answer(question, answer, used=那条的出处)；"
                "\n都不管这件事 → ask_human，checked 写清查过哪几条、为什么不管用。")

    @mcp.tool()
    def record_answer(question: str, answer: str, used: str, run: str = "", ctx: Context | None = None) -> str:
        """自动答上了：记一条答疑（自动化/答疑/，编号 Q…，跟人的笔记分开）。
        used: 用的哪条记录，写出处，如「决定 A-07」「戒律 通-5」——必须来自记录，不许自己编。
        run: 正在跑的工作流那一次，如 W1-3（没在跑就空着）。"""
        if not used.strip():
            return "没记：used 要写用的哪条记录（如「决定 A-07」）。没有出处的答案不算自动答上，去 ask_human。"
        c = conn()
        try:
            q = answers.log(c, project, question, by=who(ctx), result="自动答上", run=run, used=used, answer=answer)
        finally:
            c.close()
        return f"已记为 {q['code']}（自动答上）。接着干。"

    @mcp.tool()
    def ask_human(question: str, context: str = "", checked: str = "", run: str = "", ctx: Context | None = None) -> str:
        """有事要人定，就写进网页「待你判断」里，人会攒着一起拍板。不打断人。

        先 find_answer 查过再问：人拍过板的事不许再问。
        question: 要人定的事，一句话问清楚
        context: 背景：为什么要问、有哪几个选项、各自代价
        checked: 查过哪些记录、为什么都不管用（没写的话，这里会先替你查一遍，查到相关的就退回给你看）
        run: 正在跑的工作流那一次，如 W1-3（没在跑就空着）
        调完别停下来等答案，先做不依赖它的部分；之后用 get_overview 看人拍了没有。
        """
        by = who(ctx)
        c = conn()
        try:
            if not checked.strip():
                hits = answers.find(c, project, question)
                if hits:
                    return ("先别问——记录里可能已经答过：\n" + _hits_text(hits) +
                            "\n\n答过了就照做，调 record_answer 记一条；确实没答过，带上 checked（查过哪几条、为什么不管用）再问。")
                checked = "find_answer 没找到相关记录"
            q = store.ask_human(c, question, by=by, context=(context + "\n" if context else "") + "查过：" + checked)
            a = answers.log(c, project, question, by=by, result="转给你了", run=run, checked=checked, pending=q["code"])
        except store.Refused as e:
            return f"没记上：{e}"
        finally:
            c.close()
        return f"已记为 {q['code']}（答疑 {a['code']}），出现在网页「③ 待你判断」里。先接着干不依赖它的部分。"

    @mcp.tool()
    def move_to_trash(path: str, reason: str, request: str = "", ctx: Context | None = None) -> str:
        """把一个文件或文件夹挪进回收站（项目根 回收站/，按原来的路径原样放，清单记一条 X 号）。
        **只照人的删除请求做**（笔记里 kind「删除请求」那条，或人直接说的）；不许自己决定删。不直接删，彻底删掉要人另外明说。
        path: 从项目根算，如「资料/文献/旧稿.pdf」
        reason: 为什么删（人怎么说的）
        request: 对应的删除请求编号，如「文献-003」（有就写，清理页靠它把请求标成处理过）"""
        c = conn()
        try:
            r = trash.move(c, project, path, by=who(ctx), reason=reason, request=request, origin="agent 照删除请求挪的")
        except store.Refused as e:
            return f"没挪：{e}"
        finally:
            c.close()
        return f"已挪进回收站：{r['code']}，原来在 {'、'.join(r['from'])}，现在在 {r['to']}。人要还原就 restore_from_trash('{r['code']}')。"

    @mcp.tool()
    def restore_from_trash(code: str, swap: bool = False, ctx: Context | None = None) -> str:
        """把回收站里的一件（如 X3）原样挪回原来的位置。只在人要求时做。
        原位置已经有东西：先不挪，把情况告诉人；人确认了再带 swap=True（现有的先挪进回收站，另一个编号）。"""
        c = conn()
        try:
            r = trash.restore(c, project, code, by=who(ctx), swap=swap)
        except (store.Refused, store.NeedConfirm) as e:
            return f"没还原：{e}"
        finally:
            c.close()
        return f"已还原 {r['code']} → {r['back_to']}。" + (f"原位置上的挪进了 {r['swapped']}。" if r["swapped"] else "")

    @mcp.tool()
    def save_checkpoint(name: str, why: str, mode: str = "核心", picks: list[str] | None = None,
                        checks: list[dict] | None = None, ctx: Context | None = None) -> str:
        """存一档（游戏存档那样的好节点）。过了一关（测试全过、实验跑完、一个计划做完）就存一档。
        name: 这一档叫什么，如「表1跑完」
        why: 为什么存（做完了什么）
        mode: 核心（只复制程序和规矩：backend/、模板.html、治理/、技能库/、工具库/、插件/、自动化/……；不带资料、笔记、零碎文件）/ 只记指纹（不复制，只做记号）。
        写全量、自定义也按核心存（作者 09-30：「只存核心就行了」）。每档都记下全部文件的指纹；只留最近 10 档，多的自动丢
        picks: 不用了
        checks: 这一关你验了什么，每条 {"name": "pytest", "ok": true, "detail": "48 过"}；全过才是绿档，没写或有没过的是黄档。
        定性（认它是安全点）只有人能做，你不能。"""
        c = conn()
        try:
            m = snapshot.save(c, project, name=name, why=why, mode=snapshot.offered(mode), by=who(ctx), checks=checks)
        except store.Refused as e:
            return f"没存：{e}"
        finally:
            c.close()
        return (f"存好了：{m['code']}「{m['name']}」· {m['mode']} · {m['grade']} · 复制了 {m['copied_files']} 个文件，"
                f"全部 {m['total_files']} 个都记了指纹。在 {m['folder']}/。")

    @mcp.tool()
    def list_checkpoints() -> str:
        """看有哪些存档：编号、名字、什么时候、谁存的、存法、绿档黄档、定性没有。"""
        saves = snapshot.list_saves(project)
        if not saves:
            return "还没有存档。"
        return "\n".join(f"- {m['code']}「{m['name']}」· {m['at']} · {m['by']} · {m['mode']} · {m['grade']}"
                         + (" · 已定性" if m.get("settled") else "") + (f" · {m['why']}" if m.get("why") else "") for m in saves)

    @mcp.tool()
    def restore_checkpoint(code: str, paths: list[str] | None = None, confirm: bool = False, whole: bool = False, builtin_revision: str | None = None, ctx: Context | None = None) -> str:
        """复活：把某一档（如 C3）复制了的文件放回原位；换下来的和那之后新加的挪进回收站；笔记、计划、日志不倒回。
        **只照人的要求做**。先不带 confirm 调一次，拿到「会换几个、放回几个、挪走几个」告诉人；人确认了再带 confirm=True。
        paths: 只复活这些文件或文件夹（从项目根算）；不写就是程序和规矩及内置。whole=True：整份回到那一档（资料也回去，人明说才用）。
        builtin_revision: 确认时原样回传预览给出的内置标记版本；若确认期间有人修改，拒绝并重新预览。"""
        c = conn()
        try:
            r = snapshot.restore(c, project, code, by=who(ctx), paths=paths, confirm=confirm, whole=whole, builtin_revision=builtin_revision)
        except store.NeedConfirm as e:
            return f"还没动：{e}（人确认了再带 confirm=True，并原样回传 builtin_revision）\n" + json.dumps(e.info, ensure_ascii=False)
        except store.Refused as e:
            return f"没复活：{e}"
        finally:
            c.close()
        if r.get("nothing"):
            return f"{code} 跟现在一样，没什么要复活的。"
        return (f"复活了 {code}：换回 {r['replaced']} 个、放回 {r['restored']} 个、挪进回收站 {r['trashed']} 个"
                + (f"（{r['trash_code']}，能还原）" if r["trash_code"] else "") + "。")

    # ---- 世界树（S1-8 S2-55、S2-56）：枝 = 一档整份取出来的独立项目，枝上的 agent 跟主干互不排队；结果实、G1 验收、合回主干
    @mcp.tool()
    def world_tree(ctx: Context | None = None) -> str:
        """世界树：这里是主干还是一根枝；主干上有哪些枝（从哪一档长、为了什么、状态、谁在上面）。"""
        import worldtree
        here = worldtree.is_branch(project)
        head = (f"这里是枝 {here['code']}「{here['name']}」（从主干 {here['base']} 长出来，状态 {here['state']}）：你改的只在这根枝上，"
                "干完调 bear_fruit 结果实，G1 验收后合回主干。"
                + (f"上次打回：{here['rejected'][-1]['why']}" if here.get("rejected") else "") if here else "这里是主干。")
        bs = worldtree.list_branches(project)
        import branching
        gs = [g for g in branching.groups(project) if g["state"] in branching.OPEN]
        if gs:
            head += "\n比较单（档位 3、4 自动排的）：" + "；".join(f"{g['code']} {g['item']} · {g['state']} · 枝 {'、'.join(g['branches'])}" for g in gs)
        return head + ("\n" + "\n".join(f"- {b['code']}「{b['name']}」· 从 {b['base']} · {b['state']} · {b['path']}"
                                        + (f" · 为了 {b['why']}" if b.get("why") else "") + (f" · demo：{b['demo']}" if b.get("demo") else "")
                                        + (f" · 打回过：{b['rejected'][-1]['why']}" if b.get("rejected") else "")
                                        for b in bs) if bs else "\n还没有枝。")

    @mcp.tool()
    def grow_branch(name: str, why: str, base: str = "现在", for_task: str = "", ctx: Context | None = None) -> str:
        """长一根枝：从一档（C<n>）或现在（先存一档）整份取出来，放到项目旁边的「<项目名> 世界树/枝-<号> 名字/」。
        它是完整独立的项目：自己的库、核心锁、认领、存档；在那个文件夹里开的 agent 改的只在枝上。G1 派活用。"""
        import worldtree
        c = conn()
        try:
            b = worldtree.grow(c, project, name=name, by=who(ctx), why=why, base=base, for_=for_task)
        except store.Refused as e:
            return f"没长：{e}"
        finally:
            c.close()
        return (f"长了 {b['code']}「{b['name']}」：从 {b['base']} 取出 {b['files']} 个文件，在 {b['path']}"
                + (f"（那一档没存的 {b['missing_count']} 个没有）" if b["missing_count"] else "") + "。派活用 assign_to_branch。")

    @mcp.tool()
    def assign_to_branch(branch: str, agent: str, goal: str = "", sub: str = "", open_window: bool = True, ctx: Context | None = None) -> str:
        """派到枝上：在枝的库里替员工（G5 这样）领下这件，在网页终端里给它开窗口（标题「枝-3 · G5 名字」，进枝的文件夹、接枝的接口）。"""
        import worldtree
        c = conn()
        try:
            r = worldtree.assign(c, project, branch, agent, goal, sub, by=who(ctx), open_window=open_window)
        except (store.Refused, KeyError, RuntimeError) as e:
            return f"没派：{e}"
        finally:
            c.close()
        return f"派了：{r['agent']} {r['name']} 到 {branch}" + (f" 做 {r['task']}" if r["task"] else "") + (f"，开了窗口「{r['window']}」" if r["window"] else "") + "。"

    @mcp.tool()
    def bear_fruit(demo: str, checks: list[dict] | None = None, ctx: Context | None = None) -> str:
        """（在枝里）枝上干完了：存一档、标「结果了」、写 demo 说明（怎么看、看什么）和检查（[{name, ok, detail}]，跑过的测试写上）。之后等 G1 验收合回主干。"""
        import worldtree
        c = conn()
        try:
            b = worldtree.bear_fruit(c, project, demo=demo, checks=checks, by=who(ctx))
        except store.Refused as e:
            return f"没结：{e}"
        finally:
            c.close()
        return f"{b['code']} 结果了（存了 {b['fruit_checkpoint']}）：{b['demo']}。等 G1 验收合回主干。"

    @mcp.tool()
    def branch_changes(branch: str, ctx: Context | None = None) -> str:
        """识别改动：拿长枝那一档当底，枝改了什么、主干同期改了几个；合之前看。"""
        import worldtree
        try:
            ch = worldtree.changes(project, branch)
        except store.Refused as e:
            return f"看不了：{e}"
        part = lambda k, t: f"{t} {len(ch[k])}：" + ("、".join(ch[k][:30]) + ("……" if len(ch[k]) > 30 else "") if ch[k] else "没有")
        return "\n".join([part("take", "只枝改（直接换上）"), part("both", "两边都改（三方合并）"), part("delete", "枝删了"),
                          part("same", "改得一样"), part("records", "枝的记录（收档）"), f"主干同期自己改的 {ch['trunk_only']} 个（不动）"])

    @mcp.tool()
    def merge_branch(branch: str, confirm: bool = False, ctx: Context | None = None) -> str:
        """G1 验收过了（开枝的网页看 demo、在枝里跑过测试、看过 branch_changes），合回主干。先不带 confirm 调一次看会动什么，再带 confirm=True。
        合前、合完各存一档；只枝改的换上、两边改的三方合并，合不开的不覆盖主干（放进 自动化/世界树/枝-n/冲突/，你照着手合）。"""
        import worldtree
        c = conn()
        try:
            if not confirm:
                ch = worldtree.changes(project, branch)
                return (f"还没合：会换上 {len(ch['take'])} 个、三方合并 {len(ch['both'])} 个、删 {len(ch['delete'])} 个、收档记录 {len(ch['records'])} 个；"
                        "确认了再带 confirm=True。")
            r = worldtree.merge(c, project, branch, by=who(ctx))
        except store.Refused as e:
            return f"没合：{e}"
        finally:
            c.close()
        return (f"{branch} 合回主干了（合前 {r['before']}、合完 {r['after']}）：换上 {len(r['took'])}、三方合并 {len(r['merged'])}、删 {len(r['deleted'])}"
                + (f"；合不开 {len(r['conflicts'])} 个：" + "、".join(x["path"] for x in r["conflicts"]) + f"（在 自动化/世界树/{branch}/冲突/，照着手合）"
                   if r["conflicts"] else "") + "。")

    # ---- 清理（S1-8 S2-62、S2-63）：写摘要、出重写单
    @mcp.tool()
    def digest_material(kind: str = "", key: str = "", agent: str = "", ctx: Context | None = None) -> str:
        """写摘要的材料：不写 kind 就列出现在该写哪几份；写了（月摘要 + 年-月 / 总摘要 + 总的 / 现在的样子）就给那份的材料和要求。只读。"""
        import digest
        c = conn()
        try:
            if not kind:
                ds = digest.due(c, project)
                return "\n".join(f"- {d['kind']} {d['key']} → {d['out']}：{d['why']}" for d in ds) or "现在没有该写的摘要。"
            return json.dumps(digest.packet(c, project, kind, key or kind), ensure_ascii=False, indent=1)
        except store.Refused as e:
            return f"拿不到：{e}"
        finally:
            c.close()

    @mcp.tool()
    def write_digest(kind: str, key: str, text: str, agent: str = "", ctx: Context | None = None) -> str:
        """交一份摘要：kind 是 月摘要（key 写 年-月）· 总摘要（key 写 总的）· 现在的样子（key 写 现在的样子，四节标题照材料写）。
        只根据材料写、每句写出处、不编。程序加稿头（谁写的、什么时候、依据）、记日志。"""
        import digest
        c = conn()
        try:
            r = digest.write(c, project, kind, key, text, by=me(ctx, agent))
        except store.Refused as e:
            return f"没收：{e}"
        finally:
            c.close()
        return f"收了：{r['out']}（{r['size']} 字节，依据 {r['basis']}）。"

    @mcp.tool()
    def propose_rewrite(path: str, text: str, changes: list[dict], agent: str = "", ctx: Context | None = None) -> str:
        """给一份正本（需求、戒律、目标、协议、使用说明、AGENTS.md、技能……）出一张重写单：text 是改后全文；
        changes 每处 {what: 改了什么, from: 合并 / 去掉的是哪几条（出处）, why: 为什么}。只出单、不换上——人（方向文件）或 G1 看过对照点「行」才换。"""
        import rewrite
        c = conn()
        try:
            x = rewrite.propose(c, project, path, text, changes, by=me(ctx, agent))
        except store.Refused as e:
            return f"没出：{e}"
        finally:
            c.close()
        return f"出了 {x['code']}：{x['target']}，{len(x['changes'])} 处，{x['old_size']} → {x['new_size']} 字节；等{'人' if x['direction'] else '人或 G1'}看对照点「行」。"

    @mcp.tool()
    def review_rewrite(code: str, ok: bool, why: str, agent: str = "", ctx: Context | None = None) -> str:
        """审一张别人出的重写单（改-n，非方向文件；要有「审核」岗位）：ok=true 换上（换前存档、旧版进归档），false 不要；why 写理由。"""
        import rewrite
        c = conn()
        try:
            x = rewrite.review(c, project, code, ok, why, by=me(ctx, agent))
        except store.Refused as e:
            return f"没审：{e}"
        finally:
            c.close()
        return f"{code} {'换上了，旧版在 ' + x['old_version'] if x['state'] == '换上了' else '不要了'}。"

    @mcp.tool()
    def pick_fruit(code: str, branch: str, why: str, agent: str = "", ctx: Context | None = None) -> str:
        """挑果实（档位 3、4 的比较单，比-n）：同一件在几根枝上各做了一版，看过 demo、检查、branch_changes 后挑最好的一根合回（branch 写枝号），
        没挑中的砍掉进 .回收；都不行 branch 写空、why 写哪里不对，全部打回接着做。不能挑自己做的。设置里「挑完等你点」时只记下挑了哪根。"""
        import branching
        c = conn()
        try:
            g = branching.pick(c, project, code, branch.strip(), why, by=me(ctx, agent))
        except store.Refused as e:
            return f"没挑：{e}"
        finally:
            c.close()
        if g["state"] == "合了":
            return f"{code} 合了 {g['pick']}（合前 {g['merged']['before']}、合完 {g['merged']['after']}），其余的砍了。"
        if g["state"] == "等你点合":
            return f"{code} 挑了 {g['pick']}，设置里是「挑完等你点」：等人点合。"
        return f"{code} 都打回了，枝接着长：{why}"

    @mcp.tool()
    def reject_fruit(branch: str, why: str, ctx: Context | None = None) -> str:
        """G1 验收不过：打回果实，枝接着长（写清哪里不对、要怎么改；枝上的 agent 看 world_tree 就看得到）。"""
        import worldtree
        c = conn()
        try:
            worldtree.reject(c, project, branch, by=who(ctx), why=why)
        except store.Refused as e:
            return f"没打回：{e}"
        finally:
            c.close()
        return f"{branch} 打回了，接着长：{why}"

    @mcp.tool()
    def cut_branch(branch: str, why: str, ctx: Context | None = None) -> str:
        """砍掉一根枝（验收不过、方向不对）：停后台，文件夹挪到世界树的 .回收（能拿回来），记录留着。"""
        import worldtree
        c = conn()
        try:
            b = worldtree.cut(c, project, branch, by=who(ctx), why=why)
        except store.Refused as e:
            return f"没砍：{e}"
        finally:
            c.close()
        return f"{branch} 砍了，文件夹在 {b['path']}。"

    @mcp.tool()
    def add_log(text: str, kind: str, scope: str = "总览", agent: str = "", ctx: Context | None = None) -> str:
        """往日志记一条（机器记的那本，笔记/日志/），记成你（agent）的名字。用于戒律要求记下的事，比如 kind「改了核心」。
        人的笔记只放人写的，你不往里记；转圈的流水账进自动化日志（report_run），问题进答疑（find_answer / ask_human）。
        scope: 跟哪个模块有关：「总览」或某个模块名"""
        c = conn()
        try:
            e = journal.add(c, project, text, by=me(ctx, agent), kind=kind, scope=scope)
        except store.Refused as e2:
            return f"没记上：{e2}"
        finally:
            c.close()
        return f"已记为 {e['id']}（笔记/日志/{e['at'][:7]}.md）。"

    @mcp.tool()
    def list_skills() -> str:
        """本项目自带的技能（写给 agent 的做法说明）：名字、什么时候用、在哪。正本就在项目里，不用装，哪家 agent 都能用。
        开始一件事前看一眼，用得上的用 read_skill 读全文照做。项目根 AGENTS.md 里也有同一张目录（没有这个工具的 agent 看那张）。"""
        items = skills.catalog(project)
        if not items:
            return "这个项目还没有技能（技能库/<名>/SKILL.md，或 资料/<模块>/技能/SKILL.md）。"
        return "\n".join(f"- {s['id']} · {s['name']}" + (f"（{s['module']} 模块专属）" if s["module"] else "")
                         + f"：{s['when']}（{s['path']}）" for s in items)

    @mcp.tool()
    def read_skill(name: str, language: str = "zh-CN") -> str:
        """读一份技能的全文（SKILL.md），外加它文件夹里还有哪些文件（参考、模板……要用时按路径读）。
        name：list_skills 里的名字，如「自动化科研交互界面」「文献」"""
        try:
            s = skills.read(project, name, language)
        except KeyError:
            return f"没有「{name}」这份技能。先用 list_skills 看有哪些。"
        extra = s.get("support_files", [])
        tail = ("\n\n---\n配套文件：" + "、".join(extra[:50])) if extra else ""
        warning = "\n\n缺项：" + "；".join(s["issues"]) if s.get("issues") else ""
        fallback = "\n\n" + s["language_fallback"] if s.get("language_fallback") else ""
        if s["kind"] == "link":
            return "# 外部参考（未内置）\n\n" + s["name"] + "\n" + s["text"] + "\n" + s.get("source", {}).get("url", "") + warning
        return f"# {s['path']}\n\n{s['text']}{fallback}{warning}{tail}"

    @mcp.tool()
    def list_skill_catalog(business: str = "") -> dict:
        """与网页同读本项目普通文件技能清单。返回业务阶段、唯一编号、中文英文路径、来源许可和实际缺项。
        business 可选清单返回的业务 id；空值返回全部。只读，不下载、安装、启动或执行。"""
        data = skills.inventory(project)
        if not business:
            return data
        groups = [g for g in data["groups"] if g["id"] == business]
        if not groups:
            raise ValueError("没有这个业务，请从 list_skill_catalog 返回的 groups 选择")
        items = [s for s in data["items"] if s.get("business") == business]
        ids = {s["id"] for s in items}
        return {**data, "groups": groups, "items": items, "issues": [i for i in data["issues"] if i["id"] in ids]}

    @mcp.tool()
    def read_skill_entry(id: str, language: str = "zh-CN") -> dict:
        """按 list_skill_catalog 的完整 id 读双语全文、来源许可、配套和版本，与网页一致。
        language 为 zh-CN 或 en；同名歧义明确拒绝，缺项和语言回退不伪称可用。只读。"""
        return skills.read(project, id, language)

    @mcp.tool()
    def read_log(limit: int = 30) -> str:
        """读日志（机器记的）：最近的操作——人在网页上点了什么（装技能、存档、删模块、拍板、验收……）、agent 做了什么（改了核心……）。
        人自己写的想法和要求在笔记里，用 read_notes。"""
        es = journal.recent(project, min(max(limit, 1), 300))
        if not es:
            return "日志还是空的（笔记/日志/）。"
        return "\n".join(f"- {e['id']} · {e['at']} · {e['by']} · {e['kind']} · {e['scope']}：{e['body']}" for e in es)

    @mcp.tool()
    def list_tool_guides() -> dict:
        """内置应用安装与调用指南清单：用途、官方地址、来源版本和显式 tool/agent/plugin 关联。
        与网页工具总览同读普通文件；不是安装状态，不执行清单或指南里的命令。"""
        return tool_guides.listing(project.root)

    @mcp.tool()
    def read_tool_guide(key: str = "", path: str = "", route: str = "") -> dict:
        """读一份工具指南全文、revision 与合法内置引用。key 取 list_tool_guides 的 id；
        或用 path 读取返回的 resources 中 document target，两者只选一个。
        route 可选为清单明确记录的国内/国外方案 id，仅与 key 同用；默认仍读完整指南。
        与网页同一正本；只读，不自动下载/安装/启插件/启动 agent。"""
        if bool(key) == bool(path):
            raise ValueError("key 和 path 只填写一项")
        if route and path:
            raise ValueError("route 只能与 key 同用")
        return tool_guides.read(project.root, key, route) if key else tool_guides.document(project.root, path)

    @mcp.tool()
    def list_tools() -> str:
        """外部工具怎么调：工具库/ 里每个工具一张卡（T1、T2…），写死了命令、输入输出、要守的戒律、常见坑。
        要用 LaTeX、draw.io、Git、Python 这类外部工具之前先调这个，照卡片调。
        没登记的工具：先在 工具库/ 写一张卡（抄一张现有的改，编号用下一个 T 号，号不回收），再用。"""
        items = tools.list_tools(project.root / "工具库")
        if not items:
            return f"工具库是空的（{project.root / "工具库"}）。"
        out = [f"工具库在 {project.root / "工具库"}，共 {len(items)} 张卡。本机 PATH 可能有乱码：命令找不到时用卡上「在哪」里的完整路径。", ""]
        for t in items:
            out += [f"# {t['code']} {t['name']}（{t['kind']}）：{t['one_line']}",
                    f"在哪：{t['where'] or '（PATH 里）'}" + (f" · 配套技能：{t['skill']}" if t["skill"] else ""),
                    t["body"].strip(), ""]
        return "\n".join(out)

    @mcp.tool()
    def list_plugins() -> str:
        """插件（插件/ 里一套一个）：有哪些、这台电脑能不能用（缺不缺外部程序）、这个项目启用了没有、怎么装（插件.md 正文）。
        要用插件做事前先调；没装好的照「怎么装」装——装之前先问人（工-3）；启用只有人在网页上点。"""
        import plugins
        items = plugins.list_plugins()
        if not items:
            return f"还没有插件（{plugins.DIR}）。"
        c = conn()
        try:
            out = [f"插件在 {plugins.DIR}，共 {len(items)} 个。", ""]
            for x in items:
                ck = plugins.check_cached(x["name"])
                state = ("这台电脑能用" if ck["ok"] else f"缺外部程序：{ck['msg']}") + (" · 这个项目启用了" if plugins.enabled(c, x["name"]) else " · 这个项目没启用（人在网页上点）")
                out += [f"# {x['name']}（版本 {x['version'] or '—'}）：{x['one_line']}", state, x["body"].strip(), ""]
            return "\n".join(out)
        finally:
            c.close()

    @mcp.tool()
    def list_repos() -> str:
        """开源项目（工具页「开源项目」，O1、O2…）：名字、许可证、能不能借、状态、带什么、一句话、有没有解读。
        借代码前一定看「能不能借」：能抄 = 宽松许可证，抄了要署名、写进 第三方许可证.md（工-2）；只借思路 / 不许抄 = 只学思路，不抄代码、不带进应用（工-1）。"""
        import repos
        xs = repos.listing()
        if not xs:
            return "还没有开源项目。外部资料入口里的 GitHub 压缩包，人点「工具/开源项目」就收进来。"
        return "\n".join([f"开源项目 {len(xs)} 个（卡在 工具库/开源项目/，原件在 工具库/开源项目/原件/，不进 git）：", ""]
                         + [f"- {x['code']} {x['name']} · {x['license'] or '没许可证'} → {x['borrow']} · {x['state']} · 带：{x['has'] or '—'} · {'有解读' if x['notes'] else '还没解读'}"
                            f"\n  {x['one_line']}" + (f"\n  {x['link']}" if x["link"] else "") for x in xs])

    @mcp.tool()
    def read_repo(code: str) -> str:
        """读一个开源项目：卡片全文、解读、压缩包里有哪些文件（只读，不解开）、说明（README）开头。code 如「O3」。
        要细看某个文件用 read_repo_file。"""
        import repos
        import zips
        x = next((r for r in repos.listing() if r["code"] == code), None)
        if x is None:
            return f"没有 {code}。先 list_repos 看有哪些。"
        out = [f"# {x['code']} {x['name']}", f"许可证：{x['license'] or '没许可证'} → 能不能借：{x['borrow']}" + ("（红灯：只借思路，不抄代码，工-1）" if x["borrow"] != "能抄" else "（能抄：要署名，写进 第三方许可证.md，工-2）"),
               f"链接：{x['link'] or '—'} · 带：{x['has'] or '—'} · 原件：{x['raw']}", "", x["body"].strip(), ""]
        out += ["## 解读", x["notes"].strip() if x["notes"] else "（还没有：看完用 write_repo_notes 写）", ""]
        raw = project.root / x["raw"]
        if raw.is_file():
            try:
                e = zips.entries(raw)
                tops = sorted({i["name"].split("/", 1)[0] + ("/" if "/" in i["name"] else "") for i in e["items"]})
                out += [f"## 里面有什么（{e['total']} 个文件，最上面一层）", "、".join(tops[:80])]
                if e["readme"]:
                    out += ["", f"## {e['readme']}（前 6000 字）", zips.read(raw, e["readme"]).get("text", "")[:6000]]
            except Exception as err:
                out += [f"（压缩包读不出来：{type(err).__name__}）"]
        else:
            out += ["（原件不在这台电脑上：只有卡和解读）"]
        return "\n".join(out)

    @mcp.tool()
    def read_repo_file(code: str, path: str) -> str:
        """读开源项目压缩包里的一个文件（只读，不解开；最多 200 KB）。path 是压缩包里去掉最外层文件夹后的路径，如「src/server.py」。"""
        import repos
        import zips
        x = next((r for r in repos.listing() if r["code"] == code), None)
        if x is None:
            return f"没有 {code}。"
        raw = project.root / x["raw"]
        if not raw.is_file():
            return "原件不在这台电脑上。"
        try:
            f = zips.read(raw, path)
        except FileNotFoundError:
            return f"{code} 里没有「{path}」。read_repo 看有哪些文件。"
        if f["kind"] != "text":
            return f"「{path}」是{'图片' if f['kind'] == 'image' else '二进制文件'}（{f['size']} 字节），读不出文字。"
        return f"{code} · {path} · 许可证 {x['license'] or '没许可证'} → {x['borrow']}\n\n" + f["text"] + ("\n\n（太大，只给了前 200 KB）" if f.get("truncated") else "")

    @mcp.tool()
    def write_repo_notes(code: str, text: str, agent: str = "", ctx: Context | None = None) -> str:
        """写一个开源项目的解读（工具 S2-6）：它干什么 · 我们能借什么 · 怎么用（借思路 / 抄代码 / 装成插件 / 装成技能 / 装成 MCP）。
        整份换掉旧的（旧的 git 里有）；网页上那张卡下面就看得到。红灯的项目写「只借思路」，不写抄代码的办法。"""
        import repos
        try:
            x = repos.write_notes(code, text, by=me(ctx, agent))
        except store.Refused as e:
            return f"没写上：{e}"
        c = conn()
        try:
            with store.tx(c):
                store.log(c, me(ctx, agent), "写开源项目解读", code, x["name"])
        finally:
            c.close()
        return f"{code} {x['name']} 的解读写好了（{x['notes_file']}）。"

    @mcp.tool()
    def list_inbox() -> str:
        """看外部资料入口（资料/_外部资料入口/）里等分拣的文件：编号、名字、大小、现有候选，文字文件附前 40 行。
        看完有把握的用 sort_inbox_item 直接放进模块（写一句原因）；拿不准的用 suggest_sorting 写候选，等人在网页上点。
        候选里 by=原位置 的是这个文件原来在的地方（从模块里移到入口的），放回去就是 sort_inbox_item 选它。
        治理模块和程序管的位置（见 sort_inbox_item）agent 放不进去，只写候选等人点。"""
        c = conn()
        try:
            store.get_state(c, project)            # 对一次账：人直接丢进文件夹的也登记上
            items = intake.waiting(c)
            mods = [m["name"] for m in store.list_folder_modules(c, project)]
        finally:
            c.close()
        if not items:
            return "外部资料入口是空的。"
        out = [f"现有模块：{'、'.join(mods)}", f"待分拣 {len(items)} 个（文件在 资料/{proj.INBOX}/）", ""]
        for it in items:
            cand = "；".join(f"{x['module']}{'/' + x['folder'] if x.get('folder') else ''}（{x['conf']}，{x['by']}：{x['reason']}）"
                            for x in it["candidates"]) or "还没有"
            out += [f"## #{it['id']} {it['name']}（{it['size']} 字节，原名 {it['orig']}）", f"现有候选：{cand}"]
            path = intake.inbox_dir(project) / it["name"]
            if files.kind_of(path) == "text":
                with open(path, "rb") as f:
                    text, _ = files._decode(f.read(8000), True)
                out += ["```", "\n".join(text.splitlines()[:40]), "```"]
            else:
                out.append(f"（{files.kind_of(path)} 文件，要看内容请自己打开 资料/{proj.INBOX}/{it['name']}）")
            out.append("")
        return "\n".join(out)

    @mcp.tool()
    def suggest_sorting(item: int, candidates: list[dict], ctx: Context | None = None) -> str:
        """给外部资料入口的一个文件写分拣候选，网页上那张卡会马上显示，人从里面点一个。

        item: list_inbox 里的编号（#后面的数字）
        candidates: 1~3 个，按把握从高到低，每个 {"module": 已有模块名, "folder": 模块里的文件夹（可空，从模块根算，如「原文」「正文/引言」）,
                    "confidence": "高"/"中"/"低", "reason": 一句理由}
        理由要让人一看就能判断（比如「第一页有作者和期刊名」），不要写百分比。能看出该放进模块里哪个文件夹就写上 folder（作者 10-07：「资料入口可以分配到具体模块的具体文件夹」）。
        把握高的也可以直接 sort_inbox_item 放进去（写一句原因）。移到入口的文件记着的「原位置」候选会留在最前面。
        """
        by = who(ctx)
        c = conn()
        try:
            it = intake.suggest(c, item, candidates, by=by, p=project)
        except store.Refused as e:
            return f"没写上：{e}"
        finally:
            c.close()
        n = len([x for x in it["candidates"] if x.get("by") != intake.ORIGIN])
        return f"已给 #{item}「{it['name']}」写了 {n} 个候选，等人在网页上点。"

    @mcp.tool()
    def sort_inbox_item(item: int, module: str, reason: str, folder: str = "", ctx: Context | None = None) -> str:
        """把外部资料入口的一个文件放进模块（跟人在网页上点「放这里」一样）：挪进 资料/<模块>/ 或模块里的 folder，同名不覆盖。
        item: list_inbox 里的编号（#后面的数字）
        module: 已有模块名；放回原处就写候选里 by=原位置 的那个模块和 folder
        reason: 一句为什么放这里（必填，跟谁放的一起记进日志）
        folder: 模块里的文件夹（可空，从模块根算，如「原文」「正文/引言」；没有就建）
        拿不准的别放，用 suggest_sorting 写候选等人点。压缩包放进开源项目请人在网页卡上点。
        agent 放不进去、要人在网页上点的位置：想法 · 蓝图 · 戒律 · 源代码 模块；模块根上的 需求/蓝图/戒律/下载清单/想法.md；
        技能/、解读/；内置/、历史/、工作台/ 和缓存文件夹；链接文件夹；点开头的隐藏文件。"""
        if module == intake.OSS:
            return "没放：压缩包放进开源项目请人在网页卡上点"
        c = conn()
        try:
            r = intake.place(c, project, item, module, folder=folder, by=who(ctx), reason=reason)
        except store.Refused as e:
            return f"没放：{e}"
        finally:
            c.close()
        return f"已放进 资料/{r['item']['sorted_to']}（#{item}，日志 {r['log_id'] or r.get('warning', '没记上')}）。"

    @mcp.tool()
    def move_to_inbox(path: str, reason: str, ctx: Context | None = None) -> str:
        """把 资料/<模块>/ 里放错地方的一个普通材料挪回外部资料入口（资料/_外部资料入口/）重新分拣——跟网页阅读页「移到入口」按钮一样的检查。
        挪、不复制；原来在哪记成一个「原位置」候选，sort_inbox_item 选它就放回原处。
        不收的：想法 · 蓝图 · 戒律 · 源代码 里的文件、需求/任务/戒律/下载清单、工作台、历史、技能/、文献解读记录、
        隐藏文件、标了内置的、被 .链接.txt 挂着的。这不是删除：要删用 move_to_trash（只照人的删除请求做）。
        path: 从项目根算，如「资料/文献/放错的稿子.md」
        reason: 为什么挪回入口（必填，跟谁挪的一起记进日志）"""
        import file_actions
        c = conn()
        try:
            r = file_actions.move_to_inbox(c, project, path, by=who(ctx), source=file_actions.MCP, reason=reason)
        except store.Refused as e:
            return f"没挪：{e}"
        finally:
            c.close()
        back = r["back"]["module"] + (f"/{r['back']['folder']}" if r["back"]["folder"] else "")
        return (f"已挪到外部资料入口：{r['from']} → {r['to']}（#{r['item']['id']}，日志 {r['log_id'] or r.get('warning', '没记上')}）。"
                f"原位置 {back} 记成候选；要放回就 sort_inbox_item({r['item']['id']}, …)")

    @mcp.tool()
    def read_notes() -> str:
        """读人的笔记本：上次复制给你以后新记的条目（带编号，按模块），人正在写还没记下的草稿，最近导出的指令。
        笔记文件在项目根的 笔记/ 文件夹里，一个模块一本；复制过的都在 笔记/历史/。"""
        c = conn()
        try:
            names = [m["name"] for m in store.list_folder_modules(c, project)]
            fresh = notebook.since_last_copy(c, project, names)
            d = store.get_draft(c)
            ins = store.list_instructions(c, 3)
        finally:
            c.close()
        out = ["## 笔记本里新记的（上次复制以后）"]
        out += [f"- [{e['scope']}] {e['id']} · {e['at']} · {e['by']} · {e['kind']}：{e['body']}" for e in fresh] or ["（没有新的）"]
        out += ["", "## 人正在写、还没记下的"]
        out += [d["text"].strip() or "（空的）"]
        if d["updated_at"]:
            out.append(f"（最后改于 {d['updated_at']}）")
        out += ["", "## 最近导出的指令"]
        for i in ins:
            out += [f"### {i['created_at']}", i["text"].strip(), ""]
        if not ins:
            out.append("（还没导出过）")
        return "\n".join(out)

    import automation_mcp
    automation_mcp.attach(mcp, project, conn, me, configuration_authorization=_CONFIG_AUTH, runner_control=_RUNNER_CONTROL)
    return mcp


def main() -> None:
    ap = argparse.ArgumentParser(description="自动化科研交互界面 · 给 agent 的 MCP 入口")
    ap.add_argument("--project", help=argparse.SUPPRESS)          # 只给自动测试用
    ap.add_argument("--agent", help="网页员工连接的固定身份")
    ap.add_argument("--configuration-authorization", help=argparse.SUPPRESS)
    ap.add_argument("--runner-control", action='store_true', help=argparse.SUPPRESS)
    args = ap.parse_args()
    global _BOUND, _CONFIG_AUTH, _RUNNER_CONTROL
    _BOUND = agents.short(args.agent) if args.agent else ""
    _CONFIG_AUTH = args.configuration_authorization or ''
    _RUNNER_CONTROL = args.runner_control
    project = resolve(args.project)
    proj.ensure_skeleton(project)
    c = store.connect(project.db_path)
    store.migrate(c)
    c.close()
    build(project).run()                        # stdio；标准输出只走协议，别往里 print


if __name__ == "__main__":
    main()
