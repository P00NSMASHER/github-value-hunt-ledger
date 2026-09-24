from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.pilot_runner import run_local_pilot
from recoveryworks.tenant_isolation import (
    TenantBindingRegistry,
    TenantIdentity,
    bind_managed_tenant_artifact,
)
from recoveryworks.test_pilot_runner import LocalPilotRunnerTests
from recoveryworks.enterprise_diligence_package import (
    build_enterprise_diligence_package,
    write_enterprise_diligence_package,
)
from recoveryworks.test_enterprise_diligence_package import control_map
from recoveryworks.production_observability import (
    ProductionRunHistoryStore,
    build_success_observability,
)
from recoveryworks.production_resilience import (
    ProductionBackupPolicy,
    create_production_backup,
)


class TenantIsolationTests(unittest.TestCase):
    def test_pilot_binds_private_paths_and_rejects_cross_tenant_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            spec=LocalPilotRunnerTests().build_spec(root)
            spec["tenant_id"]="tenant-a"
            first=run_local_pilot(spec,base_dir=root)
            self.assertEqual(first.tenant_id,"tenant-a")
            registry=TenantBindingRegistry(root/".recoveryworks-tenant-bindings.json")
            tenant_a=TenantIdentity(
                tenant_id="tenant-a",client_id="client-1",namespace=str(root),
                created_at=spec["period"]["exported_at"])
            registry.assert_path_tenant(
                tenant_a,root/spec["recoveryos"]["ledger_path"])
            registry.assert_proof_tenant(tenant_a,first.export_receipt.bundle_sha256)

            # A second customer attempting to reuse the exact same state paths
            # fails before the exporter/ledger can overwrite them.
            spec2=dict(spec)
            spec2["client_id"]="client-2"
            spec2["tenant_id"]="tenant-b"
            with self.assertRaisesRegex(ValueError,"tenant path collision"):
                run_local_pilot(spec2,base_dir=root)


    def test_run_history_and_backup_inherit_same_tenant_registry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            spec=LocalPilotRunnerTests().build_spec(root)
            spec["tenant_id"]="tenant-a"
            pilot=run_local_pilot(spec,base_dir=root)
            manifest, *_ = build_success_observability(
                run_id="tenant-run-1",
                deployment_id=spec["deployment_id"],
                pilot=pilot,
                container_build_manifest_proof_hash="a"*64,
                started_at="2026-09-24T13:00:00Z",
                completed_at="2026-09-24T13:01:00Z",
            )
            history=ProductionRunHistoryStore(root/"private"/"run-history.json")
            history.record(manifest,recorded_at="2026-09-24T13:02:00Z")
            registry=TenantBindingRegistry(root/".recoveryworks-tenant-bindings.json")
            tenant=TenantIdentity(
                tenant_id="tenant-a",client_id="client-1",namespace=str(root),
                created_at=spec["period"]["exported_at"])
            registry.assert_path_tenant(tenant,history.path)

            backup=create_production_backup(
                sources={
                    "ledger": root/spec["recoveryos"]["ledger_path"],
                    "cletrics_receipts":
                        root/spec["recoveryos"]["receipt_registry_path"],
                    "assurance_report": root/spec["recoveryos"]["report_path"],
                    "run_history": history.path,
                },
                policy=ProductionBackupPolicy(
                    retention_days=30,max_rpo_seconds=300,max_rto_seconds=120),
                created_at="2026-09-24T13:03:00Z",
                source_checkpoint_at="2026-09-24T13:02:00Z",
                archive_path=root/"private"/"backup.zip",
                manifest_path=root/"private"/"backup-manifest.json",
            )
            registry.assert_proof_tenant(tenant,backup.proof_hash)
            registry.assert_path_tenant(tenant,root/"private"/"backup.zip")


    def test_managed_diligence_can_share_tenant_registry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            registry=TenantBindingRegistry(
                root/".recoveryworks-tenant-bindings.json")
            tenant=TenantIdentity(
                tenant_id="tenant-a",client_id="client-a",namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            registry.reserve_paths(
                tenant,artifact_paths={"seed":root/"seed.json"})
            package=build_enterprise_diligence_package(
                control_map(),
                generated_at="2026-09-24T13:00:00Z",
                tenant_identity=tenant,
            )
            json_path=root/"private"/"diligence.json"
            md_path=root/"private"/"diligence.md"
            write_enterprise_diligence_package(
                package,
                json_path=json_path,
                markdown_path=md_path,
                tenant_registry=registry,
            )
            registry.assert_path_tenant(tenant,json_path)
            registry.assert_proof_tenant(tenant,package.proof_hash)

    def test_same_proof_cannot_be_bound_to_two_tenants(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            registry=TenantBindingRegistry(root/"registry.json")
            a=TenantIdentity(
                tenant_id="a",client_id="client-a",namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            b=TenantIdentity(
                tenant_id="b",client_id="client-b",namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            bind_managed_tenant_artifact(
                registry,a,artifact_type="backup",artifact_key="backup-1",
                proof_hash="1"*64,path=root/"a-backup.json",
                bound_at="2026-09-24T12:01:00Z")
            with self.assertRaisesRegex(ValueError,"tenant proof collision"):
                bind_managed_tenant_artifact(
                    registry,b,artifact_type="diligence",
                    artifact_key="diligence-1",proof_hash="1"*64,
                    path=root/"b-diligence.json",
                    bound_at="2026-09-24T12:02:00Z")


if __name__=="__main__":
    unittest.main()
