# Known Limitations — LLM Model Routing Degree

Live verified (2026-06-21/22). Honest scope boundaries for every claim in this degree.

## L-1: Small suite (45 tasks) — results may not generalize

**What it means**: All accuracy and cost numbers come from a 45-item suite (15 math, 12 QA,
18 coding). Router Pareto curves, threshold selections, and ensemble comparisons are measured
on this suite specifically.

**Why it matters**: The best logistic threshold (τ=0.9 in X5) and the best kNN k (k=3 in X5)
were selected via 5-fold CV on the same 45 items. On a different distribution, the optimal
hyper-parameters would shift. Do not deploy with τ=0.9 without re-calibrating on your workload.

**What holds regardless**: The structural finding — that a trained classifier can match strong-model
accuracy at a fraction of the cost, and that ensemble approaches are dominated on a hard-tail
workload — is robust to suite size. The specific numbers are suite-specific.

## L-2: Hard-math-concentrated difficulty gap

**What it means**: The routing opportunity in this suite is almost entirely in 6 hard-math tasks
(m9, m10, m12, m13, m14, m15). 18/45 coding tasks are saturated by the cheap model. 12/12 QA
tasks are saturated by the cheap model. The "gap" is not a general coding/QA gap.

**Why it matters**: Findings about ensemble failures (MoA, SC, debate) are specific to hard-math
tasks. On a workload with more diverse failure modes (e.g., complex reasoning QA, long-context
coding), ensemble results could differ. The FrugalGPT failure is also specific to hard-math
self-confidence; coding verifier worked well.

**What holds regardless**: A routing benchmark must include tasks that at least ONE of the models
fails. If all tasks are saturated, routing is trivially "always cheap." This suite's hard-math
concentration is a valid design choice; just report it as a boundary condition.

## L-3: gpt-5 / claude-opus-4.8 / grok-4.x prices are estimated

**What it means**: Pricing for gpt-5 ($2.50/$10.00 in/out per 1M tokens estimated), claude-opus-4.8,
and grok-4.x were sourced from pricing pages at the time of research (2026-06-21). These are
subject to change.

**Why it matters**: Cost ratio claims using these models (e.g., "routing is X× cheaper vs gpt-5")
are based on estimated prices. Actual API bills may differ.

**What holds regardless**: The routing cost numbers for the actual suite pool (gpt-4o-mini,
gpt-4.1, gpt-4o) are live-measured from real token counts × documented pricing. Those numbers
are unaffected by gpt-5/grok price uncertainty.

## L-4: Classifier and k-NN trained on same suite they're evaluated on (CV, not true held-out)

**What it means**: In X5 and the capstone, router training and evaluation use 5-fold cross-validation
on the same 45 items. L2b uses a 70/30 train/test split of the same suite. There is no truly
out-of-distribution held-out evaluation.

**Why it matters**: These are tight upper-bound estimates of what a deployed router would achieve
on novel queries. In production, the task distribution will differ from the training distribution.

**Mitigation**: The 5-fold CV is leakage-free (training and evaluation folds are disjoint). The
CV results are the honest in-distribution number. The label "no oracle leakage" is accurate.
A production deployment should recalibrate on a representative sample from the real workload.

## L-5: Oracle is unrealizable

**What it means**: The oracle ($0.00214, acc=0.978) routes each task to the cheapest model that
answers correctly — which requires knowing the answer in advance. No deployable router achieves it.

**Why it matters**: Some comparisons (e.g., "AutoMix is 2.85× oracle cost") use oracle as the
reference. The oracle is a theoretical ceiling, not a deployment target.

**Consistent labeling**: Every mention of the oracle in this degree includes the qualifier
"unrealizable ceiling."

## L-6: Latency not systematically optimized

**What it means**: All POCs record latency per call but no POC optimizes for latency-first routing.
The adaptive gateway routes on cost-quality only; latency-aware routing (e.g., route cheap not
just for cost but for speed) is not measured.

**Why it matters**: In real-time applications, latency-first routing to a smaller/faster model
may be the priority over cost-quality optimization.

## L-7: Single-round interaction only

**What it means**: All tasks are single-turn (one prompt → one answer). Multi-turn conversation
routing — where routing decisions depend on conversation history — is not covered.
