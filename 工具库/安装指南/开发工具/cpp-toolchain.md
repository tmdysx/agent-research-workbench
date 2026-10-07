# C/C++ 编译工具 · MSYS2 / GCC 安装与使用

C、C++ 是语言；这里选 MSYS2 的 UCRT64 GCC 工具链作为 Windows x64 的具体实现，包含 C/C++ 编译器与调试工具。VS Code 的 C/C++ 扩展负责编辑和调试接入，不自带编译器。已有项目使用 MSVC、Clang 或其他工具链时，先遵循项目约定，不替换环境。

-

这是 MSYS2 官网的安装文档示例，未修改，不代表本机已安装、命令已运行或现在的软件版本。

## 输入、调用与输出

输入：获准的 C/C++ 源码与项目构建说明。调用：明确选择 UCRT64，运行 `gcc`、`g++` 或构建脚本。输出：可执行文件、构建日志和调试信息。编译器不提供模型账号，不等于 agent 能自动领取任务。

## 下载与方案

- [MSYS2 官网与当前安装器](https://www.msys2.org/)
- [国内方案：中国科大镜像与核对](../国内方案/cpp-toolchain.md)
- [国外方案：MSYS2 官方分发](../全球方案/cpp-toolchain.md)

本方案面向 Windows 10（1809 或更新）/11 x64。ARM64 本机原生工具链需另核 CLANGARM64 与项目依赖；不要把本页 x64 GCC 命令直接套为 ARM64 原生方案。MSYS2 已将 MINGW64 列为弃用环境，新 x64 示例采用 UCRT64。

## 安装步骤

1. 从所选官方或镜像维护方入口取得当前安装器，核发行者、文件名和签名/校验资料。软件可放在非内置工具目录，例如用户指定的 `msys64`；目录宜简短、无空格和非 ASCII 字符。若项目工具目录的完整路径含中文，另选用户指定的 ASCII 工具目录并将真实路径记入工具卡。
2. 如项目路径含中文，工具本体仍放无空格的 ASCII 路径；需要编译时先用获准的临时 ASCII 工作目录验证，不擅自搬动项目。
3. 打开 **MSYS2 UCRT64** 终端，先完成整个系统更新。下面是 Bash/MSYS2 命令，不能直接贴到 PowerShell：

```bash
pacman -Syu
```

若提示必须关闭终端，按提示关闭并重新打开 UCRT64，重复完整更新至没有待更新项。不要用日常局部更新 `pacman -Sy` 代替完整更新。

4. 安装 GCC 与基础构建工具，阅读安装清单再确认：

```bash
pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain
```

5. 在同一个 UCRT64 终端检查版本和路径：

```bash
which gcc
gcc --version
g++ --version
gdb --version
```

`which gcc` 应指向 `/ucrt64/bin/gcc`。在 VS Code 或其他程序选择对应安装目录的 `ucrt64/bin/g++.exe`；不要误选 `usr/bin` 或其他 ABI 环境。需要 PowerShell PATH 时由用户显式配置，安装指南不自动改全局变量。

## 最小编译检查

在自己允许写入的临时目录手工新建 `hello.cpp`：

```cpp
#include <iostream>
int main() { std::cout << "hello\n"; return 0; }
```

然后在该目录的 UCRT64 终端执行：

```bash
g++ hello.cpp -o hello-cpp.exe
./hello-cpp.exe
```

输出 `hello` 且退出正常，才记录 C++ 最小检查通过。C 文件用 `gcc hello.c -o hello-c.exe` 检查；C++ 用 `g++` 以正确链接 C++ 标准库。本轮只编写这些说明，没有运行编译或安装。

## 失败时处理

- 找不到 `gcc`：确认打开 UCRT64，检查是否安装 `mingw-w64-ucrt-x86_64-toolchain`，不要只检查编辑器扩展。
- 包下载慢或报镜像错误：先看[国内方案](../国内方案/cpp-toolchain.md)与维护方帮助；记录失败包、地址和报错，不关闭签名验证、不改证书。
- 编译后 DLL 或链接异常：核编译器路径、ABI 和项目依赖，不能混用 MSYS、MINGW64、UCRT64 与 MSVC 的库来凑结果。
- 老项目规定 MSVC：沿项目构建说明使用微软官方 Build Tools；本页不是替换它的授权，不用 GCC 安装成功冒充项目已兼容。

## 许可和来源图片

MSYS2 是多组件分发，按[MSYS2 许可说明](https://www.msys2.org/license/)核各包。GCC 使用 GPL 及适用的运行库例外，见[GCC 运行库许可说明](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html)；不能将所有包一概说成 MIT，也不以编译器许可替代自己程序及依赖的许可核对。本项目不附 GCC、MSYS2 安装器或它们的源码。

[-](https://www.msys2.org/)

图标识别本方案实际采用的 MSYS2，不是 C 或 C++ 语言的统一官方商标。标识与文档图版权归原方，未声明无限制图片再分发或改用本项目许可；来源、原字节与 SHA-256 见[标识记录](../应用图片/来源.md)和[示例图记录](../应用截图/来源.md)。

## 官方来源与核验范围

核验日期：2026-10-05。已只读核 MSYS2 环境、更新、镜像和 VS Code 的 GCC 接入文档，未下载安装器、执行 pacman、试编译或验各地可达性。

- [MSYS2 环境](https://www.msys2.org/docs/environments/)
- [完整系统更新](https://www.msys2.org/docs/updating/)
- [官方列明的镜像](https://www.msys2.org/dev/mirrors/)
- [VS Code GCC 配置](https://code.visualstudio.com/docs/cpp/config-mingw)

[返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。


## 已有 MSVC 工程的官方选项

项目已采用 MSVC 或 Visual Studio 构建时，先沿用原工具链，不自动换成 GCC。微软官方 [Build Tools 下载入口](https://visualstudio.microsoft.com/downloads/) 位于 Tools for Visual Studio 分类；安装和组件选择按 [Microsoft 官方 C/C++ 安装说明](https://learn.microsoft.com/zh-cn/cpp/build/vscpp-step-0-installation?view=msvc-170)，按项目需要选择「使用 C++ 的桌面开发」、MSVC 工具集与 Windows SDK，版本和使用许可另核。安装后在对应 Developer Command Prompt 检查 `cl`，不要把普通 PowerShell 中命令不存在当成未安装。这里只给官方路径与操作说明，本轮未下载或执行安装器、未接受条款、未验证本机 MSVC。
