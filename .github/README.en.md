<div align="center">

<img src="https://raw.githubusercontent.com/tmdysx/agent-research-workbench/main/%E5%93%81%E7%89%8C/miracleharness2-hero.png" alt="MiracleHarness cover illustration: a jade tree on a marble dais holding three glass spheres" width="760">

<sub>The cover is AI-generated concept art, not a screenshot of the app.</sub>

# Agent Research Workbench · MiracleHarness

**People set direction; their chosen agents do the work.**<br>
A local web console, Python backend and optional MCP interface for long-running projects, where goals, requirements, plans, rules and deliveries stay in ordinary local files.

**[Download for Windows (ZIP)](https://github.com/tmdysx/agent-research-workbench/releases/latest/download/MiracleHarness2.zip)** · **[Website](https://miracleharness.com)** · **[中文](README.md)** · **[User guide](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.en.md)**

<sub>Early release (2026-10-07) · Windows first · Source-available, free for noncommercial use (PolyForm Noncommercial 1.0.0), not OSI open source</sub>

</div>

---

## What it is

- A workbench that runs on your own computer: a Python backend plus a browser page. The backend listens only on `127.0.0.1`.
- **People set direction**: you write goals, requirements and acceptance criteria in the Blueprint. Plans, rules, deliveries and handovers are saved as ordinary local files.
- **Agents do the work**: the agents you choose (Claude Code, Codex, Cursor, Qwen Code, Trae and others) read the same files, and can also read and write through an optional local MCP server.
- The platform itself never calls a model and needs no model API key. Your agents' accounts, quotas and costs are your own choice.
- Research is the main entry point. The same setup also works for novels, promo videos and other long-running DIY projects.

> **About the names**: the repository is shown as "Agent Research Workbench · MiracleHarness" (Chinese: Agent 科研自动工作台). The release package is called **MiracleHarness2**; inside the files it is also called 自动化科研交互界面 ("automated research console"), and the MCP server is `research-console`. They are all the same thing.
>
> The interface can be switched to English (Settings → Language), but most folder and file names, and many method cards, are in Chinese.

## The research workflow

**Research route** (work out where you are first) → topic and hypothesis → literature and evidence → data and experiment design → reproduction and runs → results analysis and figures → manuscript and citations → submission preparation → revision and response<br>
<sub>Supporting: presentation and discussion · materials and showcase</sub>

| Stage | What happens | Skill / method cards |
|---|---|---|
| Research route (entry point) | Work out the current stage, fill a route card and plan the next task, budget and stop conditions, so another agent can take over. Existing work does not have to be redone. | [research-route](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-route/SKILL.en.md) · [route card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-route/assets/%E8%B7%AF%E7%BA%BF%E5%8D%A1.md) |
| Topic and hypothesis | Turn an interest or observation into a topic with evidence boundaries, falsifiable predictions and a feasibility note. Candidate hypotheses are not treated as findings. | [research-topic](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-topic/SKILL.en.md) · [topic card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%83%B3%E6%B3%95/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/%E9%80%89%E9%A2%98%E5%8D%A1.md) |
| Literature and evidence | Keep search logs, literature comparisons and a claim-evidence table, separating "the source exists" from "the source actually supports the claim". | [research-literature-evidence](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-literature-evidence/SKILL.en.md) · [evidence table (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-literature-evidence/assets/%E6%96%87%E7%8C%AE%E8%AF%81%E6%8D%AE%E8%A1%A8.md) · [download list (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E4%B8%8B%E8%BD%BD%E6%B8%85%E5%8D%95.md) |
| Data and experiment design | Turn claims into an experiment plan: data permissions, leakage-free splits, fair baselines, metrics and budget. Mainly for computational and machine-learning research. | [research-experiment-design](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-experiment-design/SKILL.en.md) · [design card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E5%AE%9E%E9%AA%8C/%E6%96%B9%E6%B3%95/%E5%AE%9E%E9%AA%8C%E8%AE%BE%E8%AE%A1%E5%8D%A1.md) · [split card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E6%95%B0%E6%8D%AE%E5%88%86%E5%89%B2%E5%8D%A1.md) |
| Reproduction and runs | Reproduce baselines and run computational experiments within approved resources, keeping commands, versions, raw results and failures. It does not start models or rent compute for you. | [research-reproduce-run](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-reproduce-run/SKILL.en.md) · [run card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E5%AE%9E%E9%AA%8C/%E6%96%B9%E6%B3%95/%E5%AE%9E%E9%AA%8C%E8%BF%90%E8%A1%8C%E5%8D%A1.md) |
| Results analysis and figures | Compute reproducible, traceable comparisons and figures from real results, decide how far each claim holds, and record limitations and negative results. No fabricated data. | [research-results-figures](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-results-figures/SKILL.en.md) · [analysis card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E5%88%86%E6%9E%90%E4%B8%8E%E5%9B%BE%E8%A1%A8%E5%8D%A1.md) · [field-source card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%95%B0%E6%8D%AE%E4%B8%8E%E5%88%86%E6%9E%90/%E6%96%B9%E6%B3%95/%E5%AD%97%E6%AE%B5%E6%9D%A5%E6%BA%90%E5%8D%A1.md) |
| Manuscript and citations | Write the paper from real methods, results and locatable sources, and check that citations and numbers agree. The paper workspace has nine chapter sections. | [research-manuscript-citations](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-manuscript-citations/SKILL.en.md) · [evidence card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95/%E8%AE%BA%E6%96%87%E8%AF%81%E6%8D%AE%E5%8D%A1.md) · [citation check (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95/%E5%BC%95%E7%94%A8%E6%A0%B8%E9%AA%8C%E5%8D%A1.md) · [paper workspace](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E8%AE%BA%E6%96%87/%E5%B7%A5%E4%BD%9C%E5%8F%B0) |
| Submission preparation | Check the target journal's current official requirements and build a local submission package with a list of missing declarations. No log-in, upload, payment or automatic submission. | [research-submission-package](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-submission-package/SKILL.en.md) · [submission checklist (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%8A%95%E7%A8%BF%E4%B8%8E%E8%BF%94%E4%BF%AE/%E6%96%B9%E6%B3%95/%E6%8A%95%E7%A8%BF%E6%A3%80%E6%9F%A5%E6%B8%85%E5%8D%95.md) |
| Revision and response | Map each reviewer comment to edits, extra experiments, manuscript locations and evidence-backed replies. Original comments are kept and nothing is sent automatically. | [research-revision](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/research-revision/SKILL.en.md) · [response card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%8A%95%E7%A8%BF%E4%B8%8E%E8%BF%94%E4%BF%AE/%E6%96%B9%E6%B3%95/%E8%BF%94%E4%BF%AE%E5%9B%9E%E5%A4%8D%E5%8D%A1.md) |
| Supporting: presentation | Present the question, methods, real results, limitations and next steps. There is no dedicated research-\* skill; use the report card and the PPT skill (materials → outline → slides → export → check). | [report card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%B1%87%E6%8A%A5/%E6%96%B9%E6%B3%95/PPT%E6%B1%87%E6%8A%A5%E5%8D%A1.md) · [PPT skill](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/PPT/%E6%8A%80%E8%83%BD/SKILL.en.md) |
| Supporting: materials and showcase | Record the source, permission and use of figures, tables and screenshots; quantitative figures must come from real data. The PPT "Results" section lists exported PPTX/PDF files. | [source card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E7%B4%A0%E6%9D%90/%E6%96%B9%E6%B3%95/%E7%B4%A0%E6%9D%90%E6%9D%A5%E6%BA%90%E5%8D%A1.md) · [figure delivery card (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E7%B4%A0%E6%9D%90/%E6%96%B9%E6%B3%95/%E5%9B%BE%E8%A1%A8%E4%BA%A4%E4%BB%98%E5%8D%A1.md) · [PPT exports](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/PPT/%E5%AF%BC%E5%87%BA) |

- Start with [the research overview page (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/README.md).
- The nine Chinese skills (one route entry plus eight stages) are adapted from ARIS, K-Dense scientific-agent-skills and K-Dense claude-scientific-writer, and are licensed separately under MIT; see the [adaptation list (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%B5%84%E6%96%99/%E6%96%87%E7%8C%AE/%E6%96%B9%E6%B3%95/%E7%A7%91%E7%A0%94/%E6%94%B9%E7%BC%96%E4%B8%8E%E6%9C%AA%E5%86%85%E7%BD%AE%E6%B8%85%E5%8D%95.md). Also included are 82 ARIS paper-method entries (with the upstream originals and their MIT license); the platform does not run them automatically.
- Aimed mainly at computational and ML research. Real medical, animal or wet-lab work needs that field's own protocols; these skills do not cover it.
- Templates are not research results. "Automatic acceptance" only means every check listed in a delivery passed. It does not mean a conclusion holds or that the work is publishable.

## Core features

| Feature | What it does |
|---|---|
| **Bring your own agents** | Any agent that can read files starts from `AGENTS.md`. An optional local MCP server, `research-console`, exposes 75 tools (register, overview, claim a task, deliver, checkpoint, ask a human and more). The platform itself never calls a model. |
| **Blueprint governance** | S0 goal → S1 → S2 tasks; requirements with acceptance criteria; numbered plans (P); three layers of rules (general, project, module); delivery (J) and handover (H) records, all as plain files. The web UI and MCP edit the same files, with revision checks so neither overwrites the other. |
| **Automation dashboard** | Project → goal → task graph, a four-column task board, an agent roster (roles, levels, supervisors), a staff allocation chart, a workflow editor (save, validate, rehearse, enable) and seven supervision rules (for example, take the lock before changing core code; deletions go to the recycle bin). Deliveries follow checks-pass: accepted automatically only when every check passes. Full auto-start must be switched on by a person and currently drives only the local Codex CLI. |
| **Literature reader and content workspaces** | A literature library pairing each source with its notes by L number; a PDF reader with highlights, stickers and pen annotations, plus select-to-note and ask-the-agent; in-page previews for zip, audio/video, Excel, Word and PPT text; sectioned plain-file workspaces for paper, testing, PPT and promo video. |
| **Snapshots, world tree and recycle bin** | Checkpoints at each milestone with content-deduplicated storage, comparison, single-file or full restore; world-tree branches grown from any checkpoint as independent projects, merged back with a three-way merge; deletions go to a restorable recycle bin (X numbers); full backup with a progress bar. |
| **Notes, sticky note and Q&A** | Press N for a sticky note. Notebook entries are numbered, and the original text is saved to `笔记/历史/` (notes history) before an entry is edited or deleted; machine logs are kept separately. Q&A works both ways (the agent asks you, you ask the agent). Screenshots and screen recordings use the Windows Snipping Tool and can be annotated. Reading, detail and terminal panes collapse into a small three-color flame button. |
| **Code map and coding workbench** | Renders the project as a zoomable treemap: syntax-colored lines from afar, readable code up close, coloring by type, recent change or git churn, and an importance pyramid. The coding workbench gathers a task's requirement, rules, approved plan and skills into a read-only work package you can copy to an agent. |
| **Appearance** | Four skins (the first-run default is 玉色科技, "jade tech"), three navigation icon sets, five optional wallpapers, light and dark modes, and Chinese, bilingual or English UI. |

## Which agents, and how to connect

The platform never calls a model and needs no model API key. The work is done by agents you choose, with your own accounts, quotas and costs. There are three ways in:

| Way in | For | How |
|---|---|---|
| (1) Plain files | Any agent that can read files | Read [`AGENTS.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/AGENTS.md) and [`技能库/自动化科研交互界面/SKILL.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%8A%80%E8%83%BD%E5%BA%93/%E8%87%AA%E5%8A%A8%E5%8C%96%E7%A7%91%E7%A0%94%E4%BA%A4%E4%BA%92%E7%95%8C%E9%9D%A2/SKILL.md) first, then work through plain files under [`自动化/协议.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%87%AA%E5%8A%A8%E5%8C%96/%E5%8D%8F%E8%AE%AE.md) (the collaboration protocol). Claude Code picks up `AGENTS.md` automatically via [`CLAUDE.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/CLAUDE.md). |
| (2) Local MCP (optional) | Clients that support stdio MCP | Server `research-console` (`python backend/mcp_server.py`) with 75 tools such as `register_agent`, `get_overview`, `next_task`, `deliver`, `save_checkpoint` and `ask_human`. [`.mcp.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/.mcp.json) covers compatible clients such as Claude Code; others are set up by hand per the [agent connection guide (zh)](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B7%A5%E5%85%B7%E5%BA%93/%E5%AE%89%E8%A3%85%E6%8C%87%E5%8D%97/Agent%E6%8E%A5%E5%85%A5.md): absolute Python path + `backend/mcp_server.py --project <path> --agent <name>`. **One-click connection is not built yet.** |
| (3) Web "staff" automation | **Only the local Codex CLI for now** | Off by default. After a person turns on the master switch, a local Python runner starts the Codex CLI once per round. |

The install guides cover these clients: Claude Code, Codex, Cursor, Qwen Code, Trae / TRAE CN, Tongyi Lingma, Tencent WorkBuddy, Tencent CodeBuddy, Zhipu ZCode, DeepSeek Harness, StepFun Step Code and Hermes Agent. [`工具库/智能体.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B7%A5%E5%85%B7%E5%BA%93/%E6%99%BA%E8%83%BD%E4%BD%93.md) also lists 27 US and 19 Chinese agents.

> **To be clear**
> - "Can connect to this app" in the agent directory is a desk judgment based on whether each vendor's website documents MCP support. The repository has no record of a real connection test for each client.
> - "No API key" applies to the platform only. DeepSeek Harness's official Web UI needs a model API key, and a logged-in agent uses its own cloud model, so this is not the same as working fully offline.
> - Automation drives Codex only. Cursor, Claude Code and the Chinese clients are not connected to the automation runner.

## Quick start

### Windows (recommended)

1. **Install Python 3.12**: open the [Windows downloads page on python.org](https://www.python.org/downloads/windows/), find **Python 3.12.10** and click "Windows installer (64-bit)" (the project is tested on the 3.12 series; 3.12.10 is the last 3.12 release with a Windows installer. Do not use the big button on the python.org home page, which gives a newer major version). On the installer's first screen, tick **"Add python.exe to PATH"**, then click Install Now.
2. **Download and unzip**: download **[MiracleHarness2.zip](https://github.com/tmdysx/agent-research-workbench/releases/latest/download/MiracleHarness2.zip)**, right-click it and choose "Extract All". Windows usually creates two nested folders with the same name (`MiracleHarness2\MiracleHarness2`); keep opening them until you can see `启动.bat` (start) and the `backend` folder (1,423 files in total). **Hold Shift and right-click** an empty spot in the folder and choose "Open PowerShell window here" (on Windows 11 it is "Open in Terminal"; you can also type `powershell` in File Explorer's address bar and press Enter).
3. **Install the dependencies**: in the PowerShell window, run:

   ```powershell
   py -3.12 -m pip install -r backend/requirements.txt "mcp>=1.20,<2" watchfiles
   ```

   > The second half, `"mcp>=1.20,<2" watchfiles`, is a fix for the 2026-10-07 ZIP: its `requirements.txt` does not cap `mcp` (a fresh install gets mcp 2.x, and the MCP server and automation modules fail on import) and does not list `watchfiles` (real-time file-change notifications; without it the app falls back to polling). The `backend/requirements.txt` in the repository is already fixed, and the extra arguments do no harm.
4. **Start**: double-click **`启动.bat`** (start). It finds Python, starts the backend and opens your browser. The black console window is the backend: closing it stops the backend (your data stays in files). Double-clicking again does not start a second copy. If you have several Pythons installed, it prefers the one in `%LOCALAPPDATA%\Programs\Python\Python312`, so install the dependencies into that same Python.

The page is at `http://127.0.0.1:8770/` by default. If the port is taken the app picks the next free one; the console window shows the real address. The page opens on the Blueprint: write your goals, requirements and acceptance criteria, then ask your agent to read `AGENTS.md`. To create a new project, double-click **`新项目.bat`** (new project) or click "New project" in the page.

Staff and plugins are off by default. If something goes wrong, see the [Troubleshooting section of the user guide](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.en.md#troubleshooting).

### macOS / Linux (not officially supported)

There are no launch scripts or docs for macOS or Linux. On 2026-10-07 the backend was tested on Linux: it started and the home page and API responded normally. **macOS has not been tested.** You can try this in the repository or in the unzipped `MiracleHarness2` folder:

```bash
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
# If you are using the 2026-10-07 Release ZIP, use this line instead (same fix as Windows step 3):
# python3 -m pip install -r backend/requirements.txt "mcp>=1.20,<2" watchfiles
python3 backend/main.py           # optional: --port 8770 --no-browser --no-reload
```

- `新项目.bat` corresponds to `python backend/new_project.py`; this has not been checked separately on these systems.
- Screenshots and recording, global hotkeys, the web terminal plugin, the PPT preview scripts and the PowerShell windows used to start staff all depend on Windows.
- `.mcp.json` uses the command `python`. With a virtual environment, or on systems that only have `python3`, change it to the interpreter's absolute path.

### Running the tests (optional)

```bash
python -m pytest backend/tests -q
node --test "backend/tests/*.js"   # front-end tests, run with Node 22; pytest does not call them
```

The full test suite still has known failures; see "Current status" below.

## Repository map

The repository root is a complete release copy. Each folder under `资料/` is one module (one page) in the web UI, and the Chinese-named `.js` files are parts of the web UI.

### Start here

| Path | What it is |
|---|---|
| [`启动.bat`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%90%AF%E5%8A%A8.bat) (start) | Windows double-click launcher: finds Python, runs `backend\main.py` and opens the web page. |
| [`新项目.bat`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%96%B0%E9%A1%B9%E7%9B%AE.bat) (new project) | Windows double-click to create a new project: runs `backend\new_project.py` and copies a clean app to a folder you choose. |
| [`使用说明.en.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.en.md) · [`使用说明.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.md) (user guide) | User guide: first use, every page, automation, snapshots, settings and troubleshooting. It is long; start with "First use". |
| [`AGENTS.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/AGENTS.md) | Onboarding page for every agent (in Chinese): where things are, the working loop and one-line rules. Any agent reads this first. |
| [`CLAUDE.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/CLAUDE.md) | Uses `@AGENTS.md` so Claude Code reads `AGENTS.md` automatically. |
| [`README.en.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/README.en.md) · [`README.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/README.md) | The short READMEs shipped with the release. `README.md` is generated by `backend/release.py`; both `README.md` and `README.en.md` are recorded in `发行清单.json`. Do not edit them by hand. The page you are reading lives in [`.github/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.github). |

### Program

| Path | What it is |
|---|---|
| [`backend/`](https://github.com/tmdysx/agent-research-workbench/tree/main/backend) | Python backend: the FastAPI web server `main.py`, the MCP server `mcp_server.py`, the staff runner and release scripts; `backend/tests/` holds 87 Python test files and 27 JS test files. |
| [`模板.html`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%A8%A1%E6%9D%BF.html) (template) | Main file of the web UI (a single page in plain JavaScript, no framework). The backend serves it, and it loads the `.js` files below. |
| [`治理界面.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%B2%BB%E7%90%86%E7%95%8C%E9%9D%A2.js) (governance UI) | Blueprint governance view, link settings and the text editor shared by people and agents (loaded in the page as `governance-ui.js`). |
| [`内容工作台.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%86%85%E5%AE%B9%E5%B7%A5%E4%BD%9C%E5%8F%B0.js) (content workspace) | Sectioned listing, creation and editing of plain files in the Literature, Paper, Testing, PPT and Promo Video modules. |
| [`自动化面板.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E8%87%AA%E5%8A%A8%E5%8C%96%E9%9D%A2%E6%9D%BF.js) (automation panel) | The automation overview's project → goal → task graph. It only reads existing records and is not a scheduler. |
| [`员工分配图.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%91%98%E5%B7%A5%E5%88%86%E9%85%8D%E5%9B%BE.js) (staff allocation) | Staff allocation flow chart. It only shows existing profiles, claims and run records; it never assigns work or starts staff. |
| [`流程编辑器.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%B5%81%E7%A8%8B%E7%BC%96%E8%BE%91%E5%99%A8.js) (workflow editor) | Drafts dispatch, review, execute, acceptance and condition nodes. Saving and rehearsal never start staff. |
| [`代码地图.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E4%BB%A3%E7%A0%81%E5%9C%B0%E5%9B%BE.js) (code map) | The Source Code module: lays out all source files as a zoomable treemap with an importance pyramid. |
| [`小窗.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%B0%8F%E7%AA%97.js) (panes) | Collapses reading, detail and terminal panes into a 30px three-color flame button and drives the "loading" flame animation. |
| [`界面英文.js`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%95%8C%E9%9D%A2%E8%8B%B1%E6%96%87.js) (UI English) | English UI string table, used when Settings → Language is set to English. |
| [`DESIGN.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/DESIGN.md) | Web UI design spec (in Chinese): three-bar layout, colors, fonts, components and don'ts. Read it before changing the UI. |

### Content and templates

| Path | What it is |
|---|---|
| [`资料/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99) (materials) | One folder per business module: ideas, literature, experiments, data and analysis, paper, submission and revision, presentations, materials, PPT, paper writing, novel writing, promo video and testing, with method cards, templates and showcase examples. |
| [`治理/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%B2%BB%E7%90%86) (governance) | Ships the general rules and an empty project-rules file; goals, requirements, tasks and plans are added later through the Blueprint. |
| [`自动化/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%87%AA%E5%8A%A8%E5%8C%96) (automation) | Collaboration protocol `协议.md`, delivery policy (checks-pass: accepted automatically when all checks pass) and workflow card W1 Auto-advance. |
| [`快捷指令/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%BF%AB%E6%8D%B7%E6%8C%87%E4%BB%A4) (quick prompts) | Five one-click prompt templates: hand over to a new agent, sort incoming material, weekly review, rule check and auto-advance. |
| [`索引/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E7%B4%A2%E5%BC%95) (index) | Runtime SQLite index. The bundled `state.db` is a demo index built only from the starter examples, so the app shows content on first open. |

Folders that `AGENTS.md` mentions, such as `笔记/` (notes), `存档/` (snapshots), `回收站/` (recycle bin) and `治理/目标/` (goals), are not in the release yet. They appear once you write them in the web UI or the app creates them.

### Skills and tools

| Path | What it is |
|---|---|
| [`技能库/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%8A%80%E8%83%BD%E5%BA%93) (skills) | How-to skills for agents: nine Chinese research skills (`research-*`, MIT), platform usage, web front-end and delivery self-check skills, plus upstream method packs for paper writing and PPT. |
| [`工具库/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%B7%A5%E5%85%B7%E5%BA%93) (tools) | Tool cards T1–T17, bundled web libraries (pdf.js, KaTeX, Mermaid, Three.js, SheetJS, docx-preview, JSZip, xterm), domestic and international install guides, an agent directory and web links. |
| [`插件/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E6%8F%92%E4%BB%B6) (plugins) | Three optional plugins, all off by default: PPT Preview (Windows; needs PowerPoint or LibreOffice on the machine to convert to PDF), Web Terminal (Windows only) and Media Edit (currently only an FFmpeg protocol and command card). |

### Brand and appearance

| Path | What it is |
|---|---|
| [`品牌/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%93%81%E7%89%8C) (brand) | The author's original phoenix bird mark, four AI-generated purpose illustrations (hero, terminal, slides, media) and the hand-drawn button icon sprite `icons.svg`. |
| [`外观/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E5%A4%96%E8%A7%82) (appearance) | Switchable appearance: four skin CSS files, three navigation icon sets, five optional wallpapers, the phoenix logo and a guide for making your own skin. |

The four purpose illustrations in `品牌/` are AI-generated concept art, not screenshots of the app.

### Configuration and manifests

| Path | What it is |
|---|---|
| [`.claude/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.claude) | Claude Code project settings (only `settings.json`); it saves Claude Code's plans into `治理/计划` (governance plans). |
| [`.mcp.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/.mcp.json) | Registers the local MCP server `research-console` (`python backend/mcp_server.py`) for MCP-capable clients. |
| [`.gitignore`](https://github.com/tmdysx/agent-research-workbench/blob/main/.gitignore) | What git ignores: the runtime database, snapshots, recycle bin, literature PDFs, machine-specific settings, large media and external installs. |
| [`模板配置.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%A8%A1%E6%9D%BF%E9%85%8D%E7%BD%AE.json) (template profile) | Template profile for this release (research): which business modules, module skills and built-in skill IDs it includes. |
| [`内置标记.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%86%85%E7%BD%AE%E6%A0%87%E8%AE%B0.json) (built-in marks) | List of built-in paths carried into new projects (the list edited in Settings → Built-in). |
| [`发行清单.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E5%8F%91%E8%A1%8C%E6%B8%85%E5%8D%95.json) (release manifest) | Generated by `backend/release.py`. It records the path, size and sha256 of the 1,422 other files in the Release ZIP (with Windows line endings), so it does not necessarily match the files in the repository byte for byte; verify against the ZIP. |
| [`新项目复制清单.json`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E6%96%B0%E9%A1%B9%E7%9B%AE%E5%A4%8D%E5%88%B6%E6%B8%85%E5%8D%95.json) (new-project copy list) | List of files (paths and sizes) copied in when this project was created. |
| [`.github/`](https://github.com/tmdysx/agent-research-workbench/tree/main/.github) | The GitHub home page text (this page) and contributing guide. Not part of the release package. |
| `.gitattributes` | Keeps `.bat` files on CRLF line endings for Windows. |

### Licenses

| Path | What it is |
|---|---|
| [`LICENSE`](https://github.com/tmdysx/agent-research-workbench/blob/main/LICENSE) | Unmodified PolyForm Noncommercial 1.0.0 text covering the original project material. |
| [`NOTICE`](https://github.com/tmdysx/agent-research-workbench/blob/main/NOTICE) | Required notice, the noncommercial terms and the commercial-licensing email. |
| [`第三方许可证.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%AC%AC%E4%B8%89%E6%96%B9%E8%AE%B8%E5%8F%AF%E8%AF%81.md) (third-party licenses) | Third-party notices: bundled web libraries, backend Python packages, terminal-plugin dependencies, MIT research skills and upstream method packs. |

## Beyond research

| Use | What exists today |
|---|---|
| Novel writing | [`资料/写小说/方法/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%86%99%E5%B0%8F%E8%AF%B4/%E6%96%B9%E6%B3%95) has a task brief, a chapter handover sheet and a seven-stage route: brief and reader → world and characters → layered outline → draft and state → continuity and cold read → author-approved revision → handoff and manuscript. These are workflow templates; the route skill is not bundled. |
| Paper writing | Works without the full research pipeline: [`资料/写论文/方法/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%86%99%E8%AE%BA%E6%96%87/%E6%96%B9%E6%B3%95) has a task brief, an evidence ledger and a stage route. |
| Promo video | The [`资料/宣传片/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/%E5%AE%A3%E4%BC%A0%E7%89%87) workspace has only "materials" and "results" sections; the Media Edit plugin lets an agent cut, join and subtitle clips from an FFmpeg command card. **The web video editor is not built yet**, and the promo-video stage skills are not bundled. |
| PPT presentations | [`资料/PPT/`](https://github.com/tmdysx/agent-research-workbench/tree/main/%E8%B5%84%E6%96%99/PPT) has materials and results sections; the PPT skill works audience → page-by-page plan → editable build → check → delivery. The bundled 23-page project introduction PPT/PDF is an example. |
| Other long-running DIY projects | The general template carries no business material. You create your own modules and set the requirements, rules and workflow; research is just one optional example. |
| Managing agents that write code | The code map, coding workbench, core lock and supervision rules can be used to manage agent-driven software work. |

## Current status

**Early release**: the core is not frozen yet. There is no 1.0 and no installer.

**Works today**

- Local web page + Python (FastAPI) backend: listens only on `127.0.0.1`, opens the browser when ready, restarts itself when backend code changes, and the page follows file changes within a second or two.
- Local MCP server `research-console` (75 tools); the web UI and agents read and write the same files.
- Blueprint (goals, requirements and acceptance, plans, rules) editable in the page, with revision-based conflict detection.
- Automation dashboard: graph, task board, agent roster, staff allocation chart, workflow editor, seven supervision rules, checks-pass automatic acceptance.
- Snapshots: deduplication, comparison, restore, world-tree branches with three-way merge, recycle bin, full backup.
- Literature library and PDF reader; in-page previews for zip, audio/video, Excel, Word and PPT.
- Notebook, sticky note, machine logs, two-way Q&A, screenshots and recording with annotation (via the Windows Snipping Tool).
- Code map and read-only coding workbench.
- Nine Chinese research skills with method cards in each module, 82 ARIS paper-method entries (with upstream originals and MIT license), and a PPT skill.
- Two working plugins: PPT Preview (Windows; needs PowerPoint or LibreOffice on the machine) and Web Terminal (Windows only, needs pywinpty). Both must be installed first and then enabled by a person.
- Tool install guides: 26 programs with domestic and international routes; the app only checks the local machine and never installs anything itself.
- Showcase examples: a 23-page project introduction PPT/PDF, novel and paper-writing workflow templates, a historical promo video and a demo index. These are examples, not your own research results.

**Not done or not verified yet**

- The web video editor is not built (the Media Edit plugin is only an FFmpeg protocol and command card).
- One-click agent connection is not built; MCP is configured by hand.
- Web "staff" automation supports only the local Codex CLI. Staff do not start by default, and only a person can turn on the full auto-start switch; "auto-start allowed" does not mean staff are running.
- Real research tasks, real task completion and installation on a second computer have not been verified.
- The full test suite is not green. On 2026-10-07 on Linux, after installing dependencies from the fixed `backend/requirements.txt` into a fresh virtual environment (Python 3.12), run as root this time: Python tests 1,072 passed, 30 skipped (29 Windows-only, 1 because the test environment could not create a link), 24 failed. Of these, 17 are tests that no longer match the current release layout or templates (the old `内置/` (built-in) folders, the removed business template, content trimmed at release time), 4 hard-code Windows assumptions, and 3 are read-only index tests (`test_work_packages.py`) that fail as root (they passed in another run the same day as a normal user). JS tests (Node 22): 653 of 656 passed. Full results on Windows have not been re-checked.
- The `requirements.txt` in the 2026-10-07 Release ZIP does not cap `mcp<2` or list `watchfiles`. The one in the repository is fixed; when installing from that ZIP, use the fix command in Quick start.
- No launch scripts or docs for macOS or Linux; screenshots and recording, the web terminal and the PPT preview scripts depend on Windows.
- World-tree 3D modeling (Blender) is paused and only a guide is provided; later parts of the "rebirth" feature are paused or not built.
- The promo-video stage skills and the novel route skill are not bundled.
- Deliberately out of scope: long screenshots, pinning to the desktop, text recognition in images, and mobile layouts.

## License and commercial use

- Original material is licensed under **[PolyForm Noncommercial 1.0.0](https://github.com/tmdysx/agent-research-workbench/blob/main/LICENSE)**. Personal learning, noncommercial research and other noncommercial use is free under its terms.
- **Commercial use, including commercial research, requires a separate written license from the author.** Contact **3129746403@qq.com**.
- The source is available, but this is **not an OSI-approved open-source license**.
- Third-party parts keep their own licenses: the nine Chinese research skills and their teaching material, and upstream content such as ARIS, K-Dense and ppt-master, are MIT; bundled web libraries are Apache-2.0, MIT and others. See [`第三方许可证.md`](https://github.com/tmdysx/agent-research-workbench/blob/main/%E7%AC%AC%E4%B8%89%E6%96%B9%E8%AE%B8%E5%8F%AF%E8%AF%81.md) (third-party licenses) and [`NOTICE`](https://github.com/tmdysx/agent-research-workbench/blob/main/NOTICE).
- The PolyForm license grants no trademark rights. You may refer to MiracleHarness truthfully, but without written permission please do not present a modified version, fork or other product as an official MiracleHarness release, and do not use the phoenix bird mark as its main identifier.
- Want to help? See the [contributing guide](CONTRIBUTING.md).

---

<div align="center">

By **Tianyi Hu** · MiracleHarness · [miracleharness.com](https://miracleharness.com)

</div>
