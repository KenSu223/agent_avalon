"""Option-order check of the step-4 belief probe (framework_study/ORDER_CHECK_DESIGN.md).

probe.py always lists options[0] (= the C answer) first, and 427/432 S4 questions also name C first. This script re-asks
the belief probe on the saved step-4 contexts (snapshots_<fw>_s4qwen / s4llama, including the retrieved contexts of Mem0,
mem0_v1 and Nemori) with the order reversed. Only the user turn changes; system prompt, context, model and decoding are
those of probe.py.

Arms
  O  original user turn (rebuilt only to check, offline, that it is byte-identical to what probe.py sent)
  R  I-first question wording (stimuli/questions_ifirst.json) + options line "I / C"      <- primary
  L  original (C-first) wording + options line "I / C"                                 <- wording/line decomposition
Tiers (rows of probed_<fw>_<tag>.jsonl; state = original two-judge code)
  1  ckpt 12, DROPPED non-neutral rows + every neutral row
  2  ckpt 12, all other rows      (raw_history and nemori: users < SUB only)
  3  ckpt 4, all rows             (raw_history and nemori: users < SUB only)

usage: python probe_order.py --arms R --tiers 1 2 3 [--tags s4qwen s4llama] [--dry-run] [--check-cache] [--max-usd 30]
Output: results/order_<arm>_<tag>.jsonl (one row per probed item; merged with what is already there)
"""
import argparse, collections, datetime, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src"))
from validate import parse
from probe import QA_SYSTEM
import sessions_v2 as S2

RES = ROOT / "framework_study/results"
FW = ["aider", "anthropic_api", "codex", "llamaindex_facts", "mem0", "mem0_v1", "nemori", "neutral_roll", "raw_history"]
MODELS = {"s4qwen": "qwen.qwen3-235b-a22b-2507-v1:0", "s4llama": "meta.llama3-3-70b-instruct-v1:0"}
BIG, SUB = {"raw_history", "nemori"}, 48
IFIRST = json.load(open(ROOT / "framework_study/stimuli/questions_ifirst.json"))
PRICE = {"qwen.qwen3-235b-a22b-2507-v1:0": (0.22, 0.88), "meta.llama3-3-70b-instruct-v1:0": (0.72, 0.72)}  # CLAUDE.md table


def user_turn(x, arm):
    a, b = x["options"]                      # a = C answer, b = I answer (all 504 items)
    q = IFIRST[x["id"]]["question_ifirst"] if arm == "R" else x["question"]
    first, second = (a, b) if arm == "O" else (b, a)
    return f"{q}\nAnswer with exactly one of these options and nothing else: {first} / {second}"


def request(model, ctx, x, arm):
    return dict(model=model, messages=[{"role": "system", "content": QA_SYSTEM.format(ctx=ctx)},
                                       {"role": "user", "content": user_turn(x, arm)}], temperature=0.0, max_tokens=12)


def tier(r, item):
    if r["ckpt"] == 12:
        if item["type"] == "neutral" or r["state"] == "DROPPED":
            return 1
        return 2 if (r["framework"] not in BIG or r["user"] < SUB) else None
    if r["ckpt"] == 4:
        return 3 if (r["framework"] not in BIG or r["user"] < SUB) else None
    return None


def rows_for(tag, tiers):
    """Yield (probed row, context) for the selected tiers."""
    for fw in FW:
        probed = {(r["user"], r["ckpt"], r["item"]): r for r in map(json.loads, open(RES / f"probed_{fw}_{tag}.jsonl"))}
        for s in map(json.loads, open(RES / f"snapshots_{fw}_{tag}.jsonl")):
            for iid, v in s["assign"]:
                r = probed.get((s["user"], s["ckpt"], iid))
                if r is None:
                    continue
                t = tier(r, S2.ITEMS[iid])
                if t in tiers:
                    yield dict(r, tier=t), s["contexts"].get(iid, s["dump"]) or "(nothing)"


