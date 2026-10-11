"""Threshold-triggered compaction (METHOD.md §10.6): a realistic trigger for the product compaction adapters.

The main design compacts after every ingested session/chunk. Real products compact only when the live context gets
close to a limit. This wrapper keeps the uncompacted turns verbatim and calls the wrapped adapter's own compaction
(verbatim prompt + framing) on ALL uncompacted turns at once, only when
    estimated tokens(current summary + uncompacted turns) > T,      estimated tokens = characters / 4.
Question-time context = summary + blank line + TAIL_HEADER + uncompacted turns as "{role}: {content}" lines.
With base=None it is the uncompacted full history (no header).
System names: "<adapter>@thr64k" (T = 64,000) and "full_history".
"""
TAIL_HEADER = "[Recent conversation, not yet compacted]"


def est_tokens(text):
    return len(text) / 4


class ThresholdCompaction:
    def __init__(self, base, threshold_tokens):
        self.base, self.T = base, threshold_tokens
        self.buf = []
        self.n_compactions = 0

    def _summary(self):
        return self.base.dump() if self.base is not None else ""

    def ingest(self, msgs):
        self.buf += msgs
        if self.base is None:
            return
        live = est_tokens(self._summary()) + sum(est_tokens(m["content"]) for m in self.buf)
        if live > self.T:
            self.base.ingest(self.buf)
            self.buf = []
            self.n_compactions += 1

    def _tail(self):
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.buf)

    def dump(self):
        if self.base is None:
            return self._tail()
        summ, tail = self._summary(), self._tail()
        parts = [p for p in (summ, f"{TAIL_HEADER}\n{tail}" if tail else "") if p]
        return "\n\n".join(parts)

    def context(self, question):
        return self.dump()


def make(system, adapters, model):
    """'codex@thr64k' -> ThresholdCompaction(Codex, 64000); 'full_history' -> ThresholdCompaction(None, inf)."""
    if system == "full_history":
        return ThresholdCompaction(None, float("inf"))
    base, thr = system.split("@thr")
    return ThresholdCompaction(adapters[base](model, temperature=0.0), int(thr.rstrip("k")) * 1000)
