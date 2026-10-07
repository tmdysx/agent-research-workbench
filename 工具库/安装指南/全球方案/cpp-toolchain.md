# C/C++ 编译工具 · 国外安装方案

使用 MSYS2 官方安装器和默认镜像选择，Windows x64 新示例采用 UCRT64 的 GCC/G++。已有工程的 MSVC、Clang 与库 ABI 约定优先，不自动换编译器。

## 官方入口

- [官网与安装器](https://www.msys2.org/)
- [官方环境说明](https://www.msys2.org/docs/environments/)
- [完整更新说明](https://www.msys2.org/docs/updating/)
- [完整指南](../开发工具/cpp-toolchain.md)

## 安装与检查

1. 核 Windows 10（1809 或更新）/11 与 x64 架构，取官网当前正式发行；ARM64 原生工具链另核 CLANGARM64 和项目依赖。
2. 选择非内置的短 ASCII 路径，打开 MSYS2 UCRT64；不把安装环境复制进新项目的内置资料。
3. 先完整更新系统；需要关闭终端时按提示关闭，重新打开 UCRT64 后重复更新再安装工具链。
4. 在同一个 UCRT64 终端执行以下检查，保存实际版本、路径与编译日志：

```bash
pacman -Syu
pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain
which gcc
gcc --version
g++ --version
gdb --version
```

这是 MSYS2 Bash 命令，不能贴到 PowerShell。前面的更新如果要求重启终端，先处理完再执行安装命令。文档编写时没有运行任何上述安装或编译。

## 项目接入与账号

在 VS Code 的 C/C++ 配置选择真实 `ucrt64/bin/g++.exe`，按主指南先编译一个授权样例，再按项目构建说明干活。不要把不同环境的 DLL、运行库和编译器拼接。本地工具链无需模型账户；agent、MCP 与其他依赖分别准备。

## 失败时处理与许可

包下载失败记录准确包名、源和错误，读[官方镜像说明](https://www.msys2.org/docs/mirrors/)；按维护方指引调整所选安装的镜像，保留备份与签名验证。不要用局部更新 `pacman -Sy` 当日常更新方案。

MSYS2 各包分别有许可；[MSYS2 许可](https://www.msys2.org/license/)和[GCC 运行库说明](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html)是核对入口，本项目不附程序或第三方代码。

核验日期：2026-10-05。只读核官方文档；未下载安装器、执行 pacman、试编译或实测各国网络。需要国内镜像时看[国内方案](../国内方案/cpp-toolchain.md)，当前该镜像目录在本机读取受限。

[返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
