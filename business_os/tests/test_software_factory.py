import tempfile
import unittest
from pathlib import Path

from business_os.audit.acceptance import (
    AcceptanceContract,
    Evidence,
    ExecutorSubmission,
    IndependentAuditor,
    Requirement,
)
from business_os.factory.software_factory import SoftwareFactory


class SoftwareFactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "factory.sqlite3"
        self.factory = SoftwareFactory(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def contract(self, task_id="work-1"):
        return AcceptanceContract(
            task_id=task_id,
            manager="product-manager",
            requirements=(
                Requirement(
                    key="tests",
                    evidence_key="ci",
                    predicate="equals",
                    expected=True,
                    allowed_producers=("CI",),
                ),
            ),
        )

    def enqueue(self, task_id="work-1", max_attempts=3):
        return self.factory.enqueue(
            "P00NSMASHER/example",
            "issue-42",
            "Fix regression",
            self.contract(task_id),
            work_item_id=task_id,
            max_attempts=max_attempts,
            now=100,
        )

    def accepted_receipt(self, item, executor="engineer-1"):
        submission = ExecutorSubmission(
            task_id=item.id,
            executor=executor,
            result={"commit": "abc"},
            evidence=(Evidence("ci", True, "CI", "actions/123"),),
        )
        item = self.factory.submit_for_verification(
            item.id, submission, now=120
        )
        receipt = IndependentAuditor("auditor-1").audit(
            self.contract(item.id), submission
        )
        return item, receipt

    def test_claim_creates_isolated_workspace(self):
        self.enqueue()
        first = self.factory.claim("work-1", "engineer-1", now=110)
        self.assertEqual("RUNNING", first.state)
        self.assertTrue(first.workspace_id.startswith("ws_work-1_1_"))

    def test_pr_is_blocked_without_independent_acceptance(self):
        self.enqueue()
        self.factory.claim("work-1", "engineer-1", now=110)
        with self.assertRaises(PermissionError):
            self.factory.record_pr("work-1", "PR#1", now=120)

    def test_accepted_exact_submission_becomes_pr_ready(self):
        self.enqueue()
        item = self.factory.claim("work-1", "engineer-1", now=110)
        item, receipt = self.accepted_receipt(item)
        ready = self.factory.accept_verification("work-1", receipt, now=130)
        self.assertEqual("READY_FOR_PR", ready.state)
        self.assertEqual(receipt.sha256, ready.accepted_receipt_sha256)

        opened = self.factory.record_pr("work-1", "PR#99", now=140)
        self.assertEqual("PR_OPEN", opened.state)
        merged = self.factory.record_merge(
            "work-1", merge_ref="merge-sha", now=150
        )
        self.assertEqual("MERGED", merged.state)

    def test_executor_cannot_audit_own_attempt(self):
        self.enqueue()
        item = self.factory.claim("work-1", "engineer-1", now=110)
        submission = ExecutorSubmission(
            task_id=item.id,
            executor="engineer-1",
            result={},
            evidence=(Evidence("ci", True, "CI", "actions/1"),),
        )
        self.factory.submit_for_verification(item.id, submission, now=120)
        receipt = IndependentAuditor("engineer-1").audit(
            self.contract(), submission
        )
        with self.assertRaises(PermissionError):
            self.factory.accept_verification(item.id, receipt, now=130)

    def test_receipt_for_different_submission_is_rejected(self):
        self.enqueue()
        item = self.factory.claim("work-1", "engineer-1", now=110)
        real = ExecutorSubmission(
            task_id=item.id,
            executor="engineer-1",
            result={"commit": "real"},
            evidence=(Evidence("ci", True, "CI", "actions/1"),),
        )
        self.factory.submit_for_verification(item.id, real, now=120)
        other = ExecutorSubmission(
            task_id=item.id,
            executor="engineer-1",
            result={"commit": "other"},
            evidence=(Evidence("ci", True, "CI", "actions/1"),),
        )
        receipt = IndependentAuditor("auditor-1").audit(
            self.contract(), other
        )
        with self.assertRaises(ValueError):
            self.factory.accept_verification(item.id, receipt, now=130)

    def test_rejected_audit_requeues_with_new_workspace(self):
        self.enqueue()
        first = self.factory.claim("work-1", "engineer-1", now=110)
        submission = ExecutorSubmission(
            task_id=first.id,
            executor="engineer-1",
            result={},
            evidence=(Evidence("ci", False, "CI", "actions/failed"),),
        )
        self.factory.submit_for_verification(first.id, submission, now=120)
        receipt = IndependentAuditor("auditor-1").audit(
            self.contract(), submission
        )
        retried = self.factory.accept_verification(first.id, receipt, now=130)
        self.assertEqual("QUEUED", retried.state)

        second = self.factory.claim("work-1", "engineer-2", now=140)
        self.assertEqual(2, second.attempts)
        self.assertNotEqual(first.workspace_id, second.workspace_id)

    def test_retry_limit_blocks_work_item(self):
        self.enqueue(max_attempts=1)
        self.factory.claim("work-1", "engineer-1", now=110)
        blocked = self.factory.fail_attempt(
            "work-1", "engineer-1", "tests failed", now=120
        )
        self.assertEqual("BLOCKED", blocked.state)

    def test_restart_reconciliation_requeues_stale_attempt(self):
        self.enqueue()
        first = self.factory.claim(
            "work-1", "engineer-1", lease_seconds=10, now=110
        )
        reopened = SoftwareFactory(self.db)
        self.assertEqual(1, reopened.reconcile(now=121))
        item = reopened.get("work-1")
        self.assertEqual("QUEUED", item.state)

        second = reopened.claim("work-1", "engineer-2", now=122)
        self.assertEqual(2, second.attempts)
        self.assertNotEqual(first.workspace_id, second.workspace_id)

    def test_events_preserve_state_history(self):
        self.enqueue()
        self.factory.claim("work-1", "engineer-1", now=110)
        events = self.factory.events("work-1")
        self.assertEqual(["ENQUEUED", "CLAIMED"], [x["event_type"] for x in events])


if __name__ == "__main__":
    unittest.main()
