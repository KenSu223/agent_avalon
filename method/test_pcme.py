"""Unit tests for pcme.py.  Run: python3 -m unittest method/test_pcme.py -v

The simulation tests draw data from the two-state model of METHOD.md §1 with known retention, so each estimator
can be checked against its identified target, including the case where assumption A3 is violated.
"""
import json, sys, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import pcme


def simulate(n=4000, R_sys=(0.0, 0.3, 0.7, 1.0), p=1.0, K=6, seed=0, prior_directed=0.0):
    """Items: 30% guessable (g=0.9), 70% non-guessable (g=0). Each system keeps item i with prob R (optionally
    lower on guessable items: prior_directed = extra drop prob on guessable items). Y ~ Bern(p) if kept else Bern(g).
    Returns draws, runs, true per-system retention (overall and on non-guessable items)."""
    rng = np.random.default_rng(seed)
    g = np.where(rng.random(n) < 0.3, 0.9, 0.0)
    draws = [dict(id=f"q{i}", model="reader", draw=f"d{k}", correct=float(rng.random() < g[i])) for i in range(n) for k in range(K)]
    runs, truth = [], {}
    for j, R in enumerate(R_sys):
        keep_p = np.where(g > 0, np.clip(R - prior_directed, 0, 1), R)
        Z = rng.random(n) < keep_p
        Y = np.where(Z, rng.random(n) < p, rng.random(n) < g).astype(float)
        truth[f"s{j}"] = dict(R=float(Z.mean()), R_res=float(Z[g == 0].mean()))
        runs += [dict(id=f"q{i}", system=f"s{j}", correct=float(Y[i]), protocol="F", cluster=f"c{i % 20}", answerable=True, abstained=None)
                 for i in range(n)]
    return draws, runs, truth, g


class TestEstimators(unittest.TestCase):
    def setUp(self):
        self.draws, self.runs, self.truth, self.g = simulate()
        self.prior = pcme.Prior(self.draws, "reader")
        self.panel = pcme.Panel(self.runs, self.prior, "F")

    def test_pcs_recovers_retention_under_A1_A3(self):
        res = pcme.evaluate(self.panel, B=200)
        for s, t in self.truth.items():
            self.assertAlmostEqual(res["systems"][s]["pcs"]["point"], t["R"], delta=0.04, msg=s)

    def test_cpr_recovers_counter_prior_retention(self):
        res = pcme.evaluate(self.panel, B=200)
        for s, t in self.truth.items():
            self.assertAlmostEqual(res["systems"][s]["cpr"]["point"], t["R_res"], delta=0.03, msg=s)

    def test_floor_and_inflation(self):
        res = pcme.evaluate(self.panel, B=200)
        gbar = self.g.mean()
        self.assertAlmostEqual(res["systems"]["s0"]["ma"]["point"], 0.0, delta=0.02)           # memoryless system
        self.assertGreater(res["systems"]["s0"]["acc"]["point"], 0.2)                           # raw floor = gbar
        for s, t in self.truth.items():                                                          # PI = (1-R) * gbar
            self.assertAlmostEqual(res["systems"][s]["pi"]["point"], (1 - t["R"]) * gbar, delta=0.03, msg=s)

    def test_two_by_two_identities(self):
        t = pcme.two_by_two(self.panel.Y, self.panel.R)
        tot = t["verified"] + t["mem_fail"] + t["unverifiable"] + t["interference"]
        np.testing.assert_allclose(tot, 1.0)
        np.testing.assert_allclose(t["verified"] + t["unverifiable"], pcme.acc(self.panel.Y))

    def test_degenerate_g_identity(self):
        """With g in {0,1}: sum(Y-g) = #correct on resistant - #wrong on answerable."""
        Y = np.array([1, 0, 1, 0, 1, 1.0]); g = np.array([0, 0, 1, 1, 1, 0.0]); R = g == 0
        lhs = (Y - g).sum()
        rhs = (Y * R).sum() - ((1 - Y) * ~R).sum()
        self.assertEqual(lhs, rhs)

    def test_ors_oracle_is_one(self):
        res = pcme.evaluate(self.panel, B=50, oracle="s3")
        self.assertAlmostEqual(res["systems"]["s3"]["ors"]["point"], 1.0, places=9)

    def test_prior_directed_deletion_biases_pcs_not_cpr(self):
        """A3 violated: guessable items dropped more. Raw accuracy barely moves; CPR stays on target."""
        d, r, truth, g = simulate(R_sys=(0.6,), prior_directed=0.5, seed=3)
        panel = pcme.Panel(r, pcme.Prior(d, "reader"), "F")
        res = pcme.evaluate(panel, B=50)
        self.assertAlmostEqual(res["systems"]["s0"]["cpr"]["point"], truth["s0"]["R_res"], delta=0.03)
        self.assertGreater(truth["s0"]["R_res"] - truth["s0"]["R"], 0.1)    # overall retention is lower
        self.assertGreater(res["systems"]["s0"]["pcs"]["point"] - truth["s0"]["R"], 0.05)   # PCS != overall R when A3 fails

    def test_two_stage_ci_wider(self):
        a = pcme.evaluate(self.panel, B=300, two_stage=False)["systems"]["s1"]["pcs"]["ci"]
        b = pcme.evaluate(self.panel, B=300, two_stage=True)["systems"]["s1"]["pcs"]["ci"]
        self.assertGreaterEqual(b[1] - b[0], (a[1] - a[0]) * 0.95)


