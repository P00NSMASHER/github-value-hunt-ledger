from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from recoveryworks.capacity_matrix import (
    CapacityDimension, build_conservative_operating_envelope, measured_capacity_cell)
from recoveryworks.production_job_control import (
    JobScheduleMode, ProductionJobRegistry, ProductionJobType,
    build_production_job_schedule, plan_job_occurrence)
from recoveryworks.production_service_levels import (
    InternalCapacityDemand, ServiceLevelPolicy, ServicePressureState,
    admit_internal_job, evaluate_internal_service_levels)
from recoveryworks.tenant_isolation import TenantIdentity
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.production_service_levels import write_internal_service_level_report

def envelope():
    cells=(
        measured_capacity_cell(dimension=CapacityDimension.BILLING_ROWS,billing_rows=1000,provider_count=1,tenant_count=1,bundle_bytes=1,runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1,evidence_proof_hashes=("1"*64,)),
        measured_capacity_cell(dimension=CapacityDimension.PROVIDERS,billing_rows=100,provider_count=3,tenant_count=1,bundle_bytes=1,runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1,evidence_proof_hashes=("2"*64,)),
        measured_capacity_cell(dimension=CapacityDimension.TENANTS,billing_rows=100,provider_count=1,tenant_count=10,bundle_bytes=1,runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1,evidence_proof_hashes=("3"*64,)),
        measured_capacity_cell(dimension=CapacityDimension.EVIDENCE_BYTES,billing_rows=100,provider_count=1,tenant_count=1,bundle_bytes=1000,evidence_bytes=1000,runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1,evidence_proof_hashes=("4"*64,)),
    )
    return build_conservative_operating_envelope(cells)

class ServiceLevelTests(unittest.TestCase):
    def jobs(self,root):
        tenant=TenantIdentity(tenant_id="t",client_id="c",namespace=str(root),created_at="2026-09-24T12:00:00Z")
        schedule=build_production_job_schedule(
            tenant,job_type=ProductionJobType.CONTINUOUS_ASSURANCE,
            payload_proof_hash="4"*64,mode=JobScheduleMode.FIXED_INTERVAL,
            starts_at="2026-09-24T12:00:00Z",interval_seconds=3600)
        return [plan_job_occurrence(schedule,occurrence_index=i) for i in range(3)]

    def test_healthy_service_admits_internal_job(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); jobs=self.jobs(root); reg=ProductionJobRegistry(root/"jobs.json")
            # Complete first two, leave future third queued.
            for i in (0,1):
                lease=reg.acquire(jobs[i],worker_id="w",acquired_at=jobs[i].scheduled_for)
                reg.mark_completed(jobs[i],lease,result_proof_hash=str(i+5)*64)
            snap=evaluate_internal_service_levels(
                jobs=jobs,registry=reg,envelope=envelope(),
                demand=InternalCapacityDemand(100,1,1),
                checked_at="2026-09-24T13:30:00Z")
            self.assertIs(snap.state,ServicePressureState.HEALTHY)
            self.assertTrue(admit_internal_job(snap)["admitted"])

    def test_missed_schedule_blocks_and_capacity_can_throttle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); jobs=self.jobs(root); reg=ProductionJobRegistry(root/"jobs.json")
            snap=evaluate_internal_service_levels(
                jobs=jobs,registry=reg,envelope=envelope(),
                demand=InternalCapacityDemand(100,1,1),
                checked_at="2026-09-24T15:00:00Z",
                policy=ServiceLevelPolicy(max_queue_depth=10,max_oldest_job_age_seconds=20000,
                    max_schedule_lateness_seconds=300,max_missed_jobs=0,
                    pressure_capacity_bps=8000,throttle_capacity_bps=9500))
            self.assertIs(snap.state,ServicePressureState.BLOCKED)
            self.assertFalse(admit_internal_job(snap)["admitted"])

            pressure=evaluate_internal_service_levels(
                jobs=(),registry=reg,envelope=envelope(),
                demand=InternalCapacityDemand(960,1,1),
                checked_at="2026-09-24T13:00:00Z")
            self.assertIs(pressure.state,ServicePressureState.THROTTLED)
            self.assertTrue(pressure.admission_throttled)


    def test_internal_slo_report_is_private_and_not_external_sla(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); reg=ProductionJobRegistry(root/"jobs.json")
            snap=evaluate_internal_service_levels(
                jobs=(),registry=reg,envelope=envelope(),
                demand=InternalCapacityDemand(100,1,1,100),
                checked_at="2026-09-24T13:00:00Z")
            json_path=root/"private"/"slo.json"
            md_path=root/"private"/"slo.md"
            write_internal_service_level_report(
                snap,json_path=json_path,markdown_path=md_path)
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(md_path))
            self.assertIn(
                "not a customer SLA",
                md_path.read_text(encoding="utf-8"))

    def test_over_capacity_blocks_before_work(self):
        with tempfile.TemporaryDirectory() as d:
            reg=ProductionJobRegistry(Path(d)/"jobs.json")
            snap=evaluate_internal_service_levels(
                jobs=(),registry=reg,envelope=envelope(),
                demand=InternalCapacityDemand(1001,1,1),
                checked_at="2026-09-24T13:00:00Z")
            self.assertIs(snap.state,ServicePressureState.BLOCKED)
            self.assertFalse(snap.capacity_admitted)

if __name__=="__main__":
    unittest.main()
