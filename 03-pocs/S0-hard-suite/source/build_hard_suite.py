"""S0 — build a HARD, deterministically-gradable suite where GPT-5.5 does NOT saturate.

Protocol (EXTENSION-PLAN Section 2):
  1. author candidate items across 3 gradable families (math golds computed by brute force here,
     so they are provably correct; coding tests validated against reference solutions);
  2. run gpt-5.5 solo (single attempt, temp 0) over all candidates — LIVE;
  3. KEEP only items gpt-5.5 does not fully solve (math wrong / coding pass-fraction < 1.0 / qa wrong)
     so the kept suite has real headroom for orchestration to show value;
  4. freeze the kept suite + a gpt-5.5 labelset.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 build_hard_suite.py
"""
import json
import math
import os
import sys
from itertools import combinations, product

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import tasks  # noqa: E402
from cache import Cache  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))

# ---------------- MATH: golds computed by brute force (provably correct) ----------------
def g_subsets4():
    return sum(1 for r in range(16) for c in combinations(range(1, 16), r) if sum(c) % 4 == 0)
def g_facmod():
    return sum(math.factorial(k) for k in range(1, 51)) % 21
def g_pairs():
    return sum(1 for a in range(1, 31) for b in range(1, 31) if (a * a + b * b) % (a + b) == 0)
def g_digitsum():
    return sum(int(d) for d in str(2 ** 100))
def g_evengrid():
    n = 0
    for m in product([0, 1], repeat=9):
        M = [m[0:3], m[3:6], m[6:9]]
        if all(sum(row) % 2 == 0 for row in M) and all(sum(col) % 2 == 0 for col in zip(*M)):
            n += 1
    return n
def g_coins():
    coins = [1, 3, 7, 12]; amt = 50
    dp = [1] + [0] * amt
    for c in coins:
        for a in range(c, amt + 1):
            dp[a] += dp[a - c]
    return dp[amt]
def g_necklace():  # 6 beads, 2 colors, rotations only (Burnside)
    return sum(2 ** math.gcd(k, 6) for k in range(6)) // 6
def g_modinv():
    return next(x for x in range(1, 101) if (17 * x) % 101 == 1)
def g_partitions():  # partitions of 20 into at most 4 parts
    from functools import lru_cache
    @lru_cache(None)
    def p(n, k):
        if n == 0: return 1
        if k == 0: return 0
        return p(n - k, k) + p(n, k - 1) if n >= k else p(n, k - 1)
    return p(20, 4)
def g_lattice():  # monotonic paths (0,0)->(6,6) staying weakly below diagonal y<=x = Catalan-ish C(6)
    from math import comb
    return comb(12, 6) // 7  # Catalan number C_6
