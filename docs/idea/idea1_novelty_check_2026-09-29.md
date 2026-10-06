# Idea 1 查新报告

- **检索时间**：2026-09-29。**整理成文**：2026-10-06。
- **对象**：[idea1_memory_converges_to_prior.md](idea1_memory_converges_to_prior.md)，即"agent 记忆 compaction 会退回预训练先验"。
- **方法**：4 个并行检索方向，共 100 多次搜索：
  1. LLM 上的 iterated learning 与传递链；
  2. agent 记忆整合中的漂移，以及 knowledge conflict；
  3. 改写过程中语言标记的丢失；
  4. 多智能体共享记忆与同质化。

  另外对 Zhu & Griffiths（2406.01860）、Perez et al.（2407.04503）、Ren et al.（2404.04286）、Acerbi & Stubbersfield（PNAS 2023）做了 Semantic Scholar 前向引用检查。
- **核实程度**：下文列出的论文都打开过 arXiv 页面或全文核实，标 UNVERIFIED 的除外。其中最关键的两处（Zhang et al. 的项目主页、Acerbi & Stubbersfield 的结论）做过二次复核。
- **收录范围**：只收录与记忆、持续学习相关的条目；原检索中与本项目范围无关的条目未收录。

**结论**：这个 topic 能做，但不是"没人碰过"。核心直觉"记忆会漂向模型先验"已有人非正式地提出过。我们的空间在于**受控检验、理论判别、定量预测**，以及偏好、跨用户同质化等扩展。必须据此定位，而且要快。

---

## 1. 逐条主张的状态

主张编号沿用 2026-09-29 版本的设计。v2 的对应关系见 §4。

| 主张 | 状态 | 最接近的工作 | 仍然新的部分 |
|---|---|---|---|
| **C1** 记忆整合即 iterated learning，会收敛到先验 | **已被非正式提出** | **Zhang et al. 2605.12978**（UIUC，Hao Peng 组；v1 2026-05-13，v2 2026-08-29）。项目主页 dylanzsz.github.io/faulty-memory 原文："The memory drifts toward the LLM's prior over what a good lesson looks like, not toward the truth of the trajectories"；"Continuously updated textual memory is an iterated generative loop with no anchor"。论文正文**没有**引用 iterated learning，也没有 Markov 或温度分析。一般 LLM 链与 iterated learning 的关系由 Ren et al.（NeurIPS 2024）和 Zhu & Griffiths（2024）建立 | 正式的 iterated learning 推导，以及对它的受控检验。不能宣称是"发现" |
| **C2** 以合理性或意外程度为自变量的受控对比 | **未被做过**（最新颖） | Zhang 的 PropWorld 使用 nonce 属性和 64 条**任意**映射，没有按合理性分级（Dynamic Cheatsheet .812→.229，LangMem .609→.203）；Kwon 2606.29279 在虚构世界中操纵的是表述的确定程度，不是合理性；knowledge-conflict 文献都只看单步 | 在 agent 记忆中、跨多轮 compaction、以意外程度为自变量 |
| **C3** 温度：T=1 时存活率随先验成对角线，greedy 时成阶跃 | **零件都有，具体预测没人检验过** | Ren et al.：认为 ICL 接近 MAP，原文写有 "We left the exploration between temperature and different phases in IL in the future"；Guo et al. CoNLL 2026（2605.23054）：在训练链中扫 τ∈{0.5,0.8,1.0}，解释为瓶颈宽度，没有 greedy 条件；Geng et al. 2603.11228：比较 greedy 与采样，greedy 下链会进入不动点或短周期，但没有把解码方式对应到学习者类型；**Cui & Yu 2506.10268：LLM 在 T=1 下也可能接近确定性**；Perez et al.：只研究温度对文本属性吸引子的影响 | 用对角线与阶跃这组对比做判别性检验。不能假设 T=1 就是采样型学习者 |
| **C4** 由单步转移拟合 Markov 模型，预测 k 步后的存活率 | **未被做过** | Geng 有句子级 Markov 核的形式化；Guo 拟合了指数收敛曲线 | 由单步数据定量预测多步的条目存活 |
| **C5** 标记漂移（hedge、evidential、体貌、量词、例外、否定） | **英语部分大多已被做过** | **Belem et al. 2606.07951**（"From 'May' to 'Is'"）：确定性升多降少，比例为 1.5–2 倍，做了 5 轮迭代改写；Kwon 2608.03372（FACTWASH）：检测多类标记的丢失，有逐轮 drift 工具；Kwon 2606.29279：记忆整合中传闻被写成事实，只做单次；Hu 2609.20211：验证状态标记在摘要和压缩中丢失；Peters & Chin-Yee 2025（2504.00025）：摘要中的量词过度泛化；Ma & Miyao ACL 2026：目的论偏差（推理任务，不是摘要） | 跨语言：强制性 evidential 语法（土耳其语 -mIş），以及跨语言整合；按类别比较吸引子；体貌在摘要中的漂移 |
| **C6** 共享整合记忆下的群体同质化（Lorenz 三效应） | **组合是新的，零件都有** | **The Deliberative Illusion 2606.03032**（Kan 组）：多智能体讨论中关键事实被抹掉，立场同质化，"anchored in base-model priors"；CoMem 2609.15009：共享记忆导致 "behavioral homogenization"；Chuang et al. NAACL-F 2024（2311.09618）：群体向模型固有偏好收敛；Social Networks of LLM Agents 2607.03695；Diverse Minds, Divided Networks 2609.12444；Fukushima 2609.19183 | 以持久的共享整合记忆为渠道（而不是讨论上下文）；完整的 Lorenz 三效应；先验契合度 × 坍缩的交互 |

