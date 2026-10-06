# Idea 1 Pilot 方案（第 1–2 周）

v1，2026-10-06。所属项目：[idea1_memory_converges_to_prior.md](../idea1_memory_converges_to_prior.md)。本项目只研究 agent 记忆与持续学习。

---

## 0. Pilot 要回答的问题

用最小的代价判断核心效应是否存在，以决定是否投入全量实验（E1）。

| 编号 | 问题 | 对应 go / no-go 指标 |
|---|---|---|
| Q1 | 在会改写记忆的 compaction 中，越偏离先验的条目是否衰减得越快？ | G1 |
| Q2 | 只追加、不改写的记忆是否没有这个效应？ | G2 |
| Q3 | 条目被改写时，是否朝先验（更典型的值）方向改？ | G3 |
| Q4（探索） | T=0 与 T=1 下，保留率对先验的曲线形状是否不同？ | — |
| Q5（探索） | 生动的意外是否比平淡的意外更容易被保留？ | — |
| Q6（探索） | 用户偏好丢失是出在存储环节还是执行环节？偏好的丢失与它偏离默认的程度有关吗？ | 决定 E2 能否作为备选主线 |
| Q7（探索） | 只用 k=1 的单步转移，能否预测 k=10 时的状态分布？ | — |

---

## 1. 刺激材料

由 [build_stimuli.py](build_stimuli.py) 生成，放在 `stimuli/` 下。运行 `python build_stimuli.py` 会重新生成文件，并做自测：每个等级填好模板后的句子，必须匹配自己的正则，且不能匹配同组其他等级的正则。当前自测通过。

| 文件 | 内容 |
|---|---|
| `facts_mundane.jsonl` | 40 组平淡事实（虚构公司 Veltrix 和小镇 Northvale 的运营、办公、流程、政策、本地生活）。36 组各 5 个等级，4 组关系型事实各 3 个等级，共 192 条。每条包括模板、问题、属性正则、各等级的取值和匹配正则 |
| `facts_vivid.jsonl` | 10 组生动事实，每组 2 个等级：典型的，以及生动、有叙事性的意外。例如"冬天时鸟钻进河泥里，用皮肤呼吸" |
| `preferences.jsonl` | 20 组用户偏好，各 2–4 个等级。L1 预设为模型的默认行为，其余等级逐渐偏离默认。每个等级包括：用户怎么说、记忆中怎么识别、行为探针的检查规则 |
| `fillers.json` | 30 条典型的填充事实，用于干扰会话，制造记忆压力 |
| `chains_facts.json` | 10 条事实链。链 1–5 用 F01–F20，链 6–10 用 F21–F40。每条链 20 条平淡事实（各等级大致均衡）加 2 条生动事实。同一组事实在 5 条链中轮流取不同等级 |
| `users_prefs.json` | 8 个模拟用户，每人 20 条偏好，等级轮换。这也能顺便给出跨用户同质化的初步读数 |

**说明**
- 等级顺序（L1 最典型）只是**设计时的预设**，用来保证平衡。分析时以**独立测得的先验**作为连续变量（§4），所以预设顺序错了只影响平衡，不影响结论。
- 所有条目都为真，同一条链里来源一致（都是用户本人陈述），每条只说一次，也不附带解释或理由。
- 正则是高精度的第一道判定。它只在提到该属性的句子或条目里使用（先用属性正则定位），匹配不上的交给 LLM judge（§3）。

---

## 2. 实验设置

### 2.1 条件

| 因子 | 取值 | 说明 |
|---|---|---|
| 记忆操作 | (a) 滚动重写（主条件）；(b) 只追加加检索（对照） | (b) 不调用 LLM 改写，把每个会话的原始轮次存起来，探针时按 embedding 检索 top-8 轮次作为"笔记" |
| 骨干模型 | 1 个开源模型（建议 Qwen3-8B，non-thinking 模式，用 vLLM 部署并开启 logprobs；许可待确认） | 第 2 周用一个强模型（≥70B 或闭源）抽查主条件。Faithful, Not Corrective（2607.09678）发现强模型接力时原子事实几乎无损，所以要尽早知道效应在强模型上是否成立 |
| compaction 温度 | T=0（greedy）、T=1 | 探针和 judge 一律用 T=0 |
| 记忆长度上限 B | 300 词、600 词 | 理论上漂移需要瓶颈；300 词会有明显压力 |
| seed | 3 个 | 改变干扰会话的顺序 |
| 检查点 k | 0, 1, 2, 3, 5, 7, 10, 15, 20 | k=0 是写入会话后的第一版记忆 |

