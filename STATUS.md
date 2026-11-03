# 项目状态总览（branch `memory-prior-paper`）

最后更新：2026-10-15。

**范围**：只研究 LLM agent 的记忆与持续学习，不涉及安全框架。目标是 ACL 2027（ARR 截稿 2027-01-04）。

---

## 当前结论（一句话）
- **记忆基准把"猜对"算成了"记住"。** 无论失败发生在写入、更新还是检索，只要证据没送到读取模型面前，模型仍能凭先验猜对；原始准确率分不出这两者。
- **先验从读取端进入，不从写入端进入。** 记忆系统删除时不区分是否符合常识、几乎不改写成常识版本；条目被删后，智能体用先验补位（Aider 保留 0%，常识题照样答对 97%）。
- **拒答倾向是混淆因素。** 记忆差的系统之间，原始分差主要来自敢不敢猜（拒答率与强制作答提分的等级相关 0.75–0.93）；LoCoMo 不可回答类别在奖励遗忘。

**论文主线（2026-10-06 定，2026-10-13 更新表述）**
- 核心贡献是评测方法 PCME：主指标为抗先验题准确率（论文中叫 CPA，代码和内部文档仍叫 cpr），辅以扣除猜测后的分数（PCS，只在强制作答下成立）和不可回答题的区分度。
- 测量目标是**证据送达率**：证据被写入、经过更新仍在、作答时被检索送达；不是只测存储（METHOD §9 术语说明）。
- 对现有基准做审计和重新打分；用 504 对同一槽位的 C/I 最小对做受控实验，提供真实保留率来验证校正，并定位先验从哪里进入。
- 论文稿：[paper_v2/](paper_v2/)。研究记录：[framework_study/FINDINGS_AND_DIRECTION.md](framework_study/FINDINGS_AND_DIRECTION.md)。

## 时间线

