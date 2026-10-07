# C/C++ 编译工具 · 国内安装方案

选 MSYS2 的 UCRT64 GCC 工具链，默认面向 Windows x64。中国科大 USTC 镜像列在 MSYS2 官方一级镜像清单；它是同步镜像，原发行者仍是 MSYS2，不冒称厂商中国独立版。

## 来源与实际核验

- [MSYS2 官方安装与发行](https://www.msys2.org/)
- [中国科大安装器镜像目录](https://mirrors.ustc.edu.cn/msys2/distrib/x86_64/)
- [USTC 镜像帮助](https://mirrors.ustc.edu.cn/help/msys2.html)
- [MSYS2 官方镜像列表](https://www.msys2.org/dev/mirrors/)
- [完整编译工具指南](../开发工具/cpp-toolchain.md)

已核官方镜像列表和维护方帮助。本次读取上述安装器目录发生 TLS/SSL 错误，没有实际下载安装器，不承诺当前目录在此电脑或全国可达。目录受限、缺发行或未同步时使用 MSYS2 官网，不猜其他站点。

## 按顺序操作

1. 在官网确认当前安装器和支持系统，再到镜像对照同名 x64 发行、签名或校验信息。Windows ARM64 原生方案另外核，不照搬本页 GCC 命令。
2. 软件安装在非内置、无空格与非 ASCII 字符的短路径。项目路径含中文时先用授权的 ASCII 临时目录测试，不迁移项目文件。
3. 打开 MSYS2 UCRT64，先完整系统更新；提示关闭时照做，重开 UCRT64 再完整更新。
4. 网络确有需要时，按维护方帮助查看 `/etc/pacman.d/mirrorlist.msys` 与 `mirrorlist.mingw`，先备份，再将已有 USTC 对应项移到优先位置。不要自动覆盖整份配置、关闭签名验证或乱混环境。
5. 在 UCRT64 安装工具链并核命令路径。下面属于 MSYS2 Bash，不是 PowerShell：

```bash
pacman -Syu
pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain
which gcc
gcc --version
g++ --version
gdb --version
```

更新后若要关闭终端，必须先按提示处理再做下一行。看到 `/ucrt64/bin/gcc` 后按主指南编译自己的最小例子，记录实际输出。

## 账号、许可与失败处理

本地编译不需要模型账号。MSYS2/GCC 各包许可另核，agent/MCP 认证与编译器无关。镜像报错先记录包名、地址和时间，备份后恢复原镜像清单或选择官方列表中的可用源；保持完整 `pacman -Syu` 更新，不教普通用户做局部升级。

核验日期：2026-10-05。仅核官方与 USTC 帮助，未下载安装器、执行包更新、试编译、登录或改全局 PATH。原样标识与官方文档示例来源见[主指南](../开发工具/cpp-toolchain.md)。

[国外方案](../全球方案/cpp-toolchain.md) · [返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
