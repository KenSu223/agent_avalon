"""Does fixing the backbone model cancel the prior in framework comparisons?

Score decomposition. For system s and item i, let R_si be the probability the item is retained and usable, and
g_si the probability of answering correctly from the prior when it is not:
    acc_s = mean_i [ R_si + (1 - R_si) * g_si ]
If (A) retention is independent of guessability and (B) g_si = g_i is the same under every system, then
    acc_s = gbar + R_s * (1 - gbar)
which is monotone in R_s: the prior is a constant offset plus a compression factor, and ranks are preserved.

Two checks on the re-scoring results (prior-answerable = closed-book correct for Qwen3-235B or Llama-3.3-70B):
  1. abstention rate on prior-answerable items per system (a direct violation of B when it varies), and
  2. implied guess rate g_hat_s = (acc_answerable - acc_resistant) / (1 - acc_resistant), which (A) and (B)
     predict to be roughly constant across systems.
Output: results/fixed_model_check.txt
"""
import json, glob, re, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from summarise_rescore import closed_book_sets

R = Path(__file__).parent / "results"
ABS = re.compile(r"not (mentioned|provided|specified|available|included|contain|stated|found)|no (information|mention|record|details|data)|"
                 r"don'?t (know|have)|does not (contain|mention|include|specify|provide)|cannot (determine|answer|find)|unknown|unable to|"
                 r"isn'?t (mentioned|specified)|not in (the|my) memory|NOT_IN_MEMORY", re.I)


def spearman(x, y):
    n = len(x)
    rx = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: x[i]))}
    ry = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: y[i]))}
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1)) if n > 2 else float("nan")


def main():
    pa = closed_book_sets()
    out = []
    for bench, filt in (("mab_ruler", lambda r: r.get("sub") == "ruler_qa1"), ("locomo", lambda r: r["category"] != 5)):
        out.append(f"=== {bench} ===")
        out.append(f"{'system':26s} {'acc_all':>8s} {'acc_resist':>11s} {'acc_answ':>9s} {'abstain_answ':>13s} {'g_hat':>7s}")
        tab = []
        for f in sorted(glob.glob(str(R / f"rescore_{bench}_*.jsonl"))):
            s = Path(f).stem.replace(f"rescore_{bench}_", "")
            rows = [r for r in (json.loads(l) for l in open(f)) if filt(r)]
            if not rows:
                continue
            res = [r for r in rows if not pa[r["id"]]]
            ans = [r for r in rows if pa[r["id"]]]
            acc = lambda rs: sum(bool(r["correct"]) for r in rs) / len(rs)
            a_all, a_res, a_ans = acc(rows), acc(res), acc(ans)
            abst = sum(bool(ABS.search(r["pred"] or "")) for r in ans) / len(ans)
            g_hat = (a_ans - a_res) / (1 - a_res) if a_res < 1 else float("nan")
            tab.append((s, a_all, a_res, a_ans, abst, g_hat))
        for s, a_all, a_res, a_ans, abst, g in sorted(tab, key=lambda t: -t[1]):
            out.append(f"{s:26s} {a_all:8.3f} {a_res:11.3f} {a_ans:9.3f} {abst:13.3f} {g:7.3f}")
        gs = [t[5] for t in tab]
        out.append(f"implied guess rate g_hat across systems: min {min(gs):.3f}  max {max(gs):.3f}  sd {statistics.pstdev(gs):.3f}")
        out.append(f"Spearman(abstention on answerable items, acc on answerable items) = {spearman([t[4] for t in tab], [t[3] for t in tab]):.3f}")
        low = [t for t in tab if t[2] <= 0.05]
        if len(low) >= 3:
            out.append(f"systems with resistant acc <= 0.05 (n={len(low)}): their acc_all ranges {min(t[1] for t in low):.3f}-{max(t[1] for t in low):.3f}; "
                       f"Spearman(abstention, acc_all) among them = {spearman([t[4] for t in low], [t[1] for t in low]):.3f}")
        out.append("")
    text = "\n".join(out)
    (R / "fixed_model_check.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
