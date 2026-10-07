# 将本地项目交给 agent

![不同工具共享项目记录](../../品牌/miracleharness2-terminal.png)

品牌插画是用途示意。先选择自己已经可用的客户端：[Codex](软件/Codex.md)、[Claude Code](软件/Claude%20Code.md)、[Cursor](软件/Cursor.md) 或 [Qwen Code](软件/Qwen%20Code.md)。只有选 npm 安装方式才看 [Node.js](软件/Node.js.md)，无需全部安装。

## 先选对项目

在客户端打开本项目根目录，先读 AGENTS.md 和技能库/自动化科研交互界面/SKILL.md。项目自带技能是普通 Markdown 正本，不需要复制作者的个人技能目录或认证文件。

## 可选 stdio MCP

客户端支持 stdio MCP 时，服务名可填 research-console。命令填写**启动后台的同一个 Python 的绝对路径**；参数按下面顺序填写。你必须用自己的真实项目路径和员工名称替换占位，不抄作者路径或历史 G 编号。

```text
<项目绝对路径>/backend/mcp_server.py
--project
<项目绝对路径>
--agent
<本员工名称>
```

客户端当前的 MCP 配置方式可能不同，不能把某一家 JSON 当作通用标准。本项目 .mcp.json 给兼容客户端参考；使用虚拟环境时填写该环境 python.exe 完整路径，双击启动.bat 不保证选择它。

## 连上后检查

1. register_agent 报到并读取真实档案；不能借别人的身份或自行提权。
2. get_overview 返回的项目名称、目标、最新记录应与网页一致；不一致就停止向该连接写入，先核对路径。
3. list_skills / read_skill 读取技能正本；蓝图详情用 get_governance。
4. 写治理正文先 read_governance_document 拿 revision，再按授权 write_governance_document。冲突先对照，不盲目覆盖。
5. 首次只做读取核验。自动开工需人已定目标、验收、岗位、范围和许可；安装和登录不等于允许启动员工。

没有 MCP 的客户端也可直接读同一项目文件、按协议保留交付和交接。真实账号、配额、模型与权限由各家客户端决定，本页没有宣称全部客户端已做实连。

## 官方入口与核验

核验日期 2026-10-05，官方资料只读；没有执行安装、登录、创建员工或开工。

- [OpenAI 官方 MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Claude Code 官方 MCP](https://code.claude.com/docs/en/mcp)
- [Cursor 官方文档](https://cursor.com/docs)
- [Qwen Code 官方入门](https://qwenlm.github.io/qwen-code-docs/en/users/quickstart/)

[返回安装指南](从这里开始.md)


## 国内客户端与各自 MCP 说明

选择一款已可用客户端即可：[两套安装方案](国内与国外方案.md)列明下载、认证与地区。具体客户端主指南保留当前官方 MCP 来源和项目参数；新增说明没有新增自动运行器适配。

- [TRAE CN / TraeCode](%E8%BD%AF%E4%BB%B6/TRAE%20CN.md)：TraeCode 与 TraeWork 是不同产品；安装入口不等于当前自动运行器支持。
- [通义灵码 / Lingma IDE](%E8%BD%AF%E4%BB%B6/%E9%80%9A%E4%B9%89%E7%81%B5%E7%A0%81.md)：旧 Lingma 与当前 Qoder CN 页面存在名称变化，按下载页核对，不冒称全部功能已实连。
- [腾讯 WorkBuddy](%E8%BD%AF%E4%BB%B6/WorkBuddy.md)：WorkBuddy 与 CodeBuddy IDE 分开；本页未新增自动启动或实连验收。
- [腾讯 CodeBuddy IDE](%E8%BD%AF%E4%BB%B6/CodeBuddy.md)：IDE、编辑器插件与 CodeBuddy Code CLI 是不同形式，不能混成一种运行器。
- [智谱 ZCode](%E8%BD%AF%E4%BB%B6/ZCode.md)：官网明确支持本地 stdio MCP；套餐、版本和地区按当前账号核对。
- [DeepSeek Harness](%E8%BD%AF%E4%BB%B6/DeepSeek%20Harness.md)：官方 Web UI 指南当前要求模型 API key，不能把此客户端说成全程无需 API。
- [阶跃 AI / Step Code](%E8%BD%AF%E4%BB%B6/%E9%98%B6%E8%B7%83%20AI.md)：桌面外部 stdio MCP 未核到；Step Code 官方终端明确支持 MCP，Windows 原生 beta，未试装。

阶跃桌面外部 stdio MCP 入口未核到，先使用普通文件接手；其官方 Step Code 终端有 MCP 与 CN/Oversea OAuth 账号方案，主指南分别说明，未新增自动运行器适配。DeepSeek Harness 使用其官方插件配置，与通用 mcpServers JSON 不同。
