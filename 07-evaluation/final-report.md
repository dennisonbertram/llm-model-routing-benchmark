# Final Report — LLM Model Routing Degree

Live verified (2026-06-21/22). Numbers from authoritative digest and committed POC evidence.

## Headline

**A numpy logistic regression over embeddings matches always-strong accuracy (0.978) at 7.4× lower
cost — and that single strong model beats every cheap-model ensemble on this hard-math-gap workload.**

Routing the ~13% of tasks that genuinely need a stronger model is the win. Ganging up cheap models
to avoid that routing decision is not.

## Suite

45 tasks: 15 math (m1–m15), 12 QA (q1–q12), 18 coding (c1–c18). Pool: cheap `gpt-4o-mini`,
strong `gpt-4.1`, mid `gpt-4o`. Deterministic graders: numeric match, normalized QA, subprocess
unit-test execution. Cost = tokens × price (pricing.py). Source: L0-smoke-and-harness,
X5-router-benchmark-pareto.

## Baseline (L0-smoke-and-harness)

Live verified.

| Strategy | Accuracy | Total cost | Notes |
|---|---|---|---|
| always-cheap (gpt-4o-mini) | 0.844 | $0.00166 | — |
| always-strong (gpt-4.1) | 0.978 | $0.02148 | 12.9× cheap |
| oracle (cheapest-correct) | 0.978 | $0.00214 | unrealizable ceiling; 10% of strong |

Only 6/45 tasks require the strong model (m9, m10, m12, m13, m14, m15 — all hard math).
Task m8: both models wrong. Cheap is sufficient for 38/45.

## Best realizable Pareto frontier (X5-router-benchmark-pareto)

Live verified.

| Router | Accuracy | Cost | vs always-strong |
|---|---|---|---|
| always-cheap | 0.844 | $0.00166 | 12.9× cheaper |
| k-NN (k=5) CV | 0.889 | $0.00204 | — |
| k-NN (k=3) CV | 0.933 | $0.00221 | — |
| logistic (thr=0.7) CV | 0.956 | $0.00233 | — |
| **logistic (thr=0.9) CV** | **0.978** | **$0.00291** | **7.4× cheaper** |
| oracle (ceiling) | 0.978 | $0.00214 | 10× cheaper; unrealizable |

The capstone adaptive gateway, independently trained and served live via HTTP, reaches
acc=0.978, $0.00257 (8.4× cheaper than always-strong, 1.20× oracle) in 5-fold CV.
Source: L-capstone-adaptive-routing-gateway.

## Honest negatives (IMPORTANT — first-class findings)

Live verified.

These findings are NOT omissions. They are the most durable lessons in the degree.

### Cheap-model ensembles did NOT beat a single strong model on this workload

| Strategy | Accuracy | Cost | vs always-strong |
|---|---|---|---|
| MoA (3 cheap + gpt-4o aggregator) | 0.956 | $0.10159 | **4.7× MORE expensive AND lower accuracy** |
| self-consistency@5 (cheap) on math | 9/15 = 0.600 | — | strong: 14/15 = 0.933 |
| debate (3 models, 1 round) | 0.957 | $0.006278 | 3.84× MORE expensive, same accuracy |

MoA and debate are dominated on the cost-quality Pareto. Self-consistency barely moved the needle
(8→9/15 on math). The reason: the 6 failing tasks are hard-math capacity failures — cheap models
all produce the same wrong intermediate steps, so ensembling amplifies the same error.
Source: X1, X2, X3, X5.

### FrugalGPT self-confidence gate failed completely

gpt-4o-mini reports confidence=0.9 on every hard math item it answers incorrectly — the same
value it reports on easy correct answers. A threshold sweep from 0.1 to 0.9 produced identical
accuracy (0.844) and identical cost ($0.00391) at every threshold. The gate has zero
discriminative power. The cascade ran at 2.4× cheap cost with no accuracy gain.
Source: L3a-frugalgpt-cascade.

Note: a code-execution verifier (YES/NO) worked well on coding tasks — 18/18, 0 false accepts.
The failure is specific to math self-reported confidence.

### AutoMix verifier overhead ate the savings vs oracle

AutoMix (k=3 verifier, T=0.67): acc=0.978, cost=$0.006092. Oracle: $0.00214. AutoMix is 2.85×
oracle cost for the same accuracy — the 135 verifier calls ($0.003570) cost more than the
escalation savings.

## Routing discipline that worked

Live verified.

- **Heuristic router (L1)**: τ=0.40 → 0.956 acc, $0.00902 (42% of strong cost). Keyword + word-count
  features; no embeddings.
