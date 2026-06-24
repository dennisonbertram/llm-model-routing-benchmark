# S4 — Fugu vs our router, head-to-head (falsification-tested)

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

A clean, apples-to-apples, **falsification-oriented** comparison: **15 fresh, deterministically-graded
tasks** (not reused from S0–S3; math golds computed by brute force, coding tests validated, QA exact-match)
run through every system with identical graders and identical cost accounting (uniform token×price; Fugu's
orchestration tokens billed at its real $5/$30 rate). Routers decide from the **prompt only**; the
classifier is trained on the **old** 45-task suite and applied to these **new** tasks (leakage-free, verified
0 prompt overlap). This experiment exists to try to **break** the claim "our routing is cheaper than Fugu."

## Results (15 identical tasks)

| system | accuracy | $/task | total $ | mean latency |
|---|---|---|---|---|
| always gpt-4o-mini (cheap) | 0.733 | $0.00003 | $0.0005 | 1.6 s |
| always gpt-5.5 (frontier) | **1.000** | $0.00191 | $0.0287 | 2.5 s |
| fugu (mini) | **1.000** | $0.01497 | $0.2246 | 5.9 s |
| **fugu-ultra (conductor)** | **1.000** | **$0.04261** | $0.6392 | 20.2 s |
| **router: heuristic** (prompt cues) | **1.000** | **$0.00135** | $0.0202 | 2.1 s |
| **router: classifier** (trained on old suite) | **1.000** | **$0.00145** | $0.0217 | 2.2 s |

## Falsification checks — the claim survived all of them

- **Fugu-ultra cheaper than a single gpt-5.5 call on any task?** 0/15. Never.
- **Fugu (mini or ultra) more accurate than gpt-5.5 on any task?** 0/15. It never beat a single frontier call.
- **Do the routers MATCH accuracy (not trade it for cost)?** Yes — both 15/15. Every model a router chose was
  correct on its task; there is no accuracy-for-cost trade here. (Cheap-alone would be 0.733 — it fails the 4
  hard-math items v_h1/v_h2/v_h5/v_h6; the routers correctly escalate those to gpt-5.5.)
- **Is "~30×" an average dragged by one outlier?** The aggregate is honest: fugu-ultra is **31.7×** the
  heuristic router and **29.4×** the classifier router. (Per-task ratios range wildly — median ~40–56×, max
  15,489× on a trivial QA item — so we quote the **aggregate ~30×**, not the cherry-picked max.)
- **Cost methodology fair to Fugu?** Yes. Fugu-ultra is billed at the *same* $5/$30 per-token rate as gpt-5.5;
  the gap is entirely Fugu's own orchestration tokens (~83% of its bill). Even counting **only** Fugu's visible
  answer tokens (stripping all orchestration), fugu-ultra is still **3.7×** a single gpt-5.5 call.

## The honest claim (what is safe to say)

> On 15 solvable tasks, a trivial prompt-only **router matched Fugu-Ultra's accuracy (15/15) at ~30× lower
> cost and ~10× lower latency** — and **even a single GPT-5.5 call matched it at ~22× lower cost.** On these
> tasks, Fugu's orchestration tokens (≈83% of its bill) bought **no** extra accuracy.

Two honesty points the evidence forces:
1. **Most of the win is "don't pay for orchestration you don't need," not router cleverness.** A single
   gpt-5.5 call is already ~22× cheaper than fugu-ultra at the same 15/15; the router adds only ~1.3–1.4× on
   top (by sending the easy majority to a cheap model). The headline is *Fugu's orchestration didn't earn its
   cost here*, with routing as the cherry on top.
2. **This is "cheaper at matched accuracy," NOT "better."** Nothing here *beat* a single frontier call — all
   15 tasks are within GPT-5.5's capability. On genuinely frontier-hard tasks (where one strong call fails),
   Fugu's orchestration could plausibly earn its cost — untested here, and the honest limit of this result.

## Caveats (mandatory)
n = 15, single run, mostly math; deterministic graders; tasks within frontier capability. `fugu-mini`'s rate
is an estimate; gpt-5.5's $5/$30 is a list-price estimate. "~30×" is vs `fugu-ultra` specifically. This is a
directional demonstration, not a publication-scale benchmark.

## Run it
```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 headtohead.py   # -> headtohead_results.json (per-task ok/usd/lat for every system)
```
