# Agent 记忆 compaction 机制调研

**日期**：2026-10-06
**所属项目**：[idea1_memory_converges_to_prior.md](../idea1_memory_converges_to_prior.md)（只研究 agent 记忆与持续学习）

**方法**：4 个并行调研方向，覆盖记忆库、研究型 agent、生产级与编码 agent、多智能体框架，共 30 多个系统。每条结论都以源码（指定 commit 的浅克隆）、官方文档或论文全文为依据；闭源系统只用官方文档，Claude Code 另外核对了本地二进制中的字符串。每个系统的逐项记录（含 prompt 文件路径、行号和原文引用）见 [raw/](raw/)。未能核实的内容在原始记录中标为 UNVERIFIED。

---

## 0. 主要结论

1. **"对摘要再做摘要"在生产系统中是常态，不是特例。** 我们查过的开源编码 agent（Codex 本地路径、OpenHands、Aider、Cline、Gemini CLI）、Anthropic API 的 compaction（文档原话："The new block summarizes the old summary and everything after it"），以及 MemGPT/Letta、Graphiti、LangMem 等记忆库，都是用"上一版摘要加新内容"生成下一版。原始轮次一旦被压缩，此后就不再被读取，只有少数系统会保留一段最近的原文。所以 compaction 链的长度就等于压缩发生的次数。
2. **存在两种时间尺度的迭代改写。**
   - **会话内**：按 token 阈值触发。触发点从窗口的约 1/16（Aider）到 50%（Gemini CLI），再到约 90%（Codex、Cline）。
   - **跨会话**：记忆整合，包括 Codex Memories、Claude Code 的 auto memory、Anthropic 的 Dreams、ChatGPT 的 "improved memory"、Letta 的反思子 agent。这条链没有长度上限，**最直接对应持续学习**。
3. **厂商和框架作者已经非正式地承认漂移，但没有人评估过。**
   - Codex 会提示用户："Long threads and multiple compactions can cause the model to be less accurate."
   - Codex 的记忆整合 prompt 写有："Do not rewrite concrete wording into more abstract synonyms… Keep original wording by default"，并给出了一个反例。OpenAI Agents SDK 的 `MEMORY.md` 整合规则相同。
   - Letta 的调优文档写有："If prior long-term goals drift over repeated compactions…"
   - Claude Code 的 compaction prompt 要求逐字引用，"to ensure there's no drift in task interpretation"。
   - langgraph-supervisor 提供 `forward_message`，"to avoid information loss any time the supervisor rewrites a worker query"。
4. **不少默认 prompt 本身就在推动泛化。** 例如：
   - LangMem 的 "What generalizations can you make?" 和 "Consolidate and compress"；
   - Cognee 的 "Use synonym words where possible"；
   - Aider 的 "Include less detail about older parts"（每一轮都让旧内容按几何级数衰减）；
   - G-Memory 和 AutoGen Teachability 要求写"general"的洞见或建议；
   - Collaborative Memory 的共享层要求 "Remove any user-specific details"。

   因此实验需要把**设计上就要求的泛化**和**意料之外的先验漂移**区分开。
5. **业界已经在用脚投票。** Mem0 在 v2.0.0（2026-04-14）把 LLM 驱动的 UPDATE/DELETE 改成只 ADD，changelog 写："Memories accumulate; nothing is overwritten"。他们把 LoCoMo 从 71.4 提升到 91.6 归功于这次改版加上新的混合检索（这组数字是 Mem0 自己的说法，没有核实，而且两项改动混在一起）。不少系统选择保留原始记录，只让 LLM 改写派生层：Graphiti 的事实只加时间戳失效、从不改写；A-MEM 只改写元数据；Letta 的消息历史不可修改。**注意**：论文中引用 Mem0 必须标明版本。论文里的 ADD/UPDATE/DELETE 算法只存在于 `mem0ai==1.0.11` 及以前。

---

## 1. 分类框架

每个系统按生命周期的四个环节记录，另外做两项对本项目最关键的判断：

