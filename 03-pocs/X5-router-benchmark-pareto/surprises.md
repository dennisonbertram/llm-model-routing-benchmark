# Surprises (live)

1. **The trained logistic router dominates always-strong.** At thr=0.9 it reaches 0.978 accuracy
   (identical to gpt-4.1) for $0.00291 vs $0.02148 — a 7.4x cost cut — landing essentially on the
   oracle ceiling. A 1536-dim embedding + a numpy logistic regression trained on 36 examples is
   enough to identify the ~6 hard-math tasks that need the strong model.

2. **Mixture-of-Agents was 4.7x more expensive than a single strong model (and 4.7x the oracle cost) AND less accurate**
   (0.956 vs 0.978) on this suite. The "cheap models together beat SOTA" hypothesis FAILED here:
   ensembling helps only when the cheap members are individually competitive with errors that
   cancel — but our gap is a hard-math tail no cheap model handles, so three of them agree on the
   wrong answer.

3. **Self-consistency added almost nothing on hard math** (8->9 of 15 vs strong's 14). Voting
   amplifies a model's existing distribution; it cannot supply reasoning the base model lacks.

4. **Random routing is strictly dominated** by every learned router — confirming the routers are
   learning real signal, not just trading accuracy for cost along the trivial line.

5. **k=5 underperformed k=3** for k-NN: with only ~36 training neighbors, a larger k blurs the
   sharp "hard-math" cluster. Predictive routers are sensitive to train-set size at this scale.
