# Commands — L3b Harness Routing

## Prerequisites

Python 3.9+, stdlib only (no pip installs). Credentials:

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## RED (credential-less failure)

```bash
unset OPENAI_API_KEY ANTHROPIC_API_KEY XAI_API_KEY
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3b-harness-routing-coding-agent/source
python3 test_l3b.py
# Expected: FAILED (errors=4) — ProviderError: Missing env var OPENAI_API_KEY
```

## GREEN (behavioral tests)

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3b-harness-routing-coding-agent/source
python3 test_l3b.py
# Expected: Ran 4 tests in ~4s. OK
```

## Main harness run

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3b-harness-routing-coding-agent/source
python3 run_l3b.py
# Expected: three-harness results table + writes l3b_summary.json
# First run: ~65s (54 live calls). Second run: <1s (all cached).
```

## Inspect results

```bash
python3 -c "
import json
s = json.load(open('source/l3b_summary.json'))
for h in s['harnesses']:
    print(h['name'], h['accuracy'], h['total_usd'], 'escalations:', h['escalations'])
"
```
