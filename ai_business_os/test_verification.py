import tempfile
import unittest
from pathlib import Path

from ai_business_os.persistent_agents.runtime import AgentRuntime, InvalidTransition
from ai_business_os.verification import VerificationError, VerificationOrchestrator


class VerificationOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.verify = VerificationOrchestrator(self.runtime)
        self.manager = self.runtime.register_agent("manager")
        self.executor = self.runtime.register_agent("executor")
        self.auditor = self.runtime.register_agent("auditor")
        self.goal = self.runtime.assign_goal(self.executor, "Ship a verified change")
        self.criteria = [
            {"id": "tests", "description": "Automated tests pass"},
            {"id": "evidence", "description": "Required evidence is attached"},
            {"id": "docs", "description": "Documentation updated", "required": False},
        ]
        self.contract = self.verify.create_contract(
            self.goal,
            manager_agent_id=self.manager,
            executor_agent_id=self.executor,
            auditor_agent_id=self.auditor,
            criteria=self.criteria,
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _submit(self):
        self.verify.start_execution(self.contract)
        self.verify.submit_execution(
            self.contract,
            executor_agent_id=self.executor,
            evidence={"commit": "abc123", "test_run": "run-1"},
        )

    def _passing_results(self):
        return [
            {"criterion_id": "tests", "verdict": "PASS", "evidence": ["run-1"]},
            {"criterion_id": "evidence", "verdict": "PASS", "evidence": ["abc123"]},
            {"criterion_id": "docs", "verdict": "UNKNOWN", "evidence": []},
        ]

    def test_executor_cannot_complete_without_audit(self):
        self._submit()
        with self.assertRaises(InvalidTransition):
            self.runtime.transition_goal(self.goal, "COMPLETE")

    def test_three_roles_must_be_distinct(self):
        other_goal = self.runtime.assign_goal(self.executor, "Another goal")
        with self.assertRaises(VerificationError):
            self.verify.create_contract(
                other_goal,
                manager_agent_id=self.executor,
                executor_agent_id=self.executor,
                auditor_agent_id=self.auditor,
                criteria=self.criteria,
            )

    def test_wrong_auditor_is_rejected(self):
        self._submit()
        outsider = self.runtime.register_agent("outsider")
        with self.assertRaises(VerificationError):
            self.verify.audit(
                self.contract,
                auditor_agent_id=outsider,
                results=self._passing_results(),
            )

    def test_failed_required_criterion_returns_goal_to_active(self):
        self._submit()
        result = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {"criterion_id": "tests", "verdict": "FAIL", "evidence": ["run-1"]},
                {"criterion_id": "evidence", "verdict": "PASS", "evidence": ["abc123"]},
                {"criterion_id": "docs", "verdict": "PASS", "evidence": ["docs"]},
            ],
            summary="Tests failed.",
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.runtime.get_goal(self.goal)["status"], "ACTIVE")
        self.assertTrue(result["report_hash"])

    def test_unknown_required_criterion_is_not_approved(self):
        self._submit()
        result = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {"criterion_id": "tests", "verdict": "PASS", "evidence": ["run-1"]},
                {"criterion_id": "evidence", "verdict": "UNKNOWN", "evidence": []},
                {"criterion_id": "docs", "verdict": "PASS", "evidence": ["docs"]},
            ],
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.runtime.get_goal(self.goal)["status"], "ACTIVE")

    def test_approved_audit_allows_manager_to_complete(self):
        self._submit()
        audited = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=self._passing_results(),
            summary="Required acceptance criteria independently verified.",
        )
        self.assertEqual(audited["status"], "APPROVED")
        self.assertEqual(self.runtime.get_goal(self.goal)["status"], "VERIFYING")

        completed = self.verify.complete_goal(
            self.contract,
            manager_agent_id=self.manager,
        )
        self.assertEqual(completed["status"], "COMPLETE")
        closed = self.verify.get_contract(self.contract)
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(
            completed["state"]["accepted_audit_report_hash"],
            audited["report_hash"],
        )

    def test_rejected_work_can_be_revised_and_reaudited(self):
        self._submit()
        self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {"criterion_id": "tests", "verdict": "FAIL", "evidence": ["run-1"]},
                {"criterion_id": "evidence", "verdict": "PASS", "evidence": ["abc123"]},
                {"criterion_id": "docs", "verdict": "PASS", "evidence": []},
            ],
        )
        self.verify.start_execution(self.contract)
        self.verify.submit_execution(
            self.contract,
            executor_agent_id=self.executor,
            evidence={"commit": "def456", "test_run": "run-2"},
        )
        audited = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {"criterion_id": "tests", "verdict": "PASS", "evidence": ["run-2"]},
                {"criterion_id": "evidence", "verdict": "PASS", "evidence": ["def456"]},
                {"criterion_id": "docs", "verdict": "PASS", "evidence": ["docs"]},
            ],
        )
        self.assertEqual(audited["status"], "APPROVED")
        self.assertEqual(audited["attempt"], 2)

    def test_missing_criterion_result_fails_closed(self):
        self._submit()
        with self.assertRaises(VerificationError):
            self.verify.audit(
                self.contract,
                auditor_agent_id=self.auditor,
                results=[
                    {"criterion_id": "tests", "verdict": "PASS", "evidence": ["run-1"]},
                    {"criterion_id": "evidence", "verdict": "PASS", "evidence": ["abc123"]},
                ],
            )


if __name__ == "__main__":
    unittest.main()
