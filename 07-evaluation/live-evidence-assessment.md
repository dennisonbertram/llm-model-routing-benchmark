# Live Evidence Assessment — LLM Model Routing Degree

Live verified (2026-06-21/22). Assessment of evidence quality and completeness per POC.

## Overall assessment

Evidence strength: **Strong**. All 15 POCs executed against real providers with committed
green-output.txt files. No mocks used for service evidence. Baseline metrics consistent across
L0, X5, and the capstone — cross-POC numbers reconcile.

## Provider coverage

| Provider | POCs using it | Evidence strength |
|---|---|---|
| OpenAI (gpt-4o-mini, gpt-4.1, gpt-4o) | All 15 | Strong — token/cost measurements throughout |
| OpenAI (text-embedding-3-small) | L2, L2b, X5, capstone | Strong — live embed calls, 1536-dim vectors confirmed |
| Anthropic (claude-haiku-4-5-20251001) | L0, X1, X3 | Strong — smoke confirmed; ensemble member |
| xAI (grok-4.3) | L0 | Smoke confirmed; not used in routing suite |

## Per-discipline evidence quality

| Discipline | Tasks | Grader | Evidence quality |
|---|---|---|---|
| Coding (c1–c18) | 18 | Subprocess unit test (deterministic) | Strongest — fully automated |
| Math (m1–m15) | 15 | Numeric match (extract integer) | Strong — deterministic |
| QA (q1–q12) | 12 | Normalized string match | Strong — deterministic |

## Key cross-POC consistency checks

- L0 baseline (acc 0.844 / 0.978, $0.00166 / $0.02148) is the anchor; X5 and capstone reproduce
  the always-cheap / always-strong values identically (different run, same suite).
- Oracle $0.00214 (L0) matches within $0.00003 of X5 oracle reference — consistent with
  stochastic routing effects being near zero.
- L2b τ=0.80 test-set: oracle-level acc; full suite comparison in X5 (logistic thr=0.9 on
  full CV): 0.978, $0.00291 — both reach oracle-level accuracy as expected.

## Evidence that is live but bounded

- **L2b embedding**: 45 prompts embedded live (confirmed); warm-cache subsequent runs $0.00
  captured in green-output.txt. Cold-cache cost estimated at ≈$2.85e-05 from token×price.
- **L3b escalation path**: repair prompt tested live via one synthetic test; the main 18-task
  run triggered 0 escalations (coding saturates cheap). The repair mechanism works; we just
  didn't need it on this suite.
- **X2 stochasticity**: 5 fresh samples forced on m9/m13 with nocache=True (confirmed near-zero
  variance — cheap model answers are essentially deterministic even at T=0.7 on hard math).

## Evidence scope boundaries

The following are live-verified within this degree:

- Cost-quality Pareto for logistic/kNN/heuristic/MoA/debate/SC/cascade routers on 45 tasks
- Adaptive gateway routing logic (budget guard, fallback, classifier, HTTP) against real providers
- All 5 failure modes (invalid slug, timeout, max_tokens, budget guard, verifier no-escalate)
- OpenAI-compatible wire format (openai SDK base_url override)
- 3-provider liveness and per-provider quirks (grok ticks, reasoning empty-text, o-series params)

The following are research-supported but NOT live-verified in this degree:

- RouteLLM LMSYS benchmark numbers (cite paper; not reproduced)
- MoA wins on general chat benchmarks (cite Wang et al; this degree measured hard-math where it loses)
- FrugalGPT cost savings claimed in the 2023 paper (cite paper; our live run found the gate failed)
- Production router SLA/throughput numbers (LiteLLM, OpenRouter, Martian)
- gpt-5, claude-opus-4.8, grok-4.x pricing at exact production rates (pricing pages captured;
  actual model calls at those prices not made — see known-limitations.md)
