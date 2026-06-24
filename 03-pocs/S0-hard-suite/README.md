# S0 — HARD suite construction (the gating prerequisite)

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence — a NEGATIVE result.

To test whether orchestration beats a single frontier model, we first needed a deterministic suite
where gpt-5.5 does NOT saturate (headroom). We authored 21 genuinely hard, deterministically-gradable
candidates (math golds computed by brute force; coding fraction-graded with adversarial hidden asserts;
trap QA) and ran gpt-5.5 solo (temp 0).

## Result: gpt-5.5 solved 21/21 (100%)

| family | gpt-5.5 solo |
|---|---|
| math (subset-sum mod 4, Burnside necklaces, modular inverse, partitions, base-12 trailing zeros, ...) | 11/11 |
| coding (strict-Roman validation, exact-fraction add, proleptic date diff, base conversion — fraction-graded) | 4/4 (frac 1.0) |
| trap QA (sheep "all but 9", overtake-2nd, 30÷½, Feb-1900, ...) | 6/6 |

**The frontier model saturates everything we can author + deterministically grade.** This is itself a
finding: orchestration has *zero headroom* on authored tasks, which is exactly why Sakana benchmarks
Fugu at the genuine frontier (GPQA-Diamond, ARC-AGI-2, SWE-bench Pro) for sub-1-point margins. It also
forced the faithful pivot: test orchestration over a DIVERSE, individually-NON-saturating pool (S1/S2)
— Sakana's actual ARC-AGI-2 condition — with gpt-5.5 as the reference ceiling.

Run: `set -a; . .agent-university/secrets.local.env; set +a; cd source && python3 build_hard_suite.py`
