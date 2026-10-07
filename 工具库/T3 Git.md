---
编号: T3
名字: Git
类别: 外部工具
一句话: 给项目存版本，看改了什么，出事能退回去
检查: git --version
在哪:
配套技能:
---
# T3 Git

## 怎么调

| 要做什么 | 命令 |
|---|---|
| 看哪些文件改了 | `git -c core.quotepath=false status` |
| 看具体改了什么 | `git diff` |
| 存一个版本 | `git add 文件…` 然后 `git commit -m "一句话说改了什么"` |
| 看历史 | `git log --oneline -20` |

`-c core.quotepath=false` 让中文文件名正常显示，不改任何设置。

## 守的戒律

- **作者说了才提交**；不自己决定存版本
- **不推到公开仓库**：公开之前先确认专利时间，这一步收不回（戒律 项-9）
- 不用会丢东西的命令：`reset --hard`、`push --force`、`clean`、`checkout -- 文件`；要退回，先问人

## 常见坑

- 本机新开的窗口可能找不到 git：用上面「在哪」里的完整路径
