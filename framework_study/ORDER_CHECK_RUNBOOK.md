# 选项顺序检查：运行手册（在 ubuntu 机器上执行）

写于 2026-11-03。本文件是**操作步骤**；要检验什么、怎么判定，以 [ORDER_CHECK_DESIGN.md](ORDER_CHECK_DESIGN.md) v1.0（commit `4ef3baa`，预先登记）为准。两者冲突时以设计文档为准，并把冲突记进本文末尾的"偏离记录"。

## 给执行者的规则（人或 agent 都适用）
1. **从第 1 步开始，严格按顺序执行，不跳步。**每一步都有"通过条件"；不通过就停下，在"偏离记录"里写清楚现象，然后报告 PI，不要自己想办法绕过去。
2. **不修改**设计文档、`probe_order.py`、`analyse_order.py`、`order_e0.py`、`questions_ifirst.json`。确实必须改，就先停下来报告。
3. **不修改论文**（`paper_v2/` 下任何文件）。本次只产出结果和判定；改论文是之后的单独一步。
4. 项目的硬规则照常适用（见 `CLAUDE.md`）：Bedrock 只通过 `infra/llm.py` 和预算代理调用；不碰代理的凭证；**运行期间不要重启代理**；只 commit，**不 push**。
5. 每条命令的输出都要保存（下面的命令已经写好了日志路径）。最后 commit 的内容见第 10 步。

## 0. 这个检查是做什么的（三句话）
- step 4 的信念探针问 agent 时，**常识答案（C）永远排在第一个选项**，题干里也几乎总是先提 C。模型在不确定时可能偏好选第一个，这会和"按常识猜"混在一起，抬高论文里的信念差距 ΔK。
- 本检查把题干和选项行都换成 **I 在前**，用 step 4 **已经保存的记忆内容**重新问一遍（臂 R）；另有一组只换选项行、不换题干（臂 L）。不重跑任何记忆系统。
- 对比两种顺序下"条目被删后选常识答案的比例"，就能分出位置偏好占多少；论文该怎么改，设计文档 §5 已经事先定好。

## 1. 拿到代码并核对版本
在项目目录 `/home/ubuntu/agent_avalon/memory_prior/` 执行：

```bash
cd /home/ubuntu/agent_avalon/memory_prior
git status --short            # 记下有没有未提交的改动；有的话先报告 PI，不要覆盖
git branch --show-current     # 应为 memory-prior-paper
```

代码同步由 PI 负责（例如在 Mac 上 push 到 GitHub，在这里 `git pull`）。同步后核对：

```bash
git log --oneline -5          # 应能看到 4ef3baa "Option-order check pre-registration v1.0"
for f in framework_study/ORDER_CHECK_DESIGN.md framework_study/ORDER_CHECK_RUNBOOK.md \
         framework_study/src/probe_order.py framework_study/src/analyse_order.py framework_study/src/order_e0.py \
         framework_study/stimuli/questions_ifirst.json; do test -f "$f" && echo "ok  $f" || echo "MISSING  $f"; done
git diff --stat 4ef3baa -- framework_study/ORDER_CHECK_DESIGN.md framework_study/src/probe_order.py \
         framework_study/src/analyse_order.py framework_study/src/order_e0.py framework_study/stimuli/questions_ifirst.json
```

**通过条件**：6 个文件都是 `ok`；最后一条 `git diff` **没有任何输出**（说明登记后的设计和代码没有被改过）。

## 2. 环境检查

```bash
curl -s 127.0.0.1:8787/v1/budget                         # 预算代理
ls -la cache/llm_cache.sqlite                            # LLM 缓存（S0 和 E0 都要用）
ls framework_study/results/snapshots_*_s4qwen.jsonl framework_study/results/snapshots_*_s4llama.jsonl \
   framework_study/results/probed_*_s4qwen.jsonl framework_study/results/probed_*_s4llama.jsonl | wc -l
PY=/home/ubuntu/llm_infra/fw-env/bin/python
$PY -c "import numpy; print('numpy', numpy.__version__)"
mkdir -p framework_study/logs/order_check
```

**通过条件**：
- 代理有响应。代理没开：`/home/ubuntu/llm_infra/proxyctl.sh start`。
- **剩余预算 ≥ $25**（本检查预计 ≤ $15.2，设计文档 §3.4）。不够就停下报告。
- 缓存文件存在。
- 输入文件数为 **36**（9 个系统 × 2 个家族 × snapshots 和 probed 两种）。
- `numpy` 能导入。

记下此刻的花费，填进第 10 步的记录里：

```bash
curl -s 127.0.0.1:8787/v1/budget | tee framework_study/logs/order_check/budget_before.json
```

## 3. E0：先验门槛按选项顺序拆开（免费，探索性）

```bash
cd framework_study/src
$PY order_e0.py 2>&1 | tee ../logs/order_check/e0.log
```

