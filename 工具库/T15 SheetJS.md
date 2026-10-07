---
编号: T15
名字: SheetJS
类别: 技术栈
一句话: 在网页里看 Excel（xlsx、xls）：每个工作表、每一格、底色、合并格，公式显示算好的结果
检查: 文件 工具库/下载/sheetjs/xlsx.full.min.js
在哪: 工具库/下载/sheetjs
配套技能:
---
# T15 SheetJS

## 用在哪

- 模块页、全站检索点开一个 xlsx / xls：网页自己读、自己画成表格（总蓝图 S1-10），不经过 agent、不用装别的
- 表头、行号钉住；几个工作表能切；太大的只画前 3000 行、100 列

## 为什么选它

- 社区版 0.20.3，Apache-2.0，从官方 cdn.sheetjs.com 下的（npm 上的 xlsx 包停在旧版，官方不再往 npm 发）
- 比 Python 的表格库宽容：作者桌面上有一份台账 Python 打不开（样式表不标准），它能读
- 颜色：读得出格子底色（直接写的颜色、主题色加深浅）；字体、边框社区版不读，网页里统一画细格线

## 怎么调

- 网页里：`/lib/sheetjs/xlsx.full.min.js`，`XLSX.read(数据, {type: 'array', cellStyles: true})`
- 画表格的是 `模板.html` 里的 `xlShow`

## 改动注意

- 升级大版本先问人；只换这一个文件，改 `工具库/下载/清单.md` 的版本和校验
