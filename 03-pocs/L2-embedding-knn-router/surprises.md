# Surprises — L2 Embedding k-NN Router

## 1. k=1 beats always-cheap out of the box (90.9% vs 81.8%)

The single nearest neighbor already provides a real accuracy signal. Before any threshold
tuning, even the crudest k-NN vote correctly identifies that hard math problems need a strong
model — because the hard math prompts (m9–m15) embed close to each other and share the same
`cheap_correct=False` label. The accuracy jump from 81.8% to 90.9% at k=1 happens for free.

## 2. Low thresholds (0.4–0.6) collapse to "mostly cheap" — threshold=0.7 is the jump point

With threshold=0.4 or 0.5, the router routes 91–100% of items to cheap regardless of k. The
hard math items' neighbor votes concentrate around 0.6–0.7 (not 0.0 as you might expect,
because some math neighbors ARE cheap-correct). Crossing threshold=0.7 is the first point
where those hard items actually get escalated to strong, jumping accuracy from 90.9% to 95.5%.
This means the threshold is not a smooth dial — it has a step at ~0.67.

## 3. k=7 with threshold=0.7 is the best single-point — not k=3

Intuitively k=3 (local) should outperform k=7 (more global) when the suite has tight clusters.
In practice k=7 finds the cheapest path to 95.5% accuracy ($0.00136 vs $0.00143 for k=3).
With more neighbors, the strong-signal from one very similar hard-math neighbor gets diluted
just enough to avoid over-routing on borderline items — a slight over-fitting avoidance effect.

## 4. numpy 2.0.2 fires a spurious `divide by zero` RuntimeWarning on `@` for large float64 matrices

Normalized 22×1536 @ 1536×23 triggers the warning even though no values are actually
zero or infinite. The fix is to use `np.dot(Q_norm, T_norm.T)` which is numerically
identical but avoids triggering the numpy 2.0 internal broadcasting path that raises the
warning. Documented in the code with a comment.

## 5. Embedding cache must be separate from the harness chat cache

The first version used `.cache.json` for both `EmbedCache` (stores `prompt -> [float]`) and
the harness `Cache` (stores `sha256_key -> {text, tokens, usd, ...}`). They collide on
`np.array()` since the cache file has mixed-type values. Fixed by using `.embed-cache.json`
and `.chat-cache.json` as separate files — the embedding file is keyed by raw prompt text,
the chat file by the harness's sha256 scheme.

## 6. The k-NN router does NOT close the gap to the oracle ($0.00122)

The oracle costs $0.00122 (11% of strong cost). The best k-NN config costs $0.00136 (12%
of strong cost). The gap — $0.00014 — comes from the router routing some items to strong
that cheap could handle. Oracle-level cost would require knowing exactly which items need
strong; the router's embedding signal correctly identifies the hard math cluster but
over-escalates on a few borderline items in the test split.
