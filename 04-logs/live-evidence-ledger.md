# Live Evidence Ledger

Live verified (2026-06-21/22). One row per POC with live result. All numbers from committed
evidence.md and green-output.txt files. "Live verified. Result: PASS" labels mark live-verified evidence.

---

## L0 — Smoke and Harness

Live verified. Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers live | OpenAI (gpt-4o-mini, gpt-4.1), Anthropic (claude-haiku-4-5-20251001), xAI (grok-4.3) |
| gpt-4o-mini smoke | latency 516ms, cost $2.40e-06, response "OK" |
| claude-haiku smoke | latency 1906ms, cost $3.20e-05, response "OK" |
| grok-4.3 smoke | latency 5232ms, cost $1.06e-03, response "OK" |
| always-cheap (gpt-4o-mini) | acc=0.844, cost=$0.00166 |
| always-strong (gpt-4.1) | acc=0.978, cost=$0.02148 (12.9× cheap) |
| oracle (cheapest-correct) | acc=0.978, cost=$0.00214 (10% of strong) |
| Items only strong solves | 6: m9, m10, m12, m13, m14, m15 (all hard math) |
| Items neither solves | 1: m8 |
| Tests | 3/3 pass, 5.4s |
| Evidence file | 03-pocs/L0-smoke-and-harness/evidence.md |

---

## L1 — Heuristic Router

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1) |
| Best threshold | τ=0.40 |
| Accuracy at τ=0.40 | 0.956 |
| Cost at τ=0.40 | $0.00902 (5.1× oracle, 42% of strong) |
| Oracle targets caught | 5 of 6 |
| False positives (cheap→strong) | 6 |
| Features | word count (40%), reasoning cues (35%), clause structure (15%), digit density (10%) |
| Evidence file | 03-pocs/L1-heuristic-router/evidence.md |

---

## L2 — Embedding k-NN Router

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (text-embedding-3-small, gpt-4o-mini, gpt-4.1) |
| Live embed call | 45 prompts → 1536-dim vectors, cost ≈$0.00003 (first cold run) |
| Best held-out point | k=7, thr=0.7: acc=0.955, 88% cost reduction vs strong |
| Tests | 6/6 pass, 0.369s |
| Evidence file | 03-pocs/L2-embedding-knn-router/evidence.md |

---

## L2b — Classifier Router

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (text-embedding-3-small — live confirm embed call $3.8e-07) |
| Train set | 32 items (70% stratified) |
| Test set | 13 items (30% held-out) |
| P(cheap) range on test | [0.737, 0.907] (narrow band — class imbalance effect) |
| Best routing acc (τ=0.80) | 1.000 (test-set, 13 items) |
| Best routing cost (τ=0.80) | $0.000773 (test-set; oracle for same: $0.000540, strong: $0.004868) |
| Tests | 6/6 pass |
| Evidence file | 03-pocs/L2b-classifier-router/evidence.md |

---

## L3a — FrugalGPT Cascade

Live verified. Result: PASS (HONEST NEGATIVE)

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini gate + verifier; gpt-4.1 escalation) |
| Gate calls | 27 math/QA confidence gates + 18 coding YES/NO verifier calls |
| Cascade accuracy (any threshold) | 0.844 = always-cheap (gate non-discriminative) |
| Cascade cost (any threshold) | $0.00391 (2.4× always-cheap, no accuracy gain) |
| Confidence gate behavior | gpt-4o-mini reports 0.9 for all 6 hard-math wrong answers; 0.0 for 2 easy correct answers |
| Coding verifier | 18/18 correct, 0 false accepts, 1 false escalation (c13) |
| Tests | 7/7 pass (1 skipped) |
| Evidence file | 03-pocs/L3a-frugalgpt-cascade/evidence.md |

---