- 只读缓存，**不发任何请求**；输出 `framework_study/results/order_e0.json`。
- 打印 4 行（qwen/llama × 非对照/无先验对照），以及 `cache misses`。
- **通过条件**：脚本正常结束。E0 是探索性的，`cache misses` 不为 0 也不停，但要在第 9 步的记录里写上数量。

## 4. S0：逐字一致检查（免费，必须通过才能继续）
**这一步在检验什么**：`infra/llm.py` 把每一次发出去的请求都存进了缓存，缓存的键是"整个请求内容"的哈希，差一个字符都对不上。`--check-cache` 用新脚本把 step 4 当年的提问（C 在前的原样版本，即臂 O）重新拼出来，到缓存里查：
- 查得到：说明新脚本拼出的请求和 step 4 当年发出的**逐字相同**（同一个系统 prompt、同一份记忆内容、同一个问题、同样的解码参数）；再用缓存里的回答重算信念，应当和 step 4 存下的结果一致。
- 查不到：说明新脚本和当年有某处不同。这时如果直接跑反序，"顺序不同"和"别的地方也不同"会混在一起，对比就不干净了。

所以这一步通过，才能保证臂 R、L 与原结果之间**只有选项顺序这一个差别**。它离线运行，不调用模型，不花钱。

```bash
$PY probe_order.py --tiers 1 --check-cache 2>&1 | tee ../logs/order_check/s0_check.log
```

输出两行，形如：

```
s4qwen: 6538 rows, cache hits 6538 (1.0000), belief reproduced 6538 (1.0000)
s4llama: 6932 rows, cache hits 6932 (1.0000), belief reproduced 6932 (1.0000)
```

**通过条件**：两行的 `cache hits` 和 `belief reproduced` 都 **≥ 0.99**，行数分别是 6538 和 6932。**不通过就停下**：不要跑第 5 步，把输出贴进"偏离记录"并报告 PI。

## 5. 第 1 层：主检验（臂 R 和 L，约 $6）
先预估，再正式运行：

```bash
$PY probe_order.py --arms R L --tiers 1 --dry-run 2>&1 | tee ../logs/order_check/tier1_dryrun.log
```

应看到 4 行：s4qwen R 和 L 各 6538 次调用，s4llama R 和 L 各 6932 次调用，`TOTAL est` 约 **$5.96**。数字明显不同就停下报告。

正式运行（耗时可能几十分钟以上；step 4 时 Llama 被限流过）：

```bash
nohup $PY probe_order.py --arms R L --tiers 1 > ../logs/order_check/tier1_run1.log 2>&1 &
tail -f ../logs/order_check/tier1_run1.log        # Ctrl-C 只退出查看，不会停止运行
```

（agent 执行时不要用 `tail -f`，改用 `tail -n 20 ../logs/order_check/tier1_run1.log` 定期查看；进程是否还在：`pgrep -f probe_order.py`。）

- 脚本会先打印 `estimate_cost`；超过 $30（`--max-usd`）会自动停止。
- 估计超过 $2 时，脚本会**自动在 `COST_LOG.md` 末尾追加一行**，不要手动重复添加。
- 失败的调用（例如 HTTP 429 限流）**不会写入结果**。运行结束后，**用同一条命令再跑一次**（日志改名为 `tier1_run2.log`、`run3`…），它只会补跑缺的行；直到 dry-run 显示每个臂都是 `0 calls`：

```bash
$PY probe_order.py --arms R L --tiers 1 --dry-run
```

- 如果出现 `BudgetExceeded` 或 HTTP 402：立刻停下报告，不要重试。

**通过条件**：dry-run 四个臂都是 `0 calls`。

## 6. 第 2、3 层：其余行（只跑臂 R，约 $9）

```bash
$PY probe_order.py --arms R --tiers 2 3 --dry-run 2>&1 | tee ../logs/order_check/tier23_dryrun.log
```

应看到：s4qwen 16555 次调用（tier 3: 11520、tier 2: 5035），s4llama 16161 次调用（tier 3: 11520、tier 2: 4641），`TOTAL est` 约 **$9.28**。

```bash
nohup $PY probe_order.py --arms R --tiers 2 3 > ../logs/order_check/tier23_run1.log 2>&1 &
tail -f ../logs/order_check/tier23_run1.log
```

和第 5 步一样，跑完后重复同一条命令补齐，直到 dry-run 显示 `0 calls`。

## 7. 完整性检查

```bash
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/results
wc -l order_R_s4qwen.jsonl order_R_s4llama.jsonl order_L_s4qwen.jsonl order_L_s4llama.jsonl
for f in order_R_s4qwen.jsonl order_R_s4llama.jsonl order_L_s4qwen.jsonl order_L_s4llama.jsonl; do
  echo "$f  UNPARSED: $(grep -c '"belief": "UNPARSED"' $f)"; done
curl -s 127.0.0.1:8787/v1/budget | tee ../logs/order_check/budget_after.json
```

