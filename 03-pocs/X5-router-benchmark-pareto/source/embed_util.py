"""Cached live embeddings (text-embedding-3-small) for the benchmark + predictive routers."""
import hashlib
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
from providers import embed  # noqa: E402

_DISK = os.path.join(os.path.dirname(__file__), ".emb_cache.json")


def get_embeddings(texts, cache=None, model="text-embedding-3-small"):
    """Return a list of embedding vectors for `texts`, embedding (live) only the uncached ones."""
    store = {}
    if os.path.exists(_DISK):
        store = json.load(open(_DISK))
    out = [None] * len(texts)
    todo = []
    todo_idx = []
    for i, t in enumerate(texts):
        k = hashlib.sha256((model + "\n" + t).encode()).hexdigest()
        if k in store:
            out[i] = store[k]
        else:
            todo.append(t)
            todo_idx.append((i, k))
    if todo:
        vecs, _usd = embed(todo, model=model)
        for (i, k), v in zip(todo_idx, vecs):
            out[i] = v
            store[k] = v
        json.dump(store, open(_DISK, "w"))
    return out
