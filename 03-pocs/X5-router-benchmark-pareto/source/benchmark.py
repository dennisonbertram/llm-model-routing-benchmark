"""X5 — RouterBench-style cost-vs-quality benchmark.

Runs every router over a shared evaluation and emits the cost-quality Pareto frontier. Following
RouterBench methodology, routers that only CHOOSE between cheap (gpt-4o-mini) and strong (gpt-4.1)
are evaluated over the LIVE-MEASURED OUTCOME MATRIX (each model's real correctness+cost per task,
from L0) — this is exact and reproducible. Predictive routers (kNN, logistic) use 5-fold
cross-validation so every task is held-out exactly once (no train/test leakage). Embeddings are
computed live. Ensemble routers (Mixture-of-Agents, self-consistency) are measured with fresh live
calls and added as reference points.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 benchmark.py
"""
import json
import os
import re
import sys

import warnings

import numpy as np

# numpy 2.0 on macOS Accelerate emits spurious "divide by zero encountered in matmul"
# RuntimeWarnings even for clean unit-norm inputs; the results are correct. Silence the noise.
warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
np.seterr(divide="ignore", over="ignore", invalid="ignore")

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
import judge  # noqa: E402
from cache import Cache  # noqa: E402
from embed_util import get_embeddings  # noqa: E402  (local helper, below)
from metrics import format_table, pareto_front  # noqa: E402

HERE = os.path.dirname(__file__)
MATRIX = json.load(open(os.path.join(HARNESS, ".cache", "labelset_export.json")))
BYID = {r["id"]: r for r in MATRIX}
IDS = [it["id"] for it in tasks.ALL]
CACHE = Cache(os.path.join(HERE, ".cache.json"))


# ---------------- outcome-matrix routers (decide cheap|strong per task) ----------------
def eval_decisions(decide):
    """decide(item_id) -> 'cheap'|'strong'. Returns (accuracy, total_usd, pct_cheap)."""
    nc = cost = cheapn = 0
    for tid in IDS:
        c = decide(tid)
        row = BYID[tid]
        nc += row[c + "_correct"]
        cost += row[c + "_usd"]
        cheapn += (c == "cheap")
    return nc / len(IDS), cost, cheapn / len(IDS)


def row_for(name, acc, cost, pct_cheap=None, extra=""):
    r = {"router": name, "accuracy": round(acc, 4), "total_usd": round(cost, 6),
         "usd_per_correct": round(cost / (acc * len(IDS)), 6) if acc > 0 else float("inf")}
    if pct_cheap is not None:
        r["pct_cheap"] = round(pct_cheap, 3)
    if extra:
        r["note"] = extra
    return r


# heuristic features from PROMPT ONLY (no difficulty/discipline leakage)
REASON_CUES = ["how many", "ways", "probability", "in total", "consecutive", "divisible",
               "remainder", "arrange", "distinct", "combination", "permutation", "at least"]


def heuristic_decide(tid):
    p = next(it["prompt"] for it in tasks.ALL if it["id"] == tid).lower()
    score = 0
    score += sum(c in p for c in REASON_CUES)
    score += 1 if len(re.findall(r"\d+", p)) >= 3 else 0
    score += 1 if len(p) > 160 else 0
    return "strong" if score >= 2 else "cheap"


# ---------------- logistic regression (numpy) ----------------
def train_logreg(X, y, iters=400, lr=0.5, l2=1e-3):
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(iters):
        z = X @ w + b
        p = 1 / (1 + np.exp(-z))
        gw = X.T @ (p - y) / n + l2 * w
        gb = float(np.mean(p - y))
        w -= lr * gw
        b -= lr * gb
    return w, b


def predict_logreg(w, b, X):
    return 1 / (1 + np.exp(-(X @ w + b)))


def cv_folds(n, k=5, seed=0):
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)
    return [idx[i::k] for i in range(k)]


