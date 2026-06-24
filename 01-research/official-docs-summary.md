# Official Docs Summary — Foundational Papers and OSS for Model Routing

**Target**: Model Routing  
**Degree**: 01-llm-model-routing  
**Gathered**: 2026-06-21 (WebFetch of arXiv abstracts + LMSYS blog + GitHub READMEs; citations are to real sources fetched during research)  
**Status**: Research supported but not live verified. Numbers are the papers' own claims — not our measurements.

---

## Overview

Model routing is the discipline of selecting the best LLM for each query at inference time, balancing cost and quality. This file summarizes the primary academic papers and OSS frameworks that define the state of the art. POC workers should consult this file for mechanism intuition before implementing; see `integrations.md` for framework-level config snippets.

---

## 1. RouteLLM: Learning to Route LLMs with Preference Data

**Authors:** Isaac Ong, Amjad Almahairi, Vincent Wu, Wei-Lin Chiang, Tianhao Wu, Joseph E. Gonzalez, M Waleed Kadous, Ion Stoica  
**Year:** 2024 (submitted June 26, 2024)  
**ArXiv:** https://arxiv.org/abs/2406.18665  
**Code / Blog:** https://github.com/lm-sys/RouteLLM — https://www.lmsys.org/blog/2024-07-01-routellm/

### Mechanism

RouteLLM trains router models on human preference data (80k battles from the Chatbot Arena platform, where users compare two anonymous model responses). The router learns to predict, for a given query, whether the weak model is "good enough" — and routes to the strong model only when needed. Training uses data augmentation. Four router architectures are provided:

- **mf** (matrix factorization) — recommended; learns a per-prompt/model scoring function
- **sw_ranking** (similarity-weighted Elo) — weighted Elo calculation based on query similarity to training battles
- **bert** — BERT classifier predicting the superior model
- **causal_llm** — causal LLM classifier

The threshold is a single scalar that controls the cost/quality tradeoff continuously. Integration is via a drop-in OpenAI client override: the `model` field encodes `router-{type}-{threshold}` (e.g., `router-mf-0.11593`).

### Headline Claims (the paper's claims, not our measurement)

The LMSYS blog reports, at 95% of GPT-4 quality on the respective benchmark:

- **MT Bench**: cost reduction of over 85% (14% of queries routed to GPT-4 with augmented training data)
- **MMLU**: cost reduction of ~45% (54% of queries to GPT-4)
- **GSM8K**: cost reduction of ~35%

The paper also reports routers transfer across strong/weak model swaps at test time.

### Notes for POC Implementation

RouteLLM's OSS framework is the direct template for the L2-embedding-knn-router and L2b-classifier-router POCs in this degree. The "preference labeling by running both models + judging" step maps directly to our harness approach. We reproduce the concept live with our own task suite and providers; the above numbers are not re-verified here.

---

## 2. FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance

**Authors:** Lingjiao Chen, Matei Zaharia, James Zou  
**Year:** 2023 (submitted May 9, 2023)  
**ArXiv:** https://arxiv.org/abs/2305.05176

### Mechanism

FrugalGPT introduces three cost-reduction strategies, then implements the most impactful as a system:

1. **Prompt adaptation** — shorten or restructure prompts
2. **LLM approximation** — cache or fine-tune a cheaper surrogate
3. **LLM cascade** — try a cheap model first; escalate to a stronger model only when the cheap model's answer fails a scoring/verification gate

The cascade learns which LLM sequence to apply per query type, treating the problem as a learned routing policy over LLM chains. Scoring gates are LLM-based (confidence estimation). The paper demonstrates that the optimal cascade is query-dependent: different task classes benefit from different model sequences.

### Headline Claims (the paper's claims)

- FrugalGPT can match the performance of GPT-4 with up to **98% cost reduction**
- FrugalGPT can **improve accuracy over GPT-4 by 4%** at the same cost

The paper notes that API costs vary by "two orders of magnitude" across providers, making cascade strategy highly effective.

### Notes for POC Implementation

FrugalGPT is the direct template for the L3a-frugalgpt-cascade POC. The cascade cheap→mid→strong structure with an LLM-judge gate is implemented live in this degree. The 98% cost reduction is not re-verified here; our live run reports whatever the actual measured outcome is.

---

## 3. Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing

