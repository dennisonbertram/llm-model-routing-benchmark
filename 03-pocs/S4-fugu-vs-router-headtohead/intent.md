# POC Intent
POC level: S4 — Fugu vs our router, head-to-head (falsification)
Concept introduced: a clean apples-to-apples cost/accuracy/latency comparison of the real Fugu vs our routers on identical fresh tasks, designed to be falsified.
Prior reused: harness cost accounting (incl Fugu orchestration billing), gpt-5.5 reference, the heuristic + classifier routers (X5/X6), deterministic graders.
Live boundary: live gpt-4o-mini, gpt-5.5, fugu, fugu-ultra over api.sakana.ai + OpenAI.
What this must prove (or disprove): whether our router matches Fugu accuracy at lower cost on the SAME tasks — with explicit falsification checks + an adversarial review.
What would count as cheating: different tasks per system; unfair cost accounting; classifier leakage; quoting a cherry-picked per-task max instead of the aggregate.
