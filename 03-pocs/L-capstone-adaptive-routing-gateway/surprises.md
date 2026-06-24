# Surprises (live)

1. **A logistic classifier trained on 36 examples is enough to run the gateway near-oracle.**
   The adaptive gateway hits strong-model accuracy (0.978) at 8.4x lower cost, 1.14x the oracle —
   from a numpy logistic regression over embeddings, no fine-tuning, no external router service.

2. **The budget guard only matters when per-call cost is real.** Our answers are short, so a
   gpt-4.1 call here is ~$0.0001; we had to set a $0.00025 cap (≈2 strong calls) to demonstrate
   the guard tripping. In production with long outputs the cap matters far sooner — the guard is a
   spend ceiling, not an accuracy control.

3. **Fallback turns a hard failure into a soft degrade.** Pointing the strong route at a bad model
   slug produced a real provider 404; the gateway fell back to gpt-4o-mini and still answered
   (`fallback_from=yes`) — the request succeeded at lower quality instead of erroring.

4. **`{model:"auto"}` is a clean integration seam.** Any OpenAI-compatible client can keep its code
   and just point `base_url` at the gateway; the routing decision rides back in a non-standard
   `x_routing_decision` field, so observability does not break wire compatibility.
