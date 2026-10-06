"""Preregistered estimators.

Everything here follows refine-logs/round-2-refinement.md change 10 and amendments A1-A3:

  * primary estimator  : family-FIXED-EFFECTS LINEAR PROBABILITY MODEL of RETAINED at k=10 on
                         within-family-centred surprise x operator, plus token-length and format
                         nuisance covariates. The estimand is a percentage-point slope, and an LPM
                         cannot suffer the quasi-complete separation that logistic FE can.
  * main-chain inference: TWO-WAY CROSSED cluster bootstrap. Families and chain x seed BLOCKS are
                         reweighted independently; a block carries all of its paired operators, so
                         an O1/O3 contrast is never split across resamples.
  * E-SHIFT inference  : trajectories are NESTED within families there, so it uses a FAMILY
                         bootstrap with arm-paired seed blocks resampled within family.
  * equivalence        : TOST in percentage points, both bounds.
"""
import json, math, random, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stimuli import ROOT

RES = ROOT / "results"
RETAINED, CHANGED, DROPPED, UNRESOLVED = "RETAINED", "CHANGED", "DROPPED", "UNRESOLVED"


def load_rows(tag):
    return [json.loads(l) for l in (RES / f"coded_{tag}.jsonl").read_text().splitlines() if l.strip()]


def attach(rows, manifest):
    """Attach the measured dose and the nuisance covariates to every coded row."""
    surp, tok = manifest["surprise_bt"], manifest["token_audit"]
    out = []
    for r in rows:
        iid = r["item_id"]
        if iid not in surp:
            continue
        t = tok.get(iid, {})
        r = dict(r)
        r["surprise"] = surp[iid]
        r["n_tokens"] = t.get("n_tokens", 0)
        r["has_digit"] = int(t.get("has_digit", False))
        r["block"] = f"{r['chain_id']}|s{r['seed_idx']}"      # crossed cluster: chain x seed
        r["retained"] = 1.0 if r["label"] == RETAINED else 0.0
        out.append(r)
    return out


# --------------------------------------------------------------------- linear probability model
def lpm(rows, interact_ops=None, covariates=("n_tokens", "has_digit")):
    """Retained ~ surprise * operator + family FE + covariates.

    Returns {"slope_<op>": pp per log-odds of surprise, "interaction_<op>": difference vs the
    reference operator}. Surprise is already within-family centred, and family fixed effects are
    included as well, so between-family variation cannot drive the slope.
    """
    if not rows:
        return {}
    ops = sorted({r["op"] for r in rows})
    ref = interact_ops[0] if interact_ops else ops[0]
    fams = sorted({r["family_id"] for r in rows})
    fidx = {f: i for i, f in enumerate(fams)}
    oidx = {o: i for i, o in enumerate(ops)}

    n = len(rows)
    p = len(fams) + len(ops) - 1 + len(ops) + len(covariates)
    X = np.zeros((n, p)); y = np.zeros(n)
    for i, r in enumerate(rows):
        y[i] = r["retained"]
        X[i, fidx[r["family_id"]]] = 1.0                                  # family FE (no intercept)
        o = oidx[r["op"]]
        if o > 0:
            X[i, len(fams) + o - 1] = 1.0                                 # operator main effects
        X[i, len(fams) + len(ops) - 1 + o] = r["surprise"]                # per-operator slope
        for j, c in enumerate(covariates):
            X[i, len(fams) + 2 * len(ops) - 1 + j] = r[c]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    out = {}
    base = len(fams) + len(ops) - 1
    for o, i in oidx.items():
        out[f"slope_{o}"] = 100.0 * beta[base + i]                        # percentage points
    for o in ops:
        if o != ref:
            out[f"interaction_{o}_vs_{ref}"] = out[f"slope_{o}"] - out[f"slope_{ref}"]
    out["_ref"] = ref
    return out


# --------------------------------------------------------------------- bootstraps
def crossed_bootstrap(rows, stat_fn, n_boot=2000, seed=11):
    """Two-way crossed cluster bootstrap over families and chain x seed blocks.

    Both dimensions are resampled independently and a row is included with the PRODUCT of the two
    draw counts, which is the standard multi-way cluster bootstrap weighting. Blocks carry all of
    their operators, so paired contrasts survive resampling intact.
    """
    rng = random.Random(seed)
    fams = sorted({r["family_id"] for r in rows})
    blocks = sorted({r["block"] for r in rows})
    by = defaultdict(list)
    for r in rows:
        by[(r["family_id"], r["block"])].append(r)
    out = []
    for _ in range(n_boot):
        cf = Counter(rng.choices(fams, k=len(fams)))
        cb = Counter(rng.choices(blocks, k=len(blocks)))
        samp = []
        for (f, b), rs in by.items():
            w = cf.get(f, 0) * cb.get(b, 0)
            if w:
                samp.extend(rs * w)
        if samp:
            try:
                out.append(stat_fn(samp))
            except Exception:
                pass
    return out


