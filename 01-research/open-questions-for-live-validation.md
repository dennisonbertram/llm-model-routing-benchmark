# Open Questions for Live Validation

**Target**: Model Routing — LLM/model selection for cost-efficient agent inference
**Status**: Pre-POC — these questions can only be answered by running against the real APIs.
**Instructions**: When a POC resolves a question, log the confirmed answer + request ID evidence in `04-logs/live-evidence-ledger.md`. Update this file with `[RESOLVED: <answer> — request-<id> <date>]`.

Each question is mapped to the POC that will answer it.

---

## L0 — Smoke and Harness

**Q1. Are all spec model IDs currently available?**

The spec lists: `gpt-4.1-nano`, `gpt-4.1-mini`, `gpt-4o-mini`, `gpt-4o`, `gpt-4.1`, `gpt-5-mini`, `gpt-5`; `claude-haiku-4-5-20251001`, `claude-sonnet-4-5-20250929`, `claude-sonnet-4-6`, `claude-opus-4-8`; `grok-4.3`.

Call `GET /v1/models` (or equivalent) for each provider and confirm every model ID is listed. Some snapshot IDs may have been deprecated between spec authoring and POC run.

*Validate in*: L0 startup check. Record which models are available, which return 404/400, and the date.

**Q2. Does grok-4.3 accept `temperature` or return an error?**

xAI is OpenAI-compatible, but grok-4.3 always generates reasoning tokens. It is unclear whether the `temperature` parameter is accepted, silently ignored, or causes a 400 error. The harness's `_is_reasoning_model()` function should branch on this.

*Validate in*: L0 smoke. Call `grok-4.3` with `temperature=0.0` and `temperature=0.7`; observe response vs. error. Record the exact error message if applicable.

**Q3. Where exactly does `cost_in_usd_ticks` appear in the xAI response?**

Docs state it is in the `usage` object of chat completions. Confirm the exact JSON path (e.g. `response.usage.cost_in_usd_ticks` vs. `response.usage["cost_in_usd_ticks"]`) and that it is present on a simple non-streaming call.

*Validate in*: L0 smoke. Log the full `usage` object from the first grok-4.3 call. Record the ticks value and USD conversion.

**Q4. Exact token field names in Anthropic vs OpenAI responses**

OpenAI uses `usage.prompt_tokens` / `usage.completion_tokens`. Anthropic native uses `usage.input_tokens` / `usage.output_tokens`. Confirm the harness `providers.py` extracts both correctly and that the normalised `prompt_tokens` / `completion_tokens` fields in `RoutingRecord` are populated correctly for all three providers.

*Validate in*: L0. Call each provider with a known short prompt and confirm token counts are plausible (e.g. "Say hello" ≈ 3–5 tokens).

**Q5. What is the baseline cost+accuracy for always-cheap vs always-strong?**

The Pareto comparison requires concrete anchor points. These are not knowable from research — they depend on which models are in the pool and what the harness task suite contains.

*Validate in*: L0 full suite run. Record: always-cheap (gpt-4.1-nano) accuracy, total USD, $/correct; always-strong (gpt-4.1 or claude-opus-4-8) accuracy, total USD, $/correct. These become the axis anchors for all subsequent Pareto plots.

---

## L1 — Heuristic Router

**Q6. Do heuristic features (prompt length, keyword match) actually predict difficulty for the harness suite?**

Heuristic routing assumes that longer or keyword-rich prompts are harder and deserve a strong model. This may or may not be true for the specific items in the harness coding/math/qa suites.

*Validate in*: L1. After running L1, compute Spearman correlation between the heuristic difficulty score and the actual correct/incorrect outcome from each model. If correlation is near zero, the heuristic is not predictive for this suite — report this plainly.

**Q7. Does the heuristic router land between the two baselines on the Pareto plot?**

RouterBench found many learned routers fail to significantly outperform the best single model. A heuristic router that performs *worse* than always-cheap is a valid negative result worth reporting.

*Validate in*: L1. Compare (accuracy, total_usd) to the L0 baselines. If the heuristic underperforms always-cheap, report why (e.g., over-routing to strong on easy items).

---

## L2 — Embedding kNN Router

**Q8. What is the optimal k and similarity threshold for the kNN router on this suite?**

RouterBench found the optimal kNN configuration was 40 neighbors with the `all-MiniLM-L12-v2` embedding model. Our setup uses `text-embedding-3-small` (OpenAI). The optimal k for a 12-item training set will be very small (k=1 to k=5). The right k is empirical.

*Validate in*: L2. Sweep k ∈ {1, 3, 5} and measure accuracy on the eval split. Record the best k and the corresponding (accuracy, total_usd) point.

**Q9. How much does the labelling cost for the kNN training set?**

Building the kNN training set requires running both the cheap and strong models on all training items to generate labels. This is a one-time cost that should be recorded in the evidence ledger — it is a real sunk cost of deploying this router.

*Validate in*: L2. Record: training set size, cost to label training set (total USD for both models), plus the per-query cost at inference time.

---

## L2b — Classifier Router

