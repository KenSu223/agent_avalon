"""Author, scrub, SELECT and validate the E-SHIFT frames.

Selection is on elicitation Half A (worlds 0..1); the reported achieved shift and everything the
retention analysis uses come from the INDEPENDENT Half B (worlds 2..3). Selecting the best-shifting
draft is therefore legitimate: the winner's curse lands entirely in Half A, which is never reused.
"""
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat, estimate_cost
from stimuli import load_families, ROOT
import frames as F
import priors as P

RES = ROOT / "results"
N_DRAFT = 14
HALF_A = list(range(P.N_WORLDS // 2))
HALF_B = list(range(P.N_WORLDS // 2, P.N_WORLDS))


def main():
    fams = load_families()
    pri = json.loads((RES / "priors.json").read_text())
    bt_all = {k: {h: {int(i): x for i, x in v.items()} for h, v in d.items()}
              for k, d in pri["bt"].items()}
    targets = F.pick_targets(fams, bt_all)
    cands, rejected = F.generate(fams, targets, n_draft=N_DRAFT)
    n_c = sum(len(v) for v in cands.values())
    print(f"{len(cands)}/{len(targets)} families with >=1 clean draft; {n_c} clean drafts total "
          f"({len(rejected)} rejected)", flush=True)

    # ---- Half A: select the best-shifting draft per family
    reqs, meta = F.shift_requests(fams, cands, worlds=HALF_A)
    print(f"Half-A selection: {len(reqs)} calls, est ${estimate_cost(F.MODEL, len(reqs), 170, 3):.3f}",
          flush=True)
    res = batch_chat(reqs, workers=16, desc="shiftA")
    sA = F.shift_collect(res, meta, fams)

    best = {}
    for fid, drafts in cands.items():
        scored = []
        for i, d in enumerate(drafts):
            s = sA.get((fid, i), {}).get("A")
            if not s or "F+" not in s or "F-" not in s:
                continue
            tgt = d["target_level"]
            scored.append((s["F+"][tgt] - s["F-"][tgt], i, d))
        if scored:
            scored.sort(key=lambda x: -x[0])
            shift_a, i, d = scored[0]
            best[fid] = dict(d, cand=i, shift_A=shift_a,
                             n_clean_drafts=len(drafts),
                             all_shift_A=[round(x[0], 3) for x in scored])

    # ---- Half B: estimate the achieved shift for the selected draft only
    sel = {fid: [d] for fid, d in best.items()}
    reqs2, meta2 = F.shift_requests(fams, sel, worlds=HALF_B)
    print(f"Half-B estimation: {len(reqs2)} calls, est "
          f"${estimate_cost(F.MODEL, len(reqs2), 170, 3):.3f}", flush=True)
    res2 = batch_chat(reqs2, workers=16, desc="shiftB")
    sB = F.shift_collect(res2, meta2, fams)

    out = {}
    for fid, d in best.items():
        rec = dict(d)
        s = sB.get((fid, 0), {}).get("B")
        tgt = d["target_level"]
        rec["shift_B"] = (s["F+"][tgt] - s["F-"][tgt]) if s and "F+" in s and "F-" in s else None
        rec["eligible"] = rec["shift_A"] >= F.MIN_SHIFT
        out[fid] = rec

    elig = sorted(f for f, r in out.items() if r["eligible"])
    r_frac = len(elig) / max(1, len(out))
    (RES / "frames.json").write_text(json.dumps(
        {"frames": out, "rejected_drafts": rejected, "min_shift": F.MIN_SHIFT,
         "n_drafts_per_family": N_DRAFT, "half_A_worlds": HALF_A, "half_B_worlds": HALF_B,
         "n_eligible": len(elig), "eligible_fraction_r": r_frac, "eligible": elig}, indent=1))
    print(f"\neligible (Half-A shift >= {F.MIN_SHIFT}): {len(elig)}/{len(out)}  r = {r_frac:.2f}",
          flush=True)
    sb = [r["shift_B"] for f, r in out.items() if r["eligible"] and r["shift_B"] is not None]
    if sb:
        print(f"achieved shift on the INDEPENDENT Half B (eligible only): "
              f"mean {statistics.mean(sb):+.2f}  median {statistics.median(sb):+.2f} log-odds; "
              f"{sum(1 for x in sb if x > 0)}/{len(sb)} in the predicted direction")
    sb_all = [r["shift_B"] for r in out.values() if r["shift_B"] is not None]
    if sb_all:
        print(f"ITT (all families, Half B): mean {statistics.mean(sb_all):+.2f} log-odds")


if __name__ == "__main__":
    main()
