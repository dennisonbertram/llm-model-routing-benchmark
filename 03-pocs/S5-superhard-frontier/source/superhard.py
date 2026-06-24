"""S5 — scale up + go SUPER HARD: can we break GPT-5.5? (deterministic golds)

Strategy to break a frontier model while keeping golds PROVABLY correct: generate problems that are
trivial to BRUTE-FORCE (we compute the gold in Python) but hard to REASON through by hand —
large inclusion-exclusion, long nonlinear modular recurrences (pure mechanical exact computation,
where LLMs slip), constrained counting over big spaces, Burnside/dihedral necklaces, Grundy values.
Parameters are scaled up to stress exact reasoning. Deterministic (seeded) and reproducible.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 superhard.py [N]
"""
import json
import os
import random
import sys
from itertools import permutations, product
from math import gcd, factorial

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
import tasks as T  # noqa: E402
from cache import Cache  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))


# ---------------- brute-force gold functions (provably correct) ----------------
def coprime_count(N, mods):
    return sum(1 for n in range(1, N + 1) if all(n % p != 0 for p in mods))

def divis_count(N, must, mustnot):
    return sum(1 for n in range(1, N + 1)
               if all(n % a == 0 for a in must) and all(n % b != 0 for b in mustnot))

def partial_derangement(n, forbidden):
    f = set(forbidden)
    return sum(1 for p in permutations(range(n)) if all((i, p[i]) not in f for i in range(n)))

def grid_paths(rows, cols, blocked):
    blocked = set(map(tuple, blocked))
    dp = [[0] * (cols + 1) for _ in range(rows + 1)]
    dp[0][0] = 0 if (0, 0) in blocked else 1
    for r in range(rows + 1):
        for c in range(cols + 1):
            if (r, c) in blocked or (r == 0 and c == 0):
                continue
            dp[r][c] = (dp[r - 1][c] if r else 0) + (dp[r][c - 1] if c else 0)
    return dp[rows][cols]

def subset_sum_mod(n, m, r):
    dp = [0] * m
    dp[0] = 1
    for v in range(1, n + 1):
        ndp = dp[:]
        for s in range(m):
            ndp[(s + v) % m] += dp[s]
        dp = ndp
    return dp[r % m]

def recurrence_mod(a, b, c, x0, x1, k, m):
    x, y = x0 % m, x1 % m
    for _ in range(k - 1):
        x, y = y, (a * y * y + b * x + c) % m
    return y if k >= 1 else x0 % m

