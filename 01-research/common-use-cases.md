# Common Use Cases — Model Routing by Discipline

**Degree**: 01-llm-model-routing  
**Evidence label**: Research supported but not live verified  
**Date compiled**: 2026-06-21

This file maps concrete routing scenarios to recommended strategies, with rationale. Each entry gives: the use-case, which strategy fits, why it fits, and the critical tradeoffs. Quantitative claims cite sources; engineering guidance is labeled as inferred from docs or research.

Cross-references: `capability-map.md` for strategy details. `mental-model.md` for the Pareto framing. `known-failure-modes.md` for where each approach breaks.

---

## 1. Coding Agents

### UC-1: Multi-Step Coding Agent (plan → edit → fix loop)

**Situation**: An autonomous coding agent runs a loop: plan a change, write/edit code, run tests, fix failures. Each step has different cognitive demands and cost implications.

**Recommended strategy**: Per-step harness routing (Category E1 in `capability-map.md`).

**Rationale**: Step type is known in advance (the harness explicitly enters a "plan" or "edit" or "fix" mode), making routing zero-cost. Planning and architecture reasoning require strong-model quality; diff application and formatting do not. This sidesteps the fundamental hard problem of coding routing (predicting difficulty from the prompt) by using metadata the harness already has.

**Configuration pattern (inferred from docs)**:
```
plan step     → strong model   (reasoning about codebase structure)
edit step     → medium model   (code generation with context)
fix step      → medium model   (targeted diff, small change)
format/lint   → cheap model    (deterministic, context-independent)
test grading  → deterministic  (subprocess, not an LLM call)
```

**Evidence from production**: opencode's model configuration exposes per-mode model selection (planning model vs. execution model). Claude Code and Aider expose separate `--model` and `--weak-model` flags, where the weak model handles background/sub-agent tasks. See: opencode discussion [github.com/anomalyco/opencode/issues/8456](https://github.com/anomalyco/opencode/issues/8456); opencode agent guide [glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/](https://www.glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/).

**Key tradeoff**: Requires the harness to expose step type as a routing signal. If the harness is a black-box tool-calling loop where all steps look the same to the router, this strategy is not applicable.

---

### UC-2: Code Generation Task (single-turn, HumanEval-style)

**Situation**: Given a function signature and docstring, generate a correct implementation. Graded by running unit tests (pass/fail). No multi-turn loop.

**Recommended strategy**: Self-consistency / sample-and-vote with cheap model, with fallback to strong model on repeated failure.

**Rationale**: Code generation has binary pass/fail grading. Running k cheap-model samples and returning the first passing one implements "pass@k" at cheap-model cost. For HumanEval-style tasks, pass@k improves substantially with k (research observation; specific numbers depend on model and task). If k samples all fail, escalate to strong model.

**Implementation pattern (inferred from research)**:
```python
for i in range(k):
    code = cheap_model.generate(prompt, temperature=0.8)
    if run_tests(code):
        return code, cost=i*cheap_cost
return strong_model.generate(prompt), cost=k*cheap_cost + strong_cost
```

**Key tradeoff**: Parallelizing k cheap calls eliminates the serial latency cost. Total cost = k × cheap + occasional strong. If cheap model's pass@1 is very low (e.g., < 20%), the expected cost per successful generation may exceed always-strong.

---

### UC-3: Code Review / Critique (Is This Code Correct?)

**Situation**: An agent needs to verify whether a code change is correct. Not generating code — judging it.

**Recommended strategy**: Heuristic routing + cheap model for simple checks; strong model only for architectural review.

**Rationale**: Simple code review (syntax, obvious bugs, naming conventions) does not require a strong model. Architectural review (subtle race conditions, security vulnerabilities, algorithmic correctness) does. The heuristic: route to strong if the diff size exceeds a threshold or the change touches security-sensitive modules (inferred from docs).

**Key tradeoff**: Under-investment in review is expensive later (bugs reach production). When in doubt, prefer strong model for review tasks.

---

## 2. QA / Chat

### UC-4: Factual Closed-Answer QA (Knowledge Retrieval)

**Situation**: A user asks factual questions with short, verifiable answers (capitals, dates, definitions). Graded by normalized exact match.

**Recommended strategy**: Heuristic routing (route to cheap model by default; escalate on long/multi-hop questions) or embedding kNN if labeled data is available.

**Rationale**: Most factual questions can be answered by a small, well-trained model. The strong model is only needed for obscure facts or multi-hop reasoning. Query length and presence of negations/conditionals are reasonable heuristic signals.

**Data requirement for kNN**: Need a labeled set of (question, "cheap sufficient" / "strong required") pairs. Generate this by running both models on a representative sample and comparing to ground truth. A few hundred examples is typically sufficient for a kNN router on factual QA (inferred from RouteLLM results; not our measurement).

