# Surprises — L3b Harness Routing

## S1: gpt-4o-mini solves ALL 18 coding tasks at temperature=0

The biggest finding: `gpt-4o-mini` achieves 100% accuracy on all 18 coding tasks — including
every "hard" problem (c8-c18: sliding window, LIS, coin change, regex, min-window-substring,
edit-distance, rainwater trap, decode ways, is_number). The escalation loop never fired.

This contradicts the naive assumption that "hard" coding tasks need a strong model. At
temperature=0 with sufficient token budget (700 tokens), gpt-4o-mini reliably writes correct
Python for canonical LeetCode-style problems.

## S2: The routing opportunity in coding is NOT difficulty-based

L0 confirmed that the real model gap is in hard math (combinatorics, discrete math), not hard
coding. The "hard" difficulty label on coding tasks does not predict model failure the same way
it does for math tasks. Routing based on difficulty labels would be misleading for coding.

## S3: The repair prompt test verifies the escalation mechanism works

Even though no task triggered escalation in the main run, the `test_repair_prompt_elicits_code`
test confirms the strong model successfully repairs a broken implementation when given a repair
prompt with failing code. The mechanism works — the suite just didn't need it.

## S4: 13.25x cost ratio makes avoiding unnecessary strong calls very valuable

Even on a small 18-task suite, all-strong costs $0.0197 vs all-cheap $0.0015. At production
scale (millions of coding tasks per day), unnecessary strong model calls are a major expense.
The escalate-on-failure pattern is correct: don't pay strong model prices unless tests fail.

## S5: Cost per task is non-linear with code complexity

Hard tasks (c13: regex matching, c14: min-window) cost ~4x more than easy tasks even for
gpt-4o-mini ($1.8e-4 vs $2.1e-5). This is driven by longer generated solutions, not token
input. Strong model costs scale similarly, maintaining roughly constant per-task cost ratio.
