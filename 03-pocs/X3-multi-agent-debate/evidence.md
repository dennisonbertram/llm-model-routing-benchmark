# Evidence — X3 Multi-Agent Debate

## Evidence tier: Live verified (2026-06-21)

All numbers in this POC come from real live API calls executed on 2026-06-21.
190 new calls billed (cache misses) + 48 cache hits (re-running test suite over cached calls).
Zero mocks.

## Live call summary

| provider | models used | purpose |
|---|---|---|
| OpenAI | gpt-4o-mini, gpt-4.1-mini, gpt-4.1 | debaters (2/3) + strong baseline + judge |
| Anthropic | claude-haiku-4-5-20251001 | debater (1/3) |

## Measured results (live, 2026-06-21)

### Full suite (23 items)

| router | accuracy | total_usd | cost/correct |
|---|---|---|---|
| always-cheap (gpt-4o-mini) | 0.6957 | $0.000147 | $0.000009 |
| always-strong (gpt-4.1) | 0.9565 | $0.001634 | $0.000074 |
| debate:3x1r | 0.9565 | $0.006278 | $0.000285 |

### Hard math (m9, m10, m12, m13, m14, m15)

| router | accuracy | total_usd |
|---|---|---|
| cheap | 0.000 | $0.000039 |
| strong | 1.000 | $0.000520 |
| debate | 1.000 | $0.001590 |

## Cost breakdown

- Calls per item: 6 (3 debaters × 2 rounds)
- Cost vs cheap: 42.7×
- Cost vs strong: 3.84×
- Cache stats: 190 misses (paid), 48 hits (reused)

## Test results (live behavioral)

All 5 tests in `source/test_x3.py` pass with credentials loaded.
RED state captured: 4 tests fail with `ProviderError: Missing env var OPENAI_API_KEY`.

## Source files

- `source/run_x3.py` — DebateRouter implementation + benchmark
- `source/test_x3.py` — 5 behavioral tests
- `source/x3_summary.json` — machine-readable results (written by run_x3.py live run)
- `source/.cache.json` — 190-entry response cache
- `source/green-output.txt` — captured 5/5 pass
- `source/red-output.txt` — captured 4 errors without keys
