from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.production_admission import (
    ProductionAdmissionPolicy,
    build_production_admission_gate,
)
from recoveryworks.production_resilience import (
    DisasterRecoveryRehearsal,
    ProductionBackupPolicy,
)
from recoveryworks.release_control import (
    ReleaseEnvironment,
    approve_release,
    build_environment_promotion_gate,
    build_release_manifest,
    build_rollback_manifest,
)
from recoveryworks.release_security import (
    ReleaseSecurityPolicy,
    build_container_attestation_input,
    build_release_sbom,
    build_release_security_gate,
    build_vulnerability_scan_receipt,
)
from recoveryworks.release_security_bridge import (
    ExternalProvenanceVerificationReceipt,
    ExternalSignatureVerificationReceipt,
    verify_external_release_security_evidence,
    write_cyclonedx_sbom,
)
from recoveryworks.models import canonical_hash
from recoveryworks.test_release_control import production_spec
from recoveryworks.production_deployment import (
    build_production_deployment_contract,
    check_production_health,
    check_production_readiness,
)


def H(value:str)->str:
    return hashlib.sha256(value.encode()).hexdigest()


class ProductionAdmissionTests(unittest.TestCase):
    def fixture(self, root: Path):
        image="registry.example/recoveryworks@sha256:"+"c"*64
        deployment=build_production_deployment_contract(
            production_spec(root,image),base_dir=root)
        build=build_container_build_manifest(
            source_commit="a"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        release=build_release_manifest(
            version="1.0.0",build_manifest=build,deployment=deployment,
            container_image_ref=image,created_at="2026-09-24T13:00:00Z")
        previous_image="registry.example/recoveryworks@sha256:"+"d"*64
        prev_dep=build_production_deployment_contract(
            production_spec(root/"prev",previous_image),base_dir=root/"prev")
        prev_build=build_container_build_manifest(
            source_commit="b"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        previous=build_release_manifest(
            version="0.9.0",build_manifest=prev_build,deployment=prev_dep,
            container_image_ref=previous_image,created_at="2026-09-23T13:00:00Z")
        rollback=build_rollback_manifest(
            release,previous,reason="rollback",created_at="2026-09-24T13:01:00Z")
        approvals=(
            approve_release(release,environment=ReleaseEnvironment.PRODUCTION,
                            approver_id="a1",role="RELEASE_MANAGER",
                            approved_at="2026-09-24T13:02:00Z"),
            approve_release(release,environment=ReleaseEnvironment.PRODUCTION,
                            approver_id="a2",role="OPERATIONS_OWNER",
                            approved_at="2026-09-24T13:03:00Z"),
        )
        promotion=build_environment_promotion_gate(
            release,environment=ReleaseEnvironment.PRODUCTION,approvals=approvals,
            health_check=check_production_health(deployment),
            readiness_check=check_production_readiness(deployment),
            rollback_manifest=rollback,gate_created_at="2026-09-24T13:04:00Z")
        sbom=build_release_sbom(
            release,build,repository_root=".",generated_at="2026-09-24T13:05:00Z")
        att=build_container_attestation_input(
            release,build,sbom,generated_at="2026-09-24T13:06:00Z")
        scan=build_vulnerability_scan_receipt(
            container_image_digest=release.container_image_digest,
            scanner_id="scanner",scanner_version="1",vulnerability_database_id="db",
            vulnerability_database_digest="e"*64,scanned_at="2026-09-24T13:07:00Z",
            severity_counts={"critical":0,"high":0},source_hash="f"*64,
            source_locator="scan://1",verified=True)
        security_gate=build_release_security_gate(
            release,sbom,att,scan,policy=ReleaseSecurityPolicy(),
            created_at="2026-09-24T13:08:00Z")
        with tempfile.TemporaryDirectory() as td:
            std=write_cyclonedx_sbom(release,sbom,path=Path(td)/"sbom.json")
            sig_i={"schema":1,"release_id":release.release_id,
                   "release_proof_hash":release.proof_hash,
                   "container_image_digest":release.container_image_digest,
                   "signer_identity":"key://signer","signature_algorithm":"ECDSA",
                   "signature_artifact_hash":"1"*64,
                   "verified_at":"2026-09-24T13:09:00Z","verifier_id":"sig-verifier",
                   "source_hash":"2"*64,"source_locator":"sig://1","verified":True}
            sig=ExternalSignatureVerificationReceipt(
                receipt_id="recoveryworks-signature-verification:"+canonical_hash(sig_i),
                **{k:v for k,v in sig_i.items() if k!="schema"})
            prov_i={"schema":1,"release_id":release.release_id,
                    "release_proof_hash":release.proof_hash,
                    "container_image_digest":release.container_image_digest,
                    "source_commit":release.source_commit,
                    "container_build_manifest_proof_hash":
                        release.container_build_manifest_proof_hash,
                    "sbom_proof_hash":sbom.proof_hash,
                    "predicate_type":"https://slsa.dev/provenance/v1",
                    "attestation_artifact_hash":"3"*64,
                    "verified_at":"2026-09-24T13:10:00Z",
                    "verifier_id":"prov-verifier","source_hash":"4"*64,
                    "source_locator":"prov://1","verified":True}
            prov=ExternalProvenanceVerificationReceipt(
                receipt_id="recoveryworks-provenance-verification:"+canonical_hash(prov_i),
                **{k:v for k,v in prov_i.items() if k!="schema"})
            sec_evidence=verify_external_release_security_evidence(
                release,security_gate,std,scan,sig,prov)
        dr_identity={
            "schema":1,"backup_id":"backup-1","backup_proof_hash":"5"*64,
            "started_at":"2026-09-24T12:00:00Z","completed_at":"2026-09-24T12:01:00Z",
            "rpo_seconds":60,"rto_seconds":60,
            "restored_artifact_hashes":{
                "ledger":"6"*64,"cletrics_receipts":"7"*64,
                "assurance_report":"8"*64,"run_history":"9"*64},
            "semantic_checks":["ok"],"passed":True}
        dr=DisasterRecoveryRehearsal(
            rehearsal_id="recoveryworks-dr-rehearsal:"+canonical_hash(dr_identity),
            backup_id="backup-1",backup_proof_hash="5"*64,
            started_at="2026-09-24T12:00:00Z",completed_at="2026-09-24T12:01:00Z",
            rpo_seconds=60,rto_seconds=60,
            restored_artifact_hashes=dr_identity["restored_artifact_hashes"],
            semantic_checks=("ok",),passed=True)
        return release,promotion,sec_evidence,dr,build

    def test_all_controls_required_for_admission(self):
        with tempfile.TemporaryDirectory() as d:
            release,promotion,security,dr,build=self.fixture(Path(d))
            gate=build_production_admission_gate(
                release,promotion,security,dr,build,
                admitted_at="2026-09-24T13:11:00Z")
            self.assertEqual(
                gate.as_dict()["state"],"PRODUCTION_ADMISSION_READY")
            self.assertFalse(gate.deployment_execution_enabled)

    def test_stale_dr_or_wrong_build_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            release,promotion,security,dr,build=self.fixture(Path(d))
            with self.assertRaisesRegex(ValueError,"too old"):
                build_production_admission_gate(
                    release,promotion,security,dr,build,
                    admitted_at="2026-10-10T13:11:00Z",
                    policy=ProductionAdmissionPolicy(max_dr_age_seconds=3600))
            wrong=replace(build, source_commit="b"*40)
            with self.assertRaisesRegex(ValueError,"source commit mismatch|manifest_id"):
                build_production_admission_gate(
                    release,promotion,security,dr,wrong,
                    admitted_at="2026-09-24T13:11:00Z")


if __name__=="__main__":
    unittest.main()
