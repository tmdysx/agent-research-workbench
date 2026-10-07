---
编号: T6
名字: SQLite
类别: 技术栈
一句话: 数据库：一个文件，不用装
检查: python -m sqlite3 -v
在哪: %LOCALAPPDATA%\Programs\Python\Python312
---
# T6 SQLite

## 用在哪

- `索引/state.db`：模块、待拍板、决定、外部资料入口的分拣、事件、各种编号
- 开了 WAL 模式：网页和 agent 同时读写不打架
- 笔记、计划、日志、答疑**不在库里**，都是普通 md 文件

## 为什么选

- 单文件、免安装，Python 自带（见 计划 S0 · R3 技术栈）

## 改动注意

- 库里有你拍过的板（决定 A-xx）和待拍板，**别手动删 `索引/state.db`**
- 改表结构只走 `backend/store.py` 里的迁移（版本号往上加），不直接改库
