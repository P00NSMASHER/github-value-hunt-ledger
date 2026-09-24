from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.pilot_runner import run_local_pilot
from recoveryworks.production_observability import (
    ProductionRunHistoryStore,
    build_success_observability,
)
from recoveryworks.production_resilience import (
    ProductionBackupPolicy,
    create_production_backup,
    rehearse_production_restore,
)
from recoveryworks.private_io import private_permissions_verified


def pilot_spec(root: Path) -> dict:
    inputs=root/"inputs"; inputs.mkdir()
    (inputs/"focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "Amazon Web Services,acct-1,EC2,2026-08-31T00:00:00Z,40.00,USD,i-1\n",
        encoding="utf-8")
    (inputs/"meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-1,10,i-1,EC2,2026-08-31\n",encoding="utf-8")
    (inputs/"rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",encoding="utf-8")
    return {
        "schema":1,"deployment_id":"dr-pilot","client_id":"client-dr",
        "currency":"USD","provider":"aws",
        "security":{
            "cloud_access_mode":"READ_ONLY",
            "recoveryos_provider_write_credentials":False,
            "remediation_execution_enabled":False,
            "external_actions_enabled":False,
            "private_state_required":True,
        },
        "period":{"start":"2026-08-01","end":"2026-08-31","exported_at":"2026-09-01T12:00:00Z"},
        "cletrics":{"focus_csv":"inputs/focus.csv","meter_csv":"inputs/meter.csv",
                    "release":"dr-test","commit":"a"*40},
        "recoveryos":{"rates_csv":"inputs/rates.csv","verification":{
            "charge_source_verified":True,"meter_source_verified":True,
            "rate_source_verified":True},
            "bundle_path":"private/bundle.zip","ledger_path":"private/ledger.json",
            "receipt_registry_path":"private/receipts.json",
            "report_path":"private/assurance.json"},
    }


class ProductionResilienceTests(unittest.TestCase):
    def state(self, root: Path):
        pilot = run_local_pilot(pilot_spec(root), base_dir=root)
        manifest, *_ = build_success_observability(
            run_id="run-dr-1", deployment_id="dr-pilot", pilot=pilot,
            container_build_manifest_proof_hash="a"*64,
            started_at="2026-09-24T12:00:00Z",
            completed_at="2026-09-24T12:01:00Z")
        history = ProductionRunHistoryStore(root/"private"/"run-history.json")
        history.record(manifest, recorded_at="2026-09-24T12:02:00Z")
        return {
            "ledger": root/"private"/"ledger.json",
            "cletrics_receipts": root/"private"/"receipts.json",
            "assurance_report": root/"private"/"assurance.json",
            "run_history": history.path,
        }

    def test_private_backup_and_semantic_restore_rehearsal_meet_rpo_rto(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            sources=self.state(root)
            policy=ProductionBackupPolicy(
                retention_days=30,max_rpo_seconds=300,max_rto_seconds=120)
            archive=root/"private"/"backup.zip"
            manifest_path=root/"private"/"backup-manifest.json"
            manifest=create_production_backup(
                sources=sources,policy=policy,
                created_at="2026-09-24T12:03:00Z",
                source_checkpoint_at="2026-09-24T12:02:00Z",
                archive_path=archive,manifest_path=manifest_path)
            self.assertEqual(manifest.rpo_seconds,60)
            self.assertTrue(private_permissions_verified(archive))
            self.assertTrue(private_permissions_verified(manifest_path))
            rehearsal=rehearse_production_restore(
                manifest,archive_path=archive,
                restore_dir=root/"restore",
                started_at="2026-09-24T12:04:00Z",
                completed_at="2026-09-24T12:04:45Z")
            self.assertEqual(rehearsal.rto_seconds,45)
            self.assertEqual(rehearsal.as_dict()["state"],"DR_REHEARSAL_PASSED")
            self.assertEqual(len(rehearsal.restored_artifact_hashes),4)

    def test_tampered_archive_and_missed_rpo_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sources=self.state(root)
            policy=ProductionBackupPolicy(
                retention_days=30,max_rpo_seconds=60,max_rto_seconds=120)
            with self.assertRaisesRegex(ValueError,"exceeds configured RPO"):
                create_production_backup(
                    sources=sources,policy=policy,
                    created_at="2026-09-24T12:05:00Z",
                    source_checkpoint_at="2026-09-24T12:02:00Z",
                    archive_path=root/"backup.zip",
                    manifest_path=root/"manifest.json")

    def test_restore_rehearsal_fails_when_archive_bytes_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sources=self.state(root)
            manifest=create_production_backup(
                sources=sources,
                policy=ProductionBackupPolicy(
                    retention_days=30,max_rpo_seconds=300,max_rto_seconds=120),
                created_at="2026-09-24T12:03:00Z",
                source_checkpoint_at="2026-09-24T12:02:00Z",
                archive_path=root/"private"/"backup.zip",
                manifest_path=root/"private"/"manifest.json")
            archive=root/"private"/"backup.zip"
            archive.write_bytes(archive.read_bytes()+b"tamper")
            if os.name!="nt":
                archive.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"archive hash mismatch"):
                rehearse_production_restore(
                    manifest,archive_path=archive,restore_dir=root/"restore",
                    started_at="2026-09-24T12:04:00Z",
                    completed_at="2026-09-24T12:04:30Z")


if __name__=="__main__":
    unittest.main()
