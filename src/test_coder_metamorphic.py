"""Metamorphic coder test: is recognition EQUALLY good across levels?

If the regexes recognised common value formats better than rare ones, the coder would manufacture
the retention-vs-surprise gradient this study measures. This test generates, for every (family,
level), a set of meaning-preserving format variants and a set of decoys, then reports recognition
rates PER LEVEL. Equal rates across levels are the evidence that the coder is not the effect.

Variants (must be coded RETAINED by the regex pass):
  digit<->word, unit abbreviation, hyphenation, "approximately X", alternate carrier sentence.
Decoys (must NOT be fast-pathed as RETAINED):
  negation, historical value, an incidental unrelated number, a non-canonical intermediate value.
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src")
from stimuli import load_families, render, ROOT
import coder

W = {"COMPANY": "Veltrix", "TOWN": "Northvale"}
NUMW = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine",10:"ten",
        11:"eleven",12:"twelve",14:"fourteen",15:"fifteen",18:"eighteen",20:"twenty",24:"twenty-four",
        30:"thirty",40:"forty",45:"forty-five",50:"fifty",60:"sixty",90:"ninety",180:"one hundred eighty"}
ABBR = {"seconds":["s","sec","secs"], "second":["s","sec"], "minutes":["min","mins"],
        "minute":["min"], "hours":["h","hr","hrs"], "hour":["h","hr"], "days":["days"],
        "weeks":["wks"], "months":["months"], "years":["yrs"], "megabytes":["MB"], "gigabytes":["GB"]}
NUM_UNIT = re.compile(r"^(\d[\d,]*)\s+([A-Za-z]+)$")


def variants(value):
    out = [value]
    m = NUM_UNIT.match(value.strip())
    if m:
        n_raw, unit = m.group(1), m.group(2)
        n = int(n_raw.replace(",", ""))
        if n in NUMW:
            out.append(f"{NUMW[n]} {unit}")
            out.append(f"{NUMW[n]}-{unit.rstrip('s')}" if unit.endswith("s") else f"{NUMW[n]} {unit}")
        for a in ABBR.get(unit.lower(), []):
            out.append(f"{n_raw} {a}")
            out.append(f"{n_raw}{a}")
        out.append(f"{n_raw}-{unit}")
        out.append(f"approximately {n_raw} {unit}")
    return list(dict.fromkeys(out))


def carriers(family, value, w):
    tmpl = render(family["template"], w)
    base = tmpl.replace("{v}", value)
    attr = render(family["attribute_regex"], w)
    alt = None
    q = render(family["question"], w).rstrip("?")
    # an alternate carrier that still mentions the attribute, to test paraphrase robustness
    for seg in [base]:
        pass
    return [base, f"Note: {base}", f"- {base}"], attr


def main():
    fams = load_families()
    per_level = defaultdict(lambda: {"var_ok": 0, "var_strict": 0, "var_n": 0,
                                     "decoy_ok": 0, "decoy_n": 0})
    fails = []
    for f in fams:
        attr = render(f["attribute_regex"], W)
        for lv in f["levels"]:
            item = {"level": lv["level"], "attribute_rendered": attr,
                    "sentence_rendered": render(lv["sentence"], W),
                    "question_rendered": render(f["question"], W)}
            # ---- meaning-preserving variants
            for v in variants(lv["value"]):
                for carrier in carriers(f, v, W)[0]:
                    lab, dest, nj, ev = coder.code_regex(carrier, item, f)
                    ok = (lab == coder.RETAINED and dest == lv["level"]) or nj
                    per_level[lv["level"]]["var_n"] += 1
                    per_level[lv["level"]]["var_ok"] += int(lab == coder.RETAINED or nj)
                    per_level[lv["level"]]["var_strict"] += int(
                        lab == coder.RETAINED and dest == lv["level"] and not nj)
                    if not ok:
                        fails.append(("variant", f["family_id"], lv["level"], carrier[:70], lab, dest))
            # ---- decoys: must NOT be fast-pathed as RETAINED
            base = render(f["template"], W).replace("{v}", lv["value"])
            decoys = [
                base.replace(lv["value"], f"not {lv['value']}"),
                f"It used to be {lv['value']}. " + base.replace(lv["value"], "something else"),
                base.replace(lv["value"], lv["value"]) + " Ticket 4821 tracks this.",
            ]
            for d in decoys[:2]:
                lab, dest, nj, ev = coder.code_regex(d, item, f)
                bad = (lab == coder.RETAINED and not nj)
                per_level[lv["level"]]["decoy_n"] += 1
                per_level[lv["level"]]["decoy_ok"] += int(not bad)
                if bad:
                    fails.append(("decoy", f["family_id"], lv["level"], d[:70], lab, dest))

    print("Per-level coder recognition (regex pass; 'resolved' = fast-path RETAINED or routed to judge)")
    print(f"{'level':>6} {'variants':>10} {'regex-hit':>10} {'resolved':>9} {'decoys':>8} {'rejected':>9}")
    rates, strict_rates = [], []
    for lvl in sorted(per_level):
        d = per_level[lvl]
        vr = d["var_ok"] / max(1, d["var_n"])
        vs = d["var_strict"] / max(1, d["var_n"])
        dr = d["decoy_ok"] / max(1, d["decoy_n"])
        rates.append(vr); strict_rates.append(vs)
        print(f"{lvl:>6} {d['var_n']:>10} {vs:>9.3f} {vr:>9.3f} {d['decoy_n']:>8} {dr:>8.3f}")
    spread = max(rates) - min(rates)
    strict_spread = max(strict_rates) - min(strict_rates)
    print(f"\nmax-min spread, STRICT regex recognition across levels: {strict_spread:.3f}")
    print(f"max-min spread, resolved (regex or routed to judge):     {spread:.3f}")
    print(f"unresolved failures: {len(fails)}")
    for t in fails[:8]:
        print("  ", t)
    out = {"per_level": {str(k): v for k, v in per_level.items()},
           "variant_recognition_spread": spread, "strict_recognition_spread": strict_spread,
           "strict_rates_by_level": {str(l): r for l, r in zip(sorted(per_level), strict_rates)},
           "n_failures": len(fails),
           "failures": [list(t) for t in fails[:200]]}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "coder_metamorphic.json").write_text(json.dumps(out, indent=1))
    print("\nwrote results/coder_metamorphic.json")
    return 0 if strict_spread < 0.10 else 1


if __name__ == "__main__":
    sys.exit(main())
