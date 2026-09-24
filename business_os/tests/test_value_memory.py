import tempfile
import unittest
from pathlib import Path

from business_os.memory.value_memory import ValueMemory


class ValueMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "memory.sqlite3"
        self.memory = ValueMemory(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_higher_observed_value_ranks_higher_when_relevance_equal(self):
        self.memory.remember(
            "Apollo manufacturing prospect search",
            objective_scope="freight",
            value=0.9,
            confidence=0.9,
            memory_id="good",
            now=1000,
        )
        self.memory.remember(
            "Apollo manufacturing prospect search",
            objective_scope="freight",
            value=-0.5,
            confidence=0.9,
            memory_id="bad",
            now=1000,
        )
        ranked = self.memory.retrieve(
            "Apollo manufacturing prospect search",
            objective_scope="freight",
            now=1000,
        )
        self.assertEqual(["good", "bad"], [x.memory.id for x in ranked])

    def test_warning_with_strong_negative_outcome_remains_retrievable(self):
        self.memory.remember(
            "Avoid generic untargeted cold email because reply quality collapsed",
            kind="WARNING",
            objective_scope="sales",
            value=-0.95,
            confidence=1.0,
            memory_id="warning",
            now=1000,
        )
        ranked = self.memory.retrieve(
            "generic cold email reply",
            objective_scope="sales",
            now=1000,
        )
        self.assertEqual("warning", ranked[0].memory.id)
        self.assertGreater(ranked[0].value_factor, 0.9)

    def test_scope_match_beats_unrelated_scope(self):
        self.memory.remember(
            "Qualified manufacturing leads through Apollo",
            objective_scope="freight",
            value=0.5,
            confidence=1.0,
            memory_id="freight",
            now=1000,
        )
        self.memory.remember(
            "Qualified manufacturing leads through Apollo",
            objective_scope="starblox",
            value=0.5,
            confidence=1.0,
            memory_id="game",
            now=1000,
        )
        ranked = self.memory.retrieve(
            "manufacturing leads Apollo",
            objective_scope="freight",
            now=1000,
        )
        self.assertEqual("freight", ranked[0].memory.id)

    def test_recency_decay_prefers_newer_equal_memory(self):
        day = 86400
        self.memory.remember(
            "pricing experiment improved conversion",
            value=0.5,
            confidence=1.0,
            memory_id="old",
            now=0,
        )
        self.memory.remember(
            "pricing experiment improved conversion",
            value=0.5,
            confidence=1.0,
            memory_id="new",
            now=89 * day,
        )
        ranked = self.memory.retrieve(
            "pricing experiment conversion",
            now=90 * day,
            half_life_days=30,
        )
        self.assertEqual("new", ranked[0].memory.id)

    def test_observed_outcome_updates_value_and_confidence(self):
        mem = self.memory.remember(
            "search tactic",
            value=0.0,
            confidence=0.4,
            memory_id="x",
            now=100,
        )
        updated = self.memory.observe_outcome(
            mem.id,
            1.0,
            observation_confidence=1.0,
            now=200,
        )
        self.assertGreater(updated.value, 0)
        self.assertGreater(updated.confidence, mem.confidence)
        self.assertEqual(2, updated.evidence_count)

    def test_zero_confidence_outcome_does_not_change_memory(self):
        mem = self.memory.remember(
            "search tactic",
            value=0.2,
            confidence=0.4,
            memory_id="x",
            now=100,
        )
        updated = self.memory.observe_outcome(
            mem.id,
            -1.0,
            observation_confidence=0.0,
            now=200,
        )
        self.assertEqual(mem.value, updated.value)
        self.assertEqual(mem.evidence_count, updated.evidence_count)

    def test_invalid_reward_fails_closed(self):
        mem = self.memory.remember("x tactic", memory_id="x")
        with self.assertRaises(ValueError):
            self.memory.observe_outcome(mem.id, 4.0)


if __name__ == "__main__":
    unittest.main()
