# How to run L1

## Prerequisites

Set up credentials (once per session):

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

Verify OPENAI_API_KEY is set:

```bash
[ -n "$OPENAI_API_KEY" ] && echo "SET" || echo "UNSET"
```

## Run the heuristic router

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L1-heuristic-router/source
python3 run_l1.py
```

Expected output: threshold sweep (7 thresholds), operating point selection, items routed to strong,
live confirmation on 3 test items, final eval at τ=0.40.

Typical runtime: ~10 seconds (3 live API calls + cached labelset).

## What it outputs

1. **stdout**
   - Baseline metrics (always-cheap, always-strong, oracle)
   - Threshold sweep table (7 rows, one per τ)
   - Recommended operating point (τ=0.40)
   - List of 11 items routed to strong
   - Live confirmation results (3 items)
   - Final evaluation summary

2. **source/l1_summary.json**
   - Machine-readable results: accuracy, cost, threshold, routed items
   - Use for downstream analysis/benchmarking

3. **source/.cache.json**
   - Local response cache (if live calls were made)
   - Safe to delete; will be rebuilt on next run

4. **source/green-output.txt**
   - Copy of stdout from last successful run

## If it fails

### Missing credentials

```
ProviderError: Missing env var OPENAI_API_KEY
```

**Fix**: Reload credentials:
```bash
set -a; . .agent-university/secrets.local.env; set +a
[ -n "$OPENAI_API_KEY" ] && echo "OK" || echo "FAILED"
```

### Network timeout

```
ConnectTimeout: HTTPSConnectionPool(...) timed out
```

**Fix**: Retry. OpenAI API can be slow; the harness has a 30-second timeout.

### Module not found

```
ModuleNotFoundError: No module named 'numpy'
```

**Fix**: numpy is bundled in the harness environment. Verify you're in the right directory:

```bash
ls -la ../../harness/
```

Should contain `providers.py`, `cache.py`, `router_base.py`, etc.

## Customization

### Change the operating-point threshold

Edit `run_l1.py`, line ~140:

```python
best_threshold = 0.40  # ← change here
```

Re-run: `python3 run_l1.py`

The script will re-evaluate only the selected threshold (cached labelset, no re-billing).

### Add new reasoning keywords

Edit `run_l1.py`, lines ~75–82 in `_compute_features()`:

```python
reasoning_cues = [
    "how many", "many ways", ..., "new_keyword_here"
]
```

Re-run to see the impact on scores.

### Evaluate over a different suite

The heuristic uses `tasks.ALL` (45 items) from the harness. To evaluate over a subset:

```python
# In run_l1.py, around line ~170:
items = [it for it in items if it["difficulty"] == "hard"]  # only hard items
```

Re-run with the filtered suite.

## Reproducibility

The heuristic is **fully deterministic**:
- No random sampling (temperature=0 on cached calls)
- No ML training
- Same features, weights, threshold → same routing decision

Results are reproducible across runs (assuming same labelset).

## For debugging

Enable verbose output during suite evaluation:

```python
# In run_l1.py, around line ~180:
final_res = run_suite(final_router, items, verbose=True)  # ← add verbose=True
```

This prints each item's routing decision and correctness.

---

**Next step**: Once satisfied with the heuristic, move to L2 (embedding-based kNN router) or
L2b (trained classifier) to approach the oracle frontier more closely.
