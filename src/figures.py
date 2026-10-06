"""Publication figures. Every number traces to a file in results/."""
import json, math, statistics, sys
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

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 200, "savefig.bbox": "tight", "axes.grid": True,
                     "grid.alpha": 0.25, "grid.linewidth": 0.4, "legend.frameon": False})
C = {"O1": "#C2410C", "O2": "#0369A1", "O3": "#6B7280", "O4": "#7E22CE",
     "O5": "#047857", "O6": "#B45309", "O7": "#111827"}
NAME = {"O1": "ROLL (rewrite)", "O2": "COPY-LLM (select)", "O3": "COPY-RAND (prior-blind)",
        "O4": "SRC (no self-read)", "O5": "ANCHOR (Codex rules)", "O6": "PIN (ours)",
        "O7": "FULL (ceiling)"}


def terciles(rows):
    s = sorted(r["surprise"] for r in rows)
    if len(s) < 3:
        return None
    return s[len(s) // 3], s[2 * len(s) // 3]


def fig1_eshift(path="fig1_eshift.pdf"):
    res = json.loads((RES / "eshift_result_confirmatory.json").read_text())
    p = res["eligible_only"]
    per = p["per_family_mean"]
    fams = sorted(per, key=lambda f: per[f])
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.5), width_ratios=[2.0, 1.0])
    vals = [per[f] for f in fams]
    ax[0].bar(range(len(fams)), vals,
              color=["#C2410C" if v > 0 else "#6B7280" for v in vals], width=0.72)
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xticks(range(len(fams)))
    ax[0].set_xticklabels(fams, rotation=90, fontsize=5.5)
    ax[0].set_ylabel("retention(expected) − retention(surprising)\n(pp, k=10)")
    ax[0].set_title("a  per family: same sentence, same value,\n    only the base-rate frame differs",
                    loc="left", fontsize=8)
    m, lo, hi = p["mean"], p["ci95"][0], p["ci95"][1]
    ax[1].errorbar([0], [m], yerr=[[m - lo], [hi - m]], fmt="o", color="#C2410C",
                   capsize=4, ms=5, lw=1.4)
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].axhspan(-p["sesoi"], p["sesoi"], color="#9CA3AF", alpha=0.18, lw=0)
    c = res.get("frame_control_O3")
    if c:
        ax[1].errorbar([1], [c["mean"]],
                       yerr=[[c["mean"] - c["ci95"][0]], [c["ci95"][1] - c["mean"]]],
                       fmt="s", color="#6B7280", capsize=4, ms=4, lw=1.2)
    ax[1].set_xticks([0, 1] if c else [0])
    ax[1].set_xticklabels(["ROLL\n(rewrites)", "COPY-RAND\n(frame control)"][: 2 if c else 1],
                          fontsize=7)
    ax[1].set_xlim(-0.6, 1.6 if c else 0.6)
    ax[1].set_ylabel("mean paired difference (pp)")
    ax[1].set_title(f"b  {p['decision'].replace('_',' ').lower()}", loc="left", fontsize=8)
    fig.savefig(FIG / path)
    plt.close(fig)
    return FIG / path


