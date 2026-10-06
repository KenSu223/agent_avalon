"""Expand numbers.tex macros into the section sources, for review and for proofreading."""
import re, sys
from pathlib import Path
P = Path("paper")
macros = {}
for m in re.finditer(r"\\(?:new|provide)command\{\\([A-Za-z]+)\}\{(.*)\}\s*$",
                     (P/"numbers.tex").read_text(), re.M):
    macros[m.group(1)] = m.group(2)
order = ["abstract", "intro", "background", "instrument", "results", "related",
         "discussion", "conclusion", "limitations", "appendix"]
out = []
for name in order:
    f = P/"sec"/f"{name}.tex"
    if not f.exists():
        continue
    t = f.read_text()
    for _ in range(3):
        t = re.sub(r"\\([A-Za-z]+)\{\}", lambda m: macros.get(m.group(1), m.group(0)), t)
    if name == "abstract":
        t = "\\section*{Abstract}\n" + t
    out.append(t)
txt = "\n\n".join(out)
# inline the generated tables
for tab in ("robust_table", "coder_table", "judge_table"):
    f = P/"sec"/f"{tab}.tex"
    if f.exists():
        txt += "\n\n" + f.read_text()
Path(sys.argv[1] if len(sys.argv) > 1 else "paper/RESOLVED.txt").write_text(txt)
print(len(txt), "chars;", len(macros), "macros;",
      len(set(re.findall(r"\\([A-Z][A-Za-z]+)\{\}", txt))), "unresolved")
