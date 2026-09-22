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
                "packet_id": "LMP:a",
                "seed": {"seed_id": "SEED:learn:a"},
            },
            {
                "packet_id": "LMP:b",
                "seed": {"seed_id": "SEED:learn:b"},
            },
            {
                "packet_id": "LMP:c",
                "seed": {"seed_id": "SEED:learn:c"},
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
        "approved_packet_ids": [],
        "approved_seed_ids": [],
        "maximum_current_activations": 0,
        "maximum_total_claims": 0,
        "allowed_work_kinds": ["learning_measurement"],
        "explicit_user_approval_required": True,
    }


def approved_policy(*, current=2, total=2):
    return {
        "schema_version": 1,
        "mode": MEASUREMENT_CANARY,
        "approval_scope": CANARY_SCOPE,
        "approval_id": "APPROVAL:test-canary",
        "approved_at": "2026-09-22T17:00:00Z",
        "approved_packet_ids": ["LMP:a", "LMP:b"][:total],
        "approved_seed_ids": [
            "SEED:learn:a",
            "SEED:learn:b",
        ][:total],
        "maximum_current_activations": current,
        "maximum_total_claims": total,
        "allowed_work_kinds": ["learning_measurement"],
        "explicit_user_approval_required": True,
    }


def claim(
    seed_id,
    *,
    status="COMPLETE",
    approval_id="APPROVAL:test-canary",
):
    return {
        "claim_id": "CLAIM:" + seed_id[-1] * 12,
        "runtime_approval_id": approval_id,
        "routing_mode": "generated",
        "assignment_work_kind": "learning_measurement",
        "assignment_source_id": seed_id,
        "status": status,
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
        self.assertEqual(gate["maximum_total_claims"], 0)
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

    def test_valid_canary_is_snapshot_bound(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(),
            readiness(ready=True),
            packets(),
        )
        self.assertTrue(gate["enabled"])
        self.assertEqual(
            gate["allowed_seed_ids"],
            ["SEED:learn:a", "SEED:learn:b"],
        )
        self.assertEqual(
            gate["approved_packet_ids"],
            ["LMP:a", "LMP:b"],
        )
        self.assertEqual(gate["remaining_claim_budget"], 2)

    def test_packet_snapshot_change_requires_new_approval(self):
        changed = packets()
        changed["packets"][0]["packet_id"] = "LMP:new-a"
        gate = evaluate_runtime_activation_gate(
            approved_policy(),
            readiness(ready=True),
            changed,
        )
        self.assertFalse(gate["enabled"])
        self.assertTrue(
            any(
                error.startswith("approved_packet_not_current:")
                for error in gate["errors"]
            )
        )

    def test_completed_or_released_claim_consumes_budget(self):
        for status in ("COMPLETE", "RELEASED", "FAILED_RETRYABLE"):
            with self.subTest(status=status):
                gate = evaluate_runtime_activation_gate(
                    approved_policy(),
                    readiness(ready=True),
                    packets(),
                    [claim("SEED:learn:a", status=status)],
                )
                self.assertTrue(gate["enabled"])
                self.assertEqual(gate["claims_consumed"], 1)
                self.assertEqual(gate["remaining_claim_budget"], 1)
                self.assertEqual(
                    gate["allowed_seed_ids"],
                    ["SEED:learn:b"],
                )

    def test_active_claim_consumes_concurrent_capacity(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(current=2, total=2),
            readiness(ready=True),
            packets(),
            [claim("SEED:learn:a", status="RUNNING")],
        )
        self.assertTrue(gate["enabled"])
        self.assertEqual(gate["active_claims"], 1)
        self.assertEqual(gate["maximum_current_activations"], 1)

    def test_budget_exhaustion_disables_canary(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(),
            readiness(ready=True),
            packets(),
            [
                claim("SEED:learn:a"),
                claim("SEED:learn:b"),
            ],
        )
        self.assertFalse(gate["enabled"])
        self.assertEqual(
            gate["reason"],
            "canary_claim_budget_exhausted",
        )
        self.assertEqual(gate["claims_consumed"], 2)
        self.assertEqual(gate["remaining_claim_budget"], 0)

    def test_same_seed_cannot_be_claimed_twice_under_approval(self):
        gate = evaluate_runtime_activation_gate(
            approved_policy(),
            readiness(ready=True),
            packets(),
            [
                claim("SEED:learn:a"),
                {
                    **claim("SEED:learn:a"),
                    "claim_id": "CLAIM:duplicate001",
                },
            ],
        )
        self.assertFalse(gate["enabled"])
        self.assertIn(
            "approved_seed_claimed_more_than_once",
            gate["errors"],
        )

    def test_capacity_above_three_fails_closed(self):
        policy = approved_policy()
        policy["maximum_current_activations"] = 4
        gate = evaluate_runtime_activation_gate(
            policy,
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

    def test_paused_policy_cannot_smuggle_approval_or_budget(self):
        policy = paused_policy()
        policy["approval_id"] = "APPROVAL:bad"
        policy["maximum_current_activations"] = 1
        policy["maximum_total_claims"] = 1
        policy["approved_packet_ids"] = ["LMP:a"]
        policy["approved_seed_ids"] = ["SEED:learn:a"]
        gate = evaluate_runtime_activation_gate(
            policy,
            readiness(ready=True),
            packets(),
        )
        self.assertFalse(gate["enabled"])
        self.assertEqual(gate["reason"], "invalid_runtime_policy")
        self.assertIn(
            "paused_mode_requires_zero_current_capacity",
            gate["errors"],
        )
        self.assertIn(
            "paused_mode_requires_zero_total_claim_budget",
            gate["errors"],
        )
        self.assertIn(
            "paused_mode_forbids_approval_id",
            gate["errors"],
        )
        self.assertIn(
            "paused_mode_forbids_approved_packet_ids",
            gate["errors"],
        )


if __name__ == "__main__":
    unittest.main()
