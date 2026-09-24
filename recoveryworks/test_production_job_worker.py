from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.models import canonical_hash
from recoveryworks.production_job_control import (
    JobScheduleMode,
    ProductionJobRegistry,
    ProductionJobType,
    build_production_job_schedule,
    plan_job_occurrence,
)
from recoveryworks.production_job_worker import (
    execute_local_production_job,
    heartbeat_local_job,
)
from recoveryworks.production_resilience import ProductionBackupPolicy
from recoveryworks.tenant_isolation import TenantIdentity
from recoveryworks.test_production_resilience import ProductionResilienceTests


class ProductionJobWorkerTests(unittest.TestCase):
    def test_backup_job_executes_locally_with_heartbeat_and_idempotent_completion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            sources=ProductionResilienceTests().state(root)
            tenant=TenantIdentity(
                tenant_id="client-dr",client_id="client-dr",
                namespace=str(root),created_at="2026-09-24T12:00:00Z")
            kwargs={
                "sources":sources,
                "policy":ProductionBackupPolicy(
                    retention_days=30,max_rpo_seconds=300,max_rto_seconds=120),
                "created_at":"2026-09-24T12:03:00Z",
                "source_checkpoint_at":"2026-09-24T12:02:00Z",
                "archive_path":root/"private"/"worker-backup.zip",
                "manifest_path":root/"private"/"worker-backup.json",
            }
            proof_inputs={
                "source_paths":sorted(str(Path(v).resolve()) for v in sources.values()),
                "created_at":kwargs["created_at"],
                "source_checkpoint_at":kwargs["source_checkpoint_at"],
            }
            payload={"proof_inputs":proof_inputs,"kwargs":kwargs}
            payload_hash=canonical_hash({
                "schema":1,"job_type":"PRIVATE_BACKUP",
                "proof_inputs":proof_inputs})
            schedule=build_production_job_schedule(
                tenant,job_type=ProductionJobType.PRIVATE_BACKUP,
                payload_proof_hash=payload_hash,mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T12:03:00Z")
            job=plan_job_occurrence(schedule)
            registry=ProductionJobRegistry(root/"private"/"jobs.json")
            lease=registry.acquire(
                job,worker_id="worker-a",
                acquired_at="2026-09-24T12:03:00Z",lease_seconds=120)
            renewed=heartbeat_local_job(
                registry,job,lease,heartbeat_at="2026-09-24T12:03:30Z",
                lease_seconds=120)
            result=execute_local_production_job(
                job,renewed,registry,payload=payload,
                completed_at="2026-09-24T12:04:00Z")
            self.assertFalse(result.external_actions_performed)
            self.assertFalse(result.provider_mutation_performed)
            self.assertEqual(registry.completed_result(job),result.result_proof_hash)

    def test_cancellation_failure_receipt_and_restart_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            tenant=TenantIdentity(
                tenant_id="tenant",client_id="client",namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            payload_hash=canonical_hash({
                "schema":1,"job_type":"CONTINUOUS_ASSURANCE",
                "proof_inputs":{"x":"1"}})
            schedule=build_production_job_schedule(
                tenant,job_type=ProductionJobType.CONTINUOUS_ASSURANCE,
                payload_proof_hash=payload_hash,mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z")
            job=plan_job_occurrence(schedule)
            registry=ProductionJobRegistry(root/"jobs.json")
            lease=registry.acquire(
                job,worker_id="worker-a",
                acquired_at="2026-09-24T13:00:00Z",lease_seconds=60)
            failure=registry.record_failure(
                job,lease,failure_code="TEMPORARY_IO_FAILURE",
                detail="simulated local write failure",
                failed_at="2026-09-24T13:00:30Z")
            self.assertEqual(len(failure),64)
            # The failure clears the lease; an expired/interrupted job may be
            # reacquired on restart as a later attempt.
            next_lease=registry.acquire(
                job,worker_id="worker-b",
                acquired_at="2026-09-24T13:02:00Z",lease_seconds=60)
            self.assertEqual(next_lease.attempt,2)
            registry.cancel(
                job,cancelled_at="2026-09-24T13:02:30Z",
                cancelled_by="operator",reason="stop retry")
            with self.assertRaisesRegex(ValueError,"cancelled"):
                registry.acquire(
                    job,worker_id="worker-c",
                    acquired_at="2026-09-24T13:04:00Z")

    def test_payload_proof_mismatch_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            tenant=TenantIdentity(
                tenant_id="tenant",client_id="client",namespace=str(root),
                created_at="2026-09-24T12:00:00Z")
            schedule=build_production_job_schedule(
                tenant,job_type=ProductionJobType.PRIVATE_BACKUP,
                payload_proof_hash="1"*64,mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z")
            job=plan_job_occurrence(schedule)
            registry=ProductionJobRegistry(root/"jobs.json")
            lease=registry.acquire(
                job,worker_id="worker",acquired_at="2026-09-24T13:00:00Z")
            with self.assertRaisesRegex(ValueError,"payload does not match"):
                execute_local_production_job(
                    job,lease,registry,
                    payload={"proof_inputs":{"wrong":True},"kwargs":{}},
                    completed_at="2026-09-24T13:01:00Z")


if __name__=="__main__":
    unittest.main()
