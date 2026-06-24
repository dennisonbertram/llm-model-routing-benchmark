# Surprises

## OpenAI silently ignores temperature=0.0 on gpt-4o-mini for short tasks
Not a failure mode per se, but notable: with temperature=0.0 the model consistently returns "4"
for "What is 2+2?" with no variation. The determinism is a feature when testing fallback chains
because it makes the recovered answer predictable and assertable.

## HTTP 400 is the right error for max_tokens=999999 — not 422
The OpenAI API returns a 400 (Bad Request) for invalid parameter values, not 422 (Unprocessable
Entity) as one might expect from REST conventions. The harness's existing `HTTPError` handler
catches 400 and does NOT retry it (only 429/5xx trigger retries), which is correct behavior —
retrying a request with a bad parameter will always fail.

## The cost-budget guard must make a REAL call to know actual cost
Unlike a pre-call estimator (which could guess cost from token counts before sending), the guard
in this POC calls the model first and then checks whether to accept. This means it still pays for
the call even when refusing — though refusal returns $0 to the caller since the answer is
discarded. In a production router, a pre-call token-count estimate would avoid this. This POC
documents the simpler "call-then-check" pattern as a baseline; token-count estimation is a
natural next step.

## gpt-4o-mini charges ~$0.00000360–0.00000405 for a simple factual question
The cost is dominated by the fixed prompt tokens (the prompt template overhead) rather than
the output. This means the minimum call cost for any question to gpt-4o-mini is roughly
$0.0000036, regardless of how short the answer is. Budget guards need to account for this floor.

## Python 3.9 does not support `dict | None` union type annotations
The harness requires Python 3.9 (stdlib + numpy only, no pip installs). The `|` union syntax
for type hints (e.g., `dict | None`) is a 3.10+ feature. The function signature had to use
plain `def f(x):` without type annotations to stay compatible.

## FM5 escalation was not triggered in the live run
The cheap model (gpt-4o-mini) answered 17*23=391 correctly, so no escalation to the strong model
occurred. This is the honest result: the cheap model handles simple arithmetic reliably. The
verifier logic and escalation path are still unit-tested via `test_fm5_verifier_escalation_logic`
to prove the logic is correct — but the live math test did not force an escalation.
