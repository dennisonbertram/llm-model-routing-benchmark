# Research Index — LLM Model Routing

**Degree**: 01-llm-model-routing  
**Track**: inference-optimization  
**Audience**: autonomous LLM coding agents  
**Date compiled**: 2026-06-21  
**Evidence label**: Research supported but not live verified (research files); Live verified reserved for POC artifacts.

---

## What this directory covers

This `01-research/` directory grounds every concept, paper claim, and design decision used in later planning, POC implementations, and distillation. It is written for an LLM agent that must be able to pick, implement, and benchmark a model router from scratch.

Each file is scoped to a distinct concern. Start with `mental-model.md` for orientation, then read in the order below for progressive depth.

---

## File map

| File | What it covers |
|---|---|
| `research-index.md` *(this file)* | Directory map and open research questions |
| `mental-model.md` | The cost-vs-quality Pareto framing; baselines (always-cheap, always-strong, random) and the ORACLE upper bound; what "a good router" means; why coding is hard to route |
| `capability-map.md` | Full taxonomy of routing strategies — non-predictive, predictive, cascades, ensembles, harness routing — with citations, when-to-use, and cost/quality tradeoffs |
| `common-use-cases.md` | Concrete routing use-cases per discipline (coding agents, QA/chat, math/reasoning, batch pipelines) with recommended strategy per use-case |
| `pricing-quotas-limits.md` | Current official pricing for the live model pool (OpenAI, Anthropic, xAI); token limits; cost-per-call accounting approach |
| `known-failure-modes.md` | Failure modes specific to routing systems: cascade runaway cost, verifier hallucination, distribution shift, cold-start with no labels, latency budget exhaustion |
| `production-routers.md` | Survey of deployed production routing products: LiteLLM Router, OpenRouter Auto, NotDiamond, Martian, Unify, Aurelio semantic-router; what each provides and when to prefer one |
| `testing-model.md` | How to evaluate a router: the RouterBench / AIQ framing; Pareto frontier plots; cost-accuracy tradeoff curves; oracle gap metric |

---

## Research questions this directory answers

These questions correspond to the POC ladder in the degree spec. Each research file answers a cluster; the mapping is shown.

### Q1 — Routing strategy taxonomy (→ `capability-map.md`)
- What is the exhaustive set of routing strategy families?
- Which strategies require labeled training data, which are zero-shot?
- What is the difference between a cascade and a router?
- How does a Mixture-of-Agents ensemble differ from a routing decision?

### Q2 — Mental model and evaluation framing (→ `mental-model.md`)
- What is the Pareto frontier in routing, and how is it plotted?
- What does "ORACLE upper bound" mean and why can't a real router reach it?
- How does the "threshold / bias-toward-cheap" knob shift the operating point?
- Why is coding harder to route than QA?

### Q3 — Use-case fit (→ `common-use-cases.md`)
- Which strategy is best suited to coding agent harness routing (opencode-style)?
- Which strategy works for closed-answer QA without training data?
- What is the cheapest viable approach for batch math/reasoning pipelines?
- When does a cascade beat a direct classifier, and vice versa?

### Q4 — Pricing and cost accounting (→ `pricing-quotas-limits.md`)
- What is the actual USD cost per 1M tokens for each model in the pool?
- Does xAI's `grok-4.3` return USD directly, and if so how?
- How do you compute total cost when a cascade makes multiple calls?

### Q5 — Failure modes (→ `known-failure-modes.md`)
- What are the ways a cascade can cost MORE than the strong model baseline?
- How does verifier hallucination corrupt AutoMix-style systems?
- What happens when the routing label distribution shifts between train and test?

### Q6 — Production systems (→ `production-routers.md`)
- What routing strategies does LiteLLM Router actually implement?
- How does OpenRouter's Auto Router (NotDiamond) work under the hood?
- What is Martian's value proposition vs. rolling your own router?

### Q7 — Evaluation methodology (→ `testing-model.md`)
- What is the AIQ metric from RouterBench and why is it preferred over accuracy alone?
- How do you construct a RouterBench-style evaluation without the full 405k-row dataset?
- What is the correct oracle for a two-model routing setup?