def key(r):
    return (r["framework"], r["user"], r["ckpt"], r["item"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["R"])
    ap.add_argument("--tiers", nargs="+", type=int, default=[1])
    ap.add_argument("--tags", nargs="+", default=["s4qwen", "s4llama"])
    ap.add_argument("--dry-run", action="store_true", help="count rows and estimate cost from context length; no calls")
    ap.add_argument("--check-cache", action="store_true", help="offline: rebuilt arm-O requests must be cache hits that reproduce the stored belief")
    ap.add_argument("--max-usd", type=float, default=30.0)
    a = ap.parse_args()

    if a.check_cache:
        from infra.llm import cache_lookup
        for tag in a.tags:
            n = hit = same = 0
            for r, ctx in rows_for(tag, set(a.tiers)):
                x = S2.ITEMS[r["item"]]
                resp, _ = cache_lookup(**request(MODELS[tag], ctx, x, "O"))
                n += 1
                if resp is not None:
                    hit += 1
                    ans = parse(resp.get("text") or "", x["options"])
                    b = "KEPT" if ans == x[r["version"]]["answer"] else "REVERTED" if ans is not None else "UNPARSED"
                    same += b == r.get("belief")
            print(f"{tag}: {n} rows, cache hits {hit} ({hit / max(n, 1):.4f}), belief reproduced {same} ({same / max(n, 1):.4f})")
        return

    plan = []
    for tag in a.tags:
        for arm in a.arms:
            dst = RES / f"order_{arm}_{tag}.jsonl"
            have = {key(r) for r in map(json.loads, open(dst))} if dst.exists() else set()
            todo = [(r, ctx) for r, ctx in rows_for(tag, set(a.tiers)) if key(r) not in have]
            plan.append((tag, arm, dst, todo))
    est = 0.0
    for tag, arm, dst, todo in plan:
        pin, pout = PRICE[MODELS[tag]]
        mean_in = sum(len(c) / 4 + 120 for _, c in todo) / max(len(todo), 1)
        e = len(todo) * (mean_in * pin + 6 * pout) / 1e6
        est += e
        print(f"{tag} arm {arm}: {len(todo)} calls, mean ~{mean_in:.0f} input tokens, est ${e:.2f} (upper bound: cache hits are free)")
        print("   by tier:", dict(collections.Counter(r["tier"] for r, _ in todo)))
    print(f"TOTAL est ${est:.2f}")
    if a.dry_run:
        return
    from infra.llm import batch_chat, estimate_cost, budget
    est2 = sum(estimate_cost(MODELS[tag], len(todo), sum(len(c) / 4 + 120 for _, c in todo) / max(len(todo), 1), 6)
               for tag, _, _, todo in plan)
    print(f"estimate_cost: ${est2:.2f}")
    if est2 > a.max_usd:
        sys.exit(f"estimate ${est2:.2f} exceeds --max-usd {a.max_usd}; stopping")
    if est2 > 2:
        spent = budget()["spent_usd"]
        ncalls = sum(len(t) for *_, t in plan)
        with open(ROOT / "COST_LOG.md", "a") as f:
            f.write(f"| {datetime.date.today()} | option-order check of the step-4 belief probe (ORDER_CHECK_DESIGN.md), arms "
                    f"{'+'.join(a.arms)}, tiers {'+'.join(map(str, a.tiers))} | qwen3-235b / llama3.3-70b (the step-4 readers; "
                    f"must be the same models) | {ncalls} | ${est2:.2f} | ${spent:.2f} before | |\n")
    for tag, arm, dst, todo in plan:
        if not todo:
            continue
        res = batch_chat([request(MODELS[tag], ctx, S2.ITEMS[r["item"]], arm) for r, ctx in todo], workers=16, desc=f"order {arm} {tag}")
        with open(dst, "a") as f:
            for (r, _), out in zip(todo, res):
                if out is None or out.get("error"):     # not written, so a rerun retries it
                    continue
                x = S2.ITEMS[r["item"]]
                t = (out or {}).get("text") or ""
                ans = parse(t, x["options"])
                b = "KEPT" if ans == x[r["version"]]["answer"] else "REVERTED" if ans is not None else "UNPARSED"
                f.write(json.dumps({k: r[k] for k in ("framework", "model", "user", "ckpt", "item", "version", "type", "state", "tier")}
                                   | {"arm": arm, "belief": b, "answer": ans, "text": t[:40]}) + "\n")
        print("wrote", dst)
    print("spent so far", budget()["spent_usd"])


if __name__ == "__main__":
    main()
