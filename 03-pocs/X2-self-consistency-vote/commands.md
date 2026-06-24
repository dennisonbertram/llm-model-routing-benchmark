# Commands to run this POC

## Prerequisites

Load credentials:
```bash
set -a; . .agent-university/secrets.local.env; set +a
```

Navigate to POC directory:
```bash
cd /Users/dennison/conductor/workspaces/agent-university/nashville/model-routing/degrees/01-llm-model-routing/03-pocs/X2-self-consistency-vote
```

## Main evaluation

Run the full self-consistency voting benchmark (15 math items, k=1,3,5):
```bash
python3 source/run_x2.py
```

**Output:**
- Baseline tables (always-cheap, always-strong)
- Self-consistency results at k=1, 3, 5
- Hard-math accuracy breakdown
- Pareto frontier analysis
- Summary JSON: `source/x2_summary.json`
- Green output log: `source/green-output.txt`

**Cost:** ~$0.002 per run (using shared cache)

## Variance test (fresh API calls)

Verify that gpt-4o-mini produces low variance at high temperature:
```bash
python3 source/test_variance.py
```

**Output:**
- 5 fresh samples each on 2 hard items (m9, m13) at T=0.7
- No caching — forces real API calls
- Outputs to `source/variance-test.txt`

**Cost:** ~$0.00008 per run (10 fresh calls)

## Debug script

Inspect actual samples and voting behavior on selected items:
```bash
python3 source/debug_x2.py
```

Uses the cache to examine what answers the voting algorithm selected.

## Expected runtimes

- Full run: ~30 seconds (mostly API latency)
- Variance test: ~20 seconds
- Debug: <5 seconds

## Troubleshooting

If you see "ProviderError: Missing env var OPENAI_API_KEY":
- Ensure `set -a; . .agent-university/secrets.local.env; set +a` ran successfully
- Verify: `echo $OPENAI_API_KEY` returns a non-empty string (do NOT print the actual key)

If variance test hits rate limits:
- Wait 60 seconds and retry
- Or use `nocache=False` to use the shared cache instead of fresh calls
