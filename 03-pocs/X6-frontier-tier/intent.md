# POC Intent

POC level: X6 — frontier tier (follow-up experiment)
POC name: Does a more powerful model (GPT-5.5) change the routing story?
Concept introduced: a frontier reasoning model as a top routing tier; 3-tier routing (cheap→mid→frontier).
Prior concepts reused: L0 outcome matrix; L2b/X5 logistic classifier; the cost/oracle framing.
Live service boundary exercised: live gpt-5.5 + gpt-5.4 calls (reasoning) + live embeddings.
Real resources required: OPENAI_API_KEY (gpt-5.5/gpt-5.4 access).
Expected learning: whether a stronger model raises the ceiling, at what cost, and whether routing captures it cheaply.
What this POC must prove: real accuracy/cost for gpt-5.5/5.4; a realizable 3-tier router near the new ceiling.
What would count as cheating: assuming gpt-5.5 is better without measuring; faking the 3-tier router; train/test leakage.
Why cheating would destroy the learning: the whole point is the MEASURED frontier-vs-cost tradeoff.