| 维度 | 取值 |
|---|---|
| WRITE | 原文追加 / LLM 抽取 |
| UPDATE | 只追加 / 原地整段重写 / 带操作的合并（ADD、UPDATE、DELETE 等） / 加时间戳失效 / 学习得到的策略 |
| FORGET | 无 / 规则（衰减、TTL、容量淘汰、滑动窗口） / LLM 决定（DELETE 操作、投票、没被抄进下一版即视为丢失） / 学习得到的策略 |
| RETRIEVE | embedding / BM25 / 图 / 近因与重要性加权 / 整段放进上下文 |
| **迭代改写链？** | LLM 是否反复读入自己上一版的记忆文本并写出新版本 |
| **先验从哪条通道进入** | **改写通道**（内容被改写）；**选择通道**（由 LLM 决定留或删）；两者兼有（凡没被抄进下一版的就丢失，删除和改写缠在一起） |

---

## 2. 总表

### A. 记忆库与基础设施
| 系统 | 更新方式 | 迭代改写链？ | 谁决定删除 | prompt 可替换 / 能否跑本地模型 | 许可 |
|---|---|---|---|---|---|
| Letta / MemGPT | LLM 原地改写（字符串编辑、整块 `memory_rethink`）；对话摘要在每次 compaction 时重新摘要；compaction 后由反思子 agent 改写记忆文件 | **是** | LLM（删除或移到 `ARCHIVE.md`）；消息历史不删 | 是（`compaction_settings.prompt`）；有本地和 Ollama 后端。旧版 Python server 禁止用于研究或评测 | Apache-2.0 |
| Mem0 v2.x（当前开源版） | 只 ADD | 否 | 用户或 API；可选 `expiration_date` | 只能追加 `custom_instructions` | Apache-2.0 |
| Mem0 ≤1.0.11（论文算法） | LLM 选 ADD / UPDATE / DELETE / NONE | 部分（UPDATE 在同一 ID 上改写一条事实） | LLM（DELETE） | 是（`custom_update_memory_prompt` 等） | Apache-2.0 |
| LangMem + LangGraph store | LLM 用 JSON patch 改写已有记忆；滚动摘要（"Extend this summary…"） | **是** | LLM（`RemoveDoc`）；store 的 TTL 按规则 | 是 | MIT |
| A-MEM | 笔记正文从不改写；LLM 改写相邻笔记的上下文和标签（"memory evolution"） | 部分（只改元数据，不留历史） | 无自动删除 | 需要覆盖属性或 fork | MIT |
| Zep / Graphiti | 事实加时间戳失效；实体、社区摘要由 LLM 改写（超过 2000 字符就把旧摘要加新消息压回 1000 字符以内） | **摘要：是；事实：否** | LLM 标出矛盾，按时间戳让边失效，不硬删 | 部分 | Apache-2.0 |
| MemOS | 默认只追加；开启 reorganize 后由 LLM 融合冲突或冗余项、给簇写摘要 | 部分（默认关闭） | 规则（达到 80% 容量时淘汰最旧的）；reorganizer 中由 LLM 决定 | 部分 | Apache-2.0 |
| Cognee | 默认是增量添加；可选的实体描述改写 pass | 默认否；反复运行该 pass 则是 | 规则（衰减、剪枝）；API `forget()` | 部分 | Apache-2.0 |

