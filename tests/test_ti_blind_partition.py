import unittest

from production.blind_partition import (
    PARTITION_METHOD,
    assign_partition,
    build_partition_receipts,
    receipt_partition_map,
    trusted_claim_id,
    validate_partition_receipts,
)


def generated_run(index=1):
    return {
        "schema_version": 16,
        "search_run_id": f"RUN:blind:{index}",
        "measurement_quality": "prospective",
        "work_action": "search",
        "allocation_mode": "generated",
        "routing_mode": "generated",
        "execution_claim_id": f"CLAIM:blind:{index}",
    }


class BlindPartitionTests(unittest.TestCase):
    def test_trusted_claim_requires_generated_v14_provenance(self):
        run = generated_run()
        self.assertEqual(
            trusted_claim_id(run),
            "CLAIM:blind:1",
        )
        run["routing_mode"] = "manual_override"
        self.assertIsNone(trusted_claim_id(run))

    def test_assignment_is_deterministic_for_secret_and_claim(self):
        first = assign_partition(
            "CLAIM:blind:1",
            "test-secret",
        )
        second = assign_partition(
            "CLAIM:blind:1",
            "test-secret",
        )
        self.assertEqual(first, second)
        self.assertIn(first[0], {"train", "confirm"})
        self.assertEqual(len(first[1]), 64)

    def test_different_secret_changes_commitment(self):
        one = assign_partition(
            "CLAIM:blind:1",
            "secret-one",
        )
        two = assign_partition(
            "CLAIM:blind:1",
            "secret-two",
        )
        self.assertNotEqual(one[1], two[1])

    def test_missing_secret_leaves_trusted_run_pending(self):
        receipts, issues = build_partition_receipts(
            [generated_run()],
            [],
            secret=None,
        )
        self.assertEqual(receipts, [])
        self.assertEqual(
            issues[0]["reason"],
            "blind_partition_secret_unavailable",
        )

    def test_receipt_is_created_only_after_run_exists(self):
        receipts, issues = build_partition_receipts(
            [generated_run()],
            [],
            secret="test-secret",
        )
        self.assertFalse(issues)
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        self.assertEqual(
            receipt["partition_method"],
            PARTITION_METHOD,
        )
        self.assertEqual(
            receipt["execution_claim_id"],
            "CLAIM:blind:1",
        )
        self.assertEqual(
            receipt["search_run_id"],
            "RUN:blind:1",
        )
        self.assertIn(receipt["partition"], {"train", "confirm"})
        self.assertEqual(len(receipt["commitment_sha256"]), 64)

    def test_receipts_validate_with_secret(self):
        runs = [generated_run(1), generated_run(2)]
        receipts, issues = build_partition_receipts(
            runs,
            [],
            secret="test-secret",
        )
        self.assertFalse(issues)
        self.assertEqual(
            validate_partition_receipts(
                receipts,
                runs,
                secret="test-secret",
            ),
            [],
        )

    def test_wrong_secret_detects_tampering_or_mismatch(self):
        runs = [generated_run()]
        receipts, _issues = build_partition_receipts(
            runs,
            [],
            secret="test-secret",
        )
        errors = validate_partition_receipts(
            receipts,
            runs,
            secret="wrong-secret",
        )
        self.assertTrue(
            any(
                error.startswith("receipt_commitment_mismatch:")
                for error in errors
            )
        )

    def test_receipt_map_contains_only_valid_partitions(self):
        rows = [
            {
                "execution_claim_id": "CLAIM:1",
                "partition": "train",
            },
            {
                "execution_claim_id": "CLAIM:2",
                "partition": "confirm",
            },
            {
                "execution_claim_id": "CLAIM:3",
                "partition": "pending",
            },
        ]
        self.assertEqual(
            receipt_partition_map(rows),
            {
                "CLAIM:1": "train",
                "CLAIM:2": "confirm",
            },
        )


if __name__ == "__main__":
    unittest.main()
