# G-011: Logistic routing classifier collapses to always-cheap at τ=0.5 due to class imbalance

**Category**: gotcha
**Severity**: high
**Evidence tier**: Live verified
**Source POC**: L2b-classifier-router

## What

Live verified. The L2b logistic regression classifier trained on 36 items predicted P(cheap_correct) in the range [0.737, 0.907] for all 45 test items. No item scored below 0.5. At the canonical default threshold τ=0.5 ("route to cheap if P > threshold"), every item routed to cheap — accuracy equaled the always-cheap baseline (0.846) with no benefit from the classifier.

The effective decision range was only 0.75–0.90 (a 0.15-wide band). Outside this band: τ < 0.75 routes 100% cheap; τ > 0.90 routes nearly all to strong.

## Why it matters

Any agent that trains a routing classifier with a standard sklearn default threshold of 0.5 on a class-imbalanced routing dataset (cheap-correct items are 84% of the typical suite) will silently get a degenerate router. The model trains correctly — it converges to predicting "cheap" for everything, which happens to be ~84% accurate. No error is raised; accuracy looks fine at 0.84.

## Root cause

Class imbalance: 38/45 items (84%) are cheap-correct. With only ~5 hard-math negatives in a 32-item training set, the L2 loss gradient from those 5 examples is overwhelmed by 27 positives. The classifier settles at a bias toward "cheap" rather than learning a separating hyperplane. The training accuracy never improves above 84.4% — exactly the base rate.

This is a known RouteLLM limitation at small dataset sizes. The RouteLLM paper used thousands of labeled preference pairs; a 32-item training set is too small for reliable class separation.

## Fix

After training, sweep the decision threshold over the actual prediction distribution rather than using 0.5:

```python
# After fitting the classifier, find the effective range:
predictions = [model.predict_proba(x) for x in X_test]
print(f"P range: [{min(predictions):.3f}, {max(predictions):.3f}]")
# Sweep thresholds within this range, not the canonical [0, 1]
for tau in np.linspace(min(predictions), max(predictions), 20):
    routed_to_strong = sum(p < tau for p in predictions)
    # ... evaluate accuracy and cost
```

Report the threshold alongside the Pareto metrics so consumers know the effective operating range is not [0, 1].

For better class separation, increase training set size (RouteLLM recommends hundreds to thousands of pairs) or apply class weighting (`class_weight={0: 1, 1: 8}` for 8:1 imbalance) to boost gradient from minority class examples.

## Regression note

After training, assert `min(predictions) < 0.75` — if all predictions are above 0.75, the classifier is degenerate and the training set needs more hard-item examples before deployment.

## Evidence

- Source: `03-pocs/L2b-classifier-router/surprises.md`, S-1: "P(cheap_correct) clusters between 0.74–0.91 — no item below 0.5. At the canonical τ=0.5, it collapses to always-cheap — it never routes to strong." (Live verified)
- Source: `03-pocs/L2b-classifier-router/surprises.md`, S-3: "Train accuracy stuck at 0.844 (the base rate) for all 300 epochs. The classifier is not learning to separate the classes; it is converging to predict 'cheap' for everything." (Live verified)
- Source: `03-pocs/L2b-classifier-router/surprises.md`, S-2: "The effective decision range is only ~0.15 wide (0.75–0.90)." (Live verified)
