"""Stimulus loading, name parameterization, and frozen chain manifests.

Design decisions enforced here (from refine-logs/round-2-refinement.md):
  * Entity names are rotated at the TRAJECTORY level (chain x seed), not per item: a
    seeding session has to describe one coherent workplace, so every fact in a trajectory
    shares one {{COMPANY}}/{{TOWN}} pair. Rotating across seeds still breaks any systematic
    level->name pairing, which is what the confound requires; realized balance is reported.
  * Dev families (F01-F12, P01-P06) are used only for operating-point selection.
    Confirmatory families (F13-F40, P07-P20) are frozen before first use.
  * No family appears twice in a chain, so levels of one family never compete with each other.
  * Chain assignment uses constrained randomization on frozen Bradley-Terry estimates
    to balance MEASURED surprise across chains (nominal level balance is not enough).
"""
import json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STIM = ROOT / "docs" / "idea" / "idea1_pilot" / "stimuli"

COMPANIES = ["Veltrix", "Quorvane", "Lamprick", "Dentara", "Oskwell"]
TOWNS = ["Northvale", "Ashmere", "Pellbury", "Kirrowan", "Stentfield"]

DEV_FACTS = {f"F{i:02d}" for i in range(1, 13)}
DEV_PREFS = {f"P{i:02d}" for i in range(1, 7)}


def _load(name):
    return [json.loads(l) for l in (STIM / name).read_text().splitlines() if l.strip()]


def _tightened():
    """Frozen tightened attribute regexes (built by src/attr_regex.py). See that file for why."""
    p = ROOT / "results" / "attribute_regexes.json"
    if not p.exists():
        return {}
    return {k: v["attribute_regex"] for k, v in json.loads(p.read_text())["regexes"].items()}


def load_families():
    """All fact families, with COMPANY/TOWN replaced by placeholders and attribute regexes
    replaced by the frozen tightened versions when those have been built."""
    fams = _load("facts_mundane.jsonl") + _load("facts_vivid.jsonl")
    tight = _tightened()
    for f in fams:
        if f["family_id"] in tight:
            f["attribute_regex_original"] = f["attribute_regex"]
            f["attribute_regex"] = tight[f["family_id"]]
        f["split"] = "dev" if f["family_id"] in DEV_FACTS else "confirmatory"
        for key in ("template", "question", "attribute_regex"):
            f[key] = f[key].replace("Veltrix", "{{COMPANY}}").replace("Northvale", "{{TOWN}}")
        for lv in f["levels"]:
            lv["sentence"] = lv["sentence"].replace("Veltrix", "{{COMPANY}}").replace("Northvale", "{{TOWN}}")
    return fams


def load_preferences():
    prefs = _load("preferences.jsonl")
    for p in prefs:
        p["split"] = "dev" if p["family_id"] in DEV_PREFS else "confirmatory"
    return prefs


def load_fillers():
    raw = json.loads((STIM / "fillers.json").read_text())
    return [s.replace("Veltrix", "{{COMPANY}}").replace("Northvale", "{{TOWN}}") for s in raw]


def world(chain_idx, seed_idx):
    """Entity names for one trajectory. Rotation breaks level->name pairing across seeds."""
    return {"COMPANY": COMPANIES[(chain_idx + seed_idx) % len(COMPANIES)],
            "TOWN": TOWNS[(chain_idx + 2 * seed_idx) % len(TOWNS)]}


def render(text, w):
    return text.replace("{{COMPANY}}", w["COMPANY"]).replace("{{TOWN}}", w["TOWN"])


def instances(families, split):
    """Every (family, level) pair in a split -> one item instance."""
    out = []
    for f in families:
        if f["split"] != split:
            continue
        for lv in f["levels"]:
            out.append({"family_id": f["family_id"], "kind": f["kind"], "level": lv["level"],
                        "item_id": f"{f['family_id']}L{lv['level']}"})
    return out


def _cost(chains, surprise, n_per_chain):
    """Max between-chain difference in mean measured surprise (lower is better)."""
    means = []
    for ch in chains:
        vals = [surprise.get(it["item_id"]) for it in ch]
        vals = [v for v in vals if v is not None]
        means.append(sum(vals) / len(vals) if vals else 0.0)
    return max(means) - min(means)


