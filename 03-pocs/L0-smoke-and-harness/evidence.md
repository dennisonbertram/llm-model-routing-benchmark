# L0 Live Evidence

Status: Complete with live evidence. Evidence strength: Strong.
Captured: 2026-06-21. Live services: OpenAI, Anthropic, xAI. No mocks.

## Provider liveness (real responses)

```
gpt-4o-mini                 -> 'OK'   516ms   $2.40e-06
claude-haiku-4-5-20251001   -> 'OK'  1906ms   $3.20e-05
grok-4.3                    -> 'OK'  5232ms   $1.06e-03
```

## Baseline over the 45-task suite (real per-call grading + cost)

```
always-cheap  (gpt-4o-mini): acc=0.844  cost=$0.00166
always-strong (gpt-4.1    ): acc=0.978  cost=$0.02148   (12.9x cheap)
ORACLE (cheapest-correct)   : acc=0.978  cost=$0.00214   (10% of strong cost, strong-level accuracy)

items only strong solves (6): m9, m10, m12, m13, m14, m15   (all hard math)
items neither solves     (1): m8
cheap is enough for 38/45 tasks
```

Machine-readable copy: `source/l0_summary.json`.

## Tests

- `source/test_l0.py` — Live behavioral test. GREEN: 3/3 pass in 5.4s (`green-output.txt`).
  RED: keys unset → `ProviderError` (`red-output.txt`).
- Assertions are claims about the live world: a real accuracy gap (`strong>cheap`), a real cost
  gap (`strong_cost > 3× cheap_cost`), and oracle headroom (`oracle acc ≥ strong acc` at
  `< 0.5× strong cost`). All hold against the live APIs.

## Claims supported
- Three providers are reachable and metered live.
- A real, measurable cost-quality gap exists; oracle headroom ≈ 10% of strong cost at strong accuracy.
- The gap is concentrated in hard reasoning math; canonical coding saturates cheap models.

## Claims NOT supported (yet)
- That any *implementable* router (no oracle) captures this headroom — that is L1–X5's job.
- Absolute cost for `gpt-5*`/`claude-opus`/`grok` beyond the reconciled core pool (estimates labeled in `pricing.py`).
