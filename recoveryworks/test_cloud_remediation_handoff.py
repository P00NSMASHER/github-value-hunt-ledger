from __future__ import annotations

import hashlib
import unittest

from recoveryworks.branches.cloud_remediation import (
    approve_cloud_remediation_plan,
    build_cloud_remediation_plan,
    prepare_cloud_remediation_envelopes,
)
from recoveryworks.branches.cloud_remediation_executor import (
    CloudRemediationDryRunRequest,
    CloudResourceSnapshot,
    prepare_cloud_remediation_dry_run,
)
from recoveryworks.branches.cloud_remediation_handoff import (
    CloudRemediationExecutionReceipt,
    CloudRemediationExecutionStatus,
    authorize_cloud_remediation_execution,
    prepare_cloud_remediation_execution_handoff,
    validate_cloud_remediation_execution_receipt,
)
from recoveryworks.branches.cloud_signals import CloudSignal, CloudSignalType
from recoveryworks.models import canonical_hash


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def receipt_id(identity: dict) -> str:
    return "cloud-remediation-execution-receipt:" + canonical_hash(identity)


class RemediationExecutionHandoffTests(unittest.TestCase):
    def fixtures(self):
        signal = CloudSignal(
            signal_id="S-1",
            signal_type=CloudSignalType.SAVINGS_OPPORTUNITY,
            provider="aws",
            account_id="acct-1",
            service_id="EC2",
            detected_at="2026-09-24T11:00:00Z",
            detection_method="test",
            source_hash=H("signal"),
            source_locator="test://signal",
            resource_id="i-1",
            estimated_impact_cents=2500,
            confidence="0.9",
            metadata={
                "savings_category": "rightsize",
                "recommendation": "Resize after review",
                "remediation_action": "resize_instance",
            },
        )
        plan = build_cloud_remediation_plan((signal,))
        action = plan.actions[0]
        approval = approve_cloud_remediation_plan(
            plan,
            reviewer_id="reviewer",
            customer_authorization_id="customer-auth-1",
            approved_action_ids=(action.action_id,),
        )
        envelope = prepare_cloud_remediation_envelopes(plan, approval)[0]
        snapshot = CloudResourceSnapshot(
            provider="aws",
            account_id="acct-1",
            resource_id="i-1",
            resource_type="ec2_instance",
            observed_at="2026-09-24T12:00:00Z",
            attributes={"instance_type": "m7i.2xlarge", "state": "running"},
            source_hash=H("snapshot"),
            source_locator="aws-readonly://i-1",
            verified=True,
        )
        request = CloudRemediationDryRunRequest(
            action_id=action.action_id,
            envelope_proof_hash=envelope.proof_hash,
            expected_resource_state_hash=snapshot.state_hash,
            parameters={"target_instance_type": "m7i.xlarge"},
        )
        dry = prepare_cloud_remediation_dry_run(
            plan=plan,
            approval=approval,
            envelope=envelope,
            snapshot=snapshot,
            request=request,
        )
        auth = authorize_cloud_remediation_execution(
            dry,
            approval,
            authorizer_id="customer-ops-approver",
            executor_id="executor-1",
            authorized_at="2026-09-24T12:01:00Z",
            expires_at="2026-09-24T12:15:00Z",
        )
        recheck = CloudResourceSnapshot(
            provider="aws",
            account_id="acct-1",
            resource_id="i-1",
            resource_type="ec2_instance",
            observed_at="2026-09-24T12:01:30Z",
            attributes={"instance_type": "m7i.2xlarge", "state": "running"},
            source_hash=H("recheck"),
            source_locator="aws-readonly://i-1/recheck",
            verified=True,
        )
        handoff = prepare_cloud_remediation_execution_handoff(
            dry,
            auth,
            recheck,
            prepared_at="2026-09-24T12:02:00Z",
        )
        return plan, action, approval, envelope, dry, auth, recheck, handoff

    def test_handoff_requires_fresh_matching_state(self):
        *_, dry, auth, recheck, handoff = self.fixtures()
        self.assertEqual(
            handoff.as_dict()["state"],
            "READY_FOR_SEPARATELY_AUTHORIZED_EXECUTOR",
        )
        stale = CloudResourceSnapshot(
            provider=recheck.provider,
            account_id=recheck.account_id,
            resource_id=recheck.resource_id,
            resource_type=recheck.resource_type,
            observed_at="2026-09-24T11:00:00Z",
            attributes=recheck.attributes,
            source_hash=H("stale"),
            source_locator="test://stale",
            verified=True,
        )
        with self.assertRaisesRegex(ValueError, "too stale"):
            prepare_cloud_remediation_execution_handoff(
                dry,
                auth,
                stale,
                prepared_at="2026-09-24T12:02:00Z",
            )

    def test_applied_execution_receipt_requires_verified_changed_post_state(self):
        *_, handoff = self.fixtures()
        post = CloudResourceSnapshot(
            provider="aws",
            account_id="acct-1",
            resource_id="i-1",
            resource_type="ec2_instance",
            observed_at="2026-09-24T12:03:30Z",
            attributes={"instance_type": "m7i.xlarge", "state": "running"},
            source_hash=H("post"),
            source_locator="aws-readonly://i-1/post",
            verified=True,
        )
        identity = {
            "schema": 1,
            "handoff_id": handoff.handoff_id,
            "handoff_proof_hash": handoff.proof_hash,
            "action_id": handoff.action_id,
            "executor_id": handoff.executor_id,
            "executed_at": "2026-09-24T12:03:00Z",
            "status": "APPLIED",
            "before_state_hash": handoff.recheck_state_hash,
            "after_state_hash": post.state_hash,
            "provider_request_id": "aws-request-123",
            "source_hash": H("executor-receipt"),
            "source_locator": "executor://receipt-1",
            "verified": True,
            "metadata": {},
        }
        receipt = CloudRemediationExecutionReceipt(
            receipt_id=receipt_id(identity),
            handoff_id=handoff.handoff_id,
            handoff_proof_hash=handoff.proof_hash,
            action_id=handoff.action_id,
            executor_id=handoff.executor_id,
            executed_at="2026-09-24T12:03:00Z",
            status=CloudRemediationExecutionStatus.APPLIED,
            before_state_hash=handoff.recheck_state_hash,
            after_state_hash=post.state_hash,
            provider_request_id="aws-request-123",
            source_hash=H("executor-receipt"),
            source_locator="executor://receipt-1",
            verified=True,
            metadata={},
        )
        validated = validate_cloud_remediation_execution_receipt(
            handoff, receipt, post
        )
        self.assertEqual(
            validated.as_dict()["state"], "EXECUTION_RECEIPT_VERIFIED"
        )

    def test_receipt_outside_handoff_window_fails_closed(self):
        *_, handoff = self.fixtures()
        post = CloudResourceSnapshot(
            provider="aws",
            account_id="acct-1",
            resource_id="i-1",
            resource_type="ec2_instance",
            observed_at="2026-09-24T12:20:30Z",
            attributes={"instance_type": "m7i.xlarge"},
            source_hash=H("post-late"),
            source_locator="test://post-late",
            verified=True,
        )
        identity = {
            "schema": 1,
            "handoff_id": handoff.handoff_id,
            "handoff_proof_hash": handoff.proof_hash,
            "action_id": handoff.action_id,
            "executor_id": handoff.executor_id,
            "executed_at": "2026-09-24T12:20:00Z",
            "status": "APPLIED",
            "before_state_hash": handoff.recheck_state_hash,
            "after_state_hash": post.state_hash,
            "provider_request_id": "request-late",
            "source_hash": H("late"),
            "source_locator": "test://late",
            "verified": True,
            "metadata": {},
        }
        receipt = CloudRemediationExecutionReceipt(
            receipt_id=receipt_id(identity),
            handoff_id=handoff.handoff_id,
            handoff_proof_hash=handoff.proof_hash,
            action_id=handoff.action_id,
            executor_id=handoff.executor_id,
            executed_at="2026-09-24T12:20:00Z",
            status=CloudRemediationExecutionStatus.APPLIED,
            before_state_hash=handoff.recheck_state_hash,
            after_state_hash=post.state_hash,
            provider_request_id="request-late",
            source_hash=H("late"),
            source_locator="test://late",
            verified=True,
            metadata={},
        )
        with self.assertRaisesRegex(ValueError, "outside the authorized"):
            validate_cloud_remediation_execution_receipt(handoff, receipt, post)


if __name__ == "__main__":
    unittest.main()