| 阶段 | 内容 | 结论 | 位置 |
|---|---|---|---|
| 0 | Idea 1 方案（v3）、调研、pilot 方案 | — | `docs/idea/` |
| 1 | ARIS 无人值守全流程（之后 PI 决定不再使用 ARIS） | 产出一篇负结果论文：意外程度对保留率没有影响。**事后审查发现三个问题**：(1) 刺激材料多为数值型的清单式事实，不像 Bartlett 的材料；(2) 删掉了最接近 Bartlett 的生动条目；(3) 偏好的"默认等级"写成了空话（"无所谓"）。另外**没有测任何真实记忆框架**；还在 worktree 外修改了一个软链接（codex-code-mode-host，原目标已失效，改动属于修复） | `paper/`、`refine-logs/`、`review-stage/`、`results/`、`src/`、`PIPELINE_STATUS.md` |
| 2 | 重做数据集：44 对反常识 minimal pair，加 V1–V3 质量检验 | V1 先验：在 Qwen3-235B 上 43/44 条 ≥ 0.9。V2 理解检验：剔除会被模型主动"纠正"的条目（S02、S08）和方向有歧义的条目（S06）。V3 Bartlett 正对照：违背常识的版本**单向**被规整回常识（4–5%），符合常识的版本从不被改成违背常识（0%） | `framework_study/stimuli/`、`framework_study/results/validation_*`、`v3_*` |
| 3 | 11 个真实记忆系统 + 完整历史上限（Nemori 后来补入，见第 7 行）；43 个模拟用户；12 个无关会话 | 删除不区分常识，改写 ≤1%；信念差距从 +0.04（Mem0 1.0.11）到 +0.96（Aider）；改写的范围决定损失大小 | `framework_study/RESULTS.md`、`results/summary_*.txt`、`decompose.txt`、`inflation.txt` |
| 4 | 查新：3 个并行检索方向 | "先验抬高分数"的原则已有人提出（Ground Truth First、MemGym、100-LongBench、PersonaMem-v2 等）。仍然新的是：(a) 审计旧基准；(b) 给现有系统重新打分；(c) 同一槽位的 C/I 成对设计，以及"删除不看先验、读取由先验补全"的因果链。最大撞车风险：PersonaMem-v2。必须对照：Nemori | `framework_study/FINDINGS_AND_DIRECTION.md` §7 |
| 5 | 现有基准闭卷审计（第一轮，答题模型 Qwen3-235B） | 能被先验答对的比例因基准而异，从 7% 到 47%：MemoryAgentBench 检索部分 35–47%；LoCoMo 第 1–4 类 16%，算上第 5 类后什么都不存也能白拿 22.8 分；LongMemEval 16%；PrefEval 7% | `benchmark_audit/`、`FINDINGS_AND_DIRECTION.md` §8 |
| 6 | 第二个答题模型（Llama-3.3-70B）复核闭卷审计 | 各基准的总体比例与 Qwen 一致；两个模型中至少一个能答对的比例（可被先验答对的上界）：LongMemEval 25%，LoCoMo 第 1–4 类 24%，MemoryAgentBench-AR 49–63% | `FINDINGS_AND_DIRECTION.md` §8.1 |
| 7 | Nemori（考虑先验的写入策略）对照 | C 和 I 都保留 100%：它实际上是只追加、全部存下，Predict-Calibrate 并没有把常识条目过滤掉 | §9 |
| 8 | 弱压缩模型（本地 Qwen3-8B） | 删得多得多，仍然几乎不改写；在唯一没有删光的系统（中性重写）里出现了按先验方向的删除：+9.1 个百分点，CI 不含 0 | §10 |
| 9 | 用 12 个系统在现有基准上重新打分 | MemoryAgentBench-AR：9/11 个系统在抗先验题上 ≤4%，排名 Spearman 0.664。LoCoMo 第 1–4 类：排名稳定（0.979）；第 5 类反过来奖励遗忘（Aider 0.86，Raw RAG 0.55） | §11 |
| 10 | 固定底座模型能否抵消先验（得分分解） | 不能。只有当各系统放弃作答倾向和保留选择都一致时，先验才只是常数偏移。实测中，可答题上的放弃作答率在 MemoryAgentBench 为 0–59%、在 LoCoMo 为 5–64%，和可答题准确率的 Spearman 分别为 −0.83 和 −0.95。LoCoMo 排名稳定只是碰巧；MemoryAgentBench 上，记忆接近零的系统比的是"敢不敢猜"。据此调整论文表述 | `FINDINGS_AND_DIRECTION.md` §12、`benchmark_audit/fixed_model_check.py` |
| 11 | 第 1 步：评测方法形式化与预先登记的性质检验 | 方法规格（METHOD.md）、工具 pcme.py（20 个测试）、4 个参照系统。抗先验分层有效：泄漏率 ≤ 0.011；给了证据后抗先验题能答对，正确率 0.72–0.76。只靠指令做不到强制作答，拒答率最高 75%；g 必须用评测 prompt 本身估计，这样下限检验在三个基准上都等价。PCS 与真实保持率的平均绝对误差是 0.018，原始准确率是 0.303。更正了 MemoryAgentBench 的 Spearman（0.664 改为 0.779，没有确认的排名反转），以及"上界"的表述 | `method/`、`FINDINGS_AND_DIRECTION.md` §13 |
| 12 | 第 2 步：作答协议对照 | 放弃作答率决定了强制作答带来的提分，H1 在 LoCoMo、QA1、QA2 上都成立；统一协议并不能恢复按记忆的排名（H2 不成立）；不可回答题的计分奖励遗忘（H7）；改成按阈值触发压缩后，先验虚高依然存在（13/14 个组合）；没有确认的排名反转 | §14 |
| 13 | 第 3 步：扩展数据集 | 724 对候选，按预先登记的门槛入选 504 对；先验因模型而异；看似任意的二选一也有先验；V3 正对照复现 | §15 |
| 14 | 第 4 步：换模型家族复现（Llama-3.3-70B，S4 共 432 对，192 个用户） | ΔR≈0、ΔF≈0、ΔK 随删除率上升，在两个家族都复现；保持率排名跨家族 ρ=0.95；知识更新违背先验时退回旧值的比例高 43–47 个百分点；无先验对照的设计有缺陷 | §16 |
| 15 | 收尾项 5a：查新"LoCoMo 第 5 类奖励遗忘" | 第 5 类的争议已有人指出（Zep 与 Mem0 之争、2607.21503）；跨系统量化（正确拒答率与 CPA 的等级相关 −0.87）和区分度 J（+0.73）没有人做过 | §7.1 |
| 16 | 收尾项 5b：弱压缩模型（Llama-3.1-8B）不触底版本 | 大多数条目两次会话内就被删光；在未触底的单元里 ΔR = +0.04 [−0.04, +0.12]，按先验方向删除的预测不成立 | §17 |
| 17 | 收尾项 5c：LangMem 调高递归上限到 100 重跑 | 两个文档上仍在读入阶段报 GraphRecursionError，记为框架失败 | §11.4 |
| 18 | 第 6 项多智能体共享记忆 | PI 2026-10-11 决定不做，转向写论文 | PLAN 第 6 项 |
| 19 | 论文初稿 v2（2026-10-11） | 官方 ACL 模板；数字、表格、3 张图都由脚本从已提交结果生成；参考文献逐条对照 arXiv 核实（修正 4 处） | `paper_v2/`、PLAN 第 8 项 |
| 20 | 定位调研与表述修改（2026-10-13） | 文献显示：先抽取再存的系统存储损失大（HaluMem 抽取召回 <60%），保留原始历史时瓶颈在检索和阅读，更新与冲突最弱；新基准已开始从构造上规避先验，但 LoCoMo、LongMemEval 仍是报头条成绩的主战场且从未被审计。据此把测量目标改称"证据送达率"、主指标改称 CPA，相关工作新增"定位记忆失败"，加重更新与冲突；补充"共享读取模型为何抵消不了先验"的论证 | FINDINGS §7.2、PLAN 第 8 项 |

