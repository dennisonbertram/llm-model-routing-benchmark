# Lesson: Heuristic Routing

Live verified (L1; 2026-06-21). Rule-based routing using prompt text features.

Back to [index](../index.md).

---

## What it is

A heuristic router assigns a complexity score to each prompt using only text features
(word count, reasoning keywords, clause structure, digit density) and routes to cheap or
strong based on whether the score exceeds a threshold. No embeddings, no model calls, no
training data required.

---

## Live results (L1; 45-task suite)

Live verified. From `03-pocs/L1-heuristic-router/README.md`.

| Router | accuracy | cost (45 tasks) | cost vs strong |
|--------|----------|-----------------|----------------|
| always-cheap (gpt-4o-mini) | 0.844 | $0.00166 | 8% |
| heuristic (thr=0.40) | **0.956** | **$0.00902** | 42% |
| always-strong (gpt-4.1) | 0.978 | $0.02148 | 100% |
| oracle (unrealizable ceiling) | 0.978 | $0.00176 | 8% |

The heuristic at thr=0.40 achieves +11.2pp accuracy over always-cheap at 42% of always-strong
cost. It routes 11 items to strong (6 oracle targets + 5 false positives).

---

## Threshold sweep (live-measured)

Live verified. Higher threshold = routes fewer items to strong = lower cost, lower accuracy.

```
thr=0.20  acc=0.978  $0.02002  (near strong, expensive)
thr=0.30  acc=0.956  $0.01402
thr=0.40  acc=0.956  $0.00902  <- best tradeoff (selected)
thr=0.50  acc=0.889  $0.00317  (rapid accuracy drop)
thr=0.60  acc=0.844  $0.00298  (equals always-cheap accuracy)
thr=0.70+ acc=0.844  ~$0.00177  (routes nothing — same as always-cheap)
```

---

## Feature weighting

Live verified. From the committed `run_l1.py`:

```python
complexity_score = (
    0.40 * word_score +      # word count > 15: up to 1.0
    0.35 * cue_score +       # reasoning keywords: "how many", "permutations", etc.
    0.15 * clause_score +    # commas + semicolons + " and "
    0.10 * digit_score       # digit density
)
```

Word count is the strongest single predictor. Reasoning keywords are second.
Digit density alone is a poor signal (easy arithmetic has high digit density; hard
combinatorics may have low density).

---

## Honest ceiling

Live verified. The best heuristic (thr=0.20) matches strong accuracy at 11.3x oracle cost.
No prompt-only heuristic reaches oracle efficiency. To approach the oracle, move to a
predictive router (L2/L2b). Heuristics plateau around 96% accuracy.

False positive rate at thr=0.40: 5 items over-routed to strong (m8, c2, c7, c13, c18).
False negative rate: 1 oracle target missed (m10, multi-step algebra, scores 0.261 < 0.40).

---

## When to use

- No training data and no embedding budget.
- Workload has strong structural signals (math word problems, code generation vs. factual QA).
- Acceptable to leave ~4–5pp accuracy on the table vs a trained classifier.

## When NOT to use

- Hard tail items look semantically like medium items in text features (the heuristic
  cannot distinguish "permutations" difficulty levels).
- You need to approach oracle efficiency — use the logistic classifier instead.

---

## Recipe

[recipes/R-001-heuristic-router.md](../recipes/R-001-heuristic-router.md)

## POC source

`../03-pocs/L1-heuristic-router/`
