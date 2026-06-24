# Commands — X1 Mixture-of-Agents

All commands run from the repo root (`agent-university/nashville`).

## Load credentials

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run behavioral tests (RED — no keys, cache bypassed)

The warm cache would serve every call even with no keys, so the cache must be
temporarily absent to reproduce the red state:

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source
mv .cache.json .cache.json.bak
OPENAI_API_KEY="" ANTHROPIC_API_KEY="" python3 test_x1.py
# → FAILED (errors=3) — ProviderError: Missing env var OPENAI_API_KEY
mv .cache.json.bak .cache.json
```

## Run behavioral tests (GREEN — with keys)

```bash
# From repo root (keys already loaded above):
cd model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source
python3 test_x1.py
# → OK (3 tests, ~3s — hits cache after first run)
```

## Run full suite

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source
python3 run_x1.py
# Takes ~5 minutes, costs ~$0.10 on first run (cached on repeat).
# Writes x1_summary.json with all metrics.
```

## Check summary

```bash
cat model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source/x1_summary.json
```