def fig2_doseresponse(rows, path="fig2_dose.pdf"):
    """Retention vs measured surprise, per operator, at the primary endpoint; plus the curve over k."""
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.5))
    ops = [o for o in ["O1", "O2", "O3", "O4", "O5", "O6", "O7"]
           if any(r["op"] == o for r in rows)]
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    t = terciles(k10)
    for op in ops:
        sub = [r for r in k10 if r["op"] == op]
        if not sub or t is None:
            continue
        groups = [[], [], []]
        for r in sub:
            g = 0 if r["surprise"] <= t[0] else (1 if r["surprise"] <= t[1] else 2)
            groups[g].append(r["retained"])
        xs = [statistics.mean([r["surprise"] for r in sub
                               if (0 if r["surprise"] <= t[0] else (1 if r["surprise"] <= t[1] else 2)) == g])
              for g in range(3) if groups[g]]
        ys = [100 * statistics.mean(g) for g in groups if g]
        se = [100 * (statistics.pstdev(g) / max(1, len(g) ** 0.5)) for g in groups if g]
        ax[0].errorbar(xs, ys, yerr=se, marker="o", ms=3.5, lw=1.3, capsize=2,
                       color=C.get(op, "k"), label=NAME.get(op, op))
    ax[0].set_xlabel("measured surprise  (−log prior, within-family centred)")
    ax[0].set_ylabel("retained at k=10 (%)")
    ax[0].set_title("a  dose–response by operator", loc="left", fontsize=8)
    ax[0].legend(fontsize=5.6, ncol=2, loc="lower left")

    ks = sorted({r["k"] for r in rows})
    for op in ops:
        for gi, (lab, sel) in enumerate([("low surprise", lambda s: s <= t[0]),
                                         ("high surprise", lambda s: s > t[1])]):
            if op not in ("O1", "O3"):
                continue
            ys = []
            for k in ks:
                sub = [r["retained"] for r in rows
                       if r["k"] == k and r["op"] == op and r["label"] != A.UNRESOLVED and sel(r["surprise"])]
                ys.append(100 * statistics.mean(sub) if sub else float("nan"))
            ax[1].plot(ks, ys, marker="o", ms=2.8, lw=1.3, color=C.get(op, "k"),
                       ls="-" if gi == 0 else "--",
                       label=f"{op} {lab}")
    ax[1].set_xlabel("compaction steps k")
    ax[1].set_ylabel("retained (%)")
    ax[1].set_title("b  decay by surprise tercile", loc="left", fontsize=8)
    ax[1].legend(fontsize=5.6)
    fig.savefig(FIG / path)
    plt.close(fig)
    return FIG / path


def fig3_direction(dirres, path="fig3_direction.pdf"):
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    ax.hist(dirres["_deltas"], bins=24, color="#C2410C", alpha=0.85)
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(dirres["mean_delta"], color="#111827", lw=1.4, ls="--",
               label=f"mean {dirres['mean_delta']:+.2f}")
    ax.set_xlabel("Δ = log p(replacement) − log p(original)")
    ax.set_ylabel("replacement events")
    ax.set_title(f"{100*dirres['frac_prior_ward']:.0f}% move toward the prior", loc="left", fontsize=8)
    ax.legend(fontsize=6.5)
    fig.savefig(FIG / path)
    plt.close(fig)
    return FIG / path


def fig5_mitigation(rows, path="fig5_mitigation.pdf"):
    """Retention recovered by each memory design, split by surprise tercile."""
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    t = terciles(k10)
    ops = [o for o in ["O1", "O5", "O6-low", "O6-random", "O6"] if any(r["op"] == o for r in k10)]
    labels = {"O1": "no mitigation", "O5": "Codex anchor rules", "O6": "surprise pinning (ours)",
              "O6-random": "random pinning\n(token-matched)", "O6-low": "low-surprise pinning\n(token-matched)"}
    fig, ax = plt.subplots(figsize=(4.4, 2.5))
    w = 0.38
    for gi, (lab, sel, col) in enumerate([("low surprise", lambda s: s <= t[0], "#9CA3AF"),
                                          ("high surprise", lambda s: s > t[1], "#C2410C")]):
        ys, es = [], []
        for op in ops:
            sub = [r["retained"] for r in k10 if r["op"] == op and sel(r["surprise"])]
            ys.append(100 * statistics.mean(sub) if sub else 0.0)
            es.append(100 * statistics.pstdev(sub) / max(1, len(sub) ** 0.5) if sub else 0.0)
        ax.bar([i + (gi - 0.5) * w for i in range(len(ops))], ys, width=w, yerr=es,
               capsize=2, color=col, label=lab)
    ax.set_xticks(range(len(ops)))
    ax.set_xticklabels([labels.get(o, o) for o in ops], fontsize=6, rotation=18, ha="right")
    ax.set_ylabel("retained at k=10 (%)")
    ax.legend(fontsize=6.5)
    fig.savefig(FIG / path)
    plt.close(fig)
    return FIG / path