def main():
    print("== embedding 45 prompts (live) ==")
    prompts = [it["prompt"] for it in tasks.ALL]
    E = np.array(get_embeddings(prompts, CACHE))
    cheap_ok = np.array([BYID[i]["cheap_correct"] for i in IDS], dtype=float)
    n = len(IDS)
    rows = []

    # --- baselines + oracle ---
    rows.append(row_for("always-cheap", *eval_decisions(lambda t: "cheap")))
    rows.append(row_for("always-strong", *eval_decisions(lambda t: "strong")))
    # random 50/50, averaged over 10 seeds
    accs = []
    costs = []
    for s in range(10):
        rng = np.random.RandomState(s)
        choice = {t: ("cheap" if rng.rand() < 0.5 else "strong") for t in IDS}
        a, c, _ = eval_decisions(lambda t: choice[t])
        accs.append(a)
        costs.append(c)
    rows.append(row_for("random-50%", float(np.mean(accs)), float(np.mean(costs)), 0.5,
                        "mean of 10 seeds"))
    rows.append(row_for("oracle (cheapest-correct)",
                        *eval_decisions(lambda t: "cheap" if BYID[t]["cheap_correct"]
                                        else ("strong" if BYID[t]["strong_correct"] else "cheap"))))
    rows.append(row_for("heuristic (prompt cues)", *eval_decisions(heuristic_decide)))

    # --- kNN router, 5-fold CV (vote neighbors' cheap_correct) ---
    En = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    sims = En @ En.T
    for k in (3, 5):
        pred = {}
        for fold in cv_folds(n, 5):
            train = [i for i in range(n) if i not in set(fold)]
            for i in fold:
                order = sorted(train, key=lambda j: -sims[i, j])[:k]
                vote = np.mean([cheap_ok[j] for j in order])
                pred[IDS[i]] = "cheap" if vote >= 0.5 else "strong"
        rows.append(row_for(f"kNN(k={k}) cv", *eval_decisions(lambda t: pred[t])))

    # --- logistic classifier, 5-fold CV, threshold sweep (Pareto curve) ---
    folds = cv_folds(n, 5)
    proba = np.zeros(n)
    for fold in folds:
        tr = np.array([i for i in range(n) if i not in set(fold)])
        w, b = train_logreg(E[tr], cheap_ok[tr])
        proba[fold] = predict_logreg(w, b, E[fold])
    for thr in (0.3, 0.5, 0.7, 0.9):
        # route cheap when P(cheap correct) >= thr, else strong
        decide = {IDS[i]: ("cheap" if proba[i] >= thr else "strong") for i in range(n)}
        a, c, pc = eval_decisions(lambda t: decide[t])
        rows.append(row_for(f"logistic(thr={thr})", a, c, pc))

    # --- ensemble reference points (LIVE, full suite) ---
    print("== Mixture-of-Agents (live, full suite) ==")
    moa_correct = moa_cost = 0
    for it in tasks.ALL:
        props = []
        for m in config.ENSEMBLE_CHEAP:
            r = CACHE.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=700 if it["discipline"] == "coding" else 256)
            props.append(r["text"]); moa_cost += r["usd"]
        agg = judge.aggregate_moa(it["prompt"], props, model=config.MID_DEFAULT, cache=CACHE,
                                  max_tokens=700 if it["discipline"] == "coding" else 256)
        moa_cost += agg["usd"]
        moa_correct += bool(it["grade"](agg["text"]))
    CACHE.save()
    rows.append(row_for("MoA(3 cheap)+agg", moa_correct / n, moa_cost, extra="ensemble; layer=1"))

    print("== self-consistency@5 on MATH (live) ==")
    math_items = tasks.suite("math")
    sc_correct = sc_cost = 0
    for it in math_items:
        votes = {}
        for s in range(5):
            r = CACHE.chat(config.CHEAP_DEFAULT, [{"role": "user", "content": it["prompt"]}],
                           max_tokens=256, temperature=0.7, nonce=s)
            sc_cost += r["usd"]
            ans = tasks._last_int(r["text"])
            votes[ans] = votes.get(ans, 0) + 1
        best = max(votes, key=votes.get) if votes else None
        sc_correct += (best == it["gold"])
    CACHE.save()
    # contextual: cheap-single and strong-single on the SAME math subset, from the matrix
    mcheap = sum(BYID[it["id"]]["cheap_correct"] for it in math_items)
    mstrong = sum(BYID[it["id"]]["strong_correct"] for it in math_items)
    print(f"  [math subset] self-consistency@5(cheap)={sc_correct}/{len(math_items)} "
          f"cheap-1={mcheap}/{len(math_items)} strong-1={mstrong}/{len(math_items)} sc_cost=${sc_cost:.5f}")

    # ---- report ----
    print("\n" + format_table(rows, ["router", "accuracy", "total_usd", "usd_per_correct"]))
    # The oracle is an unrealizable CEILING (it peeks at correctness). Separate it from the
    # realizable routers so the frontier reflects what an agent could actually deploy.
    realizable = [r for r in rows if not r["router"].startswith("oracle")]
    front = pareto_front(realizable)
    oracle = next(r for r in rows if r["router"].startswith("oracle"))
    strong = next(r for r in rows if r["router"] == "always-strong")
    print("\nRealizable Pareto frontier (cost-quality non-dominated, excludes the oracle ceiling):")
    for r in sorted(front, key=lambda x: x["total_usd"]):
        print(f"  {r['router']:28} acc={r['accuracy']:.3f}  ${r['total_usd']:.5f}")
    print(f"\n  ceiling  oracle                      acc={oracle['accuracy']:.3f}  ${oracle['total_usd']:.5f}  (unrealizable)")
    best = max((r for r in front if r['accuracy'] >= strong['accuracy'] - 1e-9), key=lambda x: -x['total_usd'], default=None)
    if best:
        print(f"  best realizable @ strong-accuracy: {best['router']} "
              f"({best['accuracy']:.3f} acc, ${best['total_usd']:.5f} = {strong['total_usd']/best['total_usd']:.1f}x cheaper than always-strong)")
    json.dump({"rows": rows, "frontier": [r["router"] for r in front],
               "self_consistency_math": {"sc5": sc_correct, "cheap1": int(mcheap),
                                         "strong1": int(mstrong), "n": len(math_items), "usd": round(sc_cost, 6)}},
              open(os.path.join(HERE, "benchmark_results.json"), "w"), indent=2)
    print("\nwrote benchmark_results.json  | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
