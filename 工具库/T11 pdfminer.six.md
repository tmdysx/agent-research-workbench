---
编号: T11
名字: pdfminer.six
类别: 技术栈
一句话: 后台从 PDF 里抽字：拖进文献时在第一页找 DOI、标题
检查: python -m pip show pdfminer.six
在哪: %LOCALAPPDATA%\Programs\Python\Python312
配套技能:
---
# T11 pdfminer.six

## 用在哪

- 文献入库（文献蓝图 S2-1）：拖一篇 PDF 进来，后台读第一页的字，找 DOI（`10.` 开头那串）、标题，先填进 信息.json；剩下的交给 agent 补
- 全站检索要搜原文时也用它抽字

## 为什么选

- 纯 Python，许可证 MIT（开源发布没问题）；这台电脑已经装了
- 不用 PyMuPDF：它是 AGPL

## 怎么调

```python
from pdfminer.high_level import extract_text
text = extract_text("原文.pdf", maxpages=1)
```

## 改动注意

- 写进 `backend/requirements.txt`（新电脑装的时候一起装）；升级先问人
