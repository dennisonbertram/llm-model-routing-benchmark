# Commands — X3 Multi-Agent Debate

## Prerequisites

```bash
# Load credentials (required for any live call)
set -a; . .agent-university/secrets.local.env; set +a
# Verify keys are present (do NOT print values)
[ -n "$OPENAI_API_KEY" ] && echo "OPENAI SET" || echo "UNSET"
[ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC SET" || echo "UNSET"
```

## Run tests

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X3-multi-agent-debate/source
python3 test_x3.py     # 5 tests — GREEN with keys, RED (4 errors) without
```

## Run main benchmark

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X3-multi-agent-debate/source
python3 run_x3.py
# Produces: x3_summary.json, updates .cache.json
# Runtime: ~4-6 minutes on first run (190 live calls); re-runs use cache
```

## Expected output summary

```
== RESULTS ==
| router             | n  | accuracy | total_usd | ...
| always:gpt-4o-mini | 23 | 0.6957   | 0.000147  |
| always:gpt-4.1     | 23 | 0.9565   | 0.001634  |
| debate:3x1r        | 23 | 0.9565   | 0.006278  |
```

## Capture red/green

```bash
# RED (without keys)
unset OPENAI_API_KEY ANTHROPIC_API_KEY && python3 test_x3.py 2>&1 > red-output.txt

# GREEN (with keys loaded)
python3 test_x3.py 2>&1 > green-output.txt
```
