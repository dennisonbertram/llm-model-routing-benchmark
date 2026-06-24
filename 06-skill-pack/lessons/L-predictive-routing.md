# Lesson: Predictive Routing (Embedding kNN + Logistic Classifier)

Live verified (L2; L2b; X5; 2026-06-21). The RouteLLM / Hybrid-LLM family of learned
routing models. Best cost-quality ratio of all strategies tested.

Back to [index](../index.md).

---

## What it is

A predictive router trains a model (kNN or logistic regression) on labeled examples
(prompt + "did cheap model get it right?") and uses learned patterns to predict which
model to route new prompts to. The decision threshold is a continuous knob that trades
cost for accuracy.

The family covers:
- **Embedding kNN**: embed prompts via text-embedding-3-small; route by majority vote
  of k nearest labeled neighbors.
- **Logistic classifier**: train a binary linear model on embedding features; threshold
  the probability P(cheap correct).

---

## Live results: kNN (L2; 22-item held-out test split)

Live verified. From `03-pocs/L2-embedding-knn-router/README.md`.

| Router | accuracy | cost (22 tasks) | % cheap |
|--------|----------|-----------------|---------|
| always-cheap | 0.818 | $0.00088 | 100% |
| kNN k=7 thr=0.5 | 0.818 | $0.00098 | 95% |
| kNN k=5 thr=0.6 | 0.909 | $0.00123 | 77% |
| **kNN k=7 thr=0.7** | **0.955** | **$0.00136** | **68%** |
| always-strong | 0.955 | $0.01104 | 0% |
| oracle (ceiling) | 0.955 | $0.00122 | — |

Best: k=7, thr=0.7 — matches always-strong accuracy (0.955) at 88% cost reduction.
Embedding one-time cost for all 45 prompts: ~$3e-05 (text-embedding-3-small).

---

## Live results: logistic classifier (L2b; 13-item held-out test set)

Live verified. From `03-pocs/L2b-classifier-router/README.md`.

| threshold τ | accuracy | cost (13 tasks) | % cheap |
|-------------|----------|-----------------|---------|
| τ=0.75 | 0.923 | $0.000468 | 92% |
| **τ=0.80** | **1.000** | **$0.000773** | **54%** |
| τ=0.85 | 1.000 | $0.000922 | 31% |
| τ=0.90 | 1.000 | $0.004609 | 8% |
| always-strong | 1.000 | $0.004868 | 0% |
| oracle | 1.000 | $0.000540 | — |

Best: τ=0.80 — oracle accuracy, 6.3x cheaper than always-strong, 84% cost reduction.

---

## Full-suite results: logistic in X5 benchmark (45 tasks, 5-fold CV)

Live verified. From `03-pocs/X5-router-benchmark-pareto/README.md`.

| Router | accuracy | total cost (45 tasks) |
|--------|----------|-----------------------|
| logistic(thr=0.7) CV | 0.956 | $0.002335 |
| **logistic(thr=0.9) CV** | **0.978** | **$0.002905** |
| always-strong | 0.978 | $0.021482 |

logistic(thr=0.9) matches always-strong accuracy at $0.00291 — 7.4x cheaper.

---

## Architecture

```
text-embedding-3-small (1536-d)
  → L2-normalize
  → logistic regression (gradient descent, L2=1e-3, 300 epochs)
  → P(cheap_correct)
  → threshold τ
  → {gpt-4o-mini | gpt-4.1}
```

Training: 32 items (70% split), labels from labelset_export.json (L0 outcome matrix).
No oracle leakage: features are embedding vectors only, not discipline/difficulty labels.

---

## Honest diagnosis (from L2b)

Live verified. The logistic classifier faces a fundamental challenge on this suite:

- **Extreme class imbalance**: 84% of prompts (38/45) are correctly answered by cheap.
  Only 7 items need strong — all hard math.
- **P(cheap_correct) clusters high**: all predicted probabilities fall between 0.74–0.91.
  The model learned the base rate but cannot sharply discriminate hard-math items.
- **Embedding proximity alone is a weak signal**: hard math items look semantically similar
  to medium math items in 1536-d embedding space.
- **Despite this**: at τ=0.80, the classifier achieves oracle accuracy because routing even
  a handful of uncertain items to strong is sufficient. It works because of the operating
  point, not because of fine-grained discrimination.

The RouteLLM paper notes their classifier needed hundreds to thousands of labeled examples
to learn reliable separating boundaries. With 45 tasks (7 negatives), the gradient has
very little signal. More data would help (research-supported, not live-verified here).

---

## When to use

- You have (or can generate) a labeled outcome matrix (both models, per-task correctness).
- You can embed all prompts once at training time (small one-time cost).
- You want to approach oracle efficiency without always-strong cost.

## When NOT to use

- No labeled data and no API budget to generate labels.
- The workload has no difficulty distribution (all easy or all hard — nothing to route).

---

## Recipe

[recipes/R-002-logistic-classifier-router.md](../recipes/R-002-logistic-classifier-router.md)

## POC sources

- `../03-pocs/L2-embedding-knn-router/`
- `../03-pocs/L2b-classifier-router/`
- `../03-pocs/X5-router-benchmark-pareto/`
