# DeepSeek Harness · 安装与使用

DeepSeek 官方桌面与 Web/CLI agent；开发者预览，模型认证单独核对。

> 官方 Web UI 指南当前要求模型 API key，不能把此客户端说成全程无需 API。

![DeepSeek Harness准备流程](../图示/deepseek-harness.svg)

## 什么时候需要

希望试用 DeepSeek 官方新 agent 执行获准工作；选择官网桌面版或官方包的 Web UI。普通 DeepSeek 聊天网站不等于 Harness 客户端。

## 输入、调用与输出

输入：选定工作区、任务与相应认证；调用：官方 DeepSeek Harness 桌面或 CLI/Web UI；输出：获准文件、命令结果与计划。源码许可为 MIT，品牌、第三方依赖与模型服务另有规则。

## 官网与下载入口

- [官方入口](https://www.deepseek.com/harness/)
- [官方软件下载 / 安装说明](https://www.deepseek.com/harness/)
- [国内安装方案](../方案/deepseek-harness-cn.md)
- [国外安装方案](../方案/deepseek-harness-global.md)

## Windows 与安装位置

官网当前列 Windows 64 位与 macOS Apple Silicon 桌面下载；未核到其他原生桌面架构，不自行推断支持。桌面程序按向导放非内置。CLI/Web UI 用本人 Node 工具环境；官方源码 package.json engines 为 ^22.19.0 或 >=24，但桌面包不因此要求用户另装 Node。

本项目本轮只读核验资料，未试装该客户端、未登录账号、未扩大系统支持范围。

## 操作步骤

1. 打开 deepseek.com/harness，沿其官网 GitHub 链接核对 deepseek-ai/deepseek-harness；不要下载同名第三方 fork。

2. 桌面方式选择符合系统的官方安装包。首次模型认证按当前桌面实际界面确认；本文没有实登录桌面，不承诺桌面必然免 API key。

3. CLI/Web UI 方式先准备满足官方包要求的 Node，再在所选项目目录运行下方 npx 命令；它会启动本机服务，不是纯版本检查。仅在你主动选择运行时执行。

4. Web UI 的 Settings → Models 当前按官方指南填写自己模型供应商的 API key；当前 provider 指南未支持 OAuth provider，不填写作者密钥。

5. Choose workspace 添加并选择当前项目，先读 AGENTS.md；空的新 Web UI 尚未选择工作区，不能假定启动目录自动成为已选项目。

6. 需要 MCP 时按官方 dsh-mcp-client 配置说明添加明确的本地服务，先核对目标；开发者预览可能变动，保留实际版本与日志。

## 安装授权与调用范围

安装目录由你选择，内置只带说明与图示，不把程序和认证复制到新项目。软件安装、文件写入、连接 MCP、自动开工分别按实际权限和已有授权执行；安装了客户端不能当作允许修改所有项目。个人账号、密钥和数据保留本机，不写进模板。

## 怎么检查成功

下面是供用户操作的说明命令，**本次没有执行安装或启动客户端**。先替换占位为本机真实路径；检查命令不是成功记录。

```powershell
node --version
npm.cmd --version
Test-Path "<项目绝对路径>/AGENTS.md"
# 下面会主动启动官方 Web UI；选择该方式并准备自己的模型认证后才运行
npx.cmd @deepseek-ai/dsh web
```

实际选择的桌面或 Web UI 版本可读，模型认证可用，工作区已明确；若接 MCP 必须看到 tools 并读到当前项目。只打开本机 Web 页面不代表模型已经可以执行任务。

## MCP 与项目接手

官方仓库的 `@deepseek-ai/dsh-mcp-client` 支持本地 stdio；没有默认启用任何服务器。下面是**项目参数适配示例**，不是已经写入客户端配置，也不是通用 mcpServers JSON。按官方持久插件/配置说明放入当前版本支持的位置：

```yaml
- id: research-console
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: research-console
    transport: stdio
    command: '<后台实际 python.exe 路径>'
    args: ['<项目绝对路径>/backend/mcp_server.py', '--project', '<项目绝对路径>', '--agent', '<本员工名称>']
```

配置后首次只读 `get_overview`，确认工具名和当前项目；查看启动日志中实际连接错误。未在本轮试连，不把此示例当自动运行器已有适配。通用项目身份与接手流程见 [Agent接入](../Agent接入.md)。

## 失败时怎样处理

- npx 包下载失败：国内路线可选择每次命令的 npm 镜像；镜像不提供模型 key 或 DeepSeek 配额。

- 界面能开但无法发任务：先选工作区并配置模型，检查官方当前认证要求。

- 桌面与 Web UI 配置不同：分别按各自实际版本，不把源码示例所有配置原样当桌面设置页。

## 官方来源与核验范围

核验日期：2026-10-05。核验官方页面和公开说明，不等于真实下载安装、登录、额度或本项目 MCP 实连验收。未核到的入口明确保留未知；本轮没有新增客户端运行器适配。

- [官网桌面下载](https://www.deepseek.com/harness/)
- [官方仓库与 CLI](https://github.com/deepseek-ai/deepseek-harness)
- [Web UI 模型与工作区](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/index.md)
- [模型提供方与 OAuth 当前范围](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md)
- [官方 MCP 插件配置](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md)
- [官方品牌使用规范](https://github.com/deepseek-ai/deepseek-harness/blob/master/BRAND_GUIDELINES.zh.md)

[返回安装指南总览](../从这里开始.md)


## 国内与国外安装方案

[国内安装方案](../方案/deepseek-harness-cn.md) · [国外安装方案](../方案/deepseek-harness-global.md)。入口区分下载来源、账号与模型服务；镜像不等于服务可用。详细选择见[两套方案总览](../国内与国外方案.md)。


## 官方小标识

-

[标识来源官网](https://www.deepseek.com/harness/)；原样保存，用于识别软件/来源。详细出处、权利与使用条件见[图片来源](../应用图片/来源.md)。


## 官方页面入口

-

来源：[官方下载 / 产品页](https://www.deepseek.com/harness/)；截图日期：2026-10-05。用于定位官方下载入口，不代表本机已安装、登录或实连。记录见[截图来源](../应用截图/来源.md)。
