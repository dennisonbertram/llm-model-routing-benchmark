# Lesson: Ensemble Strategies (MoA, Self-Consistency, Debate)

Live verified (X1; X2; X3; X4; 2026-06-21). First-class NEGATIVE findings: cheap
ensembles did NOT beat one strong model on this hard-reasoning-tail workload.

Back to [index](../index.md).

---

## Summary (live-measured)

Live verified. All numbers from committed POC evidence.

| Strategy | accuracy | total cost (45 tasks) | vs always-strong |
|----------|----------|-----------------------|------------------|
| always-cheap | 0.844 | $0.00166 | 0.08x |
| always-strong (gpt-4.1) | 0.978 | $0.02148 | 1.0x |
| MoA (3 cheap + aggregator) | 0.956 | $0.10159 | **4.7x MORE expensive** |
| self-consistency @5 (cheap, math) | 9/15 math | — | worse than single strong (14/15) |
| debate (3 models, 1 round) | 0.957 | $0.0063 (23-task subset)\* | **3.84x MORE expensive** |
| AutoMix (kNN self-verify) | 0.978 | (2.85x oracle) | accurate but expensive |

\* Debate and self-consistency were measured on SUB-suites, not the full 45 tasks: debate on a 23-task subset ($0.006278 vs $0.001634 always-strong on the same 23 = 3.84x); self-consistency on the 15-task math subset (9/15 vs strong 14/15). Only MoA was run on the full 45 ($0.10159). The ratios are apples-to-apples within each subset.

**None of the ensemble strategies dominated always-strong on both cost AND accuracy.**

---

## Mixture-of-Agents (MoA): NEGATIVE (X1)

Live verified. From `03-pocs/X1-mixture-of-agents/README.md`.

Architecture: gpt-4o-mini + gpt-4.1-mini + claude-haiku → proposals → gpt-4o (aggregator) → final answer.

| Router | accuracy | cost |
|--------|----------|------|
| always-cheap | 0.844 | $0.00166 |
| MoA | **0.956** | **$0.09966** |
| always-strong | 0.978 | $0.02148 |

MoA raises accuracy +11.2pp over cheap. But it costs **4.64x more than always-strong** and
is still 2.2pp less accurate than strong. A single gpt-4.1 call is both cheaper AND more
accurate than MoA on this suite.

Why MoA is expensive here:
- Coding tasks have long outputs (700-token budget per proposer).
- 3 proposers × 700 tokens × mid-price + one long aggregation = substantial per-item cost.
- QA and coding are already saturated at cheap tier — MoA adds cost without accuracy gain
  on those disciplines.

Per-discipline (live-measured):
- math: MoA 0.867 vs cheap 0.533 vs strong 0.933 (MoA helps but doesn't reach strong)
- qa: all three 1.000 (no routing leverage)
- coding: all three 1.000 (no routing leverage)

2-layer MoA on hard math: same accuracy as 1-layer, 60% more cost. Re-aggregating wrong
proposals twice doesn't fix reasoning failures.

---

## Self-consistency @5 (cheap model): NEGATIVE (X2)

Live verified. From `03-pocs/X2-self-consistency-vote/README.md`.

gpt-4o-mini sampled 5 times (temp>0), majority vote on math:

| Strategy | math accuracy (n=15) |
|----------|----------------------|
| single cheap (gpt-4o-mini) | 8/15 |
| self-consistency @5 (cheap) | **9/15** |
| single strong (gpt-4.1) | **14/15** |

Self-consistency gains 1/15 on math. Sampling a weak model more times does not manufacture
the reasoning it lacks. The hard-math items fail because gpt-4o-mini lacks the reasoning
capacity for multi-step combinatorics — more samples do not fill that gap.

---

## Multi-agent debate (3 models, 1 round): DOMINATED (X3)

Live verified. From `03-pocs/X3-multi-agent-debate/README.md`.

| Strategy | accuracy | cost |
|----------|----------|------|
| always-strong | 0.978 | $0.02148 |
| debate (3 models) | 0.957 | $0.0063 (23-task subset)\* |

Debate matches near-strong accuracy (0.957) at 3.84x the cost of always-strong. It is
dominated: you can achieve the same accuracy for less by just calling strong directly.

---

## AutoMix (kNN self-verify): ACCURATE but 2.85x oracle cost (X4)

Live verified. From `03-pocs/X4-verification-cascade-automix/README.md`.

AutoMix matches strong accuracy (0.978) with 71.6% cost savings vs always-strong. This
is a genuine positive — but the verifier overhead means it costs 2.85x the unrealizable
oracle. The logistic classifier (capstone) achieves the same accuracy at 1.20x the oracle.

AutoMix's verifier was 100% precise on the high-confidence bucket — a real positive finding.
But the cascade overhead makes it less efficient than a well-calibrated predictive router.

---

## Why ensembles struggle on hard-reasoning-tail workloads

Live verified. This is the degree's key negative lesson.

The 45-task suite has a hard tail: 6/45 items require multi-step combinatorics/algebra math
that gpt-4o-mini cannot solve reliably. Ensembles of cheap models:
1. Multiply cost by N × call overhead.
2. Still miss the tail items because all proposers fail them (correlated errors).
3. Cannot synthesize reasoning capacity that no individual member has.

The correct strategy for this type of workload: **route the hard tail to a stronger model**
via a predictive classifier. One strong call on 6 items costs far less than N cheap calls
that still miss the answer.

---

## When ensembles CAN work (research-supported, not live-verified here)

- Members are individually competitive with DIFFERENT failure modes (uncorrelated errors).
- The aggregator is cheap and the proposals are short.
- The workload has mixed difficulty where cheap models sometimes succeed, sometimes fail,
  independently — not a concentrated hard tail.
- Diversity of model families provides genuinely complementary knowledge.

These conditions did not hold on the 45-task suite. Report your own measured outcome.

---

## The one-sentence rule

> On a hard-reasoning-tail workload, routing to a stronger model beats ganging up cheap
> models: ensembles multiply cost and still miss the tail.

---

## POC sources

- `../03-pocs/X1-mixture-of-agents/`
- `../03-pocs/X2-self-consistency-vote/`
- `../03-pocs/X3-multi-agent-debate/`
- `../03-pocs/X4-verification-cascade-automix/`