class TestPriorAndPanel(unittest.TestCase):
    def test_union_strata_and_reader_g(self):
        draws = [dict(id="a", model="m1", draw="x", correct=0.0), dict(id="a", model="m2", draw="x", correct=1.0),
                 dict(id="b", model="m1", draw="x", correct=0.0), dict(id="b", model="m1", draw="y", correct=1.0),
                 dict(id="c", model="m1", draw="x", correct=0.0), dict(id="c", model="m2", draw="x", correct=0.0)]
        p = pcme.Prior(draws, "m1")
        self.assertEqual(p.g, {"a": 0.0, "b": 0.5, "c": 0.0})
        self.assertEqual(p.resistant, {"a": False, "b": False, "c": True})     # a: guessed by the other model
        p2 = pcme.Prior(draws, "m1", strata_models=["m1"])
        self.assertTrue(p2.resistant["a"])

    def test_panel_alignment_drops_missing(self):
        draws = [dict(id=i, model="m", draw="x", correct=0.0) for i in "abc"]
        runs = [dict(id=i, system="s", correct=1.0, protocol="F", cluster="u", answerable=True, abstained=None) for i in "abc"] + \
               [dict(id=i, system="t", correct=0.0, protocol="F", cluster="u", answerable=True, abstained=None) for i in "ab"] + \
               [dict(id="d", system="t", correct=0.0, protocol="F", cluster="u", answerable=False, abstained=True)]
        panel = pcme.Panel(runs, pcme.Prior(draws, "m"), "F")
        self.assertEqual(panel.ids, ["a", "b"])
        self.assertEqual(panel.dropped, {"s": 1, "t": 0})

    def test_loaders_adapt_repo_formats(self):
        with tempfile.TemporaryDirectory() as td:
            cb = Path(td) / "closed_book_modelx.jsonl"
            cb.write_text("\n".join(json.dumps(r) for r in [
                dict(id="q1", proto="natural", correct=True), dict(id="q1", proto="forced", correct=True),
                dict(id="q2", proto="forced", correct=False), dict(id="q3", proto="forced", correct=None)]))
            d = pcme.load_prior([str(cb)])
            self.assertEqual([(x["id"], x["model"], x["correct"]) for x in d], [("q1", "modelx", 1.0), ("q2", "modelx", 0.0)])
            rs = Path(td) / "rescore_x.jsonl"
            rs.write_text(json.dumps(dict(id="q1", system="s", correct=True, episode="e1", abstention=False)) + "\n" +
                          json.dumps(dict(id="q9", system="s", correct=False, episode="e1", abstention=True)))
            r = pcme.load_runs([str(rs)])
            self.assertEqual([(x["cluster"], x["answerable"], x["protocol"]) for x in r], [("e1", True, "A"), ("e1", False, "A")])


