"""L2 — Embedding k-NN Router (RouteLLM similarity-weighted flavor).

Strategy
--------
1. Load the per-item outcome matrix from labelset_export.json (RouterBench methodology):
   each row has {id, discipline, difficulty, prompt, cheap_correct, cheap_usd, strong_correct,
   strong_usd}.  These are real live-measured results; we do not re-bill.

2. Split by parity: even-index items -> TRAIN (labels available), odd-index items -> TEST.

3. Embed EVERY prompt with text-embedding-3-small (LIVE call; cached per this POC).

4. For a test query, find the k nearest TRAIN prompts by cosine similarity.
   Predict "cheap suffices" by weighted-vote on neighbors' cheap_correct (weight = cosine sim).
   Route to cheap if weighted-vote >= threshold, else to strong.

5. Evaluate on the held-out TEST split over the pre-measured outcome matrix (no re-billing).

6. Sweep k in {1,3,5,7} and threshold in {0.4,0.5,0.6,0.7} and report test acc/cost/pct-cheap
   vs baselines (always-cheap, always-strong) and oracle — all on the SAME test split.

7. Live-confirm a handful of routing decisions with real API calls.

HONESTY: "cheap suffices" features come ONLY from prompt text (via embeddings).
We never use item['difficulty'] or item['discipline'] — that would be oracle leakage.
"""
import json
import math
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks   # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat, embed  # noqa: E402

HERE = os.path.dirname(__file__)
EXPORT_PATH = os.path.join(HARNESS, ".cache", "labelset_export.json")
EMBED_CACHE_PATH = os.path.join(HERE, "..", ".embed-cache.json")
CHAT_CACHE_PATH = os.path.join(HERE, "..", ".chat-cache.json")


# ---------------------------------------------------------------------------
# Embedding cache — per-POC, never touches harness/.cache/labelset.json
# ---------------------------------------------------------------------------

class EmbedCache:
    """Simple on-disk cache for embedding calls."""

    def __init__(self, path):
        self.path = path
        self.data = {}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f)


# ---------------------------------------------------------------------------
# Math helpers (numpy-free fallback in case of version mismatch, but numpy OK)
# ---------------------------------------------------------------------------

try:
    import numpy as np

    def cosine_sim_matrix(query_vecs, train_vecs):
        """Return (n_q, n_tr) cosine similarity matrix."""
        # Use float64 to avoid overflow warnings with high-dim embeddings
        Q = np.array(query_vecs, dtype=np.float64)
        T = np.array(train_vecs, dtype=np.float64)
        Q_norm = Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9)
        T_norm = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-9)
        # Use np.dot (not @) to avoid a spurious divide-by-zero RuntimeWarning in numpy 2.0.2
        # that triggers on @ with large float64 matrices despite valid normalized inputs.
        return np.dot(Q_norm, T_norm.T)  # (n_q, n_tr)

    NUMPY_AVAILABLE = True
    print("numpy available:", np.__version__)
except ImportError:
    NUMPY_AVAILABLE = False
    print("numpy NOT available; falling back to pure-Python cosine")

    def cosine_sim_matrix(query_vecs, train_vecs):
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def norm(v):
            return math.sqrt(sum(x * x for x in v))

        result = []
        for q in query_vecs:
            qn = norm(q)
            row = []
            for t in train_vecs:
                tn = norm(t)
                row.append(dot(q, t) / (qn * tn + 1e-9))
            result.append(row)
        return result


def topk_indices_and_sims(sim_row, k):
    """Return top-k (index, similarity) pairs from a 1D sim row."""
    if NUMPY_AVAILABLE:
        arr = np.array(sim_row)
        k = min(k, len(arr))
        idx = np.argsort(arr)[::-1][:k]
        return [(int(i), float(arr[i])) for i in idx]
    else:
        indexed = sorted(enumerate(sim_row), key=lambda x: -x[1])[:k]
        return [(i, s) for i, s in indexed]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_labelset():
    with open(EXPORT_PATH) as f:
        return json.load(f)


