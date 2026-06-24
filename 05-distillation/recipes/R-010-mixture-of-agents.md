# R-010: Mixture-of-Agents (MoA) — More Expensive Than One Strong Model, Less Accurate

**Category**: recipe
**Evidence tier**: Live verified (POCs X1, X5)
**Source POCs**: X1-mixture-of-agents, X5-router-benchmark-pareto

## Live verified — the honest result

Live verified on the 45-task benchmark (15 math, 12 QA, 18 coding):

| Router                         | Accuracy | Total cost  | vs cheap | vs strong |
|--------------------------------|----------|-------------|----------|-----------|
| always-cheap (`gpt-4o-mini`)   | 0.844    | $0.00166    | 1×       | 0.077×    |
| **MoA** (3 cheap + gpt-4o agg) | **0.956** | **$0.10159** | **61×** | **4.73× more** |
| always-strong (`gpt-4.1`)      | 0.978    | $0.02148    | 13×      | 1×        |

**MoA did NOT beat a single strong model on this suite.** At $0.10159, MoA costs
4.73× more expensive than always-strong AND scores 2.2pp less accurately (0.956 vs 0.978).
(For reference MoA is ~47× the *oracle* cost — $0.10159 / $0.00214 — but against the realistic
always-strong baseline the multiple is 4.7×; use the 4.7× figure when comparing to what you'd
otherwise deploy.)
A single `gpt-4.1` call is both cheaper and more accurate. (X5)

From X1 (full MoA run details):

| Strategy          | Accuracy | Cost         |
|-------------------|----------|--------------|
| always-cheap      | 0.844    | $0.00166     |
| MoA 1-layer       | 0.956    | $0.09966     |
| MoA 2-layer (hard math only, n=8) | 0.750 | $0.00546 |
| always-strong     | 0.978    | $0.02148     |

Self-consistency @5 (gpt-4o-mini, temp=0.7) on math: **9/15** vs 8/15 single cheap
vs 14/15 single strong. Sampling the cheap model more times did not manufacture the
reasoning it lacks. (X5)

## Why MoA is expensive on this harness

MoA makes N+1 calls per query (N proposers + 1 aggregator). Coding tasks have long outputs
(700-token budget). Three proposals × 700 tokens × mid-price + one long aggregation =
substantial cost per task. The overhead is dominated by the aggregation call on coding
tasks. (X1)

## When MoA can make sense (not demonstrated here)

The X1 POC identifies three conditions where MoA can pay off, grounded in the paper's
reported wins:

1. The aggregator is itself cheap and proposers' answers are short
2. Model families provide genuinely complementary knowledge (diverse errors, not correlated)
3. Serving a very large batch where per-call latency caps apply and parallelism is free

None of these held on this benchmark. The MoA loss here is a **workload-specific finding**,
not a universal refutation of the paper.

## The recipe (for completeness — implement with eyes open)

```python
from providers import chat

def mixture_of_agents(
    prompt: str,
    proposers: list[str],   # e.g. ["gpt-4o-mini", "gpt-4.1-mini", "claude-haiku-4-5-20251001"]
    aggregator: str,        # e.g. "gpt-4o"
    cache=None,
) -> dict:
    """
    Wang et al. MoA: each proposer answers independently; aggregator synthesizes.
    WARNING: costs N+1 calls per query. See live cost data above before deploying.
    """
    call = cache.chat if cache else chat
    total_usd = 0.0

    # Step 1: all proposers answer in parallel (sequential here for simplicity)
    proposals = []
    for model in proposers:
        r = call(model, [{"role": "user", "content": prompt}],
                 max_tokens=700, temperature=0.0)
        proposals.append(r.text)
        total_usd += r.usd

    # Step 2: aggregator synthesizes
    proposal_block = "\n\n".join(
        f"Proposal {i+1} ({proposers[i]}):\n{p}"
        for i, p in enumerate(proposals)
    )
    agg_prompt = (
        f"You are given several independent answers to a question. "
        f"Synthesize the best final answer.\n\n"
        f"Question: {prompt}\n\n{proposal_block}\n\n"
        f"Final answer:"
    )
    agg_result = call(aggregator, [{"role": "user", "content": agg_prompt}],
                      max_tokens=700, temperature=0.0)
    total_usd += agg_result.usd

    return {
        "answer":    agg_result.text,
        "proposals": proposals,
        "usd":       total_usd,
    }
```

## Per-discipline breakdown (X1 live)

| Discipline | MoA acc | Cheap acc | Strong acc | n  |
|------------|---------|-----------|------------|----|
| math       | 0.867   | 0.533     | 0.933      | 15 |
| qa         | 1.000   | 1.000     | 1.000      | 12 |
| coding     | 1.000   | 1.000     | 1.000      | 18 |

MoA improves materially over cheap on math (+33.4pp) but QA and coding are already
saturated at the cheap tier — MoA adds cost with no accuracy gain on those disciplines.

## Decision: use MoA or not?

```
Is your cheap model already correct on ≥80% of your workload?
├── YES: the remaining errors are a hard tail. MoA will NOT fix them
│         (the hard items need a stronger model, not more cheap models).
│         Use predictive routing (R-001) instead.
└── NO:  Do cheap models in your pool have complementary, uncorrelated errors?
         ├── YES: MoA may help. Benchmark first.
         └── NO:  MoA will not help. A single strong call is cheaper and better.
```

## Evidence

- X1-mixture-of-agents/README.md — full results, 2-layer MoA, per-discipline breakdown, honest verdict
- X5-router-benchmark-pareto/README.md — benchmark table (MoA row), self-consistency math results
- results-digest.md lines 22–23, 57 — authoritative MoA and self-consistency numbers
