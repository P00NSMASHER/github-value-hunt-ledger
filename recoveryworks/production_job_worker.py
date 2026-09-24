"""Local worker execution for approved RecoveryWorks internal jobs.

The worker can execute only local continuous-assurance evaluation, private
backup, and previously authorized cloud diagnostics. It has no provider API,
cloud mutation, claim-submission, or other external-action implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.cloud_diagnostic import run_authorized_cloud_diagnostic
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.production_assurance_continuous import (
    evaluate_continuous_production_assurance,
    write_continuous_production_assurance,
)
from recoveryworks.production_job_control import (
    ProductionJobIdentity,
    ProductionJobLease,
    ProductionJobRegistry,
    ProductionJobType,
)
from recoveryworks.production_resilience import create_production_backup


@dataclass(frozen=True)
class LocalJobExecutionResult:
    job_id: str
    job_proof_hash: str
    lease_proof_hash: str
    job_type: ProductionJobType
    result_proof_hash: str
    completed_at: str
    external_actions_performed: bool = False
    provider_mutation_performed: bool = False

    def __post_init__(self) -> None:
        for name in ("job_proof_hash", "lease_proof_hash", "result_proof_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "completed_at", normalize_utc_timestamp("completed_at", self.completed_at)
        )
        if self.external_actions_performed or self.provider_mutation_performed:
            raise ValueError("local job worker cannot record external actions or mutation")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "job_id": self.job_id,
            "job_proof_hash": self.job_proof_hash,
            "lease_proof_hash": self.lease_proof_hash,
            "job_type": self.job_type.value,
            "result_proof_hash": self.result_proof_hash,
            "completed_at": self.completed_at,
            "external_actions_performed": False,
            "provider_mutation_performed": False,
        })


def _payload_hash(job_type: ProductionJobType, payload: Mapping[str, Any]) -> str:
    proof_inputs = payload.get("proof_inputs")
    if not isinstance(proof_inputs, Mapping):
        raise ValueError("job payload requires proof_inputs object")
    return canonical_hash({
        "schema": 1,
        "job_type": job_type.value,
        "proof_inputs": dict(proof_inputs),
    })


def execute_local_production_job(
    job: ProductionJobIdentity,
    lease: ProductionJobLease,
    registry: ProductionJobRegistry,
    *,
    payload: Mapping[str, Any],
    completed_at: str,
) -> LocalJobExecutionResult:
    if job.job_id != lease.job_id or job.proof_hash != lease.job_proof_hash:
        raise ValueError("worker lease does not bind job")
    if _payload_hash(job.job_type, payload) != job.payload_proof_hash:
        raise ValueError("runtime payload does not match planned job proof")

    if job.job_type is ProductionJobType.CONTINUOUS_ASSURANCE:
        kwargs = payload.get("kwargs")
        output = payload.get("output")
        if not isinstance(kwargs, Mapping) or not isinstance(output, Mapping):
            raise ValueError("assurance job requires kwargs and output mappings")
        result = evaluate_continuous_production_assurance(**dict(kwargs))
        write_continuous_production_assurance(
            result,
            json_path=output["json_path"],
            markdown_path=output["markdown_path"],
        )
        result_proof = result.proof_hash

    elif job.job_type is ProductionJobType.PRIVATE_BACKUP:
        kwargs = payload.get("kwargs")
        if not isinstance(kwargs, Mapping):
            raise ValueError("backup job requires kwargs mapping")
        result = create_production_backup(**dict(kwargs))
        result_proof = result.proof_hash

    elif job.job_type is ProductionJobType.CLOUD_DIAGNOSTIC:
        kwargs = payload.get("kwargs")
        if not isinstance(kwargs, Mapping):
            raise ValueError("diagnostic job requires kwargs mapping")
        result = run_authorized_cloud_diagnostic(**dict(kwargs))
        result_proof = canonical_hash({
            "schema": 1,
            "intake_receipt_proof_hash": result.intake_receipt.proof_hash,
            "pilot_deployment_plan_hash": result.pilot.deployment_plan_hash,
            "pilot_tenant_proof_hash": result.pilot.tenant_proof_hash,
            "pilot_state_head_hash": result.pilot.continuous_result.scan.state_head_hash,
        })
    else:
        raise ValueError("unsupported production job type")

    completed = normalize_utc_timestamp("completed_at", completed_at)
    registry.mark_completed(job, lease, result_proof_hash=result_proof)
    return LocalJobExecutionResult(
        job_id=job.job_id,
        job_proof_hash=job.proof_hash,
        lease_proof_hash=lease.proof_hash,
        job_type=job.job_type,
        result_proof_hash=result_proof,
        completed_at=completed,
        external_actions_performed=False,
        provider_mutation_performed=False,
    )


def heartbeat_local_job(
    registry: ProductionJobRegistry,
    job: ProductionJobIdentity,
    lease: ProductionJobLease,
    *,
    heartbeat_at: str,
    lease_seconds: int = 300,
) -> ProductionJobLease:
    return registry.renew_lease(
        job,
        lease,
        renewed_at=heartbeat_at,
        lease_seconds=lease_seconds,
    )
