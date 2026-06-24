# Quality Gate Log

Research / POC / Capstone / Distillation / Evidence gate verdicts (2026-06-21/22).

---

## Research gate — PASS (2026-06-21)

- Pricing documented: gpt-4o-mini ($0.15/$0.60), gpt-4.1 ($2.00/$8.00), gpt-4o ($2.50/$10.00),
  text-embedding-3-small ($0.02/1M). Source URLs + dates in 01-research/pricing-quotas-limits.md.
- Papers reviewed: RouteLLM, FrugalGPT, Hybrid LLM, RouterBench, MoA, AutoMix, Self-Consistency,
  multi-agent debate, LLM-Blender.
- Production routers surveyed: LiteLLM Router, OpenRouter Auto Router/NotDiamond, Martian, Unify,
  RouteLLM OSS, Aurelio semantic-router.
- **Open item**: gpt-5/grok-4.x prices estimated; labeled as such throughout.

---

## L0 POC gate — PASS (2026-06-21)

3/3 behavioral tests. Baseline anchored. Harness frozen. Labelset cached.
Numeric oracle ($0.00214) and baselines ($0.00166 / $0.02148) recorded and referenced by all
subsequent POCs.

---

## L1 POC gate — PASS (2026-06-21)

Threshold sweep complete. τ=0.40 Pareto point documented. No re-billing (uses cached labelset).

---

## L2 POC gate — PASS (2026-06-21)

6/6 tests. Live embed call confirmed (1536-dim vectors, cost > 0 on first run).
k=7,thr=0.7 held-out: acc=0.955. No oracle leakage (test verified).

---

## L2b POC gate — PASS (2026-06-21)

6/6 tests. Live embed confirmation call ($3.8e-07). P range [0.737, 0.907] — narrow band
documented as expected behavior (class imbalance). τ=0.80 test-set acc=1.000.

---

## L3a POC gate — PASS (HONEST NEGATIVE, 2026-06-21)

7/7 tests (1 skipped). Gate non-discriminative on hard math — documented in expectation-gap-log
EG-3. Coding verifier 18/18. FrugalGPT failure is a published finding, not a defect.

---

## L3b POC gate — PASS (2026-06-21)

4/4 live behavioral tests. 0 escalations on 18 coding tasks (all saturated cheap).
Repair path confirmed via synthetic test. $0.001482 (7.5% of all-strong).

---

## L3c POC gate — PASS (2026-06-22)

10/10 tests (4 offline + 6 live wire). openai SDK base_url override confirmed live.
Response `model` field reflects actually-served model (not "auto").

---

## L4 POC gate — PASS (2026-06-22)

3 live curl requests routed. Ledger persisted. RED state (HTTP 502 on missing key) confirmed.
Health probe behavior documented (does not check credential validity — documented in error-log E-7).

---

## L5 POC gate — PASS (2026-06-21)

5/5 live failure modes: invalid slug (404), timeout (retry), max_tokens (400), budget guard,
verifier no-escalate. All handled correctly.

---

## X1 POC gate — PASS (HONEST NEGATIVE, 2026-06-21)

185 live calls billed. MoA acc=0.956 at $0.10159 (4.64× strong AND lower accuracy).
2-layer hard-math MoA: 0.750 (still fails m8, m13). Documented in expectation-gap-log EG-4.

---

## X2 POC gate — PASS (HONEST NEGATIVE, 2026-06-21)

Stochasticity confirmed via fresh samples (nocache=True). SC@5 math: 9/15.
Near-zero variance on hard math confirmed. Cost SC@k=5 = 4.7× cheap = dominated.

---

## X3 POC gate — PASS (HONEST NEGATIVE, 2026-06-21)

190 new calls billed. Debate acc=0.957 = strong, cost=$0.006278 (3.84× strong). Dominated.

---

## X4 POC gate — PASS (PARTIAL, 2026-06-21)

135 verifier calls. AutoMix T=0.67: acc=0.978, $0.006092 (2.85× oracle).
71.6% saving vs always-strong documented. Verifier overhead dominates vs oracle — honest finding.

---

## X5 POC gate — PASS (2026-06-21)

255 cache entries. logistic(0.9) = 0.978 @ $0.00291 (7.4× cheaper than strong). MoA 4.7× strong (47× oracle)
(dominated). Pareto frontier complete. Full benchmark results in source/benchmark_results.json.

---

## Capstone gate — PASS (2026-06-21)

adaptive(thr=0.8) CV: acc=0.978, $0.00257 (8.4× cheaper, 1.20× oracle). 3 live curls.
Budget guard tripped on reqs 5–6. Fallback confirmed. Ledger persisted. OpenAI-compatible wire.

---

## Distillation gate — PASS (2026-06-22)

05-distillation/: gotchas, patterns, recipes, anti-patterns, decision-records authored.
06-skill-pack/: index, quickstart, agent-instructions authored.
"Live verified" present in every rank-bearing section.
Honest negatives (MoA/SC/debate failures, FrugalGPT gate) in first-class sections.

---

## Evidence gate — PASS (2026-06-22)

- All quantitative claims trace to digest / POC evidence.md / green-output.txt.
- No invented numbers. Estimated prices labeled.
- Oracle consistently labeled "unrealizable ceiling."
- Research-supported-but-not-live-verified claims labeled correctly.
- Corpus is ready for indexing.
