"""X1 — Mixture-of-Agents (Wang et al., 2024).

Strategy: for each task in the suite, get independent proposals from
config.ENSEMBLE_CHEAP (gpt-4o-mini, gpt-4.1-mini, claude-haiku-4-5-20251001),
then aggregate via judge.aggregate_moa (default gpt-4o) to produce a final answer.
Grade the final answer with the task's deterministic grader.

Compare:
  - MoA(cheap ensemble → gpt-4o aggregator)
  - always-cheap (gpt-4o-mini baseline)
  - always-strong (gpt-4.1 baseline)

Optional 2-layer MoA variant on hard math items only.

HONESTY NOTE: MoA costs MORE than a single cheap call (N proposals + 1 aggregation).
The question is whether the accuracy gain justifies the cost vs a single strong call.
Report the measured outcome truthfully — do NOT tune to manufacture a win.

Run:
  set -a; . .agent-university/secrets.local.env; set +a
  cd source && python3 run_x1.py
"""
import json
import os
import sys
import time

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config
import tasks
from cache import Cache
from router_base import Router, run_suite, _budget
import judge
from metrics import format_table, pareto_front

# --- POC-local cache (NOT the shared harness labelset) ---
HERE = os.path.dirname(__file__)
CACHE_PATH = os.path.join(HERE, ".cache.json")

# Baselines from L0 (reuse harness cache for cheap/strong, no re-billing)
LABELSET = os.path.join(HARNESS, ".cache", "labelset.json")


# ---------------------------------------------------------------------------
# MoA Router
# ---------------------------------------------------------------------------
class MoARouter(Router):
    """Mixture-of-Agents: each ensemble member proposes, then an aggregator synthesises."""

    def __init__(self, proposers, aggregator, cache=None):
        super().__init__(cache)
        self.proposers = proposers   # list of cheap model ids
        self.aggregator = aggregator
        self.name = f"MoA(proposers={len(proposers)},agg={aggregator.split('/')[-1]})"

    def answer(self, item):
        proposals = []
        proposal_usd = 0.0
        proposal_latency = 0

        for model in self.proposers:
            r = self._chat(model, item["prompt"], max_tokens=_budget(item), temperature=0.0)
            proposals.append(r["text"])
            proposal_usd += r["usd"]
            proposal_latency += r["latency_ms"]

        # Aggregate
        agg_r = judge.aggregate_moa(
            item["prompt"], proposals, model=self.aggregator,
            cache=self.cache, max_tokens=_budget(item)
        )

        total_usd = proposal_usd + agg_r["usd"]
        total_latency = proposal_latency + agg_r["latency_ms"]

        return {
            "text": agg_r["text"],
            "usd": total_usd,
            "latency_ms": total_latency,
            "models": list(self.proposers) + [self.aggregator],
            "decision": f"moa_agg:{self.aggregator}",
            "_proposals": proposals,
            "_proposal_usd": proposal_usd,
            "_agg_usd": agg_r["usd"],
        }


