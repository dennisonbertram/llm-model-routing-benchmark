# Debugging Playbook — LLM Model Routing

Live verified. Covers: blank responses from reasoning models, routing decisions that
look wrong, cost accounting drift, gate non-discrimination, and classifier collapse.

---

## 1. "Model returns empty string" — reasoning model budget starvation

**Live verified** (L0)

**Symptom:** API returns HTTP 200, but `response["choices"][0]["message"]["content"]`
is `""` or `None`. Finish reason is `"stop"` or `"length"`.

**Cause:** Reasoning model (gpt-5, gpt-5-mini, o-series) consumed all available tokens
on hidden chain-of-thought before emitting visible content. The budget was too small.

**Fix:**
1. Check `is_reasoning_model(model)`. If true, apply `REASONING_FLOOR=2048`.
2. Check if you passed `max_tokens` instead of `max_completion_tokens` — for o-series,
   `max_tokens` may be silently ignored or raise HTTP 400.
3. Check if you passed `temperature` to an o-series model — this returns HTTP 400
   ("temperature is not supported for this model").

```python
def is_reasoning_model(model: str) -> bool:
    return any(k in model for k in ["gpt-5", "o1", "o3", "o4", "o-preview"])

max_tokens = max(requested_tokens, REASONING_FLOOR) if is_reasoning_model(model) else requested_tokens
```

See G-001 and G-002 in `05-distillation/gotchas/`.

---

## 2. "Router always routes to cheap / always routes to strong"

**Live verified** (L2b; L1)

**Symptom:** Logistic classifier sends everything to cheap (or everything to strong)
regardless of the prompt.

**Cause A: Threshold miscalibrated.** The classifier's predicted probabilities cluster
in a narrow range. In L2b, all P(cheap_correct) values fell between 0.74–0.91. A
threshold τ ≤ 0.74 collapses to always-cheap (100% routed cheap); τ ≥ 0.91 collapses
to always-strong.

**Diagnosis:**
```python
# Print the P(cheap_correct) distribution
probs = [router.predict_proba(embed_prompt(p)) for p in test_prompts]
print(f"min: {min(probs):.3f}, max: {max(probs):.3f}, mean: {mean(probs):.3f}")
```

**Fix:** Sweep τ from 0.0 to 1.0 and plot the Pareto curve. The operative range is
where the curve moves — outside that range, the router is collapsed. Set τ within the
operative range.

**Cause B: Class imbalance.** 84% of the training set has `cheap_correct=True`. A
logistic regression will learn the base rate, not the hard boundary. Check: count of
`cheap_correct=False` items in training. If < 10, the classifier has insufficient
negative examples. Add more hard items to the training set or use a calibrated prior.

**Cause C: Embedding similarity does not discriminate.** Hard items look similar to
easy items in embedding space (they share vocabulary). Diagnose by computing the
centroid embedding of hard items and the centroid of easy items, then measuring cosine
distance. If the distance is < 0.05, the features are not discriminative and you need
different features (structural, domain-specific) or a larger labeled set.

---

## 3. "FrugalGPT cascade achieves the same accuracy as always-cheap"

**Live verified** (L3a)

**Symptom:** After building a cheap→strong cascade with a confidence gate, accuracy
equals always-cheap regardless of threshold.

**Cause:** The cheap model returns high confidence (0.9) even when wrong. The gate
cannot distinguish high-confidence-correct from high-confidence-wrong answers.

**Diagnosis:**
```python
# Check confidence values for wrong answers
for item in items:
    answer = cheap_model_call(item)
    correct = item["grade"](answer)
    confidence = ask_confidence(item, answer)
    if not correct:
        print(f"{item['id']}: wrong answer, confidence={confidence}")
```

If all wrong answers have confidence > 0.8, the gate is non-discriminative. Threshold
sweeping will not help.

**Fix options:**
1. Use a trained binary classifier (L2b) instead of self-confidence.
2. Use k=3 independent verification calls (X4, AutoMix) — this provides better signal
   than single-call self-assessment.
