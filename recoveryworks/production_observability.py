"""Structured production observability and tamper-evident run history."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_runner import PilotRunResult
from recoveryworks.private_io import atomic_private_write, private_file_lock


class ProductionRunStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class ProductionFailureCode(str, Enum):
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"
    AUTHORIZATION_INVALID = "AUTHORIZATION_INVALID"
    EVIDENCE_INTEGRITY = "EVIDENCE_INTEGRITY"
    PROVIDER_SCOPE_MISMATCH = "PROVIDER_SCOPE_MISMATCH"
    SUPERSESSION_REQUIRED = "SUPERSESSION_REQUIRED"
    STATE_CONFLICT = "STATE_CONFLICT"
    OUTPUT_INTEGRITY = "OUTPUT_INTEGRITY"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class ProductionRunEvent:
    sequence: int
    run_id: str
    occurred_at: str
    phase: str
    status: str
    provider: str
    deployment_id: str
    payload: Mapping[str, Any]
    previous_hash: str | None
    event_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        run_id: str,
        occurred_at: str,
        phase: str,
        status: str,
        provider: str,
        deployment_id: str,
        payload: Mapping[str, Any],
        previous_hash: str | None,
    ) -> "ProductionRunEvent":
        if type(sequence) is not int or sequence < 1:
            raise ValueError("event sequence must be positive")
        body = {
            "schema": 1,
            "sequence": sequence,
            "run_id": _text("run_id", run_id),
            "occurred_at": normalize_utc_timestamp("occurred_at", occurred_at),
            "phase": _text("phase", phase),
            "status": _text("status", status),
            "provider": _text("provider", provider).lower(),
            "deployment_id": _text("deployment_id", deployment_id),
            "payload": freeze_json(payload, name="event payload"),
            "previous_hash": previous_hash,
        }
        return cls(**body | {"event_hash": canonical_hash(body)})

    def verify(self, previous_hash: str | None) -> None:
        if self.previous_hash != previous_hash:
            raise ValueError("production event previous_hash mismatch")
        rebuilt = ProductionRunEvent.build(
            sequence=self.sequence,
            run_id=self.run_id,
            occurred_at=self.occurred_at,
            phase=self.phase,
            status=self.status,
            provider=self.provider,
            deployment_id=self.deployment_id,
            payload=self.payload,
            previous_hash=self.previous_hash,
        )
        if rebuilt.event_hash != self.event_hash:
            raise ValueError("production event hash mismatch")


@dataclass(frozen=True)
class ProductionMetricsSnapshot:
    run_id: str
    provider: str
    client_id: str
    recovery: Mapping[str, int]
    savings: Mapping[str, int]
    diagnostics: Mapping[str, int]
    job_health: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _text("run_id", self.run_id))
        object.__setattr__(self, "provider", _text("provider", self.provider).lower())
        object.__setattr__(self, "client_id", _text("client_id", self.client_id))
        for field_name in ("recovery", "savings", "diagnostics"):
            raw = getattr(self, field_name)
            normalized: dict[str, int] = {}
            for key, value in raw.items():
                if type(value) is not int or value < 0:
                    raise ValueError(f"{field_name}.{key} must be non-negative integer")
                normalized[str(key)] = value
            object.__setattr__(
                self, field_name, freeze_json(normalized, name=field_name)
            )
        object.__setattr__(
            self,
            "job_health",
            freeze_json(self.job_health, name="job_health"),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "run_id": self.run_id,
            "provider": self.provider,
            "client_id": self.client_id,
            "recovery": dict(self.recovery),
            "savings": dict(self.savings),
            "diagnostics": dict(self.diagnostics),
            "job_health": dict(self.job_health),
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider": self.provider,
            "client_id": self.client_id,
            "recovery": dict(self.recovery),
            "savings": dict(self.savings),
            "diagnostics": dict(self.diagnostics),
            "job_health": dict(self.job_health),
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class ProductionAlert:
    alert_id: str
    run_id: str
    provider: str
    severity: AlertSeverity
    code: str
    message: str
    dedupe_key: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _text("run_id", self.run_id))
        object.__setattr__(self, "provider", _text("provider", self.provider).lower())
        object.__setattr__(self, "code", _text("code", self.code))
        object.__setattr__(self, "message", _text("message", self.message))
        object.__setattr__(self, "dedupe_key", _text("dedupe_key", self.dedupe_key))
        if not isinstance(self.severity, AlertSeverity):
            raise ValueError("severity must be AlertSeverity")
        object.__setattr__(
            self, "metadata", freeze_json(self.metadata, name="alert metadata")
        )
        expected = "recoveryworks-alert:" + canonical_hash(self._identity())
        if self.alert_id != expected:
            raise ValueError("alert_id does not bind alert payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "run_id": self.run_id,
            "provider": self.provider,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "dedupe_key": self.dedupe_key,
            "metadata": dict(self.metadata),
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {**self._identity(), "alert_id": self.alert_id,
                "proof_hash": self.proof_hash}


@dataclass(frozen=True)
class ProductionRunManifest:
    manifest_id: str
    run_id: str
    deployment_id: str
    deployment_plan_proof_hash: str
    container_build_manifest_proof_hash: str
    client_id: str
    provider: str
    started_at: str
    completed_at: str
    status: ProductionRunStatus
    failure_code: ProductionFailureCode | None
    failure_detail: str | None
    state_head_hash: str | None
    assurance_report_proof_hash: str | None
    metrics_proof_hash: str | None
    event_hashes: tuple[str, ...]
    alert_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "run_id",
            "deployment_id",
            "client_id",
            "provider",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "deployment_plan_proof_hash",
            "container_build_manifest_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        start = normalize_utc_timestamp("started_at", self.started_at)
        end = normalize_utc_timestamp("completed_at", self.completed_at)
        if end < start:
            raise ValueError("completed_at cannot predate started_at")
        object.__setattr__(self, "started_at", start)
        object.__setattr__(self, "completed_at", end)
        if not isinstance(self.status, ProductionRunStatus):
            raise ValueError("status must be ProductionRunStatus")
        if self.status is ProductionRunStatus.FAILED:
            if self.failure_code is None or not self.failure_detail:
                raise ValueError("failed run requires failure code/detail")
        elif self.failure_code is not None or self.failure_detail is not None:
            raise ValueError("successful/review run cannot carry failure detail")
        if self.failure_detail is not None:
            object.__setattr__(
                self, "failure_detail", _text("failure_detail", self.failure_detail)
            )
        for name in (
            "state_head_hash",
            "assurance_report_proof_hash",
            "metrics_proof_hash",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, normalize_sha256(name, value))
        for collection_name in ("event_hashes", "alert_hashes"):
            values = tuple(getattr(self, collection_name))
            for index, value in enumerate(values):
                normalize_sha256(f"{collection_name}[{index}]", value)
            object.__setattr__(self, collection_name, values)
        expected = "recoveryworks-production-run:" + canonical_hash(self._identity())
        if self.manifest_id != expected:
            raise ValueError("manifest_id does not bind production run")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "run_id": self.run_id,
            "deployment_id": self.deployment_id,
            "deployment_plan_proof_hash": self.deployment_plan_proof_hash,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "client_id": self.client_id,
            "provider": self.provider,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "failure_code": (
                self.failure_code.value if self.failure_code is not None else None
            ),
            "failure_detail": self.failure_detail,
            "state_head_hash": self.state_head_hash,
            "assurance_report_proof_hash": self.assurance_report_proof_hash,
            "metrics_proof_hash": self.metrics_proof_hash,
            "event_hashes": list(self.event_hashes),
            "alert_hashes": list(self.alert_hashes),
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {**self._identity(), "manifest_id": self.manifest_id,
                "proof_hash": self.proof_hash}


def classify_production_failure(error: BaseException) -> ProductionFailureCode:
    message = str(error).lower()
    if "authorization" in message or "expired" in message:
        return ProductionFailureCode.AUTHORIZATION_INVALID
    if "hash mismatch" in message or "tamper" in message or "integrity" in message:
        return ProductionFailureCode.EVIDENCE_INTEGRITY
    if "provider" in message and ("scope" in message or "does not match" in message):
        return ProductionFailureCode.PROVIDER_SCOPE_MISMATCH
    if "supersession" in message:
        return ProductionFailureCode.SUPERSESSION_REQUIRED
    if "stale ledger writer" in message or "conflict" in message:
        return ProductionFailureCode.STATE_CONFLICT
    if "report" in message and ("hash" in message or "proof" in message):
        return ProductionFailureCode.OUTPUT_INTEGRITY
    if isinstance(error, (ValueError, TypeError, KeyError)):
        return ProductionFailureCode.CONFIGURATION_INVALID
    return ProductionFailureCode.RUNTIME_FAILURE


def _alert(
    *,
    run_id: str,
    provider: str,
    severity: AlertSeverity,
    code: str,
    message: str,
    dedupe_key: str,
    metadata: Mapping[str, Any],
) -> ProductionAlert:
    identity = {
        "schema": 1,
        "run_id": run_id,
        "provider": provider,
        "severity": severity.value,
        "code": code,
        "message": message,
        "dedupe_key": dedupe_key,
        "metadata": dict(metadata),
    }
    return ProductionAlert(
        alert_id="recoveryworks-alert:" + canonical_hash(identity),
        run_id=run_id,
        provider=provider,
        severity=severity,
        code=code,
        message=message,
        dedupe_key=dedupe_key,
        metadata=metadata,
    )


def build_success_observability(
    *,
    run_id: str,
    deployment_id: str,
    pilot: PilotRunResult,
    container_build_manifest_proof_hash: str,
    started_at: str,
    completed_at: str,
) -> tuple[
    ProductionRunManifest,
    ProductionMetricsSnapshot,
    tuple[ProductionRunEvent, ...],
    tuple[ProductionAlert, ...],
]:
    provider = pilot.export_receipt.provider
    client_id = pilot.continuous_result.scan.client_id
    recovery = pilot.continuous_result.scan.report.totals
    savings = pilot.continuous_result.savings_report
    metrics = ProductionMetricsSnapshot(
        run_id=run_id,
        provider=provider,
        client_id=client_id,
        recovery={
            key: recovery[key]
            for key in (
                "potential_cents",
                "review_cents",
                "validated_cents",
                "authorized_cents",
                "claimed_cents",
                "recovered_cents",
                "fee_cents",
                "superseded_cents",
            )
        },
        savings={
            "estimated_savings_opportunity_cents":
                savings.estimated_savings_opportunity_cents,
            "realized_savings_cents": savings.realized_savings_cents,
        },
        diagnostics={
            "estimated_anomaly_exposure_cents":
                savings.estimated_anomaly_exposure_cents,
            "reconciliation_drift_cents": savings.reconciliation_drift_cents,
        },
        job_health={
            "new_job_count": len(
                pilot.continuous_result.new_job_fingerprints
            ),
            "duplicate_job_count": len(
                pilot.continuous_result.duplicate_job_fingerprints
            ),
            "supersession_hold_count": len(
                pilot.continuous_result.supersession_candidates
            ),
            "exception_count": len(pilot.continuous_result.scan.exceptions),
            "state_head_present":
                pilot.continuous_result.scan.state_head_hash is not None,
        },
    )

    alerts: list[ProductionAlert] = []
    if pilot.continuous_result.supersession_candidates:
        alerts.append(_alert(
            run_id=run_id,
            provider=provider,
            severity=AlertSeverity.WARNING,
            code="SUPERSESSION_REVIEW_REQUIRED",
            message="Changed provider inputs/authority require reviewed supersession.",
            dedupe_key=f"{provider}:supersession",
            metadata={
                "candidate_ids": [
                    item.candidate_id
                    for item in pilot.continuous_result.supersession_candidates
                ]
            },
        ))
    if recovery["review_cents"] > 0:
        alerts.append(_alert(
            run_id=run_id,
            provider=provider,
            severity=AlertSeverity.WARNING,
            code="RECOVERY_EVIDENCE_REVIEW_REQUIRED",
            message="Recovery candidates remain in REVIEW because evidence is unverified.",
            dedupe_key=f"{provider}:recovery-review",
            metadata={"review_cents": recovery["review_cents"]},
        ))
    if pilot.continuous_result.scan.exceptions:
        alerts.append(_alert(
            run_id=run_id,
            provider=provider,
            severity=AlertSeverity.WARNING,
            code="SCAN_EXCEPTIONS_PRESENT",
            message="Provider scan completed with fail-closed exceptions.",
            dedupe_key=f"{provider}:scan-exceptions",
            metadata={
                "exception_codes": sorted({
                    item["code"]
                    for item in pilot.continuous_result.scan.exceptions
                })
            },
        ))

    event_specs = (
        ("RUN", "STARTED", {"deployment_plan_proof_hash": pilot.deployment_plan_hash}),
        ("BUNDLE", "FROZEN", {
            "bundle_sha256": pilot.export_receipt.bundle_sha256,
            "manifest_sha256": pilot.export_receipt.manifest_sha256,
        }),
        ("SCAN", "COMPLETED", {
            "state_head_hash": pilot.continuous_result.scan.state_head_hash,
            "validated_cents": recovery["validated_cents"],
            "review_cents": recovery["review_cents"],
        }),
        ("REPORT", "WRITTEN", {"report_path": pilot.report_path}),
        ("RUN", "COMPLETED", {
            "alert_count": len(alerts),
            "metrics_proof_hash": metrics.proof_hash,
        }),
    )
    events: list[ProductionRunEvent] = []
    previous = None
    for sequence, (phase, status, payload) in enumerate(event_specs, start=1):
        event = ProductionRunEvent.build(
            sequence=sequence,
            run_id=run_id,
            occurred_at=started_at if sequence == 1 else completed_at,
            phase=phase,
            status=status,
            provider=provider,
            deployment_id=deployment_id,
            payload=payload,
            previous_hash=previous,
        )
        events.append(event)
        previous = event.event_hash

    status = (
        ProductionRunStatus.REVIEW_REQUIRED
        if alerts
        else ProductionRunStatus.SUCCEEDED
    )
    identity = {
        "schema": 1,
        "run_id": run_id,
        "deployment_id": deployment_id,
        "deployment_plan_proof_hash": pilot.deployment_plan_hash,
        "container_build_manifest_proof_hash":
            container_build_manifest_proof_hash,
        "client_id": client_id,
        "provider": provider,
        "started_at": normalize_utc_timestamp("started_at", started_at),
        "completed_at": normalize_utc_timestamp("completed_at", completed_at),
        "status": status.value,
        "failure_code": None,
        "failure_detail": None,
        "state_head_hash": pilot.continuous_result.scan.state_head_hash,
        "assurance_report_proof_hash": _assurance_report_hash(pilot.report_path),
        "metrics_proof_hash": metrics.proof_hash,
        "event_hashes": [event.event_hash for event in events],
        "alert_hashes": [alert.proof_hash for alert in alerts],
    }
    manifest = ProductionRunManifest(
        manifest_id="recoveryworks-production-run:" + canonical_hash(identity),
        run_id=run_id,
        deployment_id=deployment_id,
        deployment_plan_proof_hash=pilot.deployment_plan_hash,
        container_build_manifest_proof_hash=
            container_build_manifest_proof_hash,
        client_id=client_id,
        provider=provider,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        failure_code=None,
        failure_detail=None,
        state_head_hash=pilot.continuous_result.scan.state_head_hash,
        assurance_report_proof_hash=identity["assurance_report_proof_hash"],
        metrics_proof_hash=metrics.proof_hash,
        event_hashes=tuple(identity["event_hashes"]),
        alert_hashes=tuple(identity["alert_hashes"]),
    )
    return manifest, metrics, tuple(events), tuple(alerts)


def _assurance_report_hash(path: str | Path) -> str:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("assurance report is unreadable") from exc
    proof_hash = payload.get("proof_hash")
    if not isinstance(proof_hash, str):
        raise ValueError("assurance report proof hash missing")
    normalize_sha256("assurance_report_proof_hash", proof_hash)
    identity = {key: value for key, value in payload.items() if key != "proof_hash"}
    if canonical_hash(identity) != proof_hash:
        raise ValueError("assurance report proof hash mismatch")
    return proof_hash


@dataclass(frozen=True)
class RunHistoryEntry:
    sequence: int
    recorded_at: str
    run_id: str
    run_manifest_proof_hash: str
    previous_hash: str | None
    entry_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        recorded_at: str,
        run_id: str,
        run_manifest_proof_hash: str,
        previous_hash: str | None,
    ) -> "RunHistoryEntry":
        body = {
            "schema": 1,
            "sequence": sequence,
            "recorded_at": normalize_utc_timestamp(
                "recorded_at", recorded_at
            ),
            "run_id": _text("run_id", run_id),
            "run_manifest_proof_hash": normalize_sha256(
                "run_manifest_proof_hash", run_manifest_proof_hash
            ),
            "previous_hash": previous_hash,
        }
        return cls(**body | {"entry_hash": canonical_hash(body)})


class ProductionRunHistoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_name(f".{self.path.name}.lock")

    def _read(self) -> tuple[RunHistoryEntry, ...]:
        if not self.path.exists():
            return ()
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("production run history is not valid JSON") from exc
        if envelope.get("schema") != 1:
            raise ValueError("unsupported production run history schema")
        raw_entries = envelope.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("production run history entries missing")
        entries: list[RunHistoryEntry] = []
        previous = None
        for index, raw in enumerate(raw_entries, start=1):
            rebuilt = RunHistoryEntry.build(
                sequence=raw["sequence"],
                recorded_at=raw["recorded_at"],
                run_id=raw["run_id"],
                run_manifest_proof_hash=raw["run_manifest_proof_hash"],
                previous_hash=raw.get("previous_hash"),
            )
            if rebuilt.sequence != index:
                raise ValueError("production run history sequence gap")
            if rebuilt.previous_hash != previous:
                raise ValueError("production run history chain mismatch")
            if rebuilt.entry_hash != raw.get("entry_hash"):
                raise ValueError("production run history entry hash mismatch")
            entries.append(rebuilt)
            previous = rebuilt.entry_hash
        if envelope.get("head_hash") != previous:
            raise ValueError("production run history head hash mismatch")
        return tuple(entries)

    def entries(self) -> tuple[RunHistoryEntry, ...]:
        return self._read()

    def record(
        self,
        manifest: ProductionRunManifest,
        *,
        recorded_at: str,
    ) -> str:
        with private_file_lock(self.lock_path):
            current = list(self._read())
            if any(item.run_id == manifest.run_id for item in current):
                raise ValueError("production run_id already recorded")
            previous = current[-1].entry_hash if current else None
            entry = RunHistoryEntry.build(
                sequence=len(current) + 1,
                recorded_at=recorded_at,
                run_id=manifest.run_id,
                run_manifest_proof_hash=manifest.proof_hash,
                previous_hash=previous,
            )
            current.append(entry)
            envelope = {
                "schema": 1,
                "head_hash": entry.entry_hash,
                "entries": [asdict(item) for item in current],
            }
            atomic_private_write(
                self.path,
                (
                    json.dumps(
                        envelope,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    )
                    + "\n"
                ).encode("utf-8"),
            )
            return entry.entry_hash


def write_observability_bundle(
    *,
    manifest: ProductionRunManifest,
    metrics: ProductionMetricsSnapshot,
    events: tuple[ProductionRunEvent, ...],
    alerts: tuple[ProductionAlert, ...],
    directory: str | Path,
) -> tuple[Path, Path, Path, Path]:
    target = Path(directory)
    paths = (
        target / "run-manifest.json",
        target / "metrics.json",
        target / "events.jsonl",
        target / "alerts.json",
    )
    atomic_private_write(
        paths[0],
        (json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    atomic_private_write(
        paths[1],
        (json.dumps(metrics.as_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    atomic_private_write(
        paths[2],
        b"".join(
            (
                json.dumps(
                    {**asdict(event), "payload": dict(event.payload)},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
            for event in events
        ),
    )
    atomic_private_write(
        paths[3],
        (
            json.dumps(
                [alert.as_dict() for alert in alerts],
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode(),
    )
    return paths
