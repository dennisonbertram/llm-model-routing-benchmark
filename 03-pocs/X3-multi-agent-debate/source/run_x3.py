"""X3 — Multi-Agent Debate (Du et al., 2023).

BRIEF: 3 cheap models (ENSEMBLE_CHEAP = gpt-4o-mini, gpt-4.1-mini, claude-haiku) each answer
independently. Then for 1-2 debate rounds, each model sees the others' answers and may revise.
Finally aggregate: majority vote for closed/numeric items, judge.pick_best for open-ended.
Grade the final answer. Compare debate acc/cost to:
  - single cheap (gpt-4o-mini)
  - single strong (gpt-4.1)
Focus on MATH (esp. hard) + QA subset to get meaningful accuracy signal at reasonable cost.
Report the honest outcome (debate often helps reasoning but multiplies cost — quantify).
Capture a real debate transcript snippet as evidence.

Run: set -a; . .agent-university/secrets.local.env; set +a && python3 run_x3.py
"""
import json
import os
import re
import sys
from collections import Counter

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config   # noqa: E402
import tasks    # noqa: E402
from cache import Cache  # noqa: E402
from router_base import Router, FixedModel, _budget, run_suite  # noqa: E402
from metrics import format_table, pareto_front  # noqa: E402
import judge    # noqa: E402

# ── Debate configuration ────────────────────────────────────────────────────
DEBATERS = config.ENSEMBLE_CHEAP   # [gpt-4o-mini, gpt-4.1-mini, claude-haiku-4-5-20251001]
N_ROUNDS = 1                        # 1 debate round after initial answers (round 0 = initial)

# ── Test subset ─────────────────────────────────────────────────────────────
# Math (all 15) + first 8 QA items for a 23-item representative suite
MATH = [t for t in tasks.ALL if t["discipline"] == "math"]
QA = [t for t in tasks.ALL if t["discipline"] == "qa"][:8]
SUBSET = MATH + QA   # 23 items

HARD_MATH_IDS = {"m9", "m10", "m12", "m13", "m14", "m15"}


def extract_numeric(text: str):
    """Extract the last integer from text (mirrors numeric_grader logic)."""
    nums = re.findall(r"-?\d+", text.replace(",", ""))
    return int(nums[-1]) if nums else None


