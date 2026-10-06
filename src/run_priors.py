"""Run P1 (pairwise Bradley-Terry), P2 (generative), P3 (local logprobs) and write priors.json."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat, estimate_cost
import priors as P
from stimuli import load_families, ROOT

MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
RES = ROOT / "results"


def main():
    fams = load_families()
    reqs, meta = P.p1_requests(fams, MODEL)
    est = estimate_cost(MODEL, len(reqs), 130, 3)
    print(f"P1 pairwise: {len(reqs)} calls, est ${est:.3f}", flush=True)
    r1 = batch_chat(reqs, workers=16, desc="P1")
    tally = P.p1_collect(r1, meta)

    bt = {}
    for f in fams:
        fid = f["family_id"]
        levels = [l["level"] for l in f["levels"]]
        if fid not in tally:
            continue
        bt[fid] = {h: P.bradley_terry(tally[fid][h], levels) for h in ("A", "B", "ALL")}

    reqs2, meta2 = P.p2_requests(fams, MODEL, n=30)
    print(f"P2 generative: {len(reqs2)} calls, est ${estimate_cost(MODEL, len(reqs2), 95, 20):.3f}", flush=True)
    r2 = batch_chat(reqs2, workers=16, desc="P2")
    p2 = P.p2_collect(r2, meta2, fams)

    print("P3 local logprobs (free)...", flush=True)
    p3 = P.p3_logprobs(fams)

    out = {"model": MODEL, "n_worlds": P.N_WORLDS, "n_samples": P.N_SAMPLES,
           "bt": {k: {h: {str(l): v for l, v in d.items()} for h, d in v.items()} for k, v in bt.items()},
           "p2": {k: {str(l): v for l, v in d.items()} for k, d in p2.items()},
           "p3": {k: {str(l): v for l, v in d.items()} for k, d in p3.items()},
           "pair_counts": {k: {h: {f"{a}>{b}": c for (a, b), c in d.items()} for h, d in v.items()}
                           for k, v in tally.items()}}
    RES.mkdir(exist_ok=True)
    (RES / "priors.json").write_text(json.dumps(out, indent=1))
    cost = sum(x.get("cost_usd", 0) for x in r1 + r2 if x and not x.get("error"))
    print(f"priors written. families with BT: {len(bt)}. hosted cost this run ${cost:.3f}", flush=True)


if __name__ == "__main__":
    main()
