# R-002: Embedding k-NN Router

**Category**: recipe
**Evidence tier**: Live verified (POC L2, X5)
**Source POCs**: L2-embedding-knn-router, X5-router-benchmark-pareto

## Live verified

On the 45-task benchmark (5-fold CV, X5):

- k-NN(k=3): **acc 0.933, $0.00221** (learned; dominates heuristic and random)
- k-NN(k=5): **acc 0.889, $0.00204**

On the 22-item held-out test split (L2):

- Best operating point — k=7, threshold=0.7: **acc 0.955, $0.00136 — 88% cost reduction vs
  always-strong ($0.01104)**
- Embedding corpus: one live call to text-embedding-3-small for all 45 prompts, total cost $0.000030.
  Cached and reused for free on subsequent runs.

The k-NN router lies firmly on the Pareto frontier between always-cheap and the logistic
classifier. Use it when you have a label set but want no training overhead and a direct
similarity argument for each decision.

## How it works

```
label set: [(prompt_i, cheap_correct_i)]  (built from real model runs on past tasks)
          │
          ▼
embed all prompts  (text-embedding-3-small → 1536-dim vectors)
          │
          ▼
for each new prompt q:
    embed(q) → q_vec
    cosine_sim(q_vec, train_vec_i) for each i  →  sim_scores [n]
    top-k by similarity  →  neighbors [(sim_i, cheap_correct_i)]
    weighted_vote = Σ(sim_i × cheap_correct_i) / Σ(sim_i)
    │
    ├── weighted_vote ≥ threshold  →  route CHEAP (gpt-4o-mini)
    └── weighted_vote  < threshold  →  route STRONG (gpt-4.1)
```

Feature: prompt embedding vector only. No discipline/difficulty oracle. (L2)

## Snippet (copy-paste-ready)

```python
import numpy as np
from providers import embed, chat

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (d,), b: (n, d). Returns (n,) similarity scores."""
    return np.dot(b, a)   # assumes L2-normalized inputs; avoids numpy 2.0 matmul warning

def knn_route(
    query: str,
    train_vecs: np.ndarray,   # (n, d) L2-normalized
    train_labels: list[int],  # cheap_correct: 1 or 0
    k: int = 3,
    threshold: float = 0.7,
    cheap_model: str = "gpt-4o-mini",
    strong_model: str = "gpt-4.1",
) -> dict:
    (qvec,), embed_usd = embed([query])
    qvec = np.array(qvec, dtype=np.float64)
    qvec /= np.linalg.norm(qvec) + 1e-12

    sims      = cosine_similarity(qvec, train_vecs)  # (n,)
    top_k_idx = np.argsort(sims)[-k:]
    top_k_sim = sims[top_k_idx]
    top_k_lbl = np.array(train_labels, dtype=float)[top_k_idx]

    denom          = top_k_sim.sum()
    weighted_vote  = float((top_k_sim * top_k_lbl).sum() / denom) if denom > 0 else 0.0
    model          = cheap_model if weighted_vote >= threshold else strong_model

    result = chat(model, [{"role": "user", "content": query}])
    return {
        "model":         model,
        "weighted_vote": weighted_vote,
        "answer":        result.text,
        "usd":           embed_usd + result.usd,
    }
```

## Building the label set

```python
# embed corpus once; cache aggressively
train_prompts = [task.prompt for task in suite]
(vecs, embed_usd) = embed(train_prompts)        # one batched call
train_vecs = np.array(vecs, dtype=np.float64)
# L2-normalize
norms = np.linalg.norm(train_vecs, axis=1, keepdims=True)
train_vecs /= norms + 1e-12

# get labels from the pre-run labelset (never re-bill)
train_labels = [item["cheap_correct"] for item in labelset]
```

## Threshold sweep — pick k and threshold for your SLA

Live verified (L2, 22-item test split):

| k | threshold | acc   | cost      | %cheap |
|---|-----------|-------|-----------|--------|
| 3 | 0.7       | 0.955 | $0.00143  | 64%    |
| 5 | 0.7       | 0.955 | $0.00146  | 59%    |
| **7** | **0.7** | **0.955** | **$0.00136** | **68%** |
| 5 | 0.6       | 0.909 | $0.00123  | 77%    |
| 3 | 0.4–0.6   | 0.818 | $0.00098  | 95%    |

The threshold sweet spot is sharp: threshold=0.6→0.7 jumps accuracy from 0.909 to 0.955
for a cost increase of only $0.00013–$0.00023. Hard-task embeddings cluster tightly, so their
neighbor vote concentrates near 0.6–0.7. (L2)

## Gotchas (live-discovered, L2)

- **k=1 already beats always-cheap**: k=1 achieves 90.9% accuracy vs 81.8% for always-cheap —
  embedding proximity carries genuine task-difficulty signal.
- **Low thresholds collapse to "mostly cheap"**: below threshold=0.6, the router incorrectly
  routes hard math tasks cheap because their k-NN vote scores hover just above 0.4. Hard-task
  embeddings are similar to medium-math embeddings in cosine space.
- **numpy 2.0 `@` operator triggers spurious divide-by-zero** on normalized matrices. Use
  `np.dot(b, a)` instead of `b @ a`. Same numerical result, no warning.
- **Embedding cost is negligible** ($0.000030 for 45 prompts) but embed once and cache.
  Re-embedding the same corpus on every run is pure waste.

## Evidence

- L2-embedding-knn-router/README.md — full k/threshold sweep, live routing confirmations (3 live calls)
- X5-router-benchmark-pareto/README.md — 5-fold CV benchmark (k-NN k=3: 0.933, $0.00221)
- results-digest.md lines 20–21 — authoritative benchmark numbers
