---
编号: T8
名字: pytest
类别: 技术栈
一句话: 测试：改完程序全过才交
检查: python -m pip show pytest
在哪: %LOCALAPPDATA%\Programs\Python\Python312
---
# T8 pytest

## 用在哪

- `backend/tests/`：改完程序跑 `python -m pytest backend/tests -q`，全过才交（戒律 源-1）

## 改动注意

- 测试只碰临时目录，不碰真的 `~/.claude` 和真的数据库（戒律 源-2）
- 只有跑测试才要装，平时用这个工具不需要它
