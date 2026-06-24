# Commands

## Load credentials

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the full cascade sweep

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X4-verification-cascade-automix/source
python3 run_x4.py
```

Prints: live confirmation trace, per-item verifier confidence, calibration stats,
and the threshold sweep table. Writes `x4_summary.json` and caches all verifier
calls in `.cache.json` (own cache — does not touch `harness/.cache/labelset.json`).

## Run the behavioral tests

```bash
python3 -m unittest test_x4 -v
```

4 tests: verifier reachable, cascade accuracy >= 0.97 at T=0.67, cascade cheaper
than strong, calibration (high-conf => correct, low-conf => uncertain).

## Reproduce red state (no keys)

```bash
OPENAI_API_KEY="" python3 run_x4.py
```

Fails with `ProviderError: Missing env var OPENAI_API_KEY` on the first live
strong model call in the confirmation step.
