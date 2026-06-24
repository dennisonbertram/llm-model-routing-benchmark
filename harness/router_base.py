"""Router base classes + the live evaluation loop.

A Router turns a task item into an answer, possibly making one or more REAL model calls. The
two extension points:
  - SingleModelRouter.choose(item) -> model_id           (heuristic / predictive / cascade pick)
  - Router.answer(item) -> dict                            (ensembles override this directly)

run_suite(router, items, cache) executes the router live over the items, grades each with the
item's deterministic grader, and returns a metrics.RunResult.
"""
import time

from metrics import RunResult


class Router:
    name = "router"

    def __init__(self, cache=None):
        self.cache = cache

    def _chat(self, model, prompt, max_tokens=512, temperature=0.0, system=None, nonce=None):
        if self.cache is not None:
            return self.cache.chat(model, [{"role": "user", "content": prompt}],
                                   max_tokens=max_tokens, temperature=temperature, system=system, nonce=nonce)
        from providers import chat
        return chat(model, [{"role": "user", "content": prompt}],
                    max_tokens=max_tokens, temperature=temperature, system=system)

    def answer(self, item):
        """Return {text, usd, latency_ms, models, decision}. Default = single model from choose()."""
        raise NotImplementedError


class SingleModelRouter(Router):
    """Routes each item to exactly one model chosen by choose()."""
    name = "single"

    def choose(self, item):
        raise NotImplementedError

    def answer(self, item):
        model = self.choose(item)
        r = self._chat(model, item["prompt"], max_tokens=_budget(item))
        return {"text": r["text"], "usd": r["usd"], "latency_ms": r["latency_ms"],
                "models": [model], "decision": model}


class FixedModel(SingleModelRouter):
    def __init__(self, model, cache=None):
        super().__init__(cache)
        self.model = model
        self.name = f"always:{model}"

    def choose(self, item):
        return self.model


def _budget(item):
    # Coding answers need room; closed answers are tiny.
    return 700 if item["discipline"] == "coding" else 256


def run_suite(router, items, cache=None, verbose=False):
    res = RunResult(router.name)
    for it in items:
        t0 = time.time()
        out = router.answer(it)
        correct = it["grade"](out["text"])
        res.add(it, correct, out["usd"], out.get("latency_ms", int((time.time() - t0) * 1000)),
                out["models"], out.get("decision"))
        if verbose:
            print(f"  [{it['id']:>4}|{it['difficulty']:<4}] {router.name:<22} "
                  f"{'OK ' if correct else 'XX '} ${out['usd']:.2e} -> {out.get('decision')}")
    return res
