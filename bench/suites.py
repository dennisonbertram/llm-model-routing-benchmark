"""Task suites for the benchmark. All numeric-answer (so majority-vote ensembles are well-defined).

  superhard : 56 brute-force-graded hard math/combinatorics/number-theory tasks (S5; breaks GPT-5.5 to ~0.80).
  mixed     : the math + numeric-QA items from the original 45-task suite (easier; cheap models do well).
"""
import os
import sys

S5 = os.path.join(os.path.dirname(__file__), "..", "03-pocs", "S5-superhard-frontier", "source")
HARNESS = os.path.join(os.path.dirname(__file__), "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, S5)


def load(name):
    if name == "superhard":
        import superhard as S
        items = S.gen(seed=7)[:56]
        return [{"id": it["id"], "prompt": it["prompt"], "grade": it["grade"], "gold": it["gold"]} for it in items]
    if name == "mixed":
        import tasks as T
        items = [it for it in T.MATH]  # numeric only (votable); qa golds aren't ints
        return [{"id": it["id"], "prompt": it["prompt"], "grade": it["grade"], "gold": it["gold"]} for it in items]
    raise ValueError(f"unknown suite {name!r} (use: superhard | mixed)")
