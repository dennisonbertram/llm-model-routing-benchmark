"""Repair pass for Fugu cells contaminated by rate limits.

fugu-ultra hits sustained HTTP 429 under concurrency, and the matrix records a 429 as a WRONG
answer (ans=None) — which would understate Fugu's real accuracy. This pass purges every fugu /
fugu-ultra cell that errored or has no answer, then re-measures ONLY those SERIALLY (one request at
a time) with long exponential backoff and a pause between calls, so Fugu gets a clean capability
measurement. Re-run until '0 to repair'.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
from providers import chat as live_chat, ProviderError  # noqa: E402
import matrix as MX  # noqa: E402
import suites as SU  # noqa: E402

MATRIX = os.path.join(HERE, "matrix_superhard.json")
MODELS = ["fugu", "fugu-ultra"]
BASE_SLEEP = 3.0          # pause between calls, to stay under the rate limit
BACKOFF = [8, 16, 32, 64, 90]  # on 429/5xx, wait this long and retry (serial)


def call(model, prompt):
    mt = MX.max_tokens_for(model)
    for i, wait in enumerate([0] + BACKOFF):
        if wait:
            print(f"    backoff {wait}s (attempt {i})", flush=True)
            time.sleep(wait)
        try:
            return live_chat(model, [{"role": "user", "content": prompt}], max_tokens=mt,
                             temperature=0.0, timeout=300, retries=0)
        except ProviderError as e:
            if any(s in str(e) for s in ("429", "500", "502", "503", "529")) and i < len(BACKOFF):
                continue
            raise
    raise ProviderError("exhausted backoff")


def main():
    tasks = SU.load("superhard")
    by_id = {t["id"]: t for t in tasks}
    m = MX.load(MATRIX)
    bad = [(mid, tid) for mid in MODELS for tid in list(m.get(mid, {}))
           if m[mid][tid].get("ans") is None or "err" in m[mid][tid]]
    print(f"[repair] {len(bad)} contaminated cells to re-measure (serial)", flush=True)
    for mid in MODELS:
        ok = sum(c["ok"] for c in m.get(mid, {}).values())
        print(f"  before: {mid} {ok}/{len(m.get(mid,{}))} ok", flush=True)
    if not bad:
        print("[repair] nothing to repair", flush=True)
        return

    spent = 0.0
    for n, (mid, tid) in enumerate(bad, 1):
        t = by_id[tid]
        try:
            r = call(mid, t["prompt"])
            rec = {"ans": MX.last_int(r["text"]), "ok": int(bool(t["grade"](r["text"]))),
                   "usd": r["usd"], "lat": r.get("latency_ms", 0)}
            spent += r["usd"]
            tag = "ok" if rec["ok"] else "wrong"
            print(f"[repair] {n}/{len(bad)} {mid:10s} {tid} ans={rec['ans']} {tag} "
                  f"${spent:.3f} {rec['lat']}ms", flush=True)
        except Exception as e:
            rec = {"ans": None, "ok": 0, "usd": 0.0, "lat": 0, "err": str(e)[:60]}
            print(f"[repair] {n}/{len(bad)} {mid:10s} {tid} STILL FAILED: {str(e)[:50]}", flush=True)
        m[mid][tid] = rec
        MX.save(MATRIX, m)
        time.sleep(BASE_SLEEP)

    print("[repair] done. after:", flush=True)
    for mid in MODELS:
        ok = sum(c["ok"] for c in m[mid].values())
        err = sum(1 for c in m[mid].values() if "err" in c or c.get("ans") is None)
        cpt = sum(c["usd"] for c in m[mid].values()) / max(1, len(m[mid]))
        print(f"  {mid}: {ok}/{len(m[mid])} ok, {err} still-bad, ${cpt:.5f}/task", flush=True)


if __name__ == "__main__":
    main()
