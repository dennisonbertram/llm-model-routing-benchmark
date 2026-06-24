# Lab: L2/L2b — kNN + Logistic Classifier Router

Live verified (L2; L2b; 2026-06-21). Embed prompts, train on the labelset, sweep thresholds.

Back to [index](../index.md).

---

## Goal

Embed all 45 prompts (one-time ~$3e-05 spend), build a kNN router and a logistic
classifier, sweep decision thresholds, and confirm they trace a Pareto curve between
the baselines.

---

## Commands: L2 kNN

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L2-embedding-knn-router/source

python3 test_l2.py -v      # GREEN: 5 live behavioral tests
python3 run_l2.py          # full threshold sweep; writes l2_summary.json
```

Expected best result (22-item test split, live-measured):
```
kNN k=7 thr=0.7: acc=0.955  $0.00136  68% cheap   (88% cost reduction vs strong)
```

---

## Commands: L2b Logistic

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L2b-classifier-router/source

python3 test_l2b.py -v     # GREEN: 6 live behavioral tests
python3 run_l2b.py         # full Pareto sweep; writes l2b_summary.json
```

Expected best result (13-item test set, live-measured):
```
logistic thr=0.80: acc=1.000  $0.000773  54% cheap   (6.3x cheaper than strong)
```

Live confirmation (real embed + predict):
```
prompt: "What is the derivative of x^3 + 2x?"
P(cheap_correct) = 0.8159  → gpt-4o-mini
```

---

## What to observe

- kNN k=1 is already better than always-cheap: 0.909 vs 0.818. Even one neighbor provides signal.
- The threshold sweet spot is sharp: thr=0.6→0.7 jumps kNN accuracy from 0.909 to 0.955.
- Logistic at thr=0.80 achieves oracle accuracy on the test set — the classifier works even though
  P(cheap_correct) clusters tightly between 0.74–0.91 (weak discrimination).
- The embedding cost is negligible (~$3e-05 for 45 prompts) and amortized across all routing decisions.

---

## Honest finding

Live verified (L2b). The logistic classifier faces extreme class imbalance (84% cheap-correct)
and cannot sharply separate hard-math from medium-math in embedding space. It achieves oracle
accuracy because routing even a few uncertain items to strong is sufficient — not because it
has learned fine-grained difficulty features. More labeled data would improve discrimination.

---

## POC sources

- `../03-pocs/L2-embedding-knn-router/`
- `../03-pocs/L2b-classifier-router/`