3. For coding tasks, use test execution instead of confidence (L3b).
4. Compute structural signals: numeric extraction with a lookup, format validation,
   cross-check with a rule-based verifier.

See A-002 for full documentation.

---

## 4. "Cost numbers differ from expected based on token counts"

**Live verified** (L0)

**Symptom:** Computed `usd = tokens × price` does not match provider billing or
differs between runs on cached inputs.

**Cause A: Reasoning model tokens.** o-series and gpt-5 models bill reasoning tokens
as output tokens. `completion_tokens` in the response may undercount the billed amount.
Use `billed_completion_tokens` from the harness response object (which adds
`completion_tokens_details.reasoning_tokens` if present).

**Cause B: grok-4.3 ticks conversion.** `cost_in_usd_ticks / 1e10` (not 1e9). A
factor-of-10 error makes grok appear 10× cheaper than it is. For grok, use
`native_cost_usd` from the harness response.

**Cause C: Provider-side caching.** Cached prompt tokens may be billed at a discount
(OpenAI automatic prompt caching). Uniform `tokens × price` does not account for
caching discounts — the model's billed amount will be lower. This is expected; document
it as a known difference.

**Cause D: Wrong price table.** The `pricing.py` price table was correct as of
2026-06-21 (reconciled from official pricing pages). Provider prices change; update
`pricing.py` and commit the change with a date and URL. The harness's `usd` field
reflects the table version at run time.

---

## 5. "Embedding call returns wrong dimensionality or fails"

**Live verified** (L2; L2b; capstone)

**Symptom:** `embed(texts)` returns a vector of unexpected length, or raises an error.

**Diagnosis:**
```python
vecs, usd = embed(["test"])
print(f"dims: {len(vecs[0])}, cost: ${usd:.6f}")
# Expected: dims=1536 for text-embedding-3-small
```

**Cause A: Wrong model.** Default is `text-embedding-3-small` (1536 dims). If you
pass `text-embedding-3-large`, you get 3072 dims. Make sure the router's stored
training embeddings and live-query embeddings use the same model.

**Cause B: numpy 2.0 matmul warning.** `numpy 2.0.x` on macOS emits a spurious
"divide by zero in matmul" warning on clean normalized float64 matrices. Use `np.dot`
instead of `@` for cosine similarity to suppress the warning. The numerical result
is identical. (Discovered in L2 `surprises.md`.)

**Cause C: Missing OPENAI_API_KEY.** The embedding endpoint is OpenAI. Without a key,
`embed()` raises `ProviderError: Missing env var OPENAI_API_KEY`. This is the RED state.

---

## 6. "Gateway returns HTTP 502 on first request"

**Live verified** (L4; L5)

**Symptom:** The routing gateway starts, health check passes, but the first
`/v1/chat/completions` request returns HTTP 502.

**Cause:** API credentials are not loaded in the gateway process's environment. The
gateway server process reads env vars at startup — if credentials were not set before
starting the server, the underlying provider call fails.

**Fix:**
```bash
# Load credentials BEFORE starting the server
set -a; . .agent-university/secrets.local.env; set +a
python3 gateway_server.py 8137 &
```

Verify the gateway has credentials with a smoke curl:
```bash
curl -s localhost:8137/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":4}'
# Should return non-empty choices[0].message.content and x_routing.usd > 0
```

The L4 test suite confirms: health check (`test_01_health`) passes even without
credentials; routing tests (`test_02–test_05`) require credentials.

---

## Evidence

- L0 README.md surprises: "Reasoning models silently return empty text under a tight budget." (Live verified)
- L2b README.md: "P(cheap_correct) clusters high... effective decision range is narrow (τ ∈ [0.75, 0.90])." (Live verified)
- L3a README.md: confidence probe table showing all wrong-math items at conf=0.9. (Live verified)
- L2 surprises.md: "numpy 2.0.2 `@` operator triggers a spurious divide-by-zero warning on 22×23 float64 normalized matrices. `np.dot` is clean." (Live verified)
- L4 README.md: "RED = HTTP 502 missing key." (Live verified)
- results-digest.md Gotchas 1–3: reasoning floor, o-series params, grok billing. (Live verified)
