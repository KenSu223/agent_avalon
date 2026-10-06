"""Summarise the closed-book audit: per benchmark x subset x protocol."""
import json, sys, collections, math
from pathlib import Path
R = Path(__file__).parent / "results"
f = sys.argv[1] if len(sys.argv) > 1 else str(R / "closed_book_qwen3-235b-a22b-2507.jsonl")
rows = [json.loads(l) for l in open(f)]


def acc(rs, key="correct"):
    v = [bool(r.get(key)) for r in rs if r.get(key) is not None]
    return (sum(v) / len(v) if v else float("nan")), len(v)


def ci(p, n):
    if n == 0 or p != p:
        return ""
    h = 1.96 * math.sqrt(p * (1 - p) / n)
    return f"[{max(0,p-h):.2f},{min(1,p+h):.2f}]"


print(f"source: {f}\n")
for bench in ("LongMemEval", "LoCoMo", "MemoryAgentBench", "PrefEval"):
    B = [r for r in rows if r["bench"] == bench]
    print(f"=== {bench} ===")
    print(f"{'subset':38s} {'n':>5s} {'natural (memoryless score)':>28s} {'forced guess (prior-answerable)':>32s}")
    subs = sorted({r["sub"] for r in B})
    for s in subs + ["__ALL__"]:
        rs = B if s == "__ALL__" else [r for r in B if r["sub"] == s]
        nat = [r for r in rs if r["proto"] == "natural"]; frc = [r for r in rs if r["proto"] == "forced"]
        a1, n1 = acc(nat); a2, n2 = acc(frc)
        print(f"{s:38s} {n1:5d} {a1:10.3f} {ci(a1,n1):>17s} {a2:12.3f} {ci(a2,n2):>19s}")
    if bench == "LoCoMo":
        for proto in ("natural", "forced"):
            rs = [r for r in B if r["proto"] == proto and r["category"] != 5]
            a, n = acc(rs)
            f1 = sum(r["f1"] for r in rs) / len(rs)
            print(f"  categories 1-4 only ({proto}): judge acc {a:.3f} (n={n}), official token-F1 {f1:.3f}")
    print()