def family_paired_bootstrap(per_family, n_boot=10000, seed=13):
    """E-SHIFT: families resampled with replacement; within each, its arm-paired seed blocks are
    resampled. `per_family` maps family_id -> list of per-seed paired differences."""
    rng = random.Random(seed)
    fams = sorted(per_family)
    out = []
    for _ in range(n_boot):
        vals = []
        for f in rng.choices(fams, k=len(fams)):
            seeds = per_family[f]
            if not seeds:
                continue
            draws = [seeds[rng.randrange(len(seeds))] for _ in range(len(seeds))]
            vals.append(sum(draws) / len(draws))
        if vals:
            out.append(sum(vals) / len(vals))
    return out


def ci(dist, lo=2.5, hi=97.5):
    a = np.array(dist, dtype=float)
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


def tost(dist, margin):
    """Two one-sided tests. Equivalent iff the 90% interval lies strictly inside +/- margin."""
    lo, hi = ci(dist, 5, 95)
    return {"ci90": (lo, hi), "margin": margin, "equivalent": (lo > -margin and hi < margin)}


def decision_C1(dist, sesoi):
    """The frozen four-outcome rule from amendment A2, in precedence order."""
    lo95, hi95 = ci(dist, 2.5, 97.5)
    eq = tost(dist, sesoi)
    excludes_zero = lo95 > 0
    if excludes_zero and not eq["equivalent"]:
        d = "POSITIVE_SUPPORT"
    elif excludes_zero and eq["equivalent"]:
        d = "POSITIVE_BELOW_SESOI"
    elif (lo95 <= 0 <= hi95) and eq["equivalent"]:
        d = "BOUNDARY_EVIDENCE"
    else:
        d = "INCONCLUSIVE"
    return {"decision": d, "ci95": (lo95, hi95), "ci90": eq["ci90"], "sesoi": sesoi,
            "mean": float(np.mean(dist))}


# --------------------------------------------------------------------- replacement direction
def direction(rows, manifest, n_boot=5000, seed=17):
    """Delta = log p(v_new) - log p(v_old) on the Bradley-Terry scale, over CHANGED-specific events
    whose destination is a canonical level. OTHER destinations are excluded here and analysed
    separately, because they are not on the same scale."""
    pr = manifest["prior_prob"]
    ev = []
    for r in rows:
        if r["label"] != CHANGED or r["dest"] in (None, "VAGUE", "OTHER"):
            continue
        old = pr.get(r["item_id"])
        new = pr.get(f"{r['family_id']}L{r['dest']}")
        if not old or not new:
            continue
        ev.append({"delta": math.log(new) - math.log(old), "family_id": r["family_id"],
                   "block": r["block"], "origin": r["level"], "dest": r["dest"],
                   "dist": abs(int(r["dest"]) - int(r["level"]))})
    if not ev:
        return {"n": 0}
    boot = crossed_bootstrap(ev, lambda s: float(np.mean([e["delta"] for e in s])),
                             n_boot=n_boot, seed=seed)
    # within-family permutation that PRESERVES origin rank, the opportunity set and distance:
    # destinations are permuted only among events sharing (family, origin, |distance|).
    rng = random.Random(seed)
    strata = defaultdict(list)
    for e in ev:
        strata[(e["family_id"], e["origin"], e["dist"])].append(e)
    null = []
    for _ in range(2000):
        tot = []
        for key, es in strata.items():
            dests = [e["dest"] for e in es]
            rng.shuffle(dests)
            for e, dst in zip(es, dests):
                old = pr.get(e_id := f"{e['family_id']}L{e['origin']}")
                new = pr.get(f"{e['family_id']}L{dst}")
                if old and new:
                    tot.append(math.log(new) - math.log(old))
        if tot:
            null.append(float(np.mean(tot)))
    obs = float(np.mean([e["delta"] for e in ev]))
    p = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1) if null else None
    return {"n": len(ev), "mean_delta": obs, "ci95": ci(boot), "perm_p": p,
            "frac_prior_ward": float(np.mean([e["delta"] > 0 for e in ev]))}


