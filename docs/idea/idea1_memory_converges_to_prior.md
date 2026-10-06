# Idea 1 详细方案：Agent 记忆 compaction 会退回预训练先验

**版本记录**
- **v3，2026-10-06**：整合了 compaction 机制调研、数据源核实、关键论文方法细节，并附上 pilot 方案。
- v2，2026-10-06：根据组会笔记重写。
- v1，2026-09-29。

**范围声明**：本项目只研究 **LLM agent 的记忆与持续学习**，也就是 agent 在长程任务中怎样写入、整合、遗忘和使用记忆，以及能否靠记忆持续学到预训练之外的东西。项目不涉及攻击、投毒、对抗者或安全防御，实验设计和论文叙事都不使用这些框架。

**目标会议**：ACL 2027（ARR 截稿 2027-01-04）。主投主题赛道 *Homogenization and knowledge collapse in LLMs*，同时也投主会。

**配套文件**
| 文件 | 内容 |
|---|---|
| [idea1_novelty_check_2026-09-29.md](idea1_novelty_check_2026-09-29.md) | 查新报告 |
| [idea1_survey/COMPACTION_SURVEY.md](idea1_survey/COMPACTION_SURVEY.md) | 30 多个系统的 compaction 机制调研（原始记录在 `idea1_survey/raw/`） |
| [idea1_survey/raw/datasets.md](idea1_survey/raw/datasets.md) | 数据集与许可核实 |
| [idea1_survey/raw/paper_details.md](idea1_survey/raw/paper_details.md) | 关键论文的方法细节 |
| [idea1_pilot/PILOT_PLAN.md](idea1_pilot/PILOT_PLAN.md) | 第 1–2 周 pilot 方案；刺激材料在 `idea1_pilot/stimuli/` |

---

## 0. 一页摘要

**背景**
- 长程 agent 和 continual / lifelong learning agent 靠记忆积累经验：用户偏好、任务环境里的本地事实、从失败中得到的教训。
- 几乎所有实现都让 LLM 自己做 **memory compaction**：摘要、抽取、合并，以及决定什么保留、什么过期。
- 调研发现，**"对摘要再做摘要"在生产系统中是常态**，涵盖所有查过的开源编码 agent、Anthropic API compaction、MemGPT/Letta、Graphiti、LangMem。而且有两种时间尺度：会话内 compaction 和跨会话的记忆整合。

**论点**
- 每次 compaction 都是 LLM 读入上一版记忆、写出新一版记忆。这在结构上就是认知科学中的 **iterated learning**：一条学习者链，每一代把上一代的输出当作数据。
- 理论和已有实验都表明，这类链会**收敛到学习者的先验**。因此：

> **记忆最需要保住的内容，恰恰最容易被丢掉。** 记忆的价值在于存放模型自己不知道、或者不会默认去做的事，而 compaction 会把这些内容一轮一轮拉回模型的默认预期。

**So what**
1. **in-context 持续学习的天花板**：一个靠 compaction 积累经验的 agent，其长期记忆会退回到它在没有任何经验时就相信的东西。
2. **个性化的同质化**（对应 2027 主题）：每个用户的特殊偏好都会被磨平，所有人的助手逐渐变成"平均用户"的助手。

**核心预测**（详见 §4）
- **P1 意外梯度**：记忆条目越偏离模型先验，在 compaction 中衰减得越快。
- **P2 只发生在改写中**：只追加、不改写的记忆没有这个效应。
- **P3 可定量预测**：只用单步 compaction 的数据，就能预测多步之后的状态分布。
- **P4 学习者类型判别**：用解码温度和起始值检验 LLM 的 compaction 属于哪种学习者（§2.4）。
- **P5 跨用户同质化**：偏好各异的用户，其记忆画像在多轮 compaction 后趋同。

**规模**：以 8–32B 开源模型为主，约 40–60 万次调用，不需要训练。

---

## 1. 背景与动机

