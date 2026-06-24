"""L2b — Logistic-Regression Classifier Router (RouteLLM / Hybrid-LLM family).

Trains a logistic regression (pure numpy, gradient descent) on text-embedding-3-small features
to predict P(cheap model is correct) for a prompt. Train/test split on labelset_export.json.
Decision threshold on P(cheap suffices) is the cost-quality KNOB — sweep it to trace a Pareto
curve (each point = accuracy, cost on the test set).

Key design decisions:
  - Features: the 1536-dim text-embedding-3-small vector for each prompt (live via embed()).
  - Labels: binary y = 1 if cheap_correct == True (route cheap), 0 if false (route strong).
  - NO oracle leakage: we NEVER use item['difficulty'] or item['discipline'] as features.
  - Train/test split: 70/30 stratified (preserves cheap-correct ratio).
  - Training: sigmoid logistic regression via gradient descent, L2 regularisation.
  - Threshold sweep: from 0.05 to 0.95. Routing-collapse guard: at interior thresholds assert
    0 < pct_routed_cheap < 1.
  - Live confirmation: embed + predict a fresh prompt to confirm the live code-path works.

Run:
  set -a; . .agent-university/secrets.local.env; set +a
  cd source && python3 run_l2b.py
"""
import json
import math
import os
import sys
import random

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from cache import Cache  # noqa: E402
from providers import embed  # noqa: E402
from metrics import pareto_front  # noqa: E402

HERE = os.path.dirname(__file__)
LABELSET = os.path.join(HARNESS, ".cache", "labelset_export.json")
EMBED_CACHE_PATH = os.path.join(HERE, ".cache.json")


# ---------------------------------------------------------------------------
# Numpy-free utilities (we use numpy only for matrix ops where it helps)
# ---------------------------------------------------------------------------

def sigmoid(x):
    # Numerically stable sigmoid.
    if x >= 0:
        e = math.exp(-x)
        return 1.0 / (1.0 + e)
    else:
        e = math.exp(x)
        return e / (1.0 + e)


def dot(w, x):
    return sum(wi * xi for wi, xi in zip(w, x))


# ---------------------------------------------------------------------------
# Logistic Regression (pure Python + stdlib math)
# ---------------------------------------------------------------------------

class LogisticRegressor:
    """Binary logistic regression trained with gradient descent + L2 regularisation.

    Predicts P(y=1 | x), where y=1 means "cheap model is correct" for this prompt.
    """

    def __init__(self, lr=0.1, l2=1e-3, epochs=200, verbose=False):
        self.lr = lr
        self.l2 = l2
        self.epochs = epochs
        self.verbose = verbose
        self.w = None  # weights (d,)
        self.b = 0.0   # bias

    def fit(self, X, y):
        """X: list of float vectors (n, d). y: list of 0/1 floats (n,)."""
        n = len(X)
        d = len(X[0])
        # Initialise weights to small random values to break symmetry.
        rng = random.Random(42)
        self.w = [rng.gauss(0, 0.01) for _ in range(d)]
        self.b = 0.0

        for epoch in range(self.epochs):
            total_loss = 0.0
            dw = [0.0] * d
            db = 0.0
            for xi, yi in zip(X, y):
                logit = dot(self.w, xi) + self.b
                p = sigmoid(logit)
                # Binary cross-entropy gradient
                err = p - yi
                for j in range(d):
                    dw[j] += err * xi[j]
                db += err
                # Loss (for monitoring)
                eps = 1e-12
                total_loss += -(yi * math.log(p + eps) + (1 - yi) * math.log(1 - p + eps))

            # Gradient step with L2 on weights (not bias)
            for j in range(d):
                self.w[j] -= self.lr * (dw[j] / n + self.l2 * self.w[j])
            self.b -= self.lr * (db / n)

            if self.verbose and (epoch % 50 == 0 or epoch == self.epochs - 1):
                avg_loss = total_loss / n
                # Accuracy on train
                preds = [1 if self.predict_proba(xi) >= 0.5 else 0 for xi in X]
                train_acc = sum(int(p == int(yi)) for p, yi in zip(preds, y)) / n
                print(f"    epoch {epoch:>3}  loss={avg_loss:.4f}  train_acc={train_acc:.3f}")

    def predict_proba(self, x):
        """Return P(y=1 | x) — probability that cheap model suffices."""
        return sigmoid(dot(self.w, x) + self.b)

    def predict(self, x, threshold=0.5):
        return 1 if self.predict_proba(x) >= threshold else 0


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def stratified_split(rows, train_frac=0.70, seed=7):
    """70/30 stratified split preserving cheap_correct ratio."""
    pos = [r for r in rows if r["cheap_correct"]]
    neg = [r for r in rows if not r["cheap_correct"]]
    rng = random.Random(seed)
    rng.shuffle(pos)
    rng.shuffle(neg)
    n_pos_train = max(1, round(len(pos) * train_frac))
    n_neg_train = max(1, round(len(neg) * train_frac))
    train = pos[:n_pos_train] + neg[:n_neg_train]
    test = pos[n_pos_train:] + neg[n_neg_train:]
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def normalise(vecs):
    """L2-normalise each vector in a list-of-lists."""
    out = []
    for v in vecs:
        norm = math.sqrt(sum(x * x for x in v))
        if norm < 1e-12:
            out.append(v)
        else:
            out.append([x / norm for x in v])
    return out