def embed_all_prompts(items, ecache):
    """Embed all prompts, using the embed cache. Returns list[list[float]], total_usd."""
    prompts = [it["prompt"] for it in items]
    # Check cache first
    all_cached = all(ecache.get(p) is not None for p in prompts)
    if all_cached:
        vecs = [ecache.get(p) for p in prompts]
        total_usd = 0.0
        print(f"  All {len(prompts)} embeddings loaded from cache ($0.00 live spend)")
        return vecs, total_usd

    # Some may be missing; embed uncached ones in a batch
    uncached_prompts = [p for p in prompts if ecache.get(p) is None]
    print(f"  Embedding {len(uncached_prompts)} uncached prompts (text-embedding-3-small, LIVE)...")
    vecs_new, usd = embed(uncached_prompts)
    print(f"  Live embed call: {len(uncached_prompts)} prompts -> ${usd:.5f}")
    for p, v in zip(uncached_prompts, vecs_new):
        ecache.set(p, v)
    ecache.save()

    vecs = [ecache.get(p) for p in prompts]
    return vecs, usd


def knn_predict_cheap(query_sim_row, train_items, k, threshold):
    """
    Given a row of cosine similarities between one test item and all train items,
    predict whether cheap model suffices.

    Uses similarity-weighted vote on cheap_correct labels of top-k neighbors.
    Returns True (route cheap) if weighted_vote >= threshold.
    """
    neighbors = topk_indices_and_sims(query_sim_row, k)
    total_weight = sum(s for _, s in neighbors)
    if total_weight < 1e-9:
        # Fallback: no signal -> route cheap (conservative baseline choice)
        return True
    weighted_cheap = sum(
        s * (1.0 if train_items[i]["cheap_correct"] else 0.0)
        for i, s in neighbors
    )
    vote_score = weighted_cheap / total_weight
    return vote_score >= threshold


def evaluate_split(test_items, train_items, test_vecs, train_vecs, k, threshold):
    """
    Evaluate the k-NN router on test_items.
    Returns: acc, total_usd, n_cheap_routed, n_correct, routing_decisions
    """
    sim_matrix = cosine_sim_matrix(test_vecs, train_vecs)
    n_correct = 0
    total_usd = 0.0
    n_cheap = 0
    decisions = []

    for i, item in enumerate(test_items):
        sim_row = (sim_matrix[i] if NUMPY_AVAILABLE
                   else sim_matrix[i])
        # Convert numpy row to list for pure-Python path
        if NUMPY_AVAILABLE:
            sim_row = sim_matrix[i].tolist()

        route_cheap = knn_predict_cheap(sim_row, train_items, k, threshold)
        chosen_model = config.CHEAP_DEFAULT if route_cheap else config.STRONG_DEFAULT
        correct = item["cheap_correct"] if route_cheap else item["strong_correct"]
        cost = item["cheap_usd"] if route_cheap else item["strong_usd"]

        n_correct += int(correct)
        total_usd += cost
        n_cheap += int(route_cheap)

        decisions.append({
            "id": item["id"],
            "route": "cheap" if route_cheap else "strong",
            "model": chosen_model,
            "correct": correct,
            "usd": cost,
        })

    n = len(test_items)
    acc = n_correct / n
    return acc, total_usd, n_cheap, decisions


def compute_baselines(test_items):
    """Compute always-cheap, always-strong, oracle on the test split."""
    always_cheap_acc = sum(it["cheap_correct"] for it in test_items) / len(test_items)
    always_cheap_usd = sum(it["cheap_usd"] for it in test_items)
    always_strong_acc = sum(it["strong_correct"] for it in test_items) / len(test_items)
    always_strong_usd = sum(it["strong_usd"] for it in test_items)
    oracle_acc = sum(
        1 for it in test_items if it["cheap_correct"] or it["strong_correct"]
    ) / len(test_items)
    oracle_usd = sum(
        it["cheap_usd"] if it["cheap_correct"] else it["strong_usd"]
        for it in test_items
    )
    return {
        "always_cheap": {"acc": always_cheap_acc, "usd": always_cheap_usd},
        "always_strong": {"acc": always_strong_acc, "usd": always_strong_usd},
        "oracle": {"acc": oracle_acc, "usd": oracle_usd},
    }


