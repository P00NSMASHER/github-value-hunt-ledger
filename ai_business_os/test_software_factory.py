import tempfile
import unittest
from pathlib import Path

from ai_business_os.governance import GovernanceControlPlane
from ai_business_os.persistent_agents.runtime import AgentRuntime
from ai_business_os.software_factory import SoftwareFactory, SoftwareFactoryError
from ai_business_os.verification import VerificationOrchestrator


class SoftwareFactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.gov = GovernanceControlPlane(self.runtime)
        self.verify = VerificationOrchestrator(self.runtime)
        self.factory = SoftwareFactory(self.runtime, self.gov)

        self.manager = self.runtime.register_agent("product-manager")
        self.executor = self.runtime.register_agent("engineering-executor")
        self.auditor = self.runtime.register_agent("engineering-auditor")
        self.release = self.runtime.register_agent("release-agent")

        self.goal = self.runtime.assign_goal(
            self.executor,
            "Implement issue with tests and evidence",
        )
        self.contract = self.verify.create_contract(
            self.goal,
            manager_agent_id=self.manager,
            executor_agent_id=self.executor,
            auditor_agent_id=self.auditor,
            criteria=[
                {"id": "tests", "description": "CI tests pass", "required": True},
                {"id": "scope", "description": "Change stays in requested scope", "required": True},
            ],
        )
        self.gov.set_agent_policy(
            self.release,
            allowed_classes=["EXTERNAL_WRITE", "PRODUCTION_CHANGE"],
            allowed_action_keys=["github.pr.create", "github.pr.merge"],
            human_approval_classes=["EXTERNAL_WRITE", "PRODUCTION_CHANGE"],
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"policy": "factory-release"},
        )
        self.factory.enqueue(
            work_item_id="work-1",
            repository="P00NSMASHER/example",
            issue_ref="issue-42",
            title="Fix regression",
            verification_contract_id=self.contract,
            manager_agent_id=self.manager,
            max_attempts=3,
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def claim_and_submit(self, *, commit_sha="abc123"):
        claimed = self.factory.claim(
            "work-1",
            executor_agent_id=self.executor,
            lease_seconds=900,
        )
        submitted = self.factory.submit_for_verification(
            "work-1",
            executor_agent_id=self.executor,
            commit_sha=commit_sha,
            test_evidence={"ci_run": "run-1", "passed": True},
            artifact_evidence={"diff": "artifact-1"},
        )
        return claimed, submitted

    def accept_audit(self):
        audited = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {
                    "criterion_id": "tests",
                    "verdict": "PASS",
                    "evidence": ["run-1"],
                },
                {
                    "criterion_id": "scope",
                    "verdict": "PASS",
                    "evidence": ["artifact-1"],
                },
            ],
            summary="Independent engineering acceptance passed.",
        )
        self.assertEqual("APPROVED", audited["status"])
        return self.factory.sync_audit("work-1")

    def ready_for_pr(self):
        self.claim_and_submit()
        ready = self.accept_audit()
        self.assertEqual("READY_FOR_PR", ready["state"])
        return ready

    def authorize_pr(self, *, title="Fix regression"):
        decision = self.factory.request_pr_authorization(
            "work-1",
            actor_agent_id=self.release,
            pr_title=title,
            base_branch="main",
        )
        self.assertEqual("REQUIRE_APPROVAL", decision["decision"])
        approval = self.gov.approve_request(
            decision["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": "PR create"},
        )
        allowed = self.gov.evaluate_request(
            decision["request_id"],
            approval_id=approval["id"],
        )
        self.assertEqual("ALLOW", allowed["decision"])
        return allowed["request_id"]

    def open_pr(self):
        self.ready_for_pr()
        request_id = self.authorize_pr()
        opened = self.factory.record_pr(
            "work-1",
            pr_ref="PR#99",
            governance_request_id=request_id,
            base_branch="main",
        )
        self.assertEqual("PR_OPEN", opened["state"])
        return opened

    def authorize_merge(self, *, expected_head_sha="abc123", merge_method="squash"):
        decision = self.factory.request_merge_authorization(
            "work-1",
            actor_agent_id=self.release,
            expected_head_sha=expected_head_sha,
            merge_method=merge_method,
        )
        self.assertEqual("REQUIRE_APPROVAL", decision["decision"])
        approval = self.gov.approve_request(
            decision["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": "production merge"},
        )
        allowed = self.gov.evaluate_request(
            decision["request_id"],
            approval_id=approval["id"],
        )
        self.assertEqual("ALLOW", allowed["decision"])
        return allowed["request_id"]

    def test_claim_creates_unique_isolated_workspace_and_branch(self):
        first = self.factory.claim(
            "work-1",
            executor_agent_id=self.executor,
        )
        self.assertEqual("RUNNING", first["state"])
        self.assertTrue(first["workspace_id"].startswith("ws_work-1_1_"))
        self.assertEqual("ai-factory/work-1/attempt-1", first["branch_name"])

    def test_wrong_executor_cannot_claim(self):
        outsider = self.runtime.register_agent("other-engineer")
        with self.assertRaises(SoftwareFactoryError):
            self.factory.claim(
                "work-1",
                executor_agent_id=outsider,
            )

    def test_pr_readiness_requires_independent_audit(self):
        self.claim_and_submit()
        with self.assertRaises(SoftwareFactoryError):
            self.factory.sync_audit("work-1")
        self.assertEqual("VERIFYING", self.factory.get("work-1")["state"])

    def test_rejected_audit_requeues_and_new_attempt_gets_new_workspace(self):
        first, _ = self.claim_and_submit()
        audited = self.verify.audit(
            self.contract,
            auditor_agent_id=self.auditor,
            results=[
                {
                    "criterion_id": "tests",
                    "verdict": "FAIL",
                    "evidence": ["run-1"],
                },
                {
                    "criterion_id": "scope",
                    "verdict": "PASS",
                    "evidence": ["artifact-1"],
                },
            ],
        )
        self.assertEqual("REJECTED", audited["status"])
        queued = self.factory.sync_audit("work-1")
        self.assertEqual("QUEUED", queued["state"])

        second = self.factory.claim(
            "work-1",
            executor_agent_id=self.executor,
        )
        self.assertEqual(2, second["attempts"])
        self.assertNotEqual(first["workspace_id"], second["workspace_id"])
        self.assertEqual("ai-factory/work-1/attempt-2", second["branch_name"])

    def test_retry_limit_blocks_failed_implementation(self):
        self.runtime.conn.execute(
            "UPDATE software_factory_items SET max_attempts=1 WHERE id='work-1'"
        )
        self.runtime.conn.commit()
        self.factory.claim("work-1", executor_agent_id=self.executor)
        blocked = self.factory.fail_attempt(
            "work-1",
            executor_agent_id=self.executor,
            error="tests failed",
        )
        self.assertEqual("BLOCKED", blocked["state"])

    def test_restart_reconciliation_reclaims_stale_running_attempt(self):
        first = self.factory.claim(
            "work-1",
            executor_agent_id=self.executor,
        )
        self.runtime.conn.execute(
            "UPDATE software_factory_items SET lease_expires_at=0 WHERE id='work-1'"
        )
        self.runtime.conn.commit()
        self.assertEqual(1, self.factory.reconcile())
        queued = self.factory.get("work-1")
        self.assertEqual("QUEUED", queued["state"])
        second = self.factory.claim("work-1", executor_agent_id=self.executor)
        self.assertNotEqual(first["workspace_id"], second["workspace_id"])

    def test_executor_lease_does_not_expire_independent_audit(self):
        self.claim_and_submit()
        item = self.factory.get("work-1")
        self.assertIsNone(item["lease_expires_at"])
        self.assertEqual(0, self.factory.reconcile())
        self.assertEqual("VERIFYING", self.factory.get("work-1")["state"])

    def test_pr_cannot_be_recorded_without_governance_authorization(self):
        self.ready_for_pr()
        with self.assertRaises(SoftwareFactoryError):
            self.factory.record_pr(
                "work-1",
                pr_ref="PR#1",
                governance_request_id="missing",
            )

    def test_pr_authorization_is_exact_parameter_bound(self):
        self.ready_for_pr()
        request_id = self.authorize_pr(title="Fix regression")
        with self.assertRaises(SoftwareFactoryError):
            self.factory.record_pr(
                "work-1",
                pr_ref="PR#1",
                governance_request_id=request_id,
                base_branch="release",
            )
        self.assertEqual("READY_FOR_PR", self.factory.get("work-1")["state"])

    def test_governed_pr_then_governed_merge_completes_goal(self):
        self.open_pr()
        merge_request = self.authorize_merge(
            expected_head_sha="abc123",
            merge_method="squash",
        )
        merged = self.factory.record_merge(
            "work-1",
            merge_ref="merge-sha-1",
            expected_head_sha="abc123",
            merge_method="squash",
            governance_request_id=merge_request,
        )
        self.assertEqual("MERGED", merged["state"])
        self.assertEqual("COMPLETE", self.runtime.get_goal(self.goal)["status"])
        closed = self.verify.get_contract(self.contract)
        self.assertEqual("CLOSED", closed["status"])

    def test_merge_cannot_bypass_mandatory_human_approval(self):
        self.open_pr()
        decision = self.factory.request_merge_authorization(
            "work-1",
            actor_agent_id=self.release,
            expected_head_sha="abc123",
            merge_method="squash",
        )
        self.assertEqual("REQUIRE_APPROVAL", decision["decision"])
        with self.assertRaises(SoftwareFactoryError):
            self.factory.record_merge(
                "work-1",
                merge_ref="merge-sha",
                expected_head_sha="abc123",
                merge_method="squash",
                governance_request_id=decision["request_id"],
            )

    def test_global_kill_switch_blocks_new_merge_authorization(self):
        self.open_pr()
        self.gov.set_global_kill_switch(
            enabled=True,
            principal="owner",
            principal_kind="HUMAN",
            reason="release freeze",
            evidence={"incident": "INC-1"},
        )
        decision = self.factory.request_merge_authorization(
            "work-1",
            actor_agent_id=self.release,
            expected_head_sha="abc123",
            merge_method="squash",
        )
        self.assertEqual("DENY", decision["decision"])

    def test_governance_authorization_cannot_be_rebound(self):
        self.ready_for_pr()
        request_id = self.authorize_pr()
        self.factory.record_pr(
            "work-1",
            pr_ref="PR#99",
            governance_request_id=request_id,
        )
        with self.assertRaises(SoftwareFactoryError):
            self.factory._bind_authorization(
                "work-1",
                request_id,
                purpose="SECOND_USE",
                expected_agent_id=None,
                expected_action_key="github.pr.create",
                expected_action_class="EXTERNAL_WRITE",
                expected_parameters={},
            )

    def test_event_history_contains_hashed_lifecycle(self):
        self.claim_and_submit()
        events = self.factory.events("work-1")
        self.assertEqual(
            ["ENQUEUED", "CLAIMED", "SUBMITTED_FOR_VERIFICATION"],
            [event["event_type"] for event in events],
        )
        self.assertTrue(all(len(event["event_hash"]) == 64 for event in events))


if __name__ == "__main__":
    unittest.main()
