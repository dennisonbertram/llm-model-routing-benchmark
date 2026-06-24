# X6 — Frontier Tier: does GPT-5.5 change the routing story?

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

The base degree capped out at `gpt-4.1` as the "strong" model (0.978 accuracy; one item — `m8` —
beat *both* cheap and strong). This POC runs **GPT-5.5** and **GPT-5.4** over the same 45-task
suite, live, to test what a more powerful frontier reasoning model does to the cost-quality
frontier. Answer: **it raises the achievable ceiling to 100% — and routing lets you capture that
ceiling for ~1/30th the cost of always calling it.**

## Frontier models over the 45-task suite (live)

| model | accuracy | hard-math (7) | coding | cost (45) | vs gpt-4.1 | mean latency |
|---|---|---|---|---|---|---|
| gpt-4o-mini (cheap) | 0.844 | 0/7 | 1.000 | $0.00166 | 0.1× | — |
| gpt-4.1 (prev strong) | 0.978 | 6/7 | 1.000 | $0.02148 | 1.0× | — |
| gpt-5.4 | 0.978 | 6/7 | 1.000 | $0.03958 | 1.8× | 1367ms |
| **gpt-5.5** | **1.000** | **7/7** | 1.000 | $0.11943 | 5.6× | 2753ms |

- **GPT-5.5 is the first model to clear the whole suite (100%)** — it solves the entire hard-math
  tail, including `m8` (gold 14), which neither the cheap model nor `gpt-4.1` could solve.
- It costs **5.6× more than `gpt-4.1`** and runs at ~2.8 s/call — it is a reasoning model billed at
  $5/$30 per 1M tokens *and* it spends hidden reasoning tokens (billed as output).
- **Newer ≠ better per item:** `gpt-5.4` matched `gpt-4.1`'s 0.978 at **1.8× the cost** — it *fixed*
  `m8` but *broke* `m10` (a hard-math item `gpt-4.1` had solved). On this workload `gpt-5.4` is
  strictly dominated by `gpt-4.1`. Measure each model; do not assume the higher version number wins.

## The payoff — a realizable 3-tier router (cheap → gpt-4.1 → gpt-5.5)

A single CV logistic classifier predicts `P(cheap is correct)`; two thresholds turn it into a
3-tier decision (`P≥0.8`→cheap, `P≤0.5`→gpt-5.5, else→gpt-4.1). Scored on the live outcome matrices:

| router | accuracy | cost (45) | notes |
|---|---|---|---|
| always gpt-5.5 | 1.000 | $0.11943 | frontier-everything (overkill) |
| **realizable 3-tier router** | **1.000** | **$0.00405** | routes 32→cheap, 12→gpt-4.1, **1→gpt-5.5** |
| 3-tier oracle (unrealizable) | 1.000 | $0.00372 | ceiling |

> **Live verified: a deployable 3-tier router reaches 100% accuracy at $0.00405 — 30× cheaper than
> always calling GPT-5.5, and within 1.09× of the oracle.** It sends only the single genuinely-hard
> item (`m8`) to the frontier model, the mid-hard items to `gpt-4.1`, and everything else to the
> cheap model.

## The lesson

Trying a more powerful model is exactly right — **when you route to it.** A frontier reasoning model
earns its 5.6× premium only on the hard tail; paying it on all 45 tasks wastes ~96% of the spend.
The routing discipline turns "GPT-5.5 is too expensive to use everywhere" into "GPT-5.5 for the 2%
of requests that need it" — perfect accuracy at cheap-model-adjacent cost. This is the degree's
thesis, extended one tier up.

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 run_x6.py        # frontier models over the suite -> x6_summary.json
python3 x6_3tier.py      # realizable 3-tier router -> x6_3tier_summary.json
```
First run makes the live GPT-5.5/5.4 calls (cached after; re-runs free). gpt-5.5/5.4 prices
($5/$30, $2.50/$15) sourced from openai.com/api/pricing + aipricing.guru (checked 2026-06-22).
