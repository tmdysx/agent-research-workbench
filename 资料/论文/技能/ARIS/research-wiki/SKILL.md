---
name: mh-paper-aris-module-research-wiki
description: "维护论文、想法、实验与论断之间可追溯的知识节点和类型化关系。"
license: MIT
---

# 研究知识节点与证据关系

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

当前项目明确的 wiki 目录/操作范围、节点与来源、研究简报、已确认状态以及要新增/查询/检查的具体任务。

## 方法

1. 先核对已有 schema、规范节点 ID 和关系存储位置；论文、想法、实验、论断分别管理，不以题名字符串充当唯一身份。
2. 入库时核对来源、版本和身份并去重；论文原摘要保留为原始材料，业务解读与其分开，缺失字段不猜。
3. 建立 extends、motivates、tests、supports、invalidates 等有证据的类型化关系；关系只在图的正本记录，页面 Connections 由既有流程生成。
4. 区分证明/审查状态与实验证据：真实实验节点存在后才关联支持/反驳边，不以一次指标改写证明状态或未审论断身份。
5. 生成压缩查询材料时保留失败想法、关键缺口和证据链；清除操作报错/权限提醒等不应固化为科研事实的噪声。
6. 检查孤立节点、断链、矛盾状态、未经验证的想法与空页，提出可定位修复；只执行本次授权更新，不创建新私人库。

## 产物与验收

节点/关系变更清单、来源定位、查询材料或 lint 报告；验收关系无悬空端点、失败记忆未丢、实验证据与证明状态保持区分。

## 依赖与边界

原运行流程依赖 research_wiki.py 等 helper；方法包没有安装写入器，也不读取 ~/.aris 或作者 home。可在当前获准文本中准备变更草案，写入仍走项目已有入口。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [capture-antipatterns.md](references/support/skills/shared-references/capture-antipatterns.md)
- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/research-wiki/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
