# Visual Studio Code · 国外安装方案

使用微软官方分发与文档，按系统架构选择 Windows 安装器。国际网络能下载编辑器，不等于用户所选 agent 已登录或 MCP 可用。

## 入口

- [官方 Windows 下载](https://code.visualstudio.com/Download)
- [Windows 安装文档](https://code.visualstudio.com/docs/setup/windows)
- [完整指南](../开发工具/vscode.md)

## 安装与核对

1. 查 Windows 系统类型，选 x64 或 ARM64 正式发行。User Installer 适合单用户；System Installer 用于有权限的全机安装。
2. 放在非内置工具目录或默认用户目录，PATH 与右键入口由用户决定。ZIP 方案记录解压目录并自行更新。
3. 新开 PowerShell 查版本和真实命令来源，再打开正确项目根；不把别的项目目录接给 agent。
4. 需要 Python、GCC、语言扩展或 agent 时分别按其指南准备，只安装实际任务要用的能力。

```powershell
code --version
Get-Command code
```

记录实际版本与路径，手工保存并重新读一个获准的临时文件。本文没有执行安装、启动或登录；命令只供用户按需检查。

## 账号、许可与失败处理

本地编辑器无需先有模型账号。Copilot 和其他 agent 的认证、配额、地区与 MCP 配置由相应产品文档决定。Microsoft 产品许可与源码 MIT 许可不同，本模板不附安装程序。

下载或扩展请求失败时保存域名和报错，按[微软网络说明](https://code.visualstudio.com/docs/setup/network)排查；已安装多版本时核实际 `code` 路径，不自动覆盖用户设置。国内入口见[国内方案](../国内方案/vscode.md)，并不承诺独立中国镜像。

核验日期：2026-10-05；只读核官方资料，未实测海外各地区、安装或认证。许可与图片来源见[主指南](../开发工具/vscode.md)。

[返回安装总览](../从这里开始.md)

## 本页的执行范围

这是安装与检查说明，编写时没有安装软件、登录账号、启用插件或启动员工。软件程序放在非内置的工具目录或用户安装目录，例如 `工具库/软件/`；内置只带说明和识别图片。用户可自己按步骤安装；agent 执行安装时须引用对应授权，记录实际来源、版本和路径。

本地编辑、编译与 agent 的模型认证、配额、MCP 配置分别核验；这张指南和图不能证明本机已经具备能力。没有安装检查适配器的卡片保留“未检查”。
