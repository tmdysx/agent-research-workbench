---
编号: T16
名字: docx-preview
类别: 技术栈
一句话: 在网页里看 Word（docx），照原来的排版：标题、表格、边框、勾选框、页眉页脚，一页一页
检查: 文件 工具库/下载/docx-preview/docx-preview.min.js
在哪: 工具库/下载/docx-preview
配套技能:
---
# T16 docx-preview

## 用在哪

- 模块页、全站检索点开一个 docx：网页自己排版（总蓝图 S1-10），不经过 agent、不用装别的
- 老的 .doc 它不认：用「用本机软件打开」，或者以后装插件转

## 为什么选它

- 0.4.1，Apache-2.0；要用 JSZip 3.10.2 解压（MIT；也在 `工具库/下载/jszip/`）
- 照原排版画（mammoth 那类只转出干净的网页、表格边框和字号会丢）
- 验过：作者的请假单（带边框的表格、勾选框、下划线）跟 Word 里一样

## 怎么调

- 网页里先加载 `/lib/jszip/jszip.min.js`，再 `/lib/docx-preview/docx-preview.min.js`，然后 `docx.renderAsync(数据, 容器, null, {inWrapper: true, breakPages: true})`
- 挂在 `模板.html` 的 `mountOffice`

## 改动注意

- 公式、文本框、复杂排版可能走样——这些用「用本机软件打开」
- 升级先问人；换了改 `工具库/下载/清单.md`
