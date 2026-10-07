# PyCharm · 国外安装方案

使用 JetBrains 全球官网的当前统一版 PyCharm。免费核心、Pro 附加能力与 AI 服务分别核对；国际下载渠道不替代账号认证。

## 官方入口

- [全球官网下载](https://www.jetbrains.com/pycharm/download/)
- [全球站安装指南](https://www.jetbrains.com/help/pycharm/installation-guide.html)
- [完整安装和用途](../开发工具/pycharm.md)

## 安装与真实核对

1. 按官网当前要求确认 Windows 版本、内存、磁盘及 x64 / ARM64 架构，选正式发行。
2. 用 Toolbox 管理或独立 `.exe` 安装；位置不在内置资料中，不另装 Java，不自动替换已有环境。
3. 选自己的项目与实际 Python Interpreter，已有有效环境优先复用；初次没有 Python 时先按 Python 指南准备。
4. Help → About 记录 IDE 版本，Python Console 核解释器完整路径，再运行自己的临时测试。

```python
import sys
print(sys.executable)
print(sys.version)
```

指南编写时没有执行安装、创建环境、登录或装包；以上输出必须由所选解释器真实产生。

## 授权、账号与失败处理

[统一版说明](https://www.jetbrains.com/help/pycharm/unified-pycharm.html)区分免费 Python/Jupyter 核心与 Pro 试用。免费核心的商业开发许可见[官方 FAQ](https://sales.jetbrains.com/hc/en-gb/articles/360021922640-Can-I-use-free-versions-of-IntelliJ-IDEA-and-PyCharm-for-developing-commercial-proprietary-software)；Pro、Junie、AI Assistant 或外部 agent 的服务资格另核，不由此卡推断免费或已登录。

下载失败记录具体地址和报错，可对照[中国官网下载](https://www.jetbrains.com.cn/pycharm/download/)；IDE 运行失败先核架构、系统和解释器，import 失败先核同一环境的依赖。模型额度问题不通过重装 IDE 解决。

核验日期：2026-10-05。只读核官网、安装与许可资料，未实测海外各地区网络、账户或本机安装。图片来源见[主指南](../开发工具/pycharm.md)。

[国内方案](../国内方案/pycharm.md) · [返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
