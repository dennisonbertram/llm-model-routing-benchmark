# Curriculum — LLM Model Routing

Live verified. Ordered learning path from L0 (baseline measurement) through the capstone
(adaptive gateway). Each step builds on the one before it. Every POC ran live.

Back to [index](index.md).

---

## Prerequisites

- Python 3.9, stdlib + numpy (no pip installs)
- `OPENAI_API_KEY` loaded
- Harness in `harness/` (frozen — do not edit)
- Read the spec: `../../00-metadata/degree.md` or `.context/model-routing-spec.md`

---

## Stage 1 — Baseline and harness (L0)

**POC:** `03-pocs/L0-smoke-and-harness`
**Lab:** [labs/lab-L0-baseline.md](labs/lab-L0-baseline.md)
**Time:** ~30 min

What you do:
1. Confirm 3-provider live access (OpenAI, Anthropic, xAI).
2. Run the 45-task suite through always-cheap and always-strong.
3. Compute the oracle ceiling (cheapest-correct per task).
4. Record the routing prize: only 6/45 tasks need the strong model; all 6 are hard math.

Key numbers to internalize (live-measured):
- always-cheap: acc=0.844, $0.00166
- always-strong: acc=0.978, $0.02148 (12.9x cheap cost)
- oracle (unrealizable ceiling): acc=0.978, $0.00214 (~10% of strong cost)

---

## Stage 2 — Heuristic routing (L1)

**POC:** `03-pocs/L1-heuristic-router`
**Lab:** [labs/lab-L1-heuristic.md](labs/lab-L1-heuristic.md)
**Lesson:** [lessons/L-heuristic-routing.md](lessons/L-heuristic-routing.md)
**Time:** ~30 min

What you do:
1. Build a score function over word count, reasoning keywords, clause complexity, digit density.
2. Sweep threshold from 0.2 to 0.8 to trace a Pareto curve.
3. Confirm the selected point (thr=0.40): acc=0.956, $0.00902, 42% of strong cost.

What you learn:
- Heuristics plateau around 96% accuracy; no prompt-only rule reaches oracle efficiency.
- Threshold is the knob an operator turns to trade cost for quality.
- False-positive strong calls are the dominant cost waste (5 over-routed items here).

---

## Stage 3 — Embedding-based routing (L2 + L2b)

**POCs:** `03-pocs/L2-embedding-knn-router`, `03-pocs/L2b-classifier-router`
**Lab:** [labs/lab-L2-knn.md](labs/lab-L2-knn.md)
**Lesson:** [lessons/L-predictive-routing.md](lessons/L-predictive-routing.md)
**Time:** ~45 min

What you do:
1. Embed all 45 prompts via text-embedding-3-small (~$3e-05 one-time).
2. Build a kNN router (k=3/5/7) and sweep vote threshold.
3. Train a logistic regression on embedding features; sweep decision threshold.
4. Identify the best operating point: logistic thr=0.8 on test set = oracle accuracy at 6.3x cheaper than strong.

What you learn:
- kNN(k=7, thr=0.7): acc=0.955, 88% cost reduction vs always-strong (L2).
- Logistic(thr=0.8): oracle accuracy on test set, $0.00077 for 13 items (L2b).
- The embedding space does NOT sharply separate hard-math from medium-math — the classifier works
  because even weak discrimination at the right threshold is enough.
- Honest: only 7/45 items need strong. With that few negatives, logistic regression learns the
  base rate, not fine-grained difficulty. More labeled data would help.

---

## Stage 4 — Cascade routing (L3a + L3b)

**POCs:** `03-pocs/L3a-frugalgpt-cascade`, `03-pocs/L3b-harness-routing-coding-agent`
**Lab:** [labs/lab-L3-cascade.md](labs/lab-L3-cascade.md)
**Lesson:** [lessons/L-cascade-routing.md](lessons/L-cascade-routing.md)
**Time:** ~45 min

What you do (L3a — FrugalGPT):
1. Build a cheap→strong cascade with a self-confidence gate on math/QA.
2. Observe the gate failure: gpt-4o-mini returns confidence=0.9 on ALL six wrong hard-math answers.
3. Confirm the coding verifier (YES/NO judge) works: 18/18 coding, 1 escalation, 0 false accepts.
4. Record the honest result: acc=0.844 (== always-cheap) at $0.00391 (2.4x cheap cost). FAILURE.

What you do (L3b — opencode escalation):
1. Build a cheap-first multi-step loop: cheap writes code → run tests → escalate to strong on failure.
2. Measure on 18 coding tasks: acc=1.000, $0.00148 (7.5% of all-strong), 0 escalations.
3. Confirm the repair path works via a synthetic deliberately-broken test.

What you learn:
- Self-confidence gating is non-discriminative when the cheap model is overconfident-and-wrong.
- An independent structural verifier (code test execution) is far more reliable than self-report.
- The discipline matters: coding saturates cheap; math does not. Zero escalations on coding is the correct outcome.

---

## Stage 5 — Gateway deployment (L3c + L4 + L5)

