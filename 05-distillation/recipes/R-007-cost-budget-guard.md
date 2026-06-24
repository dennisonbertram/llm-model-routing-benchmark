# R-007: Cost-Budget Guard

**Category**: recipe
**Evidence tier**: Live verified (POCs L5, L-capstone)
**Source POCs**: L5-failure-modes-and-observability, L-capstone-adaptive-routing-gateway

## Live verified

A per-session USD budget guard that tracks cumulative spend and refuses (or forces cheap)
once the cap is reached.

Live verified (L5): budget=$0.000015, 4 calls attempted.

| Task | Decision         | Model       | USD spent  | Running total | Remaining budget |
|------|------------------|-------------|------------|---------------|------------------|
| b1   | accepted         | gpt-4o-mini | $4.05e-06  | $4.05e-06     | $0.0000150       |
| b2   | accepted         | gpt-4o-mini | $3.75e-06  | $7.80e-06     | $0.0000150       |
| b3   | accepted         | gpt-4o-mini | $3.60e-06  | $1.14e-05     | $0.0000150       |
| b4   | **refused**      | —           | —          | $1.14e-05     | $3.60e-06 (too small for any model) |

The guard correctly refused b4 because even gpt-4o-mini ($3.75e-06) would have exceeded the
$3.60e-06 remaining. Both gpt-4o-mini and gpt-4.1 were tried before refusing. (L5)

Live verified (capstone): with a $0.00025 cap, requests 1–4 route normally to gpt-4.1 (strong);
requests 5–6 are forced to gpt-4o-mini (cheap) by the budget guard
(`decision=budget_guard(spent=$0.0003>=cap)`). (L-capstone)

**Note**: the guard only bites when per-call costs are real. Short factual answers cost
~$3–4e-06 each, so a $0.000015 cap is consumed in ~3–4 calls. Size the cap to your
batch size (results-digest.md gotcha #8).

## Snippet (copy-paste-ready)

```python
from providers import chat

class BudgetGuard:
    """
    Wraps a router and enforces a per-session USD cap.
    When the budget is exceeded, falls back to cheap or refuses entirely.
    """

    def __init__(
        self,
        cap_usd:      float,
        cheap_model:  str = "gpt-4o-mini",
        strong_model: str = "gpt-4.1",
        refuse_on_exhaustion: bool = False,
    ):
        self.cap_usd             = cap_usd
        self.cheap_model         = cheap_model
        self.strong_model        = strong_model
        self.refuse_on_exhaustion = refuse_on_exhaustion
        self.spent_usd           = 0.0
        self.log                 = []

    def _estimate_cost(self, model: str, prompt_tokens: int = 50) -> float:
        """Quick estimate before the call; exact cost is measured after."""
        from pricing import usd_for
        # Assume output ≈ 60 tokens for short tasks
        return usd_for(model, prompt_tokens, 60)

    def call(
        self,
        intended_model: str,
        messages: list[dict],
        **kwargs,
    ) -> dict | None:
        """
        Attempts to call intended_model within budget.
        Falls back to cheap model if strong would exceed budget.
        Returns None if budget is exhausted and refuse_on_exhaustion is True.
        """
        remaining = self.cap_usd - self.spent_usd

        # Try intended model
        for model in [intended_model, self.cheap_model]:
            if model == intended_model and model == self.cheap_model:
                # only one candidate
                candidates = [model]
            else:
                candidates = [model]

            est = self._estimate_cost(model)
            if est > remaining:
                self.log.append({
                    "decision":   "downgraded",
                    "reason":     "would_exceed_budget",
                    "attempted_model": model,
                    "attempted_usd":   est,
                    "remaining_usd":   remaining,
                })
                continue

            # Make the real call and measure actual cost
            result = chat(model, messages, **kwargs)
            if result.usd > remaining:
                # real cost exceeded estimate — still refuse
                self.log.append({
                    "decision":   "refused_post_call",
                    "model":      model,
                    "actual_usd": result.usd,
                    "remaining":  remaining,
                })
                continue

            self.spent_usd += result.usd
            self.log.append({
                "decision":    "accepted",
                "model":       model,
                "usd":         result.usd,
                "spent_total": self.spent_usd,
            })
            return {"text": result.text, "model": model, "usd": result.usd}

        if self.refuse_on_exhaustion:
            self.log.append({"decision": "refused", "reason": "no_model_fits_budget"})
            return None
        # Default: force cheapest model anyway (no guard trip)
        result = chat(self.cheap_model, messages, **kwargs)
        self.spent_usd += result.usd
        return {"text": result.text, "model": self.cheap_model, "usd": result.usd,
                "decision": "budget_guard_forced_cheap"}
```

## Integration with the gateway

```python
# In the gateway handler, wrap the router call:
guard = BudgetGuard(cap_usd=0.001, refuse_on_exhaustion=False)

def handle_request(messages, requested_model="auto"):
    model, decision = route(messages, requested_model)  # any router
    result = guard.call(model, messages)
    if result is None:
        return {"error": "budget_exhausted"}, 402
    # append to JSONL ledger
    with open("cost-ledger.jsonl", "a") as f:
        f.write(json.dumps({
            "ts":         datetime.utcnow().isoformat(),
            "decision":   decision,
            "model":      result["model"],
            "usd":        result["usd"],
            "spent_total": guard.spent_usd,
        }) + "\n")
    return result
```

## Observability log fields (live format, L5)

Each routing decision emits a structured JSON log. Never log the API key value.

```json
{
  "ts":               "23:49:48",
  "event":            "budget_guard",
  "task":             "b4",
  "decision":         "refused",
  "reason":           "no_model_fits_budget",
  "attempted_model":  "gpt-4.1",
  "attempted_usd":    5e-05,
  "remaining_usd":    3.6e-06
}
```

Required fields: `ts`, `event`, `model`, `outcome`, `tokens_prompt`, `tokens_completion`,
`usd`, `latency_ms`, `decision`, `budget_usd`, `spent_total`. No API key, no raw credential. (L5)

## Evidence

- L5-failure-modes-and-observability/README.md — FM4 budget guard detail, live log excerpt
- L-capstone-adaptive-routing-gateway/README.md — capstone budget guard demo ($0.00025 cap)
- results-digest.md lines 28–29, 51 — live budget guard behavior