**Authors:** Dujian Ding, Ankur Mallick, Chi Wang, Robert Sim, Subhabrata Mukherjee, Victor Ruhle, Laks V.S. Lakshmanan, Ahmed Hassan Awadallah  
**Year:** 2024 (accepted ICLR 2024, submitted April 22, 2024)  
**ArXiv:** https://arxiv.org/abs/2404.14618

### Mechanism

Hybrid LLM routes each query to a small (edge-deployable) or large (cloud-based) model based on predicted query difficulty and a tunable quality threshold. The router is a lightweight classifier trained to estimate how well the small model will handle a given input. At deployment, the quality threshold is a single knob that trades off small-model utilization against quality floor — and can be adjusted at test time without retraining.

The key insight: **edge models are deployed locally; large models are in the cloud**. The router eliminates unnecessary cloud calls, reducing both cost and latency for the majority of queries.

### Headline Claims (the paper's claims)

- **Up to 40% fewer calls to the large model with no drop in response quality**

The paper frames this as a practical system applicable to real deployments (Microsoft Research context).

### Notes for POC Implementation

The Hybrid LLM quality-threshold concept is used in the L2b-classifier-router POC: sweeping the decision threshold traces the Pareto curve. The "small = cheap, large = strong" mapping directly applies to our gpt-4.1-nano vs claude-sonnet-4-6 pool.

---

## 4. RouterBench: A Benchmark for Multi-LLM Routing System

**Authors:** Qitian Jason Hu, Jacob Bieker, Xiuyu Li, Nan Jiang, Benjamin Keigwin, Gaurav Ranganath, Kurt Keutzer, Shriyash Kaustubh Upadhyay  
**Year:** 2024 (submitted March 18, 2024)  
**ArXiv:** https://arxiv.org/abs/2403.12031  
**Blog:** https://withmartian.com/post/introducing-routerbench

### Mechanism

RouterBench is an evaluation framework and dataset for comparing LLM routing strategies. It provides:

