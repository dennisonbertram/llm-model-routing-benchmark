# G-009: numpy 2.0 emits spurious "divide by zero in matmul" warnings on clean inputs

**Category**: gotcha
**Severity**: low
**Evidence tier**: Live verified
**Source POC**: L2-embedding-knn-router

## What

Live verified. On macOS with numpy 2.0.2, normalizing a 22×1536 float64 matrix and computing the dot product via the `@` operator against a 1536×23 matrix fires a `RuntimeWarning: divide by zero encountered in matmul` even when no input values are zero or infinite.

Example trigger:
```python
import numpy as np
Q_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
T_norm = train_embeddings / np.linalg.norm(train_embeddings, axis=1, keepdims=True)
sims = Q_norm @ T_norm.T   # fires RuntimeWarning on numpy 2.0.2
```

The warning fires due to a numpy 2.0 internal broadcasting path change, not due to actual numerical issues in the data. The result is numerically correct.

## Why it matters

Spurious warnings in an embedding-based routing harness pollute the output, hide real warnings, and may cause CI pipelines that treat warnings as errors to fail. The warning is particularly confusing because the input data is clean — normalized cosine similarity vectors have no zeros or infinities.

## Root cause

numpy 2.0 changed the internal dispatch path for the `@` matrix-multiplication operator on large float64 arrays. The warning is a false positive — it fires in a code path that checks for division by zero but is not actually triggered by any data in the inputs. Reported as a numpy regression on macOS ARM. The `np.dot()` function uses a different dispatch path and does not trigger the warning.

## Fix

Replace the `@` operator with `np.dot()` for cosine similarity computations in embedding routers:

```python
# Before (triggers spurious warning on numpy 2.0.2):
sims = Q_norm @ T_norm.T

# After (numerically identical, no warning):
sims = np.dot(Q_norm, T_norm.T)
```

Add a comment explaining why `np.dot` is used instead of `@` so the next reader does not "fix" it back. If you need to suppress the warning rather than eliminate it:

```python
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    sims = Q_norm @ T_norm.T
```

## Regression note

The fix is cosmetic — the numeric output is identical. No correctness regression test is needed, but confirm that the switch to `np.dot` does not change any accuracy numbers in the k-NN router's test results (they should be exactly equal).

## Evidence

- Source: `03-pocs/L2-embedding-knn-router/surprises.md`, item 4: "numpy 2.0.2 fires a spurious `divide by zero` RuntimeWarning on `@` for large float64 matrices. Normalized 22×1536 @ 1536×23 triggers the warning even though no values are actually zero or infinite. The fix is to use `np.dot(Q_norm, T_norm.T)` which is numerically identical but avoids triggering the numpy 2.0 internal broadcasting path that raises the warning. Documented in the code with a comment." (Live verified)
- Source: results-digest.md, Gotchas item 9: "numpy 2.0 on macOS emits spurious 'divide by zero in matmul' warnings on clean inputs — suppress." (Live verified)
