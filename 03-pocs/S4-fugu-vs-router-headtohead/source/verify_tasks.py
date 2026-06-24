"""Fresh, independent task set for the Fugu-vs-router head-to-head (S4).

15 NEW tasks (not reused from S0-S3), deterministically graded, spanning easy -> hard-for-cheap.
Math golds are computed by brute force here (provably correct); coding tests validated against
reference solutions; trap/QA with exact accept-lists. "hard" means hard for the CHEAP model
(gpt-4o-mini) — the routing signal — not necessarily hard for gpt-5.5. Includes deceptive items
(hard but short-prompt) to adversarially stress the router into mis-routing.
"""
import math
import os
import sys
from itertools import permutations

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
import tasks as T  # noqa: E402


# ---- math golds computed ----
def g_divisible():  # 1..1000 divisible by 6 but not by 4 and not by 9
    return sum(1 for n in range(1, 1001) if n % 6 == 0 and n % 4 != 0 and n % 9 != 0)
def g_domino():  # 2x10 domino tilings = Fib with f(1)=1,f(2)=2
    a, b = 1, 2
    for _ in range(8):
        a, b = b, a + b
    return b  # f(10)
def g_derange():  # derangements of 4
    return sum(1 for p in permutations(range(4)) if all(p[i] != i for i in range(4)))
def g_lastdigit():  # last digit of 3^1000
    return pow(3, 1000, 10)
def g_roundtable():  # seat 6 people around a round table, rotations same = 5!
    return math.factorial(5)
def g_coins():  # ways to make 30 with 1,5,10,25 (order ignored)
    coins = [1, 5, 10, 25]; amt = 30; dp = [1] + [0] * amt
    for c in coins:
        for a in range(c, amt + 1):
            dp[a] += dp[a - c]
    return dp[amt]
def g_trailbits():  # number of 1-bits in the binary representation of 2024
    return bin(2024).count("1")

_MATH = [
    ("v_e1", "easy", "What is 13 multiplied by 7? Reply with just the number.", 91),
    ("v_e2", "easy", "What is 15 percent of 200? Reply with just the number.", 30),
    ("v_e3", "easy", "What is the sum of all integers from 1 to 20 inclusive? Reply with just the number.", 210),
    ("v_m1", "med", "How many distinct prime factors does 360 have? Reply with just the number.", 3),
    ("v_m2", "med", "How many ways can 6 people be seated around a round table if rotations are considered identical? Reply with just the number.", g_roundtable()),
    ("v_h1", "hard", "How many integers from 1 to 1000 inclusive are divisible by 6 but NOT divisible by 4 and NOT divisible by 9? Reply with just the number.", g_divisible()),
    ("v_h2", "hard", "What is the last digit of 3 raised to the power 1000? Reply with just the number.", g_lastdigit()),
    ("v_h3", "hard", "In how many ways can a 2x10 rectangular board be completely tiled by 1x2 dominoes? Reply with just the number.", g_domino()),
    ("v_h4", "hard", "In how many ways can 4 distinct letters be placed into 4 distinct envelopes so that NO letter goes into its matching envelope? Reply with just the number.", g_derange()),
    ("v_h5", "hard", "Using any number of coins worth 1, 5, 10, and 25, in how many distinct ways can you make exactly 30 (order does not matter)? Reply with just the number.", g_coins()),
    ("v_h6", "hard", "How many 1s appear in the binary (base-2) representation of the number 2024? Reply with just the number.", g_trailbits()),
]
MATH = [{"id": i, "discipline": "math", "difficulty": d, "prompt": p, "grade": T.numeric_grader(g), "gold": g}
        for (i, d, p, g) in _MATH]

# ---- qa ----
_QA = [
    ("v_q1", "easy", "What is the capital city of Japan? Answer with just the city name.", ["tokyo"]),
    ("v_q2", "easy", "What is the chemical symbol for gold? Answer with the symbol only.", ["au"]),
]
QA = [{"id": i, "discipline": "qa", "difficulty": d, "prompt": p, "grade": T.qa_grader(a), "gold": a[0]}
      for (i, d, p, a) in _QA]

# ---- coding (bool: all asserts pass) ----
_CODE = [
    ("v_c1", "easy", "Write a Python function `reverse_words(s: str) -> str` that reverses the order of words in s (words separated by single spaces, no leading/trailing spaces). Return only a python code block.",
     "reverse_words", "assert reverse_words('the quick brown fox')=='fox brown quick the'\nassert reverse_words('hello')=='hello'",
     "def reverse_words(s): return ' '.join(s.split()[::-1])"),
    ("v_c2", "med", "Write a Python function `is_anagram(a: str, b: str) -> bool` returning True iff a and b are anagrams ignoring case and spaces. Return only a python code block.",
     "is_anagram", "assert is_anagram('Listen','Silent') is True\nassert is_anagram('abc','abd') is False\nassert is_anagram('Dormitory','Dirty Room') is True",
     "def is_anagram(a,b):\n  f=lambda s:sorted(s.lower().replace(' ',''))\n  return f(a)==f(b)"),
]
CODE = [{"id": i, "discipline": "coding", "difficulty": d, "prompt": p, "grade": T.code_grader(t, func_required=fn),
         "gold": fn, "ref": ref}
        for (i, d, p, fn, t, ref) in _CODE]

ALL = MATH + QA + CODE


def validate():
    for it in CODE:
        assert it["grade"]("```python\n" + it["ref"] + "\n```"), f"{it['id']} ref fails"
    return True


if __name__ == "__main__":
    validate()
    print(f"{len(ALL)} tasks; golds: " + ", ".join(f"{it['id']}={it['gold']}" for it in MATH))
