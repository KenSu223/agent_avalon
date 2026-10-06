"""Publication figures. Every number is read from a file in results/."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from stimuli import ROOT
import analysis as A

RES = ROOT / "results"
FIG = ROOT / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 220, "savefig.bbox": "tight", "axes.grid": True,
                     "grid.alpha": 0.22, "grid.linewidth": 0.4, "legend.frameon": False,
                     "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7})
C = {"O1": "#C2410C", "O2": "#0369A1", "O3": "#6B7280", "O3W": "#9CA3AF", "O4": "#7E22CE",
     "O5": "#047857", "O6": "#B45309", "O6-random": "#D4A574", "O6-low": "#A8A29E",
     "O7": "#111827"}
NAME = {"O1": "ROLL: rewrite own memory", "O2": "COPY-LLM: select verbatim",
        "O3": "COPY-RAND: prior-blind\n(retention-matched)",
        "O3W": "COPY-RAND-W: prior-blind\n(budget-matched)",
        "O4": "SRC: rebuild from sources",
        "O5": "ANCHOR: +Codex rules", "O6": "PIN: high-surprise",
        "O6-random": "PIN: random", "O6-low": "PIN: low-surprise", "O7": "FULL: ceiling"}


def _rows(tag="confirm"):
    man = json.loads((RES / "manifest.json").read_text())
    return A.attach(A.load_rows(tag), man)


def terciles(rows):
    s = sorted(r["surprise"] for r in rows)
    return s[len(s)//3], s[2*len(s)//3]


# ---------------------------------------------------------------- Figure 1: E-SHIFT
def fig1():
    res = json.loads((RES / "eshift_result_confirmatory.json").read_text())
    p = res["eligible_only"]
    per = p["per_family_mean"]
    fams = sorted(per, key=lambda f: per[f])
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.3), width_ratios=[2.3, 1.0])
    vals = [per[f] for f in fams]
    ax[0].bar(range(len(fams)), vals, width=0.72,
              color=["#C2410C" if v > 0 else "#6B7280" for v in vals])
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xticks(range(len(fams)))
    ax[0].set_xticklabels(fams, rotation=90, fontsize=5.5)
    ax[0].set_ylabel("survival(expected) −\nsurvival(surprising)  (pp)")
    ax[0].set_title("a  per family: identical sentence and value,\n"
                    "     only the base-rate frame differs", loc="left", fontsize=7.5)
    m, lo, hi = p["mean"], p["ci95"][0], p["ci95"][1]
    s = p["sesoi"]
    ax[1].axhspan(-s, s, color="#9CA3AF", alpha=0.17, lw=0, label=f"±SESOI ({s:.0f} pp)")
    ax[1].errorbar([0], [m], yerr=[[m-lo], [hi-m]], fmt="o", color="#C2410C", capsize=4, ms=5, lw=1.5)
    c = res.get("frame_control_O3")
    if c:
        ax[1].errorbar([1], [c["mean"]],
                       yerr=[[c["mean"]-c["ci95"][0]], [c["ci95"][1]-c["mean"]]],
                       fmt="s", color="#6B7280", capsize=4, ms=4, lw=1.2)
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["ROLL\n(rewrites)", "COPY-RAND\n(frame control)"],
                                                    fontsize=6.5)
    ax[1].set_xlim(-0.6, 1.6)
    ax[1].set_ylabel("mean paired difference (pp)")
    ax[1].legend(fontsize=6, loc="upper right")
    ax[1].set_title("b  " + p["decision"].replace("_", " ").lower(), loc="left", fontsize=7.5)
    fig.savefig(FIG / "fig1_eshift.pdf"); plt.close(fig)


# ---------------------------------------------------------------- Figure 2: no gradient, big operator effect
def fig2():
    rows = _rows()
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    t1, t2 = terciles(k10)
    ops = ["O7", "O5", "O4", "O1", "O3", "O2"]
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.4))
    for op in ops:
        sub = [r for r in k10 if r["op"] == op]
        if not sub:
            continue
        gs = [[], [], []]
        for r in sub:
            gs[0 if r["surprise"] <= t1 else (1 if r["surprise"] <= t2 else 2)].append(r["retained"])
        xs = [0, 1, 2]
        ys = [100*statistics.mean(g) if g else np.nan for g in gs]
        es = [100*statistics.pstdev(g)/max(1, len(g)**0.5) if g else 0 for g in gs]
        ax[0].errorbar(xs, ys, yerr=es, marker="o", ms=3.5, lw=1.4, capsize=2.5,
                       color=C[op], label=NAME[op])
    ax[0].set_xticks([0, 1, 2]); ax[0].set_xticklabels(["low", "mid", "high"])
    ax[0].set_xlabel("measured surprise tercile")
    ax[0].set_ylabel("retained at $k{=}10$ (%)")
    ax[0].set_ylim(-4, 104)
    ax[0].set_title("a  retention is flat in surprise,\n     but far apart across operators",
                    loc="left", fontsize=7.5)
    ax[0].legend(fontsize=5.6, loc="center left", ncol=1)

    ks = sorted({r["k"] for r in rows})
    for op in ops:
        ys = []
        for k in ks:
            v = [r["retained"] for r in rows
                 if r["op"] == op and r["k"] == k and r["label"] != A.UNRESOLVED]
            ys.append(100*statistics.mean(v) if v else np.nan)
        ax[1].plot(ks, ys, marker="o", ms=2.6, lw=1.4, color=C[op], label=NAME[op])
    ax[1].set_xlabel("compaction steps $k$")
    ax[1].set_ylabel("retained (%)")
    ax[1].set_ylim(-4, 104)
    ax[1].set_title("b  survival over the chain", loc="left", fontsize=7.5)
    fig.savefig(FIG / "fig2_operators.pdf"); plt.close(fig)


# ---------------------------------------------------------------- Figure 3: operator contrasts
def fig3():
    sv = json.loads((RES / "sensitivity.json").read_text())
    d = {"contrasts": {k: v for k, v in sv["contrasts"]["paired"].items()}}
    # reuse the precomputed vs-O1 contrasts, adding the budget-matched control
    oc = json.loads((RES / "operator_contrasts.json").read_text())
    for k, v in oc["contrasts"].items():
        d["contrasts"].setdefault(k, v)
    order = ["O7", "O5", "O4", "O3", "O6-random", "O6", "O6-low", "O2", "O3W"]
    order = [o for o in order if f"{o}_minus_O1" in d["contrasts"]]
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    for i, op in enumerate(order):
        c = d["contrasts"][f"{op}_minus_O1"]
        lo, hi = c["ci95"]
        ax.plot([lo, hi], [i, i], color=C.get(op, "k"), lw=1.6)
        ax.plot([c["point"]], [i], "o", color=C.get(op, "k"), ms=4.5)
    ax.axvline(0, color="k", lw=0.8, ls="--")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([NAME.get(o, o) for o in order], fontsize=6.3)
    ax.set_xlabel("retention at $k{=}10$ relative to ROLL (pp)")
    ax.set_title("each arm removes one mechanism", loc="left", fontsize=7.5)
    fig.savefig(FIG / "fig3_contrasts.pdf"); plt.close(fig)


# ---------------------------------------------------------------- Figure 4: preferences
def fig4():
    mem = [json.loads(l) for l in (RES / "pref_memory.jsonl").read_text().splitlines() if l.strip()]
    beh = [json.loads(l) for l in (RES / "pref_behaviour.jsonl").read_text().splitlines() if l.strip()]
    defr = defaultdict(list)
    for r in beh:
        if r["cond"] == "C":
            defr[(r["family_id"], r["level"])].append(1.0 if r["complied"] else 0.0)
    dev = {k: 1-statistics.mean(v) for k, v in defr.items()}
    ks = sorted({r["k"] for r in mem})
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.3))
    for lab, sel, col in [("matches model default", lambda d: d < 0.5, "#6B7280"),
                          ("differs from default", lambda d: d >= 0.5, "#C2410C")]:
        ys = [100*statistics.mean([1.0 if r["stored"] else 0.0 for r in mem
                                   if r["k"] == k and sel(dev.get((r["family_id"], r["level"]), 0))])
              for k in ks]
        ax[0].plot(ks, ys, marker="o", ms=4, lw=1.6, color=col, label=lab)
    ax[0].set_xlabel("compaction steps $k$"); ax[0].set_ylabel("preference still in memory (%)")
    ax[0].set_ylim(0, 104); ax[0].legend(fontsize=6.3)
    ax[0].set_title("a  non-default preferences survive better", loc="left", fontsize=7.5)

    comp = defaultdict(list)
    for r in beh:
        comp[(r["cond"], r["k"])].append(1.0 if r["complied"] else 0.0)
    A_ = 100*statistics.mean(comp[("A", None)])
    C_ = 100*statistics.mean(comp[("C", None)])
    B = [100*statistics.mean(comp[("B", k)]) for k in ks]
    ax[1].axhline(A_, color="#047857", lw=1.3, ls="--", label=f"A: raw instructions ({A_:.0f}%)")
    ax[1].axhline(C_, color="#9CA3AF", lw=1.3, ls=":", label=f"C: no information ({C_:.0f}%)")
    ax[1].plot(ks, B, marker="o", ms=4, lw=1.6, color="#C2410C", label="B: via memory")
    ax[1].fill_between(ks, B, [A_]*len(ks), color="#C2410C", alpha=0.12)
    ax[1].set_xlabel("compaction steps $k$"); ax[1].set_ylabel("preference followed (%)")
    ax[1].set_ylim(0, 104); ax[1].legend(fontsize=6.3, loc="lower left")
    ax[1].set_title("b  storage loss (shaded) vs execution ceiling", loc="left", fontsize=7.5)
    fig.savefig(FIG / "fig4_preferences.pdf"); plt.close(fig)


# ---------------------------------------------------------------- Figure 5: mitigation
def fig5():
    rows = _rows()
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    t1, t2 = terciles(k10)
    ops = [o for o in ["O1", "O6-low", "O6-random", "O6", "O5", "O4"]
           if any(r["op"] == o for r in k10)]
    lab = {"O1": "no mitigation", "O5": "Codex anchor\nrules", "O6": "pin high-surprise",
           "O6-random": "pin random\n(token-matched)", "O6-low": "pin low-surprise\n(token-matched)",
           "O4": "rewrite from\nsources"}
    fig, ax = plt.subplots(figsize=(4.6, 2.4))
    w = 0.38
    for gi, (nm, sel, col) in enumerate([("low surprise", lambda s: s <= t1, "#9CA3AF"),
                                         ("high surprise", lambda s: s > t2, "#C2410C")]):
        ys, es = [], []
        for op in ops:
            v = [r["retained"] for r in k10 if r["op"] == op and sel(r["surprise"])]
            ys.append(100*statistics.mean(v) if v else 0)
            es.append(100*statistics.pstdev(v)/max(1, len(v)**0.5) if v else 0)
        ax.bar([i+(gi-0.5)*w for i in range(len(ops))], ys, width=w, yerr=es, capsize=2,
               color=col, label=nm)
    ax.set_xticks(range(len(ops)))
    ax.set_xticklabels([lab.get(o, o) for o in ops], fontsize=6, rotation=16, ha="right")
    ax.set_ylabel("retained at $k{=}10$ (%)")
    ax.legend(fontsize=6.5, loc="upper left")
    fig.savefig(FIG / "fig5_mitigation.pdf"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        try:
            f(); print("ok", f.__name__)
        except Exception as e:
            print("FAILED", f.__name__, repr(e)[:200])