### B. 研究型 agent 与学习型记忆
| 系统 | 更新方式 | 迭代改写链？ | 谁决定删除 | 代码与 prompt 可得性 | 许可 |
|---|---|---|---|---|---|
| Generative Agents | 记忆流只追加；反思叠在旧反思上；`currently` 状态行每天被覆盖 | 部分 | 无（`expiration` 字段存了但从不读）；只在检索时按近因衰减 | 是 | Apache-2.0 |
| MemoryBank | 原始轮次保留；每日摘要只写一次；全局摘要由每日摘要重算，不由自己上一版生成 | 否（固定两层） | 规则加随机（Ebbinghaus 曲线；代码中 `exp(-t/5*S)` 有 bug，强记忆反而衰减更快） | 是 | MIT |
| Reflexion | 每个任务追加反思，只用最近 3 条 | 部分 | 规则（滑动窗口） | 是 | MIT |
| ExpeL | 对规则列表执行 ADD / EDIT / AGREE / REMOVE | **是**（离线连续 EDIT 规则文本） | LLM 投票，计数 ≤0 即删除 | 是 | Apache-2.0 |
| Dynamic Cheatsheet | 每次查询后整份 cheatsheet 被重写，没有 ground truth（LLM 自评） | **是**（最典型） | LLM（不抄进下一版即丢失） | 是（prompt 文件可替换，支持任意 OpenAI 兼容接口） | MIT |
| Agent Workflow Memory | 代码每次从原始成功轨迹重建 workflow 文件并覆盖（论文说是追加） | 否，但每次输出会变（T=1 采样） | LLM 隐式决定，外加 LLM judge 判定哪些轨迹算成功 | 是 | Apache-2.0 |
| ReasoningBank | 只追加，每条轨迹最多 3 项 | 否 | 无 | 是 | Apache-2.0 |
| Memory-R1 | 学习得到的 ADD / UPDATE / DELETE / NOOP | 部分到是 | 学习得到的策略 | 否（代码仓库是占位，没有权重） | Apache-2.0（空仓库） |
| MEM1 | 模型每轮覆盖内部状态 | **是**（单个 episode 内） | 学习得到的策略 | 是（权重在 HF） | 代码 MIT；权重没有许可标注 |
| MemAgent | 每读一块就覆盖 1K token 的记忆 | **是**（单个任务内，数百步） | 学习得到的策略 | 是（7B、14B 权重） | Apache-2.0 |
| AgeMem | 学习得到的工具调用（Add / Update / Delete，以及上下文的 Summary / Filter） | 部分 | 学习得到的策略 | 有训练代码，没有权重 | 未附 LICENSE 文件 |
| Zhang et al. 2605.12978（Memory-Collapse-Eval） | 比较流式改写、只追加、剪枝 | **是**（研究对象本身） | 视条件而定 | 是（14 种记忆方法、6 个环境；PropWorld 代码已发布，原始运行数据未公开） | 代码 MIT；数据 CC BY 4.0 |

### C. 生产级助手与编码 agent
| 系统 | 触发条件 | 新摘要是否由旧摘要生成？ | prompt 位置 | 许可 / 开放程度 |
|---|---|---|---|---|
| Claude Code compaction | 接近上下文上限（可用 `/autocompact` 配置）；`/compact`；`/rewind` 可部分压缩 | **是**（历史变成"摘要加新轮次"后再被摘要） | 未公开；二进制中有 9 节的 "Your task is to create a detailed summary…" | 专有 |
| Claude Code auto memory | 会话中写入；`MEMORY.md` 有大小提醒 | 是（跨会话重读、合并、修剪） | 文档；"Dream" 整合 prompt 只在二进制中找到，触发条件未核实 | 专有 |
| Anthropic API compaction / Dreams | 阈值模式（默认输入 150K token）；按需；Dreams 需显式调用 | **是**（文档明说） | 文档中有默认 prompt，可用 `instructions` 替换 | 闭源 API；摘要是可读文本 |
| Codex CLI compaction | 窗口的 90%；`/compact` | **是** | `codex-rs/prompts/templates/compact/prompt.md`，可用 `compact_prompt` 覆盖 | Apache-2.0 |
| Codex Memories | 会话开始时的后台任务（默认关闭） | **是**（跨会话） | `codex-rs/memories/write/templates/memories/consolidation*.md`（含防漂移规则） | Apache-2.0 |
| OpenAI Responses API / Agents SDK | 调用方设置 `compact_threshold` | 是（推断） | 服务端加密，不可观察 | 闭源 API；SDK 为 MIT |
| Gemini CLI | token 上限的 50%；`/compress` | **是**，并明确要求整合上一份 `<state_snapshot>`，之后还有一次自检改写 | `packages/core/src/prompts/snippets.ts::getCompressionPrompt` | Apache-2.0 |
| ChatGPT memory | 未公开 | 可能（"continually updates a broader summary"） | 未公开 | 闭源 |
| claude.ai memory | 现行版本按话题更新；旧版每 24 小时刷新摘要 | 旧版可能是；现行版本只按话题改写 | 未公开 | 闭源 |
| OpenHands condenser | 超过 240 个事件或超出模型输入上限 | **是**（文档："summaries are also summarized"） | `condenser/prompts/summarizing_system.j2` | MIT；支持本地模型；**事件日志只追加，被遗忘的原始事件都保留，可作 ground truth** |
| Aider ChatSummary | 历史超过 min(max(窗口/16, 1024), 8192) token | **是**（最多递归 3 层） | `aider/prompts.py::summarize` | Apache-2.0；支持本地模型 |
| Cline | 可用输入的 90%；默认开启 | **是**（请求中带 "Previous summary:"） | `compaction-shared.ts::buildSummaryRequest` | Apache-2.0 |

