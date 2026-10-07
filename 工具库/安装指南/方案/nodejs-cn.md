# Node.js · 国内安装方案

Node 二进制可用 TUNA；npm 包另用 npmmirror，二者不是同一镜像。

![Node.js准备图](../图示/nodejs.svg)

## 下载和安装来源

- [官方软件 / 项目入口](https://nodejs.org/)
- [本方案下载 / 安装说明](https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/)
- [完整安装、用途与排查指南](../%E8%BD%AF%E4%BB%B6/Node.js.md)

国内镜像方案：TUNA 同步 nodejs.org/dist；npm 依赖可按各 agent 说明对当前命令使用社区 npmmirror。

软件程序不放内置，位置由用户选择；当前实例可放非内置工具目录，不能让新项目复制整个安装环境。国内镜像是可选来源，下载来源、软件原发行者、模型服务是不同对象。

## 按顺序操作

1. 先确认你选的 CLI 当前 Node 最低版本，再到 TUNA nodejs-release 选系统架构与安装包。

2. 自选非内置位置，安装后新开终端。

3. 检查 node/npm 版本；不因为 Node 下载镜像可用而把清华写成 npm registry。

## 账号、模型和服务地区

Node/npm 本地命令不用模型账号；模型认证、服务地区由 agent 自身决定。

## 核对真实结果

node 和 npm 两个版本可读，版本满足所选 CLI；平台原生网页并不要求 Node。

以下命令仅作说明，写文档时没有执行安装、登录、启用或启动。先读命令注释和主指南；有占位路径时替换为自己真实值。安装命令只给本次选择来源，不写全局 pip/npm 配置。

```powershell
node --version
npm.cmd --version
```

## 下载或运行失败

1. 记录失败的具体地址、步骤、时间与完整报错，先确认系统架构、版本和解释器。
2. 镜像缺包或不同步时对照原官方发行；没有核到国内独立渠道的条目保留官方入口，不猜代理站和网盘。
3. 账号、配额、地区限制归模型服务，包下载成功不能替代服务检查；[国内 / 国外方案总览](../国内与国外方案.md)提供另一入口。
4. 无当前安装检查适配时显示未检查；没有实际 MCP 连接结果也不补成已连通。当前授权不足的动作依项目原有流程记录待决定。

## 来源与核验

核验日期：2026-10-05。只读检查官方或镜像维护方说明；没有实测全国网络、安装客户端或登录所有账号。清华镜像由 TUNA 维护，npmmirror 是社区包镜像，不冒称软件厂商的国内发行。

- [Node 下载](https://nodejs.org/en/download)
- [TUNA Node 说明](https://mirrors.tuna.tsinghua.edu.cn/help/nodejs-release/)
- [npmmirror 自述](https://npmmirror.com/)

[返回完整指南](../%E8%BD%AF%E4%BB%B6/Node.js.md) · [安装总览](../从这里开始.md)
