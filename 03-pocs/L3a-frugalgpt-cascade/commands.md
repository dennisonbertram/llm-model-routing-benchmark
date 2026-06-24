# Commands — L3a FrugalGPT Cascade

All commands run from the repo root: `/Users/dennison/conductor/workspaces/agent-university/nashville`

## Load credentials

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the full cascade

```bash
python3 model-routing/degrees/01-llm-model-routing/03-pocs/L3a-frugalgpt-cascade/source/run_l3a.py
```

Outputs:
- Baselines table (from labelset, no re-billing)
- Cascade sweep at thresholds 0.1, 0.3, 0.5, 0.7, 0.9
- Verifier error analysis
- Per-discipline breakdown
- `source/l3a_summary.json`

On first run: makes 52 live gate + escalation API calls (~$0.002–0.004).
On re-runs: serves from `source/.cache.json` at $0 additional cost.

## Run behavioral tests

```bash
python3 -m pytest model-routing/degrees/01-llm-model-routing/03-pocs/L3a-frugalgpt-cascade/source/test_l3a.py -v
```

Expected: 7 passed, 1 skipped (summary test requires l3a_summary.json to exist first).

## Inspect the cascade cache

```bash
python3 -c "
import json
with open('model-routing/degrees/01-llm-model-routing/03-pocs/L3a-frugalgpt-cascade/source/.cache.json') as f:
    data = json.load(f)
print(f'Cached entries: {len(data)}')
"
```

## Check confidence values for specific items

```bash
python3 -c "
import sys, json
sys.path.insert(0, 'model-routing/degrees/01-llm-model-routing/harness')
sys.path.insert(0, 'model-routing/degrees/01-llm-model-routing/03-pocs/L3a-frugalgpt-cascade/source')
from run_l3a import get_confidence
conf, usd = get_confidence('What is 17 + 25?', '42')
print(f'conf={conf}  usd={usd:.4e}')
"
```
