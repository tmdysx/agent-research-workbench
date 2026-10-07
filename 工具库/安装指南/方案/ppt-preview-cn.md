# PPT预览 · 国内安装方案

已有 PowerPoint 可直接用；缺转换器时可选 TUNA LibreOffice。

![PPT预览准备图](../图示/ppt-preview.svg)

## 下载和安装来源

- [官方软件 / 项目入口](https://www.libreoffice.org/)
- [本方案下载 / 安装说明](https://mirrors.tuna.tsinghua.edu.cn/libreoffice/)
- [完整安装、用途与排查指南](../%E8%BD%AF%E4%BB%B6/PPT%E9%A2%84%E8%A7%88.md)

国内方案：插件本地随带；可选清华 LibreOffice 镜像，非必须购买 Office。

软件程序不放内置，位置由用户选择；当前实例可放非内置工具目录，不能让新项目复制整个安装环境。国内镜像是可选来源，下载来源、软件原发行者、模型服务是不同对象。

## 按顺序操作

1. 先检查已有 PowerPoint 或 LibreOffice，不重复装两套。

2. 确实缺转换器时沿 LibreOffice 国内方案选择官方发行的镜像安装包。

3. 用获准 PPT 只读转出新 PDF，检查排版与后台转换器实际来源。

## 账号、模型和服务地区

本地 LibreOffice 转换不需云账号；PowerPoint 的正版安装及激活按用户自身授权。

## 核对真实结果

真实样例 PDF 可打开，原 PPT 未改；插件通过不自动判定 LibreOffice 已安装。

以下命令仅作说明，写文档时没有执行安装、登录、启用或启动。先读命令注释和主指南；有占位路径时替换为自己真实值。安装命令只给本次选择来源，不写全局 pip/npm 配置。

```powershell
Test-Path "<实际 LibreOffice 目录>/program/soffice.exe"
```

## 下载或运行失败

1. 记录失败的具体地址、步骤、时间与完整报错，先确认系统架构、版本和解释器。
2. 镜像缺包或不同步时对照原官方发行；没有核到国内独立渠道的条目保留官方入口，不猜代理站和网盘。
3. 账号、配额、地区限制归模型服务，包下载成功不能替代服务检查；[国内 / 国外方案总览](../国内与国外方案.md)提供另一入口。
4. 无当前安装检查适配时显示未检查；没有实际 MCP 连接结果也不补成已连通。当前授权不足的动作依项目原有流程记录待决定。

## 来源与核验

核验日期：2026-10-05。只读检查官方或镜像维护方说明；没有实测全国网络、安装客户端或登录所有账号。清华镜像由 TUNA 维护，npmmirror 是社区包镜像，不冒称软件厂商的国内发行。

- [LibreOffice 官方](https://www.libreoffice.org/download/)
- [TUNA 镜像](https://mirrors.tuna.tsinghua.edu.cn/libreoffice/)

[返回完整指南](../%E8%BD%AF%E4%BB%B6/PPT%E9%A2%84%E8%A7%88.md) · [安装总览](../从这里开始.md)
