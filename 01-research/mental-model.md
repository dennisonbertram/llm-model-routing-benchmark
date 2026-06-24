# Mental Model — Cost-vs-Quality Pareto Framing for LLM Routing

**Degree**: 01-llm-model-routing  
**Evidence label**: Research supported but not live verified  
**Date compiled**: 2026-06-21

This file builds the conceptual foundation for understanding, designing, and evaluating LLM routers. Every router evaluation in the POC ladder uses the framing established here.

Cross-references: `capability-map.md` enumerates the strategies. `common-use-cases.md` applies the framing per discipline.

---

## 1. The Cost-vs-Quality Pareto Frontier

### The fundamental tradeoff

Every LLM routing problem has two competing objectives:

1. **Minimize cost** — measured in USD per query (tokens × unit price).
2. **Maximize quality** — measured by task accuracy (exact match, LLM-judge score, pass@1 on tests, etc.).

These objectives conflict: the cheapest model (lowest cost) typically has lower quality; the strongest model (highest quality) has the highest cost. Every routing policy navigates this tradeoff.

### Plotting the Pareto frontier

A Pareto frontier plot places each routing policy as a point in (cost, accuracy) space:

```
accuracy
  ^
1.0|                         * ORACLE
   |                   * strong model (always)
0.9|             * good router
   |       * heuristic router
0.8|  * random routing
   |* cheap model (always)
   +-----------------------------------> cost per query
   cheap                          expensive
```

A policy **dominates** another if it achieves higher accuracy at equal or lower cost, OR lower cost at equal or higher accuracy. The convex hull of all non-dominated policies is the Pareto frontier.

