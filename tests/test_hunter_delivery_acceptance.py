import unittest
from unittest.mock import patch

from tools.hunter_delivery_acceptance import (
    AcceptanceError, evaluate_receipts, verify_delivery,
)

REV = "a" * 40
REPO = "P00NSMASHER/github-value-hunt-ledger"
WORKER = {"id": "HUNTER-01", "target_repository": REPO}


class FakeAPI:
    def __init__(self, merged=True, success=True, main_sha=REV):
        self.results = {
            "/repos/" + REPO + "/pulls/37": {
                "merged": merged, "merged_at": "2026-11-05T14:00:00Z",
                "changed_files": 2, "merge_commit_sha": REV,
                "base": {"ref": "main"},
                "html_url": "https://github.com/" + REPO + "/pull/37"},
            "/repos/" + REPO + "/branches/main": {
                "name": "main", "commit": {"sha": main_sha}},
            "/repos/" + REPO + "/actions/runs/99": {
                "head_sha": REV, "head_branch": "main", "event": "push",
                "status": "completed", "conclusion": "success" if success else "failure",
                "created_at": "2026-11-05T14:01:00Z",
                "repository": {"full_name": REPO},
                "html_url": "https://github.com/" + REPO + "/actions/runs/99"},
        }

    def get(self, path):
        return self.results[path]


class AcceptanceTests(unittest.TestCase):
    def receipt(self):
        return {
            "schema_version": 1, "worker_id": "HUNTER-01",
            "target_repository": REPO, "target_main_sha": REV,
            "merged_pr_number": 37, "independent_ci_run_id": 99,
            "claimed_outcome": "CI_VERIFIED_TARGET_CHANGE",
        }

    def test_exact_source_merge_and_main_ci_are_required(self):
        result = verify_delivery(self.receipt(), WORKER, FakeAPI())
        self.assertEqual(result["status"], "ACCEPTED_CI_VERIFIED_TARGET_CHANGE")
        self.assertEqual(result["revenue"], "UNKNOWN")
        self.assertEqual(result["production_deployment"], "UNKNOWN")

    def test_false_and_stale_claims_are_rejected(self):
        for api in [FakeAPI(merged=False), FakeAPI(success=False),
                    FakeAPI(main_sha="b" * 40)]:
            with self.subTest(api=api), self.assertRaises(AcceptanceError):
                verify_delivery(self.receipt(), WORKER, api)
        for changes in [{"claimed_outcome": "REVENUE_PROVEN"},
                        {"target_main_sha": "b" * 40},
                        {"independent_ci_run_id": 0},
                        {"worker_id": "HUNTER-02"}]:
            with self.subTest(changes=changes), self.assertRaises(AcceptanceError):
                verify_delivery({**self.receipt(), **changes}, WORKER, FakeAPI())

    def test_empty_receipts_cannot_be_interpreted_as_success(self):
        with patch("tools.hunter_delivery_acceptance.validate_manifest", return_value="v2"):
            out = evaluate_receipts({"workers": [WORKER]}, [], FakeAPI())
        self.assertEqual(out["accepted_technical_changes"], 0)
        self.assertEqual(out["independent_real_world_outcomes"], "NOT_ESTABLISHED")

    def test_duplicate_target_claim_rejected(self):
        with patch("tools.hunter_delivery_acceptance.validate_manifest", return_value="v2"):
            out = evaluate_receipts({"workers": [WORKER]},
                                    [self.receipt(), self.receipt()], FakeAPI())
        self.assertEqual(out["accepted_technical_changes"], 1)
        self.assertEqual(out["rejected_claims"], 1)


if __name__ == "__main__":
    unittest.main()