## L3b — Harness Routing (Coding Agent)

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1) |
| All-cheap accuracy (18 coding tasks) | 1.000 |
| All-cheap cost | $0.001482 |
| All-strong cost | $0.019672 |
| Routed cost | $0.001482 (identical to all-cheap — 0 escalations) |
| Cost ratio strong/cheap | 13.25× |
| Grader | subprocess unit-test execution (deterministic) |
| Repair path | verified via synthetic test — gpt-4.1 repaired stubbed fizzbuzz correctly |
| Tests | 4/4 live behavioral tests pass |
| Evidence file | 03-pocs/L3b-harness-routing-coding-agent/evidence.md |

---

## L3c — OpenAI-Compatible Gateway Integration

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-22 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1, gpt-4.1-nano) |
| Cheap route (auto, factual) | gpt-4o-mini, tokens 14/7, cost $6.30e-06, latency 1010ms |
| Strong route (auto, combinatorics) | gpt-4.1, tokens 31/328, cost $0.002686, latency 3042ms |
| Passthrough (forced gpt-4.1-nano) | gpt-4.1-nano, tokens 15/4, cost $3.10e-06, latency 957ms |
| openai SDK | base_url="http://127.0.0.1:8770/v1" override confirmed; response model=gpt-4o-mini, content="The capital of France is Paris." |
| Tests | 10/10 (4 offline + 6 live wire format), 8.981s |
| Evidence file | 03-pocs/L3c-openai-compatible-gateway-integration/evidence.md |

---

## L4 — Routing Gateway Runtime

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-22 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1) |
| Req 1: auto factual | decision=default_cheap → gpt-4o-mini, tokens 14/7, cost $0.0000063, latency 763ms |
| Req 2: auto combinatorics | decision=keyword:combinatorics → gpt-4.1, tokens 27/128, cost $0.001078, latency 1700ms |
| Req 3: forced model | decision=forced → gpt-4o-mini, tokens 11/2, cost $0.0000029, latency 608ms |
| Ledger | source/cost-ledger.jsonl persisted with 3 entries |
| RED state | HTTP 502 on missing OPENAI_API_KEY confirmed (red-output.txt) |
| Evidence file | 03-pocs/L4-routing-gateway-runtime/evidence.md |

---

## L5 — Failure Modes and Observability

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini live calls for each failure mode) |
| FM1: invalid slug | gpt-9000-doesnt-exist → HTTP 404, fallback to gpt-4o-mini (444ms, $0.00000375) |
| FM2: sub-ms timeout | timeout=0.001s → URLError "timed out", retry timeout=30s → success (641ms, $0.00000375) |
| FM3: max_tokens=999999 | HTTP 400 "supports at most 16384", fallback max_tokens=64 → success ($0.00000375) |
| FM4: budget guard | 4 tasks, cap=$0.000015; 3 accepted ($0.00001140 total), 1 refused (no_model_fits_budget) |
| FM5: verifier no-escalate | 17×23=391 answered correctly; escalation not triggered; verify_numeric unit-tested |
| Evidence file | 03-pocs/L5-failure-modes-and-observability/evidence.md |

---

## X1 — Mixture of Agents

Live verified. Result: PASS (HONEST NEGATIVE)

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1-mini, gpt-4o); Anthropic (claude-haiku-4-5-20251001) |
| Live calls (first paying run) | 185 misses (paid), 35 hits |
| MoA accuracy (45 tasks) | 0.9556 |
| MoA cost | $0.09966 |
| vs always-cheap | 60.0× more expensive |
| vs always-strong | 4.64× more expensive AND lower accuracy (0.9556 vs 0.9778) |
| 2-layer hard-math MoA acc | 0.750 (still fails m8, m13) |
| Verdict | DOMINATED on this workload — cheap ensemble does NOT beat single strong model |
| Evidence file | 03-pocs/X1-mixture-of-agents/evidence.md |

---

## X2 — Self-Consistency Vote

Live verified. Result: PASS (HONEST NEGATIVE)

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini T=0.7; gpt-4.1 T=0 baseline) |
| cheap@1 (15 math) | acc=0.533 |
| strong@1 (15 math) | acc=0.933 |
| SC@k=5 (15 math) | acc=0.600 (barely above k=1) |
| hard math (7 items) SC@k=5 | acc=0.143 vs strong acc=0.857 |
| Stochasticity confirmed | m9/m13: 5 fresh samples near-identical wrong answers at T=0.7 |
| Cost SC@k=5 | 4.7× cheap baseline |
| Verdict | SC@k=5 closed 17% of hard-math gap at 4.7× cheap cost — economically dominated vs routing to strong |
| Evidence file | 03-pocs/X2-self-consistency-vote/evidence.md |

