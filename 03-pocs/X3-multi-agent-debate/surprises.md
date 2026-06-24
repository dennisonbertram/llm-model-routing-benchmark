# Surprises — X3 Multi-Agent Debate

## S-1: Debate dominated the strong model on this suite (not a win)

The hypothesis was "debate might close the accuracy gap." It did — 0.957 accuracy matches gpt-4.1
exactly — but at 3.84× gpt-4.1's cost. On the cost-quality Pareto frontier, debate is dominated
by always-strong: same accuracy, 3.84× the cost. Debate only makes sense selectively (on items
predicted to be hard), not as a blanket strategy.

## S-2: Hard math went 0%→100% — but that's the only discriminating signal

The 6 hard math items (m9, m10, m12–m15) are 0% for cheap and 100% for strong. Debate hits 100%
on all 6. This seems impressive, but the suite is biased: if a problem is easy enough for gpt-4o-mini,
all 3 debaters already agree in round 0 and round 1 changes nothing. The "debate effect" is only
visible on the hard items, and gpt-4.1 already solves those alone without debate overhead.

## S-3: Trivial items trigger no real debate

On items like "17+25=?", all 3 debaters answer "42" in round 0 and again in round 1. The debate
round is pure overhead (cost with zero information gain). A router that skips debate on
low-difficulty items would be strictly better — but that requires predicting difficulty without
oracle labels, which is the unsolved routing problem.

## S-4: QA items fall back to judge.pick_best (not majority vote)

Most QA answers are single words (Paris, Oxygen, 7) — some debaters add surrounding text, making
integer extraction fail. This correctly falls back to judge.pick_best (an extra gpt-4.1 call),
adding cost. For structured tasks, forcing debaters to reply with ONLY the answer (as the prompt
requests) would reduce judge overhead.

## S-5: 190 live calls on first run; re-runs are free

The 23-item × 6-calls/item = 138 debate calls + 46 baseline calls = 184 calls (plus a few judge
calls) were billed once and cached. All re-runs use the cache. This makes the benchmark
reproducible at zero additional cost.

## S-6: Cost per correct answer is 3.84× worse for debate vs strong

$0.000285 per correct answer (debate) vs $0.000074 (strong). Even on accuracy-matched comparisons,
debate is substantially less efficient per unit of correct output.