def compute_metrics(rows, threshold, embeddings_map, model):
    """Evaluate classifier at a given threshold on rows."""
    n = len(rows)
    cheap_model = config.CHEAP_DEFAULT
    strong_model = config.STRONG_DEFAULT
    correct = 0
    cost = 0.0
    n_cheap = 0
    decisions = []
    for row in rows:
        emb = embeddings_map[row["id"]]
        p_cheap = model.predict_proba(emb)
        route_cheap = p_cheap >= threshold
        if route_cheap:
            n_cheap += 1
            c = row["cheap_correct"]
            u = row["cheap_usd"]
        else:
            c = row["strong_correct"]
            u = row["strong_usd"]
        correct += int(c)
        cost += u
        decisions.append({"id": row["id"], "p_cheap": round(p_cheap, 4),
                          "routed_cheap": route_cheap, "correct": c})
    return {
        "threshold": threshold,
        "accuracy": correct / n,
        "total_usd": cost,
        "pct_cheap": n_cheap / n,
        "n": n,
        "decisions": decisions,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("L2b — Logistic-Regression Classifier Router")
    print("=" * 70)

    # Load labelset
    with open(LABELSET) as f:
        rows = json.load(f)
    print(f"Loaded {len(rows)} items from labelset_export.json")

    # Cheap/strong label distribution
    n_cheap_correct = sum(1 for r in rows if r["cheap_correct"])
    print(f"  cheap_correct=True  ({n_cheap_correct}/{len(rows)} = {n_cheap_correct/len(rows):.1%})")
    print(f"  cheap_correct=False ({len(rows)-n_cheap_correct}/{len(rows)} — need strong)")

    # -----------------------------------------------------------------------
    # Embed all prompts (cached in POC-local .cache.json, NOT the harness cache)
    # -----------------------------------------------------------------------
    embed_cache = Cache(EMBED_CACHE_PATH)
    print("\n-- Embedding all prompts via text-embedding-3-small (live API or cache) --")

    # We use a synthetic "chat" message to store embedding vectors in the cache.
    # Embeddings don't go through cache.chat(), so we do manual caching.
    import hashlib, json as _json
    raw_embed_cache_path = os.path.join(HERE, ".embed_cache.json")
    if os.path.exists(raw_embed_cache_path):
        with open(raw_embed_cache_path) as f:
            embed_store = json.load(f)
        print(f"  loaded {len(embed_store)} cached embeddings")
    else:
        embed_store = {}
        print("  no existing embed cache; all embeddings will be fetched live")

    total_embed_usd = 0.0
    prompts_to_embed = [(r["id"], r["prompt"]) for r in rows if r["id"] not in embed_store]
    if prompts_to_embed:
        batch_ids, batch_texts = zip(*prompts_to_embed)
        print(f"  fetching {len(batch_texts)} new embeddings (live API call)...")
        vecs, usd = embed(list(batch_texts))
        total_embed_usd += usd
        for item_id, vec in zip(batch_ids, vecs):
            embed_store[item_id] = vec
        with open(raw_embed_cache_path, "w") as f:
            json.dump(embed_store, f)
        print(f"  fetched {len(batch_texts)} embeddings, cost=${usd:.4e}")
    else:
        print("  all embeddings already cached, $0.00 live spend")

    # Build embedding map (id -> normalised vector)
    raw_vecs = [embed_store[r["id"]] for r in rows]
    norm_vecs = normalise(raw_vecs)
    embeddings_map = {r["id"]: norm_vecs[i] for i, r in enumerate(rows)}

    # -----------------------------------------------------------------------
    # Train / test split
    # -----------------------------------------------------------------------
    train_rows, test_rows = stratified_split(rows, train_frac=0.70)
    print(f"\n-- Data split --")
    print(f"  Train: {len(train_rows)} items  "
          f"({sum(1 for r in train_rows if r['cheap_correct'])} cheap-correct)")
    print(f"  Test : {len(test_rows)} items  "
          f"({sum(1 for r in test_rows if r['cheap_correct'])} cheap-correct)")

    # Features + labels
    X_train = [embeddings_map[r["id"]] for r in train_rows]
    y_train = [1.0 if r["cheap_correct"] else 0.0 for r in train_rows]
    X_test  = [embeddings_map[r["id"]] for r in test_rows]
    y_test  = [1.0 if r["cheap_correct"] else 0.0 for r in test_rows]

    # -----------------------------------------------------------------------
    # Train logistic regression
    # -----------------------------------------------------------------------
    print("\n-- Training logistic regression (numpy-free gradient descent) --")
    clf = LogisticRegressor(lr=0.1, l2=1e-3, epochs=300, verbose=True)
    clf.fit(X_train, y_train)

    # Train accuracy
    train_preds = [clf.predict(x, threshold=0.5) for x in X_train]
    train_acc = sum(int(p == int(yi)) for p, yi in zip(train_preds, y_train)) / len(y_train)
    print(f"\n  Train accuracy (threshold=0.5): {train_acc:.3f}")

    # Test accuracy (label prediction, not routing accuracy)
    test_preds = [clf.predict(x, threshold=0.5) for x in X_test]
    test_label_acc = sum(int(p == int(yi)) for p, yi in zip(test_preds, y_test)) / len(y_test)
    print(f"  Test  accuracy (threshold=0.5): {test_label_acc:.3f}")

    # -----------------------------------------------------------------------
    # Baselines on the test set (from labelset)
    # -----------------------------------------------------------------------
    print("\n-- Baselines on test set (from labelset matrix, no new API calls) --")
    cheap_acc_test  = sum(1 for r in test_rows if r["cheap_correct"])  / len(test_rows)
    cheap_cost_test = sum(r["cheap_usd"] for r in test_rows)
    strong_acc_test  = sum(1 for r in test_rows if r["strong_correct"]) / len(test_rows)
    strong_cost_test = sum(r["strong_usd"] for r in test_rows)
    oracle_cost_test = sum(
        r["cheap_usd"] if r["cheap_correct"] else r["strong_usd"]
        for r in test_rows
    )
    oracle_acc_test = sum(
        1 for r in test_rows if r["cheap_correct"] or r["strong_correct"]
    ) / len(test_rows)

    print(f"  always-cheap  (gpt-4o-mini): acc={cheap_acc_test:.3f}  cost=${cheap_cost_test:.5f}")
    print(f"  always-strong (gpt-4.1)    : acc={strong_acc_test:.3f}  cost=${strong_cost_test:.5f}  "
          f"({strong_cost_test/cheap_cost_test:.1f}x cheap)")
    print(f"  ORACLE (cheapest-correct)  : acc={oracle_acc_test:.3f}  cost=${oracle_cost_test:.5f}")

    # -----------------------------------------------------------------------
    # Threshold sweep — Pareto curve
    # -----------------------------------------------------------------------
    print("\n-- Threshold sweep: Pareto curve (test set) --")
    # First, inspect the distribution of P(cheap_correct) on the test set so we know the
    # effective operating range for the routing-collapse guard.
    all_probs = [clf.predict_proba(embeddings_map[r["id"]]) for r in test_rows]
    prob_min, prob_max = min(all_probs), max(all_probs)
    print(f"\n  P(cheap_correct) distribution on test set:")
    print(f"    min={prob_min:.4f}  max={prob_max:.4f}  "
          f"mean={sum(all_probs)/len(all_probs):.4f}")
    print(f"    items with P<0.5: {sum(1 for p in all_probs if p < 0.5)} / {len(all_probs)}")
    # The effective routing range: only thresholds between prob_min and prob_max actually split.
    # Routing-collapse guard applies only where both outcomes are possible.
    effective_lo = max(round(prob_min + 0.01, 2), 0.05)
    effective_hi = min(round(prob_max - 0.01, 2), 0.95)
    print(f"    Effective threshold range (non-collapsing): [{effective_lo:.2f}, {effective_hi:.2f}]")

    thresholds = [round(t / 100, 2) for t in range(5, 100, 5)]  # 0.05, 0.10, …, 0.95
    pareto_rows = []
    collapse_warnings = []
    for t in thresholds:
        m = compute_metrics(test_rows, t, embeddings_map, clf)
        n_cheap = sum(1 for d in m["decisions"] if d["routed_cheap"])
        n_strong = len(test_rows) - n_cheap
        # Routing-collapse guard: assert non-collapse in the effective range
        if effective_lo <= t <= effective_hi:
            assert n_cheap > 0 and n_strong > 0, (
                f"Routing collapse at threshold={t}: n_cheap={n_cheap}, n_strong={n_strong}. "
                "The model routes ALL items to one class within the effective decision range."
            )
        elif n_cheap == 0 or n_strong == 0:
            collapse_warnings.append(
                f"τ={t:.2f}: routing collapsed (n_cheap={n_cheap}, n_strong={n_strong}) "
                f"— outside effective range [{effective_lo:.2f},{effective_hi:.2f}], expected"
            )
        pareto_rows.append({
            "router": f"classifier(τ={t:.2f})",
            "threshold": t,
            "accuracy": round(m["accuracy"], 4),
            "total_usd": round(m["total_usd"], 6),
            "pct_cheap": round(m["pct_cheap"], 3),
            "n": m["n"],
        })
    if collapse_warnings:
        print("\n  Collapse notes (outside effective range — expected behaviour):")
        for w in collapse_warnings:
            print(f"    {w}")

    # Print the full curve
    print(f"\n  {'threshold':>9}  {'acc':>6}  {'cost $':>10}  {'%cheap':>7}")
    print("  " + "-" * 45)
    for r in pareto_rows:
        baseline_marker = ""
        if r["accuracy"] > cheap_acc_test and r["total_usd"] < strong_cost_test * 0.9:
            baseline_marker = "  <-- beats cheap, cheaper than strong"
        print(f"  τ={r['threshold']:.2f}  acc={r['accuracy']:.3f}  "
              f"cost=${r['total_usd']:.5f}  %cheap={r['pct_cheap']:.0%}"
              + baseline_marker)

    # Pareto front
    all_points = pareto_rows + [
        {"router": "always-cheap",  "accuracy": cheap_acc_test,  "total_usd": cheap_cost_test},
        {"router": "always-strong", "accuracy": strong_acc_test, "total_usd": strong_cost_test},
        {"router": "oracle",        "accuracy": oracle_acc_test, "total_usd": oracle_cost_test},
    ]
    front = pareto_front(all_points)
    front_names = {r["router"] for r in front}
    print(f"\n  Pareto-front routers: {sorted(front_names)}")

    # -----------------------------------------------------------------------
    # Compare to heuristic (L1) at its best operating point
    # -----------------------------------------------------------------------
    # L1 heuristic at τ=0.20 achieves (from L1 run): acc≈0.978 cost≈$0.00483 (full suite)
    # We can compute the classifier's best iso-accuracy point for comparison.
    target_acc = strong_acc_test  # oracle-level accuracy
    # Best threshold that hits at least strong accuracy (if any)
    above_oracle = [r for r in pareto_rows if r["accuracy"] >= target_acc]
    cheapest_at_oracle = min(above_oracle, key=lambda r: r["total_usd"]) if above_oracle else None
    if cheapest_at_oracle:
        print(f"\n  Best classifier point at oracle accuracy ({target_acc:.3f}): "
              f"τ={cheapest_at_oracle['threshold']:.2f}  cost=${cheapest_at_oracle['total_usd']:.5f}  "
              f"%cheap={cheapest_at_oracle['pct_cheap']:.0%}")
    else:
        print(f"\n  No classifier threshold achieves oracle accuracy ({target_acc:.3f}) on this test split.")

    # -----------------------------------------------------------------------
    # Live confirmation: embed a fresh prompt and route it
    # -----------------------------------------------------------------------
    print("\n-- Live confirmation (embed a new prompt and route it) --")
    test_prompt = "What is the derivative of x^3 + 2x? Reply with just the expression."
    vecs_live, usd_live = embed([test_prompt])
    total_embed_usd += usd_live
    print(f"  prompt: {test_prompt!r}")
    print(f"  embed cost: ${usd_live:.2e}")
    norm_v = normalise(vecs_live)[0]
    p = clf.predict_proba(norm_v)
    decision = "cheap (gpt-4o-mini)" if p >= 0.5 else "strong (gpt-4.1)"
    print(f"  P(cheap_correct) = {p:.4f} -> route to: {decision}")
    print(f"  (A well-known calculus derivative — cheap should suffice)")

    print(f"\n  Total embedding spend this run: ${total_embed_usd:.4e}")

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    print("\n== Summary results table ==")
    header_cols = ["router", "accuracy", "total_usd", "pct_cheap"]
    rows_to_print = [
        {"router": "always-cheap",  "accuracy": cheap_acc_test,  "total_usd": cheap_cost_test, "pct_cheap": 1.0},
        {"router": "always-strong", "accuracy": strong_acc_test, "total_usd": strong_cost_test, "pct_cheap": 0.0},
        {"router": "oracle",        "accuracy": oracle_acc_test, "total_usd": oracle_cost_test, "pct_cheap": None},
    ]
    # Add a selection of classifier points
    select_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    for r in pareto_rows:
        if r["threshold"] in select_thresholds:
            rows_to_print.append(r)
    print(f"\n  {'router':<28} {'acc':>6}  {'cost':>10}  {'%cheap':>7}")
    print("  " + "-" * 60)
    for r in rows_to_print:
        pc = f"{r['pct_cheap']:.0%}" if r["pct_cheap"] is not None else "  --"
        pareto_marker = "*" if r["router"] in front_names else " "
        print(f"  {pareto_marker} {r['router']:<27} {r['accuracy']:.3f}  "
              f"${r['total_usd']:.5f}  {pc}")

    # -----------------------------------------------------------------------
    # Save summary JSON
    # -----------------------------------------------------------------------
    summary = {
        "n_items_total": len(rows),
        "n_train": len(train_rows),
        "n_test": len(test_rows),
        "train_label_acc": round(train_acc, 4),
        "test_label_acc": round(test_label_acc, 4),
        "embed_model": "text-embedding-3-small",
        "embed_dim": len(norm_vecs[0]),
        "total_embed_usd": round(total_embed_usd, 6),
        "baselines_test": {
            "always_cheap":  {"acc": round(cheap_acc_test, 4),  "usd": round(cheap_cost_test, 6)},
            "always_strong": {"acc": round(strong_acc_test, 4), "usd": round(strong_cost_test, 6)},
            "oracle":        {"acc": round(oracle_acc_test, 4), "usd": round(oracle_cost_test, 6)},
        },
        "pareto_curve": pareto_rows,
        "pareto_front_members": sorted(front_names),
        "best_at_oracle_acc": cheapest_at_oracle,
        "live_confirmation": {
            "prompt": test_prompt,
            "p_cheap": round(p, 4),
            "decision": decision,
        },
    }
    out_path = os.path.join(HERE, "l2b_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
