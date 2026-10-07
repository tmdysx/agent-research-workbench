# JupyterLab · 国内安装方案

在独立实验环境用临时 TUNA PyPI 索引；不是后台必装依赖。

![JupyterLab准备图](../图示/jupyterlab.svg)

## 下载和安装来源

- [官方软件 / 项目入口](https://jupyter.org/)
- [本方案下载 / 安装说明](https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple)
- [完整安装、用途与排查指南](../%E8%BD%AF%E4%BB%B6/JupyterLab.md)

国内包镜像方案：TUNA PyPI；Jupyter 是科研工具，不混入工作台后台固定依赖。

软件程序不放内置，位置由用户选择；当前实例可放非内置工具目录，不能让新项目复制整个安装环境。国内镜像是可选来源，下载来源、软件原发行者、模型服务是不同对象。

## 按顺序操作

1. 按主指南在非内置位置建立独立实验环境，并显式用其 python.exe。

2. 使用下面 -i 只给本次 JupyterLab 安装指定镜像。

3. 版本可读后由用户主动启动 jupyter lab，浏览器打开自己的 Notebook。

## 账号、模型和服务地区

本机 Notebook 不需要 Jupyter 云账号；数据、计算资源及外部模型由实验方案另授权。

## 核对真实结果

实际实验环境可查 jupyterlab 版本；Notebook 使用的 kernel 要与实验环境匹配。

以下命令仅作说明，写文档时没有执行安装、登录、启用或启动。先读命令注释和主指南；有占位路径时替换为自己真实值。安装命令只给本次选择来源，不写全局 pip/npm 配置。

```powershell
python -m pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple jupyterlab
python -m jupyterlab --version
```

## 下载或运行失败

1. 记录失败的具体地址、步骤、时间与完整报错，先确认系统架构、版本和解释器。
2. 镜像缺包或不同步时对照原官方发行；没有核到国内独立渠道的条目保留官方入口，不猜代理站和网盘。
3. 账号、配额、地区限制归模型服务，包下载成功不能替代服务检查；[国内 / 国外方案总览](../国内与国外方案.md)提供另一入口。
4. 无当前安装检查适配时显示未检查；没有实际 MCP 连接结果也不补成已连通。当前授权不足的动作依项目原有流程记录待决定。

## 来源与核验

核验日期：2026-10-05。只读检查官方或镜像维护方说明；没有实测全国网络、安装客户端或登录所有账号。清华镜像由 TUNA 维护，npmmirror 是社区包镜像，不冒称软件厂商的国内发行。

- [Jupyter 官方安装](https://jupyter.org/install)
- [TUNA PyPI](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)

[返回完整指南](../%E8%BD%AF%E4%BB%B6/JupyterLab.md) · [安装总览](../从这里开始.md)