**RouterBench** (Hu et al., ICML 2024 — arXiv [2403.12031](https://arxiv.org/abs/2403.12031)) formalizes this evaluation using convex-hull analysis and an AIQ (Aggregate Improvement over Quality) metric across 405k precomputed inference records over 11 LLMs spanning commonsense reasoning, QA, conversation, math, coding, and RAG. The AIQ metric combines cost and quality into a single scalar for leaderboard comparison.

---

## 2. The Four Canonical Baselines

Every router evaluation MUST include these four baselines. A router that does not improve on all of them is not useful.

### Baseline 1 — Always-Cheap

Route every query to the cheapest model in the pool.

- **Cost**: minimum possible.
- **Quality**: cheapest model's accuracy, which is the floor.
- **Role on Pareto plot**: lower-left anchor point.

### Baseline 2 — Always-Strong

Route every query to the strongest (most expensive) model in the pool.

- **Cost**: maximum possible.
- **Quality**: strongest model's accuracy, which is the ceiling for a single-model policy.
- **Role on Pareto plot**: upper-right anchor point.

### Baseline 3 — Random Routing

Route each query to a uniformly random model.

- **Cost**: average of all models' costs.
- **Quality**: average of all models' accuracies (approximately, if tasks are iid).
- **Role on Pareto plot**: sits on the chord between always-cheap and always-strong. A well-designed router must dominate this chord.

**Critical insight**: A trained router that merely matches random is worthless. The trained router must produce a curve that lies **above and to the left** of the random-routing chord.

### Baseline 4 — ORACLE Upper Bound

For each query, we know in hindsight which model gave the correct answer at the lowest cost. The oracle routes every query to the cheapest model that would have gotten it right.

- **Cost**: minimum possible subject to achieving the oracle quality level.
- **Quality**: the maximum achievable quality at any given cost, given the model pool.
- **Role on Pareto plot**: the theoretical upper-left boundary. No real-time router can reach this because it requires knowing the answer in advance.

**Why oracle matters**: The "oracle gap" — the vertical or horizontal distance between a router and the oracle — tells you how much routing headroom remains. A router very close to the oracle is near-optimal. A router far from the oracle has significant room to improve, or the task mix may be fundamentally hard to route.

**How to compute oracle**: For each test item, run every model in the pool, grade each answer, identify the cheapest correct model. Sum costs and aggregate accuracy. (This requires running all models on the test set, which is why it is only useful offline.)

---

## 3. What "A Good Router" Means

A good router satisfies three properties simultaneously:

1. **Dominates random**: On the Pareto plot, the router's operating point lies above the chord between always-cheap and always-strong. Both cost and quality are simultaneously better than random.

2. **Approaches the oracle**: The router's Pareto curve is close to the oracle Pareto curve. A good operational definition: within 10–20% of oracle quality at a given cost target.

3. **Is monotone under the threshold knob**: As the router's threshold for sending to the cheap model is relaxed (more queries go cheap), quality decreases smoothly and cost decreases monotonically. A router with non-monotone behavior under threshold sweep is miscalibrated.

### The threshold / bias-toward-cheap knob

Every trained router has at least one tunable parameter that shifts the operating point along the Pareto curve:

- **Classifier probability threshold**: The minimum probability of "cheap is sufficient" to route cheap. Lower threshold → more queries go to strong model → higher quality, higher cost.
- **Cascade scoring threshold**: The minimum score for the cheap model's answer to be accepted. Higher threshold → more escalations → higher quality, higher cost.
- **Self-consistency k**: More samples → higher quality, proportionally higher cost.

**For agent use**: Set the threshold as an application-level constant, not per-query. Make it configurable (environment variable or config file). Document what quality level corresponds to which threshold value, using the Pareto plot as the reference.

---

## 4. Why Coding Is Hard to Route

Coding tasks are the hardest discipline for model routing. The difficulty stems from several compounding factors:

### 4a — Binary pass/fail evaluation

Most routing research uses quality metrics that are continuous (LLM-judge score 1–5, ROUGE, normalized text match). Routing can tune the threshold to accept "pretty good" cheap answers. Code evaluation is binary: the tests pass or they do not. A nearly-correct function is worthless. This reduces the benefit of the cheap model's partial quality.

### 4b — Difficulty is hard to predict from the prompt

The difficulty of a coding task is determined by algorithmic complexity, edge cases, and hidden test cases — none of which are visible in the prompt text. A one-line prompt ("write a function to find the median of a list") can conceal a hard edge case. A long prompt describing a complex system can be easy to implement. This makes embedding-based routers weaker for coding than for QA.

### 4c — Cheap models have high variance on coding

Cheap models for coding often pass simple cases but fail on edge cases. The distribution of cheap-model correctness on coding tasks has a long tail of near-misses. This makes calibrating the routing threshold difficult: a threshold that works for 80% accuracy may silently fail on 10% of tasks in a way that is hard to detect without running the tests.

### 4d — Cascades add latency that compounds in loops

A coding agent harness typically runs in a loop: generate code → run tests → fix errors. If each step has a cascade that adds serial latency, a 3-step loop with 2× latency overhead per step compounds to 8× total latency. Latency constraints favor direct routing over cascades for coding agents.

### 4e — What works despite these challenges

- **Per-step harness routing** (Category E in `capability-map.md`) bypasses the classification problem by using step-type as the routing signal, which is known in advance and precisely discriminative.
- **Self-consistency on code** works when the code generation task has deterministic test grading: sample k cheap-model outputs, run all k through tests, return the first passing output. Cost = k × cheap call, quality = pass@k improvement.
- **Heuristic routing on code** can be effective if the harness exposes step metadata (e.g., "this is a planning step" vs "this is a diff application step").

---

## 5. The AIQ Metric

RouterBench introduces the **AIQ (Aggregate Improvement over Quality)** metric as a scalar summary of a router's Pareto performance. The exact formula requires consulting the full RouterBench paper (arXiv [2403.12031](https://arxiv.org/abs/2403.12031)). Conceptually, AIQ integrates the area between the router's Pareto curve and the always-cheap baseline, normalized by the area between the oracle curve and always-cheap.

- AIQ = 0: router is no better than always-cheap.
- AIQ = 1: router matches the oracle.

**For this degree's POCs**: We do not compute AIQ directly (it requires the full 405k-row RouterBench dataset). Instead, we use the simpler metric: at a target cost budget (e.g., 50% of always-strong cost), what accuracy does the router achieve vs the oracle and vs random? This gives a concrete, interpretable scalar.

---

## 6. Summary — The Mental Model in One Paragraph

LLM routing is the problem of allocating each query to the cheapest model that will answer it correctly. The design space is a two-dimensional cost-quality Pareto frontier. Every routing policy traces a curve on this frontier; the ORACLE — knowing the correct answer in advance — defines the upper bound, which no real-time router can reach. A good router dominates random routing (lies above the random-routing chord) and approaches the oracle gap. The primary design knob is the threshold for sending to the cheap model: tuning this knob sweeps the operating point along the router's Pareto curve. Coding is the hardest discipline to route because evaluation is binary and prompt difficulty is hard to predict; per-step harness routing (assigning models by step type, not query difficulty) partially sidesteps this by using information that is known before the query is generated.
