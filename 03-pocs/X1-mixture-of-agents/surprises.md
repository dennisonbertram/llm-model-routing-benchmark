# Surprises — X1 Mixture-of-Agents

## 1. MoA costs MORE than always-strong (4.64×), not less

The popular narrative is "cheap models together beat a strong model at lower cost." On this suite,
MoA (3 cheap → gpt-4o aggregator) costs **$0.09966** versus gpt-4.1's **$0.02148**. That is
4.64× MORE expensive while achieving lower accuracy (0.956 vs 0.978).

**Why:** The aggregator (gpt-4o) is a mid-tier model, not a nano/mini. Coding tasks have 700-token
budgets. Three proposals at 700 tokens each + one 700-token aggregation = ~2800 tokens per coding
item at gpt-4o mid prices. Multiplied across 18 coding items, this dominates the total cost.

## 2. QA and coding add cost with zero accuracy gain

Both cheap baseline and MoA score 1.000 on QA (n=12) and coding (n=18). MoA pays for 3 proposals
+ 1 aggregation on 30 items that were already saturated. This is pure waste.

**Implication:** MoA makes most sense when applied selectively to items where cheap models
individually fail. A routing-before-ensemble strategy (classify hard math items first, apply MoA
only there) could recover the accuracy gain at a fraction of the cost.

## 3. 2-layer MoA does not help on hard math

Hard math failures (m8, m13) survived both 1-layer and 2-layer MoA. Adding a second synthesis
pass using gpt-4.1 as the final aggregator did not fix them. The failures are reasoning capacity
failures: the cheap models all produce wrong intermediate steps, so the aggregator (even gpt-4.1)
has only wrong proposals to synthesise from. More synthesis passes do not create correct
reasoning that wasn't in any proposal.

## 4. MoA improved accuracy most on math — the gain comes from the full math slice (n=15)

The **full math slice** (n=15, all difficulties) shows cheap=0.533 → MoA=0.867 (+33.4pp). This is
the headline improvement and matches the per-discipline table in the README.

The **hard math slice specifically** (n=8, items m8–m15) shows cheap=0.125 → MoA-1L=0.750 (+62.5pp).
That is a larger absolute swing, but over a smaller subset; MoA still falls short of strong on
hard math (strong=0.875). The 2-layer variant (MoA-2L) does not improve on 1-layer (both 0.750
on n=8).

Both gains confirm the Wang et al. intuition: diverse proposals cover cases where individual cheap
models fail, as long as at least one proposal is correct. The remaining failures (m8, m13) are
items where ALL 3 cheap models failed — ensemble diversity cannot create correct reasoning
from uniformly wrong proposals.

## 5. Cost per correct answer is worse for MoA than for strong

- strong: $0.000488 per correct answer
- MoA: $0.002318 per correct answer (4.75× worse)
- cheap: $0.000044 per correct answer (best on $/correct, but lowest quality)

MoA sits on the wrong side of the Pareto frontier: it is dominated by always-strong (higher
accuracy, lower cost). It is not a rational choice on this task distribution.
