# Before You Build — LLM Model Routing

Must-know preconditions before writing any model-routing code. Every item is cited.
Evidence tiers appear in each section: **Live verified** (from a real POC run in this
degree), **Research supported** (papers/docs), or **Inferred**.

---

## 1. Required credentials and what they unlock

**Live verified** (L0; L4; capstone) — you need at minimum:

- `OPENAI_API_KEY` — required for `gpt-4o-mini` (cheap default), `gpt-4.1` (strong
  default), and `text-embedding-3-small` (predictive router features). This is the
  minimum key to run every POC in this degree. All 15 POCs ran live with this key.
- `ANTHROPIC_API_KEY` — required for Claude models in the ensemble pool
  (`config.ENSEMBLE_CHEAP` includes `claude-haiku-4-5-20251001`). Needed for X1 (MoA).
- `XAI_API_KEY` — optional. Unlocks `grok-4.3` smoke test in L0. Grok-4.3 introduces
  special billing mechanics (see Section 4 below) that must be handled before you add
  it to a routing pool.
- `OPENROUTER_API_KEY` — optional enhancement. If present, add an OpenRouter backend
  to unlock open-weight models (Qwen/Llama/DeepSeek) and native per-generation cost
  accounting. NOT required for any core POC in this degree.

Load credentials without printing them:

```bash
set -a; . .agent-university/secrets.local.env; set +a
[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET
```

Never use shell expansions that print the key value. Never commit the secrets file.

---

## 2. Model pool and what each tier actually costs

**Live verified** (L0; X5) — the harness uses three tiers:

| Role | Model | Accuracy (45 tasks) | Cost (45 tasks) |
|---|---|---|---|
| cheap | `gpt-4o-mini` | 0.844 | $0.00166 |
| mid | `gpt-4o` | (used as MoA aggregator only in X1) | — |
| strong | `gpt-4.1` | 0.978 | $0.02148 (12.9× cheap) |
| oracle ceiling | cheapest-correct per task | 0.978 | $0.00214 (~10% of strong) |

The 12.9× cost ratio between cheap and strong is **the headroom you are competing to
capture**. A perfect router would reach strong accuracy at oracle cost ($0.00214). The
best trained router in this degree (logistic thr=0.9, X5 5-fold CV) reached
**acc=0.978, $0.00291 — 7.4× cheaper than always-strong**.

Config constants (harness `config.py`): `CHEAP_DEFAULT="gpt-4o-mini"`,
`STRONG_DEFAULT="gpt-4.1"`, `MID_DEFAULT="gpt-4o"`,
`ENSEMBLE_CHEAP=["gpt-4o-mini","gpt-4.1-mini","claude-haiku-4-5-20251001"]`.

---

## 3. Build a routing benchmark honestly — what to measure

**Live verified** (L0; X5; capstone)

### The outcome matrix is the foundation

Before building a router, run both cheap and strong over your full task suite and
record per-item correctness and cost. This is the **outcome matrix** (the harness calls
it the `labelset`). It lives at `harness/.cache/labelset.json` and
`03-pocs/L0-smoke-and-harness/source/l0_summary.json`.

The outcome matrix lets you:
- Compute the oracle upper bound (cheapest-correct per item)
- Identify which items actually need the strong model
- Score any routing policy against real costs without re-billing

In this degree, only **6 of 45 tasks require the strong model** — all hard math:
m9, m10, m12, m13, m14, m15. The remaining 38/45 tasks are solved correctly by the
cheap model alone. One task (m8) is wrong for both models.

### Use cross-validation, not a single train/test split

**Live verified** (X5; capstone; L2b) — for a small labeled set (45 items here), a
single held-out split can produce unstable accuracy estimates. 5-fold CV assigns each
task to exactly one held-out fold so every item is evaluated exactly once, with no
leakage. Both X5 and the capstone use 5-fold CV. Single-split results (L2 on a 22-item
test set, L2b on 13 items) show more variance. Report CV results as the canonical number.

### Report the Pareto frontier, not a single operating point

**Live verified** (L1; L2; L2b; X5) — threshold is a continuous cost-quality knob.
Always sweep the decision threshold (τ) and report the full accuracy-vs-cost curve. The
X5 benchmark realizable frontier:

```
always-cheap        acc=0.844  $0.00166   <- cost floor
k-NN(k=5) CV        acc=0.889  $0.00204
k-NN(k=3) CV        acc=0.933  $0.00221
logistic(thr=0.7)   acc=0.956  $0.00234
logistic(thr=0.9)   acc=0.978  $0.00291   <- matches always-strong at 1/7.4 cost
oracle              acc=0.978  $0.00214   <- unrealizable ceiling
always-strong       acc=0.978  $0.02148
```

