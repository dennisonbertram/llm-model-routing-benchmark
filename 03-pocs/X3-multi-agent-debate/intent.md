# Intent — X3 Multi-Agent Debate

## What we're measuring

Whether running 2–3 cheap models in a multi-round debate (Du et al., 2023) can match a single
strong model's accuracy, and at what cost premium.

## Why it matters for routing

Debate is the highest-overhead ensemble strategy. Understanding its cost-accuracy profile relative
to single-model baselines helps an agent architect decide:
- When (if ever) is it worth running multi-agent debate vs. just using a strong model?
- Can cheap models collectively achieve strong-model accuracy on hard reasoning problems?
- What cost multiplier should an agent budget for debate-style verification?

## Hypothesis

Debate closes the cheap→strong accuracy gap on hard math (where cheap models fail independently)
through cross-model correction pressure. The cost penalty is 6× per item (3 debaters × 2 rounds).
Whether the accuracy gain is worth the cost depends on the value of a correct answer.

## Design choices

- 3 debaters from `config.ENSEMBLE_CHEAP` (different families: OpenAI GPT × 2 + Anthropic Claude)
  so their errors are less correlated — maximizing the chance debate helps.
- 1 debate round (Du et al. find diminishing returns beyond 1–2 rounds).
- Majority vote for numeric items; judge.pick_best for open-ended — avoids expensive judges on
  items where numeric consensus suffices.
- Test suite: math (15 items, including 6 hard) + QA (8 items). Skips coding because the
  labelset shows all cheap models already solve all 18 coding tasks — no discriminating signal.
- Own `.cache.json` — never touches the shared `harness/.cache/labelset.json`.
