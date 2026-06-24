# Surprises (live)

1. **Canonical coding problems are memorized — they do not discriminate model strength.**
   `gpt-4.1-nano` (the cheapest model) solved all 18 coding tasks, including the supposedly "hard"
   ones (regex matching `is_match`, min-window-substring, edit distance, coin change, word break).
   We had to hunt for a spec-precise edge-case task (`is_number`) to find a coding task a cheap
   model fails. Lesson: a routing benchmark built on LeetCode-style problems will look like
   "always route cheap" because cheap *is* enough — the real discrimination is elsewhere.

2. **The gap lives in multi-step reasoning math.** All 6 tasks that only `gpt-4.1` solves are
   combinatorics/word-problem math (handshakes-with-exception, coin-change counting, distinct
   permutations of BALLOON, etc.). The classic "bat and ball costs $1.10" trap is now solved by
   even nano — models have absorbed it.

3. **Cheap-model accuracy is non-monotonic.** `gpt-4o-mini` failed `m14` (coin change count) that
   `gpt-4.1-nano` got right. "Cheaper ⇒ worse" is false per-item; it only holds in aggregate. A
   router that assumes a strict capability ladder will mis-route.

4. **Reasoning models return empty content under a tight budget.** `gpt-5-mini` with
   `max_completion_tokens=16` returned `''` (the budget was consumed by hidden reasoning).
   Fixed with `REASONING_FLOOR=2048` in the harness. This is the #1 "why is my gpt-5 call blank"
   gotcha.

5. **`grok-4.3` hides reasoning tokens from `completion_tokens` but bills them.** A trivial call
   reported `completion_tokens=1` with `total_tokens=232`. Uniform `tokens × price` undercounts
   unless you bill `total − prompt`; even then it diverges ~1.5× from xAI's native
   `cost_in_usd_ticks / 1e10`. We compute cost uniformly for cross-model fairness but record
   grok's native ticks for transparency. (The ticks scale is `1e10` per USD per xAI's cost-tracking
   docs — NOT `1e9`, which we initially assumed and corrected.)
