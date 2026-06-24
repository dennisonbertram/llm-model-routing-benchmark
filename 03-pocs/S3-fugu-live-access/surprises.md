# Surprises (live)
1. fugu-ultra MATCHES gpt-5.5 accuracy (1.000) but costs 12.2x per task and is 5.6x slower (45s vs 8s) — it burns ~7,700 orchestration tokens per query (the visible answer is a tiny fraction). Orchestration is a cost/latency multiplier, not a free accuracy win.
2. fugu (Mini) was the worst option here: LOWER accuracy (0.905; genuinely missed hm3/hm9 hard math) at 4x the cost of one gpt-5.5 call.
3. fugu-ultra's first run showed 0.905 — but 2 of those "failures" were 120s read TIMEOUTS, not wrong answers. Raising the timeout to 300s gave 1.000. Honest reporting requires separating operational timeouts from capability failures.
4. The usage object exposes orchestration_input_tokens / orchestration_output_tokens separately from the visible prompt/completion tokens — total_tokens = visible + orchestration. This is how you see (and pay for) the multi-agent machinery.
5. The Sakana key authenticated and listed models for hours BEFORE inference worked — inference was gated on an account subscription, not auth (same shape as the Fireworks degree's entitlement gate).
