# 阶跃 AI / Step Code · 安装与使用

阶跃星辰有两个可选入口：**阶跃 AI 桌面伙伴**适合桌面文件与办公；**Step Code**是官方终端编程 agent，明确支持 MCP。选择一种符合任务的方式，不必两个都装。

> 桌面的外部 stdio MCP 入口尚未核到；官方 Step Code 有 MCP 依据，Windows 原生支持当前为 beta。本轮未安装或试连。

![阶跃准备流程](../图示/stepfun.svg)

## 什么时候需要

使用阶跃官方 agent 阅读授权文件、处理任务或编程。桌面下载位于 chat.stepfun.com；终端项目为 stepfun-ai/Step-Code，不能把其他同名 step-cli / stepfun-mcp 当官方客户端。

## 输入、调用与输出

输入：项目目录、目标、任务和本人账号。调用：所选桌面应用，或真实 `step` 终端命令。输出：获准文件、命令结果、检查和交接。Step Code 可选择国内/国际 Step Plan 的浏览器 OAuth 套餐账号，也可选择 API key 按量认证；免 key 仅指账号套餐这条方式，不是所有运行形式。

## 官网与下载入口

- [官方桌面软件下载](https://chat.stepfun.com/download)
- [官方 Step Code 仓库与安装说明](https://github.com/stepfun-ai/Step-Code)
- [国内方案](../方案/stepfun-cn.md)
- [国外方案](../方案/stepfun-global.md)

## Windows 与安装位置

桌面官网列 Windows/macOS，但本次未读取完整处理器与最低系统要求；点击实际按钮核对安装包，位置用户自选且非内置。

Step Code 官方 README 给 Windows PowerShell 安装器；原生支持仍为 beta，官方推荐 Windows 使用 WSL。官网安装器默认装到个人 `.stepcode/bin` 并调整 PATH，脚本参数支持自选版本和安装目录；具体 Windows 参数以下载时的官方脚本为准。本平台本轮没有替人安装 WSL、执行远程安装脚本或启动 Step Code。

## 操作步骤

### 桌面伙伴

1. 到官方桌面下载页选择自己的系统，按安装器安装。
2. 用本人账号登录并核实际套餐和文件权限，只选授权的项目目录。
3. 先读 AGENTS.md、目标和验收；没有已核桌面 MCP 入口时使用普通文件接手。
4. 完成任务后核产物与检查，保留交付和交接，不把安装成功当任务完成。

### Step Code 终端

1. 打开官方仓库 README 核对当前安装方式。选择 Windows 原生 beta 时，先阅读官方 PowerShell 脚本；选择 WSL 时需用户已有或明确选择该环境。
2. 以下是官方安装命令的文字示例，会下载并执行远程脚本，**本轮没有执行**。安装目录和脚本行为先按当前官方内容核对。

```powershell
# 仅选择 Windows 原生安装方式且确认官方脚本时运行
irm https://static-openapi.stepfun.com/stepcode/install.ps1 | iex
```

3. 新开终端查 `step --version` 与 `step --help`；从正确项目目录启动 `step`，不要运行 `/init` 覆盖本项目已有 AGENTS.md。
4. 用 `step login` / `/login` 选国内 Step Plan 或 Step Plan Oversea 的本人账号 OAuth；若选择 API key，账号及服务端点另核，凭据只保留本机。
5. 按下面官方 MCP 客户端说明连接 research-console，只读核对目标与身份；自动运行器没有因为指南新增而完成 Step Code 适配。

## 安装授权与调用范围

软件安装、连接本地项目、修改文件及自动开工分别按用户已有授权。内置只保存说明、来源与图示，程序和 `.stepcode` 认证/会话目录不打包复制。官方客户端有自己的权限模式，首次只读核验后才执行已批准任务；本页不调用其发布能力。

## 怎么检查成功

命令是供用户实际检查的说明，本轮没有执行安装、登录或模型任务。先替换自己真实项目路径；状态输出只在本机查看，不复制认证内容到项目。

```powershell
step --version
step --help
step login status
step mcp --help
Test-Path "<项目绝对路径>/AGENTS.md"
```

桌面版在“关于”查真实版本，不假设有专用 CLI。Step Code 须版本与本人认证真实可用；连接 MCP 还需实际工具列表和 `get_overview` 返回同一项目。网页检测没有该客户端适配时保持“未检查”。

## MCP 与项目接手

**桌面伙伴**：本次没有核到外部 stdio MCP 官方配置依据，不能用开放 API 平台介绍替代桌面步骤。

**Step Code**：官方 README 明确 MCP，官方仓库技术文档描述 `step mcp add` 和 `.stepcode/config.toml`。文档注明对应实现分支，实际发行版必须先用 `step mcp --help` 核对是否已有下列命令；本文未试装、未试连。

```powershell
# 确认当前发行版支持该命令后，替换真实路径和自己员工名
step mcp add research-console -- "<后台实际 python.exe 路径>" "<项目绝对路径>/backend/mcp_server.py" --project "<项目绝对路径>" --agent "<本员工名称>"
step mcp get research-console
```

官方文档也列 TOML 结构，作为实际参数对照，不自动写入个人配置：

```toml
[mcp_servers.research-console]
command = '<后台实际 python.exe 路径>'
args = ['<项目绝对路径>/backend/mcp_server.py', '--project', '<项目绝对路径>', '--agent', '<本员工名称>']
```

Step Code 首次启动可导入已有 Claude Code/Codex MCP；仍需核对导入服务是否本项目和本人身份，不因为导入成功便借用旧员工。首次只读 `get_overview` 与 `list_skills`，按 [Agent接入](../Agent接入.md)核身份并报到。不要对当前 stdio research-console 做无关的远程 MCP OAuth。

## 失败时怎样处理

- 桌面下载的架构不明：核对官方当前页面，不自行猜 x64/ARM 包。
- 原生 Windows beta 出错：保留实际版本和日志，参考官方 WSL 建议，但不擅自安装系统功能。
- `step mcp` 不存在：当前发行版本可能与仓库技术文档不同；保留未连接事实，按当前官方发行说明处理。
- 国内/国际登录不一致：核对 Step Plan CN 与 Oversea 账号、套餐和服务端点，不能说两类凭据默认互通。
- 模型登录成功但 MCP 失败：检查后台实际 Python、完整参数及项目路径，不贴出个人 auth.json。

## 官方来源与核验范围

核验日期：2026-10-05。只读核验官方来源；桌面与终端分开记录，不把安装、认证、MCP 能力和平台运行器适配混在一起。本轮未下载执行程序、登录或实连。

- [官方桌面下载](https://chat.stepfun.com/download)
- [官方 Step Code README](https://github.com/stepfun-ai/Step-Code)
- [官方 MCP 配置技术文档](https://github.com/stepfun-ai/Step-Code/blob/main/docs/step-unified-config-and-mcp.md)
- [Step Plan 国内](https://platform.stepfun.com/step-plan)
- [Step Plan Oversea](https://platform.stepfun.ai/step-plan)
- [桌面用户协议与标识条件](https://chat.stepfun.com/legal/terms)

[返回安装总览](../从这里开始.md)


## 官方页面入口

-

来源：[官方下载 / 产品页](https://chat.stepfun.com/download)；截图日期：2026-10-05。用于定位官方下载入口，不代表本机已安装、登录或实连。记录见[截图来源](../应用截图/来源.md)。
