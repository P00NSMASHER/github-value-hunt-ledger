import tempfile
import unittest
from pathlib import Path

from business_os.memory.value_memory import MemoryError, ValueMemoryStore


class ValueMemoryTests(unittest.TestCase):
    def store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return ValueMemoryStore(Path(temp.name) / "memory.sqlite3")

    def test_observed_value_changes_ranking(self):
        store = self.store()
        good = store.add_memory("sales", "Apollo manufacturing lead search", now=100)
        bad = store.add_memory("sales", "Apollo manufacturing lead search", now=100)
        for i in range(4):
            store.record_observation(
                good.id, 0.95, outcome_ref=f"deal:{i}", now=110 + i
            )
            store.record_observation(
                bad.id, 0.10, outcome_ref=f"miss:{i}", now=110 + i
            )
        ranked = store.retrieve(
            "Apollo manufacturing lead search", scope="sales", now=120
        )
        self.assertEqual(ranked[0].item.id, good.id)
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_scope_isolation_is_fail_closed(self):
        store = self.store()
        sales = store.add_memory(
            "sales", "manufacturing prospect query", now=100
        )
        store.add_memory(
            "engineering", "manufacturing prospect query", now=100
        )
        ranked = store.retrieve(
            "manufacturing prospect", scope="sales", now=100
        )
        self.assertEqual([x.item.id for x in ranked], [sales.id])

    def test_recency_decays_stale_memory(self):
        store = self.store()
        old = store.add_memory(
            "research", "freight recovery pricing evidence", now=0
        )
        fresh = store.add_memory(
            "research", "freight recovery pricing evidence", now=90
        )
        for item in (old, fresh):
            store.record_observation(
                item.id,
                0.8,
                outcome_ref=f"eval:{item.id}",
                now=item.updated_at,
            )
        ranked = store.retrieve(
            "freight recovery pricing evidence",
            scope="research",
            now=100,
            half_life_seconds=20,
        )
        self.assertEqual(ranked[0].item.id, fresh.id)
        self.assertGreater(ranked[0].recency, ranked[1].recency)

    def test_confidence_grows_from_evidence_not_claims(self):
        store = self.store()
        item = store.add_memory(
            "product", "free audit converts better", now=10
        )
        before = store.get_memory(item.id)
        store.record_observation(
            item.id, 0.9, outcome_ref="experiment:1", now=11
        )
        store.record_observation(
            item.id, 0.9, outcome_ref="experiment:2", now=12
        )
        after = store.get_memory(item.id)
        self.assertGreater(after.confidence, before.confidence)
        self.assertEqual(after.observation_count, 2)
        self.assertAlmostEqual(after.value_mean, 0.9)

    def test_observations_require_evidence_reference(self):
        store = self.store()
        item = store.add_memory("sales", "lead pattern")
        with self.assertRaises(MemoryError):
            store.record_observation(item.id, 0.8, outcome_ref="")
        with self.assertRaises(MemoryError):
            store.record_observation(item.id, 1.5, outcome_ref="bad")

    def test_factor_breakdown_is_exposed(self):
        store = self.store()
        item = store.add_memory(
            "ops",
            "deployment rollback checklist",
            tags=["release"],
            now=100,
        )
        store.record_observation(
            item.id, 1.0, outcome_ref="incident:7", now=100
        )
        hit = store.retrieve(
            "deployment rollback", scope="ops", now=100
        )[0]
        expected = (
            hit.relevance
            * hit.observed_value
            * hit.confidence
            * hit.recency
        )
        self.assertAlmostEqual(hit.score, expected)


if __name__ == "__main__":
    unittest.main()