- **现象已有人观察到，但没人解释，也没有受控检验。**
  - Zhang et al.（2605.12978，UIUC）发现，持续整合会让记忆效用先升后降，甚至低于无记忆基线。他们的 Table 5 还把改写和删除分开：默认原地改写 43.2，只增删不改写 64.0，保留原始轨迹 76.6，可见原地改写伤害最大。但他们的解释是过度泛化，没有提先验。项目主页上提出了"漂向先验"的直觉，可他们的合成世界 PropWorld 刻意用无意义的值去除了先验。
  - Zahn & Chana（2603.17781）**声称**非默认约束会"漂向合理的默认值"，但没有逐条数据，也没有记录约束被替换成了什么。
  - Compaction Cliff（2608.22752）测到 5 轮 compaction 后约束召回从 53% 降到 10%，但他们的材料没有先验这个维度。
- **业界已经非正式地承认漂移，但没有人评估过。**
  - Codex 提示用户："multiple compactions can cause the model to be less accurate"。它的记忆整合 prompt 写着 "Do not rewrite concrete wording into more abstract synonyms"。
  - Letta 的调优文档承认 "goals drift over repeated compactions"。
  - Mem0 在 v2.0 把 UPDATE/DELETE 改成了只 ADD（"nothing is overwritten"）。
  - 详见 [调研 §0](idea1_survey/COMPACTION_SURVEY.md)。
- **组会上的一手观察**：合作者发现 LLM 很难长期保持 "Preserve my writing style" 这类偏好。这正是"偏离模型默认"的典型例子，见 E2。
- **2027 主题**：本文给出一种推理期、in-context 的同质化机制，此前没有被系统研究过。

**本文的定位**：对上述观察给出正式的理论解释（iterated learning），预测哪些内容先坏、坏得多快，并用受控实验检验。

---

## 2. 形式化

### 2.1 compaction 即 iterated learning
- 记忆状态为 M_t，第 t 个会话的观察为 O_t，compaction 算子 C 由 LLM 实现：M_{t+1} = C(M_t, O_t)。
- 对某个记忆条目 m（一条事实、偏好或教训），在与它无关的会话中，它在记忆里的表述 r_t 只由上一版决定：r_{t+1} ~ C(· | r_t, 上下文)。这是一条 Markov 链。
- **理论**（细节见 [paper_details](idea1_survey/raw/paper_details.md) §4）：
  - Griffiths & Kalish (2007)：如果每一代从后验中**采样**，链的平稳分布就是**先验**。前提是链具有遍历性，这需要一定的噪声或假设之间的重叠。瓶颈大小和数据量只影响收敛速度。
  - Kirby, Dowman & Griffiths (2007)：如果每一代取 **MAP**，终态会偏向先验的众数。偏多少取决于瓶颈大小和噪声，而**不取决于**先验本身有多强；瓶颈越紧，放大越明显。
- 漂移需要瓶颈：摘要有长度上限，而且每一轮都有新内容进来。如果只是原样复制，链不会动。

### 2.2 先验进入记忆的两条通道
1. **改写通道**：条目被改成更符合默认的样子。这对应 iterated learning。
2. **选择通道**：LLM 判断条目"不重要"或"过期"，把它整条删掉。

调研发现，有些系统两条通道是分开的（例如 ExpeL 的投票计数、Mem0 v1 的 DELETE），有些是缠在一起的（例如 Dynamic Cheatsheet、MemAgent：凡是没被抄进下一版的就丢了）。实验要分别记录"被改写"和"被删除"。

### 2.3 三态模型（定量预测的来源）
每个条目在每一轮处于三种状态之一：**保留**（R）、**改写**（W，内容被改成更接近默认的值或变模糊）、**删除**（D）。
- 用 k=1 的单步实验估计转移矩阵 T，用 T^k 预测 k=10 和 k=20 时的状态分布，再和实测比对。
- 每个条目的长期保留率应当由它的先验决定，先验是独立测量的（§3.3）。

### 2.4 温度与起始值：判别 LLM 是哪种学习者
按论文细节核实后修正的表述如下。可以把温度近似看作 r ≈ 1/T，其中 r 是 Kirby 等人模型里选择假设时的指数。这个对应对短答案是精确的，对自由文本只是定性的。

**条件性预测**：如果模型在 T=1 下的输出近似等于它的后验样本，那么：
- **T=1**：compaction 链的终态等于**先验分布**，长度上限只影响速度。
- **T<1**：终态会**过度集中在先验众数上**，也就是"悄悄退回默认"。程度取决于长度上限和噪声。
- **T>1**：终态比先验更平。
- **T→0 且没有外部噪声**：链不再具有遍历性，会**冻结在依赖起始点的不动点上**（Cui & Yu；Acerbi & Stubbersfield 也发现第 1 步之后就基本稳定）。

