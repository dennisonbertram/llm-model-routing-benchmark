# Expectation Gap Log

Live verified (2026-06-21/22). Doc-vs-live gaps discovered during POC execution.
Each entry: what docs/papers implied → what actually happened live → root cause → before-you-build implication.

---

## EG-1: Canonical coding tasks saturate cheap models — they do NOT discriminate model strength

Live verified (L0-smoke-and-harness, L3b-harness-routing-coding-agent).

**What was expected**: "Hard" LeetCode-style coding problems (edit-distance, min-window-substring,
regex matching, coin change, decode ways) would require a strong model. The degree spec included
them as discriminators.

**What happened live**: gpt-4.1-nano (cheapest model) solved all 18 coding tasks including every
"hard" one. gpt-4o-mini also solved all 18 at temperature=0. The escalation path in L3b fired
0 times out of 18 tasks.

**Root cause**: Canonical algorithm problems are memorizated from training data. The models have
absorbed the patterns for these specific problem classes. A routing suite built on LeetCode-style
problems will always look like "route everything cheap."

**Before-you-build implication**: Routing benchmarks need tasks that at least ONE model in the pool
actually fails. For coding, that means novel, spec-precise edge-case tasks — not standard interview
problems. The actual gap in this degree was multi-step combinatorics math (m9–m15).

Source: L0-smoke-and-harness (surprises 1–2), L3b-harness-routing-coding-agent (surprise S1).

---

## EG-2: Cheap-model accuracy is non-monotonic — "cheaper = worse" is false per-item

Live verified (L0-smoke-and-harness).

**What was expected**: A monotonic capability ladder — gpt-4.1-nano < gpt-4o-mini < gpt-4.1.
If gpt-4o-mini fails a task, gpt-4.1-nano definitely fails it.

**What happened live**: gpt-4o-mini failed m14 (coin change count) that gpt-4.1-nano answered
correctly. The per-item accuracy ordering is not strictly monotonic.

**Root cause**: Different models have different training-data exposure and fine-tuning objectives.
Capability does not strictly stack by price across all tasks.

**Before-you-build implication**: Do not assume a monotonic capability ordering. A router that
uses price as a proxy for capability will mis-route items where a cheaper model is locally better.
Label the routing set by measuring both models on every item.

Source: L0-smoke-and-harness (surprise 3), results-digest gotcha 5.

---

## EG-3: FrugalGPT self-confidence gate fails on overconfident cheap models

Live verified (L3a-frugalgpt-cascade).

**What was expected** (from FrugalGPT paper, Chen/Zaharia/Zou 2023): A cheap model's self-reported
confidence can act as a cascade gate — low confidence triggers escalation to a stronger model.
The gate would discriminate between items the cheap model answers correctly vs. incorrectly.

**What happened live**: gpt-4o-mini reports confidence=0.9 for ALL 6 hard-math items it answers
incorrectly (m9, m10, m12, m13, m14, m15). It also reports confidence=0.0 for 2 easy items it
answers correctly (m1: 17+25=42; m3: 25% off $20). A threshold sweep from 0.1 to 0.9 produced
identical accuracy (0.844 = always-cheap) and identical cost ($0.00391) at every threshold.

**Root cause**: Instruction-tuned models are calibrated to be helpful, not calibrated to be honest
about uncertainty. For tasks where the model follows a deterministic wrong reasoning path, it is
confident and wrong simultaneously. Self-reported confidence does not proxy for correctness on
hard-tail reasoning tasks.

**Before-you-build implication**: Do NOT use self-reported LLM confidence as a cascade gate for
tasks with structured correct answers. Use an independent verifier (code execution for coding,
a separate model call for factual QA) or a trained classifier. The FrugalGPT pattern requires
the gate to be calibrated — check calibration on your specific workload before deploying.

Source: L3a-frugalgpt-cascade (surprises 1–2), results-digest gotcha 6.

---

## EG-4: Cheap-model ensembles (MoA/debate/SC) do NOT beat a single strong model on hard-reasoning workloads

Live verified (X1-mixture-of-agents, X2-self-consistency-vote, X3-multi-agent-debate, X5-router-benchmark-pareto).

**What was expected** (from MoA paper, Wang et al / Together; debate paper, Du et al; SC paper, Wang et al):
Aggregating multiple cheap models should improve accuracy, potentially matching or exceeding a
single strong model at lower cost. This is the core "wisdom of the crowd" claim.

**What happened live**:
- MoA (3 cheap + gpt-4o aggregator): acc=0.956, cost=$0.10159 — 4.64× more expensive than
  always-strong AND 2.2 percentage points less accurate.
