# Evidence

Evidence tier: **Live verified** (2026-06-22)

## Live provider calls made

All measurements below are from real OpenAI API calls. No mocks.

### Request 1: auto routing, simple factual question
- Prompt: "What is the capital of France?"
- Routing decision: `default_cheap` (no keywords matched, prompt < 120 words)
- Model used: `gpt-4o-mini`
- Response: "The capital of France is Paris."
- Tokens: 14 prompt, 7 completion, 21 total
- Cost: $0.0000063 (computed: 14/1e6 * $0.15 + 7/1e6 * $0.60)
- Latency: 763ms

### Request 2: auto routing, hard combinatorics question
- Prompt: "How many ways can you arrange 5 items chosen from 8 distinct items using combinatorics?"
- Routing decision: `keyword:combinatorics`
- Model used: `gpt-4.1`
- Response: Begins permutation derivation, correctly identifies it as P(8,5)=6720
- Tokens: 27 prompt, 128 completion (hit max_tokens budget), 155 total
- Cost: $0.001078 (computed: 27/1e6 * $2.00 + 128/1e6 * $8.00)
- Latency: 1700ms

### Request 3: forced model routing
- Prompt: "Say hello briefly."
- model: `gpt-4o-mini` (forced, bypasses heuristics)
- Routing decision: `forced`
- Model used: `gpt-4o-mini`
- Response: "Hello!"
- Tokens: 11 prompt, 2 completion, 13 total
- Cost: $0.0000029
- Latency: 608ms

## Ledger file
Persisted at `source/cost-ledger.jsonl`. Three lines from the primary demo run:

```
{"ts": "2026-06-22T03:48:57Z", "decision": "default_cheap", "chosen_model": "gpt-4o-mini", "prompt_tokens": 14, "completion_tokens": 7, "usd": 6.3e-06, "latency_ms": 763}
{"ts": "2026-06-22T03:48:59Z", "decision": "keyword:combinatorics", "chosen_model": "gpt-4.1", "prompt_tokens": 27, "completion_tokens": 128, "usd": 0.001078, "latency_ms": 1700}
{"ts": "2026-06-22T03:48:59Z", "decision": "forced", "chosen_model": "gpt-4o-mini", "prompt_tokens": 11, "completion_tokens": 2, "usd": 2.85e-06, "latency_ms": 608}
```

## Unit test results
5/5 pass in ~3 seconds (2 requests per test; cheap + strong + forced model calls made live).
Red output: tests 2-4 error with HTTP 502 (ProviderError propagated), test 5 fails (no ledger written).

## Gateway process separation
The server runs as a background process (separate Python interpreter). Curl operates as an
independent client process. The routing decision, backend call, and ledger write all happen
inside the server process; the curl client only sees the HTTP response.
