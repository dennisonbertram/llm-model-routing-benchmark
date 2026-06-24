"""Task suites for routing experiments — coding (primary), math, qa.

Each task is a dict: {id, discipline, difficulty, prompt, grade(answer)->bool, gold}.
Graders are DETERMINISTIC (numeric match / unit-test execution / normalized QA match) so the
benchmark is reproducible without LLM-judge noise. (judge.py provides an LLM judge for the
open-ended ensemble POCs that genuinely need one.)

Tasks are authored here (not copied from a licensed dataset). Each suite deliberately mixes
EASY items (a cheap model should get) and HARD items (typically need a strong model) — that gap
is what makes routing measurable. The split is validated empirically in L0, not assumed.
"""
import re
import subprocess
import sys
import tempfile
import os


# ----------------------------- grading helpers -----------------------------
def _last_int(text):
    nums = re.findall(r"-?\d+", text.replace(",", ""))
    return int(nums[-1]) if nums else None


def numeric_grader(gold):
    def g(answer):
        return _last_int(answer) == gold
    return g


def qa_grader(acceptable):
    """Normalized match: answer contains one of the acceptable strings (case/punct-insensitive)."""
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
    accepts = [norm(a) for a in acceptable]

    def g(answer):
        a = norm(answer)
        return any(acc in a for acc in accepts)
    return g


def extract_code(text):
    """Pull the first python code block; fall back to the whole text."""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1)
    return text


def code_grader_frac(test_list, func_required=None, timeout=12):
    """Like code_grader but returns the FRACTION of independent assert-cases that pass, in [0,1].
    `test_list` is a list of standalone assert strings; each runs in its own subprocess so one
    failure doesn't mask the rest. This fraction is the AB-MCTS node-evaluator score (a candidate
    that passes 7/10 hidden cases scores 0.7). A grader callable returning bool is derived as
    `frac(answer) == 1.0` for back-compat with run_suite's pass/fail accounting."""
    def frac(answer):
        code = extract_code(answer)
        if func_required and func_required not in code:
            return 0.0
        passed = 0
        for t in test_list:
            prog = code + "\n\n" + t + "\nprint('CASE_OK')\n"
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(prog); path = f.name
            try:
                r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
                if r.returncode == 0 and "CASE_OK" in r.stdout:
                    passed += 1
            except subprocess.TimeoutExpired:
                pass
            finally:
                os.unlink(path)
        return passed / len(test_list)
    return frac


def code_grader(tests, func_required=None, timeout=12):
    """Return a grader that writes the candidate code + `tests` to a temp file and runs it.
    Passes iff the subprocess exits 0. `tests` should `assert` behavior and may print 'ALL_OK'."""
    def g(answer):
        code = extract_code(answer)
        if func_required and func_required not in code:
            return False
        prog = code + "\n\n" + tests + "\nprint('ALL_OK')\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(prog)
            path = f.name
        try:
            r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
            return r.returncode == 0 and "ALL_OK" in r.stdout
        except subprocess.TimeoutExpired:
            return False
        finally:
            os.unlink(path)
    return g


# ----------------------------- MATH suite -----------------------------
_MATH = [
    ("m1", "easy", "What is 17 + 25? Reply with just the number.", 42),
    ("m2", "easy", "What is 144 / 12? Reply with just the number.", 12),
    ("m3", "easy", "A shirt costs $20 and is 25% off. What is the sale price in dollars? Reply with just the number.", 15),
    ("m4", "easy", "What is 7 * 8? Reply with just the number.", 56),
    ("m5", "med", "A train travels 60 km in 45 minutes. How many km does it travel in 3 hours at the same speed? Reply with just the number.", 240),
    ("m6", "med", "If 3x + 7 = 28, what is x? Reply with just the number.", 7),
    ("m7", "med", "A rectangle has area 48 and width 6. What is its perimeter? Reply with just the number.", 28),
    ("m8", "hard", "There are 5 red, 3 blue and 2 green balls. You draw 2 without replacement. In how many of the C(10,2)=45 equally likely pairs are both balls the same color? Reply with just the number.", 14),
    ("m9", "hard", "Find the number of integers from 1 to 100 inclusive that are divisible by 3 or 5. Reply with just the number.", 47),
    ("m10", "hard", "A number is doubled, then 6 is added, then the result is halved, giving 19. What was the original number? Reply with just the number.", 16),
    ("m11", "hard", "How many trailing zeros are in 25! (25 factorial)? Reply with just the number.", 6),
    ("m12", "hard", "The sum of three consecutive even integers is 78. What is the largest of them? Reply with just the number.", 28),
    # The following three were live-confirmed to discriminate (gpt-4.1 solves; gpt-4o-mini fails).
    ("m13", "hard", "At a party every pair of the 9 guests shakes hands exactly once, EXCEPT two specific guests refuse to shake each other's hand. How many handshakes occur? Reply with just the number.", 35),
    ("m14", "hard", "How many ways are there to make 100 cents using any number of pennies(1), nickels(5), dimes(10), and quarters(25)? Reply with just the number.", 242),
    ("m15", "hard", "In how many distinct ways can the letters of the word 'BALLOON' be arranged? Reply with just the number.", 1260),
]
MATH = [{"id": i, "discipline": "math", "difficulty": d, "prompt": p,
         "grade": numeric_grader(g), "gold": g} for (i, d, p, g) in _MATH]