- **405,467 inference outcomes** from 11 LLMs evaluated on 8 datasets spanning 64 tasks (the paper's reported figure)
- A cost-quality tradeoff framing: every routing strategy is evaluated on the Pareto frontier of accuracy vs. cost
- Theoretical foundations for measuring router efficacy, including oracle upper-bound computation (what the best-possible router would achieve given the model pool)

The benchmark enables reproducible, apples-to-apples comparison of routing strategies across the same task distribution, separating router quality from model quality.

### Headline Claims (the paper's claims)

- "No single model can optimally address all tasks and applications, particularly when balancing performance with cost"
- The dataset supports development of strategies for cost-aware decision-making across diverse tasks

### Notes for POC Implementation

RouterBench is the template for the X5-router-benchmark-pareto POC in this degree. We do not use the RouterBench dataset itself (licensing and size); instead we build a smaller analog using our own task suite and live model runs. The Pareto frontier visualization and oracle upper-bound computation follow RouterBench methodology.

---

## 5. Mixture-of-Agents Enhances Large Language Model Capabilities

**Authors:** Junlin Wang, Jue Wang, Ben Athiwaratkun, Ce Zhang, James Zou  
**Year:** 2024 (submitted June 7, 2024, Together AI)  
**ArXiv:** https://arxiv.org/abs/2406.04692

### Mechanism

Mixture-of-Agents (MoA) exploits the empirical finding that LLMs produce better outputs when conditioned on other models' outputs (the "collaborativeness" property). The architecture:

1. **Proposer layer**: N cheap models each generate an independent response to the query
2. **Aggregator layer**: One or more models receive all proposer outputs as context and synthesize a final answer
3. Layers can be stacked (each layer's outputs feed the next layer's aggregators)

The key insight: the aggregator is *not* routing — it is synthesizing. Cost-effectiveness comes from using cheap open-source models as proposers and reserving strong models (or using the same models again) for aggregation.

### Headline Claims (the paper's claims)

- MoA achieves **65.1% on AlpacaEval 2.0** using only open-source LLMs, vs. **57.5% for GPT-4 Omni** — a 7.6 percentage-point advantage
- Achieves state-of-the-art on AlpacaEval 2.0, MT-Bench, and FLASK, surpassing GPT-4 Omni

### Notes for POC Implementation

MoA is the template for the X1-mixture-of-agents POC. The key live question is whether cheap models together beat a single strong model on our specific task suite — the above benchmark result is the paper's claim on their data; our live run reports the real measured outcome on our coding/QA/math suite.

---

## 6. AutoMix: Automatically Mixing Language Models

**Authors:** Pranjal Aggarwal, Aman Madaan, Ankit Anand, Srividya Pranavi Potharaju, Swaroop Mishra, Pei Zhou, Aditya Gupta, Dheeraj Rajagopal, Karthik Kappaganthu, Yiming Yang, Shyam Upadhyay, Manaal Faruqui, Mausam  
**Year:** 2023 (submitted); accepted NeurIPS 2024  
**ArXiv:** https://arxiv.org/abs/2310.12963  
**Code:** https://github.com/automix-llm/automix

### Mechanism

AutoMix routes queries to larger LMs based on approximate correctness of outputs from a smaller LM. Two components:

1. **Few-shot self-verification**: the small model is prompted to assess whether its own answer is likely correct, without additional training. This produces an approximate confidence signal.
2. **POMDP-based router**: models the escalation decision as a Partially Observable Markov Decision Process, selecting the appropriately-sized model based on the accumulated verification confidence across multiple outputs.

The key distinction from simple cascade: the router uses a *structured decision process* over partial observations of answer quality, not a threshold on a single confidence score.

### Headline Claims (the paper's claims)

- "AutoMix consistently surpasses strong baselines, reducing computational cost by over 50% for comparable performance" across five language models and five challenging datasets

### Notes for POC Implementation

AutoMix is the template for the X4-verification-cascade-automix POC, which simplifies the POMDP to a threshold sweep for practical implementation.

---

## 7. Self-Consistency Improves Chain of Thought Reasoning in Language Models

**Authors:** Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdhery, Denny Zhou  
**Year:** 2023 (Published ICLR 2023)  
**ArXiv:** https://arxiv.org/abs/2203.11171

### Mechanism

Self-consistency replaces greedy decoding with a sample-then-vote approach:

1. Sample k diverse reasoning paths from the model at temperature > 0
2. Each path produces a final answer
3. Select the answer that appears most consistently across paths (majority vote)

The intuition: complex reasoning problems have multiple valid solution paths, all converging to the same correct answer. Diversity in paths → robustness in the aggregate answer.

### Headline Claims (the paper's claims)

On standard reasoning benchmarks vs. single greedy decode with chain-of-thought:

| Benchmark | Improvement |
|---|---|
| GSM8K | +17.9 percentage points |
| SVAMP | +11.0 percentage points |
| AQuA | +12.2 percentage points |
| StrategyQA | +6.4 percentage points |
| ARC-challenge | +3.9 percentage points |

These are the paper's reported figures, not our measurements.

### Notes for POC Implementation

Self-consistency is the template for the X2-self-consistency-vote POC. It is the simplest "ensemble" strategy — no second model needed, just multiple samples. The cost model is straightforward: k samples at cheap model price vs. 1 sample at strong model price.

---

## 8. More Agents Is All You Need

**Authors:** Junyou Li, Qin Zhang, Yangbin Yu, Qiang Fu, Deheng Ye  
**Year:** 2024 (submitted February 3, 2024)  
**ArXiv:** https://arxiv.org/abs/2402.05120  
**Published in:** Transactions on Machine Learning Research (TMLR)

### Mechanism

"Agent Forest": instantiate N independent agent instances of the same LLM, each generates a response independently, then aggregate by majority/plurality voting. The paper demonstrates that performance scales monotonically with the number of agents, with improvement magnitude correlated to task difficulty.

The approach is "orthogonal to existing methods" — it compounds with chain-of-thought, self-consistency, etc.

### Headline Claims (the paper's claims)

Performance on a wide range of LLM benchmarks scales with agent count. Specific benchmark numbers are not reproduced here from the abstract; see the paper for per-benchmark tables.

### Relationship to Self-Consistency

Both self-consistency (Wang et al.) and Agent Forest (Li et al.) exploit sampling variance, but differ in framing: self-consistency samples reasoning paths from one inference pass; Agent Forest instantiates fully independent agent instances. For routing purposes, both support the same implementation pattern in the X2-self-consistency-vote POC.

---

## 9. Improving Factuality and Reasoning in Language Models through Multiagent Debate

**Authors:** Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, Igor Mordatch  
**Year:** 2023 (submitted May 23, 2023)  
**ArXiv:** https://arxiv.org/abs/2305.14325  
**Project page:** https://composable-models.github.io/llm_debate/

### Mechanism

Multiple LLM instances propose initial responses independently. Over R rounds, each instance receives all other instances' most recent responses and reasoning, and is prompted to revise or defend its answer. A final aggregation step (judge or majority vote) selects the consensus answer.

The "society of minds" structure reduces hallucinations because models challenge each other's errors across rounds, converging toward factually grounded answers.

### Headline Claims (the paper's claims)

- "Significantly enhances mathematical and strategic reasoning across a number of tasks"
- "Improves the factual validity of generated content, reducing fallacious answers and hallucinations"
- Applies directly to existing black-box models without fine-tuning

Specific numeric results are reported in the paper per benchmark; we do not reproduce benchmark tables here without re-verifying them.

### Notes for POC Implementation

Multi-agent debate is the template for the X3-multi-agent-debate POC. The key live question is whether multi-round debate among cheap models beats a single strong model call on our QA/math suite — the paper's findings are on their benchmarks, our POC measures on our task suite.

---

## 10. LLM-Blender: Ensembling Large Language Models with Pairwise Ranking and Generative Fusion

**Authors:** Dongfu Jiang, Xiang Ren, Bill Yuchen Lin  
**Year:** 2023 (submitted June 5, 2023; accepted ACL 2023)  
**ArXiv:** https://arxiv.org/abs/2306.02561  
**ACL:** https://aclanthology.org/2023.acl-long.792/  
**Code:** https://github.com/yuchenlin/LLM-Blender

### Mechanism

LLM-Blender separates ensemble routing into two modules:

1. **PairRanker**: a cross-attention encoder that jointly encodes the input and a *pair* of candidate responses, determining which is better. This pairwise comparison avoids the calibration problem of absolute scoring.
2. **GenFuser**: takes the top-k ranked candidate responses and generates an improved fused output, synthesizing their complementary strengths.

The system introduces **MixInstruct**, a benchmark combining multiple instruction datasets with oracle pairwise comparisons.

### Headline Claims (the paper's claims)

- "Significantly outperforms individual LLMs and baseline methods across various metrics"
- PairRanker shows "the highest correlation with ChatGPT-based ranking" among evaluated ranking approaches

### Relationship to Other Papers

LLM-Blender's GenFuser is structurally equivalent to MoA's aggregator layer. PairRanker is a more principled ranking mechanism than simple majority vote (Self-Consistency). Together, these papers form a progression: sample → rank → fuse.

---

## Which Papers Are Reproduced Live in This Degree

| Paper | POC | Live? |
|---|---|---|
| RouteLLM (Ong et al.) | L2-embedding-knn-router, L2b-classifier-router | Yes (concept; our own data) |
| FrugalGPT (Chen et al.) | L3a-frugalgpt-cascade | Yes |
| Hybrid LLM (Ding et al.) | L2b-classifier-router (threshold sweep) | Yes |
| RouterBench (Hu et al.) | X5-router-benchmark-pareto | Yes (methodology; our own suite) |
| Mixture-of-Agents (Wang et al.) | X1-mixture-of-agents | Yes |
| AutoMix (Aggarwal, Madaan et al.) | X4-verification-cascade-automix | Yes |
| Self-Consistency (Wang et al.) | X2-self-consistency-vote | Yes |
| More Agents (Li et al.) | X2-self-consistency-vote | Yes (sampling pattern) |
| Multi-agent Debate (Du et al.) | X3-multi-agent-debate | Yes |
| LLM-Blender (Jiang et al.) | X1, X3 (aggregation pattern) | Partially (aggregation only) |

All "live" POCs run against real provider APIs (OpenAI, Anthropic, xAI) and report actual measured outcomes; the numbers above from the papers are not re-verified by our runs.

---

## Sources

- https://arxiv.org/abs/2406.18665 — RouteLLM
- https://www.lmsys.org/blog/2024-07-01-routellm/ — RouteLLM blog
- https://github.com/lm-sys/RouteLLM — RouteLLM code
- https://arxiv.org/abs/2305.05176 — FrugalGPT
- https://arxiv.org/abs/2404.14618 — Hybrid LLM
- https://arxiv.org/abs/2403.12031 — RouterBench
- https://arxiv.org/abs/2406.04692 — Mixture-of-Agents
- https://arxiv.org/abs/2310.12963 — AutoMix
- https://github.com/automix-llm/automix — AutoMix code
- https://arxiv.org/abs/2203.11171 — Self-Consistency
- https://arxiv.org/abs/2402.05120 — More Agents Is All You Need
- https://arxiv.org/abs/2305.14325 — Multiagent Debate
- https://arxiv.org/abs/2306.02561 — LLM-Blender
- https://aclanthology.org/2023.acl-long.792/ — LLM-Blender ACL