- **k-NN router (L2)**: k=7, thr=0.7, held-out test → 0.955 acc, 88% cost reduction vs strong.
- **Classifier router (L2b)**: logistic, test-set best op point → oracle-level accuracy at 6.3× cheaper.
- **Harness routing for coding (L3b)**: cheap-first + escalate-on-test-failure → 1.000 acc, $0.00148
  (7.5% of all-strong cost), 0 escalations (coding saturates cheap).
- **Gateway runtime (L3c, L4)**: OpenAI-compatible HTTP gateway; openai SDK base_url override works
  end-to-end; 10/10 live wire tests pass.
- **Failure modes (L5)**: 5/5 live failure modes handled — invalid slug, timeout, max_tokens overrun,
  budget guard, verifier no-escalate.

## Key structural findings

1. The routable gap is hard-math, not coding. Canonical LeetCode problems are memorized — gpt-4o-mini
   solves 18/18 coding tasks. Hard combinatorics/discrete math is where routing earns its cost.
2. Cheap-model accuracy is non-monotonic per-item. gpt-4o-mini fails tasks gpt-4.1-nano gets right.
   A "strict capability ladder" assumption mis-routes.
3. A good classifier (logistic over text-embedding-3-small) matches oracle accuracy at ~14% of
   strong cost. No fine-tuning, no external router service — just 36 labeled examples.
4. Cost-budget guards only bite in practice when per-call cost is real (short answers: ~$0.0001/call).

## Frontier tier follow-up (X6, GPT-5.5 — Live verified 2026-06-22)

Adding a frontier reasoning model as a top tier extends the thesis rather than overturning it:
- **GPT-5.5 reached 100% accuracy** (cleared the hard-math tail incl. `m8`, which neither cheap nor
  `gpt-4.1` solved) — but at **5.6× `gpt-4.1`'s cost** and ~2.75 s/call.
- A **realizable 3-tier router** (cheap → gpt-4.1 → gpt-5.5, one CV logistic score + two thresholds)
  reached the **same 100% at $0.00405 — 30× cheaper than always-gpt-5.5**, routing just 1 of 45
  items to the frontier model.
- Honest caveat: **`gpt-5.4` did not beat `gpt-4.1`** (0.978 each) yet cost 1.8× more (fixed `m8`,
  broke `m10`) — a higher version number is not a per-item capability guarantee.

Takeaway: try the more powerful model — and *route* to it. The frontier tier earns its premium only
on the hard tail. See `03-pocs/X6-frontier-tier/`, recipe R-011, gotcha G-016.

## Sakana / adaptive-orchestration track (S0–S3, Live verified 2026-06-22)

Triggered by Sakana AI's **Fugu** (learned multi-agent orchestration). We tested whether *adaptive*
orchestration beats a single model — from both ends of the model pool — and tested the **real Fugu** live.

- **S0:** GPT-5.5 solved **21/21** authored hard tasks — the frontier model saturates anything we can
  author + deterministically grade. (So orchestration has no headroom on authored tasks; this is *why*
  Sakana benchmarks at the genuine frontier for sub-1-point margins.)
- **S1/S2:** A faithful vendored **Multi-LLM AB-MCTS** (Sakana's one open method, arXiv:2503.04412) over a
  diverse cheap pool (DeepSeek/Qwen/Gemini via OpenRouter), no-leakage public/hidden split. AB-MCTS,
  repeated-sampling, and best-single all **plateau at 0.950** on hard coding — none reach GPT-5.5's 1.000
  (correlated errors → no complementarity). AB-MCTS *is* 8× more sample-efficient than repeated sampling,
  but efficiency ≠ a capability gain; and search is **bounded by verifier coverage** (it early-stops at
  public-perfect while a hidden case still fails).
- **S3 (the real Fugu, live):** `fugu-ultra` **matches** GPT-5.5 (1.000) but at **12.2× cost, 5.6× latency,
  ~7,700 orchestration tokens/task**; `fugu` (Mini) is **less** accurate (0.905) at **4×** cost.

**Verdict:** orchestration — whether AB-MCTS over cheap models or Sakana's frontier conductor — is a
**cost/latency multiplier, not a free accuracy win**. For tasks a single strong model can solve, **route
to the right single model**; reserve orchestration for the genuine capability frontier (verifier-gated,
uncorrelated pool) where its margins are small. This *strengthens* the degree's thesis from a new angle.
(See G-017, S0–S3.) Fugu's own frontier-benchmark wins remain Sakana's cited claims, not reproduced here.

## Corpus state

20 POCs, all green/with live evidence committed (L0–L5, X1–X6, L-capstone, S0–S3). Distillation +
skill-pack authored. Evidence tiers: "Live verified" in every rank-bearing markdown section.

## Degree date

2026-06-21/22.