# ----------------------------- QA suite -----------------------------
_QA = [
    ("q1", "easy", "What is the capital of France? Answer with just the city name.", ["paris"]),
    ("q2", "easy", "What chemical element has the symbol 'O'? Answer with one word.", ["oxygen"]),
    ("q3", "easy", "How many continents are there on Earth? Answer with just the number.", ["7", "seven"]),
    ("q4", "easy", "What planet is known as the Red Planet? One word.", ["mars"]),
    ("q5", "med", "Who wrote the play 'Romeo and Juliet'? Answer with the surname.", ["shakespeare"]),
    ("q6", "med", "In what year did the Apollo 11 mission first land humans on the Moon? Just the year.", ["1969"]),
    ("q7", "med", "What is the largest internal organ of the human body? One or two words.", ["liver"]),
    ("q8", "hard", "What is the time complexity of binary search on a sorted array of n elements, in Big-O? Answer like O(...).", ["o(log n)", "olog n", "o(logn)"]),
    ("q9", "hard", "Which data structure uses FIFO (first-in, first-out) ordering? One word.", ["queue"]),
    ("q10", "hard", "In Python, which built-in function returns the number of items in a list? One word.", ["len"]),
    ("q11", "hard", "What HTTP status code means 'Not Found'? Just the number.", ["404"]),
    ("q12", "hard", "What is the name of the consensus algorithm used by Raft's competitor that uses leader election and is known for being hard to understand? One word.", ["paxos"]),
]
QA = [{"id": i, "discipline": "qa", "difficulty": d, "prompt": p,
       "grade": qa_grader(a), "gold": a[0]} for (i, d, p, a) in _QA]


