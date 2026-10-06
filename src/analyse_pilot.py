"""M2 analysis: choose the operating point, discharge A3 (O3 capacity) and prepare A1 (power)."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT
import analysis as A

RES = ROOT / "results"


import re


def _slots(r):
    if r.get("slots") is not None:
        return r["slots"]
    m = re.search(r"-O3-s(\d+)-", r.get("run_id", ""))
    return int(m.group(1)) if m else None


def summarise(rows):
    """retention at k=10 and realized stored length, by configuration."""
    by = defaultdict(lambda: {"ret": [], "words": [], "unres": 0, "n": 0})
    for r in rows:
        if r["k"] != 10:
            continue
        key = (r["op"], r["B"], r["T"], _slots(r))
        d = by[key]
        d["n"] += 1
        d["ret"].append(1.0 if r["label"] == "RETAINED" else 0.0)
        d["words"].append(r["stored_words"])
        d["unres"] += int(r["label"] == "UNRESOLVED")
    out = {}
    for key, d in by.items():
        out[key] = {"retention": statistics.mean(d["ret"]), "n": d["n"],
                    "stored_words": statistics.mean(d["words"]),
                    "unresolved_rate": d["unres"] / d["n"]}
    return out


def adequacy(ret_o1, ret_o7):
    """Prespecified empirical adequacy condition (replaces 'compression is biting')."""
    return {"retention_O1": ret_o1, "retention_O7": ret_o7,
            "gap_pp": 100 * (ret_o7 - ret_o1),
            "in_range": 0.10 <= ret_o1 <= 0.90,
            "below_ceiling_by_10pp": (ret_o7 - ret_o1) >= 0.10,
            "adequate": (0.10 <= ret_o1 <= 0.90) and ((ret_o7 - ret_o1) >= 0.10)}


if __name__ == "__main__":
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows("dev"), man)
    s = summarise(rows)
    o7 = next((v["retention"] for k, v in s.items() if k[0] == "O7"), 1.0)

    print(f"{'op':<10}{'B':>5}{'T':>5}{'slots':>6}{'ret@10':>8}{'words':>8}{'unres':>7}{'adequate':>10}")
    best = None
    for key in sorted(s, key=lambda k: (k[0], k[1], k[2], k[3] or 0)):
        op, B, T, slots = key
        v = s[key]
        ad = adequacy(v["retention"], o7)["adequate"] if op == "O1" else ""
        print(f"{op:<10}{B:>5}{T:>5}{slots or '':>6}{v['retention']:>8.3f}"
              f"{v['stored_words']:>8.0f}{v['unresolved_rate']:>7.2f}{str(ad):>10}")
        if op == "O1" and ad and T == 1.0:
            # T=1.0 is the preregistered production-like default; temperature is a later one-factor
            # diagnostic, not an operating-point knob. Prefer the cell whose retention is closest to
            # 0.5, which gives a slope the most dynamic range.
            score = abs(v["retention"] - 0.5)
            if best is None or score < best[0]:
                best = (score, key, v)

    print(f"\nO7 access ceiling retention@10 = {o7:.3f}")
    if best:
        _, key, v = best
        print(f"SELECTED operating point: op={key[0]} B={key[1]} T={key[2]} "
              f"-> retention@10 {v['retention']:.3f}, stored words {v['stored_words']:.0f}")
        W1 = v["stored_words"]
        # A3: pick the O3 slot count whose realized STORED length is closest to W1
        cands = [(abs(vv["stored_words"] - W1), k[3], vv) for k, vv in s.items() if k[0] == "O3"]
        cands.sort()
        feasible = [c for c in cands if 0.10 <= c[2]["retention"] <= 0.90]
        chosen = (feasible or cands)[0]
        tol_ok = chosen[0] <= 0.10 * W1
        print(f"A3: O3 slots={chosen[1]} -> stored {chosen[2]['stored_words']:.0f} words "
              f"(|diff| {chosen[0]:.0f}, tolerance {0.10*W1:.0f}), retention "
              f"{chosen[2]['retention']:.3f}, within tolerance: {tol_ok}")
        label = ("identical-capacity, prior-blind control" if tol_ok
                 else "prior-blind deletion control (capacity claim dropped)")
        print(f"    O3 is described as: {label}")
        out = {"operating_point": {"op": key[0], "B": key[1], "T": key[2]},
               "W1_stored_words": W1, "retention_O1_k10": v["retention"],
               "retention_O7_k10": o7, "adequacy": adequacy(v["retention"], o7),
               "O3": {"slots": chosen[1], "stored_words": chosen[2]["stored_words"],
                      "retention": chosen[2]["retention"], "within_tolerance": tol_ok,
                      "label": label},
               "grid": {f"{k[0]}|B{k[1]}|T{k[2]}|s{k[3]}": vv for k, vv in s.items()}}
        (RES / "pilot_selection.json").write_text(json.dumps(out, indent=1))
        print("\nwrote results/pilot_selection.json")
    else:
        print("\nNO adequate O1 cell in the dev grid. Under the prespecified rule this is itself the")
        print("result: at this compressor and these budgets, compaction does not remove material")
        print("content. Reported as a scoped boundary result rather than searched past.")