---

## Key papers and systems (quick reference)

All citations in this directory are real; specific quantitative claims are attributed to their source and labeled "paper's claim, not our measurement."

| System / Paper | arXiv / URL | Focus |
|---|---|---|
| RouteLLM (Ong et al., 2024) | [2406.18665](https://arxiv.org/abs/2406.18665) | Trained routers (MF, BERT, SW-ranking, causal-LLM) from preference data |
| FrugalGPT (Chen, Zaharia, Zou, 2023) | [2305.05176](https://arxiv.org/abs/2305.05176) | LLM cascade; up to 98% cost reduction vs GPT-4 (paper's claim) |
| Hybrid LLM (Ding et al., ICLR 2024) | [2404.14618](https://arxiv.org/abs/2404.14618) | Learned router; up to 40% fewer strong-model calls (paper's claim) |
| RouterBench (Hu et al., ICML 2024) | [2403.12031](https://arxiv.org/abs/2403.12031) | 405k-row benchmark; AIQ metric; 11 LLMs; Pareto/convex-hull eval |
| AutoMix (Madaan et al., NeurIPS 2024) | [2310.12963](https://arxiv.org/abs/2310.12963) | Self-verification + POMDP meta-verifier cascade; >50% cost reduction (paper's claim) |
| Mixture-of-Agents (Wang et al., 2024) | [2406.04692](https://arxiv.org/abs/2406.04692) | Layered ensemble; 65.1% AlpacaEval 2.0 vs 57.5% GPT-4o (paper's claim) |
| Self-Consistency (Wang et al., 2022) | [2203.11171](https://arxiv.org/abs/2203.11171) | Sample-and-vote; +17.9% GSM8K on PaLM-540B (paper's claim) |
| More Agents Is All You Need (Li et al., 2024) | [2402.05120](https://arxiv.org/abs/2402.05120) | Scaling agent count via voting; Llama2-13B×15 ≈ Llama2-70B (paper's claim) |
| LLM-Blender (Jiang et al., ACL 2023) | [2306.02561](https://arxiv.org/abs/2306.02561) | PairRanker + GenFuser ensemble on MixInstruct |
| Multi-agent debate (Du et al., 2023) | [2305.14325](https://arxiv.org/abs/2305.14325) | N agents debate multiple rounds; factuality + reasoning improvements |
| LiteLLM Router | [docs.litellm.ai](https://docs.litellm.ai/docs/routing) | Production gateway; simple-shuffle, least-busy, usage-based, latency-based strategies |
| NotDiamond / OpenRouter Auto | [notdiamond.ai](https://www.notdiamond.ai/) | Commercial trained router powering OpenRouter's `openrouter/auto` |
| Martian | [route.withmartian.com](https://route.withmartian.com/) | Commercial router claiming up to 98% cost reduction |

---

## Validation sequence (maps to POC ladder)

| Research cluster | Validates |
|---|---|
| `mental-model.md` + `pricing-quotas-limits.md` | L0: baseline always-cheap / always-strong / random; cost table |
| `capability-map.md` § non-predictive | L1: heuristic router |
| `capability-map.md` § predictive (kNN) | L2: embedding-kNN router |
| `capability-map.md` § predictive (classifier) | L2b: logistic regression classifier |
| `capability-map.md` § cascades + `known-failure-modes.md` | L3a: FrugalGPT cascade |
| `capability-map.md` § harness routing | L3b: opencode-style per-step routing |
| `production-routers.md` | L3c: OpenAI-compatible gateway integration |
| `testing-model.md` | X5: RouterBench-style Pareto benchmark |
| `capability-map.md` § ensembles (MoA) | X1: Mixture-of-Agents POC |
| `capability-map.md` § ensembles (self-consistency) | X2: self-consistency vote |
| `capability-map.md` § ensembles (debate) | X3: multi-agent debate |
| `capability-map.md` § cascades (AutoMix) | X4: verification cascade |
| All files | L-capstone: adaptive routing gateway |