### 2.2 会话流程（每条链、每个条件）

1. **写入会话**（不用 LLM 生成，由模板渲染）：用户 Sam 与助手 Atlas 的对话。Sam 分 6 轮说出这条链的 22 条事实，每轮 3–4 条，开场语从固定列表中轮换（例如 "A few things you should know about how things work here:"），Atlas 每轮只回复 "Noted."。偏好链与此相同，开场语换成 "Some preferences for how you write to me:"。
2. **compaction**：M_0 = C(空记忆, 写入会话)。
3. **干扰会话**（k = 1…20）：每轮取一段固定的干扰会话 transcript，然后 M_k = C(M_{k-1}, 干扰会话)。
4. **探针**：在各检查点上，对 M_k 做记忆状态判定（§3.1）和问答探针（§3.2）。偏好链还要做行为探针（§3.3）。

### 2.3 干扰会话的生成（一次性生成，人工检查后冻结）
- 共 30 段，每段约 200 词。每段是 Sam 请 Atlas 帮忙完成一件无关的任务，过程中顺带提到 2 条填充事实。
- 生成后人工检查：不能提到任何目标属性（用全部属性正则自动筛一遍，再人工看一遍）。
- 任务列表（30 个）：起草邮件、修一个 SQL 查询、规划团队午餐、改简历要点、解释一段正则、准备 1:1 议程、写一条 commit message、比较两个笔记本型号、把会议纪要整理成行动项、写生日贺卡、调试一个 Python 报错、给新人写欢迎消息、规划周末徒步路线、翻译一句客服回复、估算项目工期、写 Slack 公告、把表格转成 CSV、解释 HTTP 状态码、整理读书清单、写感谢邮件、为团队活动投票出选项、简化一段说明文字、命名一个新服务、写一段产品描述、准备面试问题、解释 git rebase 与 merge 的区别、做一份采购清单、写 bug 报告、规划演示文稿结构、写季度目标。

**生成 prompt**（用一个较强的模型生成，T=0.7）：
```
Write a short chat transcript (about 200 words) between Sam, who works at a software
company called Veltrix in the town of Northvale, and Atlas, Sam's AI assistant.
Sam asks Atlas for help with this task: {task}.
During the conversation, Sam mentions these two facts in passing:
- {filler_1}
- {filler_2}
Do not mention any of these topics: {forbidden_topics}.
Format every turn as "Sam: ..." or "Atlas: ...". Output only the transcript.
```

---

## 3. Prompt 与判定标准

### 3.1 compaction prompt（主条件，刻意保持中性）
不要求"保留精确数值"，也不给"什么重要"的标准，让模型按自己的默认判断取舍。

```
[system]
You are the memory manager for Atlas, an AI assistant that works with the same user
across many sessions. After each session you rewrite Atlas's long-term memory notes.
Future sessions will see only these notes, not the transcripts.

[user]
CURRENT MEMORY NOTES:
{memory_or_"(empty)"}

TRANSCRIPT OF THE SESSION THAT JUST ENDED:
{transcript}

Rewrite the memory notes so that they contain the information that will be useful in
future sessions. The notes must be at most {B} words. Output only the new notes.
```
- 输出超过 B 词时，按词数截断，并记录截断次数。
- **敏感性检查**（第 2 周第 5 天），用 T=0、B=300 重跑主条件的事实链：
  - **(b) Aider 式**：改编自 Aider 的 `aider/prompts.py::summarize`（Apache-2.0，commit 5dc9490）。原 prompt 针对编程对话，这里只把领域词换成通用说法，保留它最关键的那句衰减指令：
    ```
    *Briefly* summarize this partial conversation.
    Include less detail about older parts and more detail about the most recent messages.
    Start a new paragraph every time the topic changes!
    This is only part of a longer conversation so *DO NOT* conclude the summary with language like "Finally, ...".
    ```
    当前记忆放在 transcript 前面一起输入（Aider 也会对旧摘要再做摘要）。
  - **(c) 带锚定**：主 prompt 后面追加 Codex 记忆整合 prompt（`codex-rs/memories/write/templates/memories/consolidation.md`，Apache-2.0，commit 822e58c）中的防漂移规则：
    ```
    - Do not rewrite concrete wording into more abstract synonyms when the original wording fits.
    - Keep original wording by default. Only paraphrase when needed to merge duplicates, repair
      grammar, or make a point reusable.
    - Preserve distinctive nouns and verbatim strings that a future search would likely use.
    ```
    预测：(b) 的意外梯度比主条件更陡；(c) 会减弱梯度但不会消除它。(c) 也是 E1 里"带锚定的重写"这一族的预演。