# ----------------------------- CODING suite -----------------------------
# Each: (id, difficulty, prompt, func_name, tests-as-assert-string)
_CODE = [
    ("c1", "easy",
     "Write a Python function `is_palindrome(s: str) -> bool` that returns True iff s reads the same forwards and backwards (consider the string exactly as given). Return only a python code block.",
     "is_palindrome",
     "assert is_palindrome('abba') is True\nassert is_palindrome('abc') is False\nassert is_palindrome('') is True"),
    ("c2", "easy",
     "Write a Python function `fizzbuzz(n: int) -> str` returning 'Fizz' if n divisible by 3, 'Buzz' if by 5, 'FizzBuzz' if by both, else str(n). Return only a python code block.",
     "fizzbuzz",
     "assert fizzbuzz(3)=='Fizz'\nassert fizzbuzz(5)=='Buzz'\nassert fizzbuzz(15)=='FizzBuzz'\nassert fizzbuzz(7)=='7'"),
    ("c3", "easy",
     "Write a Python function `two_sum(nums, target)` returning a list of two indices i<j such that nums[i]+nums[j]==target, or None. Return only a python code block.",
     "two_sum",
     "r=two_sum([2,7,11,15],9)\nassert r==[0,1]\nassert two_sum([1,2,3],100) is None"),
    ("c4", "easy",
     "Write a Python function `count_vowels(s: str) -> int` returning the number of vowels (a,e,i,o,u, case-insensitive) in s. Return only a python code block.",
     "count_vowels",
     "assert count_vowels('Hello')==2\nassert count_vowels('xyz')==0\nassert count_vowels('AEIOU')==5"),
    ("c5", "med",
     "Write a Python function `valid_parentheses(s: str) -> bool` that returns True iff the brackets in s (containing only '()[]{}') are balanced and correctly nested. Return only a python code block.",
     "valid_parentheses",
     "assert valid_parentheses('()[]{}') is True\nassert valid_parentheses('(]') is False\nassert valid_parentheses('([{}])') is True\nassert valid_parentheses('(') is False"),
    ("c6", "med",
     "Write a Python function `merge_intervals(intervals)` that merges overlapping [start,end] intervals and returns the merged list sorted by start. Return only a python code block.",
     "merge_intervals",
     "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]])==[[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]])==[[1,5]]"),
    ("c7", "med",
     "Write a Python function `roman_to_int(s: str) -> int` converting a Roman numeral string (I,V,X,L,C,D,M) to its integer value. Return only a python code block.",
     "roman_to_int",
     "assert roman_to_int('III')==3\nassert roman_to_int('IV')==4\nassert roman_to_int('MCMXciv'.upper())==1994\nassert roman_to_int('LVIII')==58"),
    ("c8", "hard",
     "Write a Python function `length_of_longest_substring(s: str) -> int` returning the length of the longest substring of s without repeating characters. Return only a python code block.",
     "length_of_longest_substring",
     "assert length_of_longest_substring('abcabcbb')==3\nassert length_of_longest_substring('bbbbb')==1\nassert length_of_longest_substring('pwwkew')==3\nassert length_of_longest_substring('')==0"),
    ("c9", "hard",
     "Write a Python function `longest_increasing_subsequence(nums) -> int` returning the length of the longest strictly increasing subsequence. Return only a python code block.",
     "longest_increasing_subsequence",
     "assert longest_increasing_subsequence([10,9,2,5,3,7,101,18])==4\nassert longest_increasing_subsequence([0,1,0,3,2,3])==4\nassert longest_increasing_subsequence([7,7,7,7])==1"),
    ("c10", "hard",
     "Write a Python function `coin_change(coins, amount) -> int` returning the fewest number of coins to make `amount`, or -1 if impossible. Return only a python code block.",
     "coin_change",
     "assert coin_change([1,2,5],11)==3\nassert coin_change([2],3)==-1\nassert coin_change([1],0)==0"),
    ("c11", "hard",
     "Write a Python function `word_break(s: str, wordDict) -> bool` returning True iff s can be segmented into a space-separated sequence of words from wordDict. Return only a python code block.",
     "word_break",
     "assert word_break('leetcode',['leet','code']) is True\nassert word_break('applepenapple',['apple','pen']) is True\nassert word_break('catsandog',['cats','dog','sand','and','cat']) is False"),
    ("c12", "hard",
     "Write a Python function `eval_rpn(tokens) -> int` evaluating Reverse Polish Notation (operators +,-,*,/ with truncation toward zero). Return only a python code block.",
     "eval_rpn",
     "assert eval_rpn(['2','1','+','3','*'])==9\nassert eval_rpn(['4','13','5','/','+'])==6\nassert eval_rpn(['10','6','9','3','+','-11','*','/','*','17','+','5','+'])==22"),
    ("c13", "hard",
     "Write a Python function `is_match(s: str, p: str) -> bool` implementing regular-expression matching where '.' matches any single char and '*' matches zero or more of the preceding element; the match must cover the ENTIRE string s. Return only a python code block.",
     "is_match",
     "assert is_match('aa','a') is False\nassert is_match('aa','a*') is True\nassert is_match('ab','.*') is True\nassert is_match('mississippi','mis*is*p*.') is False\nassert is_match('aab','c*a*b') is True"),
    ("c14", "hard",
     "Write a Python function `min_window(s: str, t: str) -> str` returning the minimum-length substring of s containing every character of t (with multiplicity), or '' if none exists. Return only a python code block.",
     "min_window",
     "assert min_window('ADOBECODEBANC','ABC')=='BANC'\nassert min_window('a','a')=='a'\nassert min_window('a','aa')==''"),
    ("c15", "hard",
     "Write a Python function `edit_distance(a: str, b: str) -> int` returning the Levenshtein edit distance (insert/delete/replace each cost 1) between a and b. Return only a python code block.",
     "edit_distance",
     "assert edit_distance('horse','ros')==3\nassert edit_distance('intention','execution')==5\nassert edit_distance('','abc')==3"),
    ("c16", "hard",
     "Write a Python function `trap(height) -> int` returning how much rain water is trapped between the bars given by the list `height`. Return only a python code block.",
     "trap",
     "assert trap([0,1,0,2,1,0,1,3,2,1,2,1])==6\nassert trap([4,2,0,3,2,5])==9\nassert trap([])==0"),
    ("c17", "hard",
     "Write a Python function `decode_ways(s: str) -> int` returning the number of ways to decode a digit string where '1'->'A' ... '26'->'Z' (a leading zero or invalid pair contributes 0 ways). Return only a python code block.",
     "decode_ways",
     "assert decode_ways('12')==2\nassert decode_ways('226')==3\nassert decode_ways('06')==0\nassert decode_ways('0')==0"),
    # Live-confirmed discriminator: spec-precise validation with many edge cases (gpt-4o-mini fails on the cheap end).
    ("c18", "hard",
     "Write a Python function `is_number(s: str) -> bool` returning True iff s is a valid number: an optional leading sign, an integer or decimal (a decimal point with digits on at least one side), and an optional exponent 'e'/'E' followed by an optional sign and an integer. No surrounding whitespace is allowed. Return only a python code block.",
     "is_number",
     "assert is_number('0') is True\nassert is_number('-1.5e10') is True\nassert is_number('.5') is True\nassert is_number('3.') is True\nassert is_number('abc') is False\nassert is_number('1e') is False\nassert is_number('1 ') is False\nassert is_number('e9') is False"),
]
CODING = [{"id": i, "discipline": "coding", "difficulty": d, "prompt": p,
           "grade": code_grader(t, func_required=fn), "gold": fn} for (i, d, p, fn, t) in _CODE]


SUITES = {"math": MATH, "qa": QA, "coding": CODING}
ALL = MATH + QA + CODING


def suite(name):
    return SUITES[name]


def get(*names):
    out = []
    for n in names:
        out.extend(SUITES[n])
    return out
