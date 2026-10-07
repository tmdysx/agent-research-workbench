---
编号: T7
名字: MCP
类别: 技术栈
一句话: 给 agent 的接口：Claude Code、Codex 都能接
检查: python -m pip show mcp
在哪: %LOCALAPPDATA%\Programs\Python\Python312
---
# T7 MCP（官方 Python SDK）

## 用在哪

- `backend/mcp_server.py`：接口名 research-console——看全貌、加模块、问人、读笔记、查答案、报每一圈、看工具卡……
- `.mcp.json`：在项目文件夹里开 Claude Code，它就自己连上

## 为什么选

- 标准协议，不绑死某一个 agent（戒律 项-3；计划 S0 · R1 定位：接口顺着宿主走）

## 改动注意

- 最低版本写在 `backend/requirements.txt`（mcp ≥ 1.20）
- 加减工具时，同步改测试里的工具清单（`backend/tests/test_mcp.py`）
