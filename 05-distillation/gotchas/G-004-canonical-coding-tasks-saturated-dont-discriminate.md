# G-004: Canonical LeetCode/algorithm coding tasks are memorized — they do not discriminate model strength

**Category**: gotcha
**Severity**: high
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness, L1-heuristic-router, L3b-harness-routing-coding-agent, X5-router-benchmark-pareto

## What

Live verified. `gpt-4.1-nano` (the cheapest available model) solved all 18 coding tasks in the suite, including the supposedly "hard" ones: regex matching (`is_match`), min-window-substring, edit distance, coin change, word break, sliding window, LIS, rainwater trap, decode ways. The escalation loop in L3b never fired — `gpt-4o-mini` also achieved 100% accuracy on coding at temperature=0.

A routing benchmark built entirely on LeetCode-style algorithmic problems will observe "always route cheap" and conclude that routing adds no value. The real discrimination between cheap and strong models in 2026 is elsewhere.

## Why it matters

A router trained or evaluated on a coding-heavy benchmark where cheap already saturates will produce a degenerate routable gap (near zero). It will misrepresent the real cost-quality Pareto frontier. Agents that route coding tasks to a strong model are wasting money — the routing opportunity is in hard multi-step math and reasoning, not in canonical algorithm problems.

## Root cause

Frontier models at every price tier have been trained on public competitive-programming datasets. LeetCode problems, HumanEval tasks, and standard algorithm exercises (edit distance, knapsack, regex NFA, etc.) are effectively memorized. The model produces the correct implementation by pattern matching, not by reasoning from scratch.

The actual routable gap in this suite: **6 of 45 items** required the strong model (`gpt-4.1`), and all 6 were multi-step combinatorics/discrete math (handshakes with exception, BALLOON permutations, counting integers divisible by k in a range, etc.) — not coding.

## Fix

When constructing routing benchmarks, include:
- Multi-step reasoning math (combinatorics, divisibility, permutations with constraints)
- Domain-specific reasoning tasks outside the training distribution
- Specification-precise edge-case coding (e.g., `is_number` — IEEE-754 edge cases with signs, exponents, and whitespace)

Do NOT use canonical competitive-programming problems as difficulty discriminators. Verify the benchmark produces a non-trivial routable gap before using it to train or evaluate any router. From the L0 oracle: only **6/45 items** needed a strong model; all 6 were hard math, 0 were coding.

## Regression note

Before publishing any routing benchmark, run `always-cheap` as a baseline and verify its accuracy is measurably below `always-strong`. If the gap is < 5 accuracy points, the benchmark is likely saturated by cheap models and cannot train a useful router.

## Evidence

- Source: `03-pocs/L0-smoke-and-harness/surprises.md`, item 1: "`gpt-4.1-nano` (the cheapest model) solved all 18 coding tasks, including the supposedly 'hard' ones (regex matching `is_match`, min-window-substring, edit distance, coin change, word break)." (Live verified)
- Source: `03-pocs/L3b-harness-routing-coding-agent/surprises.md`, S1: "gpt-4o-mini achieves 100% accuracy on all 18 coding tasks — including every 'hard' problem (c8-c18: sliding window, LIS, coin change, regex, min-window-substring, edit-distance, rainwater trap, decode ways, is_number). The escalation loop never fired." (Live verified)
- Source: results-digest.md, Gotchas item 4: "Canonical LeetCode/algorithm coding tasks are MEMORIZED and saturate even gpt-4.1-nano → they don't discriminate model strength; the routable gap was multi-step combinatorics MATH." (Live verified)
- Source: results-digest.md, L0 baseline: "Only 6/45 need strong (m9,m10,m12,m13,m14,m15 — all hard math). m8: both wrong. Cheap suffices 38/45." (Live verified)
