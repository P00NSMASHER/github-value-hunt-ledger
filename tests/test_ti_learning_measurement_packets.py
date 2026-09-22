import copy
import unittest

from production.learning_measurement_packets import (
    build_measurement_packets,
    choose_seed_for_measurement,
    validate_measurement_packets,
)


def rec(strategy_id, rank=1):
    return {
        "rank": rank,
        "strategy_id": strategy_id,
        "phase": "train_measurement",
        "measurement_priority": 80.0 - rank,
        "selection_reason": "reduce_train_evidence_deficit",
        "requires_generated_claim": True,
        "blind_partition_rule": (
            "Do not calculate or choose train/confirm membership."
        ),
        "retry_rule": (
            "Retry only for an independent operational reason."
        ),
        "train": {
            "runs": 4,
            "deep_inspections": 10,
            "runs_needed": 1,
            "deep_inspections_needed": 10,
            "ready": False,
        },
        "confirm": {
            "runs": 0,
            "deep_inspections": 0,
            "runs_needed": 2,
            "deep_inspections_needed": 6,
            "ready": False,
        },
    }


def seed(
    seed_id,
    strategy_id,
    *,
    seed_type="learning_measurement",
    priority=50,
):
    return {
        "seed_id": seed_id,
        "seed_type": seed_type,
        "work_action": "search",
        "measurement_contract_version": "phase_blind_v1",
        "query_recipe_id": "test-transfer",
        "query_anchors": ["alpha", "beta"],
        "next_action": "Run the bounded test transfer.",
        "action_gate": "Use only the named target-domain transfer.",
        "required_signatures": ["effective rule version", "authority provenance"],
        "strategy_id": strategy_id,
        "search_objective_id": "OBJ:test",
        "capability_ids": [],
        "experiment_ids": [],
        "authorization_basis": (
            "adaptive_learning_curriculum"
            if seed_type == "learning_measurement"
            else "test_authorized"
        ),
        "acceptance_target": "Find one executable implementation.",
        "why_now": "Bounded useful hypothesis.",
        "query_templates": ["alpha beta", "gamma delta"],
        "search_surfaces": ["GitHub code search"],
        "verification_gate": "Require executable source and tests.",
        "stop_conditions": ["Stop after bounded recall rescue."],
        "exclude_domains": ["source-domain"],
        "priority": priority,
    }