### 3.2 记忆状态判定（主要因变量）

对每个目标条目和每个检查点，把 M_k 判为三态之一：

| 状态 | 定义 |
|---|---|
| **RETAINED**（保留） | 笔记里给出的答案与原值相同（可以换说法，但具体值必须一致） |
| **CHANGED**（改写） | 笔记涉及这个问题，但给出不同的值，或者更笼统的说法（例如 "a few minutes"）。另记子类型：*specific*（变成另一个具体值）和 *vague*（变模糊） |
| **DROPPED**（删除） | 笔记没有涉及这个问题 |

**判定流程**
1. 把笔记切成句子或条目，用 `attribute_regex` 找到提到该属性的片段。
2. 在这些片段上应用各等级的正则：
   - 只命中原等级 → RETAINED；
   - 只命中其他等级 → CHANGED-specific，并记下变成了哪个等级；
   - 没有片段提到这个属性 → 暂判 DROPPED。
3. 以下情况一律交给 LLM judge：命中多个等级；有片段提到属性但没有命中任何等级；暂判 DROPPED 的条目（再确认一次，防止换了说法没被属性正则抓到）。

**LLM judge prompt**（judge 模型要和 compaction 模型不同，例如 Qwen3-32B 或一个 API 模型）：
```
You will check whether a piece of information survived in an assistant's memory notes.

ORIGINAL INFORMATION: {sentence}
QUESTION IT ANSWERS: {question}

MEMORY NOTES:
{notes}

Classify the notes into exactly one category:
- RETAINED: the notes give the same answer as the original information. Paraphrase is
  fine, but the specific value must be the same.
- CHANGED: the notes address the question but give a different answer or a less
  specific one.
- DROPPED: the notes do not address the question.

Reply with JSON only:
{"label": "RETAINED" | "CHANGED" | "DROPPED",
 "notes_answer": "<the answer the notes imply, or null>",
 "evidence": "<a short quote from the notes, or null>"}
```
- judge 判为 CHANGED 时，再用各等级的正则去匹配 `notes_answer`，确定是变成了某个等级还是变模糊。
- **人工校验**：按条件和判定结果分层抽 150 个样本，由两人独立标注，报告人与人之间、人与 judge 之间的 Cohen's κ。目标 κ ≥ 0.7，达不到就修改 judge prompt。

**改写方向**（用于 G3）：一次 CHANGED-specific 算作"朝先验方向"，条件是新值的先验概率高于原值（用 §4 的先验）。数值型事实另外报告一个简单指标：新值与 L1 值之间的对数距离，是否小于原值与 L1 值之间的对数距离。

### 3.3 问答探针（次要因变量，看下游是否还能用）
```
[system]
You are Atlas. Answer using only your memory notes.

[user]
MEMORY NOTES:
{notes}

Question: {question}
Answer in a few words. If the notes do not contain the answer, reply exactly: NOT_IN_MEMORY
```
用各等级的正则判定回答：原等级、其他等级、NOT_IN_MEMORY，或无法匹配（交给 judge）。

**可猜回校正**：典型值即使从记忆里丢了，模型也可能自己猜对。Zhang et al. 的 PropWorld 设计笔记显示，用有意义的值时，没有记忆的 agent 零样本就能达到 0.91。因此问答探针还要跑一个**无记忆条件**（把笔记换成 "(no notes)"，并删掉 NOT_IN_MEMORY 选项，强制猜一个答案），得到每个条目的猜中率 g。报告问答结果时，同时给出原始正确率和超出猜测的正确率 (acc − g)/(1 − g)。记忆文本的三态（§3.2）不受这个混淆影响，仍是主要因变量。

### 3.4 偏好的行为探针（区分存储失败与执行失败）
对每个用户的每条偏好，用同一个 `probe_task` 在三种条件下各跑一次（T=0）：

| 条件 | system prompt | 衡量什么 |
|---|---|---|
| A 原始指令 | `You are Atlas, an AI assistant. The user's preferences:\n{该用户全部 20 条偏好的原话}` | 执行能力上限 |
| B 整合后记忆 | `You are Atlas, an AI assistant. Your memory notes about the user:\n{M_k}` | 记忆在第 k 轮后还能支撑多少 |
| C 无信息 | `You are Atlas, an AI assistant.` | 默认行为，也是偏好类的先验 |