### D. 多智能体框架
| 系统 | 共享还是私有 | LLM 是否改写共享记忆 | 交接时是否做摘要 | 许可 |
|---|---|---|---|---|
| AutoGen v0.4 | 每个 agent 私有；团队共享广播消息流 | 只有 TextCanvasMemory 会改写 | 否（v0.2 曾有链式 `carryover` 摘要） | MIT |
| Magentic-One | 由编排者写入共享任务账本（事实加计划） | **是**（每卡住 3 次就 "Please rewrite the following fact sheet…"，然后清空线程） | **是**（账本是唯一带入下一轮的状态） | MIT |
| Microsoft Agent Framework | 每个会话 compaction | 滚动摘要，最多 5 句，"Incorporate any previously provided summary" | 未查 | MIT |
| CrewAI | 默认共享 crew 记忆 | 是（keep / update / delete / insert_new，"prefer 'keep' when unsure"） | 传原始任务输出 | MIT |
| MetaGPT | 共享发布订阅消息池 | 否（消息不可变） | 多数情况原文传递 | MIT |
| LangGraph（supervisor / swarm） | 共享图状态 | 只在摘要配方中改写 | 否（默认 `last_message`，属于选择） | MIT |
| OpenAI Agents SDK | 交接时带完整 transcript | sandbox `MEMORY.md` 每次会话结束时增量改写（带防抽象规则） | 否 | MIT |
| CAMEL | 默认私有；`share_memory=True` 时复制原始记录 | 完全压缩会对旧摘要再摘要 | 否 | Apache-2.0 |
| G-Memory | 一个共享的层级结构 | **是**（每 5 个任务 EDIT 一次；每 20 个任务合并并替换全部洞见）。**代码与论文描述不一致** | 每次读取时按角色做一次 LLM 投影 | 无许可 |
| Collaborative Memory | 私有加共享两层 | 否（写入时一次抽取，之后只追加） | — | 未找到代码 |
| CoMem 2609.15009 | 私有加集体池 | 否（洞见原样复制，只做选择） | — | 未找到代码 |
| ShareMem 2609.32511 | 本地加共享池 | **是**（管理者 LLM 跨用户增、替、删；消融中可编辑版本优于只追加版本） | — | 未找到代码 |
| Intrinsic Memory Agents 2508.08997 | 每个 agent 私有加共享对话 | **是**（每轮 M = LLM(M_prev, output)，纯链式） | — | 未找到代码 |

**多智能体方面的结论**：多数框架默认**不**用 LLM 压缩共享通道，而是传原文、截断或只取最后一条。迭代改写链集中在三处：可选开启的摘要器；编排者的账本（Magentic-One）；跨任务的洞见库（G-Memory、各 SDK 的 `MEMORY.md`）。这支持 idea1 文档 §11 的建议，即主实验只做单 agent。

---

## 3. 直接相关的前人测量

