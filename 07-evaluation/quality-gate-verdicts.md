# Quality Gate Verdicts — LLM Model Routing Degree

Live verified (2026-06-21/22).

## Research gate

**PASS**

- Pricing for gpt-4o-mini, gpt-4.1, gpt-4o, text-embedding-3-small documented with URLs + dates in
  `01-research/pricing-quotas-limits.md`.
- Papers covered: RouteLLM (LMSYS), FrugalGPT (Chen/Zaharia/Zou), Hybrid LLM (Ding et al),
  RouterBench (Hu et al), MoA (Wang et al, Together), AutoMix (Madaan et al), Self-Consistency
  (Wang et al), multi-agent debate (Du et al). Production routers: LiteLLM, OpenRouter, Martian.
- pricing.py reconciled with official pages; cost formulas used throughout.
- gpt-5/opus-4.8/grok-4.x prices are ESTIMATED (pricing page scraped at time of research;
  actual calls not made at these prices — see known-limitations.md).

## POC gate

Live verified. **PASS — 15/15 POCs green**

| POC | Verdict | Key evidence |
|---|---|---|
| L0-smoke-and-harness | PASS | 3 providers live; baseline acc 0.844/0.978; oracle $0.00214 |
| L1-heuristic-router | PASS | τ=0.40: acc 0.956, $0.00902 |
| L2-embedding-knn-router | PASS | k=7,thr=0.7 held-out: acc 0.955, 88% cost reduction |
| L2b-classifier-router | PASS | τ=0.80 test-set: oracle-level acc, 6.3× cheaper than strong |
| L3a-frugalgpt-cascade | PASS (HONEST NEGATIVE) | acc 0.844 = always-cheap; gate non-discriminative |
| L3b-harness-routing-coding-agent | PASS | 1.000 acc, $0.00148 (7.5% all-strong), 0 escalations |
| L3c-openai-compatible-gateway-integration | PASS | 10/10 live wire tests; openai SDK base_url works |
| L4-routing-gateway-runtime | PASS | 3 live curls routed; ledger persisted; RED=HTTP 502 missing key |
| L5-failure-modes-and-observability | PASS | 5/5 live failure modes triggered + handled |
| X1-mixture-of-agents | PASS (HONEST NEGATIVE) | MoA: acc 0.956, $0.10159 — 4.7× strong cost, lower accuracy |
| X2-self-consistency-vote | PASS (HONEST NEGATIVE) | SC@5 math: 9/15 vs strong 14/15 |
| X3-multi-agent-debate | PASS (HONEST NEGATIVE) | debate: acc 0.957, $0.006278 — 3.84× strong cost |
| X4-verification-cascade-automix | PASS (PARTIAL) | acc 0.978, $0.006092 — 2.85× oracle cost |
| X5-router-benchmark-pareto | PASS | logistic(0.9): 0.978 @ $0.00291, 7.4× cheaper than strong |
| L-capstone-adaptive-routing-gateway | PASS | adaptive(thr=0.8): 0.978 @ $0.00257, 8.4× cheaper |

## Capstone gate

Live verified. **PASS**

Live adaptive gateway combines:
- Logistic classifier (embedding features, 5-fold CV, no label leakage)
- Budget guard ($0.00025 cap, tested live — reqs 5–6 forced to cheap)
- Provider fallback (bad slug → 404 → fell back to gpt-4o-mini, request answered)
- OpenAI-compatible HTTP endpoint (curl + openai SDK verified)
- Routing ledger persisted (gateway-ledger.jsonl)

Benchmark: adaptive(thr=0.8) acc=0.978, $0.00257 (8.4× cheaper than always-strong, 1.20× oracle).

## Distillation gate

**PASS**

Gotchas, patterns, recipes, anti-patterns, and decision-records authored in `05-distillation/`.
Skill-pack authored in `06-skill-pack/` (index, quickstart, agent-instructions).
"Live verified" phrase present in every rank-bearing section.
Honest negatives (MoA failure, FrugalGPT gate failure, SC marginal gain) are first-class content,
not footnotes.

## Evidence gate

**PASS**

- Every quantitative claim traces to a POC's evidence.md or the results-digest.md.
- No invented numbers. Estimated prices labeled as estimated (gpt-5, grok-4.x).
- Oracle is consistently labeled "unrealizable ceiling" — not compared as if achievable.
- FrugalGPT and MoA failures documented without softening.
- "Research supported but not live verified" applied to paper claims not reproduced here
  (e.g., RouteLLM LMSYS benchmark numbers, MoA external benchmark wins on different workloads).
