from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.models import canonical_hash
from recoveryworks.production_admission import (
    ProductionAdmissionGate,
    ProductionAdmissionPolicy,
)
from recoveryworks.production_deployment import (
    build_production_deployment_contract,
    check_production_health,
    check_production_readiness,
)
from recoveryworks.release_control import (
    ReleaseEnvironment,
    approve_release,
    build_environment_promotion_gate,
    build_release_manifest,
    build_rollback_manifest,
)
from recoveryworks.release_deployment_handoff import (
    DeploymentEnvironmentSnapshot,
    ExternalDeploymentReceipt,
    prepare_release_deployment_handoff,
    validate_external_deployment,
)


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def deployment_spec(root: Path, image: str) -> dict:
    config = root / "config"
    inputs = root / "inputs"
    state = root / "private" / "state"
    reports = root / "private" / "reports"
    for path in (config, inputs, state, reports):
        path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        state.chmod(0o700)
        reports.chmod(0o700)
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "Amazon Web Services,acct-1,EC2,2026-08-31T00:00:00Z,"
        "40.00,USD,i-1\n", encoding="utf-8")
    (inputs / "meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-1,10,i-1,EC2,2026-08-31\n", encoding="utf-8")
    (inputs / "rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8")
    pilot = {
        "schema":1,"deployment_id":"handoff-pilot","client_id":"client-handoff",
        "currency":"USD","provider":"aws",
        "security":{
            "cloud_access_mode":"READ_ONLY",
            "recoveryos_provider_write_credentials":False,
            "remediation_execution_enabled":False,
            "external_actions_enabled":False,
            "private_state_required":True,
        },
        "period":{"start":"2026-08-01","end":"2026-08-31","exported_at":"2026-09-01T12:00:00Z"},
        "cletrics":{"focus_csv":str(inputs/"focus.csv"),"meter_csv":str(inputs/"meter.csv"),
                    "release":"test","commit":"a"*40},
        "recoveryos":{"rates_csv":str(inputs/"rates.csv"),"bundle_path":str(state/"bundle.zip"),
                      "ledger_path":str(state/"ledger.json"),"receipt_registry_path":str(state/"receipts.json"),
                      "report_path":str(reports/"assurance.json")},
    }
    (config/"pilot.json").write_text(json.dumps(pilot),encoding="utf-8")
    return {
        "schema":1,"pilot_spec":str(config/"pilot.json"),
        "service":{
            "image_ref":image,"user":"65532:65532",
            "command":["python","-m","recoveryworks.pilot_runner","--spec","/config/pilot.json","--base-dir","/workspace"],
            "read_only_root_filesystem":True,"privileged":False,"host_network":False,
            "network_disabled":True,"no_new_privileges":True,"cap_drop_all":True,
            "provider_write_credentials":False,"remediation_execution_enabled":False,
            "external_actions_enabled":False,
        },
        "volumes":{
            "config":{"host_path":str(config),"container_path":"/config","read_only":True,"private_required":False},
            "inputs":{"host_path":str(inputs),"container_path":"/inputs","read_only":True,"private_required":False},
            "state":{"host_path":str(state),"container_path":"/state","read_only":False,"private_required":True},
            "reports":{"host_path":str(reports),"container_path":"/reports","read_only":False,"private_required":True},
        },
    }


