import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ti_worker_claim import runtime_approval_errors  # noqa: E402


class WorkerClaimRuntimeApprovalTests(unittest.TestCase):
    def packet(self):
        return {
            "runtime_approval_id": "APPROVAL:test",
            "runtime_approval_record_sha256": "a" * 64,
        }

    def policy(self):
        return {
            "mode": "measurement_canary",
            "approval_id": "APPROVAL:test",
            "approval_record_sha256": "a" * 64,
        }

    def test_matching_current_policy_accepts_packet(self):
        self.assertEqual(
            runtime_approval_errors(
                self.packet(),
                self.policy(),
            ),
            [],
        )

    def test_paused_policy_rejects_old_activation_packet(self):
        policy = self.policy()
        policy["mode"] = "paused"
        self.assertIn(
            "runtime_policy_not_measurement_canary",
            runtime_approval_errors(
                self.packet(),
                policy,
            ),
        )

    def test_changed_approval_id_rejects_packet(self):
        policy = self.policy()
        policy["approval_id"] = "APPROVAL:new"
        self.assertIn(
            "runtime_approval_id_stale",
            runtime_approval_errors(
                self.packet(),
                policy,
            ),
        )

    def test_changed_approval_record_hash_rejects_packet(self):
        policy = self.policy()
        policy["approval_record_sha256"] = "b" * 64
        self.assertIn(
            "runtime_approval_record_hash_stale",
            runtime_approval_errors(
                self.packet(),
                policy,
            ),
        )


if __name__ == "__main__":
    unittest.main()
