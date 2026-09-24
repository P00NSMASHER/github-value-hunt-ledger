import unittest

from business_os.audit.acceptance import (
    AcceptanceContract,
    AuditError,
    Evidence,
    ExecutorSubmission,
    IndependentAuditor,
    Requirement,
)


class IndependentAuditorTests(unittest.TestCase):
    def setUp(self):
        self.contract = AcceptanceContract(
            task_id="task-1",
            manager="chief-of-staff",
            requirements=(
                Requirement(
                    key="tests",
                    evidence_key="ci_passed",
                    predicate="equals",
                    expected=True,
                    allowed_producers=("CI",),
                ),
                Requirement(
                    key="artifact",
                    evidence_key="artifact_count",
                    predicate="gte",
                    expected=1,
                    allowed_producers=("SYSTEM", "CI"),
                ),
            ),
        )
        self.auditor = IndependentAuditor("auditor-1")

    def test_accepts_only_when_all_requirements_pass(self):
        submission = ExecutorSubmission(
            task_id="task-1",
            executor="engineering-1",
            result={"executor_claim": "done"},
            evidence=(
                Evidence("ci_passed", True, "CI", "actions/run/123"),
                Evidence("artifact_count", 2, "SYSTEM", "artifact-index"),
            ),
        )
        receipt = self.auditor.audit(self.contract, submission)
        self.assertEqual("ACCEPTED", receipt.verdict)
        self.assertTrue(all(f.passed for f in receipt.findings))
        self.assertEqual(64, len(receipt.sha256))

    def test_executor_claim_cannot_substitute_for_independent_evidence(self):
        submission = ExecutorSubmission(
            task_id="task-1",
            executor="engineering-1",
            result={"executor_claim": "everything passed"},
            evidence=(
                Evidence("ci_passed", True, "EXECUTOR", "self-claim"),
                Evidence("artifact_count", 2, "EXECUTOR", "self-claim"),
            ),
        )
        receipt = self.auditor.audit(self.contract, submission)
        self.assertEqual("REJECTED", receipt.verdict)
        self.assertFalse(receipt.findings[0].passed)
        self.assertIn("allowed producer", receipt.findings[0].reason)

    def test_missing_required_evidence_rejects(self):
        submission = ExecutorSubmission(
            task_id="task-1",
            executor="engineering-1",
            result={},
            evidence=(Evidence("ci_passed", True, "CI", "actions/run/123"),),
        )
        receipt = self.auditor.audit(self.contract, submission)
        self.assertEqual("REJECTED", receipt.verdict)
        self.assertEqual("missing evidence", receipt.findings[1].reason)

    def test_false_ci_rejects_even_when_executor_says_done(self):
        submission = ExecutorSubmission(
            task_id="task-1",
            executor="engineering-1",
            result={"status": "done"},
            evidence=(
                Evidence("ci_passed", False, "CI", "actions/run/123"),
                Evidence("artifact_count", 5, "SYSTEM", "artifact-index"),
            ),
        )
        receipt = self.auditor.audit(self.contract, submission)
        self.assertEqual("REJECTED", receipt.verdict)

    def test_contract_hash_changes_when_requirement_changes(self):
        changed = AcceptanceContract(
            task_id="task-1",
            manager="chief-of-staff",
            requirements=(
                Requirement(
                    key="tests",
                    evidence_key="ci_passed",
                    predicate="equals",
                    expected=False,
                    allowed_producers=("CI",),
                ),
            ),
        )
        self.assertNotEqual(self.contract.sha256, changed.sha256)

    def test_task_mismatch_fails_closed(self):
        submission = ExecutorSubmission(
            task_id="other-task",
            executor="engineering-1",
            result={},
            evidence=(),
        )
        with self.assertRaises(AuditError):
            self.auditor.audit(self.contract, submission)

    def test_unsupported_predicate_fails_closed(self):
        contract = AcceptanceContract(
            task_id="task-1",
            manager="chief-of-staff",
            requirements=(
                Requirement(
                    key="bad",
                    evidence_key="x",
                    predicate="model_says_ok",
                    allowed_producers=("SYSTEM",),
                ),
            ),
        )
        submission = ExecutorSubmission(
            task_id="task-1",
            executor="engineering-1",
            result={},
            evidence=(Evidence("x", True, "SYSTEM", "x"),),
        )
        with self.assertRaises(AuditError):
            self.auditor.audit(contract, submission)


if __name__ == "__main__":
    unittest.main()
