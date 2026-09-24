from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest

from recoveryworks.environment_activation import build_environment_state_discovery
from recoveryworks.incident_lifecycle import IncidentLifecycleJournal
from recoveryworks.integrations.cletrics_registry import (
    CletricsProcessingReceipt,
    CletricsReceiptRegistry,
)
from recoveryworks.models import canonical_hash
from recoveryworks.production_assurance_continuous import (
    ContinuousAssurancePolicy,
    ProductionAssuranceState,
    evaluate_continuous_production_assurance,
)
from recoveryworks.production_observability import (
    ProductionRunHistoryStore,
    ProductionRunManifest,
    ProductionRunStatus,
)
from recoveryworks.production_resilience import (
    DisasterRecoveryRehearsal,
    ProductionBackupArtifact,
    ProductionBackupManifest,
    ProductionBackupPolicy,
)
from recoveryworks.release_control import RecoveryWorksReleaseManifest


def fake_release():
    ident={
        "schema":1,"version":"1.0.0","source_commit":"a"*40,
        "container_build_manifest_proof_hash":"1"*64,
        "container_image_ref":"registry/x@sha256:"+"2"*64,
        "container_image_digest":"2"*64,
        "production_deployment_proof_hash":"3"*64,
        "created_at":"2026-09-24T10:00:00Z",
        "immutable":True,"published":False,"deployed":False}
    return RecoveryWorksReleaseManifest(
        release_id="recoveryworks-release:"+canonical_hash(ident),
        version="1.0.0",source_commit="a"*40,
        container_build_manifest_proof_hash="1"*64,
        container_image_ref=ident["container_image_ref"],
        container_image_digest="2"*64,
        production_deployment_proof_hash="3"*64,
        created_at=ident["created_at"])


def fixture(root: Path):
    release=fake_release()
    admission=SimpleNamespace(
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        container_image_digest=release.container_image_digest,
        source_commit=release.source_commit,
        proof_hash="4"*64,
    )
    environment=build_environment_state_discovery(
        provider="aws",account_id="acct",environment_id="prod",
        observed_at="2026-09-24T12:00:00Z",
        current_release_id=release.release_id,
        current_image_digest=release.container_image_digest,
        resource_summary={"resources":1},source_hash="5"*64,
        source_locator="aws://prod",verified=True)
    scan=SimpleNamespace(
        proof_hash="6"*64, scanned_at="2026-09-24T11:30:00Z", verified=True)
    sig=SimpleNamespace(
        proof_hash="7"*64, verified_at="2026-09-24T11:35:00Z")
    prov=SimpleNamespace(
        proof_hash="8"*64, verified_at="2026-09-24T11:40:00Z")
    security=SimpleNamespace(
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        container_image_digest=release.container_image_digest,
        vulnerability_scan_proof_hash=scan.proof_hash,
        signature_verification_proof_hash=sig.proof_hash,
        provenance_verification_proof_hash=prov.proof_hash,
        proof_hash="9"*64,
    )
    dr_id={
        "schema":1,"backup_id":"backup","backup_proof_hash":"a"*64,
        "started_at":"2026-09-24T10:30:00Z",
        "completed_at":"2026-09-24T10:31:00Z",
        "rpo_seconds":60,"rto_seconds":60,
        "restored_artifact_hashes":{
            "ledger":"b"*64,"cletrics_receipts":"c"*64,
            "assurance_report":"d"*64,"run_history":"e"*64},
        "semantic_checks":["ok"],"passed":True}
    dr=DisasterRecoveryRehearsal(
        rehearsal_id="recoveryworks-dr-rehearsal:"+canonical_hash(dr_id),
        backup_id="backup",backup_proof_hash="a"*64,
        started_at=dr_id["started_at"],completed_at=dr_id["completed_at"],
        rpo_seconds=60,rto_seconds=60,
        restored_artifact_hashes=dr_id["restored_artifact_hashes"],
        semantic_checks=("ok",),passed=True)
    policy=ProductionBackupPolicy(
        retention_days=30,max_rpo_seconds=300,max_rto_seconds=120)
    artifacts=tuple(
        ProductionBackupArtifact(
            role=role,archive_name=name,sha256=value,size_bytes=1)
        for role,name,value in (
            ("ledger","ledger.json","1"*64),
            ("cletrics_receipts","cletrics-receipts.json","2"*64),
            ("assurance_report","assurance-report.json","3"*64),
            ("run_history","run-history.json","4"*64),
        )
    )
    backup_ident={
        "schema":1,"created_at":"2026-09-24T11:00:00Z",
        "source_checkpoint_at":"2026-09-24T10:59:00Z",
        "expires_at":"2026-10-24T11:00:00Z",
        "policy":policy.as_dict(),"rpo_seconds":60,
        "archive_sha256":"5"*64,
        "artifacts":[__import__("dataclasses").asdict(x) for x in sorted(
            artifacts,key=lambda x:x.role)]}
    backup=ProductionBackupManifest(
        backup_id="recoveryworks-production-backup:"+canonical_hash(backup_ident),
        created_at=backup_ident["created_at"],
        source_checkpoint_at=backup_ident["source_checkpoint_at"],
        expires_at=backup_ident["expires_at"],policy=policy,rpo_seconds=60,
        archive_sha256="5"*64,artifacts=artifacts)

    history=ProductionRunHistoryStore(root/"run-history.json")
    run_ident={
        "schema":1,"run_id":"run-1","deployment_id":"dep",
        "deployment_plan_proof_hash":"a"*64,
        "container_build_manifest_proof_hash":"1"*64,
        "client_id":"client","provider":"aws",
        "started_at":"2026-09-24T11:45:00Z",
        "completed_at":"2026-09-24T11:46:00Z",
        "status":"SUCCEEDED","failure_code":None,"failure_detail":None,
        "state_head_hash":"b"*64,"assurance_report_proof_hash":"c"*64,
        "metrics_proof_hash":"d"*64,"event_hashes":[],"alert_hashes":[]}
    manifest=ProductionRunManifest(
        manifest_id="recoveryworks-production-run:"+canonical_hash(run_ident),
        run_id="run-1",deployment_id="dep",
        deployment_plan_proof_hash="a"*64,
        container_build_manifest_proof_hash="1"*64,
        client_id="client",provider="aws",
        started_at=run_ident["started_at"],completed_at=run_ident["completed_at"],
        status=ProductionRunStatus.SUCCEEDED,failure_code=None,failure_detail=None,
        state_head_hash="b"*64,assurance_report_proof_hash="c"*64,
        metrics_proof_hash="d"*64,event_hashes=(),alert_hashes=())
    history.record(manifest,recorded_at="2026-09-24T11:47:00Z")

    registry=CletricsReceiptRegistry(root/"receipts.json")
    registry.record((CletricsProcessingReceipt(
        job_fingerprint="e"*64,mode="cloud",bundle_sha256="f"*64,
        manifest_sha256="1"*64,client_id="client",provider="aws",
        billing_account_id="acct",period_start="2026-09-01",
        period_end="2026-09-23",exported_at="2026-09-24T11:20:00Z",
        authority_hashes={"rates":"2"*64},
        verification_flags={
            "charge_source_verified":True,
            "meter_source_verified":True,
            "rate_source_verified":True},
        scan_head_hash="3"*64),))
    incidents=IncidentLifecycleJournal(root/"incidents.json")
    return release,admission,environment,security,scan,sig,prov,dr,backup,history,registry,incidents


