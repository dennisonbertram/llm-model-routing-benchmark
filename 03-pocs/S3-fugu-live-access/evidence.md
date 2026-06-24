# S3 Live Evidence
Status: Complete with live evidence. Captured 2026-06-22. Live: api.sakana.ai/v1 (fugu, fugu-ultra) + gpt-5.5. No mocks. Machine-readable: source/fugu_results.json; redacted API evidence: source/evidence.txt.

21 authored hard tasks (same deterministic graders as S0):
  gpt-5.5      acc=1.000  $0.0097/task   8.1s   orch_tok/task=0
  fugu(mini)   acc=0.905  $0.0390/task  12.7s   orch_tok/task=0
  fugu-ultra   acc=1.000  $0.1191/task  45.4s   orch_tok/task=7719

Claims supported: real Fugu-Ultra matches a single gpt-5.5 call on accuracy but at 12.2x cost / 5.6x latency (orchestration overhead); fugu-mini is less accurate AND 4x pricier than one gpt-5.5 call on this workload.
Claims NOT supported: Fugu's frontier-benchmark wins (GPQA-D/ARC/SWE-Pro) — those are Sakana's claims on harder tasks, not reproduced here (our suite is below the frontier where orchestration helps). Fugu pricing for the mini tier is an estimate ($5/$30 ceiling).
