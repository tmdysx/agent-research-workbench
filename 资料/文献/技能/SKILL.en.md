---
name: Literature
description: Manage original PDFs, interactive downloads and close reading in the Literature module, with unified sticky notes and traceable explanations.
---

# Literature module

Read the Chinese canonical method in `SKILL.md` and the applicable governance rules before working. Explicit user instructions take precedence.

## Two entrances

- **Downloads**: add a URL or DOI through the existing download API. Supply verified authors, year, venue, purpose and source. Use official or lawfully accessible sources. The user or local download program obtains the PDF; do not bypass paywalls or assume an institutional subscription permits redistribution.
- **Library** (default): manage originals and open close reading in the same page. Keep the file directory collapsed by default. Legacy links remain readable.

The original PDFs live in `原文/`; each `解读/L…/` folder holds metadata, text, images and diagrams. Preserve L identifiers and explicit original-file associations. Use the library import API for numbering and deduplication. Never invent missing metadata or overwrite originals.

## Reading and notes

Write explanations in `解读/L…/文本/讲解.md`, quick summaries in `速读.md`, and authorized translations in `译文.md`. Start with the agent identity and date. Use headings such as `## 第 3 页` so the reader can synchronize pages. Distinguish source claims from your interpretation; do not invent numbers or citations.

The quill-and-paper button opens the platform's existing floating sticky note in normal and full-screen reading. The stacked-books button opens the notebook. Preserve human drafts and saved notes. Do not create a dedicated literature notebook or migrate old notes automatically.

Existing `文本/笔记.md` and history remain available as ordinary legacy files. PDF highlights and annotations remain in `批注.json`, managed by the reader. Questions and answers use the platform Q&A with paper, page and quotation references, rather than automatically writing human notes.

Diagrams belong in `图解/`; distinguish schematic examples from measured data and identify their source pages. Use locally available libraries through the existing `/lib/` mechanism.

## Starter example and delivery

`工作台/入门示例.json` explicitly declares the author's own introductory PDF, a short guide and three official research links. Initialization only runs when creating a project or when explicitly requested. It neither fetches third-party PDFs nor modifies existing reading state, explanations or notes. Ordinary GET requests never initialize examples.

Before core edits, follow the project's approved plan, core-lock and snapshot workflow. Deliver with actual checks through the existing delivery interface. This project's authorized `checks-pass` policy finishes a delivery automatically only when all nonempty checks are strictly true. Failed checks require rework; the human can also reject incorrect work. Never mark unchecked work as complete.
