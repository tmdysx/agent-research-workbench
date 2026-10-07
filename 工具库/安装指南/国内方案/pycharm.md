# PyCharm · 国内安装方案

使用 JetBrains 中国官网提供的当前统一版 PyCharm，核心 Python / Jupyter 功能免费，Pro 和 AI 附加能力另外核授权。

## 官方入口

- [中国官网下载](https://www.jetbrains.com.cn/pycharm/download/)
- [中国站安装指南](https://www.jetbrains.com.cn/help/pycharm/installation-guide.html)
- [完整指南](../开发工具/pycharm.md)

## 按顺序操作

1. 查 Windows 10/11、x64 / ARM64 与官网当前硬件要求，下载系统对应安装器；不要再找旧版 Community 单独入口。
2. 按官方选择 Toolbox 或独立安装器；放非内置用户目录，文件关联与 PATH 由本人决定。PyCharm 自带 Java 运行时，Python 解释器单独准备。
3. 打开自己的项目，在 Python Interpreter 选择已有 Python 或项目虚拟环境，核路径与平台 MCP 配置是否一致。
4. 在 Help → About 记 IDE 版本，在 Python Console 检查下列输出，再运行一个获准的小样例。

```python
import sys
print(sys.executable)
print(sys.version)
```

本次写指南没有执行安装、新建虚拟环境或装包；检查须在 IDE 真正选中的解释器中进行。

## 免费核心、账号与 AI

统一版安装可能提供 Pro 试用，试用结束可继续免费核心。国内官网下载并不自动授予 Pro、Junie、AI Assistant 或模型服务资格；账号和地区要求以所选服务当前官方条款为准。免费核心可用于商业软件开发，详见[官方 FAQ](https://sales.jetbrains.com/hc/en-gb/articles/360021922640-Can-I-use-free-versions-of-IntelliJ-IDEA-and-PyCharm-for-developing-commercial-proprietary-software)，不等于所有功能都免费。

## 失败时处理与核验

中国站下载失败保留地址、时间和完整报错，可对照[全球官网下载](https://www.jetbrains.com/pycharm/download/)，不改用未经核实的破解包或镜像。IDE 能开但导入失败时先核解释器与依赖；不要在另一个 Python 上装包。

核验日期：2026-10-05。只读核两套官方域名与文档；没有安装、登录、验证各地可达或开启付费试用。标识、界面示例与条款见[主指南](../开发工具/pycharm.md)。

[国外方案](../全球方案/pycharm.md) · [返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
