"""Continuous production assurance/currentness evaluation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable

from recoveryworks.environment_activation import EnvironmentStateDiscovery
from recoveryworks.incident_lifecycle import (
    IncidentLifecycleJournal,
    IncidentLifecycleState,
)
from recoveryworks.integrations.cletrics_registry import CletricsReceiptRegistry
from recoveryworks.integrations.cletrics_supersession import CloudSupersessionCandidate
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write
from recoveryworks.tenant_isolation import (
    bind_managed_tenant_artifact,
    file_sha256,
    find_tenant_registry,
)
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.production_observability import ProductionRunHistoryStore
from recoveryworks.production_resilience import (
    DisasterRecoveryRehearsal,
    ProductionBackupManifest,
)
from recoveryworks.release_control import RecoveryWorksReleaseManifest
from recoveryworks.release_security import VulnerabilityScanReceipt
from recoveryworks.release_security_bridge import (
    ExternalProvenanceVerificationReceipt,
    ExternalSignatureVerificationReceipt,
    VerifiedReleaseSecurityEvidence,
)


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


class AssuranceSeverity(str, Enum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class ProductionAssuranceState(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ContinuousAssurancePolicy:
    max_security_age_seconds: int = 7 * 24 * 60 * 60
    max_dr_age_seconds: int = 7 * 24 * 60 * 60
    max_backup_age_seconds: int = 24 * 60 * 60
    max_run_history_age_seconds: int = 24 * 60 * 60
    max_cloud_evidence_age_seconds: int = 36 * 60 * 60

    def __post_init__(self) -> None:
        for name in (
            "max_security_age_seconds",
            "max_dr_age_seconds",
            "max_backup_age_seconds",
            "max_run_history_age_seconds",
            "max_cloud_evidence_age_seconds",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ProductionAssuranceCheck:
    code: str
    severity: AssuranceSeverity
    passed: bool
    detail: str
    evidence_proof_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.severity, AssuranceSeverity):
            raise ValueError("severity must be AssuranceSeverity")
        if type(self.passed) is not bool:
            raise ValueError("passed must be boolean")
        hashes = tuple(
            sorted(
                normalize_sha256("evidence_proof_hash", value)
                for value in self.evidence_proof_hashes
            )
        )
        object.__setattr__(self, "evidence_proof_hashes", hashes)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "code": self.code,
            "severity": self.severity.value,
            "passed": self.passed,
            "detail": self.detail,
            "evidence_proof_hashes": list(self.evidence_proof_hashes),
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "passed": self.passed,
            "detail": self.detail,
            "evidence_proof_hashes": list(self.evidence_proof_hashes),
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class ContinuousProductionAssurance:
    assurance_id: str
    checked_at: str
    release_id: str
    release_proof_hash: str
    production_admission_proof_hash: str
    policy: ContinuousAssurancePolicy
    state: ProductionAssuranceState
    checks: tuple[ProductionAssuranceCheck, ...]
    automatic_remediation_enabled: bool = False
    external_actions_performed: bool = False
    tenant_id: str | None = None
    tenant_proof_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at)
        )
        object.__setattr__(
            self, "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash)
        )
        object.__setattr__(
            self,
            "production_admission_proof_hash",
            normalize_sha256(
                "production_admission_proof_hash",
                self.production_admission_proof_hash,
            ),
        )
        if not isinstance(self.state, ProductionAssuranceState):
            raise ValueError("state must be ProductionAssuranceState")
        checks = tuple(sorted(self.checks, key=lambda item: item.code))
        if not checks:
            raise ValueError("continuous assurance requires checks")
        object.__setattr__(self, "checks", checks)
        if (self.tenant_id is None) != (self.tenant_proof_hash is None):
            raise ValueError("tenant_id and tenant_proof_hash must be supplied together")
        if self.tenant_proof_hash is not None:
            object.__setattr__(
                self,
                "tenant_proof_hash",
                normalize_sha256("tenant_proof_hash", self.tenant_proof_hash),
            )
        if self.automatic_remediation_enabled or self.external_actions_performed:
            raise ValueError("continuous assurance is read-only")
        expected = "recoveryworks-continuous-assurance:" + canonical_hash(
            self._identity()
        )
        if self.assurance_id != expected:
            raise ValueError("assurance_id does not bind assurance snapshot")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "checked_at": self.checked_at,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "production_admission_proof_hash":
                self.production_admission_proof_hash,
            "policy": asdict(self.policy),
            "state": self.state.value,
            "check_hashes": [check.proof_hash for check in self.checks],
            "automatic_remediation_enabled": False,
            "external_actions_performed": False,
            "tenant_id": self.tenant_id,
            "tenant_proof_hash": self.tenant_proof_hash,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "checks": [check.as_dict() for check in self.checks],
            "assurance_id": self.assurance_id,
            "proof_hash": self.proof_hash,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Continuous Production Assurance",
            "",
            f"State: {self.state.value}",
            f"Release: {self.release_id}",
            f"Checked at: {self.checked_at}",
            "",
            "## Checks",
            "",
        ]
        for check in self.checks:
            marker = "PASS" if check.passed else check.severity.value
            lines.append(f"- [{marker}] {check.code}: {check.detail}")
        lines.extend([
            "",
            "Automatic remediation: disabled",
            "External actions performed: false",
            "",
        ])
        return "\n".join(lines)


def _age_seconds(now: datetime, timestamp: str) -> int:
    age = int((now - _instant(timestamp)).total_seconds())
    if age < 0:
        raise ValueError("assurance evidence timestamp is in the future")
    return age


def _check(
    code: str,
    severity: AssuranceSeverity,
    passed: bool,
    detail: str,
    *proof_hashes: str,
) -> ProductionAssuranceCheck:
    return ProductionAssuranceCheck(
        code=code,
        severity=severity,
        passed=passed,
        detail=detail,
        evidence_proof_hashes=tuple(proof_hashes),
    )


def evaluate_continuous_production_assurance(
    *,
    release: RecoveryWorksReleaseManifest,
    admission: ProductionAdmissionGate,
    environment: EnvironmentStateDiscovery,
    security_evidence: VerifiedReleaseSecurityEvidence,
    vulnerability_scan: VulnerabilityScanReceipt,
    signature_receipt: ExternalSignatureVerificationReceipt,
    provenance_receipt: ExternalProvenanceVerificationReceipt,
    dr_rehearsal: DisasterRecoveryRehearsal,
    backup: ProductionBackupManifest,
    run_history: ProductionRunHistoryStore,
    cletrics_registry: CletricsReceiptRegistry,
    incident_journal: IncidentLifecycleJournal,
    supersession_candidates: Iterable[CloudSupersessionCandidate] = (),
    checked_at: str,
    policy: ContinuousAssurancePolicy = ContinuousAssurancePolicy(),
) -> ContinuousProductionAssurance:
    checked_at = normalize_utc_timestamp("checked_at", checked_at)
    now = _instant(checked_at)
    checks: list[ProductionAssuranceCheck] = []
    managed_registry = find_tenant_registry(cletrics_registry.path)
    managed_identity = None
    if managed_registry is not None:
        managed_identity = managed_registry.identity_for_path(
            cletrics_registry.path
        )
        managed_registry.assert_path_tenant(
            managed_identity, run_history.path
        )

    release_ok = (
        admission.release_id == release.release_id
        and admission.release_proof_hash == release.proof_hash
        and admission.container_image_digest == release.container_image_digest
        and admission.source_commit == release.source_commit
    )
    checks.append(_check(
        "ADMISSION_RELEASE_BINDING",
        AssuranceSeverity.BLOCK,
        release_ok,
        "Production admission matches release/image/source."
        if release_ok else "Production admission no longer matches release/image/source.",
        admission.proof_hash,
        release.proof_hash,
    ))

    env_ok = (
        environment.verified
        and environment.current_release_id == release.release_id
        and environment.current_image_digest == release.container_image_digest
    )
    checks.append(_check(
        "ENVIRONMENT_RELEASE_DRIFT",
        AssuranceSeverity.BLOCK,
        env_ok,
        "Verified environment matches admitted release/image."
        if env_ok else "Verified environment is missing or drifted from release/image.",
        environment.proof_hash,
        release.proof_hash,
    ))

    security_binding = (
        security_evidence.release_id == release.release_id
        and security_evidence.release_proof_hash == release.proof_hash
        and security_evidence.container_image_digest == release.container_image_digest
        and security_evidence.vulnerability_scan_proof_hash == vulnerability_scan.proof_hash
        and security_evidence.signature_verification_proof_hash == signature_receipt.proof_hash
        and security_evidence.provenance_verification_proof_hash == provenance_receipt.proof_hash
    )
    latest_security_time = min(
        vulnerability_scan.scanned_at,
        signature_receipt.verified_at,
        provenance_receipt.verified_at,
    )
    security_fresh = (
        security_binding
        and vulnerability_scan.verified
        and _age_seconds(now, latest_security_time) <= policy.max_security_age_seconds
    )
    checks.append(_check(
        "SECURITY_EVIDENCE_FRESHNESS",
        AssuranceSeverity.BLOCK,
        security_fresh,
        "Security scan/signature/provenance evidence is current and release-bound."
        if security_fresh else "Security evidence is stale or no longer release-bound.",
        security_evidence.proof_hash,
        vulnerability_scan.proof_hash,
        signature_receipt.proof_hash,
        provenance_receipt.proof_hash,
    ))

    dr_fresh = (
        dr_rehearsal.passed
        and _age_seconds(now, dr_rehearsal.completed_at) <= policy.max_dr_age_seconds
    )
    checks.append(_check(
        "DR_REHEARSAL_FRESHNESS",
        AssuranceSeverity.BLOCK,
        dr_fresh,
        "Passing DR rehearsal is current."
        if dr_fresh else "DR rehearsal is stale or not passing.",
        dr_rehearsal.proof_hash,
    ))

    backup_fresh = (
        backup.rpo_seconds <= backup.policy.max_rpo_seconds
        and _age_seconds(now, backup.created_at) <= policy.max_backup_age_seconds
        and _instant(backup.expires_at) > now
    )
    checks.append(_check(
        "BACKUP_RPO_AND_FRESHNESS",
        AssuranceSeverity.BLOCK,
        backup_fresh,
        "Backup is current, retained, and within RPO."
        if backup_fresh else "Backup is stale, expired, or outside RPO.",
        backup.proof_hash,
    ))

    history_entries = run_history.entries()
    history_fresh = bool(history_entries) and (
        _age_seconds(now, history_entries[-1].recorded_at)
        <= policy.max_run_history_age_seconds
    )
    history_hash = (
        history_entries[-1].entry_hash if history_entries else "0" * 64
    )
    checks.append(_check(
        "RUN_HISTORY_INTEGRITY_AND_FRESHNESS",
        AssuranceSeverity.BLOCK,
        history_fresh,
        "Run-history chain is valid and current."
        if history_fresh else "Run-history is empty or stale.",
        history_hash,
    ))

    receipts = cletrics_registry.receipts()
    latest_exported = max((receipt.exported_at for receipt in receipts), default=None)
    cloud_fresh = latest_exported is not None and (
        _age_seconds(now, latest_exported) <= policy.max_cloud_evidence_age_seconds
    )
    registry_hash = cletrics_registry.state_hash() or "0" * 64
    checks.append(_check(
        "CLOUD_EVIDENCE_FRESHNESS",
        AssuranceSeverity.BLOCK,
        cloud_fresh,
        "Cletrics processing evidence is current."
        if cloud_fresh else "Cletrics processing evidence is missing or stale.",
        registry_hash,
    ))

    all_verified = bool(receipts) and all(
        all(receipt.verification_flags.values()) for receipt in receipts
    )
    checks.append(_check(
        "CLOUD_EVIDENCE_VERIFICATION",
        AssuranceSeverity.REVIEW,
        all_verified,
        "All current cloud money-bearing sources are verified."
        if all_verified else "One or more current cloud sources remain unverified.",
        registry_hash,
    ))

    events = incident_journal.events()
    latest_by_incident: dict[str, IncidentLifecycleState] = {}
    for event in events:
        latest_by_incident[event.incident_id] = event.state
    blocking_incidents = sorted(
        incident_id for incident_id, state in latest_by_incident.items()
        if state not in {
            IncidentLifecycleState.CLOSED,
            IncidentLifecycleState.REVIEWED,
        }
    )
    unreviewed_closed = sorted(
        incident_id for incident_id, state in latest_by_incident.items()
        if state is IncidentLifecycleState.CLOSED
    )
    incidents_clear = not blocking_incidents
    incident_hash = events[-1].event_hash if events else "0" * 64
    checks.append(_check(
        "OUTSTANDING_INCIDENTS",
        AssuranceSeverity.BLOCK,
        incidents_clear,
        "No unresolved production incidents."
        if incidents_clear else
        "Unresolved incidents: " + ", ".join(blocking_incidents),
        incident_hash,
    ))
    checks.append(_check(
        "POST_INCIDENT_REVIEW_BACKLOG",
        AssuranceSeverity.REVIEW,
        not unreviewed_closed,
        "No closed incidents awaiting review."
        if not unreviewed_closed else
        "Closed incidents awaiting REVIEWED state: " + ", ".join(unreviewed_closed),
        incident_hash,
    ))

    supersessions = tuple(supersession_candidates)
    supersession_clear = not supersessions
    checks.append(_check(
        "OUTSTANDING_SUPERSESSIONS",
        AssuranceSeverity.REVIEW,
        supersession_clear,
        "No cloud supersession candidates are outstanding."
        if supersession_clear else
        f"{len(supersessions)} cloud supersession candidate(s) require review.",
        *(candidate.proof_hash for candidate in supersessions),
    ))

    failed = [check for check in checks if not check.passed]
    if any(check.severity is AssuranceSeverity.BLOCK for check in failed):
        state = ProductionAssuranceState.BLOCKED
    elif failed:
        state = ProductionAssuranceState.REVIEW_REQUIRED
    else:
        state = ProductionAssuranceState.PASS

    checks = sorted(checks, key=lambda item: item.code)
    identity = {
        "schema": 1,
        "checked_at": checked_at,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "production_admission_proof_hash": admission.proof_hash,
        "policy": asdict(policy),
        "state": state.value,
        "check_hashes": [check.proof_hash for check in checks],
        "automatic_remediation_enabled": False,
        "external_actions_performed": False,
        "tenant_id": (
            None if managed_identity is None else managed_identity.tenant_id
        ),
        "tenant_proof_hash": (
            None if managed_identity is None else managed_identity.proof_hash
        ),
    }
    return ContinuousProductionAssurance(
        assurance_id="recoveryworks-continuous-assurance:"
        + canonical_hash(identity),
        checked_at=checked_at,
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        production_admission_proof_hash=admission.proof_hash,
        policy=policy,
        state=state,
        checks=tuple(checks),
        automatic_remediation_enabled=False,
        external_actions_performed=False,
        tenant_id=None if managed_identity is None else managed_identity.tenant_id,
        tenant_proof_hash=(
            None if managed_identity is None else managed_identity.proof_hash
        ),
    )


def write_continuous_production_assurance(
    assurance: ContinuousProductionAssurance,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                assurance.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (assurance.to_markdown() + "\n").encode("utf-8"),
    )
    if assurance.tenant_id is not None:
        registry = find_tenant_registry(json_path)
        if registry is None:
            raise ValueError(
                "tenant-bound assurance output requires tenant registry"
            )
        identity = registry.identity_for_tenant_id(assurance.tenant_id)
        if identity.proof_hash != assurance.tenant_proof_hash:
            raise ValueError("assurance tenant proof no longer matches registry")
        registry.reserve_paths(
            identity,
            artifact_paths={
                "continuous_assurance_json": json_path,
                "continuous_assurance_markdown": markdown_path,
            },
        )
        bind_managed_tenant_artifact(
            registry,
            identity,
            artifact_type="continuous_assurance_json",
            artifact_key=assurance.assurance_id,
            proof_hash=assurance.proof_hash,
            path=json_path,
            bound_at=assurance.checked_at,
        )
        bind_managed_tenant_artifact(
            registry,
            identity,
            artifact_type="continuous_assurance_markdown",
            artifact_key=assurance.assurance_id,
            proof_hash=file_sha256(markdown_path),
            path=markdown_path,
            bound_at=assurance.checked_at,
        )