def build_chains(families, split="confirmatory", n_chains=7, seed=20261006,
                 surprise=None, restarts=3000):
    """Assign (family, level) instances to chains.

    Guarantees, in order of priority:
      1. the levels of one family land in DISTINCT chains, so a family's levels never
         compete with each other inside one memory;
      2. chain sizes differ by at most one;
      3. among assignments satisfying 1-2, the one minimising the maximum between-chain
         difference in mean MEASURED surprise is chosen (constrained randomization).

    `surprise` maps item_id -> measured surprise. When None, the nominal level index is used
    as a stand-in; the manifest records which basis was used.
    """
    mundane = [i for i in instances(families, split) if i["kind"] == "mundane"]
    vivid = [i for i in instances(families, split) if i["kind"] == "vivid"]
    if surprise is None:
        surp = {i["item_id"]: float(i["level"]) for i in mundane}
        basis = "nominal-level"
    else:
        surp = surprise
        basis = "measured-BT"

    by_fam = {}
    for i in mundane:
        by_fam.setdefault(i["family_id"], []).append(i)
    n = len(mundane)
    sizes = [n // n_chains + (1 if c < n % n_chains else 0) for c in range(n_chains)]

    rng = random.Random(seed)
    best, best_cost = None, float("inf")
    for _ in range(restarts):
        chains = [[] for _ in range(n_chains)]
        cap = sizes[:]
        fams_order = list(by_fam.values())
        rng.shuffle(fams_order)
        ok = True
        for levels in fams_order:
            # chains with the most remaining capacity first, ties broken at random
            cand = sorted(range(n_chains), key=lambda c: (-cap[c], rng.random()))
            cand = [c for c in cand if cap[c] > 0][:len(levels)]
            if len(cand) < len(levels):
                ok = False; break
            lv = levels[:]
            rng.shuffle(lv)
            for c, it in zip(cand, lv):
                chains[c].append(it); cap[c] -= 1
        if not ok or any(cap):
            continue
        cost = _cost(chains, surp, None)
        if cost < best_cost:
            best, best_cost = chains, cost
    if best is None:
        raise RuntimeError("no feasible chain assignment found")

    # The vivid/mundane contrast was an exploratory factor only. It is dropped so that dev and
    # confirmatory chains carry exactly the same number of seeded items, which is what makes an
    # operating point selected on dev transfer to confirmatory.
    vivid = []

    out = []
    for ci, items in enumerate(best):
        order = items[:]
        rng.shuffle(order)          # within-session position randomized per chain
        out.append({"chain_id": f"C{ci+1:02d}", "items": order})
    return {"chains": out, "balance_basis": basis, "max_mean_surprise_gap": best_cost,
            "chain_sizes": sizes, "n_mundane": n, "n_vivid": len(vivid), "seed": seed}


if __name__ == "__main__":
    fams = load_families()
    import collections
    print("families:", collections.Counter(f["split"] for f in fams))
    conf = instances(fams, "confirmatory")
    dev = instances(fams, "dev")
    print("confirmatory instances:", len(conf), " dev instances:", len(dev))
    print("confirmatory mundane:", sum(1 for i in conf if i["kind"] == "mundane"),
          " vivid:", sum(1 for i in conf if i["kind"] == "vivid"))
    m = build_chains(fams, restarts=400)
    print("chains:", len(m["chains"]), "sizes:", m["chain_sizes"], "vivid:", m["n_vivid"],
          "gap:", round(m["max_mean_surprise_gap"], 4), "basis:", m["balance_basis"])
    for ch in m["chains"]:
        fams_in = [i["family_id"] for i in ch["items"]]
        assert len(fams_in) == len(set(fams_in)), f"family repeated in {ch['chain_id']}"
    print("check: no family repeats within any chain  OK")
    for ch in m["chains"][:2]:
        print(" ", ch["chain_id"], [i["item_id"] for i in ch["items"]][:8], "...")
