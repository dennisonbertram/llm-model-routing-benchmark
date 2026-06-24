# Intent

AutoMix-style verification cascade (Madaan et al., 2023). Instead of a trained
classifier or embedding-based router, the cheap model self-verifies its own answer:
k independent binary "is this correct?" samples produce a confidence estimate that
drives the escalation decision.

Goals:
- Quantify the cost-quality curve over threshold T (the POMDP-lite knob).
- Measure verifier calibration: does low confidence actually predict wrong answers?
- Compare to the oracle and always-strong baselines.
- Report honestly whether AutoMix is cost-competitive with the oracle and with
  classifier/embedding routers on this suite (it may not be — that is a valid finding).

This POC uses the RouterBench-style labelset (harness/.cache/labelset_export.json) for
answer correctness and answer cost, avoiding re-billing for the cheap/strong answer calls.
Verifier calls (k=3 per item) are new live calls and capture the actual overhead.
