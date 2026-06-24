# Lab: L0 — Baseline Harness

Live verified (L0; 2026-06-21). Confirm 3-provider live access and measure the routing prize.

Back to [index](../index.md).

---

## Goal

Run the 45-task suite through always-cheap and always-strong. Compute the oracle ceiling.
Record the baseline numbers that all later routers must beat to be useful.

---

## Commands

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L0-smoke-and-harness/source

# Behavioral tests (GREEN with keys, RED without)
python3 test_l0.py

# Full baseline run (makes live API calls; writes l0_summary.json)
python3 run_l0.py
```

---

## Expected output (live-measured, 2026-06-21)

```
always-cheap  gpt-4o-mini  acc=0.844  $0.00166
always-strong gpt-4.1      acc=0.978  $0.02148  (12.9x cheap)
ORACLE ceil                acc=0.978  $0.00214  (only 6/45 need strong)
```

---

## What to internalize

- Only 6/45 tasks need the strong model: m9, m10, m12, m13, m14, m15 (all hard math).
- m8: both models wrong — the oracle charges cheap here.
- Cheap suffices for 38/45 tasks. This is the routing prize.
- oracle is the unrealizable ceiling (it peeks at per-item correctness). Never claim a
  deployed router equals oracle.

---

## RED state

With `OPENAI_API_KEY` unset: `ProviderError: Missing env var OPENAI_API_KEY`.
That is correct behavior — live-access failure is the only acceptable RED.

---

## POC source

`../03-pocs/L0-smoke-and-harness/`