**期望行数**（全部补齐时）：

| 文件 | 行数 |
|---|---|
| `order_R_s4qwen.jsonl` | 23,093（6,538 + 16,555） |
| `order_R_s4llama.jsonl` | 23,093（6,932 + 16,161） |
| `order_L_s4qwen.jsonl` | 6,538 |
| `order_L_s4llama.jsonl` | 6,932 |

- 行数少于期望：回到第 5 或第 6 步补齐。补了 3 次以上仍有缺行，就记下缺多少行，继续往下走，并在结果里如实报告。
- `UNPARSED` 的行数照实记录（分析会自动排除它们，并报告数量）。

## 8. 分析（只运行一次）

```bash
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/src
$PY analyse_order.py 2>&1 | tee ../logs/order_check/analysis.log
```

- 输出 `framework_study/results/order_analysis.txt` 和 `order_analysis.json`。
- **分析只在第 5、6 步全部完成后运行一次**（设计文档 §6）。运行之后任何改动都要记为偏离，并且同时报告改动前后两个版本。

## 9. 按预先登记的规则判定，写进 FINDINGS
打开 `order_analysis.txt`，对照设计文档 §5 逐条判定，结果写进 `framework_study/FINDINGS_AND_DIRECTION.md` §18，新加一个小节"§18.1 结果（日期）"，内容包括：

1. **E1 主检验**：每个家族合并后的 π（含置信区间）、ΔK_O、ΔK_R、ΔK_B；删除率 ≥ 0.5 的每个系统的 π；判定结果是 **D1 / D2 / D3** 中的哪一个，以及依据哪一条。
2. **E2 无先验对照**：每个家族的 ΔK_O、ΔK_R、ΔK_B；判定是 **N-pos / N-label / N-mixed** 中的哪一个。
3. **E3 PCS 校准**：O、R、B 三种答案下的 MAE；P4.7 是否稳健；`\pcsMaeQwen`、`\pcsMaeLlama` 要不要改。
4. **E4a 知识更新**：P4.6 在 B 下是否仍然成立；`\updQwen`、`\updLlama` 要不要改。
5. **E0 和 E5**（探索性）：主要数字，标明"探索性"。
6. **对论文的影响**：按设计文档 §5，列出要改的宏、表格、图和句子。**只列出，不改论文。**判定为 **D3** 的，在 §18.1 开头写明"需要 PI 决定"。
7. 实际花费（`budget_after` 减 `budget_before`）、各步的补跑次数、最终缺行数和 UNPARSED 数。

同时把 §18 开头的"**状态：没有运行**"改为"已运行（日期），结果见 §18.1"。

## 10. 记录与提交
- `COST_LOG.md`：脚本已经自动追加了预估行。再手动加一行"实际花费"：日期、`option-order check actual`、实际金额、累计花费。
- `PLAN.md` 的"完成日志"加一行：日期、"选项顺序检查完成"、判定结果（D1/D2/D3、N-*）、结果文件、commit。
- `STATUS.md`：更新"累计 Bedrock 花费"。

然后提交（只提交下面这些文件；`framework_study/logs/` 被 gitignore，日志不进 git）：

```bash
cd /home/ubuntu/agent_avalon/memory_prior
git add framework_study/results/order_e0.json framework_study/results/order_R_s4qwen.jsonl \
        framework_study/results/order_R_s4llama.jsonl framework_study/results/order_L_s4qwen.jsonl \
        framework_study/results/order_L_s4llama.jsonl framework_study/results/order_analysis.txt \
        framework_study/results/order_analysis.json framework_study/FINDINGS_AND_DIRECTION.md \
        framework_study/ORDER_CHECK_RUNBOOK.md COST_LOG.md PLAN.md STATUS.md
git status --short            # 确认没有误加别的文件
git commit -m "Option-order check: results (arms R+L tier 1, R tiers 2-3); decision <D1/D2/D3>, <N-...>; FINDINGS §18.1"
```

**不要 push**；同步回 Mac 由 PI 负责。

## 11. 停止条件汇总
出现以下任何一种情况，就停下、记进偏离记录、报告 PI：

| 时机 | 情况 |
|---|---|
| 第 1 步 | 文件缺失，或登记后的设计和代码被改过（`git diff` 有输出） |
| 第 2 步 | 代理不可用，或剩余预算 < $25 |
| 第 4 步 | S0 任一指标 < 0.99 |
| 第 5、6 步 | dry-run 的调用数或预估金额和本手册明显不符；`estimate_cost` 超过 $30；`BudgetExceeded` / HTTP 402 |
| 第 9 步 | 判定为 D3（先报告 PI，论文怎么改由 PI 决定） |

## 偏离记录
（执行时填写：日期、步骤、现象、处理方式。没有偏离就写"无"。）
