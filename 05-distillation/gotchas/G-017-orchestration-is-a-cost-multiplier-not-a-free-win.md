# G-017: Multi-agent orchestration is a cost/latency multiplier, not a free accuracy win

**Evidence: Live verified (2026-06-22, S2 + S3).**

## Symptom
You reach for a multi-agent orchestrator (Mixture-of-Agents, AB-MCTS tree search, or a hosted
conductor like Sakana Fugu) expecting "many models > one model," and instead pay several times more
for the same — or worse — accuracy.

## Live root cause (measured two ways)

**S3 — the real Sakana Fugu vs a single GPT-5.5 call, 21 hard tasks, identical graders:**

| model | accuracy | $/task | latency | orchestration tokens/task |
|---|---|---|---|---|
| gpt-5.5 (single call) | 1.000 | $0.0097 | 8.1 s | 0 |
| fugu (Mini) | 0.905 | $0.039 (4.0×) | 12.7 s | 0 |
| fugu-ultra (conductor) | 1.000 | $0.119 (**12.2×**) | 45.4 s | **7,719** |

`fugu-ultra` *matches* GPT-5.5 but burns ~7,700 internal orchestration tokens per query → 12.2× cost,
5.6× latency. `fugu` (Mini) is *less* accurate AND 4× pricier than one frontier call.

**S2 — adaptive multi-model AB-MCTS over a cheap diverse pool, hard coding (hidden tests):** AB-MCTS,
repeated sampling, and best-single all plateau at 0.950; none reach GPT-5.5's 1.000 (correlated
errors → no complementarity to exploit). AB-MCTS *is* more sample-efficient than repeated sampling
(same accuracy at 8× fewer calls), but efficiency ≠ a capability gain.

## Fix / decision rule
- For tasks a single strong model can solve, **route to the right single model** — it dominates
  orchestration on cost, latency, AND accuracy. (This degree's whole thesis; X5/X6.)
- Reserve orchestration for the **genuine capability frontier**, where (a) no single model solves the
  task, (b) you have a **reliable verifier** (code tests, formal check — not self-confidence; see
  G-006/L3a), and (c) the pool's errors are **uncorrelated/complementary**. Even there the margins are
  small (Sakana's published Fugu wins are sub-1-point) and the compute premium is large.
- Always price the **orchestration tokens**, not just the visible answer tokens — `usage` exposes
  `orchestration_input_tokens` / `orchestration_output_tokens`; `total = visible + orchestration`.

## Regression note
S3's first run scored fugu-ultra 0.905 because two queries hit a 120 s read-timeout (the conductor is
slow), not because the answers were wrong — raising the timeout to 300 s gave 1.000. Separate
**operational timeouts from capability failures** when grading slow orchestrators.