- 按 `behavior_check` 自动判定遵守与否。规则包括：正则、反向正则、首个缩进字符、句子数上限或精确值、全小写、emoji 位置。
- **存储损失** = 遵守率(A) − 遵守率(B, k)，**执行损失** = 1 − 遵守率(A)。
- 偏好的记忆状态同样按 §3.2 判三态，属性定位用 `memory_patterns`。

---

## 4. 先验的测量

每组事实或偏好都在 pilot 运行**之前**测好，并且固定下来。

| 方法 | 做法 | 输出 |
|---|---|---|
| (a) 对数概率 | 上下文为 `Some facts about Veltrix, a software company in the town of Northvale.\n` 加上模板中取值之前的部分；对每个等级的取值计算续写的 token 对数概率之和（同时记录按 token 平均的版本） | 组内各等级的相对先验 p_a(level)（在该组各候选上做 softmax），以及绝对 surprisal |
| (b) 生成式引出 | `Veltrix is a software company in the town of Northvale. Without any other information, give your single best guess. {question} Answer with just the value.` 在 T=1 下采样 30 次，用各等级正则归类，归不进去的记为"其他"，加 1 平滑 | 经验先验 p_b(level) |
| (c) 默认行为率（偏好类） | §3.4 的条件 C，在 T=1 下采样 10 次，外加 1 次 T=0 | 每个等级被自发满足的比例 |
| (d)（推迟到 E1） | Zhu & Griffiths（CogSci 2025）式的迭代引出：100 条链 × 12 次迭代，起始值分散；数值型用带噪报告（"registry says about d, ±20%"）作为下一步的数据，类别型用带噪信道。必须做 Cui & Yu 的起始值检验，避免纯二项链 | pilot 只用 (a)–(c)；(d) 在第 3–4 周和全量材料一起做 |

- **语境一致**：(a)(b) 的 prompt 要用和 compaction 链相同的框架，即同一个 system 角色、"memory notes" 的格式、同样的实体介绍。Ren et al. 指出先验是以指令 prompt 为条件的。上表中的 prompt 是最简版本，正式运行前要按这一条改写，并保存最终版本。
- **意外程度** surprise = −log p_a(level)；p_b 作为稳健性检验。报告 (a) 与 (b) 的 Spearman 相关。
- 预设的等级顺序与实测先验不一致时，以实测为准。
- 和 compaction 终态比较时，要和**整个先验分布**比，而不只是和众数比。

---

## 5. 分析与 go / no-go

**主要指标**：每个条目在每个检查点的三态标签。

**G1（核心效应）**
- 条件：滚动重写、B=300，在 T=0 和 T=1 中**至少一种**温度下。
- 做法：按实测 surprise 把条目分成三等份。
- 标准：k=10 时，低意外组与高意外组的 RETAINED 比例相差 **≥ 10 个百分点**，且对 family 做 bootstrap 得到的 95% CI 不含 0。

**G2（只发生在改写中）**：只追加对照下，同样两组的保留率相差 **< 5 个百分点**。

**G3（朝先验方向）**：在所有 CHANGED-specific 事件中，**≥ 60%** 朝先验方向（二项检验，p < .05）。

**探索性分析**
- Q4（按论文细节修正后的表述）：
  1. k=20 时的保留率对 p_a 作图，T=0 与 T=1 分开画。
  2. **众数比例**：终态落在该组先验众数上的条目比例，预测 T=0 高于 T=1。
  3. **起始值检验**：同一组事实在 5 条链里从不同的起始等级出发。比较 k=20 时这些链的终态分布：T=0 时预测终态依赖起始等级（冻结在不动点上）；T=1 时依赖减弱（向同一个分布收敛）。用组内的卡方检验，或终态分布之间的平均距离来衡量。

  这些预测都以"T=1 的输出近似后验样本"为前提。Cui & Yu 发现部分模型在 T=1 时也接近确定性，所以 pilot 的结果本身就是对这个前提的检验，不能反过来假设它成立。
