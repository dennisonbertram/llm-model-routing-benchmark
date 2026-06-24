# X1 — Mixture-of-Agents

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

## What this proves

Mixture-of-Agents (MoA) — Wang et al., "Mixture-of-Agents Enhances Large Language Model
Capabilities" (Together AI, 2024) — routes each query through N cheap proposer models, then
synthesises a final answer via one aggregator. This POC measures the real cost-quality
tradeoff of MoA against single-model baselines on the 45-task harness suite.

**Architecture:**

```
query
  ├─ gpt-4o-mini        ─┐
  ├─ gpt-4.1-mini       ─┤── propose ──► gpt-4o (aggregator) ──► final answer
  └─ claude-haiku-4-5   ─┘
```

Optionally: 2-layer variant on hard math — layer-1 aggregation (gpt-4o) feeds into a
second synthesis pass (gpt-4.1).

## Live verified results table

Measured live over all 45 tasks (math=15, qa=12, coding=18). 2026-06-21.

| Router | acc | total cost (45 tasks) | vs cheap cost |
|---|---|---|---|
| always-cheap (`gpt-4o-mini`) | 0.844 | $0.00166 | 1.0× |
| **MoA** (3 cheap → gpt-4o agg) | **0.956** | **$0.09966** | **60.0×** |
| always-strong (`gpt-4.1`) | 0.978 | $0.02148 | 12.9× |

## Per-discipline breakdown

Live verified. All three disciplines measured over the real suite.

| Discipline | MoA acc | cheap acc | strong acc | n |
|---|---|---|---|---|
| math | 0.867 | 0.533 | 0.933 | 15 |
| qa | 1.000 | 1.000 | 1.000 | 12 |
| coding | 1.000 | 1.000 | 1.000 | 18 |

## 2-layer MoA on hard math

Live verified. Only tested on the 8 hard math items (m8–m15) where the gap is largest.

| Strategy | acc (n=8) | cost |
|---|---|---|
| single cheap (gpt-4o-mini) | 0.125 | — (from L0 cache) |
| single strong (gpt-4.1) | 0.875 | — (from L0 cache) |
| MoA-1L (3 cheap + gpt-4o agg) | 0.750 (hard math only) | $0.00346 |
| MoA-2L (3 cheap + gpt-4o + gpt-4.1 agg) | 0.750 | $0.00546 |

2-layer MoA did not improve on single-layer for this problem set.

## Honest verdict

Live verified. These numbers are measured, not projected.

MoA **improves materially over single cheap** (0.956 vs 0.844 accuracy, +11.2pp) on the full
suite. However:

1. **MoA does NOT match single strong** (0.956 vs 0.978, −2.2pp) on this suite.
2. **MoA costs 4.64× more than single strong** ($0.0997 vs $0.0215) — the opposite of the
   cost-saving premise. A single gpt-4.1 call is both cheaper AND more accurate than MoA here.
3. **MoA costs 60× more than single cheap.** The overhead is dominated by the aggregation
   call on coding tasks (coding answers are long; gpt-4o is mid-tier; costs add up fast).
4. **The 2-layer variant adds no accuracy** and adds 60% more cost vs 1-layer MoA on hard math.

**Where MoA _can_ make sense (not demonstrated here, but grounded in the paper):** When the
aggregator is itself cheap and the proposers' answers are short; when diversity of model
families genuinely provides complementary knowledge; or when serving a very large batch where
per-call latency caps apply and parallelism is free.

**Why MoA is expensive on this harness:** Coding tasks have long outputs (700-token budget).
Three proposals × 700 tokens × mid-price + one long aggregation = substantial cost per item.

## Key finding

> Combining 3 cheap models via MoA raises accuracy from 0.844 to 0.956 (+11.2pp) but costs
> 60× more than a single cheap call and 4.64× more than a single strong model call that
> achieves 0.978 accuracy. On this suite, single strong dominates MoA on both cost and quality.
> The accuracy gap is real and concentrated entirely in hard reasoning math; MoA reaches 0.867
> on math vs cheap's 0.533, but still falls short of strong's 0.933.

## Surprising findings (see `surprises.md`)

- MoA costs **more** than always-strong, not less — a common misconception.
- The aggregation token cost on coding tasks completely swamps the benefit.
- 2-layer MoA does not help: the hard math failures (m8, m13) are failures of reasoning
  capacity, not lack of synthesis; re-aggregating wrong proposals twice doesn't fix them.
- QA and coding are already saturated at the cheap tier — MoA adds cost without adding accuracy
  on those disciplines.

## Run it

```bash
# From the repo root:
set -a; . .agent-university/secrets.local.env; set +a

# RED (no credentials + no cache — cache must be absent so tests can't serve hits):
cd model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source
mv .cache.json .cache.json.bak
OPENAI_API_KEY="" ANTHROPIC_API_KEY="" python3 test_x1.py  # → 3 ERRORs, ProviderError
mv .cache.json.bak .cache.json

# GREEN (with credentials):
python3 test_x1.py  # → 3 tests pass (hits cache)

# Full suite run (takes ~5 min, costs ~$0.10 first time; ~$0 on warm cache):
python3 run_x1.py
```

RED: `providers.ProviderError: Missing env var OPENAI_API_KEY` on all 3 tests.
GREEN: 3 live behavioral tests pass in ~3 seconds (hits cache after first run).