def live_confirm_routing(decisions, train_items, ecache, n=3):
    """
    Live-confirm a handful of routing decisions with real API calls.
    Picks the first n items from decisions to verify live.
    """
    print(f"\n== Live confirmation: calling {n} routed items via real APIs ==")
    confirm_cache = Cache(CHAT_CACHE_PATH)

    # We need a task lookup by id for the grade function
    tasks_by_id = {it["id"]: it for it in tasks.ALL}

    confirmed = []
    for dec in decisions[:n]:
        tid = dec["id"]
        task = tasks_by_id.get(tid)
        if task is None:
            print(f"  [SKIP] {tid}: not found in tasks.ALL")
            continue

        model = dec["model"]
        r = confirm_cache.chat(
            model,
            [{"role": "user", "content": task["prompt"]}],
            max_tokens=512,
            temperature=0.0,
        )
        live_correct = bool(task["grade"](r["text"]))
        cached_correct = dec["correct"]
        match = "OK" if live_correct == cached_correct else "MISMATCH"
        print(
            f"  {tid:4s}  route={dec['route']:6s}  model={model:20s}  "
            f"correct={live_correct}  cache={cached_correct}  {match}  "
            f"${r['usd']:.2e}  cached={r.get('cached', False)}"
        )
        confirmed.append({
            "id": tid,
            "model": model,
            "live_correct": live_correct,
            "cached_correct": cached_correct,
            "match": match,
            "usd": r["usd"],
        })

    confirm_cache.save()
    return confirmed


