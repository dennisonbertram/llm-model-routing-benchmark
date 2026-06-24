# G-005: Cheap-model accuracy is non-monotonic per item — "cheaper implies worse" is false

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness

## What

Live verified. `gpt-4o-mini` failed item `m14` (coin-change permutation counting) while `gpt-4.1-nano` answered it correctly. `gpt-4.1-nano` is cheaper than `gpt-4o-mini`, yet it outperformed it on a specific hard-math item.

## Why it matters

A router that models model capability as a strict ladder — "cheap < mid < strong" — and routes up the ladder when confidence is low will mis-route items where a nominally cheaper model is actually more capable. More critically, a router's training labels derived from a single cheap model (e.g., only `gpt-4o-mini`) may produce wrong "cheap_correct=False" labels for items that a different cheap model would get right. This inflates the apparent routing opportunity.

The pattern: aggregate accuracy follows the tier ladder, but per-item accuracy does not.

## Root cause

Different models in the same price tier have different training mixtures, RLHF tuning objectives, and capability profiles. A model that costs $0.15/1M tokens may have been fine-tuned on a dataset that includes the specific reasoning chain needed for a problem that a $0.40/1M model missed. Capability is multi-dimensional; price is a one-dimensional proxy.

## Fix

When building a router's training set:
1. Label each item with correctness from **the actual cheap model you will deploy**, not from a different cheap model as a proxy.
2. If you switch the cheap model (e.g., from `gpt-4o-mini` to `gpt-4.1-mini`), regenerate training labels — they are model-specific.
3. Do not assume the routing decision is transitive: routing an item from `gpt-4o-mini` to `gpt-4.1` because `gpt-4o-mini` failed does not guarantee `gpt-4.1-nano` would also fail.

When the strong model and cheap model both fail an item (as with `m8` in this suite, which both got wrong), routing to strong guarantees nothing. Verification cascades (L3b coding verifier) or oracle-level budget spending is required for zero-failure guarantees on genuinely hard items.

## Regression note

In the routing harness label generation step, assert that the cheap model ID matches the model used at inference time. If `config.CHEAP_DEFAULT` is changed, regenerate `labelset.json` and retrain any classifiers.

## Evidence

- Source: `03-pocs/L0-smoke-and-harness/surprises.md`, item 3: "`gpt-4o-mini` failed `m14` (coin change count) that `gpt-4.1-nano` got right. 'Cheaper ⇒ worse' is false per-item; it only holds in aggregate. A router that assumes a strict capability ladder will mis-route." (Live verified)
- Source: `03-pocs/L1-heuristic-router/surprises.md`, item 4: "Item m8 (ball color pairs, combinatorics) fails for BOTH cheap and strong models. The oracle assumption was that 'strong solves everything cheap fails on.' But m8 shows there are genuinely hard items that even the strong model misses." (Live verified)
- Source: results-digest.md, Gotchas item 5: "Cheap-model accuracy is NON-MONOTONIC per item (gpt-4o-mini fails things gpt-4.1-nano gets)." (Live verified)