---

## 2. 必须正面回应的三个风险

### 风险 A：Zhang et al.（2605.12978）可能抢先（最大）
- 他们的项目主页已经写出核心直觉，还描述了论文 v2 里没有的 PropWorld。目前 PropWorld 的映射是任意的，**如果他们下一版按合理性分级，C1 和 C2 会大部分被抢先**。
- 对策：
  1. 在引言里明确引用，定位为"对他们观察到的现象的理论解释和受控检验"；
  2. 4–6 周内拿到核心结果；
  3. 查 ARR 的预印本政策，考虑尽早挂 arXiv；
  4. 每月复查他们的 arXiv 和项目主页。

### 风险 B：Acerbi & Stubbersfield（PNAS 2023）的反向证据
- ChatGPT 在传递链中**优先保留**生物学上反直觉的内容（例如"头发变成蜘蛛"），与人类研究中"轻度反直觉更好记"（MCI；Boyer；Barrett & Nyhof 2001）的效应一致。
- 对策：把"意外的类型"做成实验因子，形成生动的意外和平淡的意外两种条件。prior attractor 和 MCI 两种理论在这里给出相反的预测。

### 风险 C：温度对应学习者类型这一前提
- Cui & Yu 和 Ren et al. 都表明，LLM 在 T=1 时的 in-context 推断也可能接近 MAP。
- 对策：把 C3 写成判别性问题："LLM 记忆 compaction 在不同温度下分别表现为哪种学习者？"两种结果都能发表。

---

## 3. 其他需要引用的相关工作

**knowledge conflict（单步中，先验压过冲突的上下文）**
- ClashEval（2404.10198, NeurIPS 2024）：上下文中的值偏离真值越远，模型越少采纳；先验置信度低时更容易采纳。这是"意外内容被拒"最接近的单步版本。
- Du et al.（2404.04633, ACL 2024）：训练中见得多的实体，模型更依赖先验。
- Xie et al.（2305.13300, ICLR 2024）：连贯的反记忆证据会被接受，但模型对与参数记忆一致的证据有确认偏差。
- Basmov et al.（2404.06283）：虚构事实可以把理解和知识分开；在情态和条件句中，先验知识会漏进来。
- Sun, Bai & Dredze（2506.06485, ACL 2026）：冲突的合理性决定性能下降的幅度。
- Kochelka et al.（2609.09363）：单步 data-to-text 中，冲突效应很弱（1–5 分的忠实度量表上只差 −0.05）。这可以用来论证必须看迭代累积。

**区分方式**：这些都是单步实验，冲突对象是对已知实体的参数记忆。本文研究的是虚构世界中的一般先验，每一步的小偏差在多轮 compaction 中累积，以及真实记忆系统中的抽取、合并、更新操作。

**记忆系统中的漂移与错误**
- HaluMem 2511.03506：记忆抽取和更新中的错误累积。
- MemEvoBench 2604.15774：多轮记忆演化中的漂移。
- SSGM 2603.11768：只有概念，提出"迭代摘要导致语义漂移"，没有实验。
- Zahn & Chana 2603.17781：摘要称 compaction 侵蚀约 54% 的约束（2026-10-06 已读全文，更正见 §5）。

**LLM 上的 iterated learning 与传递链**
- Perez et al. ICLR 2025（2407.04503）。
- Ghafouri & Ferrara 2602.17674：传递中 hedge 衰减，叙事锚点保留。
- Kouwenhoven et al.（2412.07646；IJCAI 2025, 2503.04395）：emergent communication，只用 greedy。
- Guo et al.（2605.23054）。

