# DR-003: Why 5-Fold Cross-Validation Over a Single Train/Test Split

**Date**: 2026-06-21
**Status**: Accepted
**Evidence tier**: Live verified (X5; capstone; L2; L2b)

---

## Decision

Use 5-fold cross-validation (5-fold CV) as the canonical evaluation methodology for
predictive routers (k-NN, logistic classifier) in this degree. Single held-out split
results may appear as supplementary context but must be labeled "single split, N held-out
items" and not presented as the primary benchmark number.

---

## Context

The task suite has 45 items. Predictive routers must be trained on labeled data and
evaluated on held-out items. Two methodologies were compared:

1. **Single split** — used in L2 (23/22 split) and L2b (32/13 split with stratification).
   Results: L2 best router (k=7, thr=0.7): acc=0.955 on 22 held-out items; L2b classifier
   at τ=0.80: acc=1.000 on 13 held-out items.

2. **5-fold CV** — used in X5 and capstone. Each item is assigned to exactly one test fold;
   results aggregated across all 5 folds. Results: logistic(thr=0.9): acc=0.978 on all 45
   items; capstone adaptive(thr=0.8): acc=0.978 on all 45 items.

---

## Rationale

**Small data instability.** With 45 items and only 6 hard items that need the strong model,
a single 70/30 split allocates ~1.8 hard items (on average) to the test set. A partition
that puts 0 hard items in the test set shows acc=1.000 for almost any classifier. A
partition that puts all 6 in the test set shows artificially low accuracy. This variance
is not a property of the router — it is a property of the split.

L2b demonstrated this concretely: the 13-item test set (single split) showed acc=1.000 at
τ=0.80, which looks better than the 5-fold CV result (acc=0.978 at τ=0.9). The single-split
result is not wrong, but it is less stable — a different random seed could easily show
lower accuracy.

**Every item evaluated exactly once.** With 5-fold CV, each of the 45 items is in the
test set for exactly one fold. No item is evaluated twice (no data leakage through the
evaluation itself) and no item is missed. The final accuracy is averaged over all 45 items.

**Standard practice for small benchmarks.** RouterBench (Hu et al.) and RouteLLM (LMSYS)
both use CV or held-out validation on larger datasets. For datasets under ~200 items, CV
is the standard method to produce stable accuracy estimates.

---

## Consequences and accepted tradeoffs

- **Higher computational cost.** 5-fold CV trains 5 models instead of 1. For logistic
  regression in pure Python, this is negligible. For methods with expensive training
  (e.g., kNN requires recomputing neighbors), it adds a constant factor.
- **Single-split results from earlier POCs are valid.** L2 and L2b results are honest
  measured numbers. They serve as supplementary evidence and are labeled "single split."
  They are not used as the canonical benchmark numbers in the degree summary.
- **Accuracy and cost may differ slightly from single-split.** The 5-fold CV result
  reflects the full distribution of the suite, not a single partition. Expect the CV
  result to be more conservative than a lucky single split and more accurate than an
  unlucky one.

---

## Evidence

- X5 README.md: "Predictive routers (k-NN, logistic) use 5-fold cross-validation so every task is held out exactly once (no leakage)." (Live verified)
- Capstone README.md: "5-fold CV: adaptive(thr=0.8): acc 0.978, $0.00257." (Live verified)
- L2b README.md: "Train: 32 items (70% stratified split, seed=7)... Test: 13 items (30% held-out)." Note: this is the single-split methodology, labeled as such. (Live verified)
- L2 README.md: "Results table (22-item held-out test split, 2026-06-21)." (Live verified)
- results-digest.md: X5 and capstone numbers are the canonical CV results quoted throughout. (Live verified)