def necklace_dihedral(n, k):
    rot = sum(k ** gcd(j, n) for j in range(n))
    if n % 2 == 0:
        refl = n // 2 * (k ** (n // 2) + k ** (n // 2 + 1))
    else:
        refl = n * k ** ((n + 1) // 2)
    return (rot + refl) // (2 * n)

def grundy_subtraction(N, moves):
    g = [0] * (N + 1)
    for x in range(1, N + 1):
        s = {g[x - mv] for mv in moves if mv <= x}
        m = 0
        while m in s:
            m += 1
        g[x] = m
    return g[N]

def digit_sum_prime_count(N):
    def isprime(x):
        return x > 1 and all(x % d for d in range(2, int(x ** 0.5) + 1))
    return sum(1 for n in range(1, N + 1) if isprime(sum(int(d) for d in str(n))))


# ---------------- task generators (prompt + computed gold) ----------------
def gen(seed):
    rng = random.Random(seed)
    out = []
    primescat = [2, 3, 5, 7, 11, 13]

    # F1: inclusion-exclusion coprime counts (5 primes, big N)
    for _ in range(8):
        N = rng.choice([12345, 23456, 34567, 98765, 100000])
        ms = sorted(rng.sample(primescat, rng.choice([4, 5])))
        out.append((f"How many integers from 1 to {N} inclusive are divisible by NONE of "
                    f"{', '.join(map(str, ms))}? Reply with just the number.",
                    coprime_count(N, ms)))

    # F2: divisibility with must/mustnot
    for _ in range(8):
        N = rng.choice([5000, 9999, 20000])
        must = sorted(rng.sample([2, 3, 5, 7], rng.choice([1, 2])))
        mn = sorted(rng.sample([4, 9, 11, 25, 8], rng.choice([2, 3])))
        out.append((f"How many integers from 1 to {N} inclusive are divisible by all of "
                    f"{must} but by none of {mn}? Reply with just the number.",
                    divis_count(N, must, mn)))

    # F3: long nonlinear modular recurrence (mechanical exact computation)
    for _ in range(10):
        a, b, c = rng.randint(1, 4), rng.randint(1, 5), rng.randint(0, 7)
        x0, x1 = rng.randint(1, 9), rng.randint(1, 9)
        k = rng.choice([25, 40, 60, 80])
        m = rng.choice([1000, 997, 10000])
        out.append((f"Define a sequence by x_1={x0}, x_2={x1}, and for n>=3 "
                    f"x_n = ({a}*x_(n-1)^2 + {b}*x_(n-2) + {c}) mod {m}. "
                    f"What is x_{k}? Reply with just the number.",
                    recurrence_mod(a, b, c, x0, x1, k, m)))

    # F4: subset-sum modular counts
    for _ in range(8):
        n = rng.choice([16, 18, 20, 22])
        m = rng.choice([5, 7, 8])
        r = rng.randint(0, m - 1)
        out.append((f"How many subsets (including the empty set) of {{1,2,...,{n}}} have a sum "
                    f"congruent to {r} modulo {m}? Reply with just the number.",
                    subset_sum_mod(n, m, r)))

    # F5: constrained permutation counts (forbidden positions)
    for _ in range(6):
        n = rng.choice([7, 8])
        nf = rng.choice([3, 4, 5])
        forb = set()
        while len(forb) < nf:
            forb.add((rng.randint(0, n - 1), rng.randint(0, n - 1)))
        fl = sorted(forb)
        human = ", ".join(f"person {i+1} not in seat {j+1}" for i, j in fl)
        out.append((f"In how many ways can {n} people be seated in {n} numbered seats subject to: "
                    f"{human}? Reply with just the number.",
                    partial_derangement(n, fl)))

    # F6: grid paths with obstacles
    for _ in range(6):
        R, C = rng.choice([(5, 5), (6, 5), (6, 6)])
        nb = rng.choice([2, 3, 4])
        blk = set()
        while len(blk) < nb:
            cell = (rng.randint(1, R), rng.randint(1, C - 1))
            if cell != (R, C):
                blk.add(cell)
        bl = sorted(blk)
        out.append((f"On a grid you move from corner (0,0) to ({R},{C}) taking unit steps only right "
                    f"(+1 in second coord) or down (+1 in first coord). The cells {bl} are blocked and "
                    f"cannot be entered. How many distinct paths are there? Reply with just the number.",
                    grid_paths(R, C, bl)))

    # F7: dihedral necklaces
    for _ in range(5):
        n = rng.choice([6, 7, 8]); k = rng.choice([2, 3])
        out.append((f"How many distinct necklaces of {n} beads using {k} colors are there, where two "
                    f"necklaces are the same if one can be obtained from the other by rotation OR "
                    f"reflection? Reply with just the number.", necklace_dihedral(n, k)))

    # F8: Grundy / Nim subtraction game
    for _ in range(5):
        N = rng.choice([30, 47, 60]); moves = sorted(rng.sample([1, 2, 3, 4, 5, 6], 3))
        out.append((f"In a subtraction game two players alternately remove {moves} stones from a single "
                    f"pile of {N} stones; a player who cannot move loses. What is the Grundy value "
                    f"(nimber) of the starting position of {N} stones? Reply with just the number.",
                    grundy_subtraction(N, moves)))

    tasks_out = []
    for idx, (prompt, gold) in enumerate(out):
        tasks_out.append({"id": f"sh{idx:03d}", "discipline": "math", "difficulty": "superhard",
                          "prompt": prompt, "grade": T.numeric_grader(int(gold)), "gold": int(gold)})
    return tasks_out


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    items = gen(seed=7)[:N]
    print(f"== {len(items)} super-hard tasks; running gpt-5.5 solo (temp 0) ==", flush=True)
    rows = []
    correct = cost = 0
    for it in items:
        try:
            r = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}],
                           max_tokens=8000, temperature=0.0, timeout=240)
        except Exception as e:
            print(f"  TIMEOUT/ERR {it['id']}: {str(e)[:50]} -> counted as no-answer (incorrect)", flush=True)
            r = {"text": "", "usd": 0.0}
        ok = it["grade"](r["text"])
        correct += ok; cost += r["usd"]
        rows.append({"id": it["id"], "gold": it["gold"], "gpt55_ok": bool(ok), "usd": r["usd"], "prompt": it["prompt"]})
        if not ok:
            print(f"  FAIL {it['id']}: gold={it['gold']} | {it['prompt'][:90]}", flush=True)
        CACHE.save()
    print(f"\ngpt-5.5 solo: {correct}/{len(items)} = {correct/len(items):.3f}  (${cost:.4f})", flush=True)
    fails = [r['id'] for r in rows if not r['gpt55_ok']]
    print(f"gpt-5.5 FAILURES ({len(fails)}): {fails}")
    json.dump(rows, open(os.path.join(HERE, "superhard_gpt55.json"), "w"), indent=1)
    print("wrote superhard_gpt55.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
