# Evidence — L3b Harness Routing

## Evidence tier: Live verified

All numbers in this POC come from real API calls captured 2026-06-21.

## Live run evidence

### Models called
- `gpt-4o-mini` (OpenAI) — cheap harness + routed first-attempt; 18 tasks × 1 call each
- `gpt-4.1` (OpenAI) — strong harness; 18 tasks × 1 call each; also repair-prompt test

### Token and cost measurements (from l3b_summary.json)
- all-cheap total cost: $0.001482 (18 tasks, all first-attempt, 0 escalations)
- all-strong total cost: $0.019672 (18 tasks, all first-attempt)
- routed total cost: $0.001482 (identical to all-cheap — no escalations fired)
- cost ratio strong/cheap: 13.25x

### Grader evidence
All 18 coding tasks graded by subprocess unit-test execution (not an LLM judge). The grader
writes candidate code + assert tests to a temp file and runs `python3 <file>`, checking for
exit code 0 and "ALL_OK" in stdout. This is fully deterministic.

### Test evidence (test_l3b.py)
- `test_cheap_model_answers_coding_task`: gpt-4o-mini answered c1 (is_palindrome) live, cost >0, PASS
- `test_strong_model_answers_coding_task`: gpt-4.1 answered c18 (is_number, hard discriminator) live, PASS
- `test_repair_prompt_elicits_code`: gpt-4.1 given a stubbed fizzbuzz + failure context; returned
  correct code that passed unit tests — repair loop works live
- `test_result_shape`: _run_item_cheap returns a dict with all required keys

### Cache
37 entries in source/.cache.json after first run. Second run: 54 hits, 0 misses (0.8s vs 65.8s).

## What is NOT live verified

- Escalation behavior under a tighter token budget (not tested; not part of this POC)
- Non-coding disciplines (math/qa escalation covered by L0 baseline, not re-run here)
- Repair on tasks that the cheap model actually fails at temperature=0 (none existed in the 18-task suite)