## 进行中与下一步
**权威执行计划见 [PLAN.md](PLAN.md)（按顺序执行，不得漏项）。**
- 第 1–4 步完成（2026-10-10 至 10-11），收尾项 5a、5b、5c 完成，第 6 项按 PI 决定不做。
- **选项顺序检查（2026-10-27 发现）**：step 4 的信念探针总是把常识答案（C）列在第一个，可能抬高信念差距 ΔK。已预先登记（`framework_study/ORDER_CHECK_DESIGN.md`），**待在 ubuntu 上按 `framework_study/ORDER_CHECK_RUNBOOK.md` 运行**（≤ $15）。运行之前，论文中的 ΔK、无先验对照和 PCS 校准数字都来自 C 在前的探针。
- **第 7 项人工校验：等 PI 团队。** 150 条判定标签（`human_validation/stratified_150.jsonl`）和 100 条数据集审阅（`framework_study/stimuli/human_review_sheet.csv`）。完成前论文不报告任何人工结果。
- **第 8 项论文：初稿 v2 已成稿**，正文写满 8 页（上限 8 页），补入人工校验结果时需要压缩篇幅。投稿前还要：通读核对每个说法与生成的数字；重新查新（ACL Anthology 和 arXiv）；恢复官方字体设置（本机未装 inconsolata）。
- 累计 Bedrock 花费 **$307.19**（截至 2026-10-15；代理硬上限 $490，PI 绝对上限 $500）。

## 目录
| 路径 | 内容 |
|---|---|
| `docs/idea/` | Idea 1 方案 v3、查新、compaction 调研、pilot 方案 |
| `framework_study/stimuli/` | 新数据集（`items.jsonl`、`build_items.py`）、干扰会话 |
| `framework_study/src/` | 验证（`validate.py`、`v3_reproduction.py`）、框架适配器（`frameworks.py`）、执行（`run_framework.py`）、探测（`probe.py`）、分析脚本 |
| `framework_study/prompts/` | 各产品 compaction prompt 原文（Codex、OpenHands、Aider、Gemini CLI，均固定到具体 commit） |
| `framework_study/results/` | 快照、探测结果、汇总表。`capped20_*` 是被 `get_all` 默认上限截断的 Mem0 旧结果，不参与分析 |
| `method/` | PCME 评测方法：规格 `METHOD.md`（预先登记，附变更记录）、工具 `pcme.py` 及测试、先验抽取、参照系统、性质检验，结果在 `method/results/` |
| `benchmark_audit/` | 闭卷审计脚本、官方评判 prompt（`official/`）、结果。原始数据在 `benchmark_audit/data/`，已被 gitignore |
| `infra/llm.py` | 模型调用客户端：Bedrock 经过预算代理，本地走 vLLM，带磁盘缓存 |
| `PLAN.md` | 权威执行计划、预算分配、偏离记录、完成日志 |
| `framework_study/stimuli/items_v2*`、`items_v2/` | 第 3 步数据集：724 对候选、504 对入选（`items_v2_final.jsonl`），datasheet 和人工审阅表 |
| `prompts/` | 流程中用到的全部 prompt 存档（模板、逐字节核对过的完整请求样例、库内部 prompt）；提交前运行 `check_prompts.py` |
| `human_validation/` | 待 PI 团队标注的 150 条判定样本 |
| `paper_v2/` | 论文稿（ACL 模板）；`make_numbers.py`、`make_tables.py`、`make_figures.py` 从结果文件生成全部数字、表格和图 |
| 其余（`paper/`、`refine-logs/`、`results/`、`src/` 等） | ARIS 阶段的产物 |

## 基础设施（不在仓库内，位于本机 `/home/ubuntu/llm_infra/`）
- **Bedrock 预算代理**：127.0.0.1:8787，支持工具调用和流式输出，硬上限 **$490**（PI 的绝对上限 $500，2026-10-10 由 $150 提高）；每个请求都有日志。查询花费：`curl -s 127.0.0.1:8787/v1/budget`。读入历史期间不要重启代理。
- **本地 vLLM**：Qwen3-8B，127.0.0.1:8001。
- **本地 CPU embedding 服务**：bge-small-en-v1.5，127.0.0.1:8002。
- **框架运行环境**：`fw-env`（Python 3.12：Mem0 2.2.1、LangMem、LangChain、LlamaIndex）、`mem0v1-env`（Mem0 1.0.11）和 `nemori-env`（Nemori，配 docker 中的 PostgreSQL 和 Qdrant）。
- **累计 Bedrock 花费**：**$307.19**（截至 2026-10-15）。主要去向：第 2 步约 $85，第 4 步约 $119；按模型分 Qwen3-235B $171、Llama-3.3-70B $73、gpt-oss-120b $32、gemma-3-27b $28。

## 数据许可说明
- `benchmark_audit/results/` 和 `method/results/` 中含有 LoCoMo 和 PrefEval 的题目原文（`method/results/refsys_*` 中还有 LoCoMo 的对话片段），两者都是 CC BY-NC 4.0；本仓库是私有仓库，仅用于非商业研究。是否把项目算作商业用途，仍待 PI 决定（方案 §11.5）。
- LongMemEval 是 MIT；MemoryAgentBench 的 HF 标签是 MIT，但论文写的是 CC BY 4.0，两者不一致。
- 我们自建的刺激材料由我们自己编写。
