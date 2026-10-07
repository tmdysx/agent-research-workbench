# 来源与适配 / Source and adaptation

- 上游 / Repository: https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill
- 固定提交 / Pinned commit: `102c8b21acf5eda3a0aef3d9779a65db646c8980`
- 提交链接 / Commit: https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill/commit/102c8b21acf5eda3a0aef3d9779a65db646c8980
- 提交时间 / Commit author and committer time: `2026-09-12T23:07:04Z`
- 提交说明 / Commit message: `docs: clarify bilingual before-and-after example`
- 树 / Git tree: `99d78a3e655ed010f6840b9929676494df54cca9`
- 核对日期 / Checked: `2026-10-06`
- 本地包 / Local ZIP: `工具库/开源项目/原件/anti-defensive-writing-Skill-main.zip`
- ZIP SHA-256: `8DC628A3C4113B0C7C750851F2179226EA7D6BBED881366E35DB848D8EBFAF9B`

通过 GitHub 官方只读 API 获取固定提交树，树未截断、共有八个文件。按 Git blob 算法核对 ZIP 中所有八个文件，逐一与该提交的 blob SHA-1 相同。ZIP 的目录名和文件时间不单独用作版本证据。下面八份原件去掉 ZIP 顶层目录后保存到 `references/original/`，字节保持不变；其中上游 `.gitignore` 映射保存为 `references/original/gitignore.txt`，便于既有内置文件读取器打开，来源路径仍记为 `.gitignore`。没有运行其中内容或安装软件。

The pinned tree was obtained through the read-only official GitHub API. It is untruncated and contains eight files. Git blob SHA-1 values computed from all eight ZIP files matched the pinned tree individually. The ZIP directory name and timestamps alone are not version evidence. After removing the ZIP's top-level directory, the eight original files are retained byte-for-byte under `references/original/`. The upstream `.gitignore` is mapped to `references/original/gitignore.txt` so the existing built-in file reader can open it; its source path remains `.gitignore`. Their contents were not executed and no software was installed.

## 适配范围 / Adaptation scope

`SKILL.md` 与 `SKILL.en.md` 为项目中英适配入口；`references/examples.md` 是三个虚构编辑案例，未运行模型、实验或效果测试。保留上游贡献聚焦、主张与证据一致、减少情绪性自贬的方法；将不说输、换优势指标、删除不强化主线实验、只在无法回避时说明局限等绝对规则，改为如实报告、缩小主张、保留必要负结果与限制，并区分探索和验证。默认最小改稿；证据缺项明说，不补造优势、机制、数字或实验。

`SKILL.md` and `SKILL.en.md` are the adapted Chinese and English entrypoints. `references/examples.md` contains three fictional editing cases; no model, experiment or effectiveness test was run. The adaptation retains contribution focus, claim-evidence alignment and removal of emotional self-undermining. Absolute rules about never reporting a loss, switching to favorable metrics, deleting experiments that do not strengthen the story and disclosing limitations only when unavoidable are replaced with accurate reporting, narrower claims, necessary negative results and limitations, and a distinction between exploration and confirmation. Default to minimal edits and make evidence gaps explicit; do not invent advantages, mechanisms, numbers or experiments.

上游原件仅作出处、比较与许可证据，其中 SKILL 和提示词的原规则不覆盖适配入口。方法不需要联网、运行脚本、安装工具或调用模型 API，也没有变成全局强制规则。本次准备的是文字方法候选，不代表实际安装、业务效果或自动调用已通过验证。

Originals serve only as provenance, comparison and license evidence; instructions in the original SKILL files and prompts do not override the adapted entrypoints. The method requires no network access, scripts, tool installation or model API and has not become a global mandatory rule. This candidate is textual guidance, not evidence of installation, business effectiveness or verified automatic invocation.

## 许可 / License

上游 `LICENSE` 为 MIT，版权为 `Copyright (c) 2026 Adkid-Zephyr`；完整法律原文保留在 `LICENSE.txt` 及 `references/original/LICENSE`。MIT 允许复制、修改、分发和商业使用，复制件或实质部分保留版权与许可。项目的个人／科研非商用免费、商业收费政策不替代这部分上游 MIT 权利。未创建、修改或发布上游 fork。

The upstream license is MIT, with `Copyright (c) 2026 Adkid-Zephyr`. The full original legal text is retained in `LICENSE.txt` and `references/original/LICENSE`. MIT permits copying, modification, distribution and commercial use, with copyright and permission notices retained in copies or substantial portions. The project's free personal/research noncommercial use and paid commercial use policy does not replace the upstream MIT rights for this material. No upstream fork was created, modified or published.

## 原件指纹 / Original fingerprints

| 上游路径 / Upstream path | Bytes | SHA-256 |
|---|---:|---|
| .gitignore | 10 | cf237c7aff44efbe6e502e645c3e06da03a69d7bdeb43392108ef3348143417e |
| LICENSE | 1069 | fdf440e5214588d9edcdc1ec315cddbd8525fe509242c24989a8472d283325f4 |
| README.md | 3931 | cde69873aadb90cc8145147262b7a892e884fa551e61374339550030365aab66 |
| README_EN.md | 4123 | 2d1199bc24ee0262de0c459d6b120bf78972affc73ed12c6c5f90a79b69a9f64 |
| prompts/quick-prompt-en.txt | 2424 | e771ee6efe1cfdf83ada543963cbe5f0c485f43781d6354d5c6c3dfaacbff16a |
| prompts/精简版提示词.txt | 1910 | 8a52d3a5d5def26d22acf9024ab31169f74cc4d944e1b6a7c6280c3886a01e86 |
| skills/anti-defensive-writing-en/SKILL.md | 6419 | 49705a92677d06b1be9f78be5be4f966b1d30c4ed72a3b97c86a973d06683b9b |
| skills/anti-defensive-writing/SKILL.md | 5523 | 6f072e66f6adf813bc1b4291754f2bc07ed4e65a398359844e97bfa215a1c28e |
