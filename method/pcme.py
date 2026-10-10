"""PCME: prior-controlled memory evaluation (see METHOD.md for definitions, assumptions and the procedure).

Library
    load_prior / load_runs          generic JSONL loaders (+ adapters for this repo's closed-book and rescore files)
    Prior                           per-item guess rate g_i (reader-specific) and prior strata (union over models)
    Panel                           items x systems correctness matrix aligned with the prior
    point estimates                 acc, cpr, ma, pcs, ors, pi, two_by_two, abstention
    inference                       bootstrap_weights (paired, optional clusters), two-stage prior resampling,
                                    kendall_tau_b, spearman, sign-flip permutation test, Holm, TOST verdicts,
                                    confirmed rank reversals

Generic input formats (one JSON object per line)
    prior draws : {"id", "model", "draw", "correct"}                       correct in {0,1} or [0,1]
    runs        : {"id", "system", "correct", ["protocol"], ["cluster"], ["answerable"], ["abstained"]}

CLI
    python pcme.py score --prior P1.jsonl [P2.jsonl ...] --reader MODEL --runs R1.jsonl [...] [--oracle SYSTEM]
                         [--where key=value ...] [--clusters] [--B 2000] [--json out.json]
    python pcme.py audit --prior P1.jsonl [...] --reader MODEL [--where key=value ...]
"""
import argparse, collections, glob, json, math, sys
from pathlib import Path
import numpy as np

# ------------------------------------------------------------------ loading


