# POC Intent

POC level: L5 — failure modes and observability
POC name: Resilient routing under real provider faults + structured cost observability
Concept introduced: fault classification (invalid slug / timeout / malformed request / budget
  exhausted); fallback chains; cost-budget guards; structured observability without key leakage.
Prior concepts reused: providers.chat (L0), resilient_call wraps the same harness provider layer.
Live service boundary exercised: real OpenAI chat/completions calls for all 5 failure modes;
  real HTTP 404 (bad slug), real HTTP 400 (over-limit max_tokens), real network TimeoutError.
Real resources required: funded OPENAI_API_KEY (OpenAI only — no Anthropic/xAI needed for
  the failure modes; budget guard only uses gpt-4o-mini and gpt-4.1).
Expected learning: which provider errors are retryable (429/5xx) vs terminal (400/404); how a
  fallback chain is structured; how a cost-budget guard gates model calls; how to emit structured
  observability without leaking credentials.
What this POC must prove: >=3 real provider errors occur (not simulated); each is caught and
  recovered by a fallback or guard; the structured log records every decision; no key material
  appears in the log.
What would count as cheating: mocking urllib responses; injecting fake error bodies; pretending
  a timeout occurred by sleeping rather than hitting a real network deadline.
Why cheating would destroy the learning: production routing failures are provider-specific and
  error-body-specific; the value is seeing the real HTTP response format and knowing the guard
  logic works against it.
