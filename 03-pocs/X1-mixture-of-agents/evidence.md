# Evidence — X1 Mixture-of-Agents

**Evidence tier: Live verified** — all numbers from real API calls, 2026-06-21.

## Provider calls made

- **gpt-4o-mini** (OpenAI): 45 proposal calls (1 per task) — live via OPENAI_API_KEY
- **gpt-4.1-mini** (OpenAI): 45 proposal calls (1 per task) — live via OPENAI_API_KEY
- **claude-haiku-4-5-20251001** (Anthropic): 45 proposal calls (1 per task) — live via ANTHROPIC_API_KEY
- **gpt-4o** (OpenAI aggregator): 45 aggregation calls (1 per task, full suite) — live via OPENAI_API_KEY
- **gpt-4.1** (OpenAI 2nd-layer agg): 8 calls (hard math only, 2-layer variant) — live via OPENAI_API_KEY
- **gpt-4o** (OpenAI 1st-layer agg): 8 calls (hard math only, 2-layer variant) — live via OPENAI_API_KEY

Cache stats after run:
- **First paying run** (cold cache): `{'hits': 35, 'misses': 185, 'entries': 190}` — 185 live
  provider calls billed, 35 hits from the 3 behavioral tests that reuse the warmed cache.
- **Subsequent reruns** (warm cache): `{'hits': 220, 'misses': 0, 'entries': 190}` — all 220
  calls served from cache, $0 billed, identical output reproduced exactly.

## Measured numbers

All from `x1_summary.json` (written by `run_x1.py`):

| Metric | Value |
|---|---|
| MoA accuracy (45 tasks) | 0.9556 |
| MoA total cost (45 tasks) | $0.09966 |
| always-cheap acc | 0.8444 |
| always-cheap cost | $0.00166 |
| always-strong acc | 0.9778 |
| always-strong cost | $0.02148 |
| MoA cost vs cheap | 60.0× |
| MoA cost vs strong | 4.64× |
| MoA math acc | 0.867 |
| MoA qa acc | 1.000 |
| MoA coding acc | 1.000 |
| MoA-2L hard math acc (n=8) | 0.750 |

## Behavioral tests (green)

`source/green-output.txt` — 3 tests pass:
1. `test_moa_aggregator_returns_text` — aggregate_moa returns non-empty text from a live gpt-4o call
2. `test_moa_costs_more_than_single_cheap` — MoA ($>1.5× single cheap) confirmed
3. `test_moa_grades_easy_item_correctly` — m1 (17+25=42) graded correct by MoA

## Behavioral tests (red)

`source/red-output.txt` — all 3 tests ERROR with `ProviderError: Missing env var OPENAI_API_KEY`.

Reproduction requires both no credentials AND no cache (the warm cache serves every call even
without keys): rename `.cache.json` away, run with `OPENAI_API_KEY="" ANTHROPIC_API_KEY=""`,
then restore the cache. See `commands.md` for the exact steps.

## Cache isolation

OWN cache: `source/.cache.json` — 190 entries after full run.
Baselines use `harness/.cache/labelset.json` (shared, read-only for this POC).
The POC did NOT write to the harness cache.
