# Command Log

Append one entry per meaningful command (Timestamp / Working directory / Command / Purpose / Expected / Actual / Exit code / Follow-up).

---

## 2026-06-21 — Harness smoke (L0)

- **Dir**: `03-pocs/L0-smoke-and-harness/source/`
- **Command**: `python3 test_l0.py`
- **Purpose**: Verify 3 providers live + baseline accuracy
- **Expected**: 3/3 pass
- **Actual**: 3/3 pass, 5.4s; acc 0.844/0.978, $0.00166/$0.02148
- **Exit**: 0

---

## 2026-06-21 — L1 heuristic router

- **Dir**: `03-pocs/L1-heuristic-router/source/`
- **Command**: `python3 run_l1.py` then `python3 test_l1.py`
- **Purpose**: Threshold sweep + behavioral tests
- **Expected**: Pareto curve between baselines
- **Actual**: τ=0.40 → acc 0.956, $0.00902; tests pass
- **Exit**: 0

---

## 2026-06-21 — L2 embedding k-NN router

- **Dir**: `03-pocs/L2-embedding-knn-router/source/`
- **Command**: `python3 test_l2.py`
- **Purpose**: Live embed call + k-NN accuracy verification
- **Expected**: 6/6 pass; embeddings live
- **Actual**: 6/6 pass, 0.369s; 45 prompts → 1536-dim vectors, ~$0.00003
- **Exit**: 0
- **Note**: numpy 2.0 spurious divide-by-zero warning on matmul suppressed via np.dot

---

## 2026-06-21 — L2b classifier router

- **Dir**: `03-pocs/L2b-classifier-router/source/`
- **Command**: `python3 test_l2b.py`
- **Purpose**: Logistic classifier + live embed confirm
- **Expected**: 6/6 pass; P(cheap) range visible
- **Actual**: 6/6 pass; P range [0.737, 0.907]; τ=0.80 test-set acc=1.000
- **Exit**: 0

---

## 2026-06-21 — L3a FrugalGPT cascade

- **Dir**: `03-pocs/L3a-frugalgpt-cascade/source/`
- **Command**: `python3 run_l3a.py` then `python3 test_l3a.py`
- **Purpose**: Confidence gate + coding verifier + cascade cost
- **Expected**: Cascade accuracy between baselines
- **Actual**: HONEST NEGATIVE — acc=0.844 (= always-cheap) at $0.00391 (all thresholds identical)
- **Exit**: 0
- **Note**: FrugalGPT gate non-discriminative on hard math; coding verifier 18/18 correct

---

## 2026-06-21 — L3b harness routing (coding)

- **Dir**: `03-pocs/L3b-harness-routing-coding-agent/source/`
- **Command**: `python3 test_l3b.py`
- **Purpose**: Cheap-first harness routing on 18 coding tasks
- **Expected**: Escalation on some hard coding tasks
- **Actual**: 4/4 tests pass; 0 escalations — cheap solves all 18; $0.001482 (7.5% strong cost)
- **Exit**: 0

---

## 2026-06-22 — L3c OpenAI-compatible gateway

- **Dir**: `03-pocs/L3c-openai-compatible-gateway-integration/source/`
- **Command**: `python3 run_l3c.py` then `python3 test_l3c.py`
- **Purpose**: Wire-format compatibility + openai SDK integration
- **Expected**: 10/10 tests pass; SDK base_url override works
- **Actual**: 10/10 pass, 8.981s; SDK confirmed; routing decisions exposed in x_routing field
- **Exit**: 0
- **Note**: Port 8765 conflict (TIME_WAIT from test run); switched to 8770/8766

---

## 2026-06-22 — L4 gateway runtime

- **Dir**: `03-pocs/L4-routing-gateway-runtime/source/`
- **Command**: `python3 run_l4.py` (starts server + 3 curl demo requests)
- **Purpose**: Live HTTP gateway with ledger
- **Expected**: 3 routed requests; ledger persisted
- **Actual**: PASS — 3 requests (cheap/strong/forced); cost-ledger.jsonl written
- **Exit**: 0
- **RED**: `python3 run_l4.py` without OPENAI_API_KEY → HTTP 502 confirmed

---

## 2026-06-21 — L5 failure modes

- **Dir**: `03-pocs/L5-failure-modes-and-observability/source/`
- **Command**: `python3 test_l5.py`
- **Purpose**: Trigger 5 safe live failure modes
- **Expected**: 5/5 failure modes handled
- **Actual**: 5/5 pass — invalid slug 404, timeout retry, max_tokens 400, budget guard, verifier
- **Exit**: 0

---

## 2026-06-21 — X1 Mixture-of-Agents

- **Dir**: `03-pocs/X1-mixture-of-agents/source/`
- **Command**: `python3 run_x1.py` then `python3 test_x1.py`
- **Purpose**: MoA vs single strong model on 45 tasks
- **Expected**: MoA may improve accuracy; cost was unknown
- **Actual**: HONEST NEGATIVE — acc=0.956, $0.10159 (4.64× strong AND lower accuracy)
- **Exit**: 0

---

## 2026-06-21 — X2 Self-Consistency Vote

- **Dir**: `03-pocs/X2-self-consistency-vote/source/`
- **Command**: `python3 run_x2.py --variance-test` (then full run)
- **Purpose**: SC@k=1,3,5 on math; stochasticity check
- **Expected**: SC may close some of the cheap→strong gap
- **Actual**: SC@5 math acc=0.600 vs single cheap 0.533 vs strong 0.933; near-zero stochasticity on hard items
- **Exit**: 0

---

## 2026-06-21 — X3 Multi-Agent Debate

- **Dir**: `03-pocs/X3-multi-agent-debate/source/`
- **Command**: `python3 run_x3.py` then `python3 test_x3.py`
- **Purpose**: 3-model debate on 23 items
- **Expected**: Debate may close accuracy gap vs strong
- **Actual**: HONEST NEGATIVE — acc=0.957 (= strong) at $0.006278 (3.84× strong cost)
- **Exit**: 0

---

## 2026-06-21 — X4 AutoMix Verification Cascade

- **Dir**: `03-pocs/X4-verification-cascade-automix/source/`
- **Command**: `python3 run_x4.py` then `python3 test_x4.py`
- **Purpose**: k=3 verifier cascade; threshold sweep
- **Expected**: Beats oracle or approaches it
- **Actual**: acc=0.978 at $0.006092 — 71.6% saving vs always-strong but 2.85× oracle cost
- **Exit**: 0

---

## 2026-06-21 — X5 Router Benchmark Pareto

- **Dir**: `03-pocs/X5-router-benchmark-pareto/source/`
- **Command**: `python3 run_x5.py`
- **Purpose**: Full Pareto frontier across all router types
- **Expected**: Logistic router near oracle; MoA off frontier
- **Actual**: logistic(0.9) = 0.978 @ $0.00291 (7.4× cheaper than strong); MoA 4.7× strong / 47× oracle (dominated)
- **Exit**: 0

---

## 2026-06-21 — L-Capstone Adaptive Gateway

- **Dir**: `03-pocs/L-capstone-adaptive-routing-gateway/source/`
- **Command**: `python3 run_capstone.py` (5-fold CV + gateway demo)
- **Purpose**: Full adaptive gateway benchmark + live curl demo
- **Expected**: Near-oracle accuracy at fraction of strong cost
- **Actual**: adaptive(thr=0.8) acc=0.978, $0.00257 (8.4× cheaper, 1.20× oracle); 3 live curls; budget guard; fallback
- **Exit**: 0
