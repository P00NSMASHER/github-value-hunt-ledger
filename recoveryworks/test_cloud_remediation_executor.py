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
    CloudRemediationExecutorPolicy,
    CloudResourceSnapshot,
    prepare_cloud_remediation_dry_run,
)
from recoveryworks.integrations.cletrics import load_cletrics_bundle
from recoveryworks.test_cletrics_final_cycle import make_bundle


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RemediationExecutorDryRunTests(unittest.TestCase):
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
            observed_at="2026-09-24T12:00:00Z",
            attributes={
                "instance_type": "m7i.2xlarge",
                "state": "running",
                "region": "us-east-1",
            },
            source_hash=H("resource-snapshot"),
            source_locator="aws-readonly://ec2/i-1",
            verified=True,
        )
        return temp, plan, action, approval, envelope, snapshot

    def test_exact_authorization_and_snapshot_produce_non_executable_plan(self):
        temp, plan, action, approval, envelope, snapshot = self.fixtures()
        with temp:
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
            self.assertFalse(dry.live_execution_allowed)
            self.assertFalse(dry.mutation_performed)
            self.assertIsNone(dry.provider_api_operation)
            self.assertEqual(dry.risk_level, "MODIFY")
            self.assertEqual(dry.parameters["target_instance_type"], "m7i.xlarge")

    def test_stale_resource_state_fails_closed(self):
        temp, plan, action, approval, envelope, snapshot = self.fixtures()
        with temp:
            request = CloudRemediationDryRunRequest(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                expected_resource_state_hash=H("stale"),
                parameters={"target_instance_type": "m7i.xlarge"},
            )
            with self.assertRaisesRegex(ValueError, "state changed"):
                prepare_cloud_remediation_dry_run(
                    plan=plan,
                    approval=approval,
                    envelope=envelope,
                    snapshot=snapshot,
                    request=request,
                )

    def test_missing_required_action_parameter_fails_closed(self):
        temp, plan, action, approval, envelope, snapshot = self.fixtures()
        with temp:
            request = CloudRemediationDryRunRequest(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                expected_resource_state_hash=snapshot.state_hash,
                parameters={},
            )
            with self.assertRaisesRegex(ValueError, "missing required"):
                prepare_cloud_remediation_dry_run(
                    plan=plan,
                    approval=approval,
                    envelope=envelope,
                    snapshot=snapshot,
                    request=request,
                )

    def test_policy_can_narrow_allowlist(self):
        temp, plan, action, approval, envelope, snapshot = self.fixtures()
        with temp:
            request = CloudRemediationDryRunRequest(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                expected_resource_state_hash=snapshot.state_hash,
                parameters={"target_instance_type": "m7i.xlarge"},
            )
            with self.assertRaisesRegex(ValueError, "not allowlisted"):
                prepare_cloud_remediation_dry_run(
                    plan=plan,
                    approval=approval,
                    envelope=envelope,
                    snapshot=snapshot,
                    request=request,
                    policy=CloudRemediationExecutorPolicy(
                        allowed_action_types=("remove_idle_resource",)
                    ),
                )

    def test_unverified_snapshot_fails_closed(self):
        temp, plan, action, approval, envelope, snapshot = self.fixtures()
        with temp:
            unverified = CloudResourceSnapshot(
                provider=snapshot.provider,
                account_id=snapshot.account_id,
                resource_id=snapshot.resource_id,
                resource_type=snapshot.resource_type,
                observed_at=snapshot.observed_at,
                attributes=snapshot.attributes,
                source_hash=snapshot.source_hash,
                source_locator=snapshot.source_locator,
                verified=False,
            )
            request = CloudRemediationDryRunRequest(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                expected_resource_state_hash=unverified.state_hash,
                parameters={"target_instance_type": "m7i.xlarge"},
            )
            with self.assertRaisesRegex(ValueError, "independently verified"):
                prepare_cloud_remediation_dry_run(
                    plan=plan,
                    approval=approval,
                    envelope=envelope,
                    snapshot=unverified,
                    request=request,
                )


if __name__ == "__main__":
    unittest.main()
