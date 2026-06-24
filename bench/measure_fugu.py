"""Measure Sakana Fugu (fugu, fugu-ultra) on the superhard suite, gently.

The main matrix (matrix.py) calls every model with retries=0 and a short timeout, and records a
timeout / 429 as a WRONG answer. That is correct for fast OpenAI/OpenRouter models but would
*contaminate* Fugu: the conductor is slow (multi-agent orchestration, ~5x latency) and rate-limited,
so a tolerant no-answer would understate its real accuracy. This script gives Fugu its best shot —
long timeout, retries with backoff, low concurrency — then writes clean cells into the shared matrix
so Fugu participates in every offline combination (solo / vote / consensus-escalate / oracle).

Idempotent + resumable: already-measured (model, task) cells are skipped.
"""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
from providers import chat as live_chat  # noqa: E402

import matrix as MX  # noqa: E402
import suites as SUITES  # noqa: E402

MATRIX_PATH = os.path.join(HERE, "matrix_superhard.json")
MODELS = ["fugu", "fugu-ultra"]
TIMEOUT = 300
RETRIES = 2
WORKERS = 3          # Fugu rate-limits aggressively; keep concurrency low
_lock = threading.Lock()


def main():
    tasks = SUITES.load("superhard")
    m = MX.load(MATRIX_PATH)
    for mid in MODELS:
        m.setdefault(mid, {})
    todo = [(mid, t) for mid in MODELS for t in tasks if t["id"] not in m[mid]]
    print(f"[fugu] {len(todo)} cells to measure ({MODELS} x {len(tasks)} tasks); "
          f"have {sum(len(m[x]) for x in MODELS)} already", flush=True)
    if not todo:
        print("[fugu] nothing to do", flush=True)
        return

    spent = [sum(c.get("usd", 0.0) for x in MODELS for c in m[x].values())]
    done = [0]

    def one(mid, t):
        mt = MX.max_tokens_for(mid)
        try:
            r = live_chat(mid, [{"role": "user", "content": t["prompt"]}], max_tokens=mt,
                          temperature=0.0, timeout=TIMEOUT, retries=RETRIES)
            return mid, t["id"], {"ans": MX.last_int(r["text"]),
                                  "ok": int(bool(t["grade"](r["text"]))),
                                  "usd": r["usd"], "lat": r.get("latency_ms", 0)}
        except Exception as e:
            return mid, t["id"], {"ans": None, "ok": 0, "usd": 0.0, "lat": 0, "err": str(e)[:60]}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(one, mid, t): (mid, t["id"]) for mid, t in todo}
        for fu in as_completed(futs):
            mid, tid, rec = fu.result()
            with _lock:
                m[mid][tid] = rec
                spent[0] += rec["usd"]
                done[0] += 1
                tag = "ok" if rec["ok"] else ("ERR:" + rec.get("err", "")[:30] if "err" in rec else "wrong")
                print(f"[fugu] {done[0]:3d}/{len(todo)}  {mid:10s} {tid}  ans={rec['ans']} {tag}  "
                      f"${spent[0]:.3f}  {rec['lat']}ms", flush=True)
                if done[0] % 5 == 0:
                    MX.save(MATRIX_PATH, m)
    MX.save(MATRIX_PATH, m)
    for mid in MODELS:
        ok = sum(c["ok"] for c in m[mid].values())
        err = sum(1 for c in m[mid].values() if "err" in c)
        cpt = sum(c["usd"] for c in m[mid].values()) / max(1, len(m[mid]))
        print(f"[fugu] DONE {mid}: {ok}/{len(m[mid])} correct, {err} errored, ${cpt:.5f}/task", flush=True)


if __name__ == "__main__":
    main()
