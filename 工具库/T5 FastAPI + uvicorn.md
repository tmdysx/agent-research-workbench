---
编号: T5
名字: FastAPI + uvicorn
类别: 技术栈
一句话: 后端：网页和 agent 读写数据都走它
检查: python -m pip show fastapi uvicorn
在哪: %LOCALAPPDATA%\Programs\Python\Python312
---
# T5 FastAPI + uvicorn

## 用在哪

- `backend/main.py`：网页的所有接口（/api/…）、实时推送、托管 模板.html；uvicorn 负责把它跑起来
- 后台开着时打开 `/docs`：每个接口一条，点一下就能试

## 为什么选

- 自带 /docs 接口页：不读代码也看得见后端有哪些接口（见 计划 S0 · R3 技术栈）
- 语言是 Python，见 T4

## 改动注意

- 最低版本写在 `backend/requirements.txt`（fastapi ≥ 0.115，uvicorn ≥ 0.30，websockets ≥ 12）
- 换框架、升级大版本先问人：改环境不是没影响的操作