class LearningMeasurementPacketTests(unittest.TestCase):
    def test_only_adaptive_learning_seed_is_eligible(self):
        seeds = [
            seed(
                "SEED:z",
                "STRAT:x",
                seed_type="positive_dna_transfer",
            ),
            seed(
                "SEED:measure:legacy",
                "STRAT:x",
                seed_type="strategy_measurement",
            ),
            seed(
                "SEED:learn:x-target",
                "STRAT:x",
                seed_type="learning_measurement",
            ),
        ]
        chosen = choose_seed_for_measurement(
            "STRAT:x", seeds
        )
        self.assertEqual(
            chosen["seed_id"],
            "SEED:learn:x-target",
        )

    def test_seed_priority_does_not_change_precommit_choice(self):
        first = [
            seed("SEED:learn:a", "STRAT:x", priority=1),
            seed("SEED:learn:b", "STRAT:x", priority=999),
        ]
        second = copy.deepcopy(first)
        second[0]["priority"] = 999
        second[1]["priority"] = 1

        self.assertEqual(
            choose_seed_for_measurement(
                "STRAT:x", first
            )["seed_id"],
            "SEED:learn:a",
        )
        self.assertEqual(
            choose_seed_for_measurement(
                "STRAT:x", second
            )["seed_id"],
            "SEED:learn:a",
        )

    def test_bundle_is_advisory_and_partition_blind(self):
        curriculum = {
            "mode": "measurement_only",
            "policy_effect": "none",
            "recommended_measurements": [
                rec("STRAT:x")
            ],
        }
        bundle = build_measurement_packets(
            curriculum,
            [seed("SEED:learn:a", "STRAT:x")],
            curriculum_sha="a" * 64,
            seeds_sha="b" * 64,
        )
        self.assertFalse(bundle["activates_work"])
        self.assertFalse(
            bundle["partition_selection_allowed"]
        )
        packet = bundle["packets"][0]
        self.assertFalse(packet["execution_authority"])
        self.assertTrue(
            packet["requires_generated_claim"]
        )
        self.assertFalse(
            packet["manual_work_can_complete_packet"]
        )
        self.assertTrue(
            packet["partition_unknown_until_ingestion"]
        )
        frozen = packet["seed"]
        self.assertEqual(
            frozen["measurement_contract_version"],
            "phase_blind_v1",
        )
        self.assertEqual(frozen["query_recipe_id"], "test-transfer")
        self.assertEqual(frozen["query_anchors"], ["alpha", "beta"])
        self.assertEqual(
            frozen["next_action"],
            "Run the bounded test transfer.",
        )
        self.assertEqual(
            frozen["required_signatures"],
            ["effective rule version", "authority provenance"],
        )
        self.assertEqual(
            validate_measurement_packets(bundle),
            [],
        )

    def test_packet_hash_detects_mutation(self):
        bundle = build_measurement_packets(
            {
                "mode": "measurement_only",
                "policy_effect": "none",
                "recommended_measurements": [
                    rec("STRAT:x")
                ],
            },
            [seed("SEED:learn:a", "STRAT:x")],
            curriculum_sha="a" * 64,
            seeds_sha="b" * 64,
        )
        bundle["packets"][0]["seed"][
            "query_templates"
        ].append("mutated")
        errors = validate_measurement_packets(bundle)
        self.assertTrue(
            any(
                error.startswith("packet_hash_mismatch:")
                for error in errors
            )
        )

    def test_unpaired_measurement_is_reported_not_invented(self):
        bundle = build_measurement_packets(
            {
                "mode": "measurement_only",
                "policy_effect": "none",
                "recommended_measurements": [
                    rec("STRAT:missing")
                ],
            },
            [],
            curriculum_sha="a" * 64,
            seeds_sha="b" * 64,
        )
        self.assertEqual(bundle["packets"], [])
        self.assertEqual(
            bundle["unpaired_recommendations"],
            [
                {
                    "strategy_id": "STRAT:missing",
                    "reason": (
                        "no_authorized_search_seed_for_strategy"
                    ),
                }
            ],
        )

    def test_non_learning_seed_cannot_be_precommitted(self):
        legacy = seed(
            "SEED:measure:legacy",
            "STRAT:x",
            seed_type="strategy_measurement",
        )
        ordinary = seed(
            "SEED:dna:ordinary",
            "STRAT:x",
            seed_type="positive_dna_transfer",
        )
        self.assertIsNone(
            choose_seed_for_measurement(
                "STRAT:x", [legacy, ordinary]
            )
        )

    def test_non_search_seed_cannot_be_precommitted(self):
        bad = seed("SEED:learn:a", "STRAT:x")
        bad["work_action"] = "execute_fixture"
        self.assertIsNone(
            choose_seed_for_measurement(
                "STRAT:x", [bad]
            )
        )

    def test_deterministic_packet_identity(self):
        curriculum = {
            "mode": "measurement_only",
            "policy_effect": "none",
            "recommended_measurements": [
                rec("STRAT:x")
            ],
        }
        seeds = [seed("SEED:learn:a", "STRAT:x")]
        first = build_measurement_packets(
            curriculum,
            seeds,
            curriculum_sha="a" * 64,
            seeds_sha="b" * 64,
        )
        second = build_measurement_packets(
            curriculum,
            seeds,
            curriculum_sha="a" * 64,
            seeds_sha="b" * 64,
        )
        self.assertEqual(
            first["packets"][0]["packet_id"],
            second["packets"][0]["packet_id"],
        )
        self.assertEqual(
            first["packets"][0]["packet_sha256"],
            second["packets"][0]["packet_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