class MoA2LayerRouter(Router):
    """Two-layer MoA: layer-1 proposals → layer-1 aggregator → layer-2 re-aggregation.
    Only used on a small subset (hard math items) to explore if layering helps."""

    def __init__(self, proposers, l1_aggregator, l2_aggregator, cache=None):
        super().__init__(cache)
        self.proposers = proposers
        self.l1_agg = l1_aggregator
        self.l2_agg = l2_aggregator
        self.name = f"MoA2L(l1={l1_aggregator.split('/')[-1]},l2={l2_aggregator.split('/')[-1]})"

    def answer(self, item):
        # Layer 1: independent proposals
        proposals = []
        total_usd = 0.0
        total_latency = 0

        for model in self.proposers:
            r = self._chat(model, item["prompt"], max_tokens=_budget(item), temperature=0.0)
            proposals.append(r["text"])
            total_usd += r["usd"]
            total_latency += r["latency_ms"]

        # Layer 1 aggregation (first synthesis)
        l1_r = judge.aggregate_moa(
            item["prompt"], proposals, model=self.l1_agg,
            cache=self.cache, max_tokens=_budget(item)
        )
        total_usd += l1_r["usd"]
        total_latency += l1_r["latency_ms"]

        # Layer 2 aggregation: re-synthesize from original proposals + L1 synthesis
        all_candidates = proposals + [l1_r["text"]]
        l2_r = judge.aggregate_moa(
            item["prompt"], all_candidates, model=self.l2_agg,
            cache=self.cache, max_tokens=_budget(item)
        )
        total_usd += l2_r["usd"]
        total_latency += l2_r["latency_ms"]

        return {
            "text": l2_r["text"],
            "usd": total_usd,
            "latency_ms": total_latency,
            "models": list(self.proposers) + [self.l1_agg, self.l2_agg],
            "decision": f"moa2l_agg:{self.l2_agg}",
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("X1 — Mixture-of-Agents (Wang et al.)")
    print("=" * 70)

    cache = Cache(CACHE_PATH)
    # Also load the shared labelset cache so baselines use cached responses
    labelset_cache = Cache(LABELSET)

    suite = tasks.ALL
    n = len(suite)
    print(f"\nSuite: {n} tasks (math={sum(1 for t in suite if t['discipline']=='math')}, "
          f"qa={sum(1 for t in suite if t['discipline']=='qa')}, "
          f"coding={sum(1 for t in suite if t['discipline']=='coding')})")

    # --- 1) Baselines from shared labelset cache (no re-billing) ---
    print("\n--- Baselines (from labelset cache, no re-billing) ---")
    from router_base import FixedModel
    cheap_router = FixedModel(config.CHEAP_DEFAULT, cache=labelset_cache)
    strong_router = FixedModel(config.STRONG_DEFAULT, cache=labelset_cache)
    cheap_result = run_suite(cheap_router, suite, verbose=False)
    strong_result = run_suite(strong_router, suite, verbose=False)
    # Do NOT save labelset_cache — the harness labelset is read-only for this POC.

    print(f"  always-cheap  ({config.CHEAP_DEFAULT}): "
          f"acc={cheap_result.accuracy():.3f}  cost=${cheap_result.total_usd():.5f}")
    print(f"  always-strong ({config.STRONG_DEFAULT}): "
          f"acc={strong_result.accuracy():.3f}  cost=${strong_result.total_usd():.5f}  "
          f"({strong_result.total_usd()/cheap_result.total_usd():.1f}x cheap)")

    # --- 2) MoA (3 cheap proposers → gpt-4o aggregator) ---
    print("\n--- MoA: 3 cheap proposers → gpt-4o aggregator (full 45-task suite) ---")
    moa_router = MoARouter(
        proposers=config.ENSEMBLE_CHEAP,
        aggregator=config.MID_DEFAULT,  # gpt-4o
        cache=cache,
    )
    moa_result = run_suite(moa_router, suite, verbose=True)
    cache.save()

    print(f"\n  MoA result: acc={moa_result.accuracy():.3f}  "
          f"cost=${moa_result.total_usd():.5f}  "
          f"({moa_result.total_usd()/cheap_result.total_usd():.1f}x cheap)")

    # --- 3) Per-discipline breakdown ---
    print("\n--- Per-discipline accuracy ---")
    for disc in ["math", "qa", "coding"]:
        disc_items = [i for i in moa_result.items if i["discipline"] == disc]
        if not disc_items:
            continue
        acc = sum(i["correct"] for i in disc_items) / len(disc_items)
        cheap_disc = [i for i in cheap_result.items if i["discipline"] == disc]
        cheap_acc = sum(i["correct"] for i in cheap_disc) / len(cheap_disc)
        strong_disc = [i for i in strong_result.items if i["discipline"] == disc]
        strong_acc = sum(i["correct"] for i in strong_disc) / len(strong_disc)
        print(f"  {disc:6}: MoA={acc:.3f}  cheap={cheap_acc:.3f}  strong={strong_acc:.3f}")

    # --- 4) 2-layer MoA on hard math items only ---
    hard_math = [t for t in suite if t["discipline"] == "math" and t["difficulty"] == "hard"]
    print(f"\n--- 2-layer MoA on {len(hard_math)} hard math items (m8-m15) ---")
    moa2l_router = MoA2LayerRouter(
        proposers=config.ENSEMBLE_CHEAP,
        l1_aggregator=config.MID_DEFAULT,   # gpt-4o
        l2_aggregator=config.STRONG_DEFAULT, # gpt-4.1 (only for 2nd layer synthesis)
        cache=cache,
    )
    moa2l_result = run_suite(moa2l_router, hard_math, verbose=True)
    cache.save()

    # Single strong on hard math (from labelset)
    strong_hard_items = [i for i in strong_result.items if i["discipline"] == "math" and i["difficulty"] == "hard"]
    strong_hard_acc = sum(i["correct"] for i in strong_hard_items) / max(1, len(strong_hard_items))
    cheap_hard_items = [i for i in cheap_result.items if i["discipline"] == "math" and i["difficulty"] == "hard"]
    cheap_hard_acc = sum(i["correct"] for i in cheap_hard_items) / max(1, len(cheap_hard_items))

    print(f"\n  Hard math (n={len(hard_math)}):")
    print(f"    single cheap  ({config.CHEAP_DEFAULT}): acc={cheap_hard_acc:.3f}")
    print(f"    single strong ({config.STRONG_DEFAULT}): acc={strong_hard_acc:.3f}")
    print(f"    MoA-1L (3 cheap + gpt-4o agg):    acc={moa_result.accuracy():.3f} (full suite)")

    moa2l_acc = moa2l_result.accuracy()
    moa2l_usd = moa2l_result.total_usd()
    print(f"    MoA-2L (3 cheap + gpt-4o + gpt-4.1 agg): acc={moa2l_acc:.3f}  cost=${moa2l_usd:.5f}")

    # --- 5) Results table ---
    print("\n--- Results table (all 45 tasks) ---")
    rows = [cheap_result.row(), moa_result.row(), strong_result.row()]
    print(format_table(rows))

    # --- 6) Save summary ---
    hard_math_moa_items = [i for i in moa_result.items if i["discipline"] == "math" and i["difficulty"] == "hard"]
    hard_math_moa_acc = sum(i["correct"] for i in hard_math_moa_items) / max(1, len(hard_math_moa_items))

    summary = {
        "baselines": {
            "cheap": cheap_result.row(),
            "strong": strong_result.row(),
        },
        "moa": moa_result.row(),
        "moa2l_hard_math": moa2l_result.row(),
        "hard_math_breakdown": {
            "n": len(hard_math),
            "cheap_acc": round(cheap_hard_acc, 4),
            "strong_acc": round(strong_hard_acc, 4),
            "moa_1l_acc": round(hard_math_moa_acc, 4),
            "moa_2l_acc": round(moa2l_acc, 4),
        },
        "per_discipline": {},
        "cache_stats": cache.stats(),
    }
    for disc in ["math", "qa", "coding"]:
        disc_items = [i for i in moa_result.items if i["discipline"] == disc]
        if disc_items:
            acc = sum(i["correct"] for i in disc_items) / len(disc_items)
            total_usd = sum(i["usd"] for i in disc_items)
            summary["per_discipline"][disc] = {"n": len(disc_items), "acc": round(acc, 4), "usd": round(total_usd, 6)}

    out_path = os.path.join(HERE, "x1_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out_path}")
    print(f"cache stats: {cache.stats()}")

    # --- 7) Honest verdict ---
    print("\n--- Honest verdict ---")
    moa_acc = moa_result.accuracy()
    moa_cost = moa_result.total_usd()
    strong_acc = strong_result.accuracy()
    strong_cost = strong_result.total_usd()
    cheap_acc = cheap_result.accuracy()

    print(f"  MoA acc={moa_acc:.3f}  vs strong acc={strong_acc:.3f}  "
          f"(delta={moa_acc - strong_acc:+.3f})")
    print(f"  MoA cost=${moa_cost:.5f}  vs strong cost=${strong_cost:.5f}  "
          f"({moa_cost/strong_cost:.2f}x strong cost)")
    print(f"  MoA cost multiplier over single cheap: {moa_cost/cheap_result.total_usd():.1f}x")

    if moa_acc >= strong_acc - 0.01 and moa_cost < strong_cost:
        print("  VERDICT: MoA matches/beats strong at lower cost — ensemble wins")
    elif moa_acc >= cheap_acc + 0.05:
        print("  VERDICT: MoA improves over cheap but does NOT match strong; cost is higher")
    else:
        print("  VERDICT: MoA does not materially improve over cheap alone; ensemble overhead not justified here")


if __name__ == "__main__":
    main()
