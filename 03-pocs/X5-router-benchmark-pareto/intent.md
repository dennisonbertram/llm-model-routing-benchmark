# POC Intent

POC level: X5 — RouterBench-style benchmark (aggregate)
POC name: Cost-vs-quality Pareto frontier over all routers
Concept introduced: a unified, leakage-free comparison of every routing strategy on one suite, with
  an oracle ceiling and a realizable frontier.
Prior concepts reused: L0 outcome matrix; L1 heuristic; L2 kNN; L2b logistic classifier; X1 MoA; X2 self-consistency.
Live service boundary exercised: live embeddings (text-embedding-3-small) + live MoA/self-consistency calls.
Real resources required: OPENAI_API_KEY, ANTHROPIC_API_KEY.
Expected learning: which routers are actually worth deploying, and whether cheap ensembles beat a single strong model.
What this POC must prove: a realizable router can match strong accuracy far cheaper; report ensemble results honestly.
What would count as cheating: tuning the suite to force a router win; reporting MoA/self-consistency as wins when measured otherwise; train/test leakage in the predictive routers.
Why cheating would destroy the learning: the benchmark's entire value is an honest cost-quality verdict.
