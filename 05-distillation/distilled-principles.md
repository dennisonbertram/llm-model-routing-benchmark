# Distilled Principles — LLM Model Routing

The highest-leverage takeaways from this degree. All 15 POCs ran against live OpenAI
and Anthropic APIs on 2026-06-21/22. Evidence tiers are explicit; every quantitative
claim matches the results digest or a POC's committed evidence.

---

## 1. The routing prize is real — measure it before trusting it

**Live verified** (L0)

The cost-quality gap and the oracle headroom justify building a router, but they must be
measured on your own workload. In this degree:

- always-cheap (`gpt-4o-mini`): acc=0.844, $0.00166
- always-strong (`gpt-4.1`): acc=0.978, $0.02148 — 12.9× cheap
- oracle (cheapest-correct per task): acc=0.978, $0.00214 — ~10% of strong cost

Only 6 of 45 tasks required the strong model, all hard math (m9, m10, m12, m13, m14,
m15). Cheap sufficed for 38/45. One task (m8) was wrong for both models — the oracle
does not guarantee 100%.

**Action:** Build the outcome matrix first (run both models, record per-item correctness
and cost). Confirm the gap exists. If cheap accuracy ≥ 95% on your suite, routing is
a marginal optimisation.

---

## 2. A trained logistic router approximately matches the oracle — at ~7–8× cheaper than always-strong

**Live verified** (X5; capstone; L2b)

The best realizable router in this degree — a logistic regression over
`text-embedding-3-small` embeddings, 5-fold CV — reached the oracle accuracy ceiling
at near-oracle cost:

- X5 logistic(thr=0.9) CV: acc=0.978, $0.00291 — 7.4× cheaper than strong
- Capstone adaptive(thr=0.8) CV: acc=0.978, $0.00257 — 8.4× cheaper than strong

The route to this result is straightforward: embed the prompt with
`text-embedding-3-small`, train a logistic regression on (embedding, cheap-correct)
labels from the outcome matrix, sweep the decision threshold to find the operating point
that meets your accuracy SLA, and evaluate with 5-fold CV to avoid leakage.

The threshold is a continuous cost-quality knob. Higher threshold = more conservative =
more traffic to strong = higher cost, higher accuracy. The Pareto curve is smooth and
predictable.

---

## 3. Ensemble methods (MoA, debate, self-consistency) did NOT beat a single strong model on this workload

**Live verified** (X1; X2; X3; X5)

This is a first-class negative finding, not an omission.

| Method | Accuracy | Cost | vs always-strong cost |
|---|---|---|---|
| MoA (3 cheap + aggregator) | 0.956 | $0.10159 | **4.7× more expensive** |
| self-consistency@5 (math only) | 9/15 | — | barely above single cheap 8/15 |
| multi-agent debate (3 models, 1 round) | 0.957 | — | 3.84× strong cost |
| always-strong (single gpt-4.1 call) | 0.978 | $0.02148 | 1.0× |

**Why ensembles fail here:** The accuracy gap in this workload is concentrated in hard
mathematical reasoning (m9–m15). When cheap models share the same reasoning gap, running
N of them produces N wrong answers — multiplying cost without fixing the deficit.
Ensembles pay off when cheap models are individually competitive and their errors are
uncorrelated. They are not a universal substitute for a stronger model.

The MoA paper's published wins are on different benchmarks and model pools. The measured
result on this suite is a loss on both cost and quality versus a single strong call.

---

## 4. FrugalGPT self-confidence gating fails when the cheap model is overconfident

**Live verified** (L3a)

The cascade cheap → strong gated by self-reported confidence produced:
**acc=0.844 at $0.00391** — identical to always-cheap accuracy but 2.4× more expensive.

Root cause: `gpt-4o-mini` returned confidence=0.9 for all six hard-math answers it got
wrong (m9, m10, m12, m13, m14, m15). Sweeping the threshold from 0.1 to 0.9 produced
exactly the same routing decisions because the gate values never spanned any threshold.

The coding verifier (LLM-judge YES/NO on produced code) worked much better: 18/18
correct, 1 unnecessary escalation, 0 false accepts. Structural verifiers (can the code
run and pass tests?) are more reliable than self-reported confidence for any domain where
correctness can be checked independently.

**Takeaway:** If you build a cascade, use a trained verifier or an independent judge —
not the same model asking itself whether its answer is correct.

---

## 5. The harness-routing (opencode-style) escalate-on-failure pattern works — but coding saturates cheap

**Live verified** (L3b; L0)

The cheap-first → escalate-on-test-failure loop for coding:
- all-cheap: acc=1.000, $0.00148 (18 coding tasks)
- all-strong: acc=1.000, $0.01967 — 13.25× more expensive
- routed (cheap-first): acc=1.000, $0.00148 — **identical to all-cheap, 0 escalations**

