"""Vendored Multi-LLM AB-MCTS-A (Beta variant) — faithful reimplementation of Sakana's algorithm.

Source: "Wider or Deeper? Scaling LLM Inference-Time Compute with Adaptive Branching Tree Search"
(arXiv:2503.04412) + TreeQuest (github.com/SakanaAI/treequest, Apache-2.0). We reimplement AB-MCTS-A
(conjugate Beta, no MCMC) in stdlib+numpy because TreeQuest needs Python 3.11+ and this repo is 3.9.

Mechanism (per the paper):
  - Each action has a Beta posterior with a Jeffreys prior (alpha=beta=0.5); observed scores r in [0,1].
    Thompson-sample one score per action; pick argmax. GEN = generate a NEW answer (go WIDER); REFINE =
    improve an existing answer using it as context (go DEEPER). The branching factor emerges from the
    reward signal — no fixed width, no UCT constant.
  - Multi-LLM ("stack"): one GEN arm PER MODEL, each with its own Beta over the scores of answers that
    model produced. Thompson sampling over the arms picks WHICH model generates; better models get
    pulled more. (Appendix D, shared-GEN variant.)
  - Score signal = an EXTERNAL evaluator R(answer)->[0,1] (mandatory). For coding we use the fraction of
    PUBLIC unit tests passed; final quality is measured on HELD-OUT hidden tests (no leakage).
"""
import numpy as np


class Node:
    __slots__ = ("text", "pub", "model", "kids", "depth")

    def __init__(self, text, pub, model, depth):
        self.text, self.pub, self.model, self.kids, self.depth = text, pub, model, [], depth


def _beta_sample(scores, rng, jeff=0.5):
    a = jeff + sum(scores)
    b = jeff + sum(1.0 - s for s in scores)
    return float(rng.beta(a, b))


def ab_mcts_multi(pool, gen_fn, refine_fn, score_fn, budget, seed=0, max_depth=3):
    """Run Multi-LLM AB-MCTS-A. gen_fn(model)->(text,usd); refine_fn(parent_text,model)->(text,usd);
    score_fn(text)->[0,1] (public). Returns dict with best node, per-model pulls, cost, trace."""
    rng = np.random.RandomState(seed)
    nodes = []                                   # all answer nodes (for REFINE actions)
    gen_scores = {m: [] for m in pool}           # per-model GEN posterior observations
    pulls = {m: 0 for m in pool}
    cost = 0.0
    best = None

    def consider_and_act():
        nonlocal cost, best
        # 1) sample each per-model GEN arm (Jeffreys prior when empty -> very uncertain -> explores)
        best_kind, best_arg, best_s = None, None, -1.0
        for m in pool:
            s = _beta_sample(gen_scores[m], rng)
            if s > best_s:
                best_kind, best_arg, best_s = "GEN", m, s
        # 2) sample each existing node's REFINE arm (posterior over its own subtree scores)
        for nd in nodes:
            if nd.depth >= max_depth:
                continue
            subtree = [nd.pub] + [k.pub for k in nd.kids]
            s = _beta_sample(subtree, rng)
            if s > best_s:
                best_kind, best_arg, best_s = "REFINE", nd, s
        # 3) execute the winning action
        if best_kind == "GEN":
            m = best_arg
            text, c = gen_fn(m)
            sc = score_fn(text)
            node = Node(text, sc, m, depth=0)
            nodes.append(node)
            gen_scores[m].append(sc)
            pulls[m] += 1
        else:
            parent = best_arg
            # which model refines? Thompson over the per-model arms (the bandit also picks the reviser)
            pick_m, pick_s = pool[0], -1.0
            for m in pool:
                s = _beta_sample(gen_scores[m], rng)
                if s > pick_s:
                    pick_m, pick_s = m, s
            text, c = refine_fn(parent.text, pick_m)
            sc = score_fn(text)
            node = Node(text, sc, pick_m, depth=parent.depth + 1)
            parent.kids.append(node)
            nodes.append(node)
            gen_scores[pick_m].append(sc)
            pulls[pick_m] += 1
        cost += c
        if best is None or node.pub > best.pub:
            best = node
        return node.pub

    for _ in range(budget):
        pub = consider_and_act()
        if pub >= 1.0:               # public-perfect found; a real verifier would select & stop
            break
    return {"best": best, "pulls": pulls, "cost": cost, "n_nodes": len(nodes),
            "budget_used": len(nodes)}
