import unittest

from production.runtime_activation_gate import (
    CANARY_SCOPE,
    MEASUREMENT_CANARY,
    PAUSED,
    evaluate_runtime_activation_gate,
)


def packets():
    return {
        "packets": [
            {
                "seed": {
                    "seed_id": "SEED:learn:a",
                }
            },
            {
                "seed": {
                    "seed_id": "SEED:learn:b",
                }
            },
            {
                "seed": {
                    "seed_id": "SEED:learn:c",
                }
            },
        ]
    }


def readiness(*, ready=True):
    if ready:
        return {
            "state": "AWAITING_EXPLICIT_USER_APPROVAL",
            "blockers": [],
            "gates": {
                "measurement_packets_ready": True,
                "split_receipt_system_ready": True,
                "benchmark_complete": True,
                "shadow_run_gate_complete": True,
                "no_current_activations": True,
            },
        }
    return {
        "state": "BLOCKED",
        "blockers": [{"code": "frozen_benchmark_incomplete"}],
        "gates": {
            "measurement_packets_ready": True,
            "split_receipt_system_ready": True,
            "benchmark_complete": False,
            "shadow_run_gate_complete": True,
            "no_current_activations": True,
        },
    }


def paused_policy():
    return {
        "schema_version": 1,
        "mode": PAUSED,
        "approval_scope": None,
        "approval_id": None,
        "approved_at": None,
        "maximum_current_activations": 0,
        "allowed_work_kinds": ["learning_measurement"],
        "explicit_user_approval_required": True,
    }


def approved_policy(*, maximum=2):
    return {
        "schema_version": 1,
        "mode": MEASUREMENT_CANARY,
        "approval_scope": CANARY_SCOPE,
        "approval_id": "APPROVAL:test-canary",
        "approved_at": "2026-09-22T17:00:00Z",
        "maximum_current_activations": maximum,
        "allowed_work_kinds": ["learning_measurement"],
        "explicit_user_approval_required": True,
    }


class RuntimeActivationGateTests(unittest.TestCase):
    def test_machine_ready_but_paused_stays_disabled(self):
        gate = evaluate_runtime_activation_gate(
            paused_policy(),
            readiness(ready=True),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertEqual(gate["reason"], "runtime_policy_paused")
        self.assertEqual(gate["maximum_current_activations"], 0)
        self.assertEqual(gate["allowed_seed_ids"], [])

    def test_approval_cannot_bypass_blocked_machine_readiness(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(),
            readiness(ready=False),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertIn(
            "machine_restart_readiness_blocked",
            gate["errors"],
        )

    def test_valid_canary_is_bounded_to_current_packet_seeds(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(maximum=2),
            readiness(ready=True),
            packets(),
        )
        self.assertTrue(gate["enabled"])
        self.assertEqual(
            gate["allowed_work_kinds"],
            ["learning_measurement"],
        )
        self.assertEqual(
            gate["allowed_seed_ids"],
            [
                "SEED:learn:a",
                "SEED:learn:b",
                "SEED:learn:c",
            ],
        )
        self.assertEqual(gate["maximum_current_activations"], 2)

    def test_capacity_above_three_fails_closed(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(maximum=4),
            readiness(ready=True),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertIn(
            "measurement_canary_capacity_must_be_1_to_3",
            gate["errors"],
        )

    def test_canary_scope_and_work_kind_must_be_exact(self):
        policy = approved_policy()
        policy["approval_scope"] = "all_hunters"
        policy["allowed_work_kinds"] = [
            "learning_measurement",
            "wildcard",
        ]
        gate = evaluate_runtime_activation_gate(
            policy,
            readiness(ready=True),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertIn(
            "measurement_canary_scope_required",
            gate["errors"],
        )
        self.assertIn(
            "measurement_canary_work_kind_must_be_exact",
            gate["errors"],
        )

    def test_paused_policy_cannot_smuggle_approval_or_capacity(self):
        policy = paused_policy()
        policy["approval_id"] = "APPROVAL:bad"
        policy["maximum_current_activations"] = 1
        gate = evaluate_runtime_activation_gate(
            policy,
            readiness(ready=True),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertEqual(gate["reason"], "invalid_runtime_policy")
        self.assertIn(
            "paused_mode_requires_zero_capacity",
            gate["errors"],
        )
        self.assertIn(
            "paused_mode_forbids_approval_id",
            gate["errors"],
        )


if __name__ == "__main__":
    unittest.main()
