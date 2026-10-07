# PyCharm · 安装与使用

PyCharm 是 JetBrains 的 Python 开发工具，适合管理解释器、编辑科研脚本、调试和运行测试。当前使用统一版 PyCharm，核心 Python 与 Jupyter 功能可继续免费使用；Pro 扩展和 AI 服务的许可另行核对，不再按旧的 Community / Professional 双下载页指路。

-

图来自官方快速入门文档，原样保存；不是本机项目、安装或运行结果。

## 输入、调用与输出

输入：获准处理的 Python 项目、Notebook 或临时样例。调用：打开项目，明确配置已有解释器或项目虚拟环境，再运行或调试自己的代码。输出：文件、运行日志和测试结果。PyCharm 的 Java 运行时随产品提供；Python 解释器仍须单独准备。

## 官网与下载

- [中国官网下载](https://www.jetbrains.com.cn/pycharm/download/)
- [全球官网下载](https://www.jetbrains.com/pycharm/download/)
- [国内方案](../国内方案/pycharm.md) · [国外方案](../全球方案/pycharm.md)

两套域名都由 JetBrains 提供；下载渠道不改变产品授权，也不保证 AI 服务或账号在各地可用。

## Windows 安装步骤

1. 核 Windows 10/11 及 x64/ARM64 架构，到对应官网选当前系统安装器。当前官方安装页列出 8GB 内存、10GB 磁盘等要求，安装前以所选版本页面为准。
2. 可用 JetBrains Toolbox 管理安装与更新，也可直接运行独立 `.exe` 安装器。无需为 PyCharm 另装 Java；软件装在用户选定的非内置目录。
3. PATH、文件关联和快捷方式按需选择；不自动替换已有 IDE。启动后的 Pro 试用不等于全部功能永久免费，试用结束可继续使用免费核心功能。
4. 打开自己的项目目录。在设置中的 Python Interpreter 选择已有 Python 或项目虚拟环境；已有有效环境时优先复用，不对作者项目自动新建、覆盖或装包。
5. 核解释器完整路径与本项目 Python/MCP 实际配置一致。若没有 Python，先读[Python 指南](../软件/Python.md)，安装授权另行记录。
6. 在获准的临时样例或项目检查中运行一段最小代码，保存实际控制台输出。Junie、AI Assistant 或其他 agent 接入属于另外的客户端与认证配置。

## 怎么检查成功

在 Help → About 查看并记录 PyCharm 的版本。在所选解释器的 Python Console 输入：

```python
import sys
print(sys.executable)
print(sys.version)
```

输出指向预期解释器，再运行自己的最小样例并核文件保存位置。IDE 能打开不代表依赖、模型配额或 MCP 已连通；本轮未在本机执行这些安装检查。

## 失败时处理

- 提示缺解释器：检查 Python 是否已装、路径是否真实，再选 Python Interpreter；不要把随 PyCharm 的 Java 当 Python。
- `import` 报缺包：在 IDE 所选解释器中检查依赖，不能在另一个系统 Python 装包后宣称修好。
- 下载受限：记录具体域名与报错，尝试另一个 JetBrains 官方域名；未核验的镜像和破解包不作为内置方案。
- 试用功能到期：区分免费核心与 Pro/AI 附加功能，按官网现行授权选择，不伪造付费状态。

## 许可与第三方图片

[统一版说明](https://www.jetbrains.com/help/pycharm/unified-pycharm.html)介绍免费核心与 Pro 试用。[JetBrains 许可 FAQ](https://sales.jetbrains.com/hc/en-gb/articles/360021922640-Can-I-use-free-versions-of-IntelliJ-IDEA-and-PyCharm-for-developing-commercial-proprietary-software)明确免费核心可用于商业软件开发；这不改变 MiracleHarness 的许可，也不包含全部 Pro 或 AI 服务。本项目不附安装器或 JetBrains 程序代码。

[-](https://www.jetbrains.com/pycharm/)

Copyright © 2026 JetBrains s.r.o. PyCharm and the PyCharm logo are trademarks of JetBrains s.r.o. 官方标识和产品示例按[JetBrains 品牌规范](https://www.jetbrains.com/company/brand/)原样用于文档指称，未声称私下取得独立品牌授权、合作或背书。来源与 SHA-256 见[标识记录](../应用图片/来源.md)和[示例图记录](../应用截图/来源.md)。

## 官方来源与核验范围

核验日期：2026-10-05。只读核对官网、安装、免费核心、快速入门与解释器文档，未试装、登录或验本机环境。

- [中国站 Windows 安装](https://www.jetbrains.com.cn/help/pycharm/installation-guide.html)
- [全球站安装](https://www.jetbrains.com/help/pycharm/installation-guide.html)
- [快速入门](https://www.jetbrains.com/help/pycharm/quick-start-guide.html)
- [配置解释器](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html)

[返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