`gpt-4o-mini` at temperature=0 solved all 18 coding tasks including complex algorithms.
The repair mechanism is real (verified by synthetic test: a deliberately broken fizzbuzz
stub repaired by gpt-4.1 and passing tests), but it was not needed here. The coding
discipline saturates at cheap; the routable gap for this degree lives in math.

**Takeaway:** Harness routing is the correct pattern for production coding agents —
cheap first, escalate on failure, strong as the repair tier. The cost savings are real
when tasks sometimes fail at cheap. When cheap saturates (100% accuracy), routed and
always-cheap are identical.

---

## 6. AutoMix verification adds signal but the verifier overhead dominates

**Live verified** (X4)

AutoMix at T=0.34: acc=0.978, $0.006092 — correct (matches strong) but 2.85× the
oracle cost ($0.002140). The k=3 verifier calls added $0.003570 overhead across 45 tasks.

The verifier is well-calibrated: 100% precision in the high-confidence bucket (33/33
items with conf ≥ 0.67 were correctly cheap), and 45.5% cheap-correct in the
low-confidence bucket (signal is real). But the overhead eats all the savings.

**Takeaway:** AutoMix-style verification is most valuable before labeled data exists —
it provides a routing signal without training. Once you have labeled history, a
classifier (L2b) dominates AutoMix on cost at the same accuracy.

---

## 7. A deployed OpenAI-compatible gateway is the production integration pattern

**Live verified** (L3c; L4; L5; capstone)

Any OpenAI SDK client can call the routing gateway by setting `base_url` to the gateway
address. The client code does not change; routing is transparent except for the
`x_routing` extension field in the response. Forced model routing (`model:"gpt-4o-mini"`
vs `model:"auto"`) bypasses heuristics when the caller needs explicit control.

The gateway must handle real provider faults (not just happy-path):
- Invalid slug → HTTP 404 from provider → fallback to cheap model (FM1)
- Network timeout → retry with extended timeout (FM2)
- `max_tokens` over limit → HTTP 400 → fallback with corrected params (FM3)
- Budget guard trips → refuse or force-cheap (FM4)

All five failure modes were triggered live against the real OpenAI API in L5. The
`/v1/health` endpoint passes even without credentials — health-check liveness and
credential-validity are independent concerns and must be tested separately.

---

## 8. Cost accounting requires uniform methodology — with provider-specific exceptions

**Live verified** (L0)

Use `cost = Σ tokens × unit_price` from a reconciled price table (the harness
`pricing.py`). OpenAI and Anthropic do not return USD in API responses; cost is computed
client-side. This is consistent and reproducible.

Exceptions that require special handling:
- **grok-4.3**: hides reasoning tokens from `completion_tokens`; bill via
  `total_tokens − prompt_tokens`; ticks→USD is `/1e10` (not `/1e9`); still diverges
  ~1.5× from native cost for cached sessions. Trust `cost_in_usd_ticks / 1e10`.
- **o-series**: reasoning tokens billed as output tokens; keep `REASONING_FLOOR=2048`
  to avoid blank responses from budget starvation.

Never mix cost methods within a single benchmark run — use uniform `tokens × price`
everywhere and note the exceptions.

---

## 9. Structured observability is not optional

**Live verified** (L4; L5; capstone)

Every routing decision must emit a structured log line: timestamp, event type, model
chosen, decision reason, tokens, USD, latency. The capstone gateway persists to
`gateway-ledger.jsonl`. L5 confirmed: structured logs must never contain API key values
(the test suite explicitly checks for key leakage).

The log enables: offline cost audit, routing pattern analysis, budget tracking, and
detecting systematic misroutes. Without it, you cannot know whether the router is saving
money or where escalations are happening.

Sample log line (live from L4):

```json
{"ts": "2026-06-22T03:48:57Z", "decision": "default_cheap", "chosen_model": "gpt-4o-mini",
 "prompt_tokens": 14, "completion_tokens": 7, "usd": 6.3e-06, "latency_ms": 763}
```

---

## 10. The oracle is an unrealizable ceiling — report it separately

**Live verified** (L0; X5; capstone)

The oracle routes each item to the cheapest model that answers correctly, using knowledge
of the correct answer before asking — it cannot be deployed. It sets the theoretical
efficiency frontier: oracle acc=0.978, $0.00214 on this suite.

Always show the oracle in Pareto plots so readers understand the gap between the best
realizable router and the theoretical limit. The capstone adaptive(thr=0.8) reached
$0.00257 — 1.20× the oracle cost, 36% above the floor. No deployed router in this
degree broke the oracle cost at oracle accuracy.

Presenting a realizable router result without the oracle context makes the achievement
look stronger than it is. Show both.
