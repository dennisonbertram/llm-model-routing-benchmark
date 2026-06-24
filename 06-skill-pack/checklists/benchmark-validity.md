# Checklist: Benchmark Validity

Live verified (X5; L0; 2026-06-21). Gates before reporting any accuracy or cost number.

Back to [index](../index.md).

---

## Required baselines in every Pareto report

- [ ] always-cheap (gpt-4o-mini): acc=0.844, $0.00166 on this degree's suite.
- [ ] always-strong (gpt-4.1): acc=0.978, $0.02148.
- [ ] random-50% (10-seed average): acc=0.909, $0.01177. Minimum bar to beat for usefulness.
- [ ] oracle (cheapest-correct per task): acc=0.978, $0.00214. Labeled "unrealizable ceiling."

## No leakage

- [ ] Learned routers (kNN, logistic) evaluated on a strict held-out split or 5-fold CV.
      No item in the test set appeared in the training label set.
- [ ] Oracle uses per-item correctness from the L0 labelset — acceptable because oracle is
      labeled unrealizable. But do NOT train a router using oracle knowledge and claim
      it as a deployable result.
- [ ] Heuristic routers may be evaluated on the full suite (no training data used).

## Measurement integrity

- [ ] Every accuracy and cost number comes from a live run or the committed labelset cache.
      No invented numbers, no rounded-away precision.
- [ ] Costs use the reconciled price table (`harness/pricing.py`), not estimates.
- [ ] For deterministic re-runs: use `Cache` to replay cached responses, not re-bill.
- [ ] For ensemble/self-consistency: cache after first live run; warm cache = $0 for re-runs.

## Report content

- [ ] Both accuracy AND cost are reported (not just one metric).
- [ ] $/correct is reported alongside total_usd for fair comparison when suite sizes differ.
- [ ] Negative findings (dominated strategies) are included in the table, not omitted.
- [ ] NEGATIVE label applied to dominated strategies:
      "MoA: acc=0.956, $0.10159 — 4.7x more than strong AND less accurate (NEGATIVE)"
- [ ] The oracle is labeled "unrealizable ceiling" every time it appears.

## Evaluation suite integrity

- [ ] Suite was NOT tuned or modified to favor any specific router.
- [ ] Suite discipline distribution (math/QA/coding) reflects real workload characteristics.
- [ ] The grader is deterministic: numeric match, normalized QA, or unit-test execution.
      No human-in-the-loop grading for claimed live-verified results.
