"""E0 of the option-order check (framework_study/ORDER_CHECK_DESIGN.md §4): the V1 prior gate split by option order.

V1 asked every item 10 times per options-line order at T=1 (validate_v2.py) but stored only the pooled P(C). The
responses are in the infra/llm.py cache, so the split costs nothing: this script rebuilds the V1 requests for the S4
items and reads them back with cache_lookup (offline; a request that is not in the cache is counted, never sent).
Output: results/order_e0.json and printed summary.
"""
import collections, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src"))
from infra.llm import cache_lookup
from validate import parse
import validate_v2 as V
import sessions_v2 as S2

MODELS = {"qwen": "qwen.qwen3-235b-a22b-2507-v1:0", "llama": "meta.llama3-3-70b-instruct-v1:0"}


def main():
    items = list(S2.ITEMS.values())
    reqs, meta = V.requests(items)
    cnt = collections.defaultdict(lambda: [0, 0, 0])      # (model, item, order) -> [C, I, none]
    miss = collections.Counter()
    for r, (kind, m, iid, order) in zip(reqs, meta):
        if kind != "V1" or m not in MODELS.values():
            continue
        resp, _ = cache_lookup(**r)
        if resp is None:
            miss[m] += 1; continue
        x = S2.ITEMS[iid]
        a = parse(resp.get("text") or "", x["options"])
        cnt[(m, iid, order)][0 if a == x["C"]["answer"] else 1 if a == x["I"]["answer"] else 2] += 1
    out = {"cache_misses": dict(miss)}
    for fam, m in MODELS.items():
        for kind in ("non-neutral", "neutral"):
            ids = [x["id"] for x in items if (x["type"] == "neutral") == (kind == "neutral")]
            pairs = []
            for iid in ids:
                (c0, i0, _), (c1, i1, _) = cnt[(m, iid, 0)], cnt[(m, iid, 1)]
                if c0 + i0 and c1 + i1:
                    pairs.append((c0 / (c0 + i0), c1 / (c1 + i1)))
            p0, p1 = np.array(pairs).T
            n = len(pairs)
            # first-position effect on P(C): order 0 lists C first, order 1 lists I first
            o = dict(n_items=n, pC_order0=float(p0.mean()), pC_order1=float(p1.mean()), position_effect=float((p0 - p1).mean() / 2),
                     share_items_modal_C_order1=float(np.mean(p1 > 0.5)), share_items_modal_C_order0=float(np.mean(p0 > 0.5)))
            out[f"{fam}/{kind}"] = o
            print(f"{fam:6s} {kind:12s} items {n:3d}  P(C | C listed first) {o['pC_order0']:.3f}  P(C | I listed first) {o['pC_order1']:.3f}  "
                  f"position effect (half-difference) {o['position_effect']:+.3f}  modal C: {o['share_items_modal_C_order0']:.2f} / {o['share_items_modal_C_order1']:.2f}")
    print("cache misses:", dict(miss))
    (ROOT / "framework_study/results/order_e0.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
