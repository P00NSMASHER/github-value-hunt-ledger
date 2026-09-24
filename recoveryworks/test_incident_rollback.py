from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.incident_rollback import (
    ExternalRollbackReceipt,
    ProductionIncidentReason,
    approve_production_rollback,
    assess_post_deployment_incident,
    prepare_rollback_handoff,
    validate_external_rollback,
)
from recoveryworks.models import canonical_hash
from recoveryworks.release_control import (
    ReleaseEnvironment,
    build_release_manifest,
    build_rollback_manifest,
)
from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.production_deployment import build_production_deployment_contract
from recoveryworks.release_deployment_handoff import DeploymentEnvironmentSnapshot
from recoveryworks.test_release_control import production_spec


def H(v:str)->str:
    return hashlib.sha256(v.encode()).hexdigest()


class IncidentRollbackTests(unittest.TestCase):
    def releases(self, root: Path):
        current_image="registry.example/recoveryworks@sha256:"+"c"*64
        target_image="registry.example/recoveryworks@sha256:"+"d"*64
        current_build=build_container_build_manifest(
            source_commit="a"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        target_build=build_container_build_manifest(
            source_commit="b"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        current_dep=build_production_deployment_contract(
            production_spec(root/"current",current_image),base_dir=root/"current")
        target_dep=build_production_deployment_contract(
            production_spec(root/"target",target_image),base_dir=root/"target")
        current=build_release_manifest(
            version="1.0.0",build_manifest=current_build,deployment=current_dep,
            container_image_ref=current_image,created_at="2026-09-24T13:00:00Z")
        target=build_release_manifest(
            version="0.9.0",build_manifest=target_build,deployment=target_dep,
            container_image_ref=target_image,created_at="2026-09-23T13:00:00Z")
        rollback=build_rollback_manifest(
            current,target,reason="known-good rollback",
            created_at="2026-09-24T13:01:00Z")
        return current,target,rollback

    def snapshot(self, release, *, healthy=True, image_override=None):
        ident={
            "schema":1,"environment":"PRODUCTION",
            "observed_at":"2026-09-24T14:00:00Z",
            "release_id":release.release_id,
            "release_proof_hash":release.proof_hash,
            "container_image_ref":image_override or release.container_image_ref,
            "container_image_digest":
                ((image_override or release.container_image_ref).split("sha256:")[1]),
            "source_commit":release.source_commit,
            "production_deployment_proof_hash":
                release.production_deployment_proof_hash,
            "health_receipt_hash":H("health"),
            "readiness_receipt_hash":H("readiness"),
            "health_passed":healthy,"readiness_passed":healthy,
            "source_hash":H("snapshot"),"source_locator":"env://prod",
            "verified":True}
        return DeploymentEnvironmentSnapshot(
            snapshot_id="recoveryworks-environment-snapshot:"+canonical_hash(ident),
            **{k:v for k,v in ident.items() if k!="schema"})

    def test_health_failure_requires_two_approvals_and_verified_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            current,target,rollback=self.releases(Path(d))
            incident=assess_post_deployment_incident(
                current,self.snapshot(current,healthy=False),
                detected_at="2026-09-24T14:01:00Z")
            self.assertIn(ProductionIncidentReason.HEALTH_FAILURE,incident.reasons)
            approvals=(
                approve_production_rollback(
                    incident,rollback,target,approver_id="incident-commander",
                    role="INCIDENT_COMMANDER",approved_at="2026-09-24T14:02:00Z"),
                approve_production_rollback(
                    incident,rollback,target,approver_id="ops-owner",
                    role="OPERATIONS_OWNER",approved_at="2026-09-24T14:03:00Z"),
            )
            handoff=prepare_rollback_handoff(
                incident,rollback,target,approvals,
                deployer_id="external-deployer",
                issued_at="2026-09-24T14:04:00Z",
                expires_at="2026-09-24T14:20:00Z")
            receipt_i={
                "schema":1,"handoff_id":handoff.handoff_id,
                "handoff_proof_hash":handoff.proof_hash,
                "deployer_id":"external-deployer",
                "rolled_back_at":"2026-09-24T14:10:00Z",
                "target_release_id":target.release_id,
                "target_release_proof_hash":target.proof_hash,
                "target_image_ref":target.container_image_ref,
                "target_image_digest":target.container_image_digest,
                "target_source_commit":target.source_commit,
                "target_deployment_proof_hash":
                    target.production_deployment_proof_hash,
                "external_deployment_id":"rollback-123",
                "source_hash":H("rollback-receipt"),
                "source_locator":"deployer://rollback-123","verified":True}
            receipt=ExternalRollbackReceipt(
                receipt_id="recoveryworks-rollback-receipt:"+canonical_hash(receipt_i),
                **{k:v for k,v in receipt_i.items() if k!="schema"})
            post=self.snapshot(target,healthy=True)
            object.__setattr__(post,"observed_at","2026-09-24T14:11:00Z")
            validated=validate_external_rollback(handoff,receipt,post)
            self.assertEqual(validated.as_dict()["state"],"ROLLBACK_VERIFIED")

    def test_no_incident_or_single_production_approver_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            current,target,rollback=self.releases(Path(d))
            with self.assertRaisesRegex(ValueError,"does not indicate an incident"):
                assess_post_deployment_incident(
                    current,self.snapshot(current,healthy=True),
                    detected_at="2026-09-24T14:01:00Z")
            incident=assess_post_deployment_incident(
                current,self.snapshot(current,healthy=False),
                detected_at="2026-09-24T14:01:00Z")
            approval=approve_production_rollback(
                incident,rollback,target,approver_id="one",
                role="INCIDENT_COMMANDER",approved_at="2026-09-24T14:02:00Z")
            with self.assertRaisesRegex(ValueError,"2 distinct"):
                prepare_rollback_handoff(
                    incident,rollback,target,(approval,),deployer_id="deployer",
                    issued_at="2026-09-24T14:03:00Z",
                    expires_at="2026-09-24T14:20:00Z")

    def test_image_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            current,_,_=self.releases(Path(d))
            other="registry.example/recoveryworks@sha256:"+"9"*64
            incident=assess_post_deployment_incident(
                current,self.snapshot(current,healthy=True,image_override=other),
                detected_at="2026-09-24T14:01:00Z")
            self.assertIn(ProductionIncidentReason.IMAGE_DRIFT,incident.reasons)


if __name__=="__main__":
    unittest.main()