A single-point accuracy number without cost context is incomplete.

### What to measure in each run

For each routing policy, record: accuracy, total cost (USD), cost-per-correct answer,
mean latency, fraction of traffic routed cheap, and per-item decisions. The harness
`RunResult` object exposes `.accuracy()`, `.total_usd()`, `.usd_per_correct()`,
`.mean_latency()`, `.pct_cheap(models)`. Every benchmark in this degree records all of these.

---

## 4. Wire-format gotchas — what NOT to mock

**Live verified** (L0)

### Reasoning models need a token floor

`gpt-5-mini`, o-series, and any model whose ID contains "gpt-5", "o1", "o3", "o4",
"o-preview" spends tokens on a hidden reasoning chain before emitting visible content.
Under a small budget (e.g., `max_tokens=16`), all tokens are consumed by reasoning and
the response content is an empty string — HTTP 200, no error, no content. Floor all
reasoning model calls at `REASONING_FLOOR=2048`.

### o-series API surface differs from chat completions

These models use `max_completion_tokens` (not `max_tokens`) and reject custom
`temperature` with HTTP 400. A harness that passes the same parameter set to all models
will break on the first reasoning model it encounters. Branch on `is_reasoning_model(model)`.

### grok-4.3 hides reasoning tokens from `completion_tokens`

`grok-4.3` reports its reasoning tokens separately (`total − prompt` to get total
billed completion). The ticks-to-USD conversion is `/1e10` (NOT `/1e9`). Even with the
correct conversion, uniform `tokens × price` diverges ~1.5× from native cost for cached
sessions. Trust `native_cost_usd` (the `cost_in_usd_ticks / 1e10` field) for grok-family
models rather than computing cost from token counts.

### Uniform token×price cost is the consistent accounting method

**Live verified** (L0; X5; capstone) — the harness uses `cost = Σ tokens × unit_price`
from a reconciled price table (`pricing.py`). OpenAI and Anthropic do not return USD in
their API responses; cost must be computed client-side. This method is consistent across
providers and makes the benchmark reproducible without changing methodology. The
per-provider exceptions (grok native cost, reasoning token billing) are documented in
`pricing.py` and `providers.py`.

### Do not use mocks as evidence

A POC is only "green" if the response contains a real model answer from a live API call.
Local helper tests are labeled `Invalid for service evidence`. RED state = real failure
with real credentials missing. GREEN state = real API calls return correct answers.

---

## 5. Common wrong assumptions

**Live verified** (L0; L3a; X1; X2; X5)

### "Coding tasks discriminate model strength"

They do not, at standard HumanEval-style prompts. In this degree, `gpt-4o-mini` solved
all 18 coding tasks including complex algorithms (sliding window, LIS, regex matching,
coin change). The routable gap was entirely in hard **math** (combinatorics, algebra,
counting). If your benchmark contains only canonical LeetCode/algorithm problems, it will
show cheap accuracy ≈ 100% and every router will look the same — the suite is saturated.
Build tasks where cheap actually fails (hard multi-step reasoning, unfamiliar domains).
(L0; L3b)

### "Ensembles of cheap models beat a single strong model"

Not on a hard-reasoning-gap workload. MoA (3 cheap + aggregator): **acc=0.956,
$0.10159** — less accurate AND 4.7× more expensive than always-strong. Self-consistency
@5 on hard math: **9/15** vs single cheap 8/15 vs single strong 14/15. Multi-agent
debate: **acc=0.957 at 3.84× strong cost** — dominated. Ensembles multiply errors when
cheap models share the same reasoning gap. They pay off only when cheap models are
individually competitive and their errors are uncorrelated — not when the gap is hard
reasoning. (X1; X2; X3; X5)

### "FrugalGPT self-confidence gating catches escalation-worthy items"

It does not when the cheap model is overconfident. `gpt-4o-mini` returned confidence=0.9
for all six hard-math answers it got wrong (m9, m10, m12, m13, m14, m15). Sweeping the
threshold from 0.1 to 0.9 produced identical results — the gate is non-discriminative on
the items that most need escalation. FrugalGPT cascade result: **acc=0.844 at $0.00391**
— same accuracy as always-cheap but 2.4× more expensive due to gate call overhead. (L3a)

### "Cheap model accuracy is monotonic — cheaper means strictly worse per item"

It is not. `gpt-4o-mini` sometimes fails a task that `gpt-4.1-nano` gets right. A router
cannot assume the cheap model is a reliable lower bound per item; the outcome matrix must
be measured, not inferred. (L0)

### "The oracle is an achievable target"

The oracle is an **unrealizable ceiling** — it peeks at per-item correctness before
routing, which requires knowing the answer before asking. Report it separately from
realizable routers. A logistic router at thr=0.9 reached oracle accuracy (0.978) but
spent $0.00291 vs oracle $0.00214 — 36% above the oracle cost. No router in this degree
reached oracle cost. (X5; capstone)

