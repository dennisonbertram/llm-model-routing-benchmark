"""Evaluate model COMBINATIONS over the outcome matrix — entirely offline (no API calls).

Strategies:
  - solo(m):                 one model.
  - vote(members):           majority vote on the numeric answer; ties -> first member's answer.
  - consensus_escalate(members, ref): if members all agree, use that answer (cheap); else escalate to
                             the reference model. Cost = members' cost + (ref cost only on disagreement).
  - oracle(members):         a member is correct -> correct (unrealizable ceiling of the pool).

All accuracies/costs are computed from matrix[model][task] = {ans, usd, ...}. gold comes from the tasks.
"""
from collections import Counter
from itertools import combinations


def _agg(per_task):
    n = len(per_task)
    return sum(ok for ok, _ in per_task) / n, sum(c for _, c in per_task) / n


def solo(matrix, model, tasks, gold):
    pt = [((matrix[model][t["id"]]["ans"] == gold[t["id"]]), matrix[model][t["id"]]["usd"]) for t in tasks]
    return _agg(pt)


def vote(matrix, members, tasks, gold):
    pt = []
    for t in tasks:
        votes = [matrix[m][t["id"]]["ans"] for m in members]
        cost = sum(matrix[m][t["id"]]["usd"] for m in members)
        tally = Counter(v for v in votes if v is not None)
        if tally:
            top = tally.most_common()
            best = top[0][1]
            winner = next(v for v in votes if v is not None and tally[v] == best)  # tie -> first member
        else:
            winner = None
        pt.append((winner == gold[t["id"]], cost))
    return _agg(pt)


def consensus_escalate(matrix, members, ref, tasks, gold):
    pt = []
    for t in tasks:
        votes = [matrix[m][t["id"]]["ans"] for m in members]
        cost = sum(matrix[m][t["id"]]["usd"] for m in members)
        if len(set(votes)) == 1 and votes[0] is not None:      # unanimous consensus -> trust it
            winner = votes[0]
        else:                                                   # disagreement -> escalate to reference
            winner = matrix[ref][t["id"]]["ans"]
            cost += matrix[ref][t["id"]]["usd"]
        pt.append((winner == gold[t["id"]], cost))
    return _agg(pt)


def oracle(matrix, members, tasks, gold):
    pt = []
    for t in tasks:
        ok = any(matrix[m][t["id"]]["ans"] == gold[t["id"]] for m in members)
        cost = sum(matrix[m][t["id"]]["usd"] for m in members)  # pay all (upper-bound ceiling)
        pt.append((ok, cost))
    return _agg(pt)


def pareto(rows, acc="acc", cost="cost"):
    """Non-dominated set: no other row has >= accuracy AND <= cost (with one strict)."""
    out = []
    for r in rows:
        if not any(s is not r and s[acc] >= r[acc] and s[cost] <= r[cost]
                   and (s[acc] > r[acc] or s[cost] < r[cost]) for s in rows):
            out.append(r)
    return sorted(out, key=lambda r: r[cost])


def evaluate_all(matrix, models, tasks, gold, ref=None, max_k=3):
    """Return a list of result rows for solos + all k<=max_k votes + consensus-escalate + oracle."""
    rows = []
    for m in models:
        a, c = solo(matrix, m, tasks, gold)
        rows.append({"strategy": "solo", "members": [m], "acc": a, "cost": c})
    for k in range(2, max_k + 1):
        for combo in combinations(models, k):
            a, c = vote(matrix, list(combo), tasks, gold)
            rows.append({"strategy": f"vote-{k}", "members": list(combo), "acc": a, "cost": c})
            if ref and ref not in combo:
                a2, c2 = consensus_escalate(matrix, list(combo), ref, tasks, gold)
                rows.append({"strategy": f"consensus-escalate-{k}", "members": list(combo) + [f"->{ref}"], "acc": a2, "cost": c2})
    # oracle over the full non-reference pool (ceiling)
    pool = [m for m in models if m != ref]
    a, c = oracle(matrix, pool, tasks, gold)
    rows.append({"strategy": "oracle(pool)", "members": pool, "acc": a, "cost": c})
    return rows
