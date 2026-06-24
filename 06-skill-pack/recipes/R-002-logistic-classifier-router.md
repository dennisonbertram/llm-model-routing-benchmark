# Recipe R-002: Logistic Classifier Router

Live verified (L2b; X5; 2026-06-21). Embed + train + threshold sweep. The best
cost-quality router on this degree's workload.

Back to [index](../index.md).

---

## When to use

- You have (or can generate) per-task correctness labels for cheap and strong models.
- You can afford one-time embedding cost (~$3e-05 for 45 prompts via text-embedding-3-small).
- You want to approach oracle efficiency.

---

## Live results

Live verified. logistic(thr=0.9) CV on 45-task suite: acc=0.978, $0.00291 — 7.4x cheaper
than always-strong. (X5; 2026-06-21)

logistic(thr=0.80) on 13-item test set: acc=1.000, $0.000773 — 6.3x cheaper. (L2b)

See [reference/pareto-numbers.md](../reference/pareto-numbers.md).

---

## Code

```python
"""
Logistic classifier router — embed + train + threshold sweep.
Live verified: logistic(thr=0.9) CV → acc=0.978, $0.00291, 7.4x cheaper than strong.
(X5; L2b; 2026-06-21)
"""
import json, math, os, sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "harness")
sys.path.insert(0, HARNESS)
from providers import embed
from cache import Cache

CHEAP_MODEL  = "gpt-4o-mini"
STRONG_MODEL = "gpt-4.1"
EMBED_MODEL  = "text-embedding-3-small"


# ── 1. Embed all prompts (one-time; cached automatically) ──────────────────

def get_embeddings(prompts: list[str], cache_path: str = None) -> list[list[float]]:
    """Returns L2-normalized 1536-d vectors for each prompt. Uses on-disk cache."""
    # text-embedding-3-small: ~$0.02/1M tokens; 45 prompts ≈ $3e-05 total.
    vectors, _ = embed(prompts, model=EMBED_MODEL)
    # L2-normalize
    normed = []
    for v in vectors:
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        normed.append([x / norm for x in v])
    return normed


# ── 2. Logistic regression (pure Python, no sklearn) ──────────────────────

def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


def train_logistic(X: list[list[float]], y: list[int],
                   lr: float = 0.1, epochs: int = 300, l2: float = 1e-3):
    """
    X: list of 1536-d feature vectors (L2-normalized embeddings)
    y: list of 0/1 labels (1 = cheap model is correct)
    Returns weight vector w (same dim as X[0]).
    """
    dim = len(X[0])
    w = [0.0] * dim
    for _ in range(epochs):
        grad = [0.0] * dim
        for xi, yi in zip(X, y):
            err = sigmoid(sum(w[j] * xi[j] for j in range(dim))) - yi
            for j in range(dim):
                grad[j] += err * xi[j]
        for j in range(dim):
            w[j] -= lr * (grad[j] / len(X) + l2 * w[j])
    return w


def predict_proba(w: list[float], x: list[float]) -> float:
    """P(cheap_correct) for a single embedding vector x."""
    return sigmoid(sum(w[j] * x[j] for j in range(len(w))))


# ── 3. Router ──────────────────────────────────────────────────────────────

class LogisticRouter:
    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold
        self.w = None  # set after train()

    def train(self, prompts: list[str], labels: list[int]):
        """
        prompts: training prompt texts
        labels:  1 = cheap correct, 0 = cheap incorrect (from labelset)
        """
        X = get_embeddings(prompts)
        self.w = train_logistic(X, labels)

    def route(self, prompt: str) -> tuple[str, float]:
        """Returns (model_id, p_cheap). Requires train() first."""
        vec = get_embeddings([prompt])[0]
        p = predict_proba(self.w, vec)
        model = CHEAP_MODEL if p >= self.threshold else STRONG_MODEL
        return model, p


# ── 4. Load labelset and split ─────────────────────────────────────────────

def load_labelset(path: str) -> tuple[list, list, list, list]:
    """
    Loads L0 labelset from labelset_export.json.
    Returns train_prompts, train_labels, test_prompts, test_labels (70/30 split).
    """
    with open(path) as f:
        data = json.load(f)
    items = [(d["prompt"], int(d["cheap_correct"])) for d in data]
    split = int(0.70 * len(items))
    train = items[:split]
    test  = items[split:]
    return (
        [t[0] for t in train], [t[1] for t in train],
        [t[0] for t in test],  [t[1] for t in test],
    )


# ── 5. Threshold sweep ─────────────────────────────────────────────────────

def pareto_sweep(router: LogisticRouter, test_prompts, test_labels,
                 labelset_costs, thresholds=None):
    """
    Sweeps threshold values and prints the Pareto table.
    labelset_costs: dict mapping prompt → {cheap_usd, strong_usd, cheap_correct}
    """
    if thresholds is None:
        thresholds = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

    print(f"{'threshold':>10}  {'accuracy':>8}  {'cost':>10}  {'%cheap':>7}")
    for thr in thresholds:
        router.threshold = thr
        correct = total_usd = cheap_count = 0
        for prompt, label in zip(test_prompts, test_labels):
            model, _ = router.route(prompt)
            costs = labelset_costs.get(prompt, {})
            if model == CHEAP_MODEL:
                correct += costs.get("cheap_correct", 0)
                total_usd += costs.get("cheap_usd", 0)
                cheap_count += 1
            else:
                # Strong model is always correct when oracle needs it
                correct += 1
                total_usd += costs.get("strong_usd", 0)
        acc = correct / len(test_prompts)
        pct = cheap_count / len(test_prompts) * 100
        print(f"{thr:>10.2f}  {acc:>8.3f}  ${total_usd:>9.6f}  {pct:>6.0f}%")


# ── Example usage ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    labelset_path = os.path.join(HARNESS, ".cache", "labelset.json")
    if not os.path.exists(labelset_path):
        print(f"ERROR: labelset not found at {labelset_path}")
        print("Run L0 first: cd 03-pocs/L0-smoke-and-harness/source && python3 run_l0.py")
        raise SystemExit(1)

    train_p, train_y, test_p, test_y = load_labelset(labelset_path)
    print(f"Train: {len(train_p)} items, Test: {len(test_p)} items")

    router = LogisticRouter(threshold=0.80)
    print("Training (embeds all prompts if not cached)...")
    router.train(train_p, train_y)

    # Single prediction confirmation
    prompt = "What is the derivative of x^3 + 2x?"
    model, p = router.route(prompt)
    print(f"'{prompt[:50]}...'  P(cheap)={p:.4f}  → {model}")
```

---

## Key parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `threshold` | 0.80 | Higher = more items to strong = higher accuracy, higher cost |
| `epochs` | 300 | More epochs = closer convergence; diminishing returns after 200 |
| `l2` | 1e-3 | L2 regularization weight; prevents overfitting on small datasets |
| `lr` | 0.1 | Learning rate; 0.01–0.1 works for this feature scale |

## Honest notes

- With 45 training items (7 negatives), the classifier learns the base rate, not fine-grained
  difficulty features. More labeled data improves discrimination.
- All predicted P(cheap) values may cluster in a narrow range (0.74–0.91 on this suite).
  The effective threshold range is narrow — sweep carefully.
- The oracle is unrealizable: report it separately, labeled "unrealizable ceiling."

## Source

`03-pocs/L2b-classifier-router/source/run_l2b.py`
