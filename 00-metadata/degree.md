# Degree: Model Routing — LLM & Agent Model Routing

**Name**: Model Routing — LLM & Agent Model Routing

**Target**: Model Routing (the discipline of picking the best model for a job + cost efficiency)

**Category**: inference-optimization

**Degree slug**: `01-llm-model-routing`

**Audience**: Autonomous LLM coding agents. Every artifact is optimized for an LLM reader —
explicit, structured, operational, copy-paste-ready, evidence-linked.

## Prime directive

Train future autonomous coding agents to **route between models** to maximize quality per dollar.
Cover the full discipline with live, test-driven, evidence-backed POCs: rule/heuristic routing;
predictive routing (embedding-kNN, trained classifiers — RouteLLM / Hybrid-LLM); LLM cascades with
verification (FrugalGPT, AutoMix); harness routing (opencode-style per-step model selection inside
a coding agent); ensembles where cheap models used together rival a single SOTA model
(Mixture-of-Agents, self-consistency sample-and-vote, multi-agent debate); routing as a deployed
OpenAI-compatible gateway; and benchmarking routers on a cost-vs-quality Pareto frontier
(RouterBench-style, with an oracle upper bound). Capture what the papers claim, what actually
happened against real model APIs, what broke, and what a future agent must know before building.

## Primary question

Given a stream of tasks across disciplines (coding most important, plus QA and math/reasoning),
can an agent route each task to the cheapest model that will still get it right — and can cheap
models combined rival a single SOTA model — with live evidence for every cost and quality figure?

## Why this degree exists

Frontier models are expensive and overkill for most requests; tiny models are cheap but fail the
hard ones. Routing is how production agent systems (opencode, Claude Code, LiteLLM, OpenRouter Auto
Router, RouteLLM, Martian, Unify) cut cost by large factors at matched quality. This degree turns
that literature and tooling into live-verified, searchable knowledge: not "the paper says 98%
savings", but "here is a router we ran against real APIs, here are the measured cost and accuracy,
here is where it sits on the Pareto frontier, and here is what broke."

## Live substrate

OpenAI (`gpt-4.1-nano`→`gpt-4o-mini`→`gpt-4o`/`gpt-4.1`→`gpt-5`, embeddings `text-embedding-3-small`),
Anthropic (`claude-haiku-4-5`→`claude-sonnet-4-5/4-6`→`claude-opus-4-x`), and xAI (`grok-4.3`).
OpenRouter is an optional enhancement (adds open models + native per-generation cost accounting)
and is wired only if `OPENROUTER_API_KEY` is provided.

**Status**: Scaffolded; live substrate verified 2026-06-21 (OpenAI + Anthropic + xAI reachable);
POC ladder L0–L5 + ensemble experiments (X1–X4) + RouterBench Pareto (X5) + capstone planned.
