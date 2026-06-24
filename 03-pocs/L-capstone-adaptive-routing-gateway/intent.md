# POC Intent

POC level: L-capstone — combined system
POC name: Adaptive Routing Gateway (OpenAI-compatible)
Concept introduced: integrate predictive routing + verification escalation + budget guard +
  fallback + observability into one deployable OpenAI-compatible gateway, benchmarked near oracle.
Prior concepts reused: L0 outcome matrix; L2b classifier (winner); L3a/X4 verification escalation;
  L4/L3c gateway runtime; L5 failure handling + budget guard; X5 benchmark methodology.
Live service boundary exercised: live chat to OpenAI/Anthropic via the gateway; live embeddings; real HTTP server + curl.
Real resources required: OPENAI_API_KEY, ANTHROPIC_API_KEY (XAI optional).
Expected learning: a single component can capture most of the oracle's savings at strong-level accuracy, safely.
What this POC must prove: deployable router matches strong accuracy far cheaper; budget guard + fallback + gateway work live.
What would count as cheating: leakage in the benchmark (train==test); faking the gateway/ledger; hiding the budget-guard or fallback behind mocks.
Why cheating would destroy the learning: the capstone is the proof that the whole curriculum compounds into something real.