**Q10. Does a logistic regression on embedding features produce a usable Pareto curve?**

RouteLLM showed that trained classifiers can achieve strong routing with limited training data. However, with ~12 training items (our split), the classifier may not have enough signal to generalise.

*Validate in*: L2b. Sweep the decision threshold from 0.1 to 0.9 in steps of 0.1 and plot (cost, accuracy). If the curve degenerates (flat, or dominated by always-cheap), report this honestly with the training set size as context.

**Q11. Does the classifier show transfer to held-out items from a different discipline?**

LLMRouterBench found that "out-of-domain experiments showed predictive routers struggle with task transfer." Test whether a classifier trained on coding items routes math items better than random.

*Validate in*: L2b (optional, time permitting). Train on coding suite, evaluate on math suite. Report accuracy.

---

## L3a — FrugalGPT Cascade

**Q12. What verifier confidence threshold minimises cascade depth while maintaining accuracy?**

The cascade verifier (LLM-judge or self-scored) decides when to escalate to the next model. RouterBench found cascading routers with verifier error rate >0.2 deteriorate rapidly. The right threshold is empirical for our model pool and suite.

*Validate in*: L3a. Sweep verifier threshold ∈ {0.3, 0.5, 0.7, 0.9}. For each threshold, record: mean cascade steps, accuracy, total USD. Plot the tradeoff.

**Q13. Does the cascade actually reduce cost vs always-strong at matched accuracy?**

