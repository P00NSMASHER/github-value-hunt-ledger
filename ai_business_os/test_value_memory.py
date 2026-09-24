import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_business_os.persistent_agents.runtime import AgentRuntime
from ai_business_os.value_memory import ValueMemory, ValueMemoryError


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ValueMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.memory = ValueMemory(self.runtime)
        self.creator = self.runtime.register_agent("memory-creator")
        self.observer = self.runtime.register_agent("outcome-observer")
        self.verifier = self.runtime.register_agent("outcome-verifier")
        self.curator = self.runtime.register_agent("memory-curator")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _register(self, key="strategy-a", objective="sales", version="v1"):
        return self.memory.register_memory(
            memory_key=key,
            version=version,
            scope="GLOBAL",
            objective=objective,
            content={"strategy": key},
            created_by_agent_id=self.creator,
        )

    def _observe_and_verify(
        self,
        memory_id,
        event_id,
        reward,
        attribution=1.0,
        accepted=True,
    ):
        observation = self.memory.observe_outcome(
            memory_id,
            event_id=event_id,
            observer_agent_id=self.observer,
            reward=reward,
            attribution_fraction=attribution,
            evidence={"event": event_id, "metric": reward},
        )
        return self.memory.verify_observation(
            observation,
            verifier_agent_id=self.verifier,
            verification_report_hash=sha("verify:" + observation),
            accepted=accepted,
        )

    def test_unverified_outcome_does_not_change_value(self):
        item = self._register()
        self.memory.observe_outcome(
            item["id"],
            event_id="event-1",
            observer_agent_id=self.observer,
            reward=1.0,
            attribution_fraction=1.0,
            evidence={"metric": "won"},
        )
        summary = self.memory.value_summary(item["id"])
        self.assertEqual(summary["verified_count"], 0)
        self.assertEqual(summary["unverified_count"], 1)
        self.assertEqual(summary["mean_reward"], 0.0)
        self.assertEqual(summary["confidence"], 0.0)

    def test_rejected_outcome_does_not_change_value(self):
        item = self._register()
        self._observe_and_verify(item["id"], "event-1", 1.0, accepted=False)
        summary = self.memory.value_summary(item["id"])
        self.assertEqual(summary["verified_count"], 0)
        self.assertEqual(summary["rejected_count"], 1)
        self.assertEqual(summary["mean_reward"], 0.0)

    def test_observer_cannot_verify_own_outcome(self):
        item = self._register()
        observation = self.memory.observe_outcome(
            item["id"],
            event_id="event-1",
            observer_agent_id=self.observer,
            reward=0.8,
            attribution_fraction=1.0,
            evidence={"metric": "qualified lead"},
        )
        with self.assertRaises(ValueMemoryError):
            self.memory.verify_observation(
                observation,
                verifier_agent_id=self.observer,
                verification_report_hash=sha("self-verification"),
                accepted=True,
            )

    def test_verified_value_is_learned(self):
        item = self._register()
        self._observe_and_verify(item["id"], "event-1", 0.8)
        self._observe_and_verify(item["id"], "event-2", 0.4)
        summary = self.memory.value_summary(item["id"])
        self.assertEqual(summary["verified_count"], 2)
        self.assertAlmostEqual(summary["mean_reward"], 0.6, places=5)
        self.assertGreater(summary["confidence"], 0.0)

    def test_same_event_cannot_be_double_counted_for_same_memory(self):
        item = self._register()
        self.memory.observe_outcome(
            item["id"],
            event_id="event-1",
            observer_agent_id=self.observer,
            reward=0.8,
            attribution_fraction=0.5,
            evidence={"metric": "first"},
        )
        with self.assertRaises(ValueMemoryError):
            self.memory.observe_outcome(
                item["id"],
                event_id="event-1",
                observer_agent_id=self.observer,
                reward=0.8,
                attribution_fraction=0.5,
                evidence={"metric": "duplicate"},
            )

    def test_cross_memory_event_credit_is_conserved(self):
        a = self._register("strategy-a")
        b = self._register("strategy-b")
        self._observe_and_verify(a["id"], "shared-event", 1.0, attribution=0.7)

        observation = self.memory.observe_outcome(
            b["id"],
            event_id="shared-event",
            observer_agent_id=self.observer,
            reward=1.0,
            attribution_fraction=0.4,
            evidence={"metric": "same revenue event"},
        )
        with self.assertRaises(ValueMemoryError):
            self.memory.verify_observation(
                observation,
                verifier_agent_id=self.verifier,
                verification_report_hash=sha("over-attribution"),
                accepted=True,
            )
        self.assertEqual(
            self.memory.get_observation(observation)["verification_status"],
            "UNVERIFIED",
        )

    def test_objective_specific_memory_does_not_leak(self):
        sales = self._register("sales-play", objective="sales")
        engineering = self._register("engineering-play", objective="engineering")
        ranked = self.memory.rank_memories(
            {sales["id"]: 1.0, engineering["id"]: 1.0},
            objective="sales",
        )
        self.assertEqual([row["memory"]["id"] for row in ranked], [sales["id"]])

    def test_verified_positive_memory_ranks_above_neutral_and_negative(self):
        positive = self._register("positive")
        neutral = self._register("neutral")
        negative = self._register("negative")
        self._observe_and_verify(positive["id"], "win", 1.0)
        self._observe_and_verify(negative["id"], "loss", -1.0)

        ranked = self.memory.rank_memories(
            {
                positive["id"]: 1.0,
                neutral["id"]: 1.0,
                negative["id"]: 1.0,
            },
            objective="sales",
        )
        self.assertEqual(
            [row["memory"]["memory_key"] for row in ranked],
            ["positive", "neutral", "negative"],
        )

    def test_one_outcome_cannot_create_full_confidence(self):
        item = self._register()
        self._observe_and_verify(item["id"], "event-1", 1.0)
        summary = self.memory.value_summary(item["id"])
        self.assertGreater(summary["confidence"], 0.0)
        self.assertLess(summary["confidence"], 1.0)

    def test_global_memory_can_transfer_but_is_discounted(self):
        exact = self._register("exact", objective="sales")
        global_item = self._register("global-principle", objective="*")
        ranked = self.memory.rank_memories(
            {exact["id"]: 1.0, global_item["id"]: 1.0},
            objective="sales",
        )
        self.assertEqual(ranked[0]["memory"]["id"], exact["id"])
        self.assertLess(ranked[1]["objective_factor"], ranked[0]["objective_factor"])

    def test_retired_memory_is_not_ranked(self):
        item = self._register()
        self.memory.retire_memory(
            item["id"],
            curator_agent_id=self.curator,
            reason="superseded by a verified strategy",
            evidence={"replacement": "strategy-b"},
        )
        ranked = self.memory.rank_memories(
            {item["id"]: 1.0},
            objective="sales",
        )
        self.assertEqual(ranked, [])

    def test_reward_and_attribution_bounds_fail_closed(self):
        item = self._register()
        with self.assertRaises(ValueMemoryError):
            self.memory.observe_outcome(
                item["id"],
                event_id="bad-reward",
                observer_agent_id=self.observer,
                reward=1.5,
                attribution_fraction=1.0,
                evidence={"bad": True},
            )
        with self.assertRaises(ValueMemoryError):
            self.memory.observe_outcome(
                item["id"],
                event_id="bad-credit",
                observer_agent_id=self.observer,
                reward=0.5,
                attribution_fraction=1.1,
                evidence={"bad": True},
            )


if __name__ == "__main__":
    unittest.main()
