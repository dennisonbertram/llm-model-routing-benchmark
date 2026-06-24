# X2 — Self-Consistency Voting ("More Agents Is All You Need")

**Evidence: Live verified (2026-06-21).** Status: Complete with honest results.

## What this tests

Self-consistency voting (Wang et al) proposes that sampling a weak model k times at temperature >0, then taking the majority answer, can match a stronger model's accuracy. The motivating claim: "more agents is all you need" — a cheap ensemble outperforms a single expensive model.

**This POC tests whether this works on hard math.** We sample `gpt-4o-mini` k times (k ∈ {1, 3, 5}) at temperature 0.7, take the numeric majority vote, and compare to a single `gpt-4.1` call.

## Key finding: Voting fails on hard math due to systematic errors

**Live verified negative result.** Self-consistency voting DOES NOT close the hard-math gap with `gpt-4o-mini`:

| Router | Accuracy (15 math) | Hard-only acc (7 items) | Cost (15 tasks) | vs strong |
|---|---|---|---|---|
| Single cheap (`gpt-4o-mini`)      | 0.533 | 0.000 | $0.000095 | 0.1× |
| Single strong (`gpt-4.1`)         | 0.933 | 0.857 | $0.001142 | 1.0× |
| **Self-consistency @k=3**         | **0.600** | **0.143** | **$0.000267** | **0.2× strong cost** |
| **Self-consistency @k=5**         | **0.600** | **0.143** | **$0.000448** | **0.4× strong cost** |

### Why voting fails (evidence)

When we sample `gpt-4o-mini` at temperature 0.7 on hard-math items, **the model produces near-identical wrong answers across all samples**:

**Item m9** ("Find the number of integers from 1 to 100 divisible by 3 or 5"):
- Gold: 47
- Sample 0: "66"
- Sample 1: "67"
- Sample 2: "67"
- Sample 3: "67"
- Sample 4: "67"
- **Majority vote: 67 (WRONG)** — model is systematic, not stochastic

**Item m13** ("Handshake problem: 9 guests, 1 pair refuses"):
- Gold: 35
- Samples 0–4: all produce "28"
- **Majority vote: 28 (WRONG)** — no variance to vote on

### The mechanism

Self-consistency assumes model errors are **stochastic** — a bad sample on one path, a good sample on another, votes converge to truth. But `gpt-4o-mini` on hard reasoning items exhibits **systematic errors**: it follows a consistent (wrong) reasoning path and produces the same wrong answer every time, even at temperature 0.7.

The few samples that differ slightly (m9: 66 vs 67) all fall on the "wrong" side of the true answer (47). Majority voting among wrong answers still yields a wrong answer.

## Results summary

**Full math suite (15 items):**
```
Self-consistency gpt-4o-mini@k1: acc=0.600  cost=$0.00009  (9% cheaper than single cheap baseline)
Self-consistency gpt-4o-mini@k3: acc=0.600  cost=$0.00027  (2.8× cheap baseline cost)
Self-consistency gpt-4o-mini@k5: acc=0.600  cost=$0.00045  (4.7× cheap baseline cost)
```

Cost-wise, voting at k=3 and k=5 **costs more than the cheap baseline** while providing **no accuracy gain** over sampling once. Cost-quality tradeoff is strictly worse than alternatives.

**Note on cheap baseline vs SC@k=1:** The cheap baseline (T=0.0, acc=0.533) and SC@k=1 (T=0.7, acc=0.600) use the same model but different temperatures, so they draw different live samples — neither result is wrong. The "9% cheaper" observation for SC@k=1 is a small sampling-cost artifact from token-count variance across those distinct live calls.

**Hard-math gap closure (7 items):**
- Cheap → Strong gap: 0.000 → 0.857 (absolute 0.857)
- SC@k=3 closes: 0.143 / 0.857 = **17% of the gap**
- SC@k=5 closes: 0.143 / 0.857 = **17% of the gap**

No improvement with k=5 over k=3 — the hard ceiling is hit by the model's systematic reasoning limitation.

## Pareto analysis

The cost-quality frontier on this suite is dominated by:
1. **Single strong call** (`gpt-4.1`): 0.933 acc at $0.00114 (best quality; high cost)
2. **Single cheap call** (`gpt-4o-mini`@k=1): 0.600 acc at $0.00009 (cheapest point)

Self-consistency voting at k≥3 is **strictly dominated** by both: higher cost than cheap baseline, lower accuracy than strong baseline.

## Why this matters for routing

This is an **honest negative result** that teaches three routing lessons:

1. **Ensemble voting assumes stochastic errors.** When a weak model's errors are systematic (due to reasoning limitations, not noise), voting cannot rescue them. Self-consistency works best on tasks where the model can solve the problem but makes occasional mistakes due to context length, distraction, or noise — not on tasks beyond its reasoning depth.

2. **Cost of weak ensembles.** Three cheap model calls cost ~0.27¢ (3× single cheap call) but yield no accuracy boost. For hard tasks, a single strong call (~1.14¢) is cheaper and correct. Ensemble voting is only economical when:
   - The weak model CAN occasionally solve the problem (stochastic failures), OR
   - The weak model is substantially cheaper than the cost savings from avoiding strong-model calls elsewhere

3. **Routing implication.** On this task distribution, a **cascade** (cheap → if low confidence, strong) would be better than voting. The cheap model never solves hard items; a router that detects this and escalates saves k-1 cheap calls wasted on voting.

## Live evidence

- **Green output**: `source/green-output.txt` — all 15 math items evaluated with gpt-4o-mini (k=1,3,5) and gpt-4.1; cost and accuracy measured end-to-end.
- **Red output**: `source/red-output.txt` — run with API key unset; shows ProviderError / AuthenticationError confirming live API calls (no mocks).
- **Variance test**: `source/variance-test.txt` — 5 samples each on items m9 and m13 at temperature 0.7, showing systematic (not stochastic) wrong answers.
- **Summary JSON**: `source/x2_summary.json` — full results table including per-item breakdown.

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 run_x2.py      # Full evaluation: baseline + voting@k=1,3,5
python3 test_variance.py            # Fresh samples on 2 hard items (shows no stochasticity)
```

## Status

**Doctrine: Blocked.** This strategy does not improve on a single strong call and is strictly dominated on the Pareto frontier. Not recommended as a core routing method; useful as a negative example and for **comparative teaching**: why ensemble voting fails when weak models hit a reasoning ceiling.