- Debate (3 models, 1 round): acc=0.957 = always-strong, but 3.84× the cost.
- Self-consistency@5 on hard math: 9/15 vs strong 14/15. Barely moved from 8/15 single-cheap.

**Root cause**: These ensemble methods assume cheap models make uncorrelated errors that cancel
in the vote/aggregate. On hard math where all cheap models follow the same incorrect reasoning
path (e.g., overcounting permutations), errors are perfectly correlated — the ensemble amplifies
the wrong answer. More synthesis passes (2-layer MoA, additional debate rounds) do not create
correct reasoning that wasn't in any proposal.

**Before-you-build implication**: Ensembles improve accuracy only when the individual members
are individually competitive and errors are uncorrelated. Before using MoA/debate/SC:
(1) check that cheap members solve ≥50% of the hard items solo; (2) check that wrong answers
differ across members. If both conditions fail, route to a single strong model instead.

Source: X1 (surprise 1–3), X2 (surprises 1–2), X3 (surprise S1–S2), X5 (surprise 2–3), results-digest gotcha 7.

---

## EG-5: grok-4.x ticks → USD conversion is /1e10, not /1e9

Live verified (L0-smoke-and-harness).

**What was expected**: `cost_in_usd_ticks / 1e9` based on common "nanoUSD" or "milli-cent"
interpretations of a 9-decimal-place cost field.

**What happened live**: The measured ticks for a trivial grok-4.3 call ($1.06e-03) divided by 1e9
gave ~1.06e-12, which is implausible for a real API call. The correct conversion is `/1e10`:
`cost_in_usd_ticks / 1e10 ≈ $1.06e-03` (consistent with the observed response cost).

**Root cause**: xAI uses 10 decimal places for ticks (1 tick = $1e-10). xAI's cost-tracking
documentation uses "ticks" with a /1e10 conversion. Our initial assumption of /1e9 was wrong.

**Additional observation**: Even with the correct /1e10 conversion, grok-4.3's native cost
still diverges ~1.5× from `(total_tokens − prompt_tokens) × unit_price` because reasoning
tokens are billed but not reported in `completion_tokens`. Trust the provider-native field.

**Before-you-build implication**: Always verify `cost_in_usd_ticks` conversion against a known
reference call before using it in a cost model. Record the live ratio for each provider.

Source: L0-smoke-and-harness (surprise 5), results-digest gotcha 1, 3.

---

## EG-6: Reasoning models return empty text under a small token budget

Live verified (L0-smoke-and-harness, harness providers.py REASONING_FLOOR).

**What was expected**: A `max_completion_tokens=16` budget would allow the model to return a
short answer (e.g., a number, a word).

**What happened live**: gpt-5-mini with `max_completion_tokens=16` returned `text=""`. The budget
was consumed by hidden reasoning tokens before any visible content was generated.

**Root cause**: Reasoning models (gpt-5, gpt-5-mini, o-series, grok-4.x by default) spend tokens
on internal chain-of-thought before emitting output text. A small `max_completion_tokens` can be
exhausted entirely by reasoning, leaving zero tokens for visible content.

**Additional observation**: gpt-5 and o-series also use `max_completion_tokens` (not `max_tokens`)
and reject custom `temperature`. The harness must branch on model family.

**Before-you-build implication**: Set `REASONING_FLOOR=2048` for any reasoning model. Do not
use `max_tokens < 512` for gpt-5/o-series. Check `finish_reason`: if it is "length" and
content is empty, increase the budget.

Source: L0-smoke-and-harness (surprise 4), results-digest gotchas 1–2.

---

## EG-7: MoA aggregator cost dominates — MoA is not cheap

Live verified (X1-mixture-of-agents).

**What was expected**: MoA costs ~N × cheap_call + 1 aggregation call. Since cheap calls are
cheap, total cost should be moderate.

**What happened live**: MoA on 45 tasks cost $0.09966 — 60× always-cheap and 4.64× always-strong.
The aggregator was gpt-4o (mid-tier), not nano/mini. Coding tasks have 700-token budgets.
3 proposals × 700 tokens × 18 coding tasks × gpt-4o mid prices dominates the total.

**Root cause**: (1) The aggregator model choice matters as much as the proposers. A gpt-4o
aggregator over 18 coding items (already saturated) is pure waste. (2) MoA is applied to all
tasks, including QA and coding that are already saturated by cheap models.

**Before-you-build implication**: If using MoA, (1) choose the cheapest capable aggregator
(gpt-4o-mini, not gpt-4o, is sufficient for most aggregation tasks); (2) gate MoA behind a
classifier — apply it only to items predicted as hard; (3) verify proposers individually before
building an ensemble.

Source: X1 (surprise 1–2), results-digest gotcha 7.
