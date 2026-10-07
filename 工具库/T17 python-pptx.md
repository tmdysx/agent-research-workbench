---
编号: T17
名字: python-pptx · python-docx · openpyxl
类别: 技术栈
一句话: 后台用的 Python 办公库：PPT 列出每页的字和图（不装插件时）；agent 做 Word / Excel / PPT 文件
检查: python -m pip show python-pptx python-docx openpyxl
在哪: %LOCALAPPDATA%\Programs\Python\Python312
配套技能:
---
# T17 python-pptx · python-docx · openpyxl

## 用在哪

- **python-pptx**：模块页点开 pptx，后台把每页的标题、文字（带缩进）、表格、讲稿读出来，图片一张张给网页（`backend/office.py`）。照原样一页页翻要装「PPT 预览」插件（总蓝图 S1-11）
- **python-docx、openpyxl**：agent 要做 Word、Excel 文件时用；以后网页里「Excel 改几格」也用 openpyxl

## 为什么选它

- 都是 MIT，纯 Python，这台电脑已装；不引新语言
- openpyxl 读不了样式表不标准的表格（作者桌面有一份），所以**看** Excel 用网页那边的 SheetJS（T15），openpyxl 只管写

## 怎么调

- 检查：`python -m pip show python-pptx`（另外两个：`python-docx`、`openpyxl`）
- agent 做文件：做好放进对应模块（PPT 放「汇报」，表格放用到它的模块），文件名写清是什么，网页上直接能看

## 改动注意

- 新电脑要装：`python -m pip install python-pptx python-docx openpyxl`