**要区分两种"收敛"**：
- 链内不确定性的坍缩：温度越低越快（Ren et al.）。
- 对初始记忆的遗忘：温度越高越快（Griffiths & Kalish：噪声越大，混合越快；Perez et al.：温度越高，吸引子越强）。

**可直接检验的两条预测**：
1. 终态落在先验众数上的条目比例，随 T 升向 1 而**下降**。
2. **起始值检验**（来自 Cui & Yu 的诊断）：低温时，终态依赖起始等级和长度上限；T=1 时不依赖。我们的设计天然支持这个检验，因为同一组事实在不同链里以 5 个不同的起始等级出现。

**不能想当然**：Cui & Yu 发现 gpt-4o、gpt-4o-mini 在 T=1 时也比贝叶斯采样更"尖锐"；Ren et al. 认为 ICL 接近 MAP，但他们的论证是渐近的。所以本文**不假设** T=1 就是采样型学习者，而是把它当作要测量的对象。

- pilot 用 T ∈ {0, 1}。
- E1 用 T ∈ {0, 0.5, 1.0, 1.3}。

---

## 3. 刺激材料

### 3.1 三类记忆条目
| 类型 | 例子（低意外 → 高意外） | 意外程度怎么测 |
|---|---|---|
| **事实**（虚构世界的本地事实） | "Veltrix 的 API 超时是 30 秒 / 2 分钟 / 5 秒 / 20 分钟 / 6 小时" | 模型对这个属性的先验分布 |
| **用户偏好与约束**（可自动检验） | 日期格式：March 14, 2027 → 2027-03-14 → 14.03.2027 → 2027/14/03；温度单位；称呼；禁用破折号；Python 命名风格 | 没有指令时模型自发这么做的比例 |
| **程序性教训与例外** | "除周二外都可以部署"；"重置 staging 要找设施经理" | 同上，再加 log-prob |

pilot 的第一版材料已经生成（[stimuli/](idea1_pilot/stimuli/)）：40 组平淡事实（192 条）、10 组生动事实、20 组偏好（58 个等级）、30 条填充事实。每个等级都附有自动判定用的正则，并且通过了自测。

### 3.2 设计原则
- **主对比是意外程度**：所有条目都为真，来源一致，每条只说一次，不附解释。
- **minimal pair 族**：同一个句子模板只改一个值，得到 3–5 个意外等级，其他因素完全相同。
- **虚构实体**：用来切断预训练中对具体实体的记忆，只保留常识性先验的作用（借鉴 Sivaprasad et al. ACL 2025 的做法）。
- **意外的类型**（生动 vs 平淡）：Acerbi & Stubbersfield 的证据其实是**混合的**：
  - 威胁、社会、负面内容的保留优势很强（保留比例差分别为 0.523、0.321、0.117）；
  - 生物学上反直觉的内容在一则神话里保留最多，在另一则里到第 2 步就完全丢失；
  - 心理和物理上反直觉的内容属于保留最少的一类。

  因此"生动意外"作为一个探索性因子保留，事先不预设方向。情感效价和威胁、社会属性作为协变量做平衡。
- **配平**：长度、在会话中的位置、曝光次数、情感效价。

### 3.3 先验的测量（按论文细节修正）
- **与 compaction 链用同一个语境测**：同样的 system prompt、记忆格式和实体介绍。Ren et al. 指出，先验是以指令 prompt 为条件的。
- **方法 1，直接基线**：用省略了该属性的 prompt，在 T=1 下大量采样；类别型属性直接读各选项的 logprob。
- **方法 2，迭代引出**：按 Zhu & Griffiths（CogSci 2025）的设计，100 条链、每条 12 次迭代，起始值分散；下一步的数据由我们按如实告知的似然来采样。
  - 数值型：用带噪报告，例如 "registry says about d, ±20%"。
  - 类别型：用带噪信道，下一步报告以 1−ε 的概率等于模型的回答，否则换成另一个类别。有 logprob 时由我们自己按 logprob 采样，这样每一步都是精确的采样步。
  - 必须做 Cui & Yu 的起始值检验；避免纯二项链，因为它有吸收态。
