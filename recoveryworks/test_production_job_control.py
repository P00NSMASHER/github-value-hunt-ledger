from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.production_job_control import (
    JobScheduleMode,
    ProductionJobRegistry,
    ProductionJobType,
    ProductionRetryPolicy,
    build_production_job_schedule,
    decide_job_retry,
    plan_job_occurrence,
)
from recoveryworks.tenant_isolation import TenantIdentity


class ProductionJobControlTests(unittest.TestCase):
    def tenant(self, root: Path):
        return TenantIdentity(
            tenant_id="tenant-1",client_id="client-1",namespace=str(root),
            created_at="2026-09-24T12:00:00Z")

    def test_deterministic_assurance_backup_diagnostic_schedule_plans(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); tenant=self.tenant(root)
            schedules=(
                build_production_job_schedule(
                    tenant,job_type=ProductionJobType.CONTINUOUS_ASSURANCE,
                    payload_proof_hash="1"*64,mode=JobScheduleMode.FIXED_INTERVAL,
                    starts_at="2026-09-24T13:00:00Z",interval_seconds=3600),
                build_production_job_schedule(
                    tenant,job_type=ProductionJobType.PRIVATE_BACKUP,
                    payload_proof_hash="2"*64,mode=JobScheduleMode.FIXED_INTERVAL,
                    starts_at="2026-09-24T14:00:00Z",interval_seconds=86400),
                build_production_job_schedule(
                    tenant,job_type=ProductionJobType.CLOUD_DIAGNOSTIC,
                    payload_proof_hash="3"*64,mode=JobScheduleMode.ONE_TIME,
                    starts_at="2026-09-25T12:00:00Z"),
            )
            for schedule in schedules:
                self.assertFalse(schedule.execution_enabled)
                self.assertFalse(schedule.external_actions_enabled)
                self.assertEqual(schedule.as_dict()["state"],"DRY_RUN_SCHEDULE_READY")
            first=plan_job_occurrence(schedules[0],occurrence_index=0)
            second=plan_job_occurrence(schedules[0],occurrence_index=1)
            self.assertNotEqual(first.job_id,second.job_id)
            self.assertEqual(second.scheduled_for,"2026-09-24T14:00:00Z")

    def test_lease_prevents_concurrent_worker_and_job_completion_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); tenant=self.tenant(root)
            schedule=build_production_job_schedule(
                tenant,job_type=ProductionJobType.CONTINUOUS_ASSURANCE,
                payload_proof_hash="1"*64,mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z")
            job=plan_job_occurrence(schedule)
            registry=ProductionJobRegistry(root/"private"/"jobs.json")
            lease=registry.acquire(
                job,worker_id="worker-a",
                acquired_at="2026-09-24T13:00:00Z",lease_seconds=300)
            with self.assertRaisesRegex(ValueError,"active lease"):
                registry.acquire(
                    job,worker_id="worker-b",
                    acquired_at="2026-09-24T13:01:00Z",lease_seconds=300)
            registry.mark_completed(job,lease,result_proof_hash="9"*64)
            self.assertEqual(registry.completed_result(job),"9"*64)
            registry.mark_completed(job,lease,result_proof_hash="9"*64)
            with self.assertRaisesRegex(ValueError,"already completed"):
                registry.acquire(
                    job,worker_id="worker-c",
                    acquired_at="2026-09-24T14:00:00Z")

    def test_expired_lease_allows_retry_attempt_and_retry_policy_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); tenant=self.tenant(root)
            policy=ProductionRetryPolicy(
                max_attempts=3,initial_backoff_seconds=60,
                multiplier=2,max_backoff_seconds=300)
            schedule=build_production_job_schedule(
                tenant,job_type=ProductionJobType.CLOUD_DIAGNOSTIC,
                payload_proof_hash="1"*64,mode=JobScheduleMode.ONE_TIME,
                starts_at="2026-09-24T13:00:00Z",retry_policy=policy)
            job=plan_job_occurrence(schedule)
            registry=ProductionJobRegistry(root/"jobs.json")
            first=registry.acquire(
                job,worker_id="worker-a",
                acquired_at="2026-09-24T13:00:00Z",lease_seconds=60)
            second=registry.acquire(
                job,worker_id="worker-b",
                acquired_at="2026-09-24T13:02:00Z",lease_seconds=60)
            self.assertEqual(first.attempt,1)
            self.assertEqual(second.attempt,2)
            decision=decide_job_retry(
                attempt=2,failure_code="RATE_LIMITED",
                failed_at="2026-09-24T13:02:30Z",policy=policy)
            self.assertTrue(decision.retry)
            self.assertEqual(decision.next_not_before,"2026-09-24T13:04:30Z")
            stop=decide_job_retry(
                attempt=3,failure_code="RATE_LIMITED",
                failed_at="2026-09-24T13:05:00Z",policy=policy)
            self.assertFalse(stop.retry)

    def test_non_retryable_failure_stops(self):
        decision=decide_job_retry(
            attempt=1,failure_code="AUTHORIZATION_FAILED",
            failed_at="2026-09-24T13:00:00Z",
            policy=ProductionRetryPolicy())
        self.assertFalse(decision.retry)
        self.assertIsNone(decision.next_not_before)


if __name__=="__main__":
    unittest.main()