- Q5：在实测 surprise 相近的条件下，比较生动意外与平淡意外的保留率。
- Q6：偏好的存储损失与执行损失随 k 的变化；存储损失与默认偏离程度（1 − 默认行为率）的相关。8 个用户的偏好画像两两之间的距离，比较 k=0 与 k=20。
- Q7：用 k=0→1 的转移估计三态转移矩阵 T，用 T^10 预测 k=10 时的分布，报告与实测的总变差距离（total variation distance）。

**决策规则**

| 结果 | 下一步 |
|---|---|
| G1 和 G2 都满足 | 进入 E1 全量 |
| G1 不满足但 G3 满足 | 先把 k 加到 30、B 降到 200 再跑一轮；仍不满足就走下一行 |
| G1 和 G3 都不满足 | 转为以 E2（偏好的存储与执行分解）为主线，前提是 Q6 显示存储损失随偏离程度上升；否则回到组会重新讨论方向 |
| G2 不满足（对照组也有梯度） | 说明效应可能来自检索或探针本身，先查清原因（例如检索的偏好、问答探针的先验偏差），再做判断 |

---

## 6. 规模与算力

| 部分 | 运行数 | LLM 调用 |
|---|---|---|
| 事实链 compaction | 10 链 × 3 seed × 2 温度 × 2 个 B = 120 次运行 × 20 步 | 2,400 |
| 事实链探针 | 120 × 9 个检查点 × 22 条 | 约 2.4 万次问答（加上部分 judge） |
| 只追加对照 | 10 × 3 × 9 × 22 | 约 6 千次问答 |
| 偏好链 compaction | 8 用户 × 3 × 2 × 2 = 96 × 20 | 1,920 |
| 偏好行为探针 | 96 × 9 × 20，加上条件 A/C | 约 1.8 万 |
| 先验测量 | 打分约 250 次，采样约 1,500 次，默认行为约 600 次 | 约 2,500 |
| **合计** | | **约 6–8 万次短调用**，一张 80GB GPU 上大约半天到一天 |

---

## 7. 两周日程

| 天 | 第 1 周 | 第 2 周 |
|---|---|---|
| 1 | 人工通读刺激材料，修改不自然的句子；生成 30 段干扰会话并检查 | judge 判定；150 个样本的人工校验与 κ |
| 2 | 先验测量 (a)(b)(c)；搭建运行框架（vLLM、缓存、日志） | 分析 G1–G3 |
| 3 | 跑 1 条链做演练，**人工阅读 M_0…M_20 的全文**，确认 B 的压力合适、截断不频繁 | 探索性分析 Q4–Q7 |
| 4 | 全量运行 | **go / no-go 评审会** |
| 5 | 全量运行（续），判定流程的单元测试 | 敏感性检查：真实系统 prompt，或第二个模型抽查 |

## 8. 产出
- 每个检查点的记忆快照（JSONL，含条件、seed、k）。
- 判定标签：正则结果、judge 原始输出、人工校验集。
- 先验表：每组每个等级的 p_a、p_b，以及偏好的默认行为率。
- 分析 notebook，以及一份 2 页的 pilot 报告（G1–G3 结论，Q4–Q7 的初步读数）。

## 9. 根据调研结果已定的事项（2026-10-06）

1. **敏感性检查的 prompt**：(b) Aider 式；(c) 中性 prompt 加 Codex 的防漂移规则（见 §3.1）。依据：[COMPACTION_SURVEY](../idea1_survey/COMPACTION_SURVEY.md) §0、§2C。
2. **Mem0 风格的操作不放进 pilot。** 当前开源的 Mem0 v2 已改成只 ADD，论文中的 UPDATE/DELETE 只存在于 `mem0ai==1.0.11`。这一族放到 E1，届时固定用 1.0.11 版本。
3. **pilot 只用自建材料。** 外部数据放到 E1 的外部效度部分：
   - 事实：ClashEval（CC BY 4.0，需先联系作者）或 CounterFact（MIT）；
   - 偏好：CompInt 格式加 IFEval 式约束（宽松许可）；PrefEval 为 CC BY-NC，是否使用取决于项目是否算商业用途；
   - 知识更新：MemoryAgentBench FactConsolidation（MIT）。

   详见 [datasets](../idea1_survey/raw/datasets.md)。
4. **先验测量 (d)** 推迟到 E1（见 §4），pilot 用 (a)–(c)。
5. **运行框架**：pilot 用一个最小的自写框架（vLLM 加缓存），这样最快。E1 改在 Zhang et al. 的 Memory-Collapse-Eval（MIT）上扩展，第 2 周结束前评估它能否接入我们的刺激材料。