| 工作 | 测了什么 | 对本项目意味着什么 |
|---|---|---|
| **Zhang et al. 2605.12978**，Table 5（ARC-AGI Stream，GPT-5.4，第 400 步） | 默认原地改写 43.2；只追加且能看到旧存储 50.0；只增删、不原地编辑 64.0；只追加且看不到旧存储 70.0；保留原始轨迹 76.6。附录 D.2：连续 50 次改写后，"max size" 被改成 "a derived per-object numeric attribute" | 他们已经分离了改写与删除，确认原地改写伤害最大。但他们的解释是过度泛化、分割错误，**没有提先验**，也没有操纵内容偏离先验的程度 |
| **PropWorld**（同组，只在代码中发布） | 刻意用无意义的 nonce：设计笔记显示，用有意义的值时，没有记忆的 agent 零样本就能解出 0.91 | **说明我们必须控制一个混淆**：典型值即使从记忆中丢失，也能被模型猜回来。主要因变量用记忆文本的状态；问答探针要对照"无记忆猜测率" |
| **Compaction Cliff / AgentArtifactCorpus 2608.22752**（CIKM'26） | 用 Claude Code `/compact`（Sonnet 4.6）做 5 轮 compaction，约束召回从 53% 降到 10%；区分 5 种记忆类型，各自衰减不同 | 多轮衰减已有人测过；他们的条目是仓库配置规则，**没有先验维度** |
| **CompInt 2608.11242** | 15 条用户约束，单轮 compaction，A/B 探针精确匹配 | 判定格式可以借鉴 |
| **Zahn & Chana 2603.17781**（真实标题："Facts as First-Class Objects: Knowledge Objects for Persistent LLM Memory"） | 88 轮对话中逐条说出 20 条刻意不同于默认的约束（如 "retry limit 7, not 3"），自我摘要 3 轮（总压缩比 9×、17×、31×），第 3 轮后 54% 不再完全正确；**声称约束会"漂向合理的默认值"，但没有逐条数据，也没有记录被替换成了什么** | 和 E2 最接近：先验漂移这一论断已被**提出但没有被测量**。没有代码和数据 |
| **Facts Without Rules 2608.29028** | 压缩交接中事实保留、限定词丢失（25 词预算下，标记保留率从约 0.80 降到 0.57） | 支持"软内容先丢"的方向 |
| **Faithful, Not Corrective 2607.09678** | 强模型做 6 跳接力时，原子事实几乎无损（召回 ≥ 0.973），损失主要发生在第一次编码 | **反向证据**：强模型、没有压缩压力时，原子事实可能不会丢。pilot 需要有压缩瓶颈，第 2 周要加一个强模型做抽查 |

---

## 4. 对实验设计的含义

1. **E1 的 compaction 操作按"族"挑选，每族选一个代表**：
   - 只追加：原始日志或 ReasoningBank 式追加；Mem0 v2 只 ADD。
   - 整段滚动重写：Aider、OpenHands、Codex compaction 式；Letta 的对话摘要。
   - 逐条更新操作：Mem0 1.0.11 的 UPDATE。
   - 带锚定的重写：在中性 prompt 上加入 Codex 的"保留原措辞"规则；Gemini 的锚定加自检。
   - 每次查询都整份重写：Dynamic Cheatsheet。
   - 实体摘要：Graphiti。
   - 编辑操作而非重新生成（作为缓解对照）：JSON patch 或 str_replace 式。
2. **可复用的测试框架**：
   - Memory-Collapse-Eval（MIT，支持 vLLM 和本地模型，14 种方法，每个检查点都有快照）可以作为主框架。
   - Dynamic Cheatsheet 是最简单的纯改写链。
   - OpenHands 的只追加事件日志可以提供 ground truth。
   - 闭源对照可以用 Anthropic API compaction（可读文本，prompt 可替换）。
3. **混淆控制**：
   - **设计上的泛化 vs 意外的先验漂移**：使用中性 prompt；同时报告带锚定 prompt 下的结果。
   - **可猜回**：以记忆文本状态为主要因变量；问答探针要扣除无记忆猜测率。
   - **重新抽象**：AWM 不形成迭代链，但从越来越大的轨迹池重新抽象也会变差。因此要区分"读自己上一版"和"每次从原始材料重做"。可以加一个"每次从全部原始材料重写"的操作作为对照。
4. **两种时间尺度都要覆盖**：会话内 compaction（编码 agent 场景）和跨会话整合（持续学习场景）。后者是论文叙事的重点。

---

## 5. 原始记录
- [raw/libraries.md](raw/libraries.md)：记忆库与基础设施（6 个系统，commit、文件路径、行号）
- [raw/research_systems.md](raw/research_systems.md)：研究型 agent 与学习型记忆（12 个系统）
- [raw/products_coding.md](raw/products_coding.md)：生产级助手与编码 agent（10 个系统）
- [raw/multi_agent.md](raw/multi_agent.md)：多智能体框架（13 个系统，外加交接链相关论文）
- [raw/datasets.md](raw/datasets.md)：数据集与许可
- [raw/paper_details.md](raw/paper_details.md)：关键论文的方法细节（Zhu & Griffiths、Zahn & Chana、Acerbi & Stubbersfield、Griffiths & Kalish、Kirby et al.、Ren et al.、Cui & Yu）
- [raw/SCHEMA.md](raw/SCHEMA.md)：每个系统的记录模板
