# Capability Map — LLM Routing Strategy Taxonomy

**Degree**: 01-llm-model-routing  
**Evidence label**: Research supported but not live verified  
**Date compiled**: 2026-06-21

This file is an exhaustive taxonomy of routing strategy families. For each entry: what it is, when to use it, cost/quality tradeoff, and the canonical citation. Use this as the authoritative reference when choosing a router design for a POC.

Cross-references: `mental-model.md` explains the Pareto framing. `common-use-cases.md` maps disciplines to strategies. `known-failure-modes.md` covers where each category breaks.

---

## Category A — Non-Predictive Routing

Non-predictive routers make routing decisions without examining query content. They require no training data, no embedding model, and no inference overhead.

### A1 — Random Routing

Route each query to a randomly selected model (uniform distribution over the pool).

**What it is**: Stochastic baseline. No signal used.

**When to use**: As a baseline ONLY. Never as a production strategy. Required in every benchmark run as the lower bound.

**Cost/quality tradeoff**: If the pool is {cheap, strong}, random routing achieves approximately the average of the two models' quality at roughly average cost. On a cost-quality plot it sits at the midpoint on the chord between cheap and strong — always dominated by any informed router.

**Key point for agents**: If your trained router cannot beat random on both axes simultaneously, it is adding noise, not signal.

### A2 — Round-Robin / Load Balancing

Cycle through the model pool in order, or distribute by request-rate or token-quota.

**What it is**: Operational distribution strategy, not quality-sensitive. LiteLLM Router's `simple-shuffle` and `least-busy` modes implement this. Its stated goal is throughput and availability, not quality.

**When to use**: When you have multiple deployments of the same model (e.g., multiple gpt-4o-mini replicas) and want to avoid hot-spotting. Correct for availability-focused load balancing; wrong when the pool contains models of different quality.

**Cost/quality tradeoff**: Identical to random when pool models have equal quality; degrades to random-quality when pool models differ.

