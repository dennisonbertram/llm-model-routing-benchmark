"""On-disk response cache so re-running the SAME deterministic (model, prompt) pair does not
re-bill or re-introduce noise. Critical for the benchmark POC, where many routers evaluate
overlapping (model, item) pairs — without a cache the benchmark would be costly and its accuracy
numbers would wobble between runs.

Cache key = sha256 of (model, messages, system, temperature, max_tokens, nonce). For sampling
(temperature > 0) pass a distinct `nonce` per sample so each sample is its own cache entry and is
not collapsed to one response.

The cache stores the full normalized provider result EXCEPT it marks `cached: True` and zeroes
latency on a hit (a cached call did no live work). Cost (`usd`) is preserved so the *first* time a
pair is run is the billed event; the benchmark reports cost as if each unique pair were paid once.
NOT process-safe — use one cache per POC during parallel work; the serial benchmark/capstone may
share one.
"""
import hashlib
import json
import os

from providers import chat as _live_chat


class Cache:
    def __init__(self, path):
        self.path = path
        self.data = {}
        self.hits = 0
        self.misses = 0
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def _key(self, model, messages, system, temperature, max_tokens, nonce):
        blob = json.dumps([model, messages, system, temperature, max_tokens, nonce], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def chat(self, model, messages, max_tokens=512, temperature=0.0, system=None, nonce=None,
             nocache=False, **kw):
        if nocache:
            return _live_chat(model, messages, max_tokens=max_tokens, temperature=temperature,
                              system=system, **kw)
        k = self._key(model, messages, system, temperature, max_tokens, nonce)
        if k in self.data:
            self.hits += 1
            r = dict(self.data[k])
            r["cached"] = True
            return r
        self.misses += 1
        r = _live_chat(model, messages, max_tokens=max_tokens, temperature=temperature,
                       system=system, **kw)
        r["cached"] = False
        self.data[k] = r
        return r

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f)

    def stats(self):
        return {"hits": self.hits, "misses": self.misses, "entries": len(self.data)}
