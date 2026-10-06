"""Amendment A1: simulation-based power for the E-SHIFT primary analysis."""
import json, random, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT
import analysis as A

RES = ROOT / "results"


def variance_components(per_family):
    """Between-family SD of the paired difference, and within-family (seed) SD.

    The naive SD of family means confounds true between-family heterogeneity with the sampling
    noise of only n_seeds binary observations per family, so it is deconfounded here:
        Var(family mean) = sigma_fam^2 + sigma_seed^2 / n_seeds.
    """
    means = [statistics.mean(v) for v in per_family.values() if v]
    withins = [statistics.stdev(v) for v in per_family.values() if len(v) > 1]
    n_seed = statistics.mean([len(v) for v in per_family.values()]) if per_family else 3
    raw = statistics.stdev(means) if len(means) > 1 else 20.0
    s_seed = statistics.mean(withins) if withins else 25.0
    s_fam = max(1.0, (max(0.0, raw**2 - s_seed**2 / max(1, n_seed)))**0.5)
    return s_fam, s_seed


def power(n_fam, n_seed, s_fam, s_seed, effect=8.0, n_sim=2000, n_boot=600, seed=29):
    """Fraction of simulated studies in which the frozen rule returns POSITIVE_SUPPORT."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_sim):
        pf = {}
        for i in range(n_fam):
            mu = rng.gauss(effect, s_fam)
            pf[f"F{i}"] = [max(-100.0, min(100.0, rng.gauss(mu, s_seed))) for _ in range(n_seed)]
        boot = A.family_paired_bootstrap(pf, n_boot=n_boot, seed=rng.randrange(10**6))
        lo, _ = A.ci(boot, 2.5, 97.5)
        if lo > 0:
            hits += 1
    return hits / n_sim


def mde(n_fam, n_seed, s_fam, s_seed, target=0.80, lo=1.0, hi=40.0, n_sim=600):
    """Minimum detectable effect at `target` power, by bisection."""
    for _ in range(7):
        mid = (lo + hi) / 2
        if power(n_fam, n_seed, s_fam, s_seed, effect=mid, n_sim=n_sim, n_boot=400) >= target:
            hi = mid
        else:
            lo = mid
    return hi


if __name__ == "__main__":
    import analyse_eshift as E
    rows = A.load_rows("eshift_dev")
    index = json.loads((RES / "eshift_dev_index.json").read_text())
    pf = E.paired_differences(rows, index, "O1", 10, split="dev", endpoint="survival")
    s_fam, s_seed = variance_components(pf)
    print(f"dev variance components: between-family SD {s_fam:.1f} pp, "
          f"within-family (seed) SD {s_seed:.1f} pp, from {len(pf)} dev families")

    grid_f = [12, 18, 26, 40, 60]
    grid_s = [3, 6, 8, 12]
    table = {}
    print(f"\n{'n_fam':>6}" + "".join(f"{f'seeds={s}':>11}" for s in grid_s))
    for nf in grid_f:
        row = []
        for ns in grid_s:
            p = power(nf, ns, s_fam, s_seed, effect=8.0, n_sim=600, n_boot=400)
            table[f"{nf}x{ns}"] = p
            row.append(p)
        print(f"{nf:>6}" + "".join(f"{p:>11.2f}" for p in row))

    # The feasible cell is fixed by how many families survived frame eligibility; seeds are cheap.
    feasible_f, feasible_s = 18, 8
    chosen = None
    for nf in grid_f:
        if nf > feasible_f:
            break
        for ns in grid_s:
            if ns <= feasible_s and table.get(f"{nf}x{ns}", 0) >= 0.80:
                chosen = (nf, ns); break
        if chosen:
            break
    out = {"s_fam": s_fam, "s_seed": s_seed, "n_dev_families": len(pf),
           "power_table": table, "sesoi": 8.0, "endpoint": "survival_fraction",
           "amendment": "A4: primary endpoint changed from binary retention at k=10 to the survival "
                        "fraction over all nine checkpoints, decided on dev data before any "
                        "confirmatory E-SHIFT run. Dev MDE 37.8 pp -> 15.6 pp at the same cost."}
    if chosen:
        out["chosen"] = {"n_families": chosen[0], "n_seeds": chosen[1]}
        out["operative_sesoi"] = 8.0
        print(f"\nCHOSEN: {chosen[0]} eligible families x {chosen[1]} seeds (power >= 0.80 at 8 pp)")
    else:
        m = mde(feasible_f, feasible_s, s_fam, s_seed)
        out["chosen"] = {"n_families": feasible_f, "n_seeds": feasible_s}
        out["operative_sesoi"] = m
        out["note"] = ("No cell reaches 0.80 power at the 8 pp SESOI: between-family heterogeneity "
                       "in the frame effect is large and is not reducible by adding seeds. Per "
                       "amendment A1 step 5 the maximum feasible cell is used and the operative "
                       "SESOI is frozen at the minimum detectable effect under it. C1 is therefore "
                       "powered only for effects of at least this size, and the paper states so.")
        print(f"\nNo cell reaches 0.80 at 8 pp. Using the maximum FEASIBLE cell "
              f"({feasible_f} eligible families x {feasible_s} seeds); operative SESOI frozen at "
              f"X = {m:.1f} pp (amendment A1 step 5).")
    (RES / "power.json").write_text(json.dumps(out, indent=1))
