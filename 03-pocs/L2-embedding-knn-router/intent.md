# Intent — L2 Embedding k-NN Router

## Goal

Implement the RouteLLM similarity-weighted k-NN routing flavor and measure its cost/quality
trade-off against the baselines established in L0.

## What we're building

A prompt-only router that:
1. Embeds every prompt with `text-embedding-3-small` (one live API call).
2. Uses a parity-based train/test split so the test set is held out.
3. For each test prompt, finds k nearest training prompts by cosine similarity.
4. Predicts "cheap suffices" via similarity-weighted vote on `cheap_correct` labels.
5. Routes to `gpt-4o-mini` if vote >= threshold, else to `gpt-4.1`.
6. Sweeps k in {1,3,5,7} and threshold in {0.4,0.5,0.6,0.7}.
7. Evaluates on the held-out test split using the pre-measured outcome matrix (no re-billing).
8. Live-confirms 3 routing decisions against real provider APIs.

## What makes this interesting

The k-NN router requires NO training beyond the labeled outcome matrix — it is a pure
retrieval-based classifier. The embedding cost is tiny ($0.000030 for 45 prompts) and
paid once. Every subsequent routing decision is O(n) dot products.

The threshold sweep exposes the Pareto frontier directly: raising the threshold routes more
items to strong (higher cost, higher accuracy). This gives the operator a single knob to tune
for their accuracy/cost target.

## What we do NOT do

- No oracle leakage: `difficulty` and `discipline` fields are never used as features.
- No re-billing: we reuse the pre-measured outcome matrix from `labelset_export.json`.
- No mocks: embeddings come from a live OpenAI call; live-confirmation calls hit real APIs.