- **方法 3，默认行为率**（偏好类）。
- 可选：人类合理性评分。
- 比较 compaction 的终态时，要和**整个先验分布**比，而不只是和众数比。

### 3.4 外部数据（已核实许可，详见 [datasets](idea1_survey/raw/datasets.md)）
| 用途 | 数据 | 许可 | 备注 |
|---|---|---|---|
| 事实的分级偏离（外部效度） | **ClashEval**：数值按 ×0.1 到 ×10 缩放，年份偏移 ±11 到 ±100，名称分 3 级 | CC BY 4.0（见 croissant.json；仓库中没有 LICENSE 文件） | 作者已从 GitHub 删除数据文件（2025-01-17），可以从 git 历史取回；**再分发前先写信问作者**。新闻类条目可能已被新模型学过 |
| 事实（大规模备选） | CounterFact：21,919 条，34 种关系 | MIT | 没有现成分级，需要用 logprob 自己算 |
| 偏好（外部效度） | PrefEval：1,000 条显式偏好，有选择题版本 | **CC BY-NC 4.0** | 仅限非商业用途；自带的 `violation_probability` 偏斜严重，要按模型重新估计 |
| 偏好与约束（宽松许可） | CompInt 的 A/B 探针格式，加 IFEval 风格的可检验约束 | MIT / Apache-2.0 | 判定不需要 judge |
| 知识更新（E3） | **MemoryAgentBench FactConsolidation**：反事实更新，新值本身就违背先验 | MIT | 直接对应 E3 |
| 知识更新（对话场景） | LongMemEval：78 条 knowledge-update、30 条偏好 | MIT | 用 GPT-4o 做 judge |
| 方法模板 | Compaction Cliff / AgentArtifactCorpus | 数据 CC BY 4.0，需签数据使用协议 | 用作多轮 compaction 的方法参考 |

**注意**：这些数据集自带的先验标签都来自 2023–24 年的模型，必须对我们用的 compaction 模型和 reader 模型重新测量。

---

## 4. 实验

### E1：意外梯度 × compaction 操作（核心，对应 Figure 1 和 Figure 2）

**会话流程**
1. 写入会话：一个普通任务，过程中接触目标条目。
2. 无关会话：每个会话后运行一次 compaction。
3. 探针：在 k ∈ {0,1,2,3,5,7,10,15,20} 时测记忆文本中各条目的三态，以及下游问答。

**compaction 操作**（按调研的分类，每族选一个代表，见 [调研 §4](idea1_survey/COMPACTION_SURVEY.md)）
| 族 | 代表 | 作用 |
|---|---|---|
| 只追加 | 原始日志加检索；Mem0 v2 只 ADD | **对照**：预测没有先验漂移 |
| 每次从全部原始材料重写 | AWM 式 | **对照**：区分"读自己上一版"和"从原始材料重新抽象" |
| 整段滚动重写 | 中性 prompt；Aider 和 OpenHands 式 prompt | 典型的迭代链 |
| 带锚定的重写 | 中性 prompt 加 Codex 的"保留原措辞"规则 | 业界现有的缓解做法 |
| 逐条更新 | Mem0 1.0.11 的 UPDATE | 改写通道和选择通道是分开的 |
| 每次查询都整份重写 | Dynamic Cheatsheet | 改写最频繁 |
| 学习得到的改写器（可选） | MemAgent（Apache-2.0 权重），和它的基座模型对比 | — |

**测试框架**：优先在 Memory-Collapse-Eval（Zhang et al.，MIT，支持 vLLM，每个检查点都有快照）上扩展。

**其他自变量**
- 骨干模型 3 个（例如 Qwen3-8B、Qwen3-32B、Llama-3.3-70B），另加 1 个闭源模型。闭源模型用 Anthropic API compaction：摘要是可读文本，prompt 可替换。
- 温度 T ∈ {0, 0.5, 1.0, 1.3}。
- 长度上限 B 两档。
- 每个配置 3 个 seed。

**混淆控制**
- **可猜回**：Zhang et al. 的 PropWorld 设计笔记表明，典型值丢了之后可以被零样本猜回。所以主要因变量用记忆文本的三态，问答探针要扣除无记忆猜测率。
- **设计上的泛化**：主条件用中性 prompt，不用那些本身就要求"概括、泛化、换同义词"的默认 prompt。

