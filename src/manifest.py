"""Build and freeze the stimulus manifest: chains, measured surprise, token audit."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import load_families, build_chains, ROOT
import priors as P

RES = ROOT / "results"


def surprise_table(bt_all, key="ALL"):
    """item_id -> within-family-centred surprise on the Bradley-Terry log-odds scale."""
    out, probs = {}, {}
    for fid, v in bt_all.items():
        bt = {int(k): x for k, x in v[key].items()}
        s, p = P.surprise_from_bt(bt)
        for lvl, val in s.items():
            out[f"{fid}L{lvl}"] = val
            probs[f"{fid}L{lvl}"] = p[lvl]
    return out, probs


def local_surprise_table(p3):
    """item_id -> surprise from the LOCAL model's token logprobs. This is the write-time signal
    available to a deployed memory manager, and is what O6 pins on -- deliberately NOT the
    Bradley-Terry dose the analysis conditions on."""
    out = {}
    for fid, levels in p3.items():
        sc = {int(k): v["logprob"] for k, v in levels.items()}
        p = P.softmax_within_family(sc)
        import math
        mu = sum(-math.log(max(x, 1e-12)) for x in p.values()) / len(p)
        for lvl, pr in p.items():
            out[f"{fid}L{lvl}"] = -math.log(max(pr, 1e-12)) - mu
    return out


def token_audit(fams, model_hint="qwen3-8b"):
    """Token lengths of every level value, for the prespecified nuisance covariate."""
    import urllib.request
    out = {}
    for f in fams:
        for lv in f["levels"]:
            try:
                req = urllib.request.Request("http://127.0.0.1:8001/tokenize",
                    data=json.dumps({"model": model_hint, "prompt": lv["value"]}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as r:
                    n = len(json.loads(r.read())["tokens"])
            except Exception:
                n = len(lv["value"].split())
            out[f"{f['family_id']}L{lv['level']}"] = {
                "value": lv["value"], "n_tokens": n, "n_chars": len(lv["value"]),
                "n_words": len(lv["value"].split()),
                "has_digit": any(c.isdigit() for c in lv["value"])}
    return out


def build(dev_chains=5, conf_chains=7):
    fams = load_families()
    pri = json.loads((RES / "priors.json").read_text())
    surp, probs = surprise_table(pri["bt"])
    loc = local_surprise_table(pri["p3"])
    tok = token_audit(fams)

    dev = build_chains(fams, split="dev", n_chains=dev_chains, surprise=surp, restarts=3000)
    conf = build_chains(fams, split="confirmatory", n_chains=conf_chains, surprise=surp, restarts=3000)

    man = {"surprise_bt": surp, "prior_prob": probs, "surprise_local": loc, "token_audit": tok,
           "dev_manifest": dev, "confirmatory_manifest": conf,
           "n_dev_chains": dev_chains, "n_conf_chains": conf_chains}
    (RES / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


if __name__ == "__main__":
    m = build()
    print(f"dev: {len(m['dev_manifest']['chains'])} chains, sizes {m['dev_manifest']['chain_sizes']}, "
          f"measured-surprise gap {m['dev_manifest']['max_mean_surprise_gap']:.3f} "
          f"({m['dev_manifest']['balance_basis']})")
    print(f"conf: {len(m['confirmatory_manifest']['chains'])} chains, "
          f"sizes {m['confirmatory_manifest']['chain_sizes']}, "
          f"measured-surprise gap {m['confirmatory_manifest']['max_mean_surprise_gap']:.3f}")
    vals = list(m["surprise_bt"].values())
    print(f"surprise dose: n={len(vals)} range [{min(vals):.2f}, {max(vals):.2f}]")
    import statistics
    tk = [v["n_tokens"] for v in m["token_audit"].values()]
    print(f"token audit: value length mean {statistics.mean(tk):.1f} tokens, range {min(tk)}-{max(tk)}")
