"""Customer data governance for managed RecoveryWorks private state.

Controls customer isolation, purpose limitation, classification, retention,
legal hold, customer export, logical deletion receipts, and access audit history.
This module deliberately rejects raw credential/secret material.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Mapping
import zipfile

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write, private_file_lock, private_permissions_verified


class CustomerDataClassification(str, Enum):
    CUSTOMER_CONFIDENTIAL = "CUSTOMER_CONFIDENTIAL"
    FINANCIAL_EVIDENCE = "FINANCIAL_EVIDENCE"
    AUTHORIZATION_METADATA = "AUTHORIZATION_METADATA"
    OPERATIONAL_METADATA = "OPERATIONAL_METADATA"


class CustomerDataPurpose(str, Enum):
    CLOUD_BILLING_AUDIT = "CLOUD_BILLING_AUDIT"
    RECOVERY_EVIDENCE = "RECOVERY_EVIDENCE"
    SAVINGS_ANALYSIS = "SAVINGS_ANALYSIS"
    OPERATIONS = "OPERATIONS"
    COMPLIANCE = "COMPLIANCE"
    CUSTOMER_EXPORT = "CUSTOMER_EXPORT"
    DELETION = "DELETION"


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    lowered = normalized.lower()
    if any(marker in lowered for marker in ("password=", "secret=", "token=", "private_key")):
        raise ValueError(f"{name} appears to contain secret material")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class CustomerDataObject:
    object_id: str
    customer_id: str
    relative_path: str
    classification: CustomerDataClassification
    allowed_purposes: tuple[CustomerDataPurpose, ...]
    sha256: str
    size_bytes: int
    collected_at: str
    retention_until: str
    source_kind: str
    secret_material_present: bool = False

    def __post_init__(self) -> None:
        for name in ("customer_id", "relative_path", "source_kind"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if Path(self.relative_path).is_absolute() or ".." in Path(self.relative_path).parts:
            raise ValueError("relative_path must stay within the customer data space")
        if not isinstance(self.classification, CustomerDataClassification):
            raise ValueError("classification must be CustomerDataClassification")
        purposes = tuple(sorted(set(self.allowed_purposes), key=lambda x: x.value))
        if not purposes or not all(isinstance(x, CustomerDataPurpose) for x in purposes):
            raise ValueError("allowed_purposes must contain data-purpose values")
        object.__setattr__(self, "allowed_purposes", purposes)
        object.__setattr__(self, "sha256", normalize_sha256("sha256", self.sha256))
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        object.__setattr__(
            self, "collected_at", normalize_utc_timestamp("collected_at", self.collected_at)
        )
        object.__setattr__(
            self, "retention_until",
            normalize_utc_timestamp("retention_until", self.retention_until),
        )
        if _instant(self.retention_until) < _instant(self.collected_at):
            raise ValueError("retention_until cannot predate collection")
        if self.secret_material_present:
            raise ValueError("raw credential/secret material cannot enter customer data inventory")
        expected = "customer-data-object:" + canonical_hash(self._identity())
        if self.object_id != expected:
            raise ValueError("object_id does not bind customer data object")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "customer_id": self.customer_id,
            "relative_path": self.relative_path,
            "classification": self.classification.value,
            "allowed_purposes": [p.value for p in self.allowed_purposes],
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "collected_at": self.collected_at,
            "retention_until": self.retention_until,
            "source_kind": self.source_kind,
            "secret_material_present": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class CustomerDataInventory:
    inventory_id: str
    customer_id: str
    generated_at: str
    objects: tuple[CustomerDataObject, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "customer_id", _text("customer_id", self.customer_id))
        object.__setattr__(
            self, "generated_at", normalize_utc_timestamp("generated_at", self.generated_at)
        )
        objects = tuple(sorted(self.objects, key=lambda x: x.object_id))
        if any(x.customer_id != self.customer_id for x in objects):
            raise ValueError("inventory cannot mix customers")
        if len({x.relative_path for x in objects}) != len(objects):
            raise ValueError("inventory cannot contain duplicate customer paths")
        object.__setattr__(self, "objects", objects)
        expected = "customer-data-inventory:" + canonical_hash(self._identity())
        if self.inventory_id != expected:
            raise ValueError("inventory_id does not bind inventory")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "customer_id": self.customer_id,
            "generated_at": self.generated_at,
            "object_hashes": [x.proof_hash for x in self.objects],
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_customer_data_inventory(
    *,
    customer_id: str,
    customer_root: str | Path,
    object_specs: tuple[Mapping[str, Any], ...],
    generated_at: str,
) -> CustomerDataInventory:
    root = Path(customer_root).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("customer_root must be a non-symlink directory")
    objects: list[CustomerDataObject] = []
    for spec in object_specs:
        rel = Path(_text("relative_path", str(spec["relative_path"])))
        path = (root / rel).resolve()
        if not _within(root, path) or path.is_symlink() or not path.is_file():
            raise ValueError("customer data object must be a regular file inside customer_root")
        if not private_permissions_verified(path):
            raise PermissionError("customer data object must be private")
        raw_hash = _sha(path)
        collected = normalize_utc_timestamp("collected_at", spec["collected_at"])
        retention = normalize_utc_timestamp("retention_until", spec["retention_until"])
        classification = CustomerDataClassification(spec["classification"])
        purposes = tuple(CustomerDataPurpose(value) for value in spec["allowed_purposes"])
        identity = {
            "schema": 1,
            "customer_id": customer_id,
            "relative_path": rel.as_posix(),
            "classification": classification.value,
            "allowed_purposes": sorted(p.value for p in purposes),
            "sha256": raw_hash,
            "size_bytes": path.stat().st_size,
            "collected_at": collected,
            "retention_until": retention,
            "source_kind": _text("source_kind", spec["source_kind"]),
            "secret_material_present": False,
        }
        objects.append(CustomerDataObject(
            object_id="customer-data-object:" + canonical_hash(identity),
            customer_id=customer_id,
            relative_path=rel.as_posix(),
            classification=classification,
            allowed_purposes=purposes,
            sha256=raw_hash,
            size_bytes=path.stat().st_size,
            collected_at=collected,
            retention_until=retention,
            source_kind=spec["source_kind"],
            secret_material_present=False,
        ))
    generated = normalize_utc_timestamp("generated_at", generated_at)
    objects_sorted = tuple(sorted(objects, key=lambda x: x.object_id))
    identity = {
        "schema": 1,
        "customer_id": customer_id,
        "generated_at": generated,
        "object_hashes": [x.proof_hash for x in objects_sorted],
    }
    return CustomerDataInventory(
        inventory_id="customer-data-inventory:" + canonical_hash(identity),
        customer_id=customer_id,
        generated_at=generated,
        objects=objects_sorted,
    )


@dataclass(frozen=True)
class CustomerLegalHold:
    hold_id: str
    customer_id: str
    object_ids: tuple[str, ...]
    reason: str
    imposed_by: str
    imposed_at: str
    released_at: str | None = None

    def __post_init__(self) -> None:
        for name in ("customer_id", "reason", "imposed_by"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        ids = tuple(sorted(set(_text("object_id", x) for x in self.object_ids)))
        if not ids:
            raise ValueError("legal hold must bind objects")
        object.__setattr__(self, "object_ids", ids)
        object.__setattr__(
            self, "imposed_at", normalize_utc_timestamp("imposed_at", self.imposed_at)
        )
        if self.released_at is not None:
            released = normalize_utc_timestamp("released_at", self.released_at)
            if _instant(released) < _instant(self.imposed_at):
                raise ValueError("legal hold release cannot predate imposition")
            object.__setattr__(self, "released_at", released)
        expected = "customer-legal-hold:" + canonical_hash(self._identity())
        if self.hold_id != expected:
            raise ValueError("hold_id does not bind legal hold")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "customer_id": self.customer_id,
            "object_ids": list(self.object_ids),
            "reason": self.reason,
            "imposed_by": self.imposed_by,
            "imposed_at": self.imposed_at,
            "released_at": self.released_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    @property
    def active(self) -> bool:
        return self.released_at is None


@dataclass(frozen=True)
class CustomerDataAccessEvent:
    sequence: int
    customer_id: str
    object_id: str
    actor_id: str
    purpose: CustomerDataPurpose
    accessed_at: str
    allowed: bool
    reason: str
    previous_hash: str | None
    event_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        customer_id: str,
        object_id: str,
        actor_id: str,
        purpose: CustomerDataPurpose,
        accessed_at: str,
        allowed: bool,
        reason: str,
        previous_hash: str | None,
    ) -> "CustomerDataAccessEvent":
        fields = {
            "sequence": sequence,
            "customer_id": _text("customer_id", customer_id),
            "object_id": _text("object_id", object_id),
            "actor_id": _text("actor_id", actor_id),
            "purpose": purpose,
            "accessed_at": normalize_utc_timestamp("accessed_at", accessed_at),
            "allowed": allowed,
            "reason": _text("reason", reason),
            "previous_hash": previous_hash,
        }
        identity = {
            "schema": 1,
            **fields,
            "purpose": purpose.value,
        }
        return cls(**fields, event_hash=canonical_hash(identity))


class CustomerDataAccessHistory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name("." + self.path.name + ".lock")

    def _read(self) -> tuple[CustomerDataAccessEvent, ...]:
        if not self.path.exists():
            return ()
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema") != 1:
            raise ValueError("unsupported customer access history schema")
        previous = None
        events = []
        for index, row in enumerate(envelope.get("events", []), start=1):
            event = CustomerDataAccessEvent.build(
                sequence=row["sequence"],
                customer_id=row["customer_id"],
                object_id=row["object_id"],
                actor_id=row["actor_id"],
                purpose=CustomerDataPurpose(row["purpose"]),
                accessed_at=row["accessed_at"],
                allowed=row["allowed"],
                reason=row["reason"],
                previous_hash=row.get("previous_hash"),
            )
            if event.sequence != index or event.previous_hash != previous:
                raise ValueError("customer access history chain mismatch")
            if event.event_hash != row.get("event_hash"):
                raise ValueError("customer access history event hash mismatch")
            events.append(event)
            previous = event.event_hash
        if envelope.get("head_hash") != previous:
            raise ValueError("customer access history head hash mismatch")
        canonical = {
            "schema": 1,
            "head_hash": previous,
            "events": [
                {
                    **asdict(e),
                    "purpose": e.purpose.value,
                }
                for e in events
            ],
        }
        if envelope.get("state_hash") != canonical_hash(canonical):
            raise ValueError("customer access history state hash mismatch")
        return tuple(events)

    def events(self) -> tuple[CustomerDataAccessEvent, ...]:
        return self._read()

    def record(
        self,
        obj: CustomerDataObject,
        *,
        actor_id: str,
        purpose: CustomerDataPurpose,
        accessed_at: str,
    ) -> CustomerDataAccessEvent:
        with private_file_lock(self.lock_path):
            events = list(self._read())
            allowed = purpose in obj.allowed_purposes
            reason = (
                "Purpose is explicitly allowed by customer data inventory."
                if allowed else
                "Requested purpose is not permitted by customer data inventory."
            )
            previous = events[-1].event_hash if events else None
            event = CustomerDataAccessEvent.build(
                sequence=len(events) + 1,
                customer_id=obj.customer_id,
                object_id=obj.object_id,
                actor_id=actor_id,
                purpose=purpose,
                accessed_at=accessed_at,
                allowed=allowed,
                reason=reason,
                previous_hash=previous,
            )
            events.append(event)
            canonical = {
                "schema": 1,
                "head_hash": event.event_hash,
                "events": [
                    {**asdict(e), "purpose": e.purpose.value}
                    for e in events
                ],
            }
            envelope = {**canonical, "state_hash": canonical_hash(canonical)}
            atomic_private_write(
                self.path,
                (json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
            if not allowed:
                raise PermissionError(reason)
            return event


@dataclass(frozen=True)
class CustomerDataExportReceipt:
    export_id: str
    customer_id: str
    inventory_proof_hash: str
    archive_sha256: str
    object_ids: tuple[str, ...]
    exported_at: str
    customer_safe: bool = True

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "export_id": self.export_id,
            "customer_id": self.customer_id,
            "inventory_proof_hash": self.inventory_proof_hash,
            "archive_sha256": self.archive_sha256,
            "object_ids": list(self.object_ids),
            "exported_at": self.exported_at,
            "customer_safe": True,
        })


def export_customer_data(
    inventory: CustomerDataInventory,
    *,
    customer_root: str | Path,
    archive_path: str | Path,
    exported_at: str,
) -> CustomerDataExportReceipt:
    root = Path(customer_root).resolve()
    buffer = io.BytesIO()
    manifest_rows = []
    with zipfile.ZipFile(buffer, "w") as archive:
        for obj in inventory.objects:
            path = (root / obj.relative_path).resolve()
            if not _within(root, path) or not path.is_file() or path.is_symlink():
                raise ValueError("inventory path is unavailable or unsafe")
            if _sha(path) != obj.sha256:
                raise ValueError("customer export source hash changed")
            name = f"data/{obj.relative_path}"
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, path.read_bytes())
            manifest_rows.append({
                "object_id": obj.object_id,
                "relative_path": obj.relative_path,
                "classification": obj.classification.value,
                "sha256": obj.sha256,
                "size_bytes": obj.size_bytes,
            })
        manifest_raw = json.dumps(
            {"schema":1,"customer_id":inventory.customer_id,"objects":manifest_rows},
            sort_keys=True,separators=(",",":")
        ).encode()
        info = zipfile.ZipInfo("manifest.json", date_time=(1980,1,1,0,0,0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        archive.writestr(info, manifest_raw)
    raw = buffer.getvalue()
    atomic_private_write(Path(archive_path), raw)
    exported = normalize_utc_timestamp("exported_at", exported_at)
    archive_hash = hashlib.sha256(raw).hexdigest()
    identity = {
        "schema":1,"customer_id":inventory.customer_id,
        "inventory_proof_hash":inventory.proof_hash,
        "archive_sha256":archive_hash,
        "object_ids":[x.object_id for x in inventory.objects],
        "exported_at":exported,"customer_safe":True,
    }
    return CustomerDataExportReceipt(
        export_id="customer-data-export:" + canonical_hash(identity),
        customer_id=inventory.customer_id,
        inventory_proof_hash=inventory.proof_hash,
        archive_sha256=archive_hash,
        object_ids=tuple(x.object_id for x in inventory.objects),
        exported_at=exported,
        customer_safe=True,
    )


@dataclass(frozen=True)
class CustomerDataDeletionReceipt:
    deletion_id: str
    customer_id: str
    object_id: str
    deleted_sha256: str
    deleted_at: str
    authorized_by: str
    reason: str
    legal_hold_checked: bool
    logical_deletion_only: bool = True
    forensic_wipe_claimed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "deleted_sha256", normalize_sha256(
            "deleted_sha256", self.deleted_sha256
        ))
        object.__setattr__(
            self, "deleted_at", normalize_utc_timestamp("deleted_at", self.deleted_at)
        )
        for name in ("customer_id", "object_id", "authorized_by", "reason"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.legal_hold_checked is not True:
            raise ValueError("legal hold must be checked before deletion")
        if self.logical_deletion_only is not True or self.forensic_wipe_claimed:
            raise ValueError("deletion receipt cannot claim forensic secure wipe")
        expected = "customer-data-deletion:" + canonical_hash(self._identity())
        if self.deletion_id != expected:
            raise ValueError("deletion_id does not bind deletion receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema":1,"customer_id":self.customer_id,"object_id":self.object_id,
            "deleted_sha256":self.deleted_sha256,"deleted_at":self.deleted_at,
            "authorized_by":self.authorized_by,"reason":self.reason,
            "legal_hold_checked":True,"logical_deletion_only":True,
            "forensic_wipe_claimed":False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def delete_customer_data_object(
    obj: CustomerDataObject,
    *,
    customer_root: str | Path,
    holds: tuple[CustomerLegalHold, ...],
    deleted_at: str,
    authorized_by: str,
    reason: str,
    approved_early_deletion: bool = False,
) -> CustomerDataDeletionReceipt:
    for hold in holds:
        if (
            hold.customer_id == obj.customer_id
            and hold.active
            and obj.object_id in hold.object_ids
        ):
            raise ValueError("active legal hold prevents deletion")
    when = normalize_utc_timestamp("deleted_at", deleted_at)
    if _instant(when) < _instant(obj.retention_until) and not approved_early_deletion:
        raise ValueError("retention period has not expired")
    root = Path(customer_root).resolve()
    path = (root / obj.relative_path).resolve()
    if not _within(root, path) or path.is_symlink() or not path.is_file():
        raise ValueError("customer data object is unavailable or unsafe")
    if _sha(path) != obj.sha256:
        raise ValueError("customer data object hash changed before deletion")
    path.unlink()
    if path.exists():
        raise OSError("logical deletion did not remove managed file")
    identity = {
        "schema":1,"customer_id":obj.customer_id,"object_id":obj.object_id,
        "deleted_sha256":obj.sha256,"deleted_at":when,
        "authorized_by":_text("authorized_by",authorized_by),
        "reason":_text("reason",reason),"legal_hold_checked":True,
        "logical_deletion_only":True,"forensic_wipe_claimed":False,
    }
    return CustomerDataDeletionReceipt(
        deletion_id="customer-data-deletion:" + canonical_hash(identity),
        customer_id=obj.customer_id,object_id=obj.object_id,
        deleted_sha256=obj.sha256,deleted_at=when,
        authorized_by=authorized_by,reason=reason,legal_hold_checked=True,
        logical_deletion_only=True,forensic_wipe_claimed=False,
    )
