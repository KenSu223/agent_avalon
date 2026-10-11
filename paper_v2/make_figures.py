"""Generate the paper's pgfplots figures (fig_*.tex) from committed result files, so that every plotted point is traceable
(PLAN rigor standard 3). Run: python paper_v2/make_figures.py   (system python; json only). Requires
framework_study/results/step4_analysis.json with P4_7.per_cell (analyse_step4.py, 2026-10-11 or later)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
F = R / "framework_study/results"
P = Path(__file__).resolve().parent
FAMS = (("s4qwen", "Qwen3-235B", "famA", "*"), ("s4llama", "Llama-3.3-70B", "famB", "square*"))
HEAD = r"""\definecolor{famA}{RGB}{0,114,178}
\definecolor{famB}{RGB}{213,94,0}
"""


def readtime():
    """Belief gap and retention gap against deletion rate, one point per system and backbone family."""
    s4 = json.load(open(F / "step4_analysis.json"))
    plots = []
    for contrast, ci, filled in (("dK", "dK_ci", True), ("dR", "dR_ci", False)):
        for tag, name, col, mark in FAMS:
            pts = []
            for s, o in sorted(s4[tag]["systems"].items()):
                lo, hi = o[ci]
                pts.append(f"({o['drop']:.4f},{o[contrast]:.4f}) += (0,{hi - o[contrast]:.4f}) -= (0,{o[contrast] - lo:.4f})")
            fill = f"fill={col}" if filled else "fill=white"
            sym = r"\Delta K" if contrast == "dK" else r"\Delta R"
            plots.append(rf"""\addplot[only marks, mark={mark}, mark size=1.6pt, draw={col}, mark options={{{fill}}},
  error bars/.cd, y dir=both, y explicit, error bar style={{{col}, line width=0.4pt}}]
  coordinates {{{' '.join(pts)}}};
\addlegendentry{{${sym}$, {name}}}""")
    tex = HEAD + r"""\begin{tikzpicture}
\begin{axis}[width=\columnwidth, height=5.2cm, xmin=-0.04, xmax=1.04, ymin=-0.1, ymax=1.04,
  xlabel={Share of items deleted from memory (Drop)}, ylabel={Gap (congruent $-$ incongruent)},
  label style={font=\small}, tick label style={font=\footnotesize},
  legend style={font=\scriptsize, at={(0.02,0.98)}, anchor=north west, draw=none, fill=none, row sep=-2pt},
  legend cell align=left, grid=major, grid style={gray!20}]
\addplot[dashed, gray, domain=0:1, forget plot] {x};
\addplot[gray, domain=0:1, forget plot] {0};
""" + "\n".join(plots) + r"""
\end{axis}
\end{tikzpicture}
"""
    (P / "fig_readtime.tex").write_text(tex)


def pcs_vs_retention():
    """Raw accuracy and PCS from the agents' answers against judge-coded retention, one point per system x checkpoint."""
    s4 = json.load(open(F / "step4_analysis.json"))
    acc, pcs = [], []
    for tag, _, _, _ in FAMS:
        for c in s4[tag]["P4_7"]["per_cell"]:
            acc.append(f"({c['R']:.4f},{c['acc']:.4f})")
            pcs.append(f"({c['R']:.4f},{c['pcs']:.4f})")
    tex = HEAD + r"""\begin{tikzpicture}
\begin{axis}[width=\columnwidth, height=5.2cm, xmin=-0.04, xmax=1.04, ymin=-0.1, ymax=1.04,
  xlabel={Judge-coded retention of the memory}, ylabel={Score from the agent's answers},
  label style={font=\small}, tick label style={font=\footnotesize},
  legend style={font=\scriptsize, at={(0.98,0.02)}, anchor=south east, draw=none, fill=white, fill opacity=0.8,
  text opacity=1}, legend cell align=left, grid=major, grid style={gray!20}]
\addplot[dashed, gray, domain=0:1, forget plot] {x};
\addplot[only marks, mark=o, mark size=1.8pt, draw=gray!70!black] coordinates {""" + " ".join(acc) + r"""};
\addlegendentry{Raw accuracy}
\addplot[only marks, mark=triangle*, mark size=2pt, draw=famA, fill=famA] coordinates {""" + " ".join(pcs) + r"""};
\addlegendentry{\textsc{PCS}}
\end{axis}
\end{tikzpicture}
"""
    (P / "fig_pcs.tex").write_text(tex)


def abstention():
    """Pre-registered H1 (METHOD 10.2): accuracy gain from forcing an answer against native-protocol abstention, per system."""
    pr = json.load(open(R / "method/results/protocol_analysis.json"))
    plots = []
    for key, name, col, mark in (("locomo", "LoCoMo", "famA", "*"), ("mab_ruler", "RULER-QA1", "famB", "square*"),
                                 ("mab_ruler_qa2", "RULER-QA2", "famC", "triangle*")):
        b = pr[key]
        pts = " ".join(f"({a:.4f},{f - n:.4f})" for a, f, n in zip(b["abst"]["A"], b["acc"]["F"], b["acc"]["A"]))
        plots.append(rf"""\addplot[only marks, mark={mark}, mark size=1.7pt, draw={col}, fill={col}] coordinates {{{pts}}};
\addlegendentry{{{name} ($\rho={b['H1']['rho']:.2f}$)}}""")
    tex = HEAD + r"""\definecolor{famC}{RGB}{0,158,115}
\begin{tikzpicture}
\begin{axis}[width=\columnwidth, height=5.2cm, xmin=0, xmax=0.85, ymin=-0.06, ymax=0.26,
  xlabel={Abstention rate on answerable items ($\pi_A$)}, ylabel={Accuracy gain, $\pi_F$ $-$ $\pi_A$},
  label style={font=\small}, tick label style={font=\footnotesize},
  legend style={font=\scriptsize, at={(0.02,0.98)}, anchor=north west, draw=none, fill=none},
  legend cell align=left, grid=major, grid style={gray!20}]
\addplot[gray, domain=0:0.85, forget plot] {0};
""" + "\n".join(plots) + r"""
\end{axis}
\end{tikzpicture}
"""
    (P / "fig_abstention.tex").write_text(tex)


readtime(); pcs_vs_retention(); abstention()