**预测与证伪**
- 预测：P1–P4。
- 证伪：如果 k=20 时低意外与高意外条目的保留率相差不到 5 个百分点，核心论点不成立。
- 反向证据：Faithful, Not Corrective（2607.09678）发现强模型多跳接力时原子事实几乎无损。所以要确保有压缩瓶颈，并报告结论在多强的模型上成立。

### E2：用户偏好：存储失败 vs 执行失败；跨用户同质化（对应 Figure 3 和 Figure 4）
- **最接近的前人工作**：
  - Compaction Cliff：多轮约束召回衰减，分类型衰减；
  - Zahn & Chana：声称约束漂向默认值，但没有测量；
  - CompInt：单轮。

  **我们的区别**：用偏离默认的程度作为预测变量；把存储失败和执行失败分开；测量跨用户同质化。
- **三条件设计**：
  - A：直接给原始指令，衡量执行能力上限；
  - B：给 k 轮 compaction 后的记忆；
  - C：什么都不给，即默认行为。

  A 与 B 的差就是记忆造成的损失。
- **跨用户同质化**：N 个偏好组合不同的用户，比较 k=0 与 k=20 时用户偏好画像之间的距离，以及画像向模型默认值靠拢的程度。

### E3：重复曝光与知识更新（持续学习视角）
- **剂量**：一个意外条目要被重新提到几次才能稳定留在记忆里。
- **知识更新**：用 MemoryAgentBench FactConsolidation 的反事实更新和我们自己的虚构更新，检验更新为意外值的条目是否会被 compaction 退回旧的典型值。LongMemEval 的 78 条 knowledge-update 用作对话场景下的检验。

### E4（可选）：人类对照
Bartlett 式的人类传递链，约 150 人。比较人类与 LLM 的吸引子强度。

---

## 5. 记忆设计上的含义

完整的分类表见 [调研 §2](idea1_survey/COMPACTION_SURVEY.md)。下面是按实验需要归纳的版本：

| 族 | 是否迭代改写链 | 代表系统 | 理论预测 |
|---|---|---|---|
| 只追加、不改写 | 否 | Mem0 v2、ReasoningBank、MetaGPT 消息池、OpenHands 事件日志 | 没有先验漂移，只有检索问题 |
| 原始记录加 LLM 改写派生层 | 只在派生层 | Graphiti（事实加时间戳，摘要被改写）、A-MEM（只改元数据） | 派生层会漂移，原始层是锚点 |
| 整段滚动重写 | **是** | Claude Code、Codex、Aider、OpenHands、Cline、Gemini CLI 的 compaction；Letta 的对话摘要；LangMem | 漂移最强 |
| 跨会话的记忆整合 | **是**（链长没有上限） | Codex Memories、Claude Code auto memory、Anthropic Dreams、ChatGPT memory、G-Memory | 持续学习场景下的主要风险 |
| 逐条更新操作 | 部分 | Mem0 ≤1.0.11、ExpeL、Memory-R1、CrewAI | 改写通道与选择通道分开 |
| 学习得到的改写器 | 是（单个任务内） | MEM1、MemAgent | 取决于奖励设计 |

**从理论推出的缓解方式**（作为结论性实验）：
1. **锚点**：保留原始记录，摘要中附回溯指针。
2. **类型化槽位**：偏好和约束单独存，不参与自由文本摘要。
3. **意外保护**：用测得的先验识别高意外条目，在 compaction 时原样钉住。
4. **编辑而非重新生成**：用 JSON patch 或 str_replace 代替整段重写。
5. 作为对照：业界现有的"保留原措辞"类 prompt 指令（来自 Codex）。

---

## 6. 相关工作