**同质化背景**
- Peterson 2404.03502（knowledge collapse）。
- Wu et al. 2407.02209（generative monoculture）。
- Chen et al. 2604.18005（Diversity Collapse in Multi-Agent LLM Systems，ACL 2026 Findings）。
- Kong et al. 2605.17193（Multi-LLM Systems Exhibit Robust Semantic Collapse）。

---

## 4. 对 v2 设计的含义（2026-10-06）

| 查新结论 | v2 中的处理 |
|---|---|
| C1 已被非正式提出 | 定位为"理论解释加受控检验"，引言明确引用 Zhang et al. |
| C2 最新颖 | v2 的主对比改为意外程度梯度（全部为真，minimal pair），新颖性不变 |
| 风险 B | 加入"意外类型"（生动与平淡）因子 |
| C3 / 风险 C | 温度改为判别性检验 |
| C4 | 扩展为三态模型（保留、改写、删除），区分改写通道和选择通道 |
| C5 英语部分已被做过 | 跨语言 evidential 降为待定（附录或下一篇）；英语标记漂移只在用户偏好的风格层面出现（E2） |
| C6 很拥挤 | 多智能体降为待定；同质化改由跨用户实验覆盖（E2） |

## 5. 2026-10-06 补充与更正

来源：compaction 机制调研、数据源核实、论文全文核实，详见 [idea1_survey/](idea1_survey/COMPACTION_SURVEY.md)。

**更正**
- **Zahn & Chana 2603.17781**：
  - 真实标题是 "Facts as First-Class Objects: Knowledge Objects for Persistent LLM Memory"，goal drift 只是其中一个实验。
  - 实验设置：88 轮对话中逐条说出 20 条刻意不同于默认的约束（如 "retry limit 7, not 3"），自我摘要 3 轮（总压缩比 9×、17×、31×），5 个 seed，模型为 Claude Sonnet 4.5。
  - "54%" 的含义是：第 3 轮后只有 46% 完全正确（53% 丢失，1% 部分正确）。
  - 他们**声称**约束会"漂向合理的默认值"，但**没有**逐条数据，也没有记录被替换成了什么；没有发布代码和数据。

  **含义**：E2 的论点已被提出、但没有被检验。必须引用并正面区分。
- **Acerbi & Stubbersfield**：反向证据是**混合的**，不是一边倒。
  - 威胁（0.523）、社会（0.321）、负面（0.117）内容的保留优势很强。
  - 生物学上反直觉的内容在 "Muki" 神话里保留最多，在 "Taka & Toro" 里到第 2 步就全部丢失。
  - 心理和物理上反直觉的内容属于保留最少的一类。
  - 大部分变化发生在第 1 步，之后基本稳定。

  风险 B 因此有所减弱，但"意外类型"仍作为探索性因子保留。
- **Zhu & Griffiths** 已正式发表于 CogSci 2025（模型为 gpt-4-turbo-2024-04-09，100 条链 × 12 次迭代，T=1）。

**新发现的相关工作**
| 工作 | 内容 | 与本项目的关系 |
|---|---|---|
| Compaction Cliff / AgentArtifactCorpus 2608.22752（CIKM'26） | 用 Claude Code `/compact` 做 5 轮 compaction，约束召回从 53% 降到 10%；5 种记忆类型各自衰减不同 | 多轮衰减已有人测过；**没有先验维度** |
| CompInt 2608.11242 | 15 条约束，单轮 compaction，A/B 探针 | 判定格式可借鉴 |
| Facts Without Rules 2608.29028 | 压缩交接中限定词丢失（标记保留率从约 0.80 降到 0.57） | 方向一致 |
| **Faithful, Not Corrective 2607.09678** | 强模型 6 跳接力时，原子事实几乎无损（召回 ≥ 0.973） | **反向证据**：必须设置压缩瓶颈，并在强模型上检验 |
| Zhang et al. 2605.12978 的 Table 5 与 PropWorld | 原地改写伤害最大（43.2，对比只增删的 64.0、保留原始轨迹的 76.6）；PropWorld 刻意用 nonce 去掉先验，因为用有意义的值时零样本就能解出 0.91 | C1、C2 的状态不变；新增"可猜回"这一混淆需要控制 |
| Mem0 v2.0.0（2026-04） | 改为只 ADD | 业界在实践中回避原地改写；引用 Mem0 必须注明版本 |

**结论没有变化**："以意外程度为自变量的受控检验"（C2）、三态定量模型（C4），以及温度与起始值判别（C3），仍然没有人做过。

## 6. 未核实
- "Wisdom of the Machines"（OpenReview 页面打不开）。
- EchoSim（只见到被他人引用）。
- Breithaupt et al. Sci Rep 2024。
- Muto & Ogi 2026。
