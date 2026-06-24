# Surprises — L3a FrugalGPT Cascade

## Surprise 1: Threshold sweep is completely flat

All five thresholds (0.1, 0.3, 0.5, 0.7, 0.9) produce identical accuracy (0.844) and
identical cost ($0.00391). The reason: gpt-4o-mini returns 0.9 for all six hard-math items
it gets wrong. Because 0.9 >= any threshold ≤ 0.9, none of them trigger escalation at any
threshold. The sweep was designed to trace a Pareto curve but instead demonstrates that the
confidence gate has zero discriminative power on this suite.

## Surprise 2: Overconfidence on wrong answers, underconfidence on correct ones

The model returns 0.9 for all wrong hard-math answers, but returns 0.0 for two easy, correct
math answers (m1: 17+25=42; m3: 25% off $20 = $15). The calibration is inverted: the gate
is most conservative on items that need no escalation and most permissive on items that do.
This is consistent with known LLM overconfidence findings — confidence self-reports do not
correlate reliably with correctness for frontier open-source and instruction-tuned models.

## Surprise 3: Coding verifier works well with no redesign

The YES/NO coding verifier on the same cheap model (gpt-4o-mini) produces 0 false accepts
across 18 coding items and only 1 false escalation (c13 — complex regex). This is because
code has structural properties a verifier can reason about, whereas "is this math answer
correct?" requires re-solving the problem. The asymmetry between disciplines is stark.

## Surprise 4: Gate calls add non-trivial overhead

The cascade costs $0.00391 vs $0.00166 for always-cheap — a 2.4× cost overhead even though
only 4/45 items are escalated. The gate calls themselves (52 confidence/verifier calls) cost
roughly the same as the primary cheap answers. FrugalGPT savings require the gate to be cheap
relative to the primary inference cost; for short-answer tasks that is not guaranteed.

## Surprise 5: Cache key collision risk was expected but didn't occur

Initially concerned that harness labelset.json and our cascade cache might collide. In
practice they are separate Cache instances at separate paths, so no risk.