**FrugalGPT applicability**: FrugalGPT (Chen et al., 2023 — arXiv [2305.05176](https://arxiv.org/abs/2305.05176)) is well-suited to QA tasks because the cascade scoring function (checking if the cheap model's answer matches a ground-truth pattern) is cheap and reliable for closed-answer tasks.

---

### UC-5: Multi-Turn Conversational QA (Customer Support / Chatbot)

**Situation**: A multi-turn assistant that must maintain context and answer a range of questions from easy (greeting, FAQ) to hard (complex troubleshooting, ambiguous requests).

**Recommended strategy**: Classifier router (B2 in `capability-map.md`) with conversation state features; or per-turn heuristic based on turn complexity.

**Rationale**: Each turn is an independent routing decision. Turn complexity correlates with: message length, presence of complex conditionals, number of entities referenced, and whether previous turns contain unresolved ambiguity. A lightweight classifier on these features can capture much of the signal.

**Special consideration — context consistency**: Routing different turns to different models risks inconsistency in persona, style, and memory of the conversation. Mitigation: always use the strong model for turns that reference specific facts from earlier in the conversation (inferred from docs; not empirically tested here).

**Key tradeoff**: Routing the "easy" turns cheaply only saves money if easy turns are frequent. For a support bot where most queries are complex, the routing overhead may not pay off.

---

### UC-6: RAG (Retrieval-Augmented Generation) QA

**Situation**: The agent retrieves context chunks and must answer a question using retrieved evidence. Graded by faithfulness to retrieved context.

**Recommended strategy**: AutoMix cascade (C2 in `capability-map.md`) — cheap model generates and self-verifies against retrieved context; escalate if low confidence.

**Rationale**: Self-verification is most reliable when there is an objective grounding context (the retrieved passages). The cheap model can check whether its answer is supported by the retrieved text — a simpler judgment than open-ended self-verification. AutoMix's POMDP corrects for miscalibration.

**Key result from AutoMix (paper's claim, not our measurement)**: AutoMix tested on NarrativeQA, QASPER, and Quality datasets (all context-grounded QA), reducing computational cost by over 50% for comparable performance (Madaan et al., NeurIPS 2024 — arXiv [2310.12963](https://arxiv.org/abs/2310.12963)).

**Key tradeoff**: Self-verification is unreliable for tasks where the context is ambiguous or where the correct answer requires inference beyond what is in the retrieved text. In these cases, the cascade tends to over-escalate, reducing savings.

---

## 3. Math and Reasoning

### UC-7: Closed-Form Math (Arithmetic, Algebra, Word Problems)

**Situation**: The agent must solve math problems with a deterministic numeric answer. Graded by exact numeric match.

**Recommended strategy**: Self-consistency (D2) — sample cheap model k times, majority-vote the numeric answer.

**Rationale**: Math has a single correct numeric answer. The cheap model often knows the right approach but makes arithmetic errors in any single pass. Sampling k times and voting corrects for errors. "More Agents Is All You Need" (Li et al., 2024) shows that cheap models with k=15 samples can match strong models on GSM8K (paper's claim — arXiv [2402.05120](https://arxiv.org/abs/2402.05120)).

**Implementation**: Use temperature > 0 (e.g., 0.7–0.8) to diversify samples. Normalize numeric answers before voting (strip units, convert to float). If consensus is strong (e.g., 12/15 agree), high confidence; if consensus is weak (e.g., 5/15 agree), escalate to strong model.

**Cost structure**: k=5 cheap calls ≈ 1 strong call cost at a 5:1 price ratio. k=10 cheap calls ≈ 2 strong calls. The break-even point depends on the model price ratio and the difficulty of the task.

---

### UC-8: Multi-Step Reasoning (Chain-of-Thought Required)

**Situation**: The task requires multiple reasoning steps, each dependent on the previous (e.g., GSM8K competition math, StrategyQA, complex word problems).

**Recommended strategy**: Self-consistency (D2) as primary approach; strong model as fallback on weak consensus.

**Key result (paper's claim)**: Self-Consistency (Wang et al., 2022 — arXiv [2203.11171](https://arxiv.org/abs/2203.11171)) with PaLM-540B improves GSM8K from 56.5% to 74.4% (+17.9%), SVAMP (+11.0%), and AQuA (+12.2%).

**When strong model is necessary**: If the problem requires knowledge or reasoning that the cheap model demonstrably lacks (e.g., competition-level math that cheap models have near-zero pass@1 on), the cascade approach with a cheap initial attempt + strong fallback is better than repeated cheap sampling.

**Routing signal for heuristic approach**: Complexity indicators in the prompt: number of named quantities, number of "if/then" conditions, multi-sentence setup with dependencies. A heuristic that routes to strong on prompts with > 3 dependent quantities is a reasonable starting point (inferred; not measured here).

---

### UC-9: Factual Accuracy / Hallucination Reduction

**Situation**: The agent must generate accurate factual claims and minimize hallucinations. Graded by factual validity (LLM-judge or ground-truth comparison).

**Recommended strategy**: Multi-agent debate (D3) or Mixture-of-Agents (D1) for maximum accuracy; strong model single-call as the high-quality single-model baseline.

**Rationale**: Multi-agent debate (Du et al., 2023 — arXiv [2305.14325](https://arxiv.org/abs/2305.14325)) significantly reduces hallucinations by exposing agents to contradictory evidence and forcing revision. MoA (Wang et al., 2024) shows that aggregating multiple models' outputs consistently outperforms single-model generation for qualitative tasks.

**Cost warning**: Both MoA and debate are expensive. Use only when the cost of hallucination (downstream harm, re-work) exceeds the cost of additional inference.

---

## 4. Batch Pipelines

### UC-10: High-Volume Classification / Extraction Pipeline

**Situation**: A pipeline must classify or extract structured fields from thousands of documents. No interactive latency requirement. Graded by F1 or exact match.

**Recommended strategy**: Heuristic routing → classifier router → FrugalGPT cascade, in order of data availability.

**Rationale**: Batch pipelines are ideal for cascade strategies because serial latency (escalating to a strong model) is acceptable when processing in parallel. FrugalGPT (Chen et al., 2023) is the canonical approach: train a cascade scoring function on a labeled sample of the document distribution, then apply at scale.

**Data flywheel**: Start with heuristic routing on the first batch. Use strong-model outputs as training labels for a classifier or cascade scorer. After N labeled examples, deploy the trained router. This is the "cold start" → "trained router" lifecycle.

**Cost structure (illustrative, not measured here)**: If 70% of documents are "easy" (cheap model is correct) and 30% are "hard" (strong model required), and cheap model costs 1/20 of strong model per token, the routing overhead per document is one embedding + one scoring call. At scale, the savings are proportional to the "easy" fraction.

---

### UC-11: Parallel Research / Synthesis Pipeline

**Situation**: An agent must research multiple sub-questions in parallel, then synthesize findings. Different sub-questions have different difficulty.

**Recommended strategy**: Per-task difficulty estimation → route each sub-task independently.

**Rationale**: Sub-question routing is independent because sub-tasks are processed in parallel. Use an embedding kNN router (B1) trained on (sub-question type, model assignment) pairs to route each sub-question. Simple factual sub-questions go cheap; synthesis / reasoning sub-questions go strong. The synthesis step always uses the strong model.

**Inferred from research**: This pattern is analogous to RouteLLM's trained router (arXiv [2406.18665](https://arxiv.org/abs/2406.18665)) applied at the sub-task level rather than the query level.

---

### UC-12: Cost-Capped Inference (Hard Budget Per Request)

**Situation**: Each API request has a hard dollar budget (e.g., "do not spend more than $0.01 on this query"). The router must pick the best model that fits within budget.

**Recommended strategy**: Heuristic + price-aware routing. Map each model to its expected cost per query, filter to models within budget, select the highest-quality model from the affordable set.

**Implementation**:
```python
affordable_models = [m for m in pool if expected_cost(m, query) <= budget]
if not affordable_models:
    raise BudgetError
return max(affordable_models, key=lambda m: quality_score(m))
```

**Expected cost estimation**: Rough token count estimate from prompt length + typical completion length for the task type. Compute using `pricing.py` from the harness.

**Gateway implementation**: LiteLLM Router's `provider.max_price` parameter (when used via OpenRouter) implements a hard cost ceiling per request — [docs.litellm.ai/docs/routing](https://docs.litellm.ai/docs/routing). Inferred from docs; not live-tested here.

---

## 5. Strategy Selection Matrix

| Use-case | Zero training data | Some labels | Many labels | Notes |
|---|---|---|---|---|
| Multi-step coding agent | Per-step harness routing | Per-step + dynamic escalation | Classifier per step | Step type is the strongest signal |
| Single-turn code generation | Self-consistency (pass@k) | kNN router | Classifier router | Binary pass/fail favors sampling |
| Factual closed QA | Heuristic (length/complexity) | kNN router | FrugalGPT cascade | Cascade works well with reliable grader |
| Multi-turn chat | Heuristic per-turn | Classifier | Classifier | Consistency risk across turns |
| RAG QA | AutoMix cascade | AutoMix + trained POMDP | FrugalGPT cascade | AutoMix works with context-grounded tasks |
| Math/reasoning | Self-consistency (vote) | Self-consistency | Self-consistency + classifier | Voting beats single strong call at scale |
| Factuality / hallucination | MoA or debate | MoA | MoA + classifier pre-filter | High cost; use only when quality is critical |
| Batch extraction | Heuristic | FrugalGPT cascade | Trained classifier | Data flywheel: start heuristic, then train |
| Cost-capped inference | Price-aware selection | Price-aware selection | Price-aware + quality model | Hard budget constraint overrides all |
