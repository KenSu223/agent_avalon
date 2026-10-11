"""Human spot-check sheet for the expanded item set (PLAN 3.3; STEP3_DESIGN.md §4).

Stratified random sample of 100 final items: allocation proportional to type (at least 5 per type), and within each
type half from the strongest-prior half and half from the weaker half (Qwen3-235B V1). Seed 0.
The sheet shows exactly what Sam says in each version, the question and the options, and has empty columns for the
reviewer. Results are reported only after real people fill it in (never by an LLM).
Output: human_review_sheet.csv (+ human_review_instructions.md)
"""
import csv, json, random, collections
from pathlib import Path
HERE = Path(__file__).parent
N = 100


def said(x, ver):
    v = x[ver]
    if x["type"] == "update":
        return f"(earlier) {x['initial_lead']}{v['initial']}.  (later) {x['lead']}{v['clause']}."
    return f"{x['lead']}{v['clause']}."


def main():
    items = [json.loads(l) for l in open(HERE / "items_v2_final.jsonl")]
    rng = random.Random(0)
    by = collections.defaultdict(list)
    for x in items:
        by[x["type"]].append(x)
    alloc = {t: max(5, round(N * len(v) / len(items))) for t, v in by.items()}
    while sum(alloc.values()) > N:
        t = max(alloc, key=lambda k: alloc[k]); alloc[t] -= 1
    while sum(alloc.values()) < N:
        t = max(by, key=lambda k: len(by[k]) - alloc[k]); alloc[t] += 1
    sample = []
    for t, v in by.items():
        v = sorted(v, key=lambda x: -(x["prior"]["qwen"] or 0))
        hi, lo = v[:len(v) // 2], v[len(v) // 2:]
        k = alloc[t]
        sample += rng.sample(hi, min(len(hi), k - k // 2)) + rng.sample(lo, min(len(lo), k // 2))
    rng.shuffle(sample)
    cols = ["id", "type", "question", "option_1", "option_2", "version_C_what_Sam_says", "version_C_answer",
            "version_I_what_Sam_says", "version_I_answer",
            "R1_natural_1to5", "R2_versions_differ_only_in_key_content_Y_N", "R3_I_version_plausible_as_local_rule_Y_N",
            "R4_any_hint_or_surprise_marker_Y_N", "R5_question_and_options_clear_Y_N", "R6_C_is_the_common_sense_version_Y_N", "comments"]
    with open(HERE / "human_review_sheet.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for x in sample:
            w.writerow([x["id"], x["type"], x["question"], x["options"][0], x["options"][1], said(x, "C"), x["C"]["answer"],
                        said(x, "I"), x["I"]["answer"]] + [""] * 7)
    (HERE / "human_review_instructions.md").write_text("""# 人工抽查说明（PLAN 第 3.3 项）

`human_review_sheet.csv` 里共 100 个条目，是按类型和先验强度分层随机抽取的（seed 0）。每个条目有两个版本：
- **C**：符合常识的版本；
- **I**：违背常识、但作为某家公司的本地规定说得通的版本。
"what Sam says" 一列就是对话里实际出现的那句话。知识更新类条目会依次列出旧值和更新。

请每位审阅者独立填写以下各列，**不要和其他审阅者讨论，也不要借助 AI**：
- **R1 自然度**（1–5）：这句话放在工作场景的对话里，读起来是否自然。
- **R2**：C、I 两个版本是否只差关键内容（Y/N）。
- **R3**：I 版本作为一家公司的本地规定，是否说得通（Y/N）。
- **R4**：句子里有没有任何提示或惊讶语气，比如 "actually"（Y/N）。
- **R5**：问题和两个选项是否清楚、没有歧义（Y/N）。
- **R6**：C 版本是否确实是更符合常识的那一个（Y/N）。对 neutral 类，如果两个选项一样任意，就填 N/A。
- **comments**：其他意见。

建议至少由两位审阅者完成，用来计算评分者间一致性。在真人完成之前，论文和 FINDINGS 都不报告任何人工结果。
""")
    print("sampled", len(sample), dict(collections.Counter(x["type"] for x in sample)))


if __name__ == "__main__":
    main()