class DebateRouter(Router):
    """Multi-agent debate router (Du et al.).

    Protocol:
      Round 0: each debater answers independently.
      Rounds 1..N_ROUNDS: each debater sees others' latest answers + original prompt and may revise.
      Aggregation:
        - math/numeric items: majority vote on extracted integer.
        - QA items: judge.pick_best selects the best final proposal.

    Oracle leakage avoidance: the router NEVER reads item['difficulty'] or item['discipline']
    to make routing decisions. It uses the same logic for all items (the discipline is only
    used post-hoc to choose the aggregation strategy — majority for items where an integer can
    be extracted, judge.pick_best otherwise).
    """

    def __init__(self, debaters, n_rounds, cache=None):
        super().__init__(cache)
        self.debaters = debaters
        self.n_rounds = n_rounds
        self.name = f"debate:{len(debaters)}x{n_rounds}r"
        self._transcript_sample = None  # store first full transcript

    def _call(self, model, prompt, max_tokens, nonce=None):
        if self.cache is not None:
            return self.cache.chat(model, [{"role": "user", "content": prompt}],
                                   max_tokens=max_tokens, temperature=0.0, nonce=nonce)
        from providers import chat
        return chat(model, [{"role": "user", "content": prompt}],
                    max_tokens=max_tokens, temperature=0.0)

    def answer(self, item):
        prompt = item["prompt"]
        max_tok = _budget(item)
        total_usd = 0.0
        models_used = []

        # history[i] = list of responses for debater i, one per round (0 = initial)
        history = [[] for _ in self.debaters]

        # ── Round 0: independent answers ────────────────────────────────────
        for i, model in enumerate(self.debaters):
            nonce = f"debate-{item['id']}-r0-d{i}"
            r = self._call(model, prompt, max_tok, nonce=nonce)
            history[i].append(r["text"])
            total_usd += r["usd"]
            models_used.append(model)

        # ── Debate rounds 1..N_ROUNDS ────────────────────────────────────────
        for rnd in range(1, self.n_rounds + 1):
            for i, model in enumerate(self.debaters):
                # Show this debater the others' most recent answers
                others_text = ""
                for j, other_model in enumerate(self.debaters):
                    if j != i:
                        short_name = other_model.split("/")[-1].split("-")[0].capitalize()
                        others_text += f"\n[{short_name}]: {history[j][-1]}\n"
                debate_prompt = (
                    f"Original question: {prompt}\n\n"
                    f"Your previous answer: {history[i][-1]}\n\n"
                    f"Other participants' answers:{others_text}\n"
                    "Considering the above, what is your revised final answer? "
                    "Reply with ONLY the answer (match the format requested)."
                )
                nonce = f"debate-{item['id']}-r{rnd}-d{i}"
                r = self._call(model, debate_prompt, max_tok, nonce=nonce)
                history[i].append(r["text"])
                total_usd += r["usd"]
                models_used.append(model)

        # Final answers from last round
        final_answers = [history[i][-1] for i in range(len(self.debaters))]

        # ── Aggregation ──────────────────────────────────────────────────────
        # Try numeric majority first (works for math/numeric items).
        # If all debaters fail to produce integers, fall back to judge.pick_best.
        parsed = [extract_numeric(a) for a in final_answers]
        valid_ints = [p for p in parsed if p is not None]
        if len(valid_ints) >= 2:
            # At least 2 debaters produced numeric answers → majority vote
            voted = Counter(valid_ints).most_common(1)[0][0]
            final_text = str(voted)
            agg_method = "majority_numeric"
            agg_usd = 0.0
        else:
            # Non-numeric or only one parseable → judge.pick_best
            pb = judge.pick_best(prompt, final_answers, cache=self.cache)
            final_text = final_answers[pb["index"]]
            agg_usd = pb["usd"]
            total_usd += agg_usd
            agg_method = "judge_pick_best"
            models_used.append(config.JUDGE_MODEL)

        # Save first transcript for evidence
        if self._transcript_sample is None:
            self._transcript_sample = {
                "item_id": item["id"],
                "prompt": prompt,
                "history": history,
                "final_answers": final_answers,
                "final_text": final_text,
                "agg_method": agg_method,
            }

        return {
            "text": final_text,
            "usd": total_usd,
            "latency_ms": 0,   # multiple calls; wall-clock not tracked per-item
            "models": models_used,
            "decision": f"{agg_method}:rounds={self.n_rounds}",
        }