| 工作 | 内容 | 与本文的关系 |
|---|---|---|
| Zhang et al. 2605.12978（v2 2026-08）；Memory-Collapse-Eval（MIT） | 持续整合导致记忆效用先升后降；把改写和删除分开（Table 5）；附录 D.2 显示具体词汇被侵蚀；PropWorld 刻意去掉先验 | **最大风险**，也是最好的测试框架。本文提供理论解释和以意外程度为自变量的受控检验 |
| Zhu & Griffiths（arXiv 2406.01860；CogSci 2025） | 用 iterated ICL 引出 LLM 先验：gpt-4-turbo，T=1，100 条链 × 12 次迭代 | 理论与方法基础 |
| Griffiths & Kalish 2007；Kirby, Dowman & Griffiths 2007 | 采样型学习者收敛到先验；MAP 型学习者放大众数 | 理论基础，§2.4 |
| Ren et al. NeurIPS 2024（2404.04286） | iterated learning 视角下的偏差放大；认为 ICL 接近 MAP（渐近论证） | P4 回应他们留作 future work 的温度问题 |
| Cui & Yu 2506.10268 | 部分 LLM 在 T=1 时也近乎确定性；起始值诊断 | §2.4 的前提检验 |
| Guo et al. CoNLL 2026；Geng et al. 2603.11228 | 训练链中扫温度；迭代改写的 Markov 链 | 训练层面或文本多样性，不是记忆条目 |
| Perez et al. ICLR 2025；Acerbi & Stubbersfield PNAS 2023 | 传递链中的吸引子；内容偏好（威胁、社会最强；反直觉内容的证据是混合的） | 本文研究的是记忆条目和意外程度；内容偏好作为协变量 |
| **Compaction Cliff 2608.22752**（CIKM'26） | 5 轮 compaction 后约束召回从 53% 降到 10%；分类型衰减 | E2 最直接的前人测量，但没有先验维度 |
| **Zahn & Chana 2603.17781**（"Facts as First-Class Objects"） | 3 轮自我摘要后 54% 的非默认约束不再完全正确；**声称**漂向默认值，但没有测量 | E2 的论点已被提出、尚未被检验 |
| CompInt 2608.11242 | 15 条约束，单轮 compaction，A/B 探针 | 判定格式 |
| Facts Without Rules 2608.29028 | 压缩交接中限定词丢失 | 支持"软内容先丢" |
| **Faithful, Not Corrective 2607.09678** | 强模型多跳接力时原子事实几乎无损 | **反向证据**，见 §7 |
| Knowledge conflict：ClashEval、Xie et al. ICLR 2024、Du et al. ACL 2024、Sun et al. ACL 2026、Kochelka et al. 2609.09363 | 单步中先验压过冲突的上下文；Kochelka 发现单步效应很弱 | 单步 vs 迭代累积 |
| Belem et al. 2606.07951；Kwon 2606.29279、2608.03372；Peters & Chin-Yee 2025 | 改写与整合中确定性上升、限定词丢失、过度泛化 | 标记层面的相近工作 |
| Peterson 2404.03502；Wu et al. 2407.02209 | 知识坍缩；生成单一化 | 主题背景 |

---

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| Zhang et al. 下一版做出语义版的 PropWorld | 引言中明确引用并定位为理论加受控检验；4–6 周内拿到 E1 核心结果；查 ARR 的预印本政策；每月复查他们的仓库和项目主页 |
| 强模型下原子事实不丢（Faithful, Not Corrective） | 设置压缩瓶颈；同时覆盖弱模型和强模型；把"在什么条件下会丢"作为结论的一部分；偏好和软内容是主要战场 |
| 意外内容反而被保留 | 意外类型作为探索性因子；哪种意外能存活，本身就是结论 |
| T=1 不是采样型学习者 | §2.4 写成条件性预测，并用起始值检验直接测量 |
| 典型值被模型猜回 | 以记忆文本状态为主要因变量；问答探针扣除无记忆猜测率 |
| 设计上的泛化与先验漂移混在一起 | 主条件用中性 prompt；另报告带锚定 prompt 的结果 |
| 先验测量有循环之嫌 | 多种独立测量，报告一致性 |
| 部分数据集只限非商业用途 | 主要材料自建；外部效度优先用 MIT、Apache、CC BY 许可的数据 |
| LLM judge 不可靠 | 偏好类用规则判定；其余每类抽 10% 人工复核并报告 κ |

---

## 8. 规模与算力
- E1：约 600 个条目 × 7 种操作 × 3 个骨干 × 4 个温度 × 2 档 B × 3 seed × 20 步，按需在高价值的单元格上做全分辨率。
- 合计约 40–60 万次调用，以本地 8–32B 模型为主。所有调用按内容哈希缓存。
- pilot 约 6–8 万次短调用，详见 [PILOT_PLAN §6](idea1_pilot/PILOT_PLAN.md)。

---