# --------------------------------------------------------------------- value-level kernel
def rank_state(item_id, manifest, n_ranks=5):
    """Kernel states are the MEASURED prior rank within family, never the design level name --
    otherwise L2 -> L3 has no consistent meaning across families."""
    fid = item_id.split("L")[0]
    surp = manifest["surprise_bt"]
    sibs = sorted([k for k in surp if k.startswith(fid + "L")], key=lambda k: surp[k])
    return f"R{sibs.index(item_id) + 1}" if item_id in sibs else None


def kernel_fit(rows, manifest, alpha=1.0):
    """Estimate K from k=0 -> 1 with Dirichlet smoothing; returns (states, K, support)."""
    states = [f"R{i}" for i in range(1, 6)] + ["OTHER", "VAGUE", "ABSENT"]
    si = {s: i for i, s in enumerate(states)}
    by = defaultdict(dict)
    for r in rows:
        by[(r["run_id"], r["item_id"])][r["k"]] = r
    counts = np.zeros((len(states), len(states)))
    for key, ks in by.items():
        if 0 not in ks or 1 not in ks:
            continue
        a, b = state_of(ks[0], manifest), state_of(ks[1], manifest)
        if a in si and b in si:
            counts[si[a], si[b]] += 1
    support = counts.sum(axis=1).copy()
    K = (counts + alpha) / (counts + alpha).sum(axis=1, keepdims=True)
    return states, K, support


def state_of(row, manifest):
    if row["label"] == RETAINED:
        return rank_state(row["item_id"], manifest)
    if row["label"] == DROPPED:
        return "ABSENT"
    if row["label"] == CHANGED:
        d = row["dest"]
        if d in ("VAGUE", None):
            return "VAGUE"
        if d == "OTHER":
            return "OTHER"
        return rank_state(f"{row['family_id']}L{d}", manifest)
    return None


def tvd(p, q):
    return 0.5 * float(np.abs(np.asarray(p) - np.asarray(q)).sum())


def kernel_predict(rows_train, rows_test, manifest, ks=(10, 15, 20)):
    """Fit K on held-in trajectories, predict p0 K^k on HELD-OUT ones, and compare against two
    baselines that receive the same held-out p0: constant one-step retention, and pure
    absorbing-drop. Inference is on the PAIRED difference in held-out TVD."""
    states, K, support = kernel_fit(rows_train, manifest)
    si = {s: i for i, s in enumerate(states)}

    def dist_at(rows, k):
        c = np.zeros(len(states))
        for r in rows:
            if r["k"] != k:
                continue
            s = state_of(r, manifest)
            if s in si:
                c[si[s]] += 1
        return c / c.sum() if c.sum() else c

    p0 = dist_at(rows_test, 0)
    # baseline 1: constant per-step survival, estimated on the TRAINING half only
    tr1 = dist_at(rows_train, 1)
    keep = float(1.0 - tr1[si["ABSENT"]]) if tr1.sum() else 0.5
    out = {"states": states, "support": support.tolist(), "k": {}}
    for k in ks:
        obs = dist_at(rows_test, k)
        if not obs.sum():
            continue
        pred = p0 @ np.linalg.matrix_power(K, k)
        b1 = p0 * (keep ** k); b1[si["ABSENT"]] += 1 - b1.sum()          # constant decay
        b2 = np.zeros(len(states)); b2[si["ABSENT"]] = 1.0               # pure absorbing drop
        out["k"][k] = {"tvd_kernel": tvd(pred, obs), "tvd_const": tvd(b1, obs),
                       "tvd_absorb": tvd(b2, obs),
                       "paired_gain_vs_const": tvd(b1, obs) - tvd(pred, obs),
                       "paired_gain_vs_absorb": tvd(b2, obs) - tvd(pred, obs)}
    # regeneration out of ABSENT, with its observation count
    n_abs, n_regen = 0, 0
    by = defaultdict(dict)
    for r in rows_train + rows_test:
        by[(r["run_id"], r["item_id"])][r["k"]] = r
    ordered = sorted({r["k"] for r in rows_train + rows_test})
    for key, kk in by.items():
        for a, b in zip(ordered, ordered[1:]):
            if a in kk and b in kk and state_of(kk[a], manifest) == "ABSENT":
                n_abs += 1
                if state_of(kk[b], manifest) != "ABSENT":
                    n_regen += 1
    out["absent_regeneration"] = {"n_absent_transitions": n_abs, "n_regenerated": n_regen,
                                  "rate": n_regen / n_abs if n_abs else None}
    return out