FrugalGPT claimed up to 98% cost reduction at matched GPT-4 performance on their benchmarks (paper's claim, not reproduced here). Our model pool and suite may show a smaller or larger effect. The question is purely empirical.

*Validate in*: L3a. Report the observed cost reduction (or increase) at the threshold that best matches always-strong accuracy. If the cascade does not reduce cost, report that finding and the reason (e.g., verifier calls are themselves expensive).

**Q14. What is the verifier's own cost overhead?**

LLM-judge calls for the cascade verifier use a strong model. On a 12-item suite with 2 cascade steps each, that's 24 judge calls. Record the total verifier cost separately from the cascade model calls.

*Validate in*: L3a. In the routing record, log `verifier_usd` separately. Report: cascade model cost vs verifier cost as fractions of total cascade cost.

---

## L3b — Harness Routing (Coding Agent)

**Q15. Which coding agent steps benefit most from routing to a strong model?**

The opencode-style harness routes each step (plan → edit → fix) to a different model. The question is whether the "fix" step needs a strong model while "plan" can use cheap, or vice versa.

*Validate in*: L3b. Run the agent with: (a) all-strong, (b) all-cheap, (c) routed (plan=cheap, edit=cheap, fix=strong), (d) routed (plan=strong, edit=cheap, fix=cheap). Compare accuracy (unit tests passed) and cost.

**Q16. Does routing the coding agent match all-strong accuracy at lower cost?**

*Validate in*: L3b. Report the configuration that comes closest to all-strong accuracy. Confirm whether there is a configuration that is both cheaper and equally accurate.

---

## L3c — OpenAI-Compatible Gateway Integration

**Q17. Can an unmodified OpenAI SDK client call the router gateway transparently?**

The gateway exposes a `/chat/completions` endpoint that mimics OpenAI's schema. Prove that a client using `openai.OpenAI(base_url="http://localhost:PORT/v1", api_key="dummy")` can call the gateway and receive a correct response without knowing which model was actually used.

*Validate in*: L3c. Run a gateway instance and call it with the stock OpenAI Python SDK. Log the gateway-internal routing decision (which model was selected) and the SDK-side `response.model` field. Confirm they are consistent.

---

## L4 — Routing Gateway Runtime

**Q18. What is the gateway's per-request overhead latency?**

The gateway adds routing logic, HTTP forwarding, and logging overhead vs. calling the model directly. Measure the delta between direct API call latency and gateway-mediated call latency.

*Validate in*: L4. Call gpt-4.1-nano directly 5 times; call it via the gateway 5 times. Report mean latency and standard deviation for each path.

**Q19. Does the JSONL cost ledger persist correctly across gateway restart?**

The gateway writes per-request records to a JSONL file. Confirm that records written before a process restart are readable after restart, and that new records append correctly.

*Validate in*: L4. Write 3 records, restart the gateway process (kill + relaunch), write 3 more. Confirm all 6 records are present in the ledger.

---

## L5 — Failure Modes and Observability

**Q20. What is the exact retry/fallback behaviour when a provider returns HTTP 429?**

The harness should detect 429, wait, and retry or fall back to an alternate model. Confirm the fallback chain fires and the routing record captures `fallback_reason: "rate_limit"`.

*Validate in*: L5. Trigger a rate limit (send many requests rapidly, or use an invalid key that returns 429). Observe and log the full fallback chain.

**Q21. What happens when the cost budget guard trips mid-suite?**

The budget guard should stop the run and write the partial result. Confirm the partial evidence is valid (i.e., the written records are not corrupted) and the `status: budget_exceeded` field is present.

*Validate in*: L5. Set `MAX_RUN_USD=0.001` (intentionally tiny) and run the coding suite. Confirm the guard trips on the first or second item and partial results are valid.

**Q22. Is the fallback chain correctly logged when the first model returns an empty response?**

Some models return HTTP 200 with an empty `choices` array (known failure mode for some providers). The harness must detect this as a failure, not a success.

*Validate in*: L5. Simulate an empty-choices response (mock only the HTTP response parsing layer, not the API call — or use a deliberately malformed request). Confirm `fallback_reason: "empty_response"` is logged.

---

## X1 — Mixture of Agents

**Q23. Do N cheap models proposing answers together beat one strong model on the harness suite?**

This is the headline question of the MoA approach (Wang et al., Together AI). The answer may be task-dependent — MoA may work better for open-ended QA than for precise coding tasks with exact unit-test pass requirements.

*Validate in*: X1. Run MoA with 3 cheap proposers (gpt-4.1-nano × 3) + 1 aggregator (gpt-4.1-mini or claude-haiku). Compare accuracy and cost to always-strong. Report the actual measured outcome — do not assume cheap-MoA wins.

**Q24. What is the cost of running MoA vs a single strong call?**

With 3 proposer calls + 1 aggregator call, MoA uses at minimum 4 API calls per item vs 1. Even if proposers are 10× cheaper than the strong model, the aggregator adds overhead.

*Validate in*: X1. Record total USD per item for MoA vs always-strong. Report the ratio.

---

## X2 — Self-Consistency Vote

**Q25. What k (sample count) gives the best cost-accuracy tradeoff for math tasks?**

Self-consistency samples k completions at temperature>0 and takes a majority vote. Larger k gives more reliable answers but costs k×. The optimal k is the knee of the (cost, accuracy) curve.

*Validate in*: X2. Run math suite with k ∈ {3, 5, 9}. Plot (total_usd, accuracy) and identify the point where additional samples stop improving accuracy.

---

## X3 — Multi-Agent Debate

**Q26. Does debate improve accuracy over a single call?**

Multi-agent debate (Du et al.) has been shown to improve factual accuracy but the effect size on structured tasks (math, coding with unit tests) is unclear.

*Validate in*: X3. Compare debate (2–3 cheap models × 2 rounds) vs single strong call on the QA and math suites. Report accuracy and cost for both.

---

## X4 — Verification Cascade (AutoMix)

**Q27. Is cheap self-verification reliable enough to use as a cascade gate?**

AutoMix uses the cheap model to self-verify its own answer before deciding to escalate. Self-verification is known to be unreliable for the same model that produced the answer (the model is overconfident). Measure the false-accept rate (cheap model says "yes, correct" but the unit test fails).

*Validate in*: X4. Run the cheap model on the coding suite. For each item: record the self-verification score and the actual grade. Compute false-accept rate. Compare to an external LLM-judge verifier's false-accept rate.

---

## X5 — Router Benchmark Pareto

**Q28. Where does each router strategy sit on the Pareto frontier relative to the oracle?**

This is the empirical heart of the degree. The Gap@Oracle (LLMRouterBench metric) for each strategy tells you how far below optimal each approach is.

*Validate in*: X5. Aggregate results from L0–X4. Compute the oracle upper bound. Plot all strategies on the (cost, accuracy) Pareto frontier. Report Gap@Oracle per strategy.

**Q29. Which strategy has the best $/correct at each accuracy level?**

*Validate in*: X5. At accuracy levels 60%, 70%, 80%, 90%, which routing strategy achieves that accuracy at the lowest USD/correct? This is the actionable takeaway for agents choosing a routing strategy.

---

## L-Capstone — Adaptive Routing Gateway

**Q30. Does the combined classifier + cascade + ensemble gateway outperform any individual strategy on the Pareto frontier?**

The capstone combines all strategies. If the capstone does not dominate at least some individual strategies on the Pareto frontier, it means the combination adds overhead without benefit.

*Validate in*: Capstone. Compare capstone (cost, accuracy) point to the frontier from X5. Report whether it lies on, above, or below the frontier. Report the overhead cost of the combination logic itself.

**Q31. Does the cost budget guard fire correctly under realistic load?**

*Validate in*: Capstone. Set a $1.00 per-session budget and run the full test suite. Confirm the guard fires at the right point and the partial result is usable.

---

## Sources

- RouterBench: https://arxiv.org/abs/2403.12031 (Hu et al., ICML 2024)
- LLMRouterBench (Gap@Oracle, ParetoDist): https://arxiv.org/html/2601.07206v1
- RouteLLM: https://arxiv.org/abs/2406.18665 (Ong et al.)
- FrugalGPT: https://arxiv.org/abs/2305.05176 (Chen, Zaharia, Zou)
- Mixture-of-Agents: https://arxiv.org/abs/2406.04692 (Wang et al., Together AI) — verify URL at research time
- AutoMix: https://arxiv.org/abs/2310.12963 (Madaan et al.) — verify URL at research time
- Version compatibility details: see `version-compatibility.md`
- Observability fields: see `observability-model.md`
- Testing methodology: see `testing-model.md`
