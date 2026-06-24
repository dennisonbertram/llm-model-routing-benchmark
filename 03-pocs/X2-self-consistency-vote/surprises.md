# Surprises

## 1. Zero stochasticity at high temperature

Expected: temperature 0.7 would generate diverse reasoning paths and answers.
Actual: gpt-4o-mini produces near-identical wrong answers across 5 samples.

**Why this matters:** Self-consistency assumes the weak model can solve the problem but makes occasional errors due to randomness. When errors are *systematic* (the model follows a deterministic reasoning path that is wrong), voting cannot save it.

Implication: Self-consistency works best on:
- Tasks the weak model CAN solve (but is noisy on)
- NOT on tasks beyond the model's reasoning depth (reasoning limitations)

## 2. No improvement plateau at k=3

Expected: accuracy could improve gradually from k=1 to k=3 to k=5.
Actual: k=1 (hard acc=0%), k=3 (hard acc=14.3%), k=5 (hard acc=14.3%).

The model's accuracy plateaus; voting cannot extract signal that isn't there. Even the few samples that "win" the vote on hard items (like m9's 67 vs 66) are both wrong.

## 3. Voting cost exceeds cheap baseline soon

k=1: $0.00009 (same as single cheap call)
k=3: $0.00027 (2.8× cheap)
k=5: $0.00045 (4.7× cheap)

For hard math, this cost could have **paid for a single gpt-4.1 call** (at $0.00114 per 15 tasks, so ~$0.000076 per hard item). Voting is economically dominated for this task distribution.

## 4. Hard items remain unsolved

Cheap model solves 0/7 hard items.
Voting at k=5 still solves 1/7 (14.3%, and that's actually due to one item being ambiguously graded).

The ceiling is hit hard: the model lacks the reasoning capability, not the sampling diversity.

## 5. Majority-vote tiebreaker matters but doesn't help

When we have 5 samples and 4 agree on a wrong answer, the tiebreaker is clear — but we're still wrong. This is a **quorum voting** failure: the plurality is wrong.

In papers where self-consistency works (GSM8K), this is less common because the cheap model has a reasonable chance of generating a correct solution path on some samples.
