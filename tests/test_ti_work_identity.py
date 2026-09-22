import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ti_work_identity import (
    semantic_revision_sha256,
    versioned_work_item_id,
)


class WorkIdentityTests(unittest.TestCase):
    def test_mapping_order_does_not_change_identity(self):
        left = {
            "next_action": "replay fixture",
            "status": "READY",
            "capabilities": ["CAP-013", "CAP-017"],
        }
        right = {
            "capabilities": ["CAP-013", "CAP-017"],
            "status": "READY",
            "next_action": "replay fixture",
        }
        self.assertEqual(
            semantic_revision_sha256("EXP-007", left),
            semantic_revision_sha256("EXP-007", right),
        )
        self.assertEqual(
            versioned_work_item_id("verify", "EXP-007", left),
            versioned_work_item_id("verify", "EXP-007", right),
        )

    def test_semantic_plan_change_changes_work_identity(self):
        old = {
            "status": "READY",
            "next_action": "patch entry.scan_event",
        }
        new = {
            "status": "READY",
            "next_action": "validate LTQ v66 176/232 layout",
        }
        old_id, old_revision = versioned_work_item_id(
            "verify",
            "EXP-007",
            old,
        )
        new_id, new_revision = versioned_work_item_id(
            "verify",
            "EXP-007",
            new,
        )
        self.assertNotEqual(old_revision, new_revision)
        self.assertNotEqual(old_id, new_id)

    def test_prefix_and_source_are_identity_bound(self):
        payload = {"next_action": "same"}
        exp_id, _ = versioned_work_item_id(
            "experiment",
            "EXP-007",
            payload,
        )
        verify_id, _ = versioned_work_item_id(
            "verify",
            "EXP-007",
            payload,
        )
        other_id, _ = versioned_work_item_id(
            "verify",
            "EXP-008",
            payload,
        )
        self.assertNotEqual(exp_id, verify_id)
        self.assertNotEqual(verify_id, other_id)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            versioned_work_item_id(
                "BAD PREFIX",
                "EXP-007",
                {},
            )
        with self.assertRaises(ValueError):
            semantic_revision_sha256("", {})


if __name__ == "__main__":
    unittest.main()
