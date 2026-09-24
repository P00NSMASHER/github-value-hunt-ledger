"""Idempotent production job identities, leases, retries, and dry-run schedules.

This module plans/coordinates internal jobs only. It does not run provider APIs,
perform external actions, or install a scheduler daemon.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write, private_file_lock
from recoveryworks.provider_connectors import ProviderConnectorErrorCode
from recoveryworks.tenant_isolation import TenantIdentity


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


class ProductionJobType(str, Enum):
    CONTINUOUS_ASSURANCE = "CONTINUOUS_ASSURANCE"
    PRIVATE_BACKUP = "PRIVATE_BACKUP"
    CLOUD_DIAGNOSTIC = "CLOUD_DIAGNOSTIC"


class JobScheduleMode(str, Enum):
    ONE_TIME = "ONE_TIME"
    FIXED_INTERVAL = "FIXED_INTERVAL"


@dataclass(frozen=True)
class ProductionRetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: int = 60
    multiplier: int = 2
    max_backoff_seconds: int = 900

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be in 1..10")
        for name in (
            "initial_backoff_seconds", "multiplier", "max_backoff_seconds"
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds cannot be below initial backoff")

    def backoff_seconds(self, attempt: int) -> int:
        if type(attempt) is not int or attempt < 1:
            raise ValueError("attempt must be positive")
        raw = self.initial_backoff_seconds * (self.multiplier ** (attempt - 1))
        return min(raw, self.max_backoff_seconds)


@dataclass(frozen=True)
class ProductionJobSchedule:
    schedule_id: str
    tenant_id: str
    tenant_proof_hash: str
    job_type: ProductionJobType
    payload_proof_hash: str
    mode: JobScheduleMode
    starts_at: str
    interval_seconds: int | None
    retry_policy: ProductionRetryPolicy
    execution_enabled: bool = False
    external_actions_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _text("tenant_id", self.tenant_id))
        for name in ("tenant_proof_hash", "payload_proof_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        if not isinstance(self.job_type, ProductionJobType):
            raise ValueError("job_type must be ProductionJobType")
        if not isinstance(self.mode, JobScheduleMode):
            raise ValueError("mode must be JobScheduleMode")
        object.__setattr__(
            self, "starts_at", normalize_utc_timestamp("starts_at", self.starts_at)
        )
        if self.mode is JobScheduleMode.ONE_TIME:
            if self.interval_seconds is not None:
                raise ValueError("one-time schedules cannot have interval_seconds")
        else:
            if (
                type(self.interval_seconds) is not int
                or self.interval_seconds < 3600
            ):
                raise ValueError("fixed interval must be at least one hour")
        if self.execution_enabled or self.external_actions_enabled:
            raise ValueError("step 27a schedules must remain dry-run/internal-only")
        expected = "production-job-schedule:" + canonical_hash(self._identity())
        if self.schedule_id != expected:
            raise ValueError("schedule_id does not bind job schedule")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "tenant_id": self.tenant_id,
            "tenant_proof_hash": self.tenant_proof_hash,
            "job_type": self.job_type.value,
            "payload_proof_hash": self.payload_proof_hash,
            "mode": self.mode.value,
            "starts_at": self.starts_at,
            "interval_seconds": self.interval_seconds,
            "retry_policy": asdict(self.retry_policy),
            "execution_enabled": False,
            "external_actions_enabled": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "schedule_id": self.schedule_id,
            "proof_hash": self.proof_hash,
            "state": "DRY_RUN_SCHEDULE_READY",
        }


def build_production_job_schedule(
    tenant: TenantIdentity,
    *,
    job_type: ProductionJobType,
    payload_proof_hash: str,
    mode: JobScheduleMode,
    starts_at: str,
    interval_seconds: int | None = None,
    retry_policy: ProductionRetryPolicy = ProductionRetryPolicy(),
) -> ProductionJobSchedule:
    starts = normalize_utc_timestamp("starts_at", starts_at)
    payload = normalize_sha256("payload_proof_hash", payload_proof_hash)
    identity = {
        "schema": 1,
        "tenant_id": tenant.tenant_id,
        "tenant_proof_hash": tenant.proof_hash,
        "job_type": job_type.value,
        "payload_proof_hash": payload,
        "mode": mode.value,
        "starts_at": starts,
        "interval_seconds": interval_seconds,
        "retry_policy": asdict(retry_policy),
        "execution_enabled": False,
        "external_actions_enabled": False,
    }
    return ProductionJobSchedule(
        schedule_id="production-job-schedule:" + canonical_hash(identity),
        tenant_id=tenant.tenant_id,
        tenant_proof_hash=tenant.proof_hash,
        job_type=job_type,
        payload_proof_hash=payload,
        mode=mode,
        starts_at=starts,
        interval_seconds=interval_seconds,
        retry_policy=retry_policy,
        execution_enabled=False,
        external_actions_enabled=False,
    )


@dataclass(frozen=True)
class ProductionJobIdentity:
    job_id: str
    schedule_id: str
    schedule_proof_hash: str
    tenant_id: str
    tenant_proof_hash: str
    job_type: ProductionJobType
    payload_proof_hash: str
    scheduled_for: str

    def __post_init__(self) -> None:
        for name in (
            "schedule_proof_hash", "tenant_proof_hash", "payload_proof_hash"
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "scheduled_for",
            normalize_utc_timestamp("scheduled_for", self.scheduled_for)
        )
        expected = "production-job:" + canonical_hash(self._identity())
        if self.job_id != expected:
            raise ValueError("job_id does not bind production job identity")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "schedule_id": self.schedule_id,
            "schedule_proof_hash": self.schedule_proof_hash,
            "tenant_id": self.tenant_id,
            "tenant_proof_hash": self.tenant_proof_hash,
            "job_type": self.job_type.value,
            "payload_proof_hash": self.payload_proof_hash,
            "scheduled_for": self.scheduled_for,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def plan_job_occurrence(
    schedule: ProductionJobSchedule,
    *,
    occurrence_index: int = 0,
) -> ProductionJobIdentity:
    if type(occurrence_index) is not int or occurrence_index < 0:
        raise ValueError("occurrence_index must be non-negative")
    if schedule.mode is JobScheduleMode.ONE_TIME and occurrence_index != 0:
        raise ValueError("one-time schedule has only occurrence 0")
    offset = 0 if schedule.interval_seconds is None else (
        schedule.interval_seconds * occurrence_index
    )
    scheduled = (
        _instant(schedule.starts_at) + timedelta(seconds=offset)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identity = {
        "schema": 1,
        "schedule_id": schedule.schedule_id,
        "schedule_proof_hash": schedule.proof_hash,
        "tenant_id": schedule.tenant_id,
        "tenant_proof_hash": schedule.tenant_proof_hash,
        "job_type": schedule.job_type.value,
        "payload_proof_hash": schedule.payload_proof_hash,
        "scheduled_for": scheduled,
    }
    return ProductionJobIdentity(
        job_id="production-job:" + canonical_hash(identity),
        schedule_id=schedule.schedule_id,
        schedule_proof_hash=schedule.proof_hash,
        tenant_id=schedule.tenant_id,
        tenant_proof_hash=schedule.tenant_proof_hash,
        job_type=schedule.job_type,
        payload_proof_hash=schedule.payload_proof_hash,
        scheduled_for=scheduled,
    )


@dataclass(frozen=True)
class ProductionJobLease:
    lease_id: str
    job_id: str
    job_proof_hash: str
    tenant_id: str
    worker_id: str
    attempt: int
    acquired_at: str
    expires_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_proof_hash", normalize_sha256(
            "job_proof_hash", self.job_proof_hash
        ))
        for name in ("job_id", "tenant_id", "worker_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if type(self.attempt) is not int or self.attempt < 1:
            raise ValueError("attempt must be positive")
        object.__setattr__(
            self, "acquired_at", normalize_utc_timestamp("acquired_at", self.acquired_at)
        )
        object.__setattr__(
            self, "expires_at", normalize_utc_timestamp("expires_at", self.expires_at)
        )
        if _instant(self.expires_at) <= _instant(self.acquired_at):
            raise ValueError("lease must expire after acquisition")
        expected = "production-job-lease:" + canonical_hash(self._identity())
        if self.lease_id != expected:
            raise ValueError("lease_id does not bind job lease")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "job_id": self.job_id,
            "job_proof_hash": self.job_proof_hash,
            "tenant_id": self.tenant_id,
            "worker_id": self.worker_id,
            "attempt": self.attempt,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


class ProductionJobRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name("." + self.path.name + ".lock")

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": 1, "jobs": {}}
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema") != 1:
            raise ValueError("unsupported production job registry schema")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("production job registry payload missing")
        if envelope.get("state_hash") != canonical_hash(payload):
            raise ValueError("production job registry state hash mismatch")
        return payload

    def _write(self, payload: Mapping[str, Any]) -> None:
        atomic_private_write(
            self.path,
            (
                json.dumps(
                    {"schema": 1, "payload": payload, "state_hash": canonical_hash(payload)},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ) + "\n"
            ).encode("utf-8"),
        )

    def acquire(
        self,
        job: ProductionJobIdentity,
        *,
        worker_id: str,
        acquired_at: str,
        lease_seconds: int = 300,
    ) -> ProductionJobLease:
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be in 1..3600")
        acquired = normalize_utc_timestamp("acquired_at", acquired_at)
        expires = (
            _instant(acquired) + timedelta(seconds=lease_seconds)
        ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with private_file_lock(self.lock_path):
            payload = self._read()
            jobs = payload.setdefault("jobs", {})
            row = jobs.get(job.job_id)
            if row is not None:
                if row.get("completed_result_proof_hash") is not None:
                    raise ValueError("job is already completed")
                active_expiry = row.get("lease_expires_at")
                if active_expiry and _instant(active_expiry) > _instant(acquired):
                    raise ValueError("job already has an active lease")
                attempt = int(row.get("attempt", 0)) + 1
            else:
                attempt = 1
            identity = {
                "schema": 1,
                "job_id": job.job_id,
                "job_proof_hash": job.proof_hash,
                "tenant_id": job.tenant_id,
                "worker_id": _text("worker_id", worker_id),
                "attempt": attempt,
                "acquired_at": acquired,
                "expires_at": expires,
            }
            lease = ProductionJobLease(
                lease_id="production-job-lease:" + canonical_hash(identity),
                job_id=job.job_id,
                job_proof_hash=job.proof_hash,
                tenant_id=job.tenant_id,
                worker_id=worker_id,
                attempt=attempt,
                acquired_at=acquired,
                expires_at=expires,
            )
            jobs[job.job_id] = {
                "tenant_id": job.tenant_id,
                "job_proof_hash": job.proof_hash,
                "attempt": attempt,
                "lease_id": lease.lease_id,
                "lease_proof_hash": lease.proof_hash,
                "lease_worker_id": lease.worker_id,
                "lease_expires_at": lease.expires_at,
                "completed_result_proof_hash": None,
            }
            self._write(payload)
            return lease

    def mark_completed(
        self,
        job: ProductionJobIdentity,
        lease: ProductionJobLease,
        *,
        result_proof_hash: str,
    ) -> None:
        result = normalize_sha256("result_proof_hash", result_proof_hash)
        with private_file_lock(self.lock_path):
            payload = self._read()
            row = payload.setdefault("jobs", {}).get(job.job_id)
            if row is None:
                raise ValueError("job is not registered")
            if row.get("lease_proof_hash") != lease.proof_hash:
                raise ValueError("completion lease does not match active lease")
            if row.get("completed_result_proof_hash") is not None:
                if row["completed_result_proof_hash"] != result:
                    raise ValueError("job already completed with different result")
                return
            row["completed_result_proof_hash"] = result
            row["lease_expires_at"] = None
            self._write(payload)

    def completed_result(self, job: ProductionJobIdentity) -> str | None:
        row = self._read().get("jobs", {}).get(job.job_id)
        return None if row is None else row.get("completed_result_proof_hash")


@dataclass(frozen=True)
class ProductionRetryDecision:
    retry: bool
    next_not_before: str | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_RETRYABLE = {
    ProviderConnectorErrorCode.RATE_LIMITED.value,
    ProviderConnectorErrorCode.TIMEOUT.value,
    ProviderConnectorErrorCode.TRANSIENT_PROVIDER_ERROR.value,
    "STATE_CONFLICT",
    "TEMPORARY_IO_FAILURE",
}


def decide_job_retry(
    *,
    attempt: int,
    failure_code: str,
    failed_at: str,
    policy: ProductionRetryPolicy,
) -> ProductionRetryDecision:
    if attempt >= policy.max_attempts:
        return ProductionRetryDecision(
            retry=False, next_not_before=None, reason="maximum attempts reached"
        )
    if failure_code not in _RETRYABLE:
        return ProductionRetryDecision(
            retry=False, next_not_before=None, reason="failure is not retryable"
        )
    delay = policy.backoff_seconds(attempt)
    next_time = (
        _instant(failed_at) + timedelta(seconds=delay)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return ProductionRetryDecision(
        retry=True,
        next_not_before=next_time,
        reason=f"retryable failure; backoff {delay}s",
    )
