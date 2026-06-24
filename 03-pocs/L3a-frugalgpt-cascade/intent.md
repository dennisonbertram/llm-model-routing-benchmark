# Intent — L3a FrugalGPT Cascade

Implement and live-evaluate a FrugalGPT-style LLM cascade (Chen/Zaharia/Zou, 2023):

1. Call the cheap model (gpt-4o-mini) first.
2. A verification gate decides whether to accept or escalate to the strong model (gpt-4.1).
3. Gate strategy by discipline:
   - **math / qa**: ask cheap to self-rate confidence 0–1; escalate if confidence < threshold.
   - **coding**: ask cheap LLM judge "YES/NO: is this code correct?"; escalate on NO.
4. Sweep the confidence threshold (0.1–0.9) to trace cost-quality trade-off.
5. Report cascade acc/cost vs always-strong and always-cheap.
6. Measure verifier error honestly — false accepts are real failures.

Goal: show whether a confidence gate can capture most of the accuracy gain of always-strong
while paying only a fraction of the cost, and measure where it fails.

The primary baselines (always-cheap, always-strong, oracle) are read from the labelset export
without re-billing. Only gate calls and escalated strong calls are fresh live API calls.
