"""Generate the LaTeX tables from result files."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT
RES = ROOT / "results"
SEC = ROOT / "paper" / "sec"


def robust():
    d = json.loads((RES / "diag_result.json").read_text())
    rows = []
    spec = [("confirm", "Qwen3-235B (primary)", "1.0", ["O1", "O4", "O5", "O3"]),
            ("diag_temp", "Qwen3-235B", "0.0", ["O1"]),
            ("diag_llama", "Llama-3.3-70B", "1.0", ["O1", "O4", "O5"]),
            ("diag_local", "Qwen3-8B (local)", "1.0", ["O1", "O4", "O5"])]
    for tag, name, T, ops in spec:
        r = d.get(tag)
        if not r:
            continue
        for op in ops:
            key = f"{op}@T{T}"
            v = r["by_op"].get(key)
            if not v:
                continue
            ci = v["slope_ci95"]
            rows.append((name, T, op, v["retention"], v["slope_pp_per_logodds"],
                         ci, v["gap_low_minus_high_pp"], v["n"]))
    lines = [r"\begin{table}[t]", r"\centering\small",
             r"\begin{tabular}{llcrrc}", r"\toprule",
             r"model & $T$ & op. & ret.\% & slope & 95\% CI \\", r"\midrule"]
    last = None
    for name, T, op, ret, sl, ci, gap, n in rows:
        nm = name if name != last else ""
        last = name
        lines.append(f"{nm} & {T} & \\textsc{{{op.lower()}}} & {ret:.1f} & {sl:+.2f} & "
                     f"[{ci[0]:+.1f}, {ci[1]:+.1f}] \\\\")
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\caption{\textbf{The null replicates.} Retention at $k{=}10$ and the slope of "
              r"retention on measured surprise (percentage points per log-odds), with two-way "
              r"crossed cluster bootstrap intervals. Every slope interval contains zero. "
              r"\textsc{o1} rewrites its own memory, \textsc{o4} rewrites from the raw sessions, "
              r"\textsc{o5} adds the Codex anti-drift rules, \textsc{o3} is the prior-blind control "
              r"(which makes no model calls and is therefore reported once). The hosted proxy caps "
              r"temperature at $1.0$, so $T>1$ could not be tested.}",
              r"\label{tab:robust}", r"\end{table}"]
    (SEC / "robust_table.tex").write_text("\n".join(lines) + "\n")
    return len(rows)


def coder():
    d = json.loads((RES / "coder_metamorphic.json").read_text())
    pl = d["per_level"]
    lines = [r"\begin{table}[t]", r"\centering\small", r"\begin{tabular}{crrr}", r"\toprule",
             r"level & variants & recognised & decoys rejected \\", r"\midrule"]
    for lvl in sorted(pl, key=int):
        v = pl[lvl]
        lines.append(f"{lvl} & {v['var_n']} & {v['var_strict']/v['var_n']:.3f} & "
                     f"{v['decoy_ok']/v['decoy_n']:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\caption{\textbf{The coder does not favour common values.} Strict pattern "
              r"recognition of meaning-preserving format variants, and rejection of negation, "
              r"historical-value and incidental-number decoys, by designed level. Every "
              r"unrecognised variant is routed to the blind judges rather than mis-coded.}",
              r"\label{tab:coder}", r"\end{table}"]
    (SEC / "coder_table.tex").write_text("\n".join(lines) + "\n")


def judges():
    rows = []
    for tag, lab in (("confirm", "main chains"), ("eshift", "\\textsc{e-shift}"),
                     ("dev", "development pilot")):
        p = RES / f"coding_stats_{tag}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        rows.append((lab, d["n_cases"], d["n_judged"], d["cohens_kappa"],
                     d["label_distribution"]))
    lines = [r"\begin{table}[t]", r"\centering\small", r"\begin{tabular}{lrrrrr}", r"\toprule",
             r"set & cases & judged & $\kappa$ & \textsc{ret} & \textsc{chg} \\", r"\midrule"]
    for lab, n, nj, k, dist in rows:
        lines.append(f"{lab} & {n:,} & {nj:,} & {k:.3f} & {dist.get('RETAINED',0):,} & "
                     f"{dist.get('CHANGED',0)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\caption{\textbf{Coding reliability, and how rare replacement is.} Agreement "
              r"between two blind judges from different model families. \textsc{chg} counts items "
              r"changed to a different value; across all three sets it is a rounding error.}",
              r"\label{tab:judges}", r"\end{table}"]
    (SEC / "judge_table.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    n = robust(); coder(); judges()
    print(f"wrote robust_table ({n} rows), coder_table, judge_table")
