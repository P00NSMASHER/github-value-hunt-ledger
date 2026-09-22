import unittest

from production.allocator_learning_bootstrap import (
    BOOTSTRAP_MODE,
    BOOTSTRAP_REASON,
    apply_learning_bootstrap,
)


def base_policy(
    *,
    adjacency=2,
    coverage=3,
    experiment=6,
    measurement=1,
    verification=1,
    wildcard=1,
):
    slots = []
    slot_index = 1
    role_specs = [
        ("experiment", experiment, ["experiment_execution", "capability_gap"]),
        ("coverage", coverage, ["coverage_gap"]),
        ("adjacency", adjacency, ["adjacency"]),
        ("measurement", measurement, ["learning_measurement"]),
        ("verification", verification, ["independent_verification"]),
        ("wildcard", wildcard, ["wildcard"]),
    ]
    for role, count, accepts in role_specs:
        for _ in range(count):
            slots.append(
                {
                    "slot_id": f"SLOT-{slot_index:02d}",
                    "role": role,
                    "accepts": list(accepts),
                    "label": role,
                }
            )
            slot_index += 1
    return {
        "schema_version": 1,
        "slot_count": len(slots),
        "slots": slots,
        "adaptation": {
            "min_role_slots": {
                "experiment": 4,
                "coverage": 2,
                "adjacency": 1,
                "measurement": 1,
                "verification": 1,
                "wildcard": 1,
            },
            "max_slot_changes_per_generation": 1,
        },
    }


def learning_state(*, confirmed=False):
    records = []
    if confirmed:
        records.append(
            {
                "key": "STRAT:confirmed",
                "kind": "STRATEGY",
                "eligible_for_policy_consideration": True,
            }
        )
    return {"memory": {"records": records}}


def curriculum(*, recommendations=3, operational=True):
    return {
        "blind_confirmation": {
            "operational": operational,
        },
        "recommended_measurements": [
            {
                "strategy_id": f"STRAT:test-{index}",
                "phase": "train_measurement",
            }
            for index in range(recommendations)
        ],
    }


def split_status(*, operational=True):
    return {
        "key_commitment_active": operational,
        "secret_available": operational,
    }


def role_counts(policy):
    out = {}
    for slot in policy["slots"]:
        role = slot["role"]
        out[role] = out.get(role, 0) + 1
    return out


class AllocatorLearningBootstrapTests(unittest.TestCase):
    def test_bootstrap_adds_second_measurement_slot(self):
        policy = base_policy()
        effective, shift = apply_learning_bootstrap(
            policy,
            learning_state(),
            curriculum(),
            split_status(),
        )
        counts = role_counts(effective)
        self.assertEqual(counts["measurement"], 2)
        self.assertEqual(counts["adjacency"], 1)
        self.assertEqual(len(effective["slots"]), len(policy["slots"]))
        self.assertEqual(shift["reason"], BOOTSTRAP_REASON)
        self.assertEqual(shift["from_role"], "adjacency")
        self.assertEqual(shift["to_role"], "measurement")
        shifted_slot = next(
            slot
            for slot in effective["slots"]
            if slot["slot_id"] == shift["slot_id"]
        )
        self.assertEqual(
            shifted_slot["accepts"],
            ["learning_measurement"],
        )

    def test_bootstrap_is_disabled_until_blind_confirmation_operational(self):
        effective, shift = apply_learning_bootstrap(
            base_policy(),
            learning_state(),
            curriculum(operational=False),
            split_status(operational=False),
        )
        self.assertIsNone(shift)
        self.assertEqual(
            role_counts(effective),
            role_counts(base_policy()),
        )

    def test_bootstrap_reverts_after_first_confirmed_strategy_prior(self):
        effective, shift = apply_learning_bootstrap(
            base_policy(),
            learning_state(confirmed=True),
            curriculum(),
            split_status(),
        )
        self.assertIsNone(shift)
        self.assertEqual(
            role_counts(effective),
            role_counts(base_policy()),
        )

    def test_bootstrap_requires_at_least_two_measurements(self):
        effective, shift = apply_learning_bootstrap(
            base_policy(),
            learning_state(),
            curriculum(recommendations=1),
            split_status(),
        )
        self.assertIsNone(shift)
        self.assertEqual(
            role_counts(effective)["measurement"],
            1,
        )

    def test_bootstrap_never_steals_below_donor_minimum(self):
        policy = base_policy(
            adjacency=1,
            coverage=2,
            experiment=4,
        )
        effective, shift = apply_learning_bootstrap(
            policy,
            learning_state(),
            curriculum(),
            split_status(),
        )
        self.assertIsNone(shift)
        self.assertEqual(
            role_counts(effective),
            role_counts(policy),
        )

    def test_donor_preference_preserves_more_expensive_roles(self):
        policy = base_policy(
            adjacency=2,
            coverage=4,
            experiment=7,
        )
        effective, shift = apply_learning_bootstrap(
            policy,
            learning_state(),
            curriculum(),
            split_status(),
        )
        self.assertEqual(shift["from_role"], "adjacency")
        counts = role_counts(effective)
        self.assertEqual(counts["coverage"], 4)
        self.assertEqual(counts["experiment"], 7)

    def test_existing_two_measurement_slots_do_not_shift_again(self):
        policy = base_policy(
            adjacency=1,
            coverage=2,
            experiment=5,
            measurement=2,
        )
        effective, shift = apply_learning_bootstrap(
            policy,
            learning_state(),
            curriculum(),
            split_status(),
        )
        self.assertIsNone(shift)
        self.assertEqual(
            role_counts(effective)["measurement"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
