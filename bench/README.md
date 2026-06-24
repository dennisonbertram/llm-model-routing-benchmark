# Model-combination benchmark (run-all-night)

An outcome-matrix benchmark for **routing/ensemble research**: measure each model once on a task
suite, then evaluate *unlimited* combinations (solo, k-way majority vote, consensus-or-escalate,
oracle) offline → a cost-accuracy leaderboard. Built to run unattended and resume.

## Quick start

```bash
export OPENAI_API_KEY=...  OPENROUTER_API_KEY=...  SAKANA_API_KEY=...   # keys read from the environment
cd bench

python3 refresh_prices.py                                # (optional) sync registry prices to OpenRouter
python3 run.py --suite superhard --limit 8 --budget 1    # fast smoke (8 tasks)

# the real overnight run:
nohup python3 run.py --suite superhard --budget 25 --max-k 4 --timeout 90 > run.log 2>&1 &
```

In the morning read **`leaderboard_superhard.md`** (Pareto frontier + cheapest-config-matching-the-
reference + full table) and `results_superhard.json`. Watch progress: `tail -f run.log`.

## How it works
- **`registry.json`** — the model pool (id, $/1M in/out, tier, enabled). The `reference` model
  (default `gpt-5.5`) is the accuracy bar + the escalation target. Add/disable models here.
- **`matrix.py`** — measures every (model, task) pair *once*, in parallel, with a per-call timeout,
  tolerant of failures (timeout/rate-limit → recorded as wrong, never hangs), flushing
  `matrix_<suite>.json` incrementally. **Resumable**: re-running skips measured pairs (free) and
  only measures new ones — so adding a model to the registry and re-running just fills its column.
  **Budget-capped** (`--budget`, USD): stops measuring when hit; still evaluates what it has.
- **`combos.py`** — offline strategy evaluation over the matrix (no API calls): `solo`, `vote-k`
  (all k-combinations, majority vote on the numeric answer), `consensus-escalate-k` (cheap members
  agree → use; disagree → escalate to the reference), `oracle` (pool ceiling). Plus `pareto()`.
- **`suites.py`** — `superhard` (56 brute-force-graded hard math; breaks GPT-5.5 to ~0.80) and
  `mixed` (easier numeric). All numeric-answer so majority vote is well-defined.

## Knobs
`--suite superhard|mixed` · `--budget <USD>` · `--max-k <ensemble size>` · `--timeout <s>` ·
`--workers <n>` · `--limit <n tasks, for smoke>`.

## Notes / gotchas
- Reasoner models (Qwen3-Thinking, GLM-5.2, …) are slow + sometimes rate-limited on hard tasks; the
  timeout + tolerance keep the run moving (a no-answer counts as wrong — honest).
- Voting is defined for numeric answers; coding tasks aren't in these suites (code can't be
  majority-voted). Extend `suites.py` + the matrix `ans` extraction to add other answer types.
- The matrix is the asset — it persists across runs, so combination analysis is effectively free
  once a model is measured.