def _read_jsonl(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _match(row, where):
    return all(str(row.get(k)) == v for k, v in where)


def load_prior(paths, where=()):
    """Generic prior draws -> list of dicts. Rows from this repo's closed_book_<model>.jsonl files are adapted:
    only the forced protocol counts, model = file tag, draw = 'F0_T0'."""
    out = []
    for p in paths:
        stem = Path(p).stem
        for r in _read_jsonl(p):
            if not _match(r, where):
                continue
            if "proto" in r and "model" not in r:          # closed_book.py output
                if r["proto"] != "forced" or r.get("correct") is None:
                    continue
                out.append(dict(id=r["id"], model=stem.replace("closed_book_", ""), draw="F0_T0", correct=float(bool(r["correct"]))))
            else:
                if r.get("correct") is None:
                    continue
                out.append(dict(id=r["id"], model=r["model"], draw=r["draw"], correct=float(r["correct"])))
    return out


def load_runs(paths, where=()):
    """Generic run rows. Rows from rescore.py are adapted: cluster = episode, answerable = not abstention."""
    out = []
    for p in paths:
        for r in _read_jsonl(p):
            if not _match(r, where):
                continue
            out.append(dict(id=r["id"], system=r["system"], correct=None if r.get("correct") is None else float(r["correct"]),
                            protocol=r.get("protocol", "A"), cluster=r.get("cluster", r.get("episode", "all")),
                            answerable=r.get("answerable", not r.get("abstention", False)), abstained=r.get("abstained")))
    return out


# ------------------------------------------------------------------ prior


class Prior:
    """g[id] = mean correctness over the reader's draws; resistant[id] = no draw of any model is correct."""

    def __init__(self, draws, reader, strata_models=None):
        by = collections.defaultdict(list)
        anyc = collections.defaultdict(float)
        self.reader = reader
        for d in draws:
            if strata_models is None or d["model"] in strata_models or d["model"] == reader:
                anyc[d["id"]] = max(anyc[d["id"]], d["correct"])
            if d["model"] == reader:
                by[d["id"]].append(d["correct"])
        if not by:
            raise ValueError(f"no draws for reader {reader!r}; models present: {sorted({d['model'] for d in draws})}")
        self.draws = {i: np.array(v, float) for i, v in by.items()}
        self.g = {i: float(v.mean()) for i, v in self.draws.items()}
        self.resistant = {i: anyc[i] == 0 for i in self.g}

    def answerable_rate(self, ids):
        return 1 - float(np.mean([self.resistant[i] for i in ids]))


# ------------------------------------------------------------------ panel


class Panel:
    """Items x systems matrix for one protocol. Items = answerable items present for every system and in the prior."""

    def __init__(self, runs, prior, protocol=None, systems=None):
        rows = [r for r in runs if (protocol is None or r["protocol"] == protocol) and r["answerable"] and r["correct"] is not None]
        by_sys = collections.defaultdict(dict)
        clus = {}
        for r in rows:
            by_sys[r["system"]][r["id"]] = r["correct"]
            clus[r["id"]] = r["cluster"]
        self.systems = sorted(by_sys) if systems is None else [s for s in systems if s in by_sys]
        common = set(prior.g)
        for s in self.systems:
            common &= set(by_sys[s])
        self.ids = sorted(common)
        self.dropped = {s: len(set(by_sys[s]) - common) for s in self.systems}
        self.Y = np.array([[by_sys[s][i] for i in self.ids] for s in self.systems], float)   # S x n
        self.g = np.array([prior.g[i] for i in self.ids])
        self.R = np.array([prior.resistant[i] for i in self.ids], bool)
        self.cluster = np.array([str(clus[i]) for i in self.ids])
        self.prior = prior
        protos = {r["protocol"] for r in rows}
        self.protocol = protocol if protocol is not None else (protos.pop() if len(protos) == 1 else "mixed")

    def row(self, system):
        return self.Y[self.systems.index(system)]


# ------------------------------------------------------------------ point estimates (weights w: per-item multiplicity, default 1)


def _w(n, w):
    return np.ones(n) if w is None else w


def acc(Y, w=None):
    w = _w(Y.shape[-1], w)
    return (Y * w).sum(-1) / w.sum(-1)


def cpr(Y, R, w=None):
    w = _w(Y.shape[-1], w) * R
    return (Y * w).sum(-1) / w.sum(-1)


def ma(Y, g, w=None):
    w = _w(Y.shape[-1], w)
    return ((Y - g) * w).sum(-1) / w.sum(-1)


def pcs(Y, g, w=None):
    w = _w(Y.shape[-1], w)
    return ((Y - g) * w).sum(-1) / ((1 - g) * w).sum(-1)


def ors(Y, g, Yo, w=None):
    w = _w(Y.shape[-1], w)
    return ((Y - g) * w).sum(-1) / ((Yo - g) * w).sum(-1)


def pi(Y, g, w=None):
    return acc(Y, w) - pcs(Y, g, w)


def two_by_two(Y, R):
    """Shares of answerable items: verified memory, memory failure, unverifiable credit, prior interference."""
    n = Y.shape[-1]
    vm = (Y * R).sum(-1) / n
    mf = ((1 - Y) * R).sum(-1) / n
    uc = (Y * ~R).sum(-1) / n
    intf = ((1 - Y) * ~R).sum(-1) / n
    a = vm + uc
    return dict(verified=vm, mem_fail=mf, unverifiable=uc, interference=intf,
                verified_share=np.where(a > 0, vm / np.where(a > 0, a, 1), np.nan))


def abstention(abst_answerable, abst_unanswerable):
    """CA = P(abstain | unanswerable), FA = P(abstain | answerable), J = CA - FA."""
    ca = float(np.mean(abst_unanswerable)); fa = float(np.mean(abst_answerable))
    return dict(CA=ca, FA=fa, J=ca - fa)


# ------------------------------------------------------------------ inference


def bootstrap_weights(n, B=2000, seed=0, clusters=None):
    """B x n multiplicity matrix. Paired: the same matrix is used for every system. With clusters, whole clusters
    are resampled (each item gets its cluster's draw count)."""
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx = rng.integers(0, n, size=(B, n))
        W = np.zeros((B, n))
        np.add.at(W, (np.repeat(np.arange(B), n), idx.ravel()), 1)
        return W
    labels, inv = np.unique(clusters, return_inverse=True)
    k = len(labels)
    cidx = rng.integers(0, k, size=(B, k))
    C = np.zeros((B, k))
    np.add.at(C, (np.repeat(np.arange(B), k), cidx.ravel()), 1)
    return C[:, inv]


def prior_resample(prior, ids, B=2000, seed=1):
    """Two-stage bootstrap of g: within each item, resample its K draws. Returns B x n matrix of g."""
    rng = np.random.default_rng(seed)
    G = np.empty((B, len(ids)))
    for j, i in enumerate(ids):
        d = prior.draws[i]
        G[:, j] = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return G


def ci(samples, level=0.95):
    a = (1 - level) / 2
    s = np.asarray(samples, float)
    s = s[~np.isnan(s)]
    return float(np.quantile(s, a)), float(np.quantile(s, 1 - a))


def tost(point, samples, delta):
    """Equivalence verdict per METHOD §5: 'equivalent' if the 90% CI lies within +-delta; 'not equivalent' if the
    95% CI excludes 0 and |point| > delta; otherwise 'inconclusive'."""
    lo90, hi90 = ci(samples, 0.90)
    lo95, hi95 = ci(samples, 0.95)
    if -delta <= lo90 and hi90 <= delta:
        v = "equivalent"
    elif (lo95 > 0 or hi95 < 0) and abs(point) > delta:
        v = "not equivalent"
    else:
        v = "inconclusive"
    return dict(point=float(point), ci90=(lo90, hi90), ci95=(lo95, hi95), delta=delta, verdict=v)


def _ranks(x):
    """Average ranks (1 = smallest), ties get the mean rank."""
    x = np.asarray(x, float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = _ranks(x), _ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def kendall_tau_b(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = np.sign(x[i] - x[j]); dy = np.sign(y[i] - y[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                conc += 1
            else:
                disc += 1
    den = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return (conc - disc) / den if den else float("nan")


def signflip_test(d, n_perm=10000, seed=0):
    """Two-sided paired sign-flip permutation test of mean(d) = 0."""
    d = np.asarray(d, float)
    d = d[d != 0] if np.any(d != 0) else d
    if len(d) == 0 or not np.any(d):
        return 1.0
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    signs = rng.choice((-1.0, 1.0), size=(n_perm, len(d)))
    null = np.abs((signs * d).mean(1))
    return float((1 + (null >= obs - 1e-12).sum()) / (n_perm + 1))


def holm(pvals):
    """Holm step-down adjusted p-values (same order as input)."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def confirmed_reversals(diff_raw, diff_new):
    """Pairs whose raw and corrected differences both have 95% CIs excluding 0, with opposite signs."""
    conf, unres = [], []
    for k in diff_raw:
        (pr, (lr, hr)), (pn, (ln, hn)) = diff_raw[k], diff_new[k]
        if np.sign(pr) == np.sign(pn) or pr == 0 or pn == 0:
            continue
        sig_r = lr > 0 or hr < 0
        sig_n = ln > 0 or hn < 0
        (conf if sig_r and sig_n else unres).append(k)
    return conf, unres


# ------------------------------------------------------------------ batch evaluation


def evaluate(panel, B=2000, seed=0, clusters=False, oracle=None, two_stage=False):
    """All point estimates + paired-bootstrap CIs for every system in the panel."""
    n = len(panel.ids)
    W = bootstrap_weights(n, B, seed, panel.cluster if clusters else None)
    Y, g, R = panel.Y, panel.g, panel.R
    G = prior_resample(panel.prior, panel.ids, B, seed + 1) if two_stage else None
    Yo = panel.row(oracle) if oracle else None

    def boot(fn):
        # S x B
        return np.stack([fn(Y[s], W) for s in range(len(panel.systems))])

    stats = {
        "acc": (lambda y, w: acc(y, w)),
        "cpr": (lambda y, w: cpr(y, R, w)),
        "ma": (lambda y, w: ma(y, g if G is None or w is None else G, w)),
        "pcs": (lambda y, w: pcs(y, g if G is None or w is None else G, w)),
        "pi": (lambda y, w: pi(y, g if G is None or w is None else G, w)),
    }
    if Yo is not None:
        stats["ors"] = lambda y, w: ors(y, g if G is None or w is None else G, Yo, w)
    if panel.protocol != "F":       # METHOD §2.4: MA / PCS / PI / ORS are identified only under the forced protocol
        stats = {k: stats[k] for k in ("acc", "cpr")}
    res = {"protocol": panel.protocol, "n_items": n, "n_resistant": int(R.sum()), "prior_answerable_rate": float(1 - R.mean()), "mean_g": float(g.mean()),
           "systems": {}, "dropped": panel.dropped, "B": B, "clusters": bool(clusters), "two_stage": bool(two_stage)}
    boots = {k: boot(f) for k, f in stats.items()}
    tbt = two_by_two(Y, R)
    for si, s in enumerate(panel.systems):
        d = {}
        for k, f in stats.items():
            p = float(f(Y[si], None))
            d[k] = dict(point=p, ci=ci(boots[k][si]))
        for k, v in tbt.items():
            d["2x2_" + k] = float(v[si])
        res["systems"][s] = d
    res["_boot"] = boots
    return res


def ranking_analysis(panel, res, a="acc", b="cpr"):
    """Kendall tau_b / Spearman between the system rankings by two statistics, with bootstrap CIs, and pairwise
    confirmed reversals."""
    Sa, Sb = res["_boot"][a], res["_boot"][b]
    pa = np.array([res["systems"][s][a]["point"] for s in panel.systems])
    pb = np.array([res["systems"][s][b]["point"] for s in panel.systems])
    taus = [kendall_tau_b(Sa[:, k], Sb[:, k]) for k in range(Sa.shape[1])]
    rhos = [spearman(Sa[:, k], Sb[:, k]) for k in range(Sa.shape[1])]
    diff = lambda S, p: {(panel.systems[i], panel.systems[j]): (float(p[i] - p[j]), ci(S[i] - S[j]))
                         for i in range(len(p)) for j in range(i + 1, len(p))}
    conf, unres = confirmed_reversals(diff(Sa, pa), diff(Sb, pb))
    return dict(kendall_tau_b=kendall_tau_b(pa, pb), tau_ci=ci(taus), spearman=spearman(pa, pb), rho_ci=ci(rhos),
                confirmed_reversals=conf, unresolved_reversals=unres)


def format_table(panel, res, title=""):
    cols = [k for k in ("acc", "cpr", "ma", "pcs", "pi", "ors") if k in next(iter(res["systems"].values()))]
    lines = [title, f"items {res['n_items']}  prior-resistant {res['n_resistant']}  prior-answerable {res['prior_answerable_rate']:.1%}  "
                    f"mean g {res['mean_g']:.3f}  protocol {res['protocol']}  (B={res['B']}, clusters={res['clusters']}, two-stage g={res['two_stage']})"]
    if res["protocol"] != "F":
        lines.append("note: MA/PCS/PI are not reported off the forced protocol (not identified, METHOD §2.4)")
    lines.append(f"{'system':26s} " + " ".join(f"{c:>21s}" for c in cols) + f" {'verified share':>15s} {'interference':>13s}")
    order = sorted(panel.systems, key=lambda s: -res["systems"][s]["acc"]["point"])
    for s in order:
        d = res["systems"][s]
        cells = [f"{d[c]['point']:6.3f} [{d[c]['ci'][0]:6.3f},{d[c]['ci'][1]:6.3f}]" for c in cols]
        lines.append(f"{s:26s} " + " ".join(f"{x:>21s}" for x in cells) + f" {d['2x2_verified_share']:15.3f} {d['2x2_interference']:13.3f}")
    return "\n".join(lines)


def _jsonable(res):
    out = {k: v for k, v in res.items() if not k.startswith("_")}
    return json.loads(json.dumps(out, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("score", "audit"):
        p = sub.add_parser(name)
        p.add_argument("--prior", nargs="+", required=True)
        p.add_argument("--reader", required=True)
        p.add_argument("--strata-models", nargs="*", default=None, help="models whose draws define the strata (default: all)")
        p.add_argument("--where", nargs="*", default=[], help="key=value filters applied to prior and run rows")
        if name == "score":
            p.add_argument("--runs", nargs="+", required=True)
            p.add_argument("--protocol", default=None)
            p.add_argument("--oracle", default=None)
            p.add_argument("--clusters", action="store_true")
            p.add_argument("--two-stage", action="store_true")
            p.add_argument("--B", type=int, default=2000)
            p.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    where = [tuple(x.split("=", 1)) for x in a.where]
    paths = [p for pat in a.prior for p in sorted(glob.glob(pat))]
    prior = Prior(load_prior(paths, where), a.reader, a.strata_models)
    if a.cmd == "audit":
        ids = sorted(prior.g)
        rs = np.array([not prior.resistant[i] for i in ids], float)
        W = bootstrap_weights(len(ids))
        lo, hi = ci((W * rs).sum(1) / W.sum(1))
        print(f"items {len(ids)}  prior-answerable {rs.mean():.3f} [{lo:.3f},{hi:.3f}]  mean g (reader) {np.mean([prior.g[i] for i in ids]):.3f}")
        return
    runs = load_runs([p for pat in a.runs for p in sorted(glob.glob(pat))], where)
    panel = Panel(runs, prior, a.protocol)
    res = evaluate(panel, a.B, clusters=a.clusters, oracle=a.oracle, two_stage=a.two_stage)
    print(format_table(panel, res))
    rk = ranking_analysis(panel, res)
    print(f"ranking acc vs cpr: tau_b {rk['kendall_tau_b']:.3f} {rk['tau_ci']}  spearman {rk['spearman']:.3f}  "
          f"confirmed reversals {len(rk['confirmed_reversals'])}  unresolved {len(rk['unresolved_reversals'])}")
    if a.json:
        out = _jsonable(res); out["ranking_acc_vs_cpr"] = rk
        Path(a.json).write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
