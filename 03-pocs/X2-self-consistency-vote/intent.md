# Intent: Self-Consistency Voting

## Hypothesis

Self-consistency voting (Wang et al, "Self-Consistency Improves Chain of Thought Reasoning in Language Models") claims that sampling a weak model multiple times at high temperature, then taking majority vote on the answer, can match a much stronger model's accuracy — a cheap ensemble beats a single expensive model.

## Test setup

- **Models**: gpt-4o-mini (cheap) vs gpt-4.1 (strong)
- **Suite**: math tasks only (15 items: 8 easy/med, 7 hard)
- **Voting scope**: numeric majority vote on final answer (clean for math)
- **k values tested**: 1, 3, 5 (number of samples per item)
- **Temperature**: 0.7 (high entropy to generate diverse samples)

## Success criteria

- Voting at k=3 or k=5 should improve accuracy over single cheap call
- Cost per item should be <4× single cheap call for meaningful gain
- On hard math (7 items), voting should close ≥50% of the gap to strong model
- OR: If voting fails, document why (systematic vs stochastic errors)

## Expected outcome

Original self-consistency paper showed gains on GSM8K and SVAMP (grade-school math), so we expect:
- k=3: modest accuracy gain, ~3× cost of single cheap
- k=5: further gain, ~5× cost of single cheap
- Hard-math gap closure: 40–70% of gap to strong model

## Actual outcome

**Voting FAILED to improve accuracy.** See README.md for why: model errors are systematic, not stochastic. No improvement in hard math; cost-quality dominated by strong baseline.
