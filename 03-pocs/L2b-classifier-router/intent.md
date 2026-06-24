# Intent — L2b Classifier Router

**Hypothesis**: A logistic regression trained on text-embedding-3-small features can predict
P(cheap model is correct) for a prompt, and sweeping the decision threshold traces a cost-quality
Pareto curve between the always-cheap and always-strong baselines.

**Why this matters**: This is the RouteLLM / Hybrid-LLM approach — supervised learning replaces
hand-tuned heuristics. With enough labeled examples, a trained classifier should outperform both
heuristics (L1) and kNN similarity (L2) because it learns a decision boundary over the full
embedding space.

**What we're testing**:
1. Can a numpy-free logistic regression learn a useful signal from 1536-dim embeddings?
2. Does threshold sweeping produce a real Pareto curve with interior operating points?
3. Where does this approach hit its limits (class imbalance, small dataset)?
4. How close to the oracle ($0.00214 on full suite) can the classifier get?

**Rules respected**:
- No oracle leakage: features are embedding vectors only (no `item['difficulty']` or `item['discipline']`)
- No mock calls: embeddings via real `embed()` API call; outcome matrix from L0's live runs
- Routing-collapse guard: asserted at interior thresholds within the effective decision range
