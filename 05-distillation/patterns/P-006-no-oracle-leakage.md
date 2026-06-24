# P-006: No Oracle Leakage — Features from Prompt Only

**Category**: pattern
**Evidence tier**: Live verified (POCs L2, L2b, X5)
**Source POCs**: L2-embedding-knn-router, L2b-classifier-router, X5-router-benchmark-pareto

## Live verified

Both predictive routers in this degree (kNN and logistic) use **only the prompt text** as
features, via a text embedding. They never use `difficulty`, `discipline`, or any label
derived from running the models on the same task. All benchmark results use 5-fold CV
(kNN, logistic) or a fixed train/test split (L2, L2b) so every task is held out at
evaluation time. (L2, L2b, X5)

L2 test: 6 behavioral tests include a dedicated "leakage" guard that verifies the router
makes its decision without any oracle field in its feature vector. (L2)

## The pattern

**Oracle leakage**: using information that is available only at training/evaluation time —
such as `difficulty` labels, `discipline` labels, or the ground-truth answer — as a routing
feature. This inflates measured accuracy because the router is peeking at information it
cannot have in production.

Forms of leakage to guard against:

| Leakage type             | Example                                      | Fix |
|--------------------------|----------------------------------------------|-----|
| Label leakage            | Use `task.difficulty` as a feature           | Use embedding only |
| Discipline leakage       | Use `task.discipline` ("math", "coding")     | Use embedding only |
| Gold-answer leakage      | Embed prompt + gold answer together          | Embed prompt text only |
| Same-fold train+eval     | Train and evaluate on the same data split    | Use k-fold CV |
| Oracle-model leakage     | Use `cheap_correct` from labelset as a live feature | Only use as training label; never at inference |

## How to check for leakage

```python
def check_no_leakage(router, suite):
    """
    Assert the router does not use oracle fields.
    The harness task has: id, discipline, difficulty, prompt, grade, gold
    Only 'prompt' is allowed at inference time.
    """
    for task in suite:
        # Simulate inference: provide only prompt, no oracle fields
        inference_input = {"prompt": task.prompt}   # only allowed field
        decision = router.route_from_text(inference_input["prompt"])
        assert decision in ("cheap", "strong"), f"Invalid decision for {task.id}"
    print("No oracle leakage: router uses prompt text only.")
```

## Why this matters for deployed cost savings

If a router uses `difficulty = "hard"` as a feature, it achieves good accuracy on the
benchmark — but that label is NOT available in production when a user sends a prompt.
The production router has no difficulty label. Reported cost savings would not materialize.

The logistic router in this degree achieves 0.978 accuracy using only the 1536-dim embedding
of the prompt text. This is the deployable result. (L2b, X5)

## The oracle is a ceiling, not a feature

The oracle (cheapest-correct per task) correctly serves as a benchmark calibration tool
because it is never used as a feature. It is computed from the outcome matrix after the
fact and reported separately from realizable routers. (P-001, X5)

Using the oracle's per-task assignments as training labels for a classifier IS leakage
if the evaluation is done on the same tasks. Use k-fold CV to ensure every task's oracle
label is only used in training folds where that task is not being evaluated. (X5)

## k-fold CV implementation guard

```python
# Correct: 5-fold CV — each fold is evaluated on tasks not seen during training
for fold in range(5):
    train_idx = [i for i in range(n) if fold_of(i) != fold]
    test_idx  = [i for i in range(n) if fold_of(i) == fold]

    # Train on train_idx only
    router = train_router(X[train_idx], y[train_idx])

    # Evaluate on test_idx (never seen during training)
    for i in test_idx:
        decision = router.predict(X[i])     # uses embedding only
        record(decision, y[i])              # y[i] used only for scoring, not as feature

# WRONG (leakage): train on all data, evaluate on same data
router = train_router(X, y)
for i in range(n):
    decision = router.predict(X[i])   # saw X[i] during training — optimistic result
```

## Evidence

- L2-embedding-knn-router/README.md — features section: "Features used: prompt text only"
- L2b-classifier-router/README.md — "Features: L2-normalised 1536-dim embedding vector (no discipline/difficulty oracle leakage)"
- X5-router-benchmark-pareto/README.md — "5-fold cross-validation so every task is held out exactly once (no leakage)"
- L2-embedding-knn-router source/test_l2.py — dedicated leakage behavioral test
