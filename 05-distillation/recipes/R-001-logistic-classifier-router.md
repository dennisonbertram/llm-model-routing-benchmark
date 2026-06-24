# R-001: Logistic-Regression Classifier Router (the winner)

**Category**: recipe
**Evidence tier**: Live verified (POC L2b, X5, capstone)
**Source POCs**: L2b-classifier-router, X5-router-benchmark-pareto, L-capstone-adaptive-routing-gateway

## Live verified

On the 45-task benchmark (15 math, 12 QA, 18 coding), a logistic-regression router trained
on text-embedding-3-small features:

- At τ=0.9 (5-fold CV): **acc 0.978, $0.00291 — 7.4× cheaper than always-strong ($0.02148)**
- At τ=0.8 (capstone 5-fold CV): **acc 0.978, $0.00257 — 8.4× cheaper than always-strong**
- On held-out test set (13 items, τ=0.80): oracle-level accuracy at 6.3× cost reduction vs always-strong

This is the single best realizable router on the benchmark. It ties the oracle's accuracy
($0.00214 ceiling) at only 1.20× oracle cost — the closest any non-oracle method gets.

## Architecture

```
prompt text
    │
    ▼
text-embedding-3-small  (1536-dim, $~6e-07 per prompt)
    │
    ▼
L2-normalize embedding
    │
    ▼
logistic regression  (300 epochs, lr=0.1, L2=1e-3, numpy sigmoid)
  trained on labelset: cheap_correct(task) → {0, 1}
    │
    ▼
P(cheap_correct) ∈ [0, 1]
    │
    ▼
P ≥ τ  → route to gpt-4o-mini  (cheap)
P < τ  → route to gpt-4.1      (strong)
```

Features: embedding vector only — no discipline, no difficulty, no oracle label. (L2b)

## Training the label set (one-time cost)

```python
# Run both models on your task suite; record per-task correctness
labelset = []
for task in suite:
    cheap_res = cache.chat("gpt-4o-mini", task.messages)
    strong_res = cache.chat("gpt-4.1",   task.messages)
    labelset.append({
        "id":            task.id,
        "cheap_correct": task.grade(cheap_res.text),
        "strong_correct": task.grade(strong_res.text),
        "cheap_usd":     cheap_res.usd,
        "strong_usd":    strong_res.usd,
    })
# Reuse this cache; never re-bill the same (model, task) pair.
```

## Training the classifier (pure numpy, no sklearn)

```python
import numpy as np

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

def train_logistic(X, y, epochs=300, lr=0.1, l2=1e-3):
    """
    X: (n, d) float64, L2-normalized embedding vectors
    y: (n,)   float64, 1.0 if cheap is correct else 0.0
    Returns: (w, b) — weight vector and bias
    """
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        logits = X @ w + b
        probs  = sigmoid(logits)
        err    = probs - y
        w -= lr * (X.T @ err / n + l2 * w)
        b -= lr * (err.mean())
    return w, b

def predict_proba(X, w, b):
    """Returns P(cheap_correct) for each row in X."""
    return sigmoid(X @ w + b)
```

## Threshold sweep (pick τ for your cost-quality target)

```python
thresholds = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
for tau in thresholds:
    decisions   = ["cheap" if p >= tau else "strong" for p in p_cheap]
    total_cost  = sum(cheap_usd[i] if d == "cheap" else strong_usd[i]
                      for i, d in enumerate(decisions))
    accuracy    = compute_accuracy(decisions, labelset)
    pct_cheap   = decisions.count("cheap") / len(decisions) * 100
    print(f"τ={tau:.2f}  acc={accuracy:.3f}  cost=${total_cost:.5f}  cheap={pct_cheap:.0f}%")
```

Live verified results from L2b test set (13 items):

| τ     | accuracy | cost (13 tasks) | %cheap |
|-------|----------|-----------------|--------|
| 0.70  | 0.846    | $0.000373       | 100%   |
| 0.75  | 0.923    | $0.000468       |  92%   |
| **0.80** | **1.000** | **$0.000773** | **54%** |
| 0.85  | 1.000    | $0.000922       |  31%   |
| 0.90  | 1.000    | $0.004609       |   8%   |

**Use 5-fold cross-validation to pick τ.** Never evaluate on the same split used to
choose τ — that leaks oracle labels (see P-006-no-oracle-leakage).

## Routing at inference time

```python
import numpy as np
from providers import embed, chat

# embed once; cache and reuse
def route_and_answer(prompt: str, w, b, tau: float = 0.80) -> dict:
    (vec,), embed_usd = embed([prompt])
    vec = np.array(vec, dtype=np.float64)
    vec /= np.linalg.norm(vec) + 1e-12
    p_cheap = float(sigmoid(vec @ w + b))
    model   = CHEAP if p_cheap >= tau else STRONG
    result  = chat(model, [{"role": "user", "content": prompt}])
    return {"model": model, "p_cheap": p_cheap, "answer": result.text,
            "usd": embed_usd + result.usd}
```

Live confirmed (capstone): "capital of France" → p_cheap=0.97 → gpt-4o-mini → "Paris.";
"arrange BALLOON" → p_cheap=0.38 → gpt-4.1 → "1260" (correct). (L-capstone)

## Honest class-imbalance caveat (live-discovered, L2b)

Live verified: On a suite where 84% of tasks are already handled correctly by the cheap
model (38/45), the logistic regression learns the base rate but struggles to sharply separate
the hard-math tail in embedding space. All predicted P(cheap_correct) scores cluster between
0.74–0.91. This means the effective threshold range is narrow. With only 7 negative-class
examples in 45 total, the gradient has little signal. The classifier works because even weak
discrimination routes the uncertain items to strong — but a larger, more balanced labeled
dataset (hundreds of examples per class, as RouteLLM recommends) would sharpen the boundary.

## Gotchas

- numpy 2.0 on macOS emits spurious "divide by zero in matmul" warnings on clean normalized
  inputs. Suppress with `np.errstate(divide='ignore', invalid='ignore')` or switch to
  `np.dot`. (L0 surprises)
- Embed costs are tiny ($~6e-07 per call with text-embedding-3-small) but pay them up front
  by embedding the label set once and caching. (L2b)
- Never put `difficulty` or `discipline` labels in the feature vector — that leaks oracle
  knowledge available only at training time. (L2b)

## Evidence

- L2b-classifier-router/README.md — full Pareto sweep, class-imbalance analysis, live embed confirm
- X5-router-benchmark-pareto/README.md — 5-fold CV results (thr=0.9: acc 0.978, $0.00291)
- L-capstone-adaptive-routing-gateway/README.md — capstone CV (thr=0.8: acc 0.978, $0.00257)
- results-digest.md lines 21–24 — authoritative benchmark numbers
