"""Internal production service-level controls and admission throttling."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
from typing import Any, Iterable

from recoveryworks.capacity_matrix import (
    ConservativeOperatingEnvelope,
    enforce_operating_envelope,
)
from recoveryworks.models import canonical_hash, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write
from recoveryworks.production_job_control import (
    ProductionJobIdentity,
    ProductionJobRegistry,
)


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


class ServicePressureState(str, Enum):
    HEALTHY = "HEALTHY"
    PRESSURE = "PRESSURE"
    THROTTLED = "THROTTLED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ServiceLevelPolicy:
    max_queue_depth: int = 20
    max_oldest_job_age_seconds: int = 3600
    max_schedule_lateness_seconds: int = 900
    max_missed_jobs: int = 0
    pressure_capacity_bps: int = 8000
    throttle_capacity_bps: int = 9500

    def __post_init__(self) -> None:
        for name in (
            "max_queue_depth","max_oldest_job_age_seconds",
            "max_schedule_lateness_seconds","pressure_capacity_bps",
            "throttle_capacity_bps",
        ):
            value=getattr(self,name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be positive")
        if type(self.max_missed_jobs) is not int or self.max_missed_jobs < 0:
            raise ValueError("max_missed_jobs must be non-negative")
        if not 1 <= self.pressure_capacity_bps < self.throttle_capacity_bps <= 10000:
            raise ValueError("capacity pressure thresholds are invalid")


@dataclass(frozen=True)
class InternalCapacityDemand:
    billing_rows: int
    provider_count: int
    tenant_count: int
    evidence_bytes: int = 1

    def __post_init__(self) -> None:
        for name in ("billing_rows","provider_count","tenant_count","evidence_bytes"):
            if type(getattr(self,name)) is not int or getattr(self,name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class ServiceLevelAlert:
    code: str
    severity: str
    detail: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema":1,**asdict(self)})


@dataclass(frozen=True)
class InternalServiceLevelSnapshot:
    snapshot_id: str
    checked_at: str
    state: ServicePressureState
    queue_depth: int
    oldest_job_age_seconds: int
    schedule_lateness_seconds: int
    missed_job_count: int
    capacity_utilization_bps: int
    capacity_admitted: bool
    alerts: tuple[ServiceLevelAlert,...]
    admission_throttled: bool
    autonomous_external_actions_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,"checked_at",normalize_utc_timestamp("checked_at",self.checked_at)
        )
        if not isinstance(self.state,ServicePressureState):
            raise ValueError("state must be ServicePressureState")
        for name in (
            "queue_depth","oldest_job_age_seconds","schedule_lateness_seconds",
            "missed_job_count","capacity_utilization_bps",
        ):
            value=getattr(self,name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.autonomous_external_actions_enabled:
            raise ValueError("service-level controls cannot enable external actions")
        expected="recoveryworks-service-level:"+canonical_hash(self._identity())
        if self.snapshot_id!=expected:
            raise ValueError("snapshot_id does not bind service-level snapshot")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"checked_at":self.checked_at,"state":self.state.value,
            "queue_depth":self.queue_depth,
            "oldest_job_age_seconds":self.oldest_job_age_seconds,
            "schedule_lateness_seconds":self.schedule_lateness_seconds,
            "missed_job_count":self.missed_job_count,
            "capacity_utilization_bps":self.capacity_utilization_bps,
            "capacity_admitted":self.capacity_admitted,
            "alert_hashes":[a.proof_hash for a in self.alerts],
            "admission_throttled":self.admission_throttled,
            "autonomous_external_actions_enabled":False,
        }
    @property
    def proof_hash(self)->str: return canonical_hash(self._identity())
    def as_dict(self)->dict[str,Any]:
        return {**self._identity(),"snapshot_id":self.snapshot_id,
                "proof_hash":self.proof_hash,
                "report_state":"INTERNAL_SERVICE_LEVEL_SNAPSHOT"}

    def to_markdown(self)->str:
        lines=[
            "# Internal Production Service-Level Snapshot","",
            f"State: {self.state.value}",
            f"Checked at: {self.checked_at}",
            f"Queue depth: {self.queue_depth}",
            f"Oldest job age seconds: {self.oldest_job_age_seconds}",
            f"Schedule lateness seconds: {self.schedule_lateness_seconds}",
            f"Missed job count: {self.missed_job_count}",
            f"Measured capacity utilization bps: {self.capacity_utilization_bps}",
            f"Admission throttled: {str(self.admission_throttled).lower()}","",
            "## Alerts","",
        ]
        if not self.alerts:
            lines.append("- none")
        else:
            for alert in self.alerts:
                lines.append(
                    f"- [{alert.severity}] {alert.code}: {alert.detail}"
                )
        lines.extend([
            "",
            "Internal engineering control only; not a customer SLA.",
            "Autonomous external actions: disabled",
            "",
        ])
        return "\n".join(lines)


def _capacity_utilization_bps(
    envelope: ConservativeOperatingEnvelope,
    demand: InternalCapacityDemand,
) -> int:
    ratios=(
        demand.billing_rows*10000//envelope.max_measured_billing_rows,
        demand.provider_count*10000//envelope.max_measured_provider_count,
        demand.tenant_count*10000//envelope.max_measured_tenant_count,
        demand.evidence_bytes*10000//envelope.max_measured_evidence_bytes,
    )
    return max(ratios)


def evaluate_internal_service_levels(
    *,
    jobs: Iterable[ProductionJobIdentity],
    registry: ProductionJobRegistry,
    envelope: ConservativeOperatingEnvelope,
    demand: InternalCapacityDemand,
    checked_at: str,
    policy: ServiceLevelPolicy = ServiceLevelPolicy(),
) -> InternalServiceLevelSnapshot:
    now=_instant(checked_at)
    rows=registry._read().get("jobs", {})
    backlog=[]
    missed=0
    lateness=0
    for job in jobs:
        row=rows.get(job.job_id)
        completed=row is not None and row.get("completed_result_proof_hash") is not None
        cancelled=row is not None and row.get("cancelled_at") is not None
        if completed or cancelled:
            continue
        backlog.append(job)
        scheduled=_instant(job.scheduled_for)
        late=max(0,int((now-scheduled).total_seconds()))
        lateness=max(lateness,late)
        if late > policy.max_schedule_lateness_seconds:
            missed += 1
    oldest=max(
        (max(0,int((now-_instant(job.scheduled_for)).total_seconds())) for job in backlog),
        default=0,
    )
    capacity_decision=enforce_operating_envelope(
        envelope,billing_rows=demand.billing_rows,
        provider_count=demand.provider_count,tenant_count=demand.tenant_count,
        evidence_bytes=demand.evidence_bytes)
    utilization=_capacity_utilization_bps(envelope,demand)
    alerts=[]
    if len(backlog)>policy.max_queue_depth:
        alerts.append(ServiceLevelAlert("QUEUE_DEPTH","BLOCK",f"queue depth {len(backlog)} exceeds {policy.max_queue_depth}"))
    if oldest>policy.max_oldest_job_age_seconds:
        alerts.append(ServiceLevelAlert("OLDEST_JOB_AGE","BLOCK",f"oldest job age {oldest}s exceeds {policy.max_oldest_job_age_seconds}s"))
    if missed>policy.max_missed_jobs:
        alerts.append(ServiceLevelAlert("MISSED_SCHEDULES","BLOCK",f"{missed} missed schedule(s) exceed {policy.max_missed_jobs}"))
    if not capacity_decision["admitted"]:
        alerts.append(ServiceLevelAlert("CAPACITY_ENVELOPE","BLOCK","requested internal work exceeds measured capacity envelope"))
    elif utilization>=policy.throttle_capacity_bps:
        alerts.append(ServiceLevelAlert("CAPACITY_PRESSURE","WARNING",f"capacity utilization {utilization} bps requires throttling"))
    elif utilization>=policy.pressure_capacity_bps:
        alerts.append(ServiceLevelAlert("CAPACITY_PRESSURE","INFO",f"capacity utilization {utilization} bps is elevated"))

    blocking=any(a.severity=="BLOCK" for a in alerts)
    if blocking:
        state=ServicePressureState.BLOCKED
    elif utilization>=policy.throttle_capacity_bps or len(backlog)>=policy.max_queue_depth:
        state=ServicePressureState.THROTTLED
    elif alerts or utilization>=policy.pressure_capacity_bps:
        state=ServicePressureState.PRESSURE
    else:
        state=ServicePressureState.HEALTHY
    throttled=state in {ServicePressureState.THROTTLED,ServicePressureState.BLOCKED}
    checked=normalize_utc_timestamp("checked_at",checked_at)
    identity={
        "schema":1,"checked_at":checked,"state":state.value,
        "queue_depth":len(backlog),"oldest_job_age_seconds":oldest,
        "schedule_lateness_seconds":lateness,"missed_job_count":missed,
        "capacity_utilization_bps":utilization,
        "capacity_admitted":capacity_decision["admitted"],
        "alert_hashes":[a.proof_hash for a in alerts],
        "admission_throttled":throttled,
        "autonomous_external_actions_enabled":False,
    }
    return InternalServiceLevelSnapshot(
        snapshot_id="recoveryworks-service-level:"+canonical_hash(identity),
        checked_at=checked,state=state,queue_depth=len(backlog),
        oldest_job_age_seconds=oldest,schedule_lateness_seconds=lateness,
        missed_job_count=missed,capacity_utilization_bps=utilization,
        capacity_admitted=capacity_decision["admitted"],alerts=tuple(alerts),
        admission_throttled=throttled,autonomous_external_actions_enabled=False,
    )


def admit_internal_job(
    snapshot: InternalServiceLevelSnapshot,
) -> dict[str,Any]:
    return {
        "admitted":not snapshot.admission_throttled,
        "state":"INTERNAL_JOB_ADMITTED" if not snapshot.admission_throttled
                else "INTERNAL_JOB_ADMISSION_THROTTLED",
        "service_level_proof_hash":snapshot.proof_hash,
        "external_actions_performed":False,
    }


def write_internal_service_level_report(
    snapshot: InternalServiceLevelSnapshot,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                snapshot.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ) + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (snapshot.to_markdown() + "\n").encode("utf-8"),
    )