**Citation**: LiteLLM Router routing strategies documentation — [docs.litellm.ai/docs/routing](https://docs.litellm.ai/docs/routing).

### A3 — Rule / Heuristic Routing

Deterministic rules that inspect observable features of the query without prediction: query length, keyword presence, topic prefix, structured vs. free-form, tool-call presence.

**What it is**: A decision tree or if/else logic over hand-crafted features.

**Examples**:
- "Route to strong model if prompt > 2000 tokens."
- "Route to strong model if prompt contains 'debug' or 'refactor'."
- "Route code generation tasks to coding-specialized model."
- "Route math questions (contain numbers + operators) to reasoning-optimized model."

**When to use**:
- Zero training data available.
- Explainability is required (compliance, auditability).
- The task space has sharp, predictable structure (e.g., API where one field determines complexity).

**Cost/quality tradeoff**: Better than random if the rules have genuine discriminative power; degrades gracefully as the rule set becomes stale or the query distribution drifts. Typically lies between random and a trained classifier on the Pareto frontier.

**Key gotcha**: Rule quality is entirely determined by the engineer's prior knowledge of the query distribution. For a heterogeneous agent harness this is usually low.

---

## Category B — Predictive Routing

Predictive routers model query-level difficulty or model-query fit, then classify each query to the appropriate model. They require training data (labels) or at minimum an embedding model.

### B1 — Embedding k-NN (Similarity-Weighted Routing)

Embed the incoming query with a small embedding model (e.g., `text-embedding-3-small`). Find the k nearest labeled examples from a routing training set. Aggregate their labels (majority vote, or weighted by similarity score) to decide the model assignment.

**What it is**: A non-parametric classifier operating in embedding space. RouteLLM calls this the "SW-ranking router" (similarity-weighted Elo calculation).

**When to use**:
- Moderate training data available (hundreds to low thousands of labeled examples).
- Embedding model is cheap and fast (OpenAI `text-embedding-3-small` is ~$0.02/million tokens as of 2026).
- No GPU available for fine-tuning.

**Cost/quality tradeoff**: The routing overhead is one embedding call per query (~1ms + cost). Quality is bounded by how representative the training set is. Works well when the training queries cluster cleanly in embedding space by difficulty.

**Training data requirement**: For each training example, you need a label "which model was better/sufficient." Generate this by running both the cheap and strong model on the example and using an LLM judge or ground-truth comparison.

**Citation**: RouteLLM (Ong et al., 2024) — arXiv [2406.18665](https://arxiv.org/abs/2406.18665). RouteLLM's SW-ranking router uses preference data from Chatbot Arena and augmentation from an LLM judge.

### B2 — Trained Classifier (Logistic Regression / MLP on Embeddings)

Embed the query and train a supervised classifier (logistic regression, small MLP) to predict "cheap model is sufficient" vs "strong model required." At inference: embed query → classifier → model assignment.

**What it is**: A parametric classifier trained on (embedding, label) pairs. Lightweight enough to run on CPU in milliseconds. Equivalent to RouteLLM's BERT-based router but here implemented as a linear head on top of frozen embeddings.

**When to use**:
- Hundreds or more labeled examples available.
- Want a probability score (not just hard assignment) so a decision threshold can be swept.
- Want to trace a Pareto curve by varying the threshold.

**Cost/quality tradeoff**: Adds only classifier inference overhead (microseconds for logistic regression). Quality is typically better than kNN because the parametric boundary can generalize across the embedding manifold.

**Threshold as cost/quality knob**: Increasing the threshold for "cheap is sufficient" routes more queries to the cheap model (lower cost, lower quality). Sweeping the threshold traces the Pareto curve between always-cheap and always-strong.

**Citation**: RouteLLM (Ong et al., 2024) — arXiv [2406.18665](https://arxiv.org/abs/2406.18665). The paper's matrix factorization and BERT routers are trained classifiers in this sense. Hybrid LLM (Ding et al., ICLR 2024) — arXiv [2404.14618](https://arxiv.org/abs/2404.14618) also trains a router to predict query difficulty.

### B3 — RouteLLM Matrix Factorization Router

Train a matrix factorization model that learns a joint embedding of (query, model), producing a scalar score for "how well this model handles this query." Route to the model with the highest score above a threshold.

**What it is**: A latent-factor model generalizing collaborative filtering to the LLM routing problem. Learns from human preference data (Chatbot Arena win/loss records).

**Key result from the paper (paper's claim, not our measurement)**: With Arena data + LLM judge augmentation, the MF router achieves 95% of GPT-4 quality using only 14% GPT-4 calls on MT-Bench — representing over 85% cost reduction compared to the random baseline on MT-Bench, 45% on MMLU, and 35% on GSM8K. The augmented dataset used was approximately 1500 samples, under 2% of the total training data.

**Citation**: RouteLLM (Ong et al., 2024) — arXiv [2406.18665](https://arxiv.org/abs/2406.18665); LMSYS blog post [lmsys.org/blog/2024-07-01-routellm](https://www.lmsys.org/blog/2024-07-01-routellm/).

### B4 — RouteLLM Causal-LLM Classifier

Use a small causal language model to classify query difficulty. The LLM itself becomes the router, trained on (query, label) pairs.

**What it is**: Fine-tuned small LLM predicting "cheap sufficient" or "strong required." Heavier than a linear classifier but can leverage the LLM's language understanding for complex queries.

**Key result from the paper (paper's claim)**: With golden-label augmentation, the causal-LLM router achieves 95% GPT-4 quality using 54% GPT-4 calls on MMLU (14% savings vs. random baseline).

**When to use**: When the routing decision requires understanding implicit complexity signals in the text (e.g., multi-step reasoning hints, ambiguous phrasing). When inference latency is not critical.

**Cost/quality tradeoff**: Adds a full LLM inference call for routing (latency + cost), but this is amortized if the routed call cost is high.

**Citation**: RouteLLM (Ong et al., 2024) — arXiv [2406.18665](https://arxiv.org/abs/2406.18665).

### B5 — Hybrid LLM Quality-Gap Routing

Train a router that explicitly models the "quality gap" between a cheap and a strong model for a given query. Route to the strong model only when the predicted gap exceeds a configurable quality threshold.

**What it is**: Proposed by Ding et al. (ICLR 2024). The router predicts not just "cheap or strong" but the magnitude of quality difference, making the threshold semantically meaningful.

**Key result from the paper (paper's claim, not our measurement)**: Up to 40% fewer calls to the large model with no drop in response quality compared to always using the large model.

**Cost/quality tradeoff**: The quality threshold is a single interpretable knob: raising it allows more queries to go to the cheap model (cheaper but riskier); lowering it preserves quality.

**Citation**: Hybrid LLM (Ding et al., ICLR 2024) — arXiv [2404.14618](https://arxiv.org/abs/2404.14618); ICLR proceedings [proceedings.iclr.cc/paper_files/paper/2024/file/b47d93c99fa22ac0b377578af0a1f63a-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2024/file/b47d93c99fa22ac0b377578af0a1f63a-Paper-Conference.pdf).

---

## Category C — Cascades

A cascade makes an initial attempt with the cheap model, then decides whether to escalate to a stronger model based on a scoring or verification signal. The key distinction from a router: the cascade *generates* before deciding whether to use the result.

### C1 — FrugalGPT Learned Cascade

A learned cascade that determines the optimal sequence of LLM calls per query. Given a set of LLMs with different costs, FrugalGPT learns which model (or sequence of models) to call for each query, stopping as soon as the scoring function judges the answer good enough.

**What it is**: A cascade where the call sequence and stopping criterion are learned from data. Each step's LLM response is scored; if the score exceeds a threshold, the cascade stops and returns that answer. Otherwise it escalates to the next (typically larger, more expensive) LLM.

**Architecture**: cheap model → score → (if sufficient, return) → mid model → score → (if sufficient, return) → strong model (always return).

**Key results from the paper (paper's claim, not our measurement)**: FrugalGPT can match GPT-4 performance with up to 98% cost reduction, or improve accuracy over GPT-4 by 4% at the same cost.

**When to use**:
- When you have labeled data to train the scoring function.
- When moderate-quality answers are acceptable for a substantial fraction of queries.
- Batch workloads where latency is not critical (cascade adds serial latency for escalated queries).

**Cost/quality tradeoff**: The cascade can cost MORE than always-strong if many queries escalate and run all levels. The scoring quality is critical: a poor scorer that passes bad answers degrades quality; one that over-escalates eliminates savings.

**Citation**: FrugalGPT (Chen, Zaharia, Zou, 2023) — arXiv [2305.05176](https://arxiv.org/abs/2305.05176).

### C2 — AutoMix Self-Verification Cascade

The cheap model generates an answer AND self-verifies its own output. A POMDP-based meta-verifier assesses the reliability of the self-verification signal. Only if the meta-verifier indicates low confidence does the query escalate to a stronger model.

**What it is**: Two-level cascade where the escalation decision is driven by the cheap model's own uncertainty estimate, corrected by a POMDP model that accounts for the known unreliability of self-verification.

**Architecture**:
1. Small LM generates answer to query in context.
2. Small LM self-verifies: produces a noisy confidence score.
3. POMDP meta-verifier: estimates the probability the answer is correct given the noisy self-verification signal.
4. If estimated probability > threshold: return answer from small LM.
5. Else: escalate to large LM.

**Key result from the paper (paper's claim, not our measurement)**: AutoMix reduces computational cost by over 50% for comparable performance, evaluated across five challenging datasets (CNLI, CoQA, NarrativeQA, QASPER, Quality).

**Why POMDP**: Self-verification is known to be miscalibrated — LLMs tend to affirm their own answers regardless of correctness. The POMDP step corrects for this systematic bias, giving a better escalation signal than raw self-reported confidence.

**When to use**:
- When no external judge is available and you cannot run the strong model just to score cheap-model answers.
- When the cheap model produces responses with natural confidence signals (extractive QA, structured output, factual recall).
- Less suitable for open-ended generation where self-verification is especially unreliable.

**Citation**: AutoMix (Madaan et al., NeurIPS 2024) — arXiv [2310.12963](https://arxiv.org/abs/2310.12963); GitHub [github.com/automix-llm/automix](https://github.com/automix-llm/automix).

---

## Category D — Ensembles (Cheap Models Combined)

Ensembles generate multiple outputs and aggregate them. Unlike cascades, ensembles typically do NOT escalate to a strong model; they combine cheap-model outputs to approach (or exceed) strong-model quality.

### D1 — Mixture-of-Agents (Layered Ensemble)

N cheap models each generate a response in a "proposer" layer. An aggregator model (or another layer of models) synthesizes all N proposals into a final answer.

**What it is**: Collaborative multi-model generation in layers. Each agent in each layer receives the outputs of all agents in the previous layer as additional context when generating its response.

**Architecture**:
```
Layer 1:  [model_A, model_B, model_C]  → 3 proposals
Layer 2:  [model_D, model_E]           → 2 refinements (seeing all 3 proposals)
Aggregator: [model_F]                  → final answer (seeing all 5)
```

**Key result from the paper (paper's claim, not our measurement)**: Using only open-source LLMs, MoA achieved 65.1% LC win rate on AlpacaEval 2.0 compared to 57.5% for GPT-4 Omni (a 7.6 percentage point improvement). MoA-Lite (2 layers, Qwen1.5-72B-Chat aggregator) achieves 1.8% improvement on AlpacaEval 2.0 with cost-effective open models.

**When to use**:
- When quality is the primary objective and you have multiple cheap models available.
- Creative generation, instruction following, qualitative tasks where aggregation adds value.
- When single-model variance is high and aggregation reduces it.

**Cost/quality tradeoff**: Cost = N × (cheap model cost) + (aggregator cost). If cheap models are very cheap and N is small (3–5), total cost can still be less than a single strong model call while exceeding its quality. The key finding from the MoA paper is that improvement persists even when some proposers produce lower-quality outputs than the aggregator would alone.

**Citation**: Mixture-of-Agents (Wang, Wang, Athiwaratkun, Zhang, Zou, 2024) — arXiv [2406.04692](https://arxiv.org/abs/2406.04692); GitHub [github.com/togethercomputer/MoA](https://github.com/togethercomputer/MoA).

### D2 — Self-Consistency / Sample-and-Vote

Sample the same cheap model k times at temperature > 0. Aggregate the k answers by majority vote (for closed-answer tasks) or by consistency (for free-form tasks).

**What it is**: A decoding-time ensemble over a single model's stochastic output space. Replaces greedy decoding with voting over a diverse sample.

**Key result from the paper (paper's claim, not our measurement)**: Self-Consistency with PaLM-540B improves GSM8K from 56.5% to 74.4% — a +17.9% improvement. The method also improves SVAMP (+11.0%), AQuA (+12.2%), StrategyQA (+6.4%), and ARC-challenge (+3.9%).

**Scaling behavior**: "More Agents Is All You Need" (Li et al., 2024) — arXiv [2402.05120](https://arxiv.org/abs/2402.05120) — shows that with k=15 samples, Llama2-13B reaches accuracy comparable to Llama2-70B on GSM8K. The gain correlates with task difficulty: easy tasks show diminishing returns; hard tasks show strong scaling.

**When to use**:
- Math, reasoning, or multi-step tasks with deterministic correct answers (verifiable by exact match).
- When the cheap model has good average probability of producing the right answer but high per-sample variance.
- When latency allows k parallel calls (run in parallel, not serial).

**Cost/quality tradeoff**: Cost = k × (cheap model cost per call). Quality gain is logarithmic in k — the first few samples provide most of the benefit. Typically k=5–20 gives most of the gain. Running k cheap models can cost less than one call to a strong model if the cheap model is significantly cheaper per token.

**Citation**: Self-Consistency (Wang et al., 2022) — arXiv [2203.11171](https://arxiv.org/abs/2203.11171). More Agents Is All You Need (Li et al., 2024) — arXiv [2402.05120](https://arxiv.org/abs/2402.05120).

### D3 — Multi-Agent Debate

Multiple LLM agents independently generate answers, then read each other's responses and revise over multiple rounds. A final aggregator or majority vote decides the answer.

**What it is**: Iterative social reasoning. Agents are exposed to dissenting answers and must justify or update their positions. Convergence to a correct answer is driven by the quality of reasoning presented, not just by popularity.

**Key result from the paper (paper's claim, not our measurement)**: Multi-agent debate significantly enhances mathematical and strategic reasoning and improves factual validity of generated content, reducing hallucinations, across tasks evaluated with 2–3 agent instances.

**When to use**:
- Factual accuracy tasks where hallucination is a primary concern.
- Tasks where agents benefit from seeing dissenting evidence (e.g., conflicting facts in a document).
- Fewer useful for simple closed-answer tasks where voting suffices.

**Cost/quality tradeoff**: Cost = N agents × R rounds × (cost per call). Substantially more expensive than self-consistency for the same number of models because each round requires reading previous rounds' outputs (growing context). Typically use N=2–3 and R=2–3.

**Citation**: Multi-agent debate (Du, Li, Torralba, Tenenbaum, Mordatch, 2023) — arXiv [2305.14325](https://arxiv.org/abs/2305.14325).

### D4 — LLM-Blender: PairRanker + GenFuser

Generate k candidate outputs from k different models (or k samples from one model). Use PairRanker to rank all candidate pairs by pairwise comparison. Then use GenFuser to fuse the top-ranked candidates into a single output that capitalizes on their collective strengths.

**What it is**: A two-stage ensemble that first ranks candidates by pairwise quality comparison, then generatively fuses the best ones. The ranking step uses a cross-attention encoder to jointly encode (input, candidate_A, candidate_B) and output which is better.

**Key result from the paper (paper's claim, not our measurement)**: LLM-Blender significantly surpasses the best individual LLMs and baseline ensembling methods across multiple metrics on MixInstruct. PairRanker exhibits the highest correlation with ChatGPT-based ranking among the ranker variants tested.

**When to use**:
- Heterogeneous model pool where different models excel at different aspects of a task.
- Instruction following, open-ended generation tasks (the MixInstruct benchmark covers these).
- When you can afford k inference calls + 1 ranker call + 1 fuser call per query.

**Cost/quality tradeoff**: High — k model calls + ranking overhead + fusion call. Best justified when quality is paramount and the query distribution is known to be heterogeneous in difficulty.

**Citation**: LLM-Blender (Jiang, Ren, Mundra, et al., ACL 2023) — arXiv [2306.02561](https://arxiv.org/abs/2306.02561); ACL Anthology [aclanthology.org/2023.acl-long.792](https://aclanthology.org/2023.acl-long.792/).

---

## Category E — Harness Routing (Per-Step / Per-Mode)

In an agent harness (coding agent, research agent), routing is not a single decision per query — it is a series of decisions, one per agent step or mode. The harness itself becomes the routing layer.

### E1 — Per-Step Model Selection

Different steps in the agent loop are assigned different models based on the expected difficulty or cost of each step.

**What it is**: A static or dynamic policy that maps step_type → model_id. Example:
- `plan` step → strong model (requires reasoning about the full codebase)
- `edit` step → medium model (code generation with good context)
- `fix` step → cheap model (small diffs, easy verification)
- `verify` step → cheap model (yes/no judgment)

**Implemented in practice**: opencode's model configuration exposes per-agent-mode model selection. Claude Code and Aider allow separate model flags for different operations. The pattern is documented in opencode's GitHub discussion [github.com/anomalyco/opencode/issues/8456](https://github.com/anomalyco/opencode/issues/8456) and described in production guides such as [glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/](https://www.glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/).

**When to use**:
- Coding agents, research agents, any multi-step harness with distinct step types.
- When the cost difference between step types is significant and easy to categorize.

**Cost/quality tradeoff**: High potential savings with minimal quality loss if the step taxonomy is correct. The expensive steps (planning, reasoning) are few; the cheap steps (formatting, diffing) are many. Routing the cheap steps to cheap models can reduce total harness cost by 40–70% (this is an engineering observation; specific numbers vary by harness and model pool).

### E2 — Dynamic Difficulty Escalation in Harness

Combine the heuristic/classifier router with the harness: for each step, estimate the difficulty dynamically (e.g., based on context size, error count, step retry count) and route accordingly.

**What it is**: A feedback-aware harness router. If a step fails or produces low-confidence output, escalate to a stronger model for the retry.

**When to use**:
- When step difficulty is not predictable in advance (e.g., an `edit` step targeting a complex dependency graph may require a strong model; an `edit` targeting a simple function does not).
- Coding agent fix loops where the number of retries signals difficulty.

**Cost/quality tradeoff**: More complex to implement than static per-step routing. Adds one routing decision per retry. Best suited for harnesses with high variance in step difficulty.

---

## Strategy Selection Quick-Reference

| Strategy | Training data needed | Routing overhead | Best for | Key risk |
|---|---|---|---|---|
| Random | None | None | Baseline only | Never use in production |
| Round-robin | None | None | Load balancing within same model | Degrades when pool is heterogeneous |
| Heuristic rules | None | Negligible | Zero-data, structured APIs | Stale rules, incomplete coverage |
| Embedding kNN | Hundreds of labeled pairs | 1 embedding call | Moderate data, no fine-tuning | Degrades on out-of-distribution queries |
| Classifier (LR/MLP) | Hundreds–thousands | Microseconds | Traced Pareto curves | Requires labeled data; distribution shift |
| MF/BERT classifier | Thousands (preference data) | Milliseconds | Best trained single-router quality | Complex training pipeline |
| FrugalGPT cascade | Training data for scorer | Serial latency on escalation | Batch QA, high-variance tasks | Cascade cost explosion if scorer is bad |
| AutoMix cascade | None (few-shot) | Serial latency + self-verify | No external judge available | Self-verification miscalibration |
| MoA ensemble | None | N × cheap call cost | Quality maximization, instruction following | Cost scales linearly with N |
| Self-consistency | None | k × cheap call cost | Math/reasoning closed-answer | Fails on open-ended tasks |
| Multi-agent debate | None | N × R × call cost | Factuality, hallucination reduction | Very expensive; slow |
| LLM-Blender | None | k + rank + fuse calls | Heterogeneous pool, quality-first | Most expensive option |
| Per-step harness | None (taxonomy) | Negligible | Coding agents, multi-step harnesses | Requires step taxonomy design |
