"""Summarise probed framework snapshots.

Per framework x checkpoint x version (C = schema-congruent, I = schema-incongruent):
  memory state (both judges agree): RETAINED / DROPPED / FLIPPED
  belief (agent answers from the framework's own context): KEPT (told version) / REVERTED (the other one)
Key contrasts at the last checkpoint, with user-level bootstrap CIs:
  flip asymmetry      FLIPPED(I) - FLIPPED(C)    : regularisation toward the schema in the memory text
  retention gap       RETAINED(C) - RETAINED(I)
  belief gap          KEPT(C) - KEPT(I)          : how much more often the agent loses the counter-schema version
"""
import json, glob, collections, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
_BASE = ["raw_history", "mem0", "mem0_v1", "nemori", "langmem", "llamaindex_facts", "langchain_summary", "codex", "openhands", "aider",
         "gemini_cli", "anthropic_api", "neutral_roll"]
ORDER = _BASE + [b + "@8b" for b in _BASE]


def load():
    rows = []
    for f in glob.glob(str(RES / "probed_*.jsonl")):
        if "smoke" in f:
            continue
        for l in open(f):
            r = json.loads(l)
            if str(r.get("model", "")).startswith("local:"):
                r["framework"] = r["framework"] + "@8b"
            rows.append(r)
    return rows


def rate(rs, field, val):
    rs = [r for r in rs if r.get(field) not in (None, "DISAGREE", "UNPARSED")]
    return (sum(r[field] == val for r in rs) / len(rs)) if rs else float("nan"), len(rs)


def boot(rows, fn, n=1000, seed=0):
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["user"]].append(r)
    users = sorted(by)
    vals = []
    for _ in range(n):
        samp = [r for u in (rng.choice(users) for _ in users) for r in by[u]]
        v = fn(samp)
        if v == v:
            vals.append(v)
    vals.sort()
    return fn(rows), vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


def contrasts(rs):
    C = [r for r in rs if r["version"] == "C"]; I = [r for r in rs if r["version"] == "I"]
    return {
        "flip_asym": lambda s: rate([r for r in s if r["version"] == "I"], "state", "FLIPPED")[0] - rate([r for r in s if r["version"] == "C"], "state", "FLIPPED")[0],
        "retention_gap": lambda s: rate([r for r in s if r["version"] == "C"], "state", "RETAINED")[0] - rate([r for r in s if r["version"] == "I"], "state", "RETAINED")[0],
        "belief_gap": lambda s: rate([r for r in s if r["version"] == "C"], "belief", "KEPT")[0] - rate([r for r in s if r["version"] == "I"], "belief", "KEPT")[0],
    }


def main(subset=None):
    rows = load()
    if subset:
        rows = [r for r in rows if subset(r)]
    fws = [f for f in ORDER if any(r["framework"] == f for r in rows)]
    last = max(r["ckpt"] for r in rows)
    print(f"judge agreement: {sum(r['state'] != 'DISAGREE' for r in rows) / len(rows):.3f}   (n={len(rows)})\n")
    print(f"{'framework':18s} ckpt | C: ret  drop flip | I: ret  drop flip | belief kept C   I")
    for f in fws:
        for k in sorted({r["ckpt"] for r in rows if r["framework"] == f}):
            rs = [r for r in rows if r["framework"] == f and r["ckpt"] == k]
            C = [r for r in rs if r["version"] == "C"]; I = [r for r in rs if r["version"] == "I"]
            cs = [rate(C, "state", s)[0] for s in ("RETAINED", "DROPPED", "FLIPPED")]
            is_ = [rate(I, "state", s)[0] for s in ("RETAINED", "DROPPED", "FLIPPED")]
            print(f"{f:18s} {k:4d} | {cs[0]:.2f} {cs[1]:.2f} {cs[2]:.2f} | {is_[0]:.2f} {is_[1]:.2f} {is_[2]:.2f} | {rate(C, 'belief', 'KEPT')[0]:.2f} {rate(I, 'belief', 'KEPT')[0]:.2f}")
        print()
    print(f"\n=== contrasts at the last checkpoint (k={last}), user-level bootstrap 95% CI ===")
    print(f"{'framework':18s} {'flip asym I-C':>24s} {'retention gap C-I':>24s} {'belief gap C-I':>24s}")
    for f in fws:
        rs = [r for r in rows if r["framework"] == f and r["ckpt"] == last]
        out = []
        for name, fn in contrasts(rs).items():
            v, lo, hi = boot(rs, fn)
            out.append(f"{v:+.3f} [{lo:+.3f},{hi:+.3f}]")
        print(f"{f:18s} {out[0]:>24s} {out[1]:>24s} {out[2]:>24s}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    sub = {"all": None,
           "descriptive": lambda r: r["type"] in ("rule", "procedure") and not r["normative"],
           "normative": lambda r: r["normative"],
           "preference": lambda r: r["type"] == "preference"}[which]
    main(sub)
