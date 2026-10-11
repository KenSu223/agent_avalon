"""Drive one memory framework through every simulated user history and snapshot its memory at checkpoints.

usage: python run_framework.py <framework> [--model M] [--users N] [--distract D] [--workers W] [--tag T] [--v2] [--checkpoints 0,4,12]
Output: results/snapshots_<framework>[_<tag>].jsonl  (one line per user x checkpoint)
  --v2: step 4 (STEP4_DESIGN.md): expanded item subset S4 and distractor pool v2 (sessions_v2.py); rows carry item_set="v2"
"""
import argparse, json, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework_study/src"))
import sessions as SESS
from frameworks import ADAPTERS
make_users, build_history, load_distractors, ITEMS = SESS.make_users, SESS.build_history, SESS.load_distractors, SESS.ITEMS

CHECKPOINTS = [0, 2, 4, 8, 12]  # number of distractor sessions seen after the last seeding session
ITEM_SET = "v1"


def run_user(fw, model, u, assign, distractors, n_distract, temperature):
    ad = ADAPTERS[fw](model, temperature=temperature)
    hist = build_history(assign, distractors, n_distract=n_distract, seed=u)
    n_seed = sum(1 for s in hist if s["kind"] == "seed")
    snaps, t0 = [], time.time()
    for i, s in enumerate(hist):
        ad.ingest(s["messages"])
        seen = i + 1 - n_seed
        if seen in CHECKPOINTS:
            qctx = {}
            for iid, _ in assign:
                c = ad.context(ITEMS[iid]["question"])
                qctx[iid] = c
            snaps.append({"framework": fw, "model": model, "user": u, "assign": assign, "ckpt": seen, "item_set": ITEM_SET,
                          "dump": ad.dump(), "contexts": qctx, "elapsed": round(time.time() - t0, 1)})
    return snaps


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("framework")
    ap.add_argument("--model", default="qwen.qwen3-235b-a22b-2507-v1:0")
    ap.add_argument("--users", type=int, default=43)
    ap.add_argument("--distract", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--v2", action="store_true")
    ap.add_argument("--checkpoints", default=None, help="comma-separated, e.g. 0,4,12")
    a = ap.parse_args()
    if a.v2:
        import sessions_v2 as S2
        make_users, build_history, load_distractors, ITEMS = S2.make_users, S2.build_history, S2.load_distractors, S2.ITEMS
        ITEM_SET = "v2"
    if a.checkpoints:
        CHECKPOINTS[:] = [int(c) for c in a.checkpoints.split(",")]
    users = make_users(a.users)
    ds = load_distractors()
    out = ROOT / f"framework_study/results/snapshots_{a.framework}{('_' + a.tag) if a.tag else ''}.jsonl"
    done = set()
    if out.exists():
        for l in open(out):
            r = json.loads(l); done.add(r["user"])
    todo = [u for u in range(a.users) if u not in done]
    print(f"{a.framework}: {len(todo)} users to run ({len(done)} already done)", flush=True)
    fails = 0
    with ThreadPoolExecutor(a.workers) as ex, open(out, "a") as f:
        futs = {ex.submit(run_user, a.framework, a.model, u, users[u], ds, a.distract, a.temperature): u for u in todo}
        for k, fu in enumerate(as_completed(futs)):
            u = futs[fu]
            try:
                for s in fu.result():
                    f.write(json.dumps(s) + "\n")
                f.flush()
            except Exception as e:
                fails += 1
                print(f"user {u} FAILED: {e!r}", flush=True)
                traceback.print_exc()
            if (k + 1) % 5 == 0:
                print(f"  {k+1}/{len(todo)} users", flush=True)
    print("done; failures:", fails)
