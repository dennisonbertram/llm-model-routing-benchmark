# Troubleshooting: Logistic Router Always Routes Cheap

Live verified (L2b; 2026-06-21). The logistic classifier routes all (or nearly all)
traffic to the cheap model regardless of threshold.

Back to [index](../index.md).

---

## Symptom

- At any threshold τ ≤ 0.70, the router routes 100% (or 95%+) of items to cheap.
- Accuracy equals always-cheap (e.g., 0.844 on this suite).
- Sweeping threshold from 0.7 to 0.9 barely changes routing decisions.
- `P(cheap_correct)` values all cluster in a narrow range (e.g., 0.74–0.91).

---

## Root cause

Live verified (L2b). The classifier learned the base rate rather than fine-grained
difficulty features. When class imbalance is extreme (84% cheap-correct in this suite),
logistic regression converges to a near-constant high probability for all inputs.

Specifically on this suite:
- Only 7/45 items need strong (15.6% negative class).
- The hard items (multi-step combinatorics math) embed similarly to medium math items.
- With this few negatives, the gradient has very little signal to fit a discriminative boundary.

---

## Diagnosis steps

1. Check your P(cheap_correct) distribution:
   ```python
   probs = [predict_proba(w, get_embeddings([p])[0]) for p in all_prompts]
   print(f"min={min(probs):.3f}  max={max(probs):.3f}  mean={sum(probs)/len(probs):.3f}")
   ```
   If all values fall in a narrow range (< 0.2 spread), the classifier is not discriminating.

2. Check class balance in your labelset:
   ```python
   pos = sum(labels)
   print(f"cheap-correct: {pos}/{len(labels)} = {pos/len(labels):.1%}")
   ```
   Below 20% negatives, the gradient signal is very weak.

3. Confirm training converged:
   ```python
   # Print train accuracy after training
   correct = sum(int(predict_proba(w, X[i]) >= 0.5) == y[i] for i in range(len(X)))
   print(f"Train accuracy: {correct/len(X):.3f}")
   ```
   Train accuracy near the base rate (e.g., 0.844) means the model learned the prior, not the pattern.

---

## Fixes

**1. Generate more labeled data.** The RouteLLM paper needed hundreds to thousands of
labeled examples for reliable discrimination. With 45 items, expect weak discrimination.
Generate more (model, task) pairs from your real workload and add them to the labelset.

**2. Try higher thresholds (τ > 0.75).** Even with clustering, the hard items may have
slightly lower P values. Sweeping τ from 0.75 to 0.95 may reveal a discrimination window.
Live finding: on this suite, the effective range was τ ∈ [0.75, 0.90].

**3. Add domain-specific features.** If text features (math keyword count, problem length)
are strong predictors on your workload, add them as additional input features beyond just
the embedding vector.

**4. Try a non-linear classifier.** Logistic regression is linear in embedding space. A
kNN router (L2) or a small neural net may find non-linear boundaries that separate the
hard-math cluster from the easy-math cluster.

**5. Accept the weak discrimination and use the threshold.** Even a weakly-discriminating
logistic router at the right threshold can achieve oracle accuracy on this suite (L2b
thr=0.80: acc=1.000 on 13-item test set). The mechanism is that routing just a few
uncertain items to strong is sufficient.

---

## What NOT to do

- Do NOT lower the threshold below 0.70 hoping to capture hard items — you will just
  collapse to always-cheap behavior (routes nothing to strong).
- Do NOT add oracle features (discipline="math", difficulty="hard") to the training data —
  these are unknown at inference time. That is leakage.

---

## Source

`03-pocs/L2b-classifier-router/README.md` (honest diagnosis section)
