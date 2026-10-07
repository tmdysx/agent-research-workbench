# Visual Studio Code · 安装与使用

VS Code 是微软的代码编辑器。它可以编辑本项目的 Python、HTML、Markdown，也可通过扩展调试 Python 和 C/C++；解释器、编译器和 agent 客户端需要另行准备。

-

图来自官方界面文档，原样保存；是文档示例，不是本机安装截图。

## 输入、调用与输出

输入：获准修改的项目文件或临时样例。调用：在 VS Code 打开项目目录，手工编辑，或在其终端调用已确认路径的工具。输出：文件修改、编译或运行日志。安装编辑器不会自动接入本项目 MCP，也不会自行启动模型。

## 官网与下载

- [微软官方下载](https://code.visualstudio.com/Download)
- [Windows 安装说明](https://code.visualstudio.com/docs/setup/windows)
- [国内方案](../国内方案/vscode.md) · [国外方案](../全球方案/vscode.md)

国内与国外均使用微软官方分发；没有核到独立官方国内镜像，不以未知网盘或代理替代。

## Windows 安装步骤

1. 在 Windows“设置 → 系统 → 关于”核对系统类型，选择 x64 或 ARM64 的当前 Windows 发行。不要把架构名称当版本。
2. 普通单人使用优先 User Installer，通常无需管理员权限，默认装在 `%LOCALAPPDATA%/Programs/Microsoft VS Code`。需要全机共享时才选 System Installer 并核管理员权限；ZIP 可作便携方式，但须自行更新。
3. 选择非内置的安装位置。按需要勾选 PATH 或右键“通过 Code 打开”，文件关联由用户决定，不替换现有编辑器配置。
4. 安装后新开 PowerShell，先检查 `code --version` 与实际路径；命令不存在时从开始菜单打开 VS Code，或使用已确认的可执行文件完整路径。
5. 使用“文件 → 打开文件夹”选择自己的项目根，先读 `AGENTS.md`。Python 工作需要另装 Python 并选择真实解释器；C/C++ 工作先读[编译工具指南](cpp-toolchain.md)。扩展安装并不自带这些运行环境。
6. 如要在编辑器里使用 agent，选择自己的客户端或扩展，再依其官方 MCP 文档配置本项目；不要把普通编辑器当已完成认证的 agent。

## 怎么检查成功

以下命令只作操作说明，本轮没有运行安装或验收这台电脑的 VS Code。

```powershell
code --version
Get-Command code
```

版本能返回，命令路径指向刚确认的安装目录。再打开一份授权的临时 Markdown 文件，保存并重新读取，确认实际保存位置。`code .` 会打开当前目录；先确认终端所在目录就是要处理的项目。

## 失败时处理

- `code` 不存在：重新开终端，核安装器的 PATH 选项；已有多份版本时先记录 `Get-Command code -All` 的实际结果，再选一份。
- 能打开编辑器但 Python/C++ 跑不了：核解释器或编译器路径，编辑器本身不包含这些工具。
- 能下载编辑器但装不了扩展：微软下载分发与 Marketplace 是不同服务。按[官方网络说明](https://code.visualstudio.com/docs/setup/network)记录失败域名、时间和报错，交给自己的网络管理员处理，不绕过证书或安全配置。

## 许可与第三方图片

微软产品使用条款与源码 MIT 许可分别见[Visual Studio Code 产品许可](https://code.visualstudio.com/license)和[源码 LICENSE](https://github.com/microsoft/vscode/blob/main/LICENSE.txt)。本项目只保存链接、原创中文指南和原样识别图，不捆绑或改发微软安装程序。

[-](https://code.visualstudio.com/)

Visual Studio Code 名称与图标属于 Microsoft；依[官方品牌页](https://code.visualstudio.com/brand)原样用于文档识别和官网链接，不作 MiracleHarness 标识或背书。图标与官方文档示例的源地址、SHA-256 见[小标识来源](../应用图片/来源.md)和[示例图来源](../应用截图/来源.md)。

## 官方来源与核验范围

核验日期：2026-10-05。只读核对官方下载、Windows 安装、网络、界面与品牌资料；未实测各地网络、扩展登录、MCP 或本机安装。

- [Windows 安装](https://code.visualstudio.com/docs/setup/windows)
- [界面与文档示例](https://code.visualstudio.com/docs/getstarted/userinterface)
- [C/C++ 与外部编译器](https://code.visualstudio.com/docs/cpp/config-mingw)

[返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
