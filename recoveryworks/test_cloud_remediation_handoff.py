from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
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
    CloudExecutionOutcome,
    build_cloud_remediation_execution_receipt,
    create_cloud_remediation_handoff,
    recheck_cloud_remediation_handoff,
)
from recoveryworks.integrations.cletrics import load_cletrics_bundle
from recoveryworks.test_cletrics_final_cycle import make_bundle


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RemediationHandoffReceiptTests(unittest.TestCase):
    def fixtures(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        bundle = load_cletrics_bundle(make_bundle(root / "bundle.zip"))
        plan = build_cloud_remediation_plan(bundle.signals)
        action = plan.actions[0]
        approval = approve_cloud_remediation_plan(
            plan,
            reviewer_id="reviewer",
            customer_authorization_id="customer-auth",
            approved_action_ids=(action.action_id,),
        )
        envelope = prepare_cloud_remediation_envelopes(plan, approval)[0]
        snapshot = CloudResourceSnapshot(
            provider=action.provider,
            account_id=action.account_id,
            resource_id=action.resource_id,
            resource_type="ec2_instance",
            observed_at="2026-09-25T12:00:00Z",
            attributes={"instance_type": "m7i.2xlarge", "state": "running"},
            source_hash=H("pre-state"),
            source_locator="readonly://pre",
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
        handoff = create_cloud_remediation_handoff(
            dry_run=dry,
            approval=approval,
            envelope=envelope,
            executor_id="executor-aws-prod-1",
            handoff_authorizer_id="cloud-change-manager",
            issued_at="2026-09-25T12:05:00Z",
            expires_at="2026-09-25T13:05:00Z",
        )
        fresh = CloudResourceSnapshot(
            provider=snapshot.provider,
            account_id=snapshot.account_id,
            resource_id=snapshot.resource_id,
            resource_type=snapshot.resource_type,
            observed_at="2026-09-25T12:10:00Z",
            attributes=snapshot.attributes,
            source_hash=H("fresh-pre-state"),
            source_locator="readonly://fresh",
            verified=True,
        )
        gate = recheck_cloud_remediation_handoff(
            handoff,
            fresh_snapshot=fresh,
            checked_at="2026-09-25T12:11:00Z",
        )
        return temp, action, approval, envelope, dry, handoff, fresh, gate

    def test_handoff_contains_no_credentials_or_provider_operation(self):
        temp, _action, _approval, _envelope, _dry, handoff, _fresh, _gate = self.fixtures()
        with temp:
            payload = handoff.as_dict()
            self.assertFalse(payload["credentials_embedded"])
            self.assertFalse(payload["provider_operation_embedded"])
            self.assertEqual(payload["state"], "READY_FOR_SEPARATE_EXECUTOR")
            self.assertFalse(payload["mutation_performed"])

    def test_changed_state_blocks_fresh_execution_gate(self):
        temp, _action, _approval, _envelope, _dry, handoff, fresh, _gate = self.fixtures()
        with temp:
            changed = CloudResourceSnapshot(
                provider=fresh.provider,
                account_id=fresh.account_id,
                resource_id=fresh.resource_id,
                resource_type=fresh.resource_type,
                observed_at="2026-09-25T12:12:00Z",
                attributes={"instance_type": "m7i.large", "state": "running"},
                source_hash=H("changed"),
                source_locator="readonly://changed",
                verified=True,
            )
            with self.assertRaisesRegex(ValueError, "new review is required"):
                recheck_cloud_remediation_handoff(
                    handoff,
                    fresh_snapshot=changed,
                    checked_at="2026-09-25T12:13:00Z",
                )

    def test_verified_external_applied_receipt_binds_post_state(self):
        temp, _action, _approval, _envelope, _dry, handoff, fresh, gate = self.fixtures()
        with temp:
            post = CloudResourceSnapshot(
                provider=fresh.provider,
                account_id=fresh.account_id,
                resource_id=fresh.resource_id,
                resource_type=fresh.resource_type,
                observed_at="2026-09-25T12:22:00Z",
                attributes={"instance_type": "m7i.xlarge", "state": "running"},
                source_hash=H("post-state"),
                source_locator="readonly://post",
                verified=True,
            )
            receipt = build_cloud_remediation_execution_receipt(
                handoff=handoff,
                gate=gate,
                post_snapshot=post,
                outcome=CloudExecutionOutcome.APPLIED,
                started_at="2026-09-25T12:20:00Z",
                completed_at="2026-09-25T12:23:00Z",
                provider_request_id="req-123",
                source_hash=H("executor-receipt"),
                source_locator="executor://receipt/req-123",
                verified=True,
                mutation_performed=True,
            )
            self.assertEqual(receipt.outcome, CloudExecutionOutcome.APPLIED)
            self.assertTrue(receipt.verified)
            self.assertNotEqual(
                receipt.pre_resource_state_hash,
                receipt.post_resource_state_hash,
            )

    def test_applied_receipt_without_changed_state_fails_closed(self):
        temp, _action, _approval, _envelope, _dry, handoff, fresh, gate = self.fixtures()
        with temp:
            post = CloudResourceSnapshot(
                provider=fresh.provider,
                account_id=fresh.account_id,
                resource_id=fresh.resource_id,
                resource_type=fresh.resource_type,
                observed_at="2026-09-25T12:22:00Z",
                attributes=fresh.attributes,
                source_hash=H("same-post"),
                source_locator="readonly://same-post",
                verified=True,
            )
            with self.assertRaisesRegex(ValueError, "changed resource state"):
                build_cloud_remediation_execution_receipt(
                    handoff=handoff,
                    gate=gate,
                    post_snapshot=post,
                    outcome=CloudExecutionOutcome.APPLIED,
                    started_at="2026-09-25T12:20:00Z",
                    completed_at="2026-09-25T12:23:00Z",
                    source_hash=H("bad-receipt"),
                    source_locator="executor://bad",
                    verified=True,
                    mutation_performed=True,
                )


if __name__ == "__main__":
    unittest.main()
