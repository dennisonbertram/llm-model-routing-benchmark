# POC Intent
POC level: S3 — real Sakana Fugu vs GPT-5.5 (live)
Concept introduced: calling the actual production multi-agent orchestrator (Fugu Mini + Ultra) and pricing its orchestration overhead.
Prior concepts reused: the hard suite (S0), deterministic graders, gpt-5.5 reference (X6), uniform cost accounting (harness, extended to fold Fugu orchestration tokens).
Live service boundary: live api.sakana.ai/v1 chat completions (fugu, fugu-ultra) + gpt-5.5.
What this must prove: real Fugu accuracy vs a single frontier call, and the true cost/latency of orchestration — win OR loss.
What would count as cheating: fabricating Fugu numbers; hiding the orchestration-token cost; scoring Fugu's timeouts as capability failures without saying so.
