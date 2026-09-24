"""Private production backup/restore and disaster-recovery rehearsal."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import zipfile

from recoveryworks.integrations.cletrics_registry import CletricsReceiptRegistry
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write, private_permissions_verified
from recoveryworks.production_observability import ProductionRunHistoryStore
from recoveryworks.store import LocalBundleStore


_REQUIRED_ROLES = (
    "ledger",
    "cletrics_receipts",
    "assurance_report",
    "run_history",
)
_ARCHIVE_NAMES = {
    "ledger": "ledger.json",
    "cletrics_receipts": "cletrics-receipts.json",
    "assurance_report": "assurance-report.json",
    "run_history": "run-history.json",
}


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ProductionBackupPolicy:
    retention_days: int
    max_rpo_seconds: int
    max_rto_seconds: int

    def __post_init__(self) -> None:
        if type(self.retention_days) is not int or not 1 <= self.retention_days <= 3650:
            raise ValueError("retention_days must be in 1..3650")
        for name in ("max_rpo_seconds", "max_rto_seconds"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class ProductionBackupArtifact:
    role: str
    archive_name: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if self.role not in _REQUIRED_ROLES:
            raise ValueError("unsupported backup artifact role")
        if self.archive_name != _ARCHIVE_NAMES[self.role]:
            raise ValueError("unexpected backup archive name")
        object.__setattr__(self, "sha256", normalize_sha256("sha256", self.sha256))
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")


@dataclass(frozen=True)
class ProductionBackupManifest:
    backup_id: str
    created_at: str
    source_checkpoint_at: str
    expires_at: str
    policy: ProductionBackupPolicy
    rpo_seconds: int
    archive_sha256: str
    artifacts: tuple[ProductionBackupArtifact, ...]

    def __post_init__(self) -> None:
        created = normalize_utc_timestamp("created_at", self.created_at)
        checkpoint = normalize_utc_timestamp(
            "source_checkpoint_at", self.source_checkpoint_at
        )
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(checkpoint) > _instant(created):
            raise ValueError("source checkpoint cannot postdate backup")
        if _instant(expires) <= _instant(created):
            raise ValueError("backup retention expiry must follow creation")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "source_checkpoint_at", checkpoint)
        object.__setattr__(self, "expires_at", expires)
        if type(self.rpo_seconds) is not int or self.rpo_seconds < 0:
            raise ValueError("rpo_seconds must be non-negative")
        if self.rpo_seconds > self.policy.max_rpo_seconds:
            raise ValueError("backup exceeds configured RPO")
        object.__setattr__(
            self, "archive_sha256", normalize_sha256("archive_sha256", self.archive_sha256)
        )
        artifacts = tuple(sorted(self.artifacts, key=lambda item: item.role))
        if tuple(item.role for item in artifacts) != tuple(sorted(_REQUIRED_ROLES)):
            raise ValueError("backup manifest must contain all required state roles")
        object.__setattr__(self, "artifacts", artifacts)
        expected = "recoveryworks-production-backup:" + canonical_hash(self._identity())
        if self.backup_id != expected:
            raise ValueError("backup_id does not bind backup manifest")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "created_at": self.created_at,
            "source_checkpoint_at": self.source_checkpoint_at,
            "expires_at": self.expires_at,
            "policy": self.policy.as_dict(),
            "rpo_seconds": self.rpo_seconds,
            "archive_sha256": self.archive_sha256,
            "artifacts": [asdict(item) for item in self.artifacts],
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "backup_id": self.backup_id,
            "proof_hash": self.proof_hash,
            "state": "PRIVATE_BACKUP_FROZEN",
        }


def _zip_bytes(payloads: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payloads[name])
    return buffer.getvalue()


def create_production_backup(
    *,
    sources: Mapping[str, str | Path],
    policy: ProductionBackupPolicy,
    created_at: str,
    source_checkpoint_at: str,
    archive_path: str | Path,
    manifest_path: str | Path,
) -> ProductionBackupManifest:
    if set(sources) != set(_REQUIRED_ROLES):
        raise ValueError("backup sources must exactly match required state roles")
    created = normalize_utc_timestamp("created_at", created_at)
    checkpoint = normalize_utc_timestamp("source_checkpoint_at", source_checkpoint_at)
    rpo_seconds = int((_instant(created) - _instant(checkpoint)).total_seconds())
    if rpo_seconds < 0 or rpo_seconds > policy.max_rpo_seconds:
        raise ValueError("backup exceeds configured RPO")

    payloads: dict[str, bytes] = {}
    artifacts: list[ProductionBackupArtifact] = []
    for role in _REQUIRED_ROLES:
        path = Path(sources[role])
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"backup source must be a regular file: {role}")
        if not private_permissions_verified(path):
            raise PermissionError(f"backup source is not private: {role}")
        raw = path.read_bytes()
        archive_name = _ARCHIVE_NAMES[role]
        payloads[archive_name] = raw
        artifacts.append(
            ProductionBackupArtifact(
                role=role,
                archive_name=archive_name,
                sha256=_sha(raw),
                size_bytes=len(raw),
            )
        )

    archive_raw = _zip_bytes(payloads)
    atomic_private_write(Path(archive_path), archive_raw)
    if not private_permissions_verified(Path(archive_path)):
        raise PermissionError("backup archive is not private")
    expires = (
        _instant(created) + timedelta(days=policy.retention_days)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identity = {
        "schema": 1,
        "created_at": created,
        "source_checkpoint_at": checkpoint,
        "expires_at": expires,
        "policy": policy.as_dict(),
        "rpo_seconds": rpo_seconds,
        "archive_sha256": _sha(archive_raw),
        "artifacts": [asdict(item) for item in sorted(artifacts, key=lambda item: item.role)],
    }
    manifest = ProductionBackupManifest(
        backup_id="recoveryworks-production-backup:" + canonical_hash(identity),
        created_at=created,
        source_checkpoint_at=checkpoint,
        expires_at=expires,
        policy=policy,
        rpo_seconds=rpo_seconds,
        archive_sha256=identity["archive_sha256"],
        artifacts=tuple(artifacts),
    )
    atomic_private_write(
        Path(manifest_path),
        (
            json.dumps(
                manifest.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    return manifest


def _verify_assurance_report(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("restored assurance report is invalid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("restored assurance report must be an object")
    proof = payload.get("proof_hash")
    if not isinstance(proof, str):
        raise ValueError("restored assurance report proof hash missing")
    normalize_sha256("assurance_report.proof_hash", proof)
    identity = {key: value for key, value in payload.items() if key != "proof_hash"}
    if canonical_hash(identity) != proof:
        raise ValueError("restored assurance report proof hash mismatch")
    return proof


@dataclass(frozen=True)
class DisasterRecoveryRehearsal:
    rehearsal_id: str
    backup_id: str
    backup_proof_hash: str
    started_at: str
    completed_at: str
    rpo_seconds: int
    rto_seconds: int
    restored_artifact_hashes: Mapping[str, str]
    semantic_checks: tuple[str, ...]
    passed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "backup_proof_hash", normalize_sha256(
                "backup_proof_hash", self.backup_proof_hash
            )
        )
        start = normalize_utc_timestamp("started_at", self.started_at)
        end = normalize_utc_timestamp("completed_at", self.completed_at)
        if _instant(end) < _instant(start):
            raise ValueError("rehearsal completion cannot predate start")
        object.__setattr__(self, "started_at", start)
        object.__setattr__(self, "completed_at", end)
        if type(self.rpo_seconds) is not int or self.rpo_seconds < 0:
            raise ValueError("rpo_seconds must be non-negative")
        if type(self.rto_seconds) is not int or self.rto_seconds < 0:
            raise ValueError("rto_seconds must be non-negative")
        hashes = {
            str(key): normalize_sha256(f"restored_artifact_hashes.{key}", value)
            for key, value in self.restored_artifact_hashes.items()
        }
        if set(hashes) != set(_REQUIRED_ROLES):
            raise ValueError("rehearsal must verify all required state roles")
        object.__setattr__(self, "restored_artifact_hashes", hashes)
        if self.passed is not True:
            raise ValueError("DR rehearsal artifact only represents a passing rehearsal")
        expected = "recoveryworks-dr-rehearsal:" + canonical_hash(self._identity())
        if self.rehearsal_id != expected:
            raise ValueError("rehearsal_id does not bind DR rehearsal")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "backup_id": self.backup_id,
            "backup_proof_hash": self.backup_proof_hash,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "rpo_seconds": self.rpo_seconds,
            "rto_seconds": self.rto_seconds,
            "restored_artifact_hashes": dict(sorted(self.restored_artifact_hashes.items())),
            "semantic_checks": list(self.semantic_checks),
            "passed": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "rehearsal_id": self.rehearsal_id,
            "proof_hash": self.proof_hash,
            "state": "DR_REHEARSAL_PASSED",
        }


def rehearse_production_restore(
    manifest: ProductionBackupManifest,
    *,
    archive_path: str | Path,
    restore_dir: str | Path,
    started_at: str,
    completed_at: str,
) -> DisasterRecoveryRehearsal:
    archive = Path(archive_path)
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("backup archive must be a regular file")
    raw_archive = archive.read_bytes()
    if _sha(raw_archive) != manifest.archive_sha256:
        raise ValueError("backup archive hash mismatch")
    target = Path(restore_dir)
    target.mkdir(parents=True, exist_ok=True)

    artifact_index = {item.archive_name: item for item in manifest.artifacts}
    restored_hashes: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(raw_archive), "r") as zipped:
        names = [name for name in zipped.namelist() if not name.endswith("/")]
        if set(names) != set(artifact_index):
            raise ValueError("backup archive file set mismatch")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or len(pure.parts) != 1:
                raise ValueError("unsafe backup archive path")
            artifact = artifact_index[name]
            raw = zipped.read(name)
            if len(raw) != artifact.size_bytes or _sha(raw) != artifact.sha256:
                raise ValueError(f"backup artifact integrity mismatch: {artifact.role}")
            out = target / name
            if out.exists():
                raise ValueError("restore target must not contain existing artifact files")
            atomic_private_write(out, raw)
            restored_hashes[artifact.role] = _sha(raw)

    ledger = LocalBundleStore(target / _ARCHIVE_NAMES["ledger"]).load()
    if ledger is None:
        raise ValueError("restored RecoveryOS ledger is empty")
    CletricsReceiptRegistry(
        target / _ARCHIVE_NAMES["cletrics_receipts"]
    ).receipts()
    assurance_proof = _verify_assurance_report(
        target / _ARCHIVE_NAMES["assurance_report"]
    )
    ProductionRunHistoryStore(
        target / _ARCHIVE_NAMES["run_history"]
    ).entries()

    start = normalize_utc_timestamp("started_at", started_at)
    end = normalize_utc_timestamp("completed_at", completed_at)
    rto_seconds = int((_instant(end) - _instant(start)).total_seconds())
    if rto_seconds < 0 or rto_seconds > manifest.policy.max_rto_seconds:
        raise ValueError("restore rehearsal exceeds configured RTO")
    if manifest.rpo_seconds > manifest.policy.max_rpo_seconds:
        raise ValueError("backup no longer satisfies configured RPO")
    checks = (
        "archive hash verified",
        "all required private-state artifacts restored",
        "RecoveryOS ledger bundle integrity verified",
        "Cletrics receipt registry integrity verified",
        f"assurance report proof verified: {assurance_proof}",
        "production run-history chain verified",
        "RPO objective satisfied",
        "RTO objective satisfied",
    )
    identity = {
        "schema": 1,
        "backup_id": manifest.backup_id,
        "backup_proof_hash": manifest.proof_hash,
        "started_at": start,
        "completed_at": end,
        "rpo_seconds": manifest.rpo_seconds,
        "rto_seconds": rto_seconds,
        "restored_artifact_hashes": dict(sorted(restored_hashes.items())),
        "semantic_checks": list(checks),
        "passed": True,
    }
    return DisasterRecoveryRehearsal(
        rehearsal_id="recoveryworks-dr-rehearsal:" + canonical_hash(identity),
        backup_id=manifest.backup_id,
        backup_proof_hash=manifest.proof_hash,
        started_at=start,
        completed_at=end,
        rpo_seconds=manifest.rpo_seconds,
        rto_seconds=rto_seconds,
        restored_artifact_hashes=restored_hashes,
        semantic_checks=checks,
        passed=True,
    )
