# 后台依赖 · 国内安装方案

对当前命令临时选清华 PyPI 镜像，不修改全局 pip 配置。

![后台依赖准备图](../图示/backend-dependencies.svg)

## 下载和安装来源

- [官方软件 / 项目入口](https://pip.pypa.io/)
- [本方案下载 / 安装说明](https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple)
- [完整安装、用途与排查指南](../%E8%BD%AF%E4%BB%B6/%E5%90%8E%E5%8F%B0%E4%BE%9D%E8%B5%96.md)

国内镜像方案：TUNA PyPI，来源是各包公开 PyPI 发行。

软件程序不放内置，位置由用户选择；当前实例可放非内置工具目录，不能让新项目复制整个安装环境。国内镜像是可选来源，下载来源、软件原发行者、模型服务是不同对象。

## 按顺序操作

1. 在项目根使用后台实际 Python，先确认 python -m pip --version。

2. 按项目 requirements 安装；当前命令加 -i 临时索引参数。

3. pip check 后按主指南 import 检查，再启动后台；虚拟环境需显式使用其 python.exe。

## 账号、模型和服务地区

依赖安装不需要模型账号；镜像只供包下载，不提供 agent 登录或模型服务。

## 核对真实结果

依赖 import 和 pip check 正常，网页项目名称匹配；不能因镜像访问成功称工作台已启动。

以下命令仅作说明，写文档时没有执行安装、登录、启用或启动。先读命令注释和主指南；有占位路径时替换为自己真实值。安装命令只给本次选择来源，不写全局 pip/npm 配置。

```powershell
python -m pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r backend/requirements.txt
python -m pip check
```

## 下载或运行失败

1. 记录失败的具体地址、步骤、时间与完整报错，先确认系统架构、版本和解释器。
2. 镜像缺包或不同步时对照原官方发行；没有核到国内独立渠道的条目保留官方入口，不猜代理站和网盘。
3. 账号、配额、地区限制归模型服务，包下载成功不能替代服务检查；[国内 / 国外方案总览](../国内与国外方案.md)提供另一入口。
4. 无当前安装检查适配时显示未检查；没有实际 MCP 连接结果也不补成已连通。当前授权不足的动作依项目原有流程记录待决定。

## 来源与核验

核验日期：2026-10-05。只读检查官方或镜像维护方说明；没有实测全国网络、安装客户端或登录所有账号。清华镜像由 TUNA 维护，npmmirror 是社区包镜像，不冒称软件厂商的国内发行。

- [TUNA PyPI 使用说明](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)
- [pip 官方](https://pip.pypa.io/en/stable/cli/pip_install/)

[返回完整指南](../%E8%BD%AF%E4%BB%B6/%E5%90%8E%E5%8F%B0%E4%BE%9D%E8%B5%96.md) · [安装总览](../从这里开始.md)
