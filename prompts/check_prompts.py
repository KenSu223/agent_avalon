"""Reproducibility check for the prompt archive: rebuild it into a temp dir and compare byte-for-byte with prompts/.
Fails (exit 1) if any template / library file differs, if a committed file is missing from the rebuild (or vice
versa), or if any exemplar is no longer verified against the response cache. Run before every commit that touches
code with prompts, and before building the paper.   python prompts/check_prompts.py   (fw-env python)
"""
import filecmp, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "prompts"
PY = sys.executable


def main():
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, PROMPTS_OUT=td, LLM_REQUEST_LOG_DIR=os.path.join(td, "_reqlog"))
        for s in ("capture.py", "export_library.py"):
            r = subprocess.run([PY, str(P / s)], env=env, capture_output=True, text=True)
            if r.returncode:
                print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
        bad = []
        for sub in ("templates", "exemplars", "library"):
            a, b = P / sub, Path(td) / sub
            ra = {str(p.relative_to(a)) for p in a.rglob("*") if p.is_file()}
            rb = {str(p.relative_to(b)) for p in b.rglob("*") if p.is_file()}
            bad += [f"{sub}/{x}: missing in rebuild" for x in sorted(ra - rb)] + [f"{sub}/{x}: not committed" for x in sorted(rb - ra)]
            bad += [f"{sub}/{x}: differs" for x in sorted(ra & rb) if not filecmp.cmp(a / x, b / x, shallow=False)]
        reg = json.load(open(Path(td) / "registry.json"))
        bad += [f"exemplar {r['id']} not verified in cache" for r in reg if r["kind"] == "exemplar" and not r["verified"]]
        bad += [f"capture error {r['id']}: {r['error']}" for r in reg if r["kind"] == "error"]
    if bad:
        print("PROMPT ARCHIVE CHECK FAILED"); print("\n".join(bad[:200])); sys.exit(1)
    print("prompt archive OK: templates, exemplars (all cache-verified) and library files match the code")


if __name__ == "__main__":
    main()