### "AutoMix verifier overhead is negligible"

It is not. AutoMix with k=3 self-verifier calls added $0.003570 overhead across 45
tasks — consuming the oracle gap entirely. The result: $0.006092 vs oracle $0.002140 for
the same accuracy. AutoMix is most valuable before labeled data exists (no training
needed); once you have labels, a classifier dominates on cost. (X4)

---

## 6. Saturation and non-monotonicity traps

**Live verified** (L0; L3b; L2b)

### Task saturation means the benchmark cannot discriminate

When cheap accuracy is 100% on a discipline, no routing policy can improve on it — the
suite is saturated. Coding saturated at cheap in this degree (18/18 correct for
`gpt-4o-mini`). Math did not saturate (cheap 8/15, strong 14/15 — hard items remain).
Before finalizing a benchmark, verify that cheap accuracy is meaningfully below strong
accuracy on at least some tasks. If cheap ≥ 98% across all tasks, routing is a
no-op and measuring it is not useful.

### Small labeled sets produce fragile classifiers

`L2b` (logistic regression, 45 items total, 7 hard items) had 84% of prompts correctly
solved by cheap — severe class imbalance. The classifier learned the base rate, not the
hard boundary. P(cheap_correct) clustered in [0.74, 0.91]; the effective decision range
was narrow (τ ∈ [0.75, 0.90]). The RouteLLM paper required hundreds to thousands of
labeled examples for stable classification. With fewer than ~100 hard examples, expect
a classifier that barely improves on the base rate unless the hard items are very
dissimilar in embedding space. (L2b)

### Non-monotonicity means you need a real outcome matrix

Because cheap-model accuracy is non-monotonic per item — the cheap model sometimes fails
where a cheaper-still model succeeds — you cannot infer the outcome matrix from
benchmarks on other models. Always measure your specific cheap and strong models on your
specific task suite. (L0)

---

## 7. Budget guard — when it matters and when it does not

**Live verified** (L5; capstone)

A cost-budget guard only bites when per-call cost is real and cumulative. In this degree,
simple short answers cost ~$0.000004–$0.00001 per call. With a $0.00025 cap, the guard
fired after 4 requests; with a $0.000015 cap, it fired after 3. For interactive chatbots
or long-context calls where per-request cost is higher (>$0.001), the guard fires
sooner and is more consequential.

The capstone gateway enforces the guard at request time: compute estimated cost from
token count estimate, compare to remaining budget, refuse or downgrade if it would
exceed. The L5 budget guard in practice refused the 4th request when remaining budget
($0.0000036) was smaller than the cheapest model's estimated cost ($0.00000375). (L5)

---

## 8. What is live-verified in this degree

**Live verified** (all 15 POCs, 2026-06-21/22)

All 15 POCs ran against live OpenAI (and Anthropic for X1) APIs with real credentials.
No mocks at any service boundary. Summary:

| POC | Focus | Key live metric |
|---|---|---|
| L0 | Harness + baselines | cheap acc=0.844, strong acc=0.978, oracle $0.00214 |
| L1 | Heuristic router | τ=0.40: acc=0.956, $0.00902 (42% of strong) |
| L2 | Embedding k-NN | k=7,thr=0.7: acc=0.955, 88% cost reduction vs strong |
| L2b | Logistic classifier | τ=0.80, test set: oracle accuracy, 6.3× cheaper than strong |
| L3a | FrugalGPT cascade | FAILED: acc=0.844 (== cheap) at $0.00391 — gate non-discriminative |
| L3b | Harness/opencode routing | All 18 coding tasks solved cheap-first, 0 escalations |
| L3c | OpenAI-compat gateway seam | 10/10 live tests pass; SDK base_url override end-to-end |
| L4 | HTTP gateway runtime | 3 live curls routed; ledger persisted; RED=HTTP 502 no key |
| L5 | Failure modes | 5 failure modes triggered live; 9/9 tests pass |
| X1 | Mixture-of-Agents | MoA: acc=0.956, $0.09966 — 4.64× more expensive than strong |
| X2 | Self-consistency | math @5: 9/15 vs single strong 14/15 — barely helps |
| X3 | Multi-agent debate | acc=0.957 at 3.84× strong cost — dominated |
| X4 | AutoMix verification cascade | acc=0.978 at $0.006092 — 2.85× oracle, verifier overhead |
| X5 | RouterBench Pareto | logistic(0.9): acc=0.978, $0.00291 — 7.4× cheaper than strong |
| capstone | Adaptive gateway | adaptive(0.8): acc=0.978, $0.00257 — 8.4× cheaper than strong |
