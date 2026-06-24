# Future Work — LLM Model Routing Degree

Research-supported proposed directions. Items are NOT committed or scheduled.
Evidence status: Research supported but not live verified (unless a specific POC is cited).

## FW-1: OpenRouter open-model tier (unblock BL-1)

Add an OpenRouter backend to the adaptive gateway. Use Qwen2.5-72B or DeepSeek-V3 as the
"cheap" tier ($0.07–$0.14/1M out) and compare against the current gpt-4.1 strong tier.
Expected: similar routing benefit, lower absolute costs, native per-generation cost accounting
via `GET /generation`. Prerequisite: OPENROUTER_API_KEY in secrets.

## FW-2: Latency-aware routing

Add a latency dimension to the Pareto frontier (cost × latency × quality 3D surface).
Route to the fastest model below a latency SLA, then optimize cost within that constraint.
Useful for real-time agent steps where sub-second response matters more than per-call cost.

## FW-3: Selective MoA on predicted hard items

MoA failed on the full suite (4.7× strong cost, lower accuracy) but may work when applied only
to items the classifier predicts as hard. Gate X1 behind the L2b classifier:
- If p_cheap < τ: run MoA instead of routing straight to strong.
- Measure whether 3-cheap-ensemble beats single strong on the 6 hard items in isolation.
Expected: MoA wins on hard items if the cheap members are individually partially correct (they
are not in this suite — all produce the same wrong intermediate steps — so the result may still
be negative).

## FW-4: RouteLLM-style online learning with query logs

The classifier in L2b and the capstone is trained offline on 32 labeled examples. A production
system can accumulate labels from verified answers and periodically retrain. Measure accuracy
improvement as the label set grows from 32 → 100 → 500 items. Expected: accuracy approaches
oracle more closely as the training set grows; threshold stability improves.

## FW-5: Multi-turn routing with context windows

Extend the task suite to multi-turn interactions (a coding agent's plan/edit/verify steps).
Route each turn independently vs. route based on full conversation history. Relevant for
harness routing (L3b) in production agents where step difficulty correlates across turns.

## FW-6: Router calibration across workload shifts

Deploy the logistic classifier trained on this suite against a different workload (e.g., SQL
generation, document summarization) without re-training. Measure accuracy degradation. This
tests whether the embedding-based router transfers or requires per-domain calibration.

## FW-7: Anthropic models in the routing pool (unblock BL-4)

Add claude-sonnet-4-6 as `STRONG_DEFAULT` and claude-haiku-4-5-20251001 as `CHEAP_DEFAULT`.
Verify that the harness cost model handles cross-provider price normalization correctly.
Measure whether the routing signal (embedding k-NN) generalizes across provider boundaries.

## FW-8: Streaming + partial-output routing

The current gateway returns complete responses. A streaming gateway could abort a cheap-model
generation mid-stream if the output looks wrong (e.g., intermediate reasoning token count
exceeds expected), then re-route to strong. This is the "speculative routing" pattern.
Not covered; research-supported from recent streaming router papers.
