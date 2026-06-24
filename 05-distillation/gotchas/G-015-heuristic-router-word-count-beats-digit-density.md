# G-015: Heuristic routers: word count beats digit density as a complexity signal for math routing

**Category**: gotcha
**Severity**: low
**Evidence tier**: Live verified
**Source POC**: L1-heuristic-router

## What

Live verified. In the L1 heuristic router, digit density (fraction of characters that are digits) was expected to be the strongest signal for hard math problems. It is not. Easy arithmetic problems (m1: 17+25, m2: 144/12, m3: 25% off $20) contain 4–5 digits in 9–20 characters, giving 20–50% digit density. Hard combinatorics problems (m15: "BALLOON permutations" has 0 digits; m10: "A number is doubled, then 6 is added" has only 3 digits in 25 words, 2% density) have near-zero digit density.

The actual discriminating signal was: **word count** (oracle targets m9–m15 average 22 words; easy items average 10–14 words), plus **domain keywords** ("how many", "permutations", "distinct ways", "divisible", "consecutive").

The final feature weighting that achieved 0.956 accuracy: word count 40%, keywords 30%, sentence structure 20%, digit density 10%.

## Why it matters

A routing heuristic built around digit density will route arithmetic questions to strong (many digits, easy) and miss hard combinatorics (no digits, hard). This is the opposite of the correct routing decision. An agent that builds a domain heuristic without first profiling the actual signal in the target task distribution will have inverted routing for a significant fraction of tasks.

## Root cause

Math difficulty in 2026 is not primarily about numbers — it is about the complexity of the reasoning chain (counting distinct combinations, tracking divisibility constraints, applying combinatorics rules). Hard problems describe structured scenarios in natural language with few explicit numbers. Easy problems state simple operations directly with explicit numeric operands.

The heuristic also hit a ceiling: feature engineering with word count + keywords plateaued at 0.956 accuracy. Going from 0.956 to 0.978 required embedding-based routers (L2, L2b) because the boundary between hard and medium math is not capturable by surface-level text features.

## Fix

When building a routing heuristic for math/reasoning tasks:
1. Profile the actual oracle items (which tasks require strong?) before choosing features.
2. Prioritize word count and multi-step keywords over digit density.
3. Use domain-specific keywords: "how many", "distinct", "combinations", "permutations", "consecutive", "divisible", "remainder", "probability", "ways to arrange".
4. Do not rely on digit density as a primary feature.
5. Set a ceiling expectation: heuristic features produce ~96% accuracy; close the remaining 4% with embedding routers.

## Regression note

When tuning a heuristic router, verify routing decisions on the known oracle targets (m9, m10, m12, m13, m14, m15 from this suite) before evaluating on the full suite. A heuristic that misses any of these 6 has already left accuracy on the table.

## Evidence

- Source: `03-pocs/L1-heuristic-router/surprises.md`, item 1: "Digit density is noisy. Easy arithmetic (m1, m2, m3) has 4–5 digits in 9–20 characters, giving 20–50% density. Hard combinatorics (m15: 'BALLOON', 0% density; m10: algebra with 3 digits in 25 words, 2% density) have low density. The actual signal: Word count. Oracle targets (m9–m15) average 22 words; easy items average 10–14. Longer prompts tend to describe multi-step, complex reasoning. We now weight word count at 40% and digit density at only 10%." (Live verified)
- Source: `03-pocs/L1-heuristic-router/surprises.md`, item 2: "Keywords are consistent. Hard math items reliably contain 'how many', 'permutations', 'consecutive', 'divisible', 'distinct ways', etc." (Live verified)
- Source: results-digest.md, L1: "heuristic (prompt cues): 0.933, $0.00520" — showing 4.5pp below logistic at 2.2× the logistic cost. (Live verified)
