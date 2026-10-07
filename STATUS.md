# 项目状态总览（branch `memory-prior-paper`）

最后更新：2026-10-06。

**范围**：只研究 LLM agent 的记忆与持续学习，不涉及安全框架。目标是 ACL 2027（ARR 截稿 2027-01-04）。

---

## 当前结论（一句话）
- **记忆系统删除内容时，不区分它是否符合常识。** 但条目被删掉以后，agent 会用先验把空缺补上，所以 **agent 的认知会向先验退化，而记忆文本本身并不会**。
- **用"合理的"题目考记忆系统，分数会被先验抬高。** 例如 Aider 实际保留 0%，常识题照样得 97 分。

**论文主线（PI 2026-10-06 定）**
- 现有的 memory benchmark 把"猜对"算成了"记住"。
- 我们提出同一槽位的 C/I minimal-pair benchmark，把两者区分开。
- 第二贡献："改写的范围"决定记忆损失有多大。

详见 [framework_study/FINDINGS_AND_DIRECTION.md](framework_study/FINDINGS_AND_DIRECTION.md)。

## 时间线

| 阶段 | 内容 | 结论 | 位置 |
|---|---|---|---|
| 0 | Idea 1 方案（v3）、调研、pilot 方案 | — | `docs/idea/` |
| 1 | ARIS 无人值守全流程（之后 PI 决定不再使用 ARIS） | 产出一篇负结果论文：意外程度对保留率没有影响。**事后审查发现三个问题**：(1) 刺激材料多为数值型的清单式事实，不像 Bartlett 的材料；(2) 删掉了最接近 Bartlett 的生动条目；(3) 偏好的"默认等级"写成了空话（"无所谓"）。另外**没有测任何真实记忆框架**；还在 worktree 外修改了一个软链接（codex-code-mode-host，原目标已失效，改动属于修复） | `paper/`、`refine-logs/`、`review-stage/`、`results/`、`src/`、`PIPELINE_STATUS.md` |
| 2 | 重做数据集：44 对反常识 minimal pair，加 V1–V3 质量检验 | V1 先验：在 Qwen3-235B 上 43/44 条 ≥ 0.9。V2 理解检验：剔除会被模型主动"纠正"的条目（S02、S08）和方向有歧义的条目（S06）。V3 Bartlett 正对照：违背常识的版本**单向**被规整回常识（4–5%），符合常识的版本从不被改成违背常识（0%） | `framework_study/stimuli/`、`framework_study/results/validation_*`、`v3_*` |
| 3 | 11 个真实记忆系统 + 完整历史上限；43 个模拟用户；12 个无关会话 | 删除不区分常识，改写 ≤1%；信念差距从 +0.04（Mem0 1.0.11）到 +0.96（Aider）；改写的范围决定损失大小 | `framework_study/RESULTS.md`、`results/summary_*.txt`、`decompose.txt`、`inflation.txt` |
| 4 | 查新：3 个并行检索方向 | "先验抬高分数"的原则已有人提出（Ground Truth First、MemGym、100-LongBench、PersonaMem-v2 等）。仍然新的是：(a) 审计旧基准；(b) 给现有系统重新打分；(c) 同一槽位的 C/I 成对设计，以及"删除不看先验、读取由先验补全"的因果链。最大撞车风险：PersonaMem-v2。必须对照：Nemori | `framework_study/FINDINGS_AND_DIRECTION.md` §7 |
| 5 | 现有基准闭卷审计（第一轮，答题模型 Qwen3-235B） | 能被先验答对的比例因基准而异，从 7% 到 47%：MemoryAgentBench 检索部分 35–47%；LoCoMo 第 1–4 类 16%，算上第 5 类后什么都不存也能白拿 22.8 分；LongMemEval 16%；PrefEval 7% | `benchmark_audit/`、`FINDINGS_AND_DIRECTION.md` §8 |

