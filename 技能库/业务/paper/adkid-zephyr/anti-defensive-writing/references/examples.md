# 去防御性写作的中英案例 / Bilingual editing examples

以下是三个虚构的短编辑案例，用来说明判断边界；没有运行模型或实验，不构成效果评估。默认只改给定段落。

These are three fictional short editing cases illustrating decision boundaries. No model or experiment was run, and these cases are not an effectiveness evaluation. Edit only the supplied passage by default.

## 1. 有数字的劣势继续保留 / Retain a numerical shortfall

**给定原文 / Input**

“遗憾的是，本方法在数据集 D 上仅达到 91.2% 的准确率，仍低于基线的 93.5%，这说明我们的方法没有价值。”

“Unfortunately, our method achieves only 91.2% accuracy on dataset D, below the baseline's 93.5%, which shows that our method has no value.”

**最小改稿 / Minimal edit**

“本方法在数据集 D 上达到 91.2% 的准确率，低于基线的 93.5%；该结果未显示本方法在此条件下的准确率优势。”

“Our method achieves 91.2% accuracy on dataset D, below the baseline's 93.5%; this result does not show an accuracy advantage under these conditions.”

**判断 / Decision**

去掉情绪词及从局部比较推导整体无价值的结论，保留两个数字、比较方向、数据集和成立条件。不能写成“性能相当”、统计无显著差异或成本权衡，因为原文未提供相应证据。

Remove the emotional framing and the unsupported verdict on the whole method. Retain both numbers, the direction of comparison, the dataset and the conditions. Do not claim comparable performance, statistical nonsignificance or a cost trade-off without evidence.

## 2. 泛化未评估必须说清 / Preserve unevaluated generalization

**给定原文 / Input**

“虽然本方法在两个同领域数据集上提高了准确率，但我们必须承认，跨领域泛化尚未评估。”

“Although our method improves accuracy on two in-domain datasets, we must admit that cross-domain generalization has not been evaluated.”

**最小改稿 / Minimal edit**

“本方法在两个同领域数据集上提高了准确率；跨领域泛化尚未评估。”

“Our method improves accuracy on two in-domain datasets; cross-domain generalization has not been evaluated.”

**判断 / Decision**

两项事实都保留，只消除认错式转折。不能改成“具有跨领域泛化能力”，也不能删除未评估的说明并扩大结论范围。

Retain both facts and remove only the confessional framing. Do not claim cross-domain generalization or remove the unevaluated limitation while expanding the conclusion.

## 3. 错误优势与机制不能补造 / Do not invent an advantage or mechanism

**给定证据和原文 / Supplied evidence and input**

证据只有准确率：本方法 92.1%，基线 93.4%；没有消融或机制检验。原文：“本方法优于基线，证明注意力模块是性能提升的原因。”

The only evidence is accuracy: 92.1% for our method and 93.4% for the baseline; no ablation or mechanism test is available. Input: “Our method outperforms the baseline, proving that the attention module causes the improvement.”

**必要改稿 / Necessary edit**

“本方法准确率为 92.1%，低于基线的 93.4%；这些结果不能证明注意力模块的因果作用。”

“Our method achieves 92.1% accuracy, below the baseline's 93.4%; these results do not establish a causal role for the attention module.”

**判断 / Decision**

原优势主张与数字矛盾，机制主张没有相应证据，应纠正并说明证据缺项。不能编出另一数据集、速度优势、参数优势或新的消融结果来挽救原句；也不替作者自动设计或执行实验。

The claimed advantage contradicts the numbers, and the mechanism claim lacks evidence. Correct the claims and flag the missing evidence. Do not invent another dataset, speed or parameter advantage, or ablation result to rescue the sentence; do not automatically design or run an experiment for the author.
