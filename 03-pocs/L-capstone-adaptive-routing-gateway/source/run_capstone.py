"""Capstone driver:
  (1) HONEST benchmark of the AdaptiveRouter's decisions over the 45-task suite with 5-fold CV
      (no leakage), scored on the L0 outcome matrix -> where it lands on the realizable frontier.
  (2) LIVE behavior demos: budget-guard tripping, and provider-error fallback.
The OpenAI-compatible HTTP runtime is exercised separately via gateway_server.py + curl (commands.md).
"""
import json
import os
import sys
import warnings

import numpy as np

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
np.seterr(all="ignore")

import config  # noqa: E402
from adaptive_router import _embed_cached, _train_logreg, AdaptiveRouter  # noqa: E402

MATRIX = json.load(open(os.path.join(HARNESS, ".cache", "labelset_export.json")))
BYID = {r["id"]: r for r in MATRIX}
IDS = [r["id"] for r in MATRIX]


def cv_benchmark(threshold=0.6, k=5, seed=0):
    """5-fold CV: train the classifier on train folds, decide on test fold, score from the matrix."""
    X = np.array(_embed_cached([BYID[i]["prompt"] for i in IDS]))
    y = np.array([float(BYID[i]["cheap_correct"]) for i in IDS])
    n = len(IDS)
    rng = np.random.RandomState(seed)
    perm = rng.permutation(n)
    folds = [perm[i::k] for i in range(k)]
    decide = {}
    for fold in folds:
        tr = np.array([i for i in range(n) if i not in set(fold)])
        w, b = _train_logreg(X[tr], y[tr])
        for i in fold:
            p = float(1 / (1 + np.exp(-(X[i] @ w + b))))
            decide[IDS[i]] = "cheap" if p >= threshold else "strong"
    nc = cost = cheapn = 0
    for tid in IDS:
        c = decide[tid]
        nc += BYID[tid][c + "_correct"]; cost += BYID[tid][c + "_usd"]; cheapn += (c == "cheap")
    return nc / n, cost, cheapn / n


def main():
    print("== (1) Adaptive router — honest 5-fold CV benchmark over 45 tasks ==")
    ac = sum(BYID[i]["cheap_correct"] for i in IDS) / len(IDS)
    acost = sum(BYID[i]["cheap_usd"] for i in IDS)
    sc = sum(BYID[i]["strong_correct"] for i in IDS) / len(IDS)
    scost = sum(BYID[i]["strong_usd"] for i in IDS)
    # Oracle = cheapest model that is CORRECT; for an unsolvable item charge the cheap model
    # (don't pay for a strong call that also fails). Matches L0/X5's oracle definition.
    ocost = sum((BYID[i]["cheap_usd"] if BYID[i]["cheap_correct"]
                 else (BYID[i]["strong_usd"] if BYID[i]["strong_correct"] else BYID[i]["cheap_usd"])) for i in IDS)
    print(f"  always-cheap : acc={ac:.3f}  ${acost:.5f}")
    print(f"  always-strong: acc={sc:.3f}  ${scost:.5f}")
    print(f"  oracle ceil  : acc={sc:.3f}  ${ocost:.5f}")
    best = None
    for thr in (0.5, 0.6, 0.7, 0.8, 0.9):
        a, c, pc = cv_benchmark(threshold=thr)
        flag = ""
        if a >= sc - 1e-9 and (best is None or c < best[1]):
            best = (thr, c, a)
            flag = "  <- matches strong accuracy"
        print(f"  adaptive(thr={thr}): acc={a:.3f}  ${c:.5f}  pct_cheap={pc:.0%}{flag}")
    if best:
        print(f"\n  BEST adaptive @ strong-accuracy: thr={best[0]}  acc={best[2]:.3f}  ${best[1]:.5f}  "
              f"= {scost/best[1]:.1f}x cheaper than always-strong, {best[1]/ocost:.2f}x the oracle cost")

    print("\n== (2a) LIVE budget guard (cap chosen just above ~2 strong calls) ==")
    r = AdaptiveRouter(threshold=0.6, budget_usd=0.00025)
    hard = "How many ways are there to make 100 cents using pennies, nickels, dimes, and quarters? Reply with just the number."
    for i in range(6):
        out = r.answer(hard)
        e = out["entry"]
        print(f"  req{i+1}: served={e['served_model']:11} decision={e['decision'][:40]:40} spent=${e['total_spent']:.4f}")
    guarded = [e for e in r.ledger if "budget_guard" in e["decision"]]
    print(f"  -> budget guard engaged on {len(guarded)} request(s) after the ${r.budget_usd} cap")

    print("\n== (2b) LIVE provider fallback (bad primary -> fallback) ==")
    rf = AdaptiveRouter(threshold=0.6, fallback=config.CHEAP_DEFAULT)
    rf.strong = "gpt-4.1-NONEXISTENT-xyz"  # force the strong route to a bad slug
    out = rf.answer(hard)  # hard prompt routes to (bad) strong -> should fall back
    e = out["entry"]
    print(f"  served={e['served_model']}  fallback_from={'yes' if e['fallback_from'] else 'no'}  answer={out['text'][:40]!r}")

    print("\nDONE")


if __name__ == "__main__":
    main()