def g_trailingbase12():  # trailing zeros of 50! in base 12 = min over prime powers
    def vp(n, p):
        s = 0; pk = p
        while pk <= n:
            s += n // pk; pk *= p
        return s
    return min(vp(50, 2) // 2, vp(50, 3))  # 12 = 2^2 * 3
def g_sqsum():  # number of n in 1..200 expressible as sum of two squares (incl 0)
    sq = {a * a for a in range(15)}
    return sum(1 for n in range(1, 201) if any((n - s) in sq for s in sq if s <= n))

MATH = [
    ("hm1", f"How many subsets of {{1,2,...,15}} (including the empty set) have a sum divisible by 4? Reply with just the number.", g_subsets4()),
    ("hm2", "What is the remainder when (1! + 2! + 3! + ... + 50!) is divided by 21? Reply with just the number.", g_facmod()),
    ("hm3", "How many ordered pairs (a,b) of integers with 1<=a<=30 and 1<=b<=30 satisfy (a^2+b^2) being divisible by (a+b)? Reply with just the number.", g_pairs()),
    ("hm4", "What is the sum of the decimal digits of 2^100? Reply with just the number.", g_digitsum()),
    ("hm5", "How many of the 512 3x3 matrices with entries in {0,1} have every row sum even AND every column sum even? Reply with just the number.", g_evengrid()),
    ("hm6", "Using any number of coins of denominations 1, 3, 7, and 12, in how many ways can you make exactly 50 (order does not matter)? Reply with just the number.", g_coins()),
    ("hm7", "How many distinct necklaces of 6 beads using 2 colors are there, counting two necklaces the same if one is a rotation of the other? Reply with just the number.", g_necklace()),
    ("hm8", "What is the multiplicative inverse of 17 modulo 101 (the integer x in 1..100 with 17x = 1 mod 101)? Reply with just the number.", g_modinv()),
    ("hm9", "In how many ways can the integer 20 be written as a sum of at most 4 positive integers (order does not matter)? Reply with just the number.", g_partitions()),
    ("hm10", "What is the number of trailing zeros of 50! when 50! is written in base 12? Reply with just the number.", g_trailingbase12()),
    ("hm11", "How many integers n with 1<=n<=200 can be written as a sum of two perfect squares (squares of non-negative integers, e.g. 0,1,4,9,...)? Reply with just the number.", g_sqsum()),
]

# ---------------- CODING: fraction-graded, with reference solutions to validate the test lists ----------------
CODE = [
 ("hc1", "is_valid_roman",
  "Write a Python function `is_valid_roman(s: str) -> bool` returning True iff s is a STRICTLY valid Roman numeral (1..3999): standard form only — no more than three consecutive identical of I/X/C/M, V/L/D never repeated, and only valid subtractive pairs IV IX XL XC CD CM. Empty string is invalid. Return only a python code block.",
  ["assert is_valid_roman('MCMXCIV') is True","assert is_valid_roman('IIII') is False","assert is_valid_roman('VV') is False","assert is_valid_roman('IL') is False","assert is_valid_roman('XIX') is True","assert is_valid_roman('MMMM') is False","assert is_valid_roman('') is False","assert is_valid_roman('IC') is False","assert is_valid_roman('MMMCMXCIX') is True","assert is_valid_roman('ABC') is False","assert is_valid_roman('IXI') is False","assert is_valid_roman('XLII') is True"],
  "def is_valid_roman(s):\n  import re\n  if not s: return False\n  if not re.fullmatch(r'M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', s): return False\n  return True"),
 ("hc2", "add_fractions",
  "Write a Python function `add_fractions(a, b, c, d)` that adds the fractions a/b + c/d and returns a tuple (num, den) in lowest terms with den > 0 (and num=0 -> (0,1)). Denominators b,d are nonzero (may be negative). Return only a python code block.",
  ["assert add_fractions(1,2,1,3)==(5,6)","assert add_fractions(1,2,-1,2)==(0,1)","assert add_fractions(2,4,1,4)==(3,4)","assert add_fractions(1,-2,1,2)==(0,1)","assert add_fractions(-1,3,-1,6)==(-1,2)","assert add_fractions(3,1,4,1)==(7,1)","assert add_fractions(1,2,1,-3)==(1,6)","assert add_fractions(0,5,0,7)==(0,1)","assert add_fractions(5,10,5,10)==(1,1)","assert add_fractions(1,6,1,6)==(1,3)"],
  "def add_fractions(a,b,c,d):\n  from math import gcd\n  num=a*d+c*b; den=b*d\n  if den<0: num,den=-num,-den\n  if num==0: return (0,1)\n  g=gcd(abs(num),abs(den)); return (num//g, den//g)"),
 ("hc3", "days_between",
  "Write a Python function `days_between(y1,m1,d1,y2,m2,d2) -> int` returning the number of days between two valid proleptic Gregorian calendar dates (absolute value; order-independent), using correct leap-year rules. Same date -> 0. Return only a python code block.",
  ["assert days_between(2000,1,1,2000,1,2)==1","assert days_between(2000,1,1,2001,1,1)==366","assert days_between(2001,1,1,2002,1,1)==365","assert days_between(1900,2,28,1900,3,1)==1","assert days_between(2000,2,28,2000,3,1)==2","assert days_between(2024,2,28,2024,3,1)==2","assert days_between(2020,3,1,2020,2,28,)==2","assert days_between(1999,12,31,2000,1,1)==1","assert days_between(2100,2,28,2100,3,1)==1","assert days_between(2023,6,15,2023,6,15)==0"],
  "def days_between(y1,m1,d1,y2,m2,d2):\n  import datetime\n  return abs((datetime.date(y2,m2,d2)-datetime.date(y1,m1,d1)).days)"),
 ("hc5", "to_base",
  "Write a Python function `to_base(n: int, b: int) -> str` converting integer n (may be negative or zero) to its representation in base b (2<=b<=36), using digits 0-9 then lowercase a-z, with a leading '-' for negatives and '0' for zero. Return only a python code block.",
  ["assert to_base(0,2)=='0'","assert to_base(10,2)=='1010'","assert to_base(255,16)=='ff'","assert to_base(-255,16)=='-ff'","assert to_base(35,36)=='z'","assert to_base(36,36)=='10'","assert to_base(-1,2)=='-1'","assert to_base(1000,10)=='1000'","assert to_base(31,32)=='v'","assert to_base(-8,8)=='-10'"],
  "def to_base(n,b):\n  if n==0: return '0'\n  digs='0123456789abcdefghijklmnopqrstuvwxyz'; neg=n<0; n=abs(n); out=''\n  while n: out=digs[n%b]+out; n//=b\n  return ('-' if neg else '')+out"),
]

# ---------------- TRAP QA: classic traps with clean short answers ----------------
QA = [
 ("hq1", "A farmer has 17 sheep. All but 9 die. How many sheep are left alive? Reply with just the number.", ["9"]),
 ("hq2", "If you are running a race and you overtake the person in 2nd place, what place are you in now? Reply with just the ordinal (e.g. 1st, 2nd).", ["2nd", "second", "2"]),
 ("hq3", "How many of the twelve months of the year have 28 days? Reply with just the number.", ["12", "twelve"]),
 ("hq4", "Divide 30 by one half, then add ten. What is the result? Reply with just the number.", ["70"]),
 ("hq5", "How many days were in the month of February in the year 1900? Reply with just the number.", ["28"]),
 ("hq6", "Some months have 31 days, some have 30. How many have exactly 30 days? Reply with just the number.", ["4", "four"]),
]


def validate():
    # math golds are computed, so they are correct by construction; just sanity print
    for cid, _, g in MATH:
        assert isinstance(g, int)
    # validate coding test lists with reference solutions (where provided)
    for cid, fn, prompt, tlist, ref in CODE:
        if ref is None:
            continue
        grader = tasks.code_grader_frac(tlist, func_required=fn)
        frac = grader("```python\n" + ref + "\n```")
        assert frac == 1.0, f"{cid} reference only scores {frac}; fix tests/ref"
    print("validation OK (math golds computed; coding refs pass 1.0)")


def build_items():
    items = []
    for cid, prompt, gold in MATH:
        items.append({"id": cid, "discipline": "math", "difficulty": "hard", "prompt": prompt,
                      "grade": tasks.numeric_grader(gold), "frac": None, "gold": gold})
    for cid, fn, prompt, tlist, ref in CODE:
        items.append({"id": cid, "discipline": "coding", "difficulty": "hard", "prompt": prompt,
                      "grade": tasks.code_grader_frac(tlist, func_required=fn), "frac": True,
                      "gold": fn, "tests": tlist})
    for cid, prompt, accepts in QA:
        items.append({"id": cid, "discipline": "qa", "difficulty": "hard", "prompt": prompt,
                      "grade": tasks.qa_grader(accepts), "frac": None, "gold": accepts[0]})
    return items


def main():
    validate()
    items = build_items()
    print(f"\n== gpt-5.5 solo over {len(items)} candidates (temp 0, single attempt) ==")
    labelset = []
    for it in items:
        mt = 8000 if it["discipline"] == "coding" else 3000
        r = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}], max_tokens=mt)
        score = it["grade"](r["text"])  # fraction for coding, bool for math/qa
        score = float(score)
        labelset.append({"id": it["id"], "discipline": it["discipline"], "prompt": it["prompt"],
                         "gpt55_score": score, "gpt55_usd": r["usd"], "gold": it["gold"]})
        print(f"  {it['id']:5} {it['discipline']:7} gpt5.5 score={score:.2f}")
    CACHE.save()

    kept = [l for l in labelset if l["gpt55_score"] < 1.0]
    by = {}
    for l in labelset:
        by.setdefault(l["discipline"], []).append(l["gpt55_score"])
    print("\n== gpt-5.5 solo accuracy by family (all candidates) ==")
    for d, ss in by.items():
        print(f"  {d:7} mean score={sum(ss)/len(ss):.3f}  ({sum(1 for s in ss if s==1.0)}/{len(ss)} fully solved)")
    overall = sum(l["gpt55_score"] for l in labelset) / len(labelset)
    print(f"\noverall gpt-5.5 mean score over candidates: {overall:.3f}")
    print(f"items with headroom (score<1.0): {len(kept)}/{len(labelset)} -> {[l['id'] for l in kept]}")
    json.dump(labelset, open(os.path.join(HERE, "labelset_hard.json"), "w"), indent=1)
    print("wrote labelset_hard.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
