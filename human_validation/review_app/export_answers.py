"""Export pair-review answers from D1 and decode them from Version A/B to C/I with key.json.

  python export_answers.py --local     # the wrangler dev database
  python export_answers.py --remote    # the deployed database (after `wrangler login`)

Writes human_validation/results/pair_review_<local|remote>.jsonl (one row per reviewer x item, decoded) and
pair_review_<local|remote>_state.json (training results and submission times). Raw A/B payloads are kept in each row.
"""
import argparse, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"
WRANGLER = ["npx", "--yes", "wrangler@4.149.0"]


def query(sql, where):
    r = subprocess.run(WRANGLER + ["d1", "execute", "pair-review", f"--{where}", "--json", "--command", sql],
                       cwd=HERE, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)[0]["results"]


def decode(p, a):
    """A/B answers -> C/I answers. a: the key entry for this assignment."""
    va, vb = a["ab_order"][0], a["ab_order"][1]           # which version (C or I) was shown as A and as B
    to = {"A": va, "B": vb}
    side = lambda x: {"A": va, "B": vb, "both": "both", "neither": "neither", "none": "none"}.get(x, x)
    row = {
        "natural": {to[k]: p["q1_natural"][k] for k in "AB"},
        "minimal": p["q2_minimal"], "minimal_note": p["q2_note"],
        "expected": side(p["q3_expected"]),               # C / I / both / neither
        "answer": {to[k]: p["q4_answer"][k] for k in "AB"},
        "plausible": {to[k]: p["q5_plausible"][k] for k in "AB"},
        "cue": side(p["q6_cue"]),                         # none / C / I / both
        "comment": p["q7_comment"], "flagged": p["flagged"], "flag_reason": p["flag_reason"],
    }
    row["answer_correct"] = {v: row["answer"][v] == a["answers"][v] for v in ("C", "I")}
    return row


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--local", action="store_true")
    g.add_argument("--remote", action="store_true")
    where = "local" if ap.parse_args().local else "remote"
    key = json.load(open(HERE / "key.json"))
    rows = query("SELECT * FROM answers ORDER BY reviewer, uid", where)
    state = query("SELECT * FROM reviewer_state ORDER BY reviewer", where)
    OUT.mkdir(exist_ok=True)
    n_unknown = 0
    with open(OUT / f"pair_review_{where}.jsonl", "w") as f:
        for r in rows:
            a = key["assignments"].get(r["uid"])
            if a is None:
                n_unknown += 1
                continue
            p = json.loads(r["payload"])
            f.write(json.dumps({"reviewer": r["reviewer"], "item_id": a["item_id"], "type": a["type"],
                                "catch": a["catch"], "ab_order": a["ab_order"], "options_shown": a["options_shown"],
                                "complete": bool(r["complete"]), "seconds": r["seconds"],
                                "app_version": r["app_version"], "guideline_version": r["guideline_version"],
                                "updated_at": r["updated_at"], **decode(p, a), "raw": p}, ensure_ascii=False) + "\n")
    for s in state:
        s["training_result"] = json.loads(s["training_result"]) if s["training_result"] else None
    json.dump(state, open(OUT / f"pair_review_{where}_state.json", "w"), indent=1)
    print(f"{len(rows) - n_unknown} answers -> {OUT / f'pair_review_{where}.jsonl'}"
          + (f" ({n_unknown} rows with uids not in key.json were skipped)" if n_unknown else ""))


if __name__ == "__main__":
    main()
