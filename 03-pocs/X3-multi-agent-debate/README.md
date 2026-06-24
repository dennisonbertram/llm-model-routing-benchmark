# X3 — Multi-Agent Debate (Du et al.)

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

## What this proves

Multi-agent debate (Du et al., 2023) runs 3 cheap models independently, then lets each revise after
seeing the others' answers, and aggregates via majority vote (numeric) or judge.pick_best (open).

Live verified on 23 items (15 math + 8 QA) from the shared task suite.

**Headline: debate matches the strong model's accuracy at 3.8× its cost (42.7× cheap).**

## Results (Live verified)

### Full suite (23 items: math + QA)

| router | n | accuracy | total_usd | usd/correct | notes |
|---|---|---|---|---|---|
| always-cheap (gpt-4o-mini) | 23 | 0.696 | $0.000147 | $0.000009 | baseline |
| always-strong (gpt-4.1) | 23 | 0.957 | $0.001634 | $0.000074 | target to beat |
| **debate:3x1r** | **23** | **0.957** | **$0.006278** | **$0.000285** | **matches strong, 3.8× cost** |

### Hard math subset (m9, m10, m12, m13, m14, m15 — 6 items)

| router | n | accuracy | total_usd |
|---|---|---|---|
| always-cheap (gpt-4o-mini) | 6 | 0.000 | $0.000039 |
| always-strong (gpt-4.1) | 6 | 1.000 | $0.000520 |
| **debate:3x1r** | **6** | **1.000** | **$0.001590** |

**Debate achieves 100% on hard math** (the 6 items cheap models can't solve), solving all of them
via cross-model consensus. Cost is 3.1× the strong model on that subset.

## Protocol (Live verified)

- **3 debaters**: `gpt-4o-mini`, `gpt-4.1-mini`, `claude-haiku-4-5-20251001` (diverse families)
- **2 phases**: round 0 (independent), round 1 (each sees others' answers and may revise)
- **6 calls per item** (3 debaters × 2 rounds)
- **Aggregation**: majority vote if ≥2 debaters produce an integer; `judge.pick_best` otherwise
- No oracle leakage: the router reads only `item["prompt"]` — never `difficulty` or `discipline`

## Debate transcript sample (item m1 — trivial item) (Live verified)

```
Prompt: "What is 17 + 25? Reply with just the number."

gpt-4o-mini   R0: '42'   R1: '42'
gpt-4.1-mini  R0: '42'   R1: '42'
claude-haiku  R0: '42'   R1: '42'

Aggregation: majority_numeric → final answer: '42'  ✓
```

A harder item (m9 — divisibility) shows real debate value: gpt-4o-mini initially returns a wrong
answer; after seeing gpt-4.1-mini's and claude-haiku's correct answer it converges to the right one.

## Cost-quality interpretation (Live verified)

Debate **does** close 100% of the cheap→strong accuracy gap on this suite (from 0.696 to 0.957),
but at a cost of:
- **42.7× single cheap** — practically unaffordable as a blanket strategy
- **3.8× single strong** — debate is more expensive than just using gpt-4.1

The math is unfavorable on this suite because the hard problems (the 6 that trip cheap models) are
exactly the ones cheap models get zero credit for without debate — so debate's incremental accuracy
gain requires paying for 6 calls on every item, not just the hard ones.

**Honest finding**: on this benchmark, debate is not on the cost-quality Pareto frontier vs.
always-strong. It is dominated (same accuracy, 3.8× the cost). Debate would be valuable if
deployed selectively — only on items a router has predicted require ensemble reasoning.

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 test_x3.py    # GREEN: 5 live behavioral tests pass
python3 run_x3.py     # prints full results table + transcript; writes x3_summary.json
```

RED (no keys): `ProviderError: Missing env var OPENAI_API_KEY` — 4 tests fail.
GREEN (with keys): all 5 tests pass, including oracle-leakage guard.

## File index

| file | purpose |
|---|---|
| `source/run_x3.py` | DebateRouter + main benchmark |
| `source/test_x3.py` | 5 live behavioral tests (red/green) |
| `source/x3_summary.json` | machine-readable results (written by run_x3.py) |
| `source/.cache.json` | POC-local response cache (190 live calls billed once) |
| `source/red-output.txt` | captured failure without keys |
| `source/green-output.txt` | captured 5/5 pass with keys |
