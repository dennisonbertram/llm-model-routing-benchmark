# S3 — Real Sakana Fugu vs GPT-5.5 (live, head-to-head)

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

With an active Sakana subscription we ran **the real Fugu** — `fugu` (Mini) and `fugu-ultra` (the
multi-agent conductor) — against **GPT-5.5**, on the same 21 authored hard tasks GPT-5.5 solved 21/21
in S0, with the same deterministic graders. The harness folds Fugu's **orchestration tokens** into the
billed cost (`fugu-ultra` = $5/$30 per 1M, billed on ALL tokens including orchestration), so cost is
the true price of the multi-agent machinery.

## Live results (21 hard tasks: 11 math, 4 coding, 6 trap-QA)

| model | accuracy | $/task | mean latency | orchestration tokens/task |
|---|---|---|---|---|
| **gpt-5.5 (single call)** | **1.000** | **$0.0097** | **8.1 s** | 0 |
| `fugu` (Mini conductor) | 0.905 | $0.039 (4.0×) | 12.7 s | 0 |
| `fugu-ultra` (full conductor) | **1.000** | $0.119 (**12.2×**) | 45.4 s | **7,719** |

(API: OpenAI-compatible at `https://api.sakana.ai/v1`; models `fugu`, `fugu-ultra`. Auth via
`SAKANA_API_KEY`, gitignored. Earlier the key listed models but inference returned "No active
subscription" — now active.)

## What this shows (honest, and fair to Fugu)

1. **`fugu-ultra` matches the frontier on accuracy (1.000)** — it solves every task GPT-5.5 does.
   (Two items first hit our 120 s read-timeout — the conductor is slow — and only passed once the
   timeout was raised to 300 s; the 0.905 in an earlier run was a timeout artifact, corrected here.)
2. **But it is a 12.2× cost and 5.6× latency multiplier for the *same* answer**, because the
   multi-agent conductor burns **~7,700 orchestration tokens per query** (visible answer tokens are a
   tiny fraction). On tasks a single frontier model already solves, that orchestration is pure overhead.
3. **`fugu` (Mini) is the worst of both worlds here:** *lower* accuracy (0.905 — it genuinely missed two
   hard-math items, hm3 & hm9) at *4× the cost* of one GPT-5.5 call.
4. This mirrors S2 exactly from the opposite end of the pool: there, adaptive search over *cheap* models
   couldn't beat the frontier; here, an adaptive conductor over *frontier* models can only *match* it, at
   a large cost/latency premium. **Orchestration is a cost/latency multiplier, not a free accuracy win.**

## When IS orchestration worth it?

Per Sakana's own benchmarks (cited, not reproduced here — `01-research`/`.context/sakana/`), Fugu-Ultra's
*wins* over single frontier models are **sub-1-point** and only on the genuine capability frontier
(GPQA-Diamond, ARC-AGI-2, SWE-bench Pro) — tasks no single model solves outright. Our suite (and most
practical tasks) live well below that frontier, where **routing to the right single model dominates** on
cost, latency, and accuracy. Orchestration earns its premium only when a single model *cannot* solve the
task at all and a verifier/diverse-pool can find a solution none finds alone (the AB-MCTS ARC result).

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 run_fugu.py   # -> fugu_results.json ; redacted evidence in source/evidence.txt
```
