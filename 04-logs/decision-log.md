# Decision Log

Deterministic decisions + why no user question was asked (2026-06-21/22).

---

## D-1: Keep model pool to gpt-4o-mini / gpt-4.1 / gpt-4o (OpenAI-only routing suite)

**Decision**: The primary routing suite uses only OpenAI models; Anthropic is used as an ensemble
member in X1/X3 only. xAI is confirmed live (L0 smoke) but not in the routing suite.

**Why**: Cross-provider cost normalization requires trusting different billing models. grok-4.3's
native cost diverges ~1.5× from token×price due to billed reasoning tokens. Including it in the
Pareto table would require per-provider cost accounting that obscures the routing signal. The
routing lesson (classifier near oracle) does not depend on the exact provider.

**Not a user question**: The spec's pool definition (`config.CHEAP_DEFAULT=gpt-4o-mini`,
`config.STRONG_DEFAULT=gpt-4.1`) was explicit and locked after L0.

---

## D-2: Report MoA/debate/SC failures as first-class negative findings, not omissions

**Decision**: Ensemble failures are documented prominently in final-report.md, expectation-gap-log,
the Pareto table, and every rank-bearing distillation section. They are not buried in appendices.

**Why**: The spec (NON-NEGOTIABLE honesty rules) requires honest results. The negative finding
that cheap ensembles fail on hard-reasoning-gap workloads is the most operationally important
lesson in the degree. Hiding it would mislead an agent deploying a routing system.

---

## D-3: Use 5-fold CV for all classifier evaluation (no single train/test split in X5/capstone)

**Decision**: X5 and the capstone use 5-fold cross-validation on 45 items. L2b uses 70/30 split.

**Why**: 45 items is too small for a reliable single held-out split. 5-fold CV gives a
leakage-free accuracy estimate using all examples. The "no oracle leakage" test in L2b
verifies the CV folds are correct.

---

## D-4: Mark oracle as "unrealizable ceiling" consistently

**Decision**: Every comparison to oracle includes the qualifier "unrealizable ceiling." The oracle
never appears as a deployment target, only as an upper bound.

**Why**: The oracle peeks at the correct answer. No deployable router can reproduce it. Presenting
it as a target would be misleading.

---

## D-5: Exclude gpt-5/grok-4.3 from full routing suite due to cost and billing complexity

**Decision**: gpt-5 and grok-4.3 confirmed live in L0 smoke but excluded from the 45-task routing
suite. All Pareto comparisons use gpt-4o-mini, gpt-4.1, gpt-4o.

**Why**: (1) Cost discipline: running gpt-5 on 45 tasks × all router types would cost $2–$10;
(2) grok billing divergence (~1.5×) makes fair cost comparison unreliable; (3) the routing
lesson generalizes from the gpt-4.1 vs gpt-4o-mini pool.

---

## D-6: Use text-embedding-3-small (not -large) for routing features

**Decision**: All embedding-based routers use `text-embedding-3-small` (1536 dim, $0.02/1M tokens).

**Why**: The task prompts are short (<50 tokens each). -large (3072 dim, $0.13/1M tokens) adds
6.5× embedding cost for routing decisions that already saturate at 1536 dim on a 45-item suite.
Embedding cost ($0.00003 one-time for 45 prompts) is negligible vs. inference cost either way.

---

## D-7: Accept REASONING_FLOOR=2048 for all o-series / gpt-5 calls rather than per-call tuning

**Decision**: Harness sets `REASONING_FLOOR=2048` for reasoning model families. No per-task
tuning.

**Why**: 2048 is sufficient for the largest math/reasoning answers in the suite (verified: all
answers fit in 100–200 tokens of visible content; 1800+ tokens for reasoning). The alternative
(dynamic budget based on task) adds complexity without improving results for the suite.

---

## D-8: Report FrugalGPT result as a published negative, not a "bug to fix"

**Decision**: L3a is marked status=complete with "HONEST NEGATIVE" in the ledger. The cascade
code is correctly implemented; the failure is the pattern's assumption.

**Why**: The gate was implemented faithfully to the FrugalGPT paper's design. The result is a
calibration failure on this workload, not a code defect. Marking it as a bug would misrepresent
the lesson. The lesson — that self-confidence gates require calibration verification before
deployment — is more useful than a "fixed" result.

---

## D-9: Pin logistic classifier to numpy-only (no sklearn, no pip installs)

**Decision**: The logistic classifier in L2b, X5, and the capstone uses a pure numpy gradient
descent implementation (no sklearn, no scipy).

**Why**: Spec requires Python 3.9 stdlib + numpy only. No pip installs. This also prevents
the "sklearn installed but wrong version" class of errors in agent environments.

---

## D-10: Embed costs are estimated for warm-cache runs; annotate clearly

**Decision**: Where a green-output.txt shows $0.00 for embedding (warm-cache hit), the evidence
annotates the cold-cache estimate (tokens × price) alongside the captured value.

**Why**: The $0.00 warm-cache entry is accurate (no API call made) but misleading if cited as
the embedding cost. The estimate is honest; the distinction between first-run and cached runs is
preserved.