| 6 | 第二个答题模型（Llama-3.3-70B）复核闭卷审计 | 各基准的总体比例与 Qwen 一致；两个模型中至少一个能答对的比例（可被先验答对的上界）：LongMemEval 25%，LoCoMo 第 1–4 类 24%，MemoryAgentBench-AR 49–63% | `FINDINGS_AND_DIRECTION.md` §8.1 |
| 7 | Nemori（考虑先验的写入策略）对照 | C 和 I 都保留 100%：它实际上是只追加、全部存下，Predict-Calibrate 并没有把常识条目过滤掉 | §9 |
| 8 | 弱压缩模型（本地 Qwen3-8B） | 删得多得多，仍然几乎不改写；在唯一没有删光的系统（中性重写）里出现了按先验方向的删除：+9.1 个百分点，CI 不含 0 | §10 |
| 9 | 用 12 个系统在现有基准上重新打分 | MemoryAgentBench-AR：9/11 个系统在抗先验题上 ≤4%，排名 Spearman 0.664。LoCoMo 第 1–4 类：排名稳定（0.979）；第 5 类反过来奖励遗忘（Aider 0.86，Raw RAG 0.55） | §11 |

## 进行中与下一步
1. 下一阶段：**多智能体共享记忆**。
2. 待补：
   - 为弱模型的"按先验方向删除"补做不会触底的实验（加大容量或缩短链长）；
   - 对"LoCoMo 第 5 类奖励遗忘"做查新；
   - 人工校验；
   - LangMem 在长文档上的失败：可以调高 recursion_limit 后重跑，作为偏离默认设置的补充实验。

## 目录
| 路径 | 内容 |
|---|---|
| `docs/idea/` | Idea 1 方案 v3、查新、compaction 调研、pilot 方案 |
| `framework_study/stimuli/` | 新数据集（`items.jsonl`、`build_items.py`）、干扰会话 |
| `framework_study/src/` | 验证（`validate.py`、`v3_reproduction.py`）、框架适配器（`frameworks.py`）、执行（`run_framework.py`）、探测（`probe.py`）、分析脚本 |
| `framework_study/prompts/` | 各产品 compaction prompt 原文（Codex、OpenHands、Aider、Gemini CLI，均固定到具体 commit） |
| `framework_study/results/` | 快照、探测结果、汇总表。`capped20_*` 是被 `get_all` 默认上限截断的 Mem0 旧结果，不参与分析 |
| `benchmark_audit/` | 闭卷审计脚本、官方评判 prompt（`official/`）、结果。原始数据在 `benchmark_audit/data/`，已被 gitignore |
| `infra/llm.py` | 模型调用客户端：Bedrock 经过预算代理，本地走 vLLM，带磁盘缓存 |
| 其余（`paper/`、`refine-logs/`、`results/`、`src/` 等） | ARIS 阶段的产物 |

## 基础设施（不在仓库内，位于本机 `/home/ubuntu/llm_infra/`）
- **Bedrock 预算代理**：127.0.0.1:8787，支持工具调用和流式输出，硬上限 **$140**（PI 的上限是 $150）。查询花费：`curl -s 127.0.0.1:8787/v1/budget`。
- **本地 vLLM**：Qwen3-8B，127.0.0.1:8001。
- **本地 CPU embedding 服务**：bge-small-en-v1.5，127.0.0.1:8002。
- **框架运行环境**：`fw-env`（Python 3.12：Mem0 2.2.1、LangMem、LangChain、LlamaIndex）和 `mem0v1-env`（Mem0 1.0.11）。
- **累计 Bedrock 花费**：约 $40（ARIS 阶段 $19.88，其余为本轮研究）。

## 数据许可说明
- `benchmark_audit/results/` 中含有 LoCoMo 和 PrefEval 的题目原文，两者都是 CC BY-NC 4.0；本仓库是私有仓库，仅用于非商业研究。是否把项目算作商业用途，仍待 PI 决定（方案 §11.5）。
- LongMemEval 是 MIT；MemoryAgentBench 的 HF 标签是 MIT，但论文写的是 CC BY 4.0，两者不一致。
- 我们自建的刺激材料由我们自己编写。
