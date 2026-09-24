"""One-command simulated operator rehearsal for a RecoveryWorks pilot.

Uses synthetic customer data and local-only execution. No real customer is
contacted/onboarded and no provider/external action is performed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from recoveryworks.cloud_onboarding import (
    materialize_cloud_diagnostic_call,
    validate_cloud_onboarding,
    write_onboarding_outputs,
)
from recoveryworks.models import canonical_hash
from recoveryworks.private_io import atomic_private_write, private_permissions_verified
from recoveryworks.production_job_control import (
    JobScheduleMode,
    ProductionJobRegistry,
    ProductionJobType,
    build_production_job_schedule,
    plan_job_occurrence,
)
from recoveryworks.production_job_worker import execute_local_production_job
from recoveryworks.tenant_isolation import TenantIdentity, TenantBindingRegistry


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class OperatorRehearsalResult:
    rehearsal_id: str
    tenant_id: str
    onboarding_proof_hash: str
    diagnostic_job_proof_hash: str
    diagnostic_result_proof_hash: str
    assurance_report_path: str
    assurance_report_proof_hash: str
    diligence_index_path: str
    runbook_path: str
    checklist_path: str
    customer_contacted: bool = False
    real_customer_onboarded: bool = False
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        if self.customer_contacted or self.real_customer_onboarded or self.external_actions_performed:
            raise ValueError("operator rehearsal must remain simulated and local-only")
        expected="recoveryworks-operator-rehearsal:"+canonical_hash(self._identity())
        if self.rehearsal_id!=expected:
            raise ValueError("rehearsal_id does not bind operator rehearsal")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"tenant_id":self.tenant_id,
            "onboarding_proof_hash":self.onboarding_proof_hash,
            "diagnostic_job_proof_hash":self.diagnostic_job_proof_hash,
            "diagnostic_result_proof_hash":self.diagnostic_result_proof_hash,
            "assurance_report_path":self.assurance_report_path,
            "assurance_report_proof_hash":self.assurance_report_proof_hash,
            "diligence_index_path":self.diligence_index_path,
            "runbook_path":self.runbook_path,"checklist_path":self.checklist_path,
            "customer_contacted":False,"real_customer_onboarded":False,
            "external_actions_performed":False,
        }
    @property
    def proof_hash(self)->str: return canonical_hash(self._identity())
    def as_dict(self)->dict[str,Any]:
        return {**self._identity(),"rehearsal_id":self.rehearsal_id,
                "proof_hash":self.proof_hash,"state":"SIMULATED_OPERATOR_REHEARSAL_PASSED"}


def _fixture_files(root: Path) -> dict[str,str]:
    inputs=root/"inputs"; inputs.mkdir(parents=True,exist_ok=True)
    if os.name!="nt": inputs.chmod(0o700)
    focus=inputs/"focus.csv"; meter=inputs/"meter.csv"; rates=inputs/"rates.csv"
    focus.write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,BilledCost,"
        "BillingCurrency,ResourceId\n"
        "Amazon Web Services,sim-acct,EC2,2026-08-31T00:00:00Z,40.00,USD,i-sim\n",
        encoding="utf-8")
    meter.write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-SIM,10,i-sim,EC2,2026-08-31\n",encoding="utf-8")
    rates.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",encoding="utf-8")
    if os.name!="nt":
        for p in (focus,meter,rates): p.chmod(0o600)
    return {"focus_csv":str(focus),"meter_csv":str(meter),"rates_csv":str(rates)}


def run_simulated_operator_rehearsal(
    root: str | Path,
    *,
    run_at: str = "2026-09-24T14:00:00Z",
) -> OperatorRehearsalResult:
    root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    files=_fixture_files(root)
    tenant=TenantIdentity(
        tenant_id="simulated-client",client_id="simulated-client",
        namespace=str(root),created_at="2026-09-24T13:00:00Z")
    tenant_registry=TenantBindingRegistry(root/".recoveryworks-tenant-bindings.json")
    tenant_registry.reserve_paths(tenant,artifact_paths={"operator_seed":root/"operator-seed.json"})

    spec={
        "schema":2,"onboarding_id":"sim-onboarding","diagnostic_id":"sim-diagnostic",
        "client_id":"simulated-client","provider":"aws","billing_account_id":"sim-acct",
        "currency":"USD",
        "period":{"start":"2026-08-01","end":"2026-08-31"},
        "authorization":{
            "customer_actor_id":"simulated-authorizer",
            "authorized_at":"2026-09-24T12:00:00Z",
            "expires_at":"2026-09-25T12:00:00Z",
            "source_hash":"a"*64,"source_locator":"simulation://authorization",
            "verified":True,
        },
        "evidence_review":{
            "reviewer_id":"simulated-reviewer",
            "reviewed_at":"2026-09-24T12:05:00Z",
            "charge_source_verified":True,
            "meter_source_verified":True,
            "rate_source_verified":True,
        },
        "inputs":files,
        "cletrics":{
            "release":"operator-rehearsal","commit":"b"*40,
            "exported_at":"2026-09-24T13:00:00Z",
        },
        "outputs":{"private_root":str(root/"private"/"diagnostic")},
    }
    readiness=validate_cloud_onboarding(spec,base_dir=root)
    if not readiness.diagnostic_ready:
        raise ValueError("simulated onboarding unexpectedly not ready")
    private=root/"private"; private.mkdir(parents=True,exist_ok=True)
    if os.name!="nt": private.chmod(0o700)
    checklist=private/"onboarding-checklist.json"
    diagnostic_request=private/"diagnostic-request.json"
    write_onboarding_outputs(
        readiness,checklist_path=checklist,diagnostic_request_path=diagnostic_request)
    kwargs=materialize_cloud_diagnostic_call(readiness)
    kwargs["base_dir"]=root
    kwargs["run_at"]=run_at

    proof_inputs={
        "onboarding_proof_hash":readiness.proof_hash,
        "authorization_proof_hash":kwargs["authorization"].proof_hash,
        "evidence_review_proof_hash":kwargs["evidence_review"].proof_hash,
    }
    payload_hash=canonical_hash({
        "schema":1,"job_type":"CLOUD_DIAGNOSTIC","proof_inputs":proof_inputs})
    schedule=build_production_job_schedule(
        tenant,job_type=ProductionJobType.CLOUD_DIAGNOSTIC,
        payload_proof_hash=payload_hash,mode=JobScheduleMode.ONE_TIME,
        starts_at=run_at)
    job=plan_job_occurrence(schedule)
    registry=ProductionJobRegistry(private/"jobs.json")
    lease=registry.acquire(job,worker_id="operator-rehearsal-worker",acquired_at=run_at)
    execution=execute_local_production_job(
        job,lease,registry,payload={"proof_inputs":proof_inputs,"kwargs":kwargs},
        completed_at=run_at)

    assurance_path=root/"private"/"diagnostic"/"cloud-assurance.json"
    payload=json.loads(assurance_path.read_text(encoding="utf-8"))
    assurance_proof=payload["proof_hash"]
    diligence_path=private/"buyer-diligence-index.json"
    diligence={
        "schema":1,"simulation_only":True,"tenant_id":tenant.tenant_id,
        "onboarding_proof_hash":readiness.proof_hash,
        "diagnostic_job_proof_hash":job.proof_hash,
        "diagnostic_result_proof_hash":execution.result_proof_hash,
        "assurance_report_proof_hash":assurance_proof,
        "certification_claims":[],
        "customer_contacted":False,"real_customer_onboarded":False,
        "external_actions_performed":False,
    }
    diligence["proof_hash"]=canonical_hash(diligence)
    atomic_private_write(
        diligence_path,(json.dumps(diligence,sort_keys=True,separators=(",",":"))+"\n").encode())

    runbook_path=private/"operator-runbook.md"
    runbook=(
        "# RecoveryWorks Simulated Operator Runbook\n\n"
        "1. Create isolated tenant workspace.\n"
        "2. Validate authorized billing/meter/rate intake.\n"
        "3. Confirm processing authorization is separate from evidence verification.\n"
        "4. Schedule tenant-bound CLOUD_DIAGNOSTIC job.\n"
        "5. Acquire local worker lease and execute diagnostic.\n"
        "6. Verify private Cloud Assurance report and proof hash.\n"
        "7. Review read-only findings before any later authorization.\n"
        "8. Generate customer-safe diligence index.\n"
        "9. Confirm no customer contact, provider mutation, claim submission, or external action occurred.\n"
    )
    atomic_private_write(runbook_path,runbook.encode())
    for p in (checklist,diagnostic_request,assurance_path,diligence_path,runbook_path):
        if not private_permissions_verified(p):
            raise PermissionError(f"operator rehearsal output is not private: {p}")

    identity={
        "schema":1,"tenant_id":tenant.tenant_id,
        "onboarding_proof_hash":readiness.proof_hash,
        "diagnostic_job_proof_hash":job.proof_hash,
        "diagnostic_result_proof_hash":execution.result_proof_hash,
        "assurance_report_path":str(assurance_path),
        "assurance_report_proof_hash":assurance_proof,
        "diligence_index_path":str(diligence_path),
        "runbook_path":str(runbook_path),"checklist_path":str(checklist),
        "customer_contacted":False,"real_customer_onboarded":False,
        "external_actions_performed":False,
    }
    return OperatorRehearsalResult(
        rehearsal_id="recoveryworks-operator-rehearsal:"+canonical_hash(identity),
        tenant_id=tenant.tenant_id,onboarding_proof_hash=readiness.proof_hash,
        diagnostic_job_proof_hash=job.proof_hash,
        diagnostic_result_proof_hash=execution.result_proof_hash,
        assurance_report_path=str(assurance_path),
        assurance_report_proof_hash=assurance_proof,
        diligence_index_path=str(diligence_path),runbook_path=str(runbook_path),
        checklist_path=str(checklist),customer_contacted=False,
        real_customer_onboarded=False,external_actions_performed=False,
    )
