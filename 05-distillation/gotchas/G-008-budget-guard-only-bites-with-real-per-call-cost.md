# G-008: Cost-budget guard only bites when per-call cost is real — short answers are ~$0.0001 each

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: L-capstone-adaptive-routing-gateway, L5-failure-modes-and-observability

## What

Live verified. In the capstone gateway, the budget guard used a $0.00025 cap (approximately 2 strong calls) to demonstrate it tripping. At that cap, requests 5 and 6 were forced to cheap. Without this deliberately tight cap, the guard would never have engaged: each `gpt-4.1` call on short answers cost approximately $0.0001.

From L5 evidence: `gpt-4o-mini` charges approximately $0.00000360–0.00000405 per simple factual question. The minimum call cost is dominated by the fixed prompt-template token overhead, not the output length.

## Why it matters

An agent that adds a budget guard and expects it to fire on typical short-answer routing workloads will be surprised to find it never triggers. The guard is a spend ceiling, not an accuracy control, and its practical threshold must be calibrated against the actual per-call cost of your specific workload — not a round number.

The inverse trap: setting a very tight cap ($0.0001 or less) on a short-answer workload will force every strong-model call cheap, defeating the routing strategy entirely, even for items that genuinely need the strong model.

## Root cause

Router cost guards are typically designed for production workloads with substantial output tokens (e.g., code generation, long-form text). For short factual and math answers, the `gpt-4.1` cost is ~$0.0001 per call, which means a $0.01 daily cap accommodates ~100 strong calls — far more than most demos require. The guard's granularity breaks down at per-call costs this small.

Additionally, the "call-then-check" guard pattern (L5) pays for the call even when refusing it, because cost is only known after the provider returns usage counts. A pre-call token-count estimator would avoid this but requires predicting output length.

## Fix

1. Calibrate the budget cap against your real workload. Measure actual per-call cost at production token counts before setting the cap value.
2. For long-output tasks (code, essays), the guard engages naturally — no special calibration needed.
3. For short-output tasks, either raise the per-request threshold or switch to a per-session or per-hour spend limit rather than a per-call cap.
4. Document the cap in the gateway config with a comment showing the expected call count it permits (`$0.00025 cap ≈ 2.5 strong calls at $0.0001 each`).
5. If using a "call-then-check" pattern, accept that refused calls still incur a small cost. Use a pre-call token-count estimate if zero-cost refusal is required.

## Regression note

In the gateway test suite, include one test with a deliberately tight cap (below the cost of a single strong call) to verify the guard fires. Document the cap value used in the test and why it is below a normal production threshold.

## Evidence

- Source: `03-pocs/L-capstone-adaptive-routing-gateway/surprises.md`, item 2: "Our answers are short, so a gpt-4.1 call here is ~$0.0001; we had to set a $0.00025 cap (≈2 strong calls) to demonstrate the guard tripping. In production with long outputs the cap matters far sooner — the guard is a spend ceiling, not an accuracy control." (Live verified)
- Source: `03-pocs/L5-failure-modes-and-observability/surprises.md`: "gpt-4o-mini charges ~$0.00000360–0.00000405 for a simple factual question. The cost is dominated by the fixed prompt tokens (the prompt template overhead) rather than the output. This means the minimum call cost for any question to gpt-4o-mini is roughly $0.0000036, regardless of how short the answer is. Budget guards need to account for this floor." (Live verified)
- Source: results-digest.md, Gotchas item 8: "Cost-budget guard only bites when per-call cost is real (short answers are ~$0.0001 each)." (Live verified)
- Source: results-digest.md, capstone: "Budget guard ($0.00025 cap): reqs 5–6 forced cheap." (Live verified)