---

## X3 — Multi-Agent Debate

Live verified. Result: PASS (HONEST NEGATIVE)

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini, gpt-4.1-mini, gpt-4.1); Anthropic (claude-haiku-4-5-20251001) |
| Live calls | 190 new calls billed |
| debate:3x1r accuracy (23 items) | 0.9565 (= always-strong) |
| debate:3x1r cost | $0.006278 |
| vs always-strong cost | 3.84× more expensive |
| Hard math (debate) | acc=1.000, cost=$0.001590 (vs strong: $0.000520) |
| Verdict | Matches strong accuracy at 3.84× strong cost — DOMINATED |
| Evidence file | 03-pocs/X3-multi-agent-debate/evidence.md |

---

## X4 — Verification Cascade (AutoMix)

Live verified. Result: PASS (PARTIAL — 2.85× oracle cost)

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (gpt-4o-mini verifier; gpt-4.1 escalation) |
| Verifier calls | 135 fresh calls (k=3, 45 items) |
| AutoMix T=0.67 accuracy | 0.9778 |
| AutoMix T=0.67 cost | $0.006092 |
| vs always-strong | 71.6% cost savings |
| vs oracle ($0.002140) | 2.85× more expensive |
| Verifier calibration | high-confidence bucket (0.67–1.00, n=33): 100% cheap-correct |
| Verdict | Beats always-strong by 71.6%; loses to oracle by 2.85× (verifier overhead dominates) |
| Evidence file | 03-pocs/X4-verification-cascade-automix/evidence.md |

---

## X5 — Router Benchmark Pareto

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (embeddings + chat); Anthropic (ensemble member) |
| Cache entries after first run | 255 entries; 0 misses on re-run |
| random-50% (10 seeds) | acc=0.909, cost=$0.01177 — dominated by all learned routers |
| heuristic | acc=0.933, cost=$0.00520 |
| k-NN(k=5) CV | acc=0.889, cost=$0.00204 |
| k-NN(k=3) CV | acc=0.933, cost=$0.00221 |
| logistic(thr=0.7) CV | acc=0.956, cost=$0.00233 |
| logistic(thr=0.9) CV | acc=0.978, cost=$0.00291 (= strong acc, 7.4× cheaper) |
| MoA | acc=0.956, cost=$0.10159 (4.7× strong, 47× oracle; AND lower acc) |
| SC@5 math | 9/15 vs cheap 8/15 vs strong 14/15 |
| Evidence file | 03-pocs/X5-router-benchmark-pareto/evidence.md |

---

## L-Capstone — Adaptive Routing Gateway

Live verified. Result: PASS

| Item | Value |
|---|---|
| Date | 2026-06-21 |
| Providers | OpenAI (chat + embeddings); Anthropic (ensemble member) |
| CV benchmark (5-fold) adaptive(thr=0.8) | acc=0.978, cost=$0.00257 |
| vs always-strong ($0.02148) | 8.4× cheaper |
| vs oracle ($0.00214) | 1.20× oracle cost |
| cheap route fraction | ~71% |
| Live curl: "capital of France" | p_cheap=0.97 → gpt-4o-mini → "Paris." |
| Live curl: "arrange BALLOON" | p_cheap=0.38 → gpt-4.1 → "1260" (correct) |
| Live curl: forced gpt-4o-mini | decision=forced, honored |
| Budget guard ($0.00025 cap) | reqs 5–6 forced to cheap |
| Fallback | bad strong slug → 404 → fell back to gpt-4o-mini (fallback_from=yes) |
| Ledger | gateway-ledger.jsonl persisted |
| Evidence file | 03-pocs/L-capstone-adaptive-routing-gateway/evidence.md |
