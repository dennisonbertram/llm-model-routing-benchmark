"""X6b — realizable 3-tier router (cheap -> gpt-4.1 -> gpt-5.5).

Now that GPT-5.5 hits 100% on the suite, the question is: can a DEPLOYABLE router buy that
perfect accuracy without paying always-5.5 prices, by reserving GPT-5.5 for only the hard tail?

A single logistic classifier predicts P(cheap is correct) from embeddings (5-fold CV, no leakage,
same approach as X5). Two thresholds turn that one score into a 3-tier decision:
    P >= hi  -> cheap (gpt-4o-mini)
    P <= lo  -> gpt-5.5 (looks hard -> send to the frontier model)
    else     -> gpt-4.1 (the mid tier)
Accuracy/cost come from the committed live outcome matrices (cheap/gpt-4.1 from L0 labelset;
gpt-5.5 from this POC's run_x6 cache). Embeddings are live.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 x6_3tier.py
"""
import hashlib
import json
import os
import sys
import warnings

import numpy as np

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
np.seterr(all="ignore")

import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from providers import embed  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
M = {r["id"]: r for r in json.load(open(os.path.join(HARNESS, ".cache", "labelset_export.json")))}
IDS = [it["id"] for it in tasks.ALL]
_EMB = os.path.join(HERE, ".emb_cache.json")


def embeddings(prompts):
    store = json.load(open(_EMB)) if os.path.exists(_EMB) else {}
    out, todo, idx = [None] * len(prompts), [], []
    for i, t in enumerate(prompts):
        k = hashlib.sha256(("text-embedding-3-small\n" + t).encode()).hexdigest()
        if k in store: out[i] = store[k]
        else: todo.append(t); idx.append((i, k))
    if todo:
        vecs, _ = embed(todo)
        for (i, k), v in zip(idx, vecs): out[i] = v; store[k] = v
        json.dump(store, open(_EMB, "w"))
    return np.array(out)


def train(X, y, iters=500, lr=0.5, l2=1e-3):
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        w -= lr * (X.T @ (p - y) / len(y) + l2 * w); b -= lr * float(np.mean(p - y))
    return w, b


def gpt55_per_item():
    ok, usd = {}, {}
    for it in tasks.ALL:
        mt = 8000 if it["discipline"] == "coding" else 3000
        r = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}], max_tokens=mt)
        ok[it["id"]] = bool(it["grade"](r["text"])); usd[it["id"]] = r["usd"]
    return ok, usd


def main():
    X = embeddings([it["prompt"] for it in tasks.ALL])
    y = np.array([float(M[i]["cheap_correct"]) for i in IDS])
    n = len(IDS)
    # 5-fold CV out-of-fold P(cheap correct)
    rng = np.random.RandomState(0); perm = rng.permutation(n)
    folds = [perm[i::5] for i in range(5)]
    proba = np.zeros(n)
    for fold in folds:
        tr = np.array([i for i in range(n) if i not in set(fold)])
        w, b = train(X[tr], y[tr]); proba[fold] = 1 / (1 + np.exp(-(X[fold] @ w + b)))
    g55_ok, g55_usd = gpt55_per_item(); CACHE.save()

    def correct(i, tier):
        return {"cheap": M[i]["cheap_correct"], "g41": M[i]["strong_correct"], "g55": g55_ok[i]}[tier]

    def cost(i, tier):
        return {"cheap": M[i]["cheap_usd"], "g41": M[i]["strong_usd"], "g55": g55_usd[i]}[tier]

    def evaluate(hi, lo):
        nc = c = ncheap = ng41 = ng55 = 0
        for k, i in enumerate(IDS):
            p = proba[k]
            tier = "cheap" if p >= hi else ("g55" if p <= lo else "g41")
            nc += correct(i, tier); c += cost(i, tier)
            ncheap += tier == "cheap"; ng41 += tier == "g41"; ng55 += tier == "g55"
        return nc / n, c, (ncheap, ng41, ng55)

    # references
    always55 = sum(g55_usd.values())
    print("== references ==")
    print(f"  always gpt-4o-mini : acc={sum(M[i]['cheap_correct'] for i in IDS)/n:.3f}  ${sum(M[i]['cheap_usd'] for i in IDS):.5f}")
    print(f"  always gpt-4.1     : acc={sum(M[i]['strong_correct'] for i in IDS)/n:.3f}  ${sum(M[i]['strong_usd'] for i in IDS):.5f}")
    print(f"  always gpt-5.5     : acc={sum(g55_ok.values())/n:.3f}  ${always55:.5f}")
    o3 = sum((M[i]['cheap_usd'] if M[i]['cheap_correct'] else (M[i]['strong_usd'] if M[i]['strong_correct'] else g55_usd[i])) for i in IDS)
    print(f"  3-tier ORACLE      : acc=1.000  ${o3:.5f}  (unrealizable ceiling)")

    print("\n== realizable 3-tier router (CV logistic; hi/lo thresholds) ==")
    best = None
    for hi, lo in [(0.6, 0.3), (0.7, 0.4), (0.8, 0.5), (0.7, 0.5), (0.8, 0.4)]:
        a, c, (nc, n41, n55) = evaluate(hi, lo)
        print(f"  hi={hi} lo={lo}: acc={a:.3f}  ${c:.5f}  route[cheap={nc},gpt4.1={n41},gpt5.5={n55}]")
        if best is None or (a > best[2]) or (a == best[2] and c < best[1]):
            best = (f"hi={hi},lo={lo}", c, a, (nc, n41, n55))
    print(f"\n  BEST realizable 3-tier: {best[0]}  acc={best[2]:.3f}  ${best[1]:.5f} "
          f"= {always55/best[1]:.0f}x cheaper than always-gpt-5.5, {best[1]/o3:.2f}x the 3-tier oracle")
    json.dump({"best": {"cfg": best[0], "acc": best[2], "usd": round(best[1], 5),
                        "route": best[3]}, "always_gpt55_usd": round(always55, 5),
               "oracle_3tier_usd": round(o3, 5)},
              open(os.path.join(HERE, "x6_3tier_summary.json"), "w"), indent=2)
    print("wrote x6_3tier_summary.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
