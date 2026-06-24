# L1 Surprising Findings

## 1. Word count is stronger than digit density

**Expected**: Math problems have many digits; they should be the strongest signal.

**Reality**: Digit density is noisy. Easy arithmetic (m1, m2, m3) has 4–5 digits in 9–20 characters,
giving 20–50% density. Hard combinatorics (m15: "BALLOON", 0% density; m10: algebra with 3 digits
in 25 words, 2% density) have low density.

**The actual signal**: Word count. Oracle targets (m9–m15) average 22 words; easy items average 10–14.
Longer prompts tend to describe multi-step, complex reasoning. **We now weight word count at 40%**
and digit density at only 10%.

---

## 2. Reasoning keywords beat digits

**Expected**: Keywords like "probability", "combinations", "factorial" would be occasional wins for signal.

**Reality**: Keywords are consistent. Hard math items reliably contain "how many", "permutations",
"consecutive", "divisible", "distinct ways", etc. Easy items rarely use these words.

**The impact**: Adding keywords like "distinct ways" and "consecutive" to the feature list caught m15
(BALLOON permutations), which had 0 digits but multiple reasoning cues.

---

## 3. Coding problems do not discriminate model strength

**Expected**: Hard coding tasks like regex, edit distance, or min-window should need strong models.

**Reality**: All coding tasks (18/18) are solved by gpt-4o-mini. The heuristic routes 5 hard coding
tasks to strong based on length + keywords, but cheap solves them fine. This is a **false positive
source**: c2, c7, c13, c18 all route to strong but could be cheap.

**Implication**: The hard gap is MATH, not coding. Canonical LeetCode problems are saturated by the
cheapest model. Only grade-school reasoning math (divisibility, combinatorics, permutations) escapes
the cheap model's reach.

---

## 4. Both models can fail; it's not just a cost-quality gap

**Unexpected**: Item m8 (ball color pairs, combinatorics) fails for BOTH cheap and strong models.

**The oracle assumption** was that "strong solves everything cheap fails on." But m8 shows there
are genuinely hard items that even the strong model misses. The oracle efficiency (10% of strong cost
at strong accuracy) assumes strong is a ceiling; m8 suggests the problem itself may be ambiguously
worded or require a capability neither model has.

**Impact on routing**: False confidence. A router cannot assume "route to strong = guaranteed success."
Verification or verification cascades (L3a, L3b) become necessary for high-stakes applications.

---

## 5. Over-routing is cheaper than under-routing in terms of measurement noise

**Observation**: At τ=0.40, we route 11 items but oracle needs 6. The cost per item is:
- Correct routing: ~$0.0002 per item
- False positive (cheap could solve): ~$0.0005 per item (cost of wasting strong model)

**Result**: 5 false positives cost ~$0.0025. But at τ=0.50 (cost $0.00317), we drop to 0.889 accuracy,
losing 5 items (vs 1 at τ=0.40). The false positives are cheaper per-item than missing one hard item.

**Implication**: Conservative routing (route more to strong when uncertain) is cost-efficient for
reliability. The "avoid over-routing" intuition fails when missing one hard item costs more than
over-routing 5 easy ones.

---

## 6. Heuristic precision doesn't improve beyond ~96% accuracy

**Observation**: Thresholds τ=0.30 and τ=0.40 both achieve 0.956 accuracy. Trying to improve beyond
this (lower τ → 0.20 at 0.978) costs >10× oracle. Going conservative (higher τ → 0.50+) drops
accuracy sharply.

**Why**: The heuristic features are coarse. Text length, keywords, and structure are binary signals;
they cannot distinguish the ~4% of hard items that need fine-grained reasoning from the ~96% that don't.

**Next steps**: Predictive routers (L2–L2b) that embed prompts and learn thresholds will break through
this plateau. Cascades (L3a) and ensembles (X1–X4) offer orthogonal improvements.

---

## 7. Problem wording confounds feature extraction

**Example**: m15 (BALLOON permutations) has 0 digits but contains "distinct ways", triggering high
complexity score. m9 ("Find the number of integers...") has high word count + "divisibility" cue.
Both are correctly routed.

**Counterexample**: m10 ("A number is doubled, then 6 is added...") has 25 words but no keywords
matching our list, giving score=0.261. It's an oracle target, but our heuristic misses it because
the wording is procedural, not combinatorial.

**Implication**: Real routing systems need domain-specific keywords or learned embeddings to capture
domain-specific complexity. A generic heuristic plateaus at 96% because natural language is ambiguous.