**POCs:** `03-pocs/L3c-openai-compatible-gateway-integration`, `03-pocs/L4-routing-gateway-runtime`, `03-pocs/L5-failure-modes-and-observability`
**Lab:** [labs/lab-L4-gateway.md](labs/lab-L4-gateway.md)
**Lesson:** [lessons/L-gateway-deployment.md](lessons/L-gateway-deployment.md)
**Time:** ~45 min

What you do (L3c):
1. Expose the router behind OpenAI-compatible `POST /v1/chat/completions`.
2. Override `base_url` in the openai-python SDK and confirm 10/10 live tests pass.

What you do (L4):
1. Run the gateway as a real local HTTP server; curl it from a separate process.
2. Inspect `x_routing` metadata in the response; read the persisted cost ledger.

What you do (L5):
1. Trigger 5 live failure modes: invalid slug (404→fallback), timeout (retry), max_tokens overlimit
   (400→fallback), budget guard (refused), verifier no-escalate.
2. Confirm all 9 behavioral tests pass with structured observability logs.

What you learn:
- `model: "auto"` is the client-side convention; the gateway returns the actually-served model name.
- ProviderError wraps HTTP 404, 400, and network-level TimeoutError uniformly.
- The budget guard makes a real call, measures actual cost, and only accepts if it fits remaining budget.

---

## Stage 6 — Ensemble strategies (X1–X4)

**POCs:** `03-pocs/X1-mixture-of-agents`, `03-pocs/X2-self-consistency-vote`, `03-pocs/X3-multi-agent-debate`, `03-pocs/X4-verification-cascade-automix`
**Lab:** [labs/lab-X-ensembles.md](labs/lab-X-ensembles.md)
**Lesson:** [lessons/L-ensemble-strategies.md](lessons/L-ensemble-strategies.md)
**Time:** ~1 hour

What you observe (NEGATIVE findings — first-class lessons):
- MoA (3 cheap + aggregator): acc=0.956, $0.100 — 4.64x more expensive than always-strong AND less accurate. (X1)
- Self-consistency @5 cheap on math: 9/15 vs 8/15 single cheap vs 14/15 single strong. Barely helps. (X2)
- Debate (3 models, 1 round): 0.957 == strong but 3.84x its cost. Dominated. (X3)
- AutoMix (kNN self-verify, escalate): 0.978 at 71.6% savings vs always-strong; but 2.85x oracle cost. Verifier overhead eats headroom. (X4)

What you learn:
- On a workload where the difficulty gap is a hard reasoning tail, ensembles multiply cost and still
  miss the tail. Routing that tail to a stronger model beats ganging up cheap models.
- Ensembles pay off only when members are individually competitive and their errors are uncorrelated.
  None of those conditions hold for hard math here.

---

## Stage 7 — Full benchmark (X5)

**POC:** `03-pocs/X5-router-benchmark-pareto`
**Lab:** [labs/lab-X5-benchmark.md](labs/lab-X5-benchmark.md)
**Reference:** [reference/pareto-numbers.md](reference/pareto-numbers.md)
**Time:** ~30 min (mostly cache hits)

What you do:
1. Run all routers over one shared evaluation: always-cheap, always-strong, random-50%,
   heuristic, kNN, logistic, MoA, self-consistency, oracle.
2. Emit the cost-vs-quality Pareto frontier table.
3. Identify the realizable frontier: always-cheap → kNN(k=5) → kNN(k=3) → logistic(0.7) → logistic(0.9).

Key headline (live-measured):
- logistic(thr=0.9): acc=0.978, $0.00291 — matches always-strong, 7.4x cheaper.
- MoA: acc=0.956, $0.10159 — 4.7x more than strong AND less accurate. (NEGATIVE, confirmed)

---

## Stage 8 — Capstone adaptive gateway

**POC:** `03-pocs/L-capstone-adaptive-routing-gateway`
**Lab:** [labs/lab-X5-benchmark.md](labs/lab-X5-benchmark.md)
**Time:** ~30 min (CV + live curls)

What you do:
1. Run 5-fold CV over 45 tasks; confirm adaptive(thr=0.8) = acc=0.978, $0.00257 (8.4x cheaper than strong).
2. Start the OpenAI-compatible HTTP gateway; curl two requests and confirm routing decisions.
3. Test the budget guard (cap forces cheap after spending $0.00025) and provider fallback.

What you have now: a live, deployable, benchmark-validated routing gateway that routes ~71% of
traffic to the cheap model and catches the hard-math tail with the strong model.

---

## Learning path summary

```
L0 baseline  →  L1 heuristic  →  L2/L2b predictive  →  L3a/b cascade
    ↓
L3c/L4/L5 gateway  ←  X1-X4 ensembles (negative lessons)  ←  X5 benchmark
    ↓
L-capstone (adaptive gateway)
```

The realizable Pareto frontier (from [reference/pareto-numbers.md](reference/pareto-numbers.md)):

```
always-cheap        acc=0.844  $0.00166
kNN(k=5) CV         acc=0.889  $0.00203
kNN(k=3) CV         acc=0.933  $0.00221
logistic(thr=0.7)   acc=0.956  $0.00233
logistic(thr=0.9)   acc=0.978  $0.00291   <- matches strong, 7.4x cheaper
---
oracle (unrealizable ceiling)  acc=0.978  $0.00214
always-strong       acc=0.978  $0.02148   <- dominated by logistic(thr=0.9)
```
