<div align="center">

<img src="https://raw.githubusercontent.com/tmdysx/agent-research-workbench/main/%E5%93%81%E7%89%8C/miracleharness2-hero.png" alt="MiracleHarness 封面插画：白玉圆台上的玉树托着三个玻璃球" width="760">

<sub>封面是 AI 生成的概念插画，不是界面截图。</sub>

# Agent 科研自动工作台 · MiracleHarness

**人定方向，agent 做事：一个本地运行的科研工作台。**<br>
目标、需求、计划、规则和交付都存成本地普通文件，你自己选的 agent 照着干活。

**[下载 Windows 版 ZIP](https://github.com/tmdysx/agent-research-workbench/releases/latest/download/MiracleHarness2.zip)** · **[官网](https://miracleharness.com)** · **[English](README.en.md)** · **[使用说明](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.md)**

<sub>早期版本（2026-10-07 发行）· Windows 优先 · 源码公开、非商用免费（PolyForm Noncommercial 1.0.0），不是 OSI 开源</sub>

</div>

---

## 这是什么

- 一个在你自己电脑上运行的网页工作台：Python 后台加浏览器页面，后台只监听本机 `127.0.0.1`。
- **人定方向**：你在“蓝图”里写目标、需求和验收标准；计划、规则（戒律）、交付和交接都存成本地普通文件。
- **agent 做事**：干活的是你自己选的 agent（Claude Code、Codex、Cursor、Qwen Code、Trae 等）。它们读同一份文件，也可以通过可选的本地 MCP 服务读写。
- 平台本身不调用模型，也不需要模型 API Key；agent 的账号、额度和费用由你自己决定。
- 科研是主入口；同一套东西也能用来写小说、做宣传片和其他长期 DIY 项目。

> **名字说明**：仓库展示名是“Agent 科研自动工作台 · MiracleHarness”，发行包叫 **MiracleHarness2**，文件里也叫“自动化科研交互界面”，MCP 服务名是 `research-console`。它们指的是同一个东西。

## 科研全流程

**科研路线**（先判断现在到哪一步）→ 选题与假设 → 文献与证据 → 数据与实验设计 → 复现与运行 → 结果分析与图表 → 论文写作与引用 → 投稿准备 → 返修与回复<br>
<sub>配套：汇报与交流 · 素材与成果展示</sub>

| 阶段 | 做什么 | 技能 / 方法卡 |
|---|---|---|
| 科研路线（总入口） | 判断现在做到哪一步，写路线卡，排出下一件事、预算和停止条件；换 agent 也能接手。不要求从头重做已有工作。 | [research-route](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-route/SKILL.md) · [路线卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-route/assets/%E8%B7%AF%E7%BA%BF%E5%8D%A1.md) |
| 选题与假设 | 把兴趣或观察变成有证据边界、可反驳预测和可行性说明的选题。候选假设不当成发现。 | [research-topic](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-topic/SKILL.md) · [选题卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%83%B3%E6%B3%95/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/%E9%80%89%E9%A2%98%E5%8D%A1.md) |
| 文献与证据 | 写检索记录、文献比较和论断证据表，分清“来源存在”和“来源真的支持这个论断”。 | [research-literature-evidence](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-literature-evidence/SKILL.md) · [文献证据表](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-literature-evidence/assets/%E6%96%87%E7%8C%AE%E8%AF%81%E6%8D%AE%E8%A1%A8.md) · [下载列表](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E4%B8%8B%E8%BD%BD%E6%B8%85%E5%8D%95.md) |
| 数据与实验设计 | 把论断变成实验方案：数据权限、无泄漏的划分、公平基线、评价指标和预算。主要面向计算与机器学习研究。 | [research-experiment-design](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-experiment-design/SKILL.md) · [实验设计卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E5%AE%9E%E9%AA%8C/%E6%96%B9%E6%B3%95/%E5%AE%9E%E9%AA%8C%E8%AE%BE%E8%AE%A1%E5%8D%A1.md) · [数据分割卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E6%95%B0%E6%8D%AE%E5%88%86%E5%89%B2%E5%8D%A1.md) |
| 复现与运行 | 在获准资源内复现基线、跑计算实验，保存命令、版本、原始结果和失败记录。不会替你启动模型或租用算力。 | [research-reproduce-run](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-reproduce-run/SKILL.md) · [实验运行卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E5%AE%9E%E9%AA%8C/%E6%96%B9%E6%B3%95/%E5%AE%9E%E9%AA%8C%E8%BF%90%E8%A1%8C%E5%8D%A1.md) |
| 结果分析与图表 | 从真实结果算出可复算、可追溯的比较和图表，写清论断成立的范围、局限和负结果。不编数据。 | [research-results-figures](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-results-figures/SKILL.md) · [分析与图表卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E5%88%86%E6%9E%90%E4%B8%8E%E5%9B%BE%E8%A1%A8%E5%8D%A1.md) · [字段来源卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E5%AD%97%E6%AE%B5%E6%9D%A5%E6%BA%90%E5%8D%A1.md) |
| 论文写作与引用 | 依据真实方法、结果和可定位的文献写论文，核对引用和数值是否一致。论文工作台按九章分区。 | [research-manuscript-citations](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-manuscript-citations/SKILL.md) · [论文证据卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95/%E8%AE%BA%E6%96%87%E8%AF%81%E6%8D%AE%E5%8D%A1.md) · [引用核验卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95/%E5%BC%95%E7%94%A8%E6%A0%B8%E9%AA%8C%E5%8D%A1.md) · [论文工作台](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E5%B7%A5%E4%BD%9C%E5%8F%B0) |
| 投稿准备 | 查目标期刊当前的官方要求，在本地做好投稿包和声明缺口清单。不登录、不上传、不付款、不自动提交。 | [research-submission-package](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-submission-package/SKILL.md) · [投稿检查清单](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%8A%95%E7%A8%BF%E4%B8%8E%E8%BF%94%E4%BF%AE/%E6%96%B9%E6%B3%95/%E6%8A%95%E7%A8%BF%E6%A3%80%E6%9F%A5%E6%B8%85%E5%8D%95.md) |
| 返修与回复 | 把审稿意见逐条对应到修改、补做的实验、正文位置和有依据的回复。保留原意见，不自动发送。 | [research-revision](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-revision/SKILL.md) · [返修回复卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%8A%95%E7%A8%BF%E4%B8%8E%E8%BF%94%E4%BF%AE/%E6%96%B9%E6%B3%95/%E8%BF%94%E4%BF%AE%E5%9B%9E%E5%A4%8D%E5%8D%A1.md) |
| 配套：汇报与交流 | 讲清问题、方法、真实结果、局限和下一步。没有专门的 research-\* 技能，用汇报卡和 PPT 技能（材料 → 大纲 → 幻灯片 → 导出 → 检查）。 | [PPT汇报卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%B1%87%E6%8A%A5/%E6%96%B9%E6%B3%95/PPT%E6%B1%87%E6%8A%A5%E5%8D%A1.md) · [PPT 技能](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/PPT/%E6%8A%80%E8%83%BD/SKILL.md) |
| 配套：素材与成果展示 | 记录图、表、截图的来源、权限和用途，定量图必须来自真实数据。PPT 的“成果展示”区直接列出导出的 PPTX/PDF。 | [素材来源卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E7%B4%A0%E6%9D%90/%E6%96%B9%E6%B3%95/%E7%B4%A0%E6%9D%90%E6%9D%A5%E6%BA%90%E5%8D%A1.md) · [图表交付卡](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E7%B4%A0%E6%9D%90/%E6%96%B9%E6%B3%95/%E5%9B%BE%E8%A1%A8%E4%BA%A4%E4%BB%98%E5%8D%A1.md) · [PPT 导出](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/PPT/%E5%AF%BC%E5%87%BA) |

- 先读 [从选题到投稿：先看这页](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/README.md)。
- 这 9 个中文技能（1 个路线入口加 8 个阶段）改编自 ARIS 以及 K-Dense 的 scientific-agent-skills 和 claude-scientific-writer，单独采用 MIT 许可，来源见 [改编与未内置清单](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/%E6%94%B9%E7%BC%96%E4%B8%8E%E6%9C%AA%E5%86%85%E7%BD%AE%E6%B8%85%E5%8D%95.md)。另附 82 个 ARIS 论文方法入口（附上游原文和 MIT 许可），平台不会自动运行它们。
- 主要面向计算 / 机器学习研究。真实医学、动物或湿实验需要另用该领域的协议，这些技能不覆盖。
- 模板不是科研结果。“自动验收”只表示交付里列出的检查都通过了，不代表结论成立，也不代表能发表。

## 核心能力

| 能力 | 说明 |
|---|---|
| **多 Agent 接入** | 任何能读文件的 agent 都可以先读 `AGENTS.md` 再开工。可选的本地 MCP 服务 `research-console` 提供 73 个工具（报到、看全貌、领活、交付、存档、向人提问等）。平台本身不调用模型。 |
| **蓝图治理** | S0 总目标 → S1 → S2 任务；需求写明验收标准；计划按 P 号存档；戒律分通用、项目、模块三层；交付单 J、交接单 H 都是普通文件。网页和 MCP 读写同一份文件，用版本号防止互相覆盖。 |
| **自动化面板** | 项目 → 目标 → 任务关系图、四列任务看板、agent 名册（岗位、等级、上级）、员工分配图、可保存 / 校验 / 演练 / 启用的流程编辑器，以及 7 条监管规则（例如改核心先拿锁、删除先进回收站）。交付按 checks-pass：检查全部通过才自动验收。全自动开工必须由人打开，目前只能驱动本机 Codex CLI。 |
| **文献阅读与内容工作台** | 文献库用 L 编号把原文和解读对应起来；PDF 阅读页可以高亮、贴纸、画笔批注，选中原句记笔记或问 agent。网页内能预览压缩包、音视频、Excel、Word 和 PPT 文字。论文、测试、PPT、宣传片都有分区的普通文件工作台。 |
| **存档、世界树与回收站** | 每过一关存一档，相同内容只存一份，可以对比、复活单个文件或整份回去。可以从任意一档长出世界树分支（独立项目），再用三方合并合回主干。删除先进回收站（X 编号，可还原）。另有带进度条的全量备份。 |
| **笔记、便签与问答** | 按 N 打开便签；笔记本有编号，改或删之前原文先存进 `笔记/历史/`，机器日志单独存放；问答是双向的：agent 问你，你也能问 agent。截图和录屏借用 Windows 截图工具，截完可以标注。阅读、详情、终端窗可以收成三色火苗小按钮。 |
| **代码地图与编程工作台** | 把整个项目铺成能缩放的方块图：远看是按语法上色的细线，拉近能读代码；可以按类型、最近改动、git 改动次数上色，并有重要性金字塔。编程工作台把任务的需求、戒律、批准计划和技能整理成一份只读工作包，可以复制给 agent。 |
| **外观** | 4 套皮肤（首次默认“玉色科技”）、3 套导航图标、5 张可选壁纸、亮 / 暗两档，界面语言可选中文、中英对照或 English。 |

## 支持哪些 Agent，怎么接入

平台不调用模型，也不需要模型 API Key；干活的是你自己选的 agent，账号、额度和费用自理。有三种接法：

| 接法 | 适用 | 怎么做 |
|---|---|---|
| ① 读普通文件 | 任何能读文件的 agent | 先读 [`AGENTS.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/AGENTS.md) 和 [`技能库/自动化科研交互界面/SKILL.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/%E8%87%AA%E5%8A%A8%E5%8C%96%E7%A7%91%E7%A0%94%E4%BA%A4%E4%BA%92%E7%95%8C%E9%9D%A2/SKILL.md)，按 [`自动化/协议.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%87%AA%E5%8A%A8%E5%8C%96/%E5%8D%8F%E8%AE%AE.md) 干活。Claude Code 通过 [`CLAUDE.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/CLAUDE.md) 自动读到 `AGENTS.md`。 |
| ② 本地 MCP（可选） | 支持 stdio MCP 的客户端 | 服务 `research-console`（`python backend/mcp_server.py`），73 个工具，例如 `register_agent`、`get_overview`、`next_task`、`deliver`、`save_checkpoint`、`ask_human`。[`.mcp.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/.mcp.json) 供 Claude Code 等兼容客户端读取；其他客户端按 [Agent 接入指南](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B7%A5%E5%85%B7%E5%BA%93/%E5%AE%89%E8%A3%85%E6%8C%87%E5%8D%97/Agent%E6%8E%A5%E5%85%A5.md) 手动填写“Python 绝对路径 + `backend/mcp_server.py --project <路径> --agent <名字>`”。**一键接入还没做。** |
| ③ 网页“员工”自动运行 | **目前只支持本机 Codex CLI** | 默认关闭。由人打开总开关后，本机 Python 运行器每轮启动一次 Codex CLI。 |

安装指南里有这些客户端的说明：Claude Code、Codex、Cursor、Qwen Code、Trae / TRAE CN、通义灵码 / Lingma、腾讯 WorkBuddy、腾讯 CodeBuddy、智谱 ZCode、DeepSeek Harness、阶跃 Step Code、Hermes Agent。[`工具库/智能体.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B7%A5%E5%85%B7%E5%BA%93/%E6%99%BA%E8%83%BD%E4%BD%93.md) 另列了美国 27 款、中国 19 款智能体。

> **说清楚几件事**
> - 智能体名录里的“能接本应用”是按各家官网是否支持 MCP 做的书面判断，仓库里没有逐个客户端的实连记录。
> - “不需要 API Key”只是说平台本身。DeepSeek Harness 的官方 Web UI 需要模型 API Key；已登录的 agent 用的是它自己的云端模型，所以不等于全部离线。
> - 自动运行只接 Codex；Cursor、Claude Code、国内客户端都没有接入自动运行器。

## 快速开始

### Windows（推荐）

1. **装 Python 3.12**：打开 [python.org 的 Windows 下载页](https://www.python.org/downloads/windows/)，找到 **Python 3.12.10**，点 “Windows installer (64-bit)”（项目按 3.12 系列测试；3.12.10 是 3.12 系列最后一个带 Windows 安装包的版本。不要点 python.org 首页的大按钮，那是更新的大版本）。安装第一页记得勾选 **“Add python.exe to PATH”**，再点 Install Now。
2. **下载并解压**：下载 **[MiracleHarness2.zip](https://github.com/tmdysx/agent-research-workbench/releases/latest/download/MiracleHarness2.zip)**，右键“全部解压缩”。Windows 默认会解压成两层同名文件夹（`MiracleHarness2\MiracleHarness2`），请一直点进去，直到能直接看到 `启动.bat` 和 `backend` 文件夹的那一层（共 1423 个文件）。在文件夹空白处**按住 Shift 再点右键**，选“在此处打开 PowerShell 窗口”（Windows 11 上叫“在终端中打开”；也可以在资源管理器地址栏输入 `powershell` 后回车）。
3. **装依赖**：在 PowerShell 窗口里运行：

   ```powershell
   py -3.12 -m pip install -r backend/requirements.txt "mcp>=1.20,<2" watchfiles
   ```

   > 后半段 `"mcp>=1.20,<2" watchfiles` 是给 2026-10-07 那版 ZIP 打的补丁：那版 `requirements.txt` 没给 `mcp` 设上限（新装会装到 mcp 2.x，MCP 服务和自动化模块一导入就报错），也没列 `watchfiles`（实时发现文件变化，缺了会退回轮询）。仓库里的 `backend/requirements.txt` 已经修好，多写这一段也无害。
4. **启动**：双击 **`启动.bat`**。它会自己找 Python、启动后台并打开浏览器。黑色窗口就是后台，关掉它就关了后端（数据在文件里，不会丢）；再双击一次不会多开。电脑里有多个 Python 时，它优先用 `%LOCALAPPDATA%\Programs\Python\Python312` 里的那个，依赖要装在同一个 Python 里。

网页地址默认是 `http://127.0.0.1:8770/`，端口被占用时会自动往后换，以黑窗口里显示的为准。网页默认先进入“蓝图”：写下目标、需求和验收标准，然后让你的 agent 先读 `AGENTS.md`。新建项目：双击 **`新项目.bat`**，或在网页点“新建项目”。

默认不启动员工、不启用插件。遇到问题先看[使用说明的“出问题怎么办”](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.md#%E5%87%BA%E9%97%AE%E9%A2%98%E6%80%8E%E4%B9%88%E5%8A%9E)。

### macOS / Linux（未正式支持）

仓库没有为 macOS / Linux 提供启动脚本或文档。2026-10-07 在 Linux 上实测：网页后台能启动，首页和接口都正常返回；**macOS 没有测试过**。可以在仓库或解压出的 `MiracleHarness2` 文件夹里这样尝试：

```bash
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
# 若用的是 2026-10-07 的 Release ZIP，改用下面这行（补丁同 Windows 第 3 步）：
# python3 -m pip install -r backend/requirements.txt "mcp>=1.20,<2" watchfiles
python3 backend/main.py           # 可选参数：--port 8770 --no-browser --no-reload
```

- `新项目.bat` 对应 `python backend/new_project.py`，没有在这些系统上单独验证过。
- 截图 / 录屏、全局快捷键、网页终端插件、PPT 预览脚本、员工开工用的 PowerShell 窗口都依赖 Windows。
- `.mcp.json` 里写的命令是 `python`；用虚拟环境或只有 `python3` 的系统，请改成解释器的绝对路径。

### 运行测试（可选）

```bash
python -m pytest backend/tests -q
node --test "backend/tests/*.js"   # 前端测试，用 Node 22 跑过；pytest 不会调用它们
```

完整测试目前还有已知失败，见下面“当前状态”。

## 目录导览

根目录是一份完整的发行副本。`资料/` 下的一个文件夹就是网页里的一个模块；带中文名的 `.js` 文件是网页界面的各个部分。

### 从这里开始

| 路径 | 是什么 |
|---|---|
| [`启动.bat`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%90%AF%E5%8A%A8.bat) | Windows 双击启动：自己找 Python，运行 `backend\main.py`，打开网页。 |
| [`新项目.bat`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%96%B0%E9%A1%B9%E7%9B%AE.bat) | Windows 双击新建项目：运行 `backend\new_project.py`，在你选的位置复制一份干净的应用。 |
| [`使用说明.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.md) · [`使用说明.en.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.en.md) | 用户手册：第一次使用、各页面怎么用、自动化、存档、设置和排错。很长，先看开头的“第一次使用”。 |
| [`AGENTS.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/AGENTS.md) | 写给所有 agent 的入门页：东西在哪、做事流程、戒律一行版。哪家 agent 都先读它。 |
| [`CLAUDE.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/CLAUDE.md) | 用 `@AGENTS.md` 让 Claude Code 自动读到 `AGENTS.md`。 |
| [`README.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/README.md) · [`README.en.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/README.en.md) | 发行包自带的简短说明。`README.md` 由 `backend/release.py` 生成；`README.md`、`README.en.md` 都记录在 `发行清单.json` 里，不要手改。你现在看的这页在 [`.github/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.github) 里。 |

### 程序

| 路径 | 是什么 |
|---|---|
| [`backend/`](https://github.com/tmdysx/agent-research-workbench/tree/main/backend) | Python 后台：FastAPI 网页服务 `main.py`、MCP 服务 `mcp_server.py`、员工运行器、发行脚本；`backend/tests/` 下有 87 个 Python 测试文件和 27 个 JS 测试文件。 |
| [`模板.html`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%A8%A1%E6%9D%BF.html) | 整个网页界面的主文件（单页、原生 JavaScript、无框架）。后台把它发给浏览器，它再加载下面这些 `.js`。 |
| [`治理界面.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%B2%BB%E7%90%86%E7%95%8C%E9%9D%A2.js) | “蓝图”里的治理全文、关联设置，以及人和 agent 共用的正文编辑器（网页里以 `governance-ui.js` 的地址加载）。 |
| [`内容工作台.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%86%85%E5%AE%B9%E5%B7%A5%E4%BD%9C%E5%8F%B0.js) | 文献、论文、测试、PPT、宣传片等模块里分区列出、新建和编辑普通文件。 |
| [`自动化面板.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%87%AA%E5%8A%A8%E5%8C%96%E9%9D%A2%E6%9D%BF.js) | 自动化总览的“项目 → 目标 → 任务”关系图。只读现有记录，不是调度器。 |
| [`员工分配图.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%91%98%E5%B7%A5%E5%88%86%E9%85%8D%E5%9B%BE.js) | 员工分配流程图。只展示已有档案、领活和运行记录，不派活、不启动员工。 |
| [`流程编辑器.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%B5%81%E7%A8%8B%E7%BC%96%E8%BE%91%E5%99%A8.js) | 编辑派活、审核、施工、验收、条件节点的流程草稿。保存和演练都不启动员工。 |
| [`代码地图.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BB%A3%E7%A0%81%E5%9C%B0%E5%9B%BE.js) | “源代码”模块：把全部源码铺成可缩放的方块图，并有重要性金字塔。 |
| [`小窗.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B0%8F%E7%AA%97.js) | 把阅读、详情、终端窗收成 30px 的三色火苗按钮，也负责“正在读取”的火苗动画。 |
| [`界面英文.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%95%8C%E9%9D%A2%E8%8B%B1%E6%96%87.js) | 界面英文对照表，设置 → 语言选 English 时使用。 |
| [`DESIGN.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/DESIGN.md) | 网页设计规范：三条导航布局、颜色、字体、组件和不要做的事。改界面前先读。 |

### 内容与模板

| 路径 | 是什么 |
|---|---|
| [`资料/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99) | 各业务模块的文件夹：想法、文献、实验、数据与分析、论文、投稿与返修、汇报、素材、PPT、写论文、写小说、宣传片、测试。里面是方法卡、模板和展示示例。 |
| [`治理/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%B2%BB%E7%90%86) | 治理文件夹。目前带通用戒律和空白的项目戒律；目标、需求、任务、计划由你在蓝图里写进来。 |
| [`自动化/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%87%AA%E5%8A%A8%E5%8C%96) | 人和 agent 的配合协议 `协议.md`、交付策略（checks-pass：检查全过就自动验收）和工作流卡 W1 自动推进。 |
| [`快捷指令/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%BF%AB%E6%8D%B7%E6%8C%87%E4%BB%A4) | 5 条一键提示词：交接给新 agent、分拣外部资料、整理本周进展、检查是否违反戒律、自动推进。 |
| [`索引/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E7%B4%A2%E5%BC%95) | 运行用的 SQLite 索引。随包的 `state.db` 只是用示例建的演示索引，第一次打开就能看到内容。 |

`AGENTS.md` 里提到的 `笔记/`、`存档/`、`回收站/`、`治理/目标/` 等目录发行包里还没有，第一次使用后由你在网页里写入或由程序创建。

### 技能与工具

| 路径 | 是什么 |
|---|---|
| [`技能库/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%8A%80%E8%83%BD%E5%BA%93) | 写给 agent 的做法说明：9 份中文科研技能（`research-*`，MIT）、平台用法、网页前端、交付自查，以及论文 / PPT 的上游方法包。 |
| [`工具库/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%B7%A5%E5%85%B7%E5%BA%93) | 外部工具卡 T1–T17、随包网页库（pdf.js、KaTeX、Mermaid、Three.js、SheetJS、docx-preview、JSZip、xterm）、国内外安装指南、智能体名录和网页链接。 |
| [`插件/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%8F%92%E4%BB%B6) | 三个可选插件，默认不启用：PPT预览（Windows，需要本机 PowerPoint 或 LibreOffice，借它转 PDF）、网页终端（仅 Windows）、剪辑（目前只有 FFmpeg 协议和命令卡）。 |

### 品牌与外观

| 路径 | 是什么 |
|---|---|
| [`品牌/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%93%81%E7%89%8C) | 作者原有的凤凰鸟标、4 张 AI 生成的用途插画（封面、终端、幻灯片、素材）和自绘按钮图标 `icons.svg`。 |
| [`外观/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%A4%96%E8%A7%82) | 可换外观：4 套皮肤 CSS、3 套导航图标、5 张可选壁纸、凤凰标志和自制皮肤说明。 |

`品牌/` 里的 4 张用途插画是 AI 生成的概念图，不是产品界面截图。

### 配置与清单

| 路径 | 是什么 |
|---|---|
| [`.claude/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.claude) | Claude Code 的项目设置（只有 `settings.json`），把 Claude Code 生成的计划存进 `治理/计划`。 |
| [`.mcp.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/.mcp.json) | 给支持 MCP 的客户端登记本地服务 `research-console`（`python backend/mcp_server.py`）。 |
| [`.gitignore`](https://github.com/tmdysx/agent-research-workbench/blob/main/.gitignore) | 不进 git 的东西：运行库、存档、回收站、文献 PDF、本机设置、大音视频和外部安装。 |
| [`模板配置.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%A8%A1%E6%9D%BF%E9%85%8D%E7%BD%AE.json) | 本发行包的模板配置（research）：带哪些业务模块、模块技能和内置技能编号。 |
| [`内置标记.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%86%85%E7%BD%AE%E6%A0%87%E8%AE%B0.json) | 新建项目时一起带走的“内置”路径清单（就是设置 → 内置里勾选的那份）。 |
| [`发行清单.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%8F%91%E8%A1%8C%E6%B8%85%E5%8D%95.json) | 由 `backend/release.py` 生成，记录 Release ZIP 中除它自己以外 1422 个文件（Windows 换行）的路径、大小与 sha256，与仓库里的文件不一定逐字节相同，要校验请拿 ZIP 对。 |
| [`新项目复制清单.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%96%B0%E9%A1%B9%E7%9B%AE%E5%A4%8D%E5%88%B6%E6%B8%85%E5%8D%95.json) | 这个项目被新建时复制进来的文件清单（路径和字节数）。 |
| [`.github/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.github) | GitHub 首页说明（就是这页）与贡献须知，不属于发行包。 |
| `.gitattributes` | 让 `.bat` 在 Windows 上保持 CRLF 换行。 |

### 许可

| 路径 | 是什么 |
|---|---|
| [`LICENSE`](https://github.com/tmdysx/agent-research-workbench/blob/main/LICENSE) | 原创部分采用的 PolyForm Noncommercial 1.0.0 官方原文。 |
| [`NOTICE`](https://github.com/tmdysx/agent-research-workbench/blob/main/NOTICE) | 版权声明、非商用免费说明和商业授权邮箱。 |
| [`第三方许可证.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%AC%AC%E4%B8%89%E6%96%B9%E8%AE%B8%E5%8F%AF%E8%AF%81.md) | 第三方许可清单：随包网页库、后台 Python 包、终端插件依赖、MIT 科研技能和上游方法包。 |

## 不止科研

| 用途 | 现在有什么 |
|---|---|
| 写小说 | [`资料/写小说/方法/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%86%99%E5%B0%8F%E8%AF%B4/%E6%96%B9%E6%B3%95) 有任务简报、章节接手和 7 段阶段路线：立项与读者 → 世界观与人物 → 分层大纲 → 正文与状态 → 一致性与首读 → 作者批准修订 → 接手与整稿。目前是流程模板，路线技能没有随包。 |
| 写论文 | 不走科研全流程也行：[`资料/写论文/方法/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%86%99%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95) 有任务简报、证据账本和阶段路线。 |
| 宣传片 / 视频 | [`资料/宣传片/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%AE%A3%E4%BC%A0%E7%89%87) 的工作台只分“素材”和“成果”两区；剪辑插件让 agent 按 FFmpeg 命令卡截段、拼接、加字幕。**网页剪辑器还没做**，宣传片的阶段技能也没有随包。 |
| PPT 演示 | [`资料/PPT/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/PPT) 有素材和成果展示两区；PPT 技能按受众 → 逐页计划 → 可编辑制作 → 检查 → 交付来做。随包的 23 页项目介绍 PPT/PDF 是示例。 |
| 其他 DIY 长期项目 | 通用模板不带业务材料，你自己建模块，定需求、规则和流程；科研只是可选示例。 |
| 管 agent 写代码 | 代码地图、编程工作台、核心锁和监管规则可以用来管理 agent 的软件开发。 |

## 当前状态

**早期版本**：核心还没固化，没有 1.0，也没有安装包。

**已经能用**

- 本地网页 + Python（FastAPI）后台：只监听 `127.0.0.1`，就绪后自动开浏览器，改了后台代码自动重启，文件一变网页一两秒内自己跟上。
- 本地 MCP 服务 `research-console`（73 个工具），网页和 agent 读写同一份文件。
- 蓝图（目标、需求与验收、计划、戒律）可以在网页直接编辑，按版本号检测冲突。
- 自动化面板：关系图、任务看板、agent 名册、员工分配图、流程编辑器、7 条监管规则、checks-pass 自动验收。
- 存档：内容去重、对比、复活、世界树分支和三方合并、回收站、全量备份。
- 文献库和 PDF 阅读页；网页内预览压缩包、音视频、Excel、Word 和 PPT。
- 笔记本、便签、机器日志、双向问答、截图 / 录屏及标注（借用 Windows 截图工具）。
- 代码地图和只读的编程工作台。
- 9 个中文科研技能和各模块方法卡、82 个 ARIS 论文方法入口（附上游原文和 MIT 许可）、PPT 技能。
- 两个可用插件：PPT预览（Windows，需要本机 PowerPoint 或 LibreOffice）、网页终端（仅 Windows，需要 pywinpty）。都要先装好，再由人启用。
- 工具安装指南：26 项软件分国内 / 国外两套方案，只在本机检查、不自动安装。
- 展示示例：23 页项目介绍 PPT/PDF、写小说和写论文的流程模板、一段历史宣传片、演示用索引。这些都是示例，不是你自己的研究成果。

**还没做 / 没验证**

- 网页剪辑器还没做（剪辑插件目前只有 FFmpeg 协议和命令卡）。
- 一键接入 agent 还没做，MCP 要手动配置。
- 网页“员工”自动运行只支持本机 Codex CLI。员工默认不启动，全自动开工总开关只能由人打开；“已允许自动开工”不等于员工正在跑。
- 真实科研任务、真实任务完成和在第二台电脑上安装都没有验证过。
- 完整测试还没全绿。2026-10-07 在 Linux 上，用修好的 `backend/requirements.txt` 在全新虚拟环境（Python 3.12）里安装依赖后运行（这次以 root 运行）：Python 测试 1072 通过、30 跳过（29 个是 Windows 专用，1 个因测试环境建不了链接）、24 失败。其中 17 个是测试与当前发行布局或模板不一致（旧 `内置/` 目录、已移除的 business 模板、发行时裁剪的内容），4 个是测试写死了 Windows 假设，3 个是只读索引测试（`test_work_packages.py`）在 root 下失败（同日另一次以普通用户运行时这 3 个通过）。JS 测试（Node 22）656 个里 653 个通过。Windows 上的完整结果还没复核。
- 2026-10-07 那版 Release ZIP 里的 `requirements.txt` 没有锁定 `mcp<2`、也没列 `watchfiles`；仓库里的已经修好，用那版 ZIP 安装时请用快速开始里的补丁命令。
- macOS / Linux 没有启动脚本，也没有文档；截图录屏、网页终端、PPT 预览脚本依赖 Windows。
- 世界树 3D 建模（Blender）暂停，只提供指南；“重生”功能的后续部分暂停或未做。
- 宣传片的阶段技能、写小说的路线技能没有随包。
- 明确不做：长截图、钉在桌面、识别图中文字、手机适配。

## 许可与商业授权

- 原创部分采用 **[PolyForm Noncommercial 1.0.0](https://github.com/tmdysx/agent-research-workbench/blob/main/LICENSE)**：个人学习、非商业研究等非商业用途免费，按许可原文执行。
- **商业使用（包括商业研究）需要作者另行书面授权**，联系 **3129746403@qq.com**。
- 源码公开，但这**不是 OSI 认可的开源许可证**。
- 第三方部分保持各自的许可：9 个中文科研技能及教材、ARIS / K-Dense / ppt-master 等上游内容为 MIT，随包网页库为 Apache-2.0、MIT 等。详见 [`第三方许可证.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%AC%AC%E4%B8%89%E6%96%B9%E8%AE%B8%E5%8F%AF%E8%AF%81.md) 和 [`NOTICE`](https://github.com/tmdysx/agent-research-workbench/blob/main/NOTICE)。
- PolyForm 许可不授予商标权。可以如实提及 MiracleHarness；未经书面许可，请不要把修改版、分支或其他产品说成官方 MiracleHarness 发行，也不要用凤凰鸟标作为它们的主要标识。
- 想参与改进？请看 [贡献指南](CONTRIBUTING.md)。

---

<div align="center">

作者 **Tianyi Hu** · MiracleHarness · [miracleharness.com](https://miracleharness.com)

</div>
