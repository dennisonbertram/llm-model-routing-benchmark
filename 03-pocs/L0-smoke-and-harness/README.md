# L0 — Live Smoke + Baseline Harness

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

## What this proves

1. **Live access** to three real model providers — OpenAI, Anthropic, xAI — each returns a real
   completion with measured tokens, latency, and cost. No mocks.
2. **The measurement harness works**: it runs a 45-task suite (15 math, 12 QA, 18 coding) through
   any model, grades each task deterministically (numeric match / normalized QA / unit-test
   execution), and reports accuracy, USD cost (uniform `tokens × price`), and latency.
3. **The routing prize is real, not assumed.** The cost-quality gap and the oracle headroom that
   justify this entire degree are measured live:

| Router | accuracy | cost (45 tasks) | vs cheap |
|---|---|---|---|
| always-cheap (`gpt-4o-mini`) | 0.844 | $0.00166 | 1× |
| always-strong (`gpt-4.1`) | 0.978 | $0.02148 | 12.9× |
| **ORACLE** (cheapest-correct per task) | **0.978** | **$0.00214** | **1.3×** |

**The oracle matches the strong model's accuracy (97.8%) for ~10% of its cost.** Only **6 of 45**
tasks actually need the strong model — and all six are multi-step combinatorics/reasoning *math*
(`m9, m10, m12, m13, m14, m15`). `gpt-4o-mini` is already sufficient for **38/45** tasks. This is
the headroom every router in this degree competes to capture.

## Surprising live findings (see `surprises.md`)

- **Canonical coding problems are saturated even for the cheapest model.** `gpt-4.1-nano` solves
  all 18 coding tasks — including regex matching, min-window-substring, edit-distance — so they do
  **not** discriminate model strength. The real gap is in hard reasoning math. (One spec-precise
  edge-case task, `is_number`, is the only coding task that trips a cheap model.)
- **Cheap-model accuracy is non-monotonic/noisy**: `gpt-4o-mini` sometimes fails a task
  `gpt-4.1-nano` solves. A router cannot assume "cheaper ⇒ strictly worse per item."
- **Reasoning models silently return empty text** under a small token budget (the budget is spent
  on hidden reasoning). The harness floors their budget (`REASONING_FLOOR=2048`).
- **`grok-4.3` hides reasoning tokens from `completion_tokens`** but bills them; uniform
  `tokens × price` undercounts unless you bill `total − prompt`, and even then diverges ~1.5× from
  xAI's native `cost_in_usd_ticks / 1e10`. Trust the provider's native cost field for grok.

## The harness (frozen; all later POCs import it)

`harness/` (Python 3.9, stdlib + numpy only — no pip installs):
`providers.py` (unified `chat`/`embed`), `pricing.py` (reconciled price table),
`tasks.py` (the 45-task suite + deterministic graders), `cache.py` (on-disk response cache so the
benchmark pays for each unique `(model, task)` once), `metrics.py` (accuracy/cost/Pareto),
`router_base.py` (`Router`/`SingleModelRouter`/`run_suite`), `judge.py` (ensemble aggregation),
`config.py` (the live-verified model pool).

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 test_l0.py    # GREEN: 3 live behavioral tests pass
python3 run_l0.py                  # prints the baseline table above; writes l0_summary.json
```

RED (recorded in `red-output.txt`): with the API keys unset, `test_providers_live` fails with
`ProviderError: Missing env var OPENAI_API_KEY` — the live-access blocker.
