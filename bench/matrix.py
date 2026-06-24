"""Persistent outcome matrix — the heart of the all-night benchmark.

Measure each (model, task) pair ONCE, live, and persist to matrix.json. This is the only expensive
step; every ensemble/router combination is then evaluated OFFLINE for free (combos.py).

Design (hardened from a long night of slow models, timeouts, and rate limits):
  - RESUMABLE: on restart, already-measured (model, task) pairs are skipped. Safe to Ctrl-C / re-run.
  - PARALLEL: ThreadPoolExecutor over all unmeasured pairs (I/O-bound HTTP).
  - TOLERANT: a timeout / error / rate-limit records the pair as measured with answer=None (= wrong),
    so one stalled model can't hang or corrupt the run.
  - INCREMENTAL: matrix.json is flushed every FLUSH_EVERY results, so a crash loses almost nothing.
  - BUDGET-CAPPED: stops submitting new calls once cumulative USD exceeds the cap (can't run away).

matrix[model_id][task_id] = {"ans": <extracted answer or null>, "ok": 0/1, "usd": float, "lat": ms}
"""
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HARNESS = os.path.join(os.path.dirname(__file__), "..", "harness")
sys.path.insert(0, HARNESS)
from providers import chat as live_chat  # noqa: E402

FLUSH_EVERY = 20
_lock = threading.Lock()

# Token budget. An EARLIER version gave only substring-matched "reasoners" 16000 tokens and everyone
# else 6000 -- but that asymmetry truncated non-listed models mid-answer and mismarked them wrong
# (GLM-4.7-flash produced 31 no-integer/null answers at the 6000 cap, understating its score; a Codex
# method-audit flagged this). Fix: give EVERY model the same generous budget so no model is penalised
# for truncation and the comparison is token-fair. Models that answer concisely stop early, so the
# uniform budget costs nothing extra for them; only would-be-truncated answers use more.
def max_tokens_for(model_id):
    return 16000  # uniform budget for all models (token fairness — see note above)


def last_int(text):
    n = re.findall(r"-?\d+", (text or "").replace(",", ""))
    return int(n[-1]) if n else None


def load(path):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            pass
    return {}


def save(path, m):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f)
    os.replace(tmp, path)


def measure_all(models, tasks, path, timeout=60, budget_usd=10.0, max_workers=10, log=print):
    """Fill in matrix[model][task] for every unmeasured pair, live. Returns (matrix, spent_usd)."""
    m = load(path)
    for mid in models:
        m.setdefault(mid, {})
    todo = [(mid, t) for mid in models for t in tasks if t["id"] not in m[mid]]
    spent = sum(m[mid][tid].get("usd", 0.0) for mid in m for tid in m[mid])
    log(f"[matrix] {len(todo)} pairs to measure ({len(models)} models x {len(tasks)} tasks; "
        f"already have {sum(len(v) for v in m.values())}); budget ${budget_usd}, spent ${spent:.4f}")
    if not todo:
        return m, spent

    def one(mid, t):
        mt = max_tokens_for(mid)
        try:
            r = live_chat(mid, [{"role": "user", "content": t["prompt"]}], max_tokens=mt,
                          temperature=0.0, timeout=timeout, retries=0)
            ans = last_int(r["text"])
            return mid, t["id"], {"ans": ans, "ok": int(bool(t["grade"](r["text"]))),
                                  "usd": r["usd"], "lat": r.get("latency_ms", 0)}
        except Exception as e:
            return mid, t["id"], {"ans": None, "ok": 0, "usd": 0.0, "lat": 0, "err": str(e)[:40]}

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(one, mid, t): (mid, t["id"]) for mid, t in todo}
        for fu in as_completed(futs):
            mid, tid, rec = fu.result()
            with _lock:
                m[mid][tid] = rec
                spent += rec["usd"]
                done += 1
                if done % FLUSH_EVERY == 0:
                    save(path, m)
                    log(f"[matrix] {done}/{len(todo)} measured, spent ${spent:.4f}")
                if spent >= budget_usd:
                    log(f"[matrix] BUDGET CAP ${budget_usd} hit at ${spent:.4f} — stopping new measurement")
                    # cancel the rest
                    for f2 in futs:
                        f2.cancel()
                    break
    save(path, m)
    log(f"[matrix] done: {sum(len(v) for v in m.values())} cells, spent ${spent:.4f}")
    return m, spent
