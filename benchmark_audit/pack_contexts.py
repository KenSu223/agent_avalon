"""Pack benchmark_audit/results_v2/*.jsonl (saved contexts, 600+ MB, mostly repeated text) into a git-friendly form:
    results_v2_packed/<name>.rows.jsonl.gz      every row, with "ctx" replaced by "ctx_sha256"
    results_v2_packed/<name>.contexts.json.gz   {sha256: context} for the unique contexts of that file
`python pack_contexts.py unpack` rebuilds results_v2/ byte-for-byte (rows are re-serialised with the original key order).
results_v2/ itself is gitignored.
"""
import gzip, hashlib, json, sys
from pathlib import Path
D = Path(__file__).parent
SRC, DST = D / "results_v2", D / "results_v2_packed"


def pack():
    DST.mkdir(exist_ok=True)
    tot_in = tot_out = 0
    for f in sorted(SRC.glob("*.jsonl")):
        ctxs, rows = {}, []
        raw = f.read_bytes()
        tot_in += len(raw)
        for line in raw.decode().splitlines():
            r = json.loads(line)
            if "ctx" in r:
                h = hashlib.sha256(r["ctx"].encode()).hexdigest()
                ctxs[h] = r["ctx"]
                r = {k: (h if k == "ctx" else v) for k, v in r.items()}
                r = {("ctx_sha256" if k == "ctx" else k): v for k, v in r.items()}
            rows.append(r)
        with gzip.open(DST / f"{f.stem}.rows.jsonl.gz", "wt") as g:
            for r in rows:
                g.write(json.dumps(r, default=str) + "\n")
        with gzip.open(DST / f"{f.stem}.contexts.json.gz", "wt") as g:
            json.dump(ctxs, g)
        tot_out += (DST / f"{f.stem}.rows.jsonl.gz").stat().st_size + (DST / f"{f.stem}.contexts.json.gz").stat().st_size
    print(f"packed {tot_in/1e6:.0f} MB -> {tot_out/1e6:.1f} MB")


def unpack():
    SRC.mkdir(exist_ok=True)
    for g in sorted(DST.glob("*.rows.jsonl.gz")):
        stem = g.name[:-len(".rows.jsonl.gz")]
        ctxs = json.load(gzip.open(DST / f"{stem}.contexts.json.gz", "rt"))
        with open(SRC / f"{stem}.jsonl", "w") as out:
            for line in gzip.open(g, "rt"):
                r = json.loads(line)
                r = {("ctx" if k == "ctx_sha256" else k): (ctxs[v] if k == "ctx_sha256" else v) for k, v in r.items()}
                out.write(json.dumps(r, default=str) + "\n")
    print("unpacked to", SRC)


def verify():
    """Round-trip check: unpack into memory and compare with results_v2/ line by line."""
    bad = 0
    for g in sorted(DST.glob("*.rows.jsonl.gz")):
        stem = g.name[:-len(".rows.jsonl.gz")]
        ctxs = json.load(gzip.open(DST / f"{stem}.contexts.json.gz", "rt"))
        orig = (SRC / f"{stem}.jsonl").read_text().splitlines()
        for a, line in zip(orig, gzip.open(g, "rt")):
            r = json.loads(line)
            r = {("ctx" if k == "ctx_sha256" else k): (ctxs[v] if k == "ctx_sha256" else v) for k, v in r.items()}
            bad += json.loads(a) != r
    print("round-trip mismatches:", bad)


if __name__ == "__main__":
    {"pack": pack, "unpack": unpack, "verify": verify}[sys.argv[1] if len(sys.argv) > 1 else "pack"]()