def main():
    print("== X3: Multi-Agent Debate (Du et al.) ==\n")
    print(f"Debaters: {DEBATERS}")
    print(f"Debate rounds: {N_ROUNDS}")
    print(f"Test suite: {len(SUBSET)} items ({len(MATH)} math + {len(QA)} QA)\n")

    # Own cache — never touches harness/.cache/labelset.json
    cache_path = os.path.join(os.path.dirname(__file__), ".cache.json")
    cache = Cache(cache_path)

    # ── Baselines (reuse L0 labelset cache for cheap/strong baselines) ──────
    # Note: the harness labelset cache has the full suite already billed.
    # We re-run through our own cache (which will populate from live calls if not already cached).
    print("--- Baselines ---")
    cheap_router = FixedModel(config.CHEAP_DEFAULT, cache=cache)
    strong_router = FixedModel(config.STRONG_DEFAULT, cache=cache)

    cheap_result = run_suite(cheap_router, SUBSET, verbose=True)
    print(f"  cheap baseline: acc={cheap_result.accuracy():.3f}  cost=${cheap_result.total_usd():.5f}")
    cache.save()

    strong_result = run_suite(strong_router, SUBSET, verbose=True)
    print(f"  strong baseline: acc={strong_result.accuracy():.3f}  cost=${strong_result.total_usd():.5f}")
    cache.save()

    # ── Debate router ────────────────────────────────────────────────────────
    print(f"\n--- Debate: {len(DEBATERS)} models × (1 init + {N_ROUNDS} debate round) ---")
    debate = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=cache)
    debate_result = run_suite(debate, SUBSET, verbose=True)
    print(f"  debate: acc={debate_result.accuracy():.3f}  cost=${debate_result.total_usd():.5f}")
    cache.save()

    # ── Hard math subset ─────────────────────────────────────────────────────
    print("\n--- Hard Math Subset (m9,m10,m12,m13,m14,m15) ---")
    hard_items = [t for t in MATH if t["id"] in HARD_MATH_IDS]
    cheap_hard = run_suite(cheap_router, hard_items)
    strong_hard = run_suite(strong_router, hard_items)

    debate_hard = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=cache)
    debate_hard_result = run_suite(debate_hard, hard_items, verbose=True)
    cache.save()

    # ── Cost multipliers ─────────────────────────────────────────────────────
    cheap_cost = cheap_result.total_usd()
    strong_cost = strong_result.total_usd()
    debate_cost = debate_result.total_usd()
    calls_per_item = len(DEBATERS) * (1 + N_ROUNDS)

    print("\n== RESULTS ==")
    rows = [
        cheap_result.row(),
        strong_result.row(),
        debate_result.row(),
    ]
    print(format_table(rows))

    print("\n== HARD MATH SUBSET ==")
    hard_rows = [
        cheap_hard.row(),
        strong_hard.row(),
        debate_hard_result.row(),
    ]
    print(format_table(hard_rows))

    print("\n== KEY METRICS ==")
    print(f"  Calls per item (debate): {calls_per_item}  ({len(DEBATERS)} debaters × {1+N_ROUNDS} rounds)")
    print(f"  Cost multiplier vs cheap: {debate_cost/cheap_cost:.1f}×")
    print(f"  Cost multiplier vs strong: {debate_cost/strong_cost:.1f}×")
    print(f"  Accuracy: cheap={cheap_result.accuracy():.3f}  strong={strong_result.accuracy():.3f}  debate={debate_result.accuracy():.3f}")
    print(f"  Hard math: cheap={cheap_hard.accuracy():.3f}  strong={strong_hard.accuracy():.3f}  debate={debate_hard_result.accuracy():.3f}")

    acc_gap_vs_cheap = cheap_result.accuracy()
    acc_gap_vs_strong = strong_result.accuracy()
    debate_acc = debate_result.accuracy()
    if acc_gap_vs_strong > acc_gap_vs_cheap:
        gap = acc_gap_vs_strong - acc_gap_vs_cheap
        closed = (debate_acc - acc_gap_vs_cheap) / gap if gap > 0 else 0
        print(f"  Debate closes {closed:.0%} of cheap→strong accuracy gap")

    # ── Transcript sample ────────────────────────────────────────────────────
    if debate._transcript_sample:
        ts = debate._transcript_sample
        print(f"\n== DEBATE TRANSCRIPT SAMPLE (item: {ts['item_id']}) ==")
        print(f"  Prompt: {ts['prompt']}")
        print(f"  Initial answers:")
        for i, (model, ans) in enumerate(zip(DEBATERS, [h[0] for h in ts["history"]])):
            print(f"    [{model.split('/')[-1][:20]:20s}] R0: {ans!r}")
        if N_ROUNDS >= 1:
            print(f"  After round 1:")
            for i, (model, hist) in enumerate(zip(DEBATERS, ts["history"])):
                if len(hist) > 1:
                    print(f"    [{model.split('/')[-1][:20]:20s}] R1: {hist[1]!r}")
        print(f"  Aggregation: {ts['agg_method']}")
        print(f"  Final answer: {ts['final_text']!r}")

    # Save summary
    summary = {
        "config": {
            "debaters": DEBATERS,
            "n_rounds": N_ROUNDS,
            "n_items": len(SUBSET),
            "calls_per_item": calls_per_item,
        },
        "baseline_cheap": cheap_result.row(),
        "baseline_strong": strong_result.row(),
        "debate": debate_result.row(),
        "hard_math": {
            "cheap": cheap_hard.row(),
            "strong": strong_hard.row(),
            "debate": debate_hard_result.row(),
        },
        "cost_multipliers": {
            "vs_cheap": round(debate_cost / cheap_cost, 2),
            "vs_strong": round(debate_cost / strong_cost, 2),
        },
        "transcript_sample": debate._transcript_sample,
        "cache_stats": cache.stats(),
    }
    out_path = os.path.join(os.path.dirname(__file__), "x3_summary.json")
    json.dump(summary, open(out_path, "w"), indent=2, default=str)
    print(f"\nwrote {out_path}")
    print(f"Cache stats: {cache.stats()}")


if __name__ == "__main__":
    main()
