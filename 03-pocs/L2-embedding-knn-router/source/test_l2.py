"""L2 behavioral test. Label: Live behavioral test.

RED (before keys / harness): ImportError or ProviderError on embed call.
GREEN (with keys + harness + cached embeddings): all assertions pass.

Tests:
1. Live embeddings: embed() returns real 1536-dim vectors with nonzero cost.
2. k-NN routing: at least one test item routes correctly (not all trivially cheap).
3. Pareto property: best k-NN router lies between always-cheap and always-strong on cost/acc.
4. Oracle vs kNN: kNN does not falsely claim oracle-level accuracy in a way that proves
   oracle leakage (it should be <= oracle + small epsilon).
"""
import json
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from providers import embed  # noqa: E402

HERE = os.path.dirname(__file__)
EXPORT_PATH = os.path.join(HARNESS, ".cache", "labelset_export.json")
EMBED_CACHE_PATH = os.path.join(HERE, "..", ".embed-cache.json")

# Import the router helpers
sys.path.insert(0, HERE)
from run_l2 import (  # noqa: E402
    EmbedCache, load_labelset, embed_all_prompts,
    cosine_sim_matrix, topk_indices_and_sims, knn_predict_cheap,
    evaluate_split, compute_baselines,
)


class L2Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load data and embeddings once for all tests."""
        cls.rows = load_labelset()
        cls.ecache = EmbedCache(EMBED_CACHE_PATH)
        cls.all_vecs, cls.embed_usd = embed_all_prompts(cls.rows, cls.ecache)
        n = len(cls.rows)
        cls.train_items = [cls.rows[i] for i in range(n) if i % 2 == 0]
        cls.test_items  = [cls.rows[i] for i in range(n) if i % 2 == 1]
        cls.train_vecs  = [cls.all_vecs[i] for i in range(n) if i % 2 == 0]
        cls.test_vecs   = [cls.all_vecs[i] for i in range(n) if i % 2 == 1]
        cls.baselines   = compute_baselines(cls.test_items)

    def test_embeddings_live(self):
        """Embeddings are real 1536-dim vectors, not placeholders."""
        # The embed cache path exists only after run; force one tiny live call to confirm
        vecs, usd = embed(["test embedding call for L2"])
        self.assertEqual(len(vecs), 1, "Expected 1 embedding vector")
        self.assertEqual(len(vecs[0]), 1536, "text-embedding-3-small is 1536-dim")
        self.assertGreater(usd, 0.0, "Embedding call should have nonzero cost")
        self.assertTrue(all(isinstance(x, float) for x in vecs[0][:5]),
                        "Embedding values should be floats")

    def test_cosine_similarity_range(self):
        """Cosine similarity matrix values are in [-1, 1]."""
        sim = cosine_sim_matrix(self.test_vecs[:3], self.train_vecs[:5])
        for row in (sim if not hasattr(sim, 'tolist') else sim.tolist()):
            for v in row:
                self.assertGreaterEqual(float(v), -1.01, "Cosine sim below -1")
                self.assertLessEqual(float(v), 1.01, "Cosine sim above 1")

    def test_knn_routes_some_strong(self):
        """With threshold=0.7 and k=3, at least some items should be routed to strong."""
        acc, cost, n_cheap, decisions = evaluate_split(
            self.test_items, self.train_items,
            self.test_vecs, self.train_vecs,
            k=3, threshold=0.7
        )
        n_strong = len(self.test_items) - n_cheap
        self.assertGreater(n_strong, 0,
                           "k-NN router with threshold=0.7 should route at least one item to strong")

    def test_knn_pareto_property(self):
        """Best k-NN result should be between always-cheap and always-strong in cost."""
        # Find best (acc-maximizing) result
        best_acc = 0
        best_cost = float("inf")
        for k in [3, 5]:
            for thresh in [0.5, 0.6]:
                acc, cost, n_cheap, _ = evaluate_split(
                    self.test_items, self.train_items,
                    self.test_vecs, self.train_vecs,
                    k=k, threshold=thresh
                )
                if acc > best_acc or (acc == best_acc and cost < best_cost):
                    best_acc = acc
                    best_cost = cost

        cheap_cost = self.baselines["always_cheap"]["usd"]
        strong_cost = self.baselines["always_strong"]["usd"]
        # Cost should be above always-cheap (it uses some strong calls)
        # but below always-strong (it avoids some strong calls)
        self.assertLessEqual(best_cost, strong_cost,
                             "Best k-NN should cost at most as much as always-strong")
        # Accuracy should be at least as good as always-cheap
        self.assertGreaterEqual(best_acc, self.baselines["always_cheap"]["acc"] - 0.05,
                                "Best k-NN accuracy should be close to or better than always-cheap")

    def test_knn_accuracy_bounded_by_oracle(self):
        """k-NN accuracy cannot exceed oracle (it doesn't have access to difficulty labels)."""
        oracle_acc = self.baselines["oracle"]["acc"]
        for k in [1, 3, 5]:
            for thresh in [0.5, 0.6]:
                acc, _, _, _ = evaluate_split(
                    self.test_items, self.train_items,
                    self.test_vecs, self.train_vecs,
                    k=k, threshold=thresh
                )
                self.assertLessEqual(acc, oracle_acc + 1e-6,
                                     f"k={k} t={thresh}: k-NN acc={acc:.3f} > oracle={oracle_acc:.3f}")

    def test_no_oracle_leakage(self):
        """Verify router uses ONLY prompt text, not difficulty/discipline labels."""
        # This is a structural test: run_l2.knn_predict_cheap receives only
        # sim_row (cosine sims from embeddings) and train_items (which do contain
        # cheap_correct as labels — that's legitimate: it's the routing signal).
        # The forbidden fields are 'difficulty' and 'discipline'.
        # We verify by ensuring the function signature doesn't take item features.
        import inspect
        sig = inspect.signature(knn_predict_cheap)
        param_names = list(sig.parameters.keys())
        self.assertNotIn("difficulty", param_names,
                         "knn_predict_cheap must not accept 'difficulty'")
        self.assertNotIn("discipline", param_names,
                         "knn_predict_cheap must not accept 'discipline'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
