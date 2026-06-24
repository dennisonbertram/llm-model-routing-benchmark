# Evidence — L3c OpenAI-Compatible Gateway Integration

**Evidence tier: Live verified (2026-06-22)**

## Live evidence

All numbers below come from the captured run in `source/green-output.txt` and
`source/l3c_evidence.json`. No mocks.

### Wire test results (live, 2026-06-22)

| Test | Request model | Model served | Tokens (p/c/total) | USD | Latency |
|---|---|---|---|---|---|
| cheap route — "What is the capital of France?" | `auto` | `gpt-4o-mini` | 14/7/21 | $6.30e-06 | 1010 ms |
| strong route — combinatorics problem | `auto` | `gpt-4.1` | 31/328/359 | $0.002686 | 3042 ms |
| passthrough — explicit `gpt-4.1-nano` | `gpt-4.1-nano` | `gpt-4.1-nano` | 15/4/19 | $3.10e-06 | 957 ms |

### openai Python SDK live evidence

```
openai SDK used: True
result: model=gpt-4o-mini content='The capital of France is Paris.'
```

The `openai.OpenAI(base_url="http://127.0.0.1:8770/v1", api_key="x")` call completed
successfully against the gateway, which in turn called the real OpenAI API.

### Test suite result

```
Ran 10 tests in 8.981s
OK
```
- 4 offline heuristic routing tests: all pass
- 6 live wire-format tests: all pass

### Heuristic routing unit test results (offline, no API call)

```
[PASS] cheap — factual/short    expected='gpt-4o-mini'  got='gpt-4o-mini'
[PASS] cheap — coding task      expected='gpt-4o-mini'  got='gpt-4o-mini'
[PASS] strong — combinatorics   expected='gpt-4.1'      got='gpt-4.1'
[PASS] strong — proof/reasoning expected='gpt-4.1'      got='gpt-4.1'
```

## RED evidence

Without API keys loaded, the gateway starts normally but upstream calls fail with HTTP 502
(the gateway catches `ProviderError: Missing env var OPENAI_API_KEY` and returns 502 to
the client). The 4 offline heuristic tests still pass. Full traceback in `source/red-output.txt`.

## Provenance

- `source/gateway.py` — gateway implementation (stdlib only, no pip installs)
- `source/run_l3c.py` — integration run script
- `source/test_l3c.py` — behavioral tests
- `source/green-output.txt` — captured live run output
- `source/red-output.txt` — captured failing run (no keys)
- `source/l3c_evidence.json` — structured evidence JSON with per-request costs/latencies