class TestInference(unittest.TestCase):
    def test_bootstrap_weights_shapes(self):
        W = pcme.bootstrap_weights(50, B=100)
        self.assertEqual(W.shape, (100, 50)); np.testing.assert_allclose(W.sum(1), 50)
        cl = np.array([i // 10 for i in range(50)])
        Wc = pcme.bootstrap_weights(50, B=100, clusters=cl)
        np.testing.assert_allclose(Wc.sum(1), 50)                        # equal-size clusters
        for b in range(5):                                               # constant within cluster
            for c in range(5):
                self.assertEqual(len(set(Wc[b, cl == c])), 1)

    def test_bootstrap_coverage(self):
        rng = np.random.default_rng(7)
        hits = 0
        for t in range(200):
            y = (rng.random(300) < 0.3).astype(float)
            W = pcme.bootstrap_weights(300, B=400, seed=t)
            lo, hi = pcme.ci(pcme.acc(y, W))
            hits += lo <= 0.3 <= hi
        self.assertTrue(0.90 <= hits / 200 <= 0.99, hits)

    def test_kendall_spearman(self):
        self.assertAlmostEqual(pcme.kendall_tau_b([1, 2, 3, 4], [1, 2, 3, 4]), 1.0)
        self.assertAlmostEqual(pcme.kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        # with ties: x = [1,2,2,3], y = [1,2,3,4] -> concordant 5, discordant 0, ties in x 1 -> 5/sqrt(5*6)
        self.assertAlmostEqual(pcme.kendall_tau_b([1, 2, 2, 3], [1, 2, 3, 4]), 5 / np.sqrt(30))
        self.assertAlmostEqual(pcme.spearman([1, 2, 3], [3, 2, 1]), -1.0)

    def test_holm(self):
        np.testing.assert_allclose(pcme.holm([0.01, 0.04, 0.03, 0.005]), [0.03, 0.06, 0.06, 0.02])

    def test_signflip(self):
        rng = np.random.default_rng(0)
        self.assertLess(pcme.signflip_test(rng.normal(0.5, 1, 200)), 0.001)
        self.assertGreater(pcme.signflip_test(rng.normal(0.0, 1, 200)), 0.01)

    def test_tost_verdicts(self):
        rng = np.random.default_rng(0)
        self.assertEqual(pcme.tost(0.0, rng.normal(0, 0.005, 2000), 0.03)["verdict"], "equivalent")
        self.assertEqual(pcme.tost(0.1, rng.normal(0.1, 0.01, 2000), 0.03)["verdict"], "not equivalent")
        self.assertEqual(pcme.tost(0.02, rng.normal(0.02, 0.03, 2000), 0.03)["verdict"], "inconclusive")

    def test_confirmed_reversal(self):
        raw = {("a", "b"): (0.1, (0.05, 0.15)), ("a", "c"): (0.1, (0.05, 0.15))}
        new = {("a", "b"): (-0.1, (-0.15, -0.05)), ("a", "c"): (-0.1, (-0.2, 0.01))}
        conf, unres = pcme.confirmed_reversals(raw, new)
        self.assertEqual(conf, [("a", "b")]); self.assertEqual(unres, [("a", "c")])

    def test_unidentified_stats_omitted_off_forced_protocol(self):
        d, r, _, _ = simulate(n=200, R_sys=(0.5,))
        r = [dict(x, protocol="A") for x in r]
        res = pcme.evaluate(pcme.Panel(r, pcme.Prior(d, "reader"), "A"), B=20)
        self.assertEqual(set(k for k in res["systems"]["s0"] if not k.startswith("2x2")), {"acc", "cpr"})

    def test_abstention_all_abstain_gets_zero_J(self):
        self.assertEqual(pcme.abstention([1, 1, 1], [1, 1])["J"], 0.0)


if __name__ == "__main__":
    unittest.main()
