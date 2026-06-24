# Error Log

Live errors discovered and resolved during POC execution (2026-06-21/22).

---

## E-1: Reasoning model returns empty text under small token budget

- **POC**: L0-smoke-and-harness
- **Error**: `gpt-5-mini` smoke call returned `text=""` with `finish_reason=length`
- **Context**: `max_completion_tokens=16` was the harness default for provider smoke checks
- **Root cause**: gpt-5-mini spends reasoning tokens internally before emitting visible content;
  16 tokens are consumed by reasoning with 0 remaining for output text
- **Fix**: Added `REASONING_FLOOR=2048` constant to harness; provider dispatch branches on model
  family; o-series / gpt-5 use `max_completion_tokens` (not `max_tokens`) + no custom `temperature`
- **Regression**: `test_l0.py` asserts `len(text) > 0` for all provider smokes; would catch regression
- **Skill-pack implication**: gotcha G-001 "reasoning-empty-text-under-small-budget"

---

## E-2: grok-4.x ticks / 1e9 gives implausible cost

- **POC**: L0-smoke-and-harness
- **Error**: `cost_in_usd_ticks / 1e9` for a grok-4.3 call returned `~1.06e-12 USD` (impossible)
- **Context**: Initial assumption was nanoUSD (9 decimal places), common for IoT/billing APIs
- **Root cause**: xAI uses 10 decimal places (1 tick = $1e-10). Correct formula: `/ 1e10`
- **Fix**: Updated `pricing.py` grok branch to `native_cost_usd = cost_in_usd_ticks / 1e10`
- **Regression**: L0 evidence.md records the live $1.06e-03 for grok-4.3 smoke — cross-check
  against any future grok calls
- **Skill-pack implication**: gotcha G-002 "grok-ticks-conversion-is-1e10"

---

## E-3: numpy 2.0 spurious divide-by-zero warning on matrix multiply

- **POC**: L2-embedding-knn-router
- **Error**: `RuntimeWarning: divide by zero encountered in matmul` on normalized embedding dot product
- **Context**: `Q_norm @ T_norm.T` for 22×1536 @ 1536×23 matrices; inputs are valid float64
- **Root cause**: numpy 2.0 internal broadcasting path fires a spurious warning for large float64
  matrices; actual values are not zero or infinite
- **Fix**: Replace `Q_norm @ T_norm.T` with `np.dot(Q_norm, T_norm.T)` (numerically identical;
  avoids the triggering path)
- **Regression**: Test suite confirms cosine similarities are in [−1, 1] (test_cosine_similarity_range)
- **Skill-pack implication**: gotcha "suppress-numpy-2-matmul-warning"

---

## E-4: Port already in use — OSError 48 from prior test run's TIME_WAIT

- **POC**: L3c-openai-compatible-gateway-integration, L4-routing-gateway-runtime
- **Error**: `OSError: [Errno 48] Address already in use` when starting a new gateway server
- **Context**: A prior test run had used port 8765; OS TIME_WAIT state held the port for ~2 minutes
- **Root cause**: TCP TIME_WAIT prevents immediate reuse of the same (IP, port) pair after a
  connection is closed. The test suite and the run script both tried to bind port 8765.
- **Fix**: L3c test suite uses port 8766; L3c run script uses port 8770. L4 run script kills
  any prior server on the target port before starting a new one.
- **Regression**: Tests bind explicit ports; no dynamic allocation. Port 8770/8766 documented.
- **Skill-pack implication**: recipe "gateway-server-port-reuse-guard"

---

## E-5: Python 3.9 rejects f-string dict-lookup expressions

- **POC**: L4-routing-gateway-runtime
- **Error**: `SyntaxError: f-string: expecting '}'` for ledger display code
- **Context**: Shell-embedded Python used `f"  {'ts':24}  {'decision':20}  ..."` (Python 3.12 syntax)
- **Root cause**: f-string support for quote-matched expressions inside `{}` was added in Python 3.12.
  The system Python on macOS 14 is 3.9.
- **Fix**: Replace f-string with `.format()` for all ledger display code
- **Regression**: All harness/POC code runs under Python 3.9; stdlib-only requirement enforced
- **Skill-pack implication**: "python-3-9-fstring-compatibility" caution in recipes

---

## E-6: L3a gate calls inflate cost with no accuracy gain (cascade design error)

- **POC**: L3a-frugalgpt-cascade
- **Error**: Cascade cost $0.00391 = 2.4× always-cheap at NO accuracy improvement
- **Context**: The FrugalGPT gate (confidence self-report) was expected to discriminate hard items
- **Root cause**: gpt-4o-mini reports confidence=0.9 for all 6 hard-math wrong answers.
  The gate calls themselves (~52 calls to gpt-4o-mini) each cost ~$0.00001–0.00003; those
  27+18=45 gate calls dominate the overhead even though only 4 items are escalated.
- **Fix**: No code fix — this is a documented HONEST NEGATIVE. The gate was correctly implemented;
  the failure is in the pattern's assumption about cheap-model calibration on this workload.
- **Lesson**: Gate overhead is paid unconditionally. If the gate has zero discriminative power,
  cascade = always-cheap + gate_cost (worse than always-cheap).
- **Skill-pack implication**: anti-pattern "frugalgpt-gate-requires-calibration-check"

---

## E-7: Gateway health probe passes without valid API credentials

- **POC**: L4-routing-gateway-runtime
- **Error**: `GET /v1/health` returns 200 OK even when OPENAI_API_KEY is unset or invalid
- **Context**: Container readiness probes using `/v1/health` would falsely report ready
- **Root cause**: The health endpoint does not make a live provider call — it just checks that
  the server process is running. API key validity is only checked when a model call is attempted.
- **Fix**: Documented in surprises.md. A production deployment needs a separate "canary" request
  (a cheap model call) in addition to the health check, not just a health-check ping.
- **Skill-pack implication**: recipe "production-gateway-canary-request"