class ContinuousProductionAssuranceTests(unittest.TestCase):
    def test_all_current_controls_pass(self):
        with tempfile.TemporaryDirectory() as d:
            args=fixture(Path(d))
            assurance=evaluate_continuous_production_assurance(
                release=args[0],admission=args[1],environment=args[2],
                security_evidence=args[3],vulnerability_scan=args[4],
                signature_receipt=args[5],provenance_receipt=args[6],
                dr_rehearsal=args[7],backup=args[8],run_history=args[9],
                cletrics_registry=args[10],incident_journal=args[11],
                checked_at="2026-09-24T12:05:00Z")
            self.assertIs(assurance.state,ProductionAssuranceState.PASS)
            self.assertTrue(all(check.passed for check in assurance.checks))

    def test_release_drift_or_stale_cloud_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            args=list(fixture(Path(d)))
            drift=build_environment_state_discovery(
                provider="aws",account_id="acct",environment_id="prod",
                observed_at="2026-09-24T12:00:00Z",
                current_release_id="other",current_image_digest="9"*64,
                resource_summary={"resources":1},source_hash="5"*64,
                source_locator="aws://prod",verified=True)
            args[2]=drift
            assurance=evaluate_continuous_production_assurance(
                release=args[0],admission=args[1],environment=args[2],
                security_evidence=args[3],vulnerability_scan=args[4],
                signature_receipt=args[5],provenance_receipt=args[6],
                dr_rehearsal=args[7],backup=args[8],run_history=args[9],
                cletrics_registry=args[10],incident_journal=args[11],
                checked_at="2026-09-24T12:05:00Z")
            self.assertIs(assurance.state,ProductionAssuranceState.BLOCKED)

    def test_unverified_cloud_evidence_requires_review_not_automatic_action(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=list(fixture(root))
            registry=CletricsReceiptRegistry(root/"review-receipts.json")
            registry.record((CletricsProcessingReceipt(
                job_fingerprint="4"*64,mode="cloud",bundle_sha256="5"*64,
                manifest_sha256="6"*64,client_id="client",provider="aws",
                billing_account_id="acct",period_start="2026-09-01",
                period_end="2026-09-23",exported_at="2026-09-24T11:20:00Z",
                authority_hashes={"rates":"7"*64},
                verification_flags={
                    "charge_source_verified":True,
                    "meter_source_verified":True,
                    "rate_source_verified":False},
                scan_head_hash="8"*64),))
            args[10]=registry
            assurance=evaluate_continuous_production_assurance(
                release=args[0],admission=args[1],environment=args[2],
                security_evidence=args[3],vulnerability_scan=args[4],
                signature_receipt=args[5],provenance_receipt=args[6],
                dr_rehearsal=args[7],backup=args[8],run_history=args[9],
                cletrics_registry=args[10],incident_journal=args[11],
                checked_at="2026-09-24T12:05:00Z")
            self.assertIs(
                assurance.state,ProductionAssuranceState.REVIEW_REQUIRED)
            self.assertFalse(assurance.automatic_remediation_enabled)
            self.assertFalse(assurance.external_actions_performed)


if __name__=="__main__":
    unittest.main()
