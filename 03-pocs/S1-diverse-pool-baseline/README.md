# S1 — Diverse OpenRouter pool (the non-saturating pool for AB-MCTS)

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

Since gpt-5.5 saturates authored tasks (S0), the faithful Sakana test needs a DIVERSE,
individually-non-saturating pool — mirroring their ARC-AGI-2 trio (o4-mini + Gemini-2.5-Pro +
DeepSeek-R1). With the OpenRouter key we stood up a cross-architecture pool and verified each model
live through the harness (real cost accounting via OpenRouter `usage.cost` + a price-table fallback):

| model (OpenRouter) | family | role |
|---|---|---|
| `deepseek/deepseek-chat-v3.1` | DeepSeek | pool arm |
| `qwen/qwen-2.5-72b-instruct` | Alibaba | pool arm |
| `google/gemini-2.5-flash-lite` | Google | pool arm |
| `deepseek/deepseek-r1-0528` | DeepSeek (reasoning) | Sakana's exact ARC model (available; slow/pricey) |

## Coding-slice solo baseline (the headroom check; from S2's measured run)

All three pool models score **0.950 hidden / 3-of-4 fully solved** on the hard coding slice — each
~20–75× cheaper per call than gpt-5.5 — but they fail the **same** 4th item's **same** hidden cases.
That **correlated failure = no complementarity** is the key precondition result: AB-MCTS (S2) therefore
cannot exploit diversity to beat the best single model here.

> Operational note (gotcha): a full 21-item × 5-model solo sweep was abandoned because several
> OpenRouter models stall intermittently (a single call can hang within the timeout window),
> making large sequential sweeps fragile. Fix applied in S2: tolerant calls (stalled → empty/score 0),
> a 40s timeout, and incremental cache-save so runs are crash-safe and resumable.

Run: `set -a; . .agent-university/secrets.local.env; set +a; cd source && python3 pool_baseline.py`
