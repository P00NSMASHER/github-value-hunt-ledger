from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoveryworks.models import canonical_hash
from recoveryworks.multicloud_orchestration import run_multicloud_orchestration
from recoveryworks.production_acceptance import (
    ProductionAcceptanceCheck,
    build_production_acceptance_report,
)
from recoveryworks.production_job_control import (
    JobScheduleMode,
    ProductionJobRegistry,
    ProductionJobType,
    build_production_job_schedule,
    plan_job_occurrence,
)
from recoveryworks.production_resilience import (
    ProductionBackupPolicy,
    create_production_backup,
    rehearse_production_restore,
)
from recoveryworks.tenant_isolation import (
    TenantBindingRegistry,
    TenantIdentity,
)
from recoveryworks.test_multicloud_execution import executable_job
from recoveryworks.test_production_resilience import ProductionResilienceTests


class ProductionChaosAcceptanceTests(unittest.TestCase):
    def test_full_chaos_recovery_acceptance_suite(self):
        checks = []

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            tenant = TenantIdentity(
                tenant_id="tenant",
                client_id="client",
                namespace=str(root),
                created_at="2026-09-24T12:00:00Z",
            )
            schedule = build_production_job_schedule(
                tenant,
                job_type=ProductionJobType.CONTINUOUS_ASSURANCE,
                payload_proof_hash="1" * 64,
                mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z",
            )
            job = plan_job_occurrence(schedule)
            registry = ProductionJobRegistry(root / "jobs.json")
            first = registry.acquire(
                job,
                worker_id="worker-a",
                acquired_at="2026-09-24T13:00:00Z",
                lease_seconds=30,
            )
            self.assertIn(
                job.job_id,
                registry.recoverable_jobs(observed_at="2026-09-24T13:01:00Z"),
            )
            second = registry.acquire(
                job,
                worker_id="worker-b",
                acquired_at="2026-09-24T13:01:00Z",
                lease_seconds=30,
            )
            self.assertEqual(first.attempt, 1)
            self.assertEqual(second.attempt, 2)
            checks.append(ProductionAcceptanceCheck(
                scenario="STALE_LEASE_RECOVERY",
                passed=True,
                detail="Expired worker lease was recovered by a later worker attempt.",
                evidence_proof_hash=second.proof_hash,
            ))

            registry.path.write_text(
                '{"schema":1,"payload":{"jobs":{}},"state_hash":"bad"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "state hash mismatch"):
                registry.completed_result(job)
            checks.append(ProductionAcceptanceCheck(
                scenario="CORRUPTED_STATE_FAIL_CLOSED",
                passed=True,
                detail="Tampered job registry state hash was rejected.",
            ))

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            tenant = TenantIdentity(
                tenant_id="tenant",
                client_id="client",
                namespace=str(root),
                created_at="2026-09-24T12:00:00Z",
            )
            schedule = build_production_job_schedule(
                tenant,
                job_type=ProductionJobType.PRIVATE_BACKUP,
                payload_proof_hash="2" * 64,
                mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z",
            )
            job = plan_job_occurrence(schedule)
            registry = ProductionJobRegistry(root / "jobs.json")
            with patch(
                "recoveryworks.production_job_control.atomic_private_write",
                side_effect=OSError("simulated disk write failure"),
            ):
                with self.assertRaisesRegex(OSError, "simulated disk write failure"):
                    registry.acquire(
                        job,
                        worker_id="worker",
                        acquired_at="2026-09-24T13:00:00Z",
                    )
            self.assertFalse(registry.path.exists())
            checks.append(ProductionAcceptanceCheck(
                scenario="ATOMIC_WRITE_FAILURE_FAIL_CLOSED",
                passed=True,
                detail="Injected registry write failure produced no partially committed job state.",
            ))

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            registry = TenantBindingRegistry(root / "tenant-registry.json")
            a = TenantIdentity(
                tenant_id="a", client_id="a", namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            b = TenantIdentity(
                tenant_id="b", client_id="b", namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            shared = root / "shared.json"
            registry.reserve_paths(a, artifact_paths={"ledger": shared})
            with self.assertRaisesRegex(ValueError, "tenant path collision"):
                registry.reserve_paths(b, artifact_paths={"ledger": shared})
            checks.append(ProductionAcceptanceCheck(
                scenario="TENANT_COLLISION_FAIL_CLOSED",
                passed=True,
                detail="Cross-tenant reuse of a managed state path was rejected.",
                evidence_proof_hash=registry.state_hash(),
            ))

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources = ProductionResilienceTests().state(root)
            backup = create_production_backup(
                sources=sources,
                policy=ProductionBackupPolicy(
                    retention_days=30,
                    max_rpo_seconds=300,
                    max_rto_seconds=120,
                ),
                created_at="2026-09-24T12:03:00Z",
                source_checkpoint_at="2026-09-24T12:02:00Z",
                archive_path=root / "private" / "backup.zip",
                manifest_path=root / "private" / "backup.json",
            )
            rehearsal = rehearse_production_restore(
                backup,
                archive_path=root / "private" / "backup.zip",
                restore_dir=root / "restored-after-crash",
                started_at="2026-09-24T12:04:00Z",
                completed_at="2026-09-24T12:04:30Z",
            )
            checks.append(ProductionAcceptanceCheck(
                scenario="RESTORE_AFTER_CRASH",
                passed=True,
                detail="Private production state restored and passed semantic verification.",
                evidence_proof_hash=rehearsal.proof_hash,
            ))

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            execution = run_multicloud_orchestration(
                {
                    "schema": 1,
                    "client_id": "client-multi-exec",
                    "currency": "USD",
                    "jobs": [
                        executable_job(root, "aws", 1000),
                        executable_job(root, "azure", 2000),
                    ],
                },
                base_dir=root,
            )
            self.assertEqual(len(execution.provider_runs), 2)
            self.assertEqual(
                len({run.assurance_report_path for run in execution.provider_runs}),
                2,
            )
            checks.append(ProductionAcceptanceCheck(
                scenario="ISOLATED_MULTI_PROVIDER_JOBS",
                passed=True,
                detail="Two provider jobs completed with distinct state and report planes.",
                evidence_proof_hash=execution.proof_hash,
            ))

        report = build_production_acceptance_report(
            tuple(checks),
            executed_at="2026-09-24T14:00:00Z",
        )
        self.assertEqual(
            report.as_dict()["state"],
            "PRODUCTION_ACCEPTANCE_PASSED",
        )
        self.assertEqual(len(report.checks), 6)
        self.assertFalse(report.external_actions_performed)


if __name__ == "__main__":
    unittest.main()