class ReleaseDeploymentHandoffTests(unittest.TestCase):
    def fixture(self, root: Path):
        image = "registry.example/recoveryworks@sha256:" + "c"*64
        deployment = build_production_deployment_contract(
            deployment_spec(root, image), base_dir=root)
        build = build_container_build_manifest(
            source_commit="a"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        release = build_release_manifest(
            version="1.0.0", build_manifest=build, deployment=deployment,
            container_image_ref=image, created_at="2026-09-24T13:00:00Z")
        previous_image = "registry.example/recoveryworks@sha256:" + "d"*64
        previous_deployment = build_production_deployment_contract(
            deployment_spec(root/"previous", previous_image), base_dir=root/"previous")
        previous = build_release_manifest(
            version="0.9.0",
            build_manifest=build_container_build_manifest(
                source_commit="b"*40,
                dockerfile_path="recoveryworks/deploy/Dockerfile.production",
                dependency_lock_path="recoveryworks/requirements.production.lock"),
            deployment=previous_deployment, container_image_ref=previous_image,
            created_at="2026-09-23T13:00:00Z")
        rollback = build_rollback_manifest(
            release, previous, reason="rollback", created_at="2026-09-24T13:01:00Z")
        approvals = (
            approve_release(release, environment=ReleaseEnvironment.PRODUCTION,
                            approver_id="release-manager", role="RELEASE_MANAGER",
                            approved_at="2026-09-24T13:02:00Z"),
            approve_release(release, environment=ReleaseEnvironment.PRODUCTION,
                            approver_id="ops-owner", role="OPERATIONS_OWNER",
                            approved_at="2026-09-24T13:03:00Z"),
        )
        gate = build_environment_promotion_gate(
            release, environment=ReleaseEnvironment.PRODUCTION,
            approvals=approvals, health_check=check_production_health(deployment),
            readiness_check=check_production_readiness(deployment),
            rollback_manifest=rollback, gate_created_at="2026-09-24T13:04:00Z")
        policy = ProductionAdmissionPolicy()
        admission_identity = {
            "schema": 1,
            "release_id": release.release_id,
            "release_proof_hash": release.proof_hash,
            "promotion_gate_proof_hash": gate.proof_hash,
            "security_evidence_proof_hash": "1" * 64,
            "dr_rehearsal_proof_hash": "2" * 64,
            "container_build_manifest_proof_hash": build.proof_hash,
            "container_image_digest": release.container_image_digest,
            "source_commit": release.source_commit,
            "admitted_at": "2026-09-24T13:04:30Z",
            "policy": asdict(policy),
            "admitted": True,
            "deployment_execution_enabled": False,
        }
        admission = ProductionAdmissionGate(
            admission_id="recoveryworks-production-admission:"
            + canonical_hash(admission_identity),
            release_id=release.release_id,
            release_proof_hash=release.proof_hash,
            promotion_gate_proof_hash=gate.proof_hash,
            security_evidence_proof_hash="1" * 64,
            dr_rehearsal_proof_hash="2" * 64,
            container_build_manifest_proof_hash=build.proof_hash,
            container_image_digest=release.container_image_digest,
            source_commit=release.source_commit,
            admitted_at="2026-09-24T13:04:30Z",
            policy=policy,
            admitted=True,
            deployment_execution_enabled=False,
        )
        return release, gate, admission

    def test_separate_deployer_handoff_and_post_deploy_verification(self):
        with tempfile.TemporaryDirectory() as d:
            release, gate, admission = self.fixture(Path(d))
            handoff = prepare_release_deployment_handoff(
                release, gate, admission, deployer_id="external-deployer",
                issued_at="2026-09-24T13:05:00Z",
                expires_at="2026-09-24T13:20:00Z")
            self.assertEqual(
                handoff.as_dict()["state"], "READY_FOR_SEPARATE_DEPLOYER")
            receipt_identity = {
                "schema":1,"handoff_id":handoff.handoff_id,
                "handoff_proof_hash":handoff.proof_hash,
                "release_id":release.release_id,"release_proof_hash":release.proof_hash,
                "environment":"PRODUCTION","deployer_id":"external-deployer",
                "deployed_at":"2026-09-24T13:10:00Z",
                "container_image_ref":release.container_image_ref,
                "container_image_digest":release.container_image_digest,
                "source_commit":release.source_commit,
                "production_deployment_proof_hash":release.production_deployment_proof_hash,
                "external_deployment_id":"deploy-123",
                "source_hash":H("deploy-receipt"),"source_locator":"deployer://deploy-123",
                "verified":True,
            }
            receipt = ExternalDeploymentReceipt(
                receipt_id="recoveryworks-deployment-receipt:"+canonical_hash(receipt_identity),
                **{k:v for k,v in receipt_identity.items() if k!="schema"})
            snapshot_identity = {
                "schema":1,"environment":"PRODUCTION","observed_at":"2026-09-24T13:12:00Z",
                "release_id":release.release_id,"release_proof_hash":release.proof_hash,
                "container_image_ref":release.container_image_ref,
                "container_image_digest":release.container_image_digest,
                "source_commit":release.source_commit,
                "production_deployment_proof_hash":release.production_deployment_proof_hash,
                "health_receipt_hash":H("health"),"readiness_receipt_hash":H("readiness"),
                "health_passed":True,"readiness_passed":True,
                "source_hash":H("environment"),"source_locator":"environment://prod",
                "verified":True,
            }
            snapshot = DeploymentEnvironmentSnapshot(
                snapshot_id="recoveryworks-environment-snapshot:"+canonical_hash(snapshot_identity),
                **{k:v for k,v in snapshot_identity.items() if k!="schema"})
            validated = validate_external_deployment(handoff, receipt, snapshot)
            self.assertEqual(validated.as_dict()["state"], "DEPLOYMENT_VERIFIED")

    def test_wrong_image_or_failed_post_health_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            release, gate, admission = self.fixture(Path(d))
            handoff = prepare_release_deployment_handoff(
                release, gate, admission, deployer_id="external-deployer",
                issued_at="2026-09-24T13:05:00Z",
                expires_at="2026-09-24T13:20:00Z")
            bad_identity = {
                "schema":1,"handoff_id":handoff.handoff_id,
                "handoff_proof_hash":handoff.proof_hash,
                "release_id":release.release_id,"release_proof_hash":release.proof_hash,
                "environment":"PRODUCTION","deployer_id":"external-deployer",
                "deployed_at":"2026-09-24T13:10:00Z",
                "container_image_ref":"registry.example/recoveryworks@sha256:"+"e"*64,
                "container_image_digest":"e"*64,"source_commit":release.source_commit,
                "production_deployment_proof_hash":release.production_deployment_proof_hash,
                "external_deployment_id":"deploy-123","source_hash":H("bad"),
                "source_locator":"deployer://bad","verified":True,
            }
            receipt = ExternalDeploymentReceipt(
                receipt_id="recoveryworks-deployment-receipt:"+canonical_hash(bad_identity),
                **{k:v for k,v in bad_identity.items() if k!="schema"})
            snapshot_identity = {
                "schema":1,"environment":"PRODUCTION","observed_at":"2026-09-24T13:12:00Z",
                "release_id":release.release_id,"release_proof_hash":release.proof_hash,
                "container_image_ref":release.container_image_ref,
                "container_image_digest":release.container_image_digest,
                "source_commit":release.source_commit,
                "production_deployment_proof_hash":release.production_deployment_proof_hash,
                "health_receipt_hash":H("health"),"readiness_receipt_hash":H("readiness"),
                "health_passed":False,"readiness_passed":True,
                "source_hash":H("environment"),"source_locator":"environment://prod",
                "verified":True,
            }
            snapshot = DeploymentEnvironmentSnapshot(
                snapshot_id="recoveryworks-environment-snapshot:"+canonical_hash(snapshot_identity),
                **{k:v for k,v in snapshot_identity.items() if k!="schema"})
            with self.assertRaisesRegex(ValueError, "container_image_ref mismatch"):
                validate_external_deployment(handoff, receipt, snapshot)


if __name__ == "__main__":
    unittest.main()
