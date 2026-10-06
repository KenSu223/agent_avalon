"""Drive compaction trajectories and store every memory snapshot.

A trajectory is (chain, seed, operator, config). Step 0 compacts the seeding session into M_0;
steps 1..K compact a distractor session into M_k. Snapshots at every checkpoint are written to
results/chains/<run_id>.jsonl so that coding and analysis never need to re-run a model.
"""
import json, random, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import operators as OPS
from stimuli import load_families, render, world, ROOT
from sessions import seeding_session, seeding_sentences, distractor_sentences

RESULTS = ROOT / "results"
CHECKPOINTS = [0, 1, 2, 3, 5, 7, 10, 15, 20]
_lock = threading.Lock()


def load_distractors():
    d = json.loads((RESULTS / "distractors.json").read_text())
    return [s for s in d["sessions"] if s.get("transcript")]


def run_trajectory(chain, families, distractors, cfg, surprise_local=None, frame=None):
    """One compaction chain. Returns a record with a snapshot at every checkpoint."""
    w = world(cfg["chain_idx"], cfg["seed_idx"])
    fam = {f["family_id"]: f for f in families}
    seed_txt, _ = seeding_session(chain, families, w, frame)
    seed_sents = seeding_sentences(chain, families, w, frame)
    rng = random.Random(cfg["rand_seed"])

    # distractor order is rotated symmetrically by seed
    order = list(range(len(distractors)))
    n_s = max(1, cfg["n_seeds"])
    rot = ((cfg["seed_idx"] % n_s) * len(order)) // n_s   # even spacing, never collapses to 0
    order = order[rot:] + order[:rot]

    pins = None
    if cfg["op"] == "O6" or cfg["op"].startswith("O6-"):
        items = [{"item_id": it["item_id"],
                  "sentence": render(next(l for l in fam[it["family_id"]]["levels"]
                                          if l["level"] == it["level"])["sentence"], w)}
                 for it in chain["items"]]
        mode = cfg["op"].split("-")[1] if "-" in cfg["op"] else None
        if mode in ("random", "low"):
            pins = OPS.choose_pins_control(items, surprise_local or {}, cfg["B"], mode, rng)
        else:
            pins = OPS.choose_pins(items, surprise_local or {}, cfg["B"])

    state = {"text": "", "sentences": []}
    snaps, transcripts, cost, truncs, retries_total = [], [], 0.0, 0, 0
    for k in range(0, cfg["K"] + 1):
        if k == 0:
            transcript, new_sents = seed_txt, seed_sents
        else:
            d = distractors[order[(k - 1) % len(order)]]
            transcript = render(d["transcript"], w)
            new_sents = distractor_sentences(transcript, w)
        transcripts.append(transcript)

        op = cfg["op"]
        c = dict(cfg)
        c["sample_idx"] = cfg["rand_seed"] * 1000 + k
        if op == "O1":
            out = OPS.op_roll(state, transcript, c)
        elif op == "O2":
            out = OPS.op_copy_llm(state, new_sents, c)
        elif op == "O3":
            out = OPS.op_copy_rand(state, new_sents, c, rng)
        elif op == "O3W":
            out = OPS.op_copy_rand_w(state, new_sents, c, rng)
        elif op == "O4":
            out = OPS.op_src(state, transcripts, c)
        elif op == "O5":
            out = OPS.op_roll(state, transcript, c, anchor=True)
        elif op.startswith("O6"):
            out = OPS.op_roll(state, transcript, c, pinned=pins)
        elif op == "O7":
            out = OPS.op_full(state, new_sents, c)
        else:
            raise ValueError(op)
        state = {"text": out["text"], "sentences": out["sentences"]}
        cost += out["cost"]
        truncs += int(out["hard_trimmed"])
        retries_total += out.get("retries", 0)
        if k in CHECKPOINTS:
            # `words` is the length of the STATE THAT IS CARRIED FORWARD, which is what capacity
            # matching must use; over-generation is recorded separately as a protocol diagnostic.
            snaps.append({"k": k, "notes": out["text"], "words": out["stored_words"],
                          "n_lines": out["n_lines"], "retries": out.get("retries", 0),
                          "hard_trimmed": out["hard_trimmed"],
                          "n_picked": out.get("n_picked"), "pool_size": out.get("pool_size")})
    return {"run_id": cfg["run_id"], "chain_id": chain["chain_id"], "op": cfg["op"],
            "model": cfg["model"], "T": cfg["T"], "B": cfg["B"], "slots": cfg.get("slots"),
            "seed_idx": cfg["seed_idx"], "world": w, "frame": frame,
            "items": [{"item_id": i["item_id"], "family_id": i["family_id"], "level": i["level"],
                       "kind": i["kind"]} for i in chain["items"]],
            "snapshots": snaps, "cost_usd": cost, "n_hard_trimmed": truncs,
            "n_budget_retries": retries_total, "pins": pins}


def run_many(jobs, out_path, workers=8, desc=""):
    """jobs: list of dicts with keys chain, families, distractors, cfg, surprise_local, frame."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done_ids = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["run_id"])
    todo = [j for j in jobs if j["cfg"]["run_id"] not in done_ids]
    print(f"[{desc}] {len(todo)} trajectories to run ({len(done_ids)} already done)", flush=True)
    t0, n, total_cost = time.time(), 0, 0.0
    with open(out_path, "a") as fh, ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(run_trajectory, j["chain"], j["families"], j["distractors"],
                          j["cfg"], j.get("surprise_local"), j.get("frame")): j for j in todo}
        for f in as_completed(futs):
            try:
                rec = f.result()
            except Exception as e:
                print(f"  FAILED {futs[f]['cfg']['run_id']}: {e!r}", flush=True)
                continue
            with _lock:
                fh.write(json.dumps(rec) + "\n"); fh.flush()
            n += 1; total_cost += rec["cost_usd"]
            if n % max(1, len(todo) // 10) == 0:
                print(f"  [{desc}] {n}/{len(todo)}  {time.time()-t0:.0f}s  ${total_cost:.3f}", flush=True)
    print(f"[{desc}] done: {n} trajectories, ${total_cost:.3f}, {time.time()-t0:.0f}s", flush=True)
    return total_cost
