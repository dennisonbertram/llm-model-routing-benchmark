# Intent — X1 Mixture-of-Agents

**What:** Implement and benchmark Mixture-of-Agents (MoA) from Wang et al. (Together AI, 2024).
Fan out each query to N cheap proposer models from different families (gpt-4o-mini, gpt-4.1-mini,
claude-haiku-4-5), then synthesise a single answer using an aggregator (gpt-4o). Optionally run
a 2-layer variant on hard items.

**Why:** The Wang et al. paper claims cheap models together can match or exceed a single SOTA
model by leveraging cross-family answer diversity and synthesis. This POC measures whether that
claim holds on the routing harness suite — particularly on the 6 hard math items that define
the cost-quality gap established in L0.

**Research question:** Does MoA(3 cheap models) match single strong model accuracy? At what cost?
Is the accuracy gain worth the overhead, or does a single strong model dominate?

**Hypothesis (stated before running):** MoA should help on hard math (where cheap models
individually fail but diverse proposals might contain a correct one). QA/coding are already
saturated — MoA will add cost with no accuracy gain there. The aggregator call on long coding
answers will be expensive.

**Constraints:**
- Use only `config.ENSEMBLE_CHEAP` as proposers (no oracle leakage via difficulty/discipline).
- Use `judge.aggregate_moa` from the frozen harness — do not rewrite aggregation logic.
- Use OWN cache at `source/.cache.json`, not the shared harness labelset.
- Baselines (cheap/strong) reuse the harness labelset cache (no re-billing).
- Report the measured outcome truthfully; do not tune the suite or prompts.
