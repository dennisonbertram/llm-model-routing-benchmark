# Commands

## Prerequisites
Load credentials (OpenAI only needed for this POC):
```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the behavioral tests (RED/GREEN)
```bash
# RED (no credentials):
OPENAI_API_KEY="" ANTHROPIC_API_KEY="" XAI_API_KEY="" python3 source/test_l5.py
# Expected: 5 failures (ProviderError: Missing env var OPENAI_API_KEY)

# GREEN (with credentials loaded):
cd source && python3 test_l5.py
# Expected: Ran 9 tests ... OK
```

## Run the full failure-modes demonstration
```bash
cd source && python3 run_l5.py
# Triggers FM1–FM5 live; prints structured log; writes l5_results.json
```

## Inspect the results
```bash
cat source/l5_results.json | python3 -m json.tool | head -80
```

## Verify no key leakage in output
```bash
# Check that the log output contains no raw key values:
python3 run_l5.py 2>&1 | grep -c "sk-"   # should be 0
```