## 9. 论文结构

**标题候选**
- *Agents Forget What Surprised Them: Memory Compaction Regresses to the Pretraining Prior*
- *Memory Converges to the Prior: Why LLM Agents Cannot Keep What They Learn*
- *What Agents Can't Remember: Iterated Learning in LLM Memory Compaction*

**图表规划**
- **Figure 1**：按意外程度分组的保留率随 k 的变化；只追加对照为水平线。
- **Figure 2**：终态与先验的关系：不同温度下的形状对比，加上起始值检验。
- **Figure 3**：偏好的存储损失与执行损失分解。
- **Figure 4**：跨用户画像的多样性随 k 下降。
- **Figure 5**：各种缓解方式的保留率与成本对比。

**贡献草稿**
1. 指出 LLM 驱动的 memory compaction 是 iterated learning 的一个实例；区分改写与选择两条通道；给出可由单步数据预测多步结果的模型。
2. 第一个以意外程度为自变量的受控检验：越偏离先验的记忆衰减越快，只追加的记忆不受影响。
3. 用温度和起始值判别 LLM compaction 属于哪种学习者。
4. 在用户偏好上把存储失败与执行失败分开，发现 compaction 会造成跨用户的偏好同质化。
5. 从理论推出缓解方式，并与业界现有做法比较。

**英文摘要草稿**
> Long-horizon and continual-learning agents keep what they learn in memories that an LLM repeatedly compacts: after each session, the model reads its previous memory and writes a condensed one. This summary-of-a-summary loop is standard in production agents. We show it is an instance of iterated learning, which converges to learners' prior biases. Memory exists to hold what a model does not already expect, so this predicts that memory is worst at keeping exactly what it is for. We use minimal-pair memory items whose deviation from the model's prior is graded and measured independently. Across compaction operators and model families, retention falls with surprise, and the effect appears only for operators that rewrite memory. A three-state model fitted to a single compaction step predicts the state distribution many steps later. Varying decoding temperature and starting state reveals which kind of iterated learner LLM compaction behaves as. For user preferences, compaction erodes what users state and homogenizes users toward the model's defaults. Theory-derived surprise protection restores retention at modest cost.

---

## 10. 时间线（2026-10-06 → 2027-01-04，13 周）

| 周 | 内容 | Go / no-go |
|---|---|---|
| 1–2 | **pilot**（[PILOT_PLAN](idea1_pilot/PILOT_PLAN.md)） | **第 2 周末评审**：G1–G3 |
| 3–4 | 三类条目全量材料；先验测量（含迭代引出与起始值检验）；在 Memory-Collapse-Eval 上搭建统一接口 | 先验测量之间的一致性 ρ > 0.5 |
| 4–7 | E1 全量；三态模型；温度与起始值检验 | — |
| 6–8 | E2 | — |
| 8–9 | E3 | — |
| 9–10 | 缓解实验；（可选）E4，IRB 需在第 5 周前提交 | — |
| 10–12 | 写作 | — |
| 12–13 | 模拟审稿、补实验、润色 | 2027-01-04 提交 |

---

## 11. 待定决策（需要组里拍板）
1. **多智能体**：建议只做单 agent。调研显示，多智能体框架大多默认不用 LLM 改写共享通道，而且这个方向已经很拥挤。
2. **跨语言 evidential**：建议降为附录或下一篇。
3. **E3 知识更新**：放进主文还是附录。
4. **E4 人类对照**：是否申请 IRB。
5. **数据许可**：项目是否算商业用途？这决定能不能用 PrefEval、LoCoMo 这类 CC BY-NC 数据。
6. **标题**：等 pilot 结果后再定。

## 12. 尚未核实或需要跟进
1. 给 ClashEval 作者写信，确认许可和再分发方式。
2. Compaction Cliff 的数据使用协议；读全文，弄清各记忆类型的衰减曲线。
3. Faithful, Not Corrective（2607.09678）全文：模型强度、有无长度上限，以及原子事实的定义。
4. 评估 Memory-Collapse-Eval 的框架能否直接接入我们的刺激材料。
5. Mem0 v2 的 LoCoMo 提升中，有多少来自"只 ADD"、有多少来自新的检索方法（它们是一起改的）。
6. Qwen3 系列的许可，以及 vLLM 的 logprobs 支持。
