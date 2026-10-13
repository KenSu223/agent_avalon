"""Generate the paper's tables (paper_v2/tab_*.tex) from committed result files (PLAN rigor standard 3).
Run: python paper_v2/make_tables.py"""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
P = Path(__file__).parent
M = R / "method/results"
F = R / "framework_study/results"
NAMES = {"raw_rag": "Raw RAG", "mem0": "Mem0 (2.2.1)", "mem0_v1": "Mem0 (1.0.11)", "langmem": "LangMem", "llamaindex_facts_default": "LlamaIndex facts",
         "llamaindex_facts": "LlamaIndex facts", "gemini_cli": "Gemini CLI", "neutral_roll": "Neutral rewrite", "openhands": "OpenHands",
         "langchain_summary": "LangChain summ.", "aider": "Aider", "anthropic_api": "Anthropic API", "codex": "Codex", "nemori": "Nemori",
         "raw_history": "Full history"}


def tab_protocols():
    pr = json.load(open(M / "protocol_analysis.json"))
    L, Q = pr["locomo"], pr["mab_ruler"]
    rows = []
    for s in sorted(L["systems"], key=lambda s: -L["acc"]["A"][L["systems"].index(s)]):
        i = L["systems"].index(s)
        cells = [f"{L['acc']['A'][i]:.2f}", f"{L['acc']['F'][i]:.2f}", f"{L['cpr']['A'][i]:.2f}", f"{L['cpr']['F'][i]:.2f}", f"{L['abst']['A'][i]:.2f}"]
        if s in Q["systems"]:
            j = Q["systems"].index(s)
            cells += [f"{Q['acc']['A'][j]:.2f}", f"{Q['acc']['F'][j]:.2f}", f"{Q['cpr']['A'][j]:.2f}", f"{Q['cpr']['F'][j]:.2f}", f"{Q['abst']['A'][j]:.2f}"]
        else:
            cells += ["--"] * 5
        rows.append(f"{NAMES.get(s, s)} & " + " & ".join(cells) + r" \\")
    tex = r"""\begin{table*}[t]
\centering\small
\begin{tabular}{l ccccc ccccc}
\toprule
& \multicolumn{5}{c}{LoCoMo (cat.\ 1--4, $n{=}1540$)} & \multicolumn{5}{c}{MemoryAgentBench RULER-QA1 ($n{=}100$)} \\
\cmidrule(lr){2-6}\cmidrule(lr){7-11}
System & Acc$_A$ & Acc$_F$ & \cpr{}$_A$ & \cpr{}$_F$ & Abst$_A$ & Acc$_A$ & Acc$_F$ & \cpr{}$_A$ & \cpr{}$_F$ & Abst$_A$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\caption{Twelve memory systems re-scored with the same reader (Qwen3-235B) and judge. Acc$_A$/Acc$_F$: accuracy under the native
and the forced answer protocol; \cpr{}$_A$/\cpr{}$_F$: counter-prior accuracy (accuracy on prior-resistant items) under each protocol, $\pi_F$ being the primary score; Abst$_A$: abstention rate on answerable
items under the native protocol (LLM-classified). LangMem fails on MemoryAgentBench documents (see \S\ref{sec:audit}).}
\label{tab:protocols}
\end{table*}
"""
    (P / "tab_protocols.tex").write_text(tex)


def tab_step4():
    s4 = json.load(open(F / "step4_analysis.json"))
    q, l = s4["s4qwen"]["systems"], s4["s4llama"]["systems"]
    order = ["raw_history", "nemori", "mem0_v1", "mem0", "llamaindex_facts", "neutral_roll", "codex", "anthropic_api", "aider"]
    rows = []
    for s in order:
        cells = []
        for fam in (q, l):
            o = fam[s]
            cells += [f"{o['drop']:.2f}", f"{o['dR']:+.2f}", f"{o['dF']:+.3f}", f"{o['dK']:+.2f}"]
        rows.append(f"{NAMES.get(s, s)} & " + " & ".join(cells) + r" \\")
    tex = r"""\begin{table*}[t]
\centering\small
\begin{tabular}{l cccc cccc}
\toprule
& \multicolumn{4}{c}{Qwen3-235B as compactor and reader} & \multicolumn{4}{c}{Llama-3.3-70B as compactor and reader} \\
\cmidrule(lr){2-5}\cmidrule(lr){6-9}
System & Drop & $\Delta R$ & $\Delta F$ & $\Delta K$ & Drop & $\Delta R$ & $\Delta F$ & $\Delta K$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\caption{Controlled counter-schema probes (432 minimal pairs, 192 simulated users, after 12 distractor sessions). Drop: share of
items deleted from memory; $\Delta R = R^C - R^I$ (retention gap); $\Delta F = F^I - F^C$ (rewriting toward the schema);
$\Delta K = K^C - K^I$ (belief gap: how much more often the agent keeps the congruent than the incongruent version).
User-level bootstrap CIs are in the supplementary results.}
\label{tab:step4}
\end{table*}
"""
    (P / "tab_step4.tex").write_text(tex)


tab_protocols(); tab_step4()
print("tables written")