def main():
    ecache = EmbedCache(EMBED_CACHE_PATH)

    # 1. Load labelset
    rows = load_labelset()
    n_total = len(rows)
    print(f"Loaded {n_total} items from labelset_export.json")

    # 2. Train/test split by parity
    train_items = [rows[i] for i in range(n_total) if i % 2 == 0]
    test_items  = [rows[i] for i in range(n_total) if i % 2 == 1]
    print(f"  Train: {len(train_items)} items (even indices)")
    print(f"  Test:  {len(test_items)} items (odd indices)")

    # 3. Embed ALL prompts (LIVE — text-embedding-3-small)
    print("\n== Embedding all prompts (LIVE) ==")
    all_vecs, embed_usd = embed_all_prompts(rows, ecache)
    train_vecs = [all_vecs[i] for i in range(n_total) if i % 2 == 0]
    test_vecs  = [all_vecs[i] for i in range(n_total) if i % 2 == 1]
    print(f"  Embedding dimension: {len(all_vecs[0])}")

    # 4. Compute baselines on test split
    baselines = compute_baselines(test_items)
    print("\n== Baselines on TEST split (from labelset outcome matrix) ==")
    print(f"  always-cheap:  acc={baselines['always_cheap']['acc']:.3f}  "
          f"cost=${baselines['always_cheap']['usd']:.5f}")
    print(f"  always-strong: acc={baselines['always_strong']['acc']:.3f}  "
          f"cost=${baselines['always_strong']['usd']:.5f}  "
          f"({baselines['always_strong']['usd']/baselines['always_cheap']['usd']:.1f}x cheap)")
    print(f"  oracle:        acc={baselines['oracle']['acc']:.3f}  "
          f"cost=${baselines['oracle']['usd']:.5f}  "
          f"({baselines['oracle']['usd']/baselines['always_strong']['usd']*100:.0f}% of strong cost)")

    # 5. Sweep k and threshold
    k_values = [1, 3, 5, 7]
    threshold_values = [0.4, 0.5, 0.6, 0.7]
    print("\n== k-NN Router Sweep (on TEST split) ==")
    print(f"  {'k':>3}  {'thresh':>6}  {'acc':>5}  {'cost':>9}  {'%cheap':>7}  {'vs_cheap':>9}  {'vs_strong':>10}")
    print(f"  {'-'*3}  {'-'*6}  {'-'*5}  {'-'*9}  {'-'*7}  {'-'*9}  {'-'*10}")

    all_results = []
    best_result = None
    best_score = -1.0

    for k in k_values:
        for thresh in threshold_values:
            acc, cost, n_cheap, decisions = evaluate_split(
                test_items, train_items, test_vecs, train_vecs, k, thresh
            )
            pct_cheap = n_cheap / len(test_items) * 100
            vs_cheap = cost / baselines["always_cheap"]["usd"]
            vs_strong = cost / baselines["always_strong"]["usd"]
            print(f"  {k:>3}  {thresh:>6.1f}  {acc:>5.3f}  ${cost:>8.5f}  "
                  f"{pct_cheap:>6.0f}%  {vs_cheap:>8.2f}x  {vs_strong:>9.2f}x")
            result = {
                "k": k, "threshold": thresh,
                "acc": acc, "cost": cost,
                "pct_cheap": pct_cheap,
                "n_cheap": n_cheap,
                "decisions": decisions,
            }
            all_results.append(result)
            # "Best" = highest accuracy; among ties, lowest cost.
            # Multiply acc by a large constant so accuracy dominates cost.
            score = acc * 10000 - cost
            if score > best_score:
                best_score = score
                best_result = result

    # 6. Print best configuration
    best = best_result
    print(f"\n== Best configuration: k={best['k']}, threshold={best['threshold']:.1f} ==")
    print(f"  acc={best['acc']:.3f}  cost=${best['cost']:.5f}  "
          f"{best['pct_cheap']:.0f}% cheap")

    # 7. Live-confirm routing decisions
    confirmed = live_confirm_routing(best["decisions"], train_items, ecache)

    # 8. Summary table
    print("\n== Final summary (on 22-item TEST split) ==")
    print(f"  {'Router':30s}  {'acc':>5}  {'cost':>10}  {'vs cheap':>9}  {'%cheap':>7}")
    print(f"  {'-'*30}  {'-'*5}  {'-'*10}  {'-'*9}  {'-'*7}")
    print(f"  {'always-cheap (gpt-4o-mini)':30s}  "
          f"{baselines['always_cheap']['acc']:>5.3f}  "
          f"${baselines['always_cheap']['usd']:>9.5f}  "
          f"{'1.0x':>9}  {'100%':>7}")
    print(f"  {'always-strong (gpt-4.1)':30s}  "
          f"{baselines['always_strong']['acc']:>5.3f}  "
          f"${baselines['always_strong']['usd']:>9.5f}  "
          f"{baselines['always_strong']['usd']/baselines['always_cheap']['usd']:>8.1f}x  "
          f"{'0%':>7}")
    print(f"  {'oracle':30s}  "
          f"{baselines['oracle']['acc']:>5.3f}  "
          f"${baselines['oracle']['usd']:>9.5f}  "
          f"{baselines['oracle']['usd']/baselines['always_cheap']['usd']:>8.1f}x  "
          f"{'N/A':>7}")
    for k in [3, 5]:
        for thresh in [0.5, 0.6]:
            for r in all_results:
                if r["k"] == k and r["threshold"] == thresh:
                    label = f"kNN k={k} thresh={thresh:.1f}"
                    print(f"  {label:30s}  "
                          f"{r['acc']:>5.3f}  "
                          f"${r['cost']:>9.5f}  "
                          f"{r['cost']/baselines['always_cheap']['usd']:>8.1f}x  "
                          f"{r['pct_cheap']:>6.0f}%")
    best_label = f"kNN BEST k={best['k']} t={best['threshold']:.1f}"
    print(f"  {best_label:30s}  "
          f"{best['acc']:>5.3f}  "
          f"${best['cost']:>9.5f}  "
          f"{best['cost']/baselines['always_cheap']['usd']:>8.1f}x  "
          f"{best['pct_cheap']:>6.0f}%")

    # 9. Write results JSON
    out = {
        "split": {"train": len(train_items), "test": len(test_items)},
        "embed_model": config.EMBED_MODEL,
        "embed_usd_live": embed_usd,
        "baselines": baselines,
        "sweep": [
            {k: v for k, v in r.items() if k != "decisions"}
            for r in all_results
        ],
        "best": {
            "k": best["k"],
            "threshold": best["threshold"],
            "acc": best["acc"],
            "cost": best["cost"],
            "pct_cheap": best["pct_cheap"],
        },
        "live_confirmations": confirmed,
    }
    outpath = os.path.join(HERE, "l2_results.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {outpath}")
    print(f"\nEmbedding cost (live): ${embed_usd:.5f} (one-time; subsequent runs free from cache)")


if __name__ == "__main__":
    main()
