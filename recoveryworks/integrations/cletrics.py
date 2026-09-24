"""Hash-bound Cletrics evidence-bundle ingestion for CloudRecovery.

Cletrics is treated as an upstream collection/normalization plane. The bundle
records provenance and freezes normalized billing/meter inputs, but it cannot
self-assert RecoveryOS verification. Verification is supplied separately by
the Scan 360 caller after the underlying provider evidence has been reviewed.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping
import zipfile

from recoveryworks.branches.contract_billing import InvoiceCharge, UsageRecord
from recoveryworks.branches.cloud_signals import CloudSignal, CloudSignalType
from recoveryworks.branches.contract_billing_csv import dollars_to_cents
from recoveryworks.models import normalize_sha256, normalize_utc_timestamp


CLETRICS_BUNDLE_TYPE = "CLETRICS_RECOVERYOS_CLOUD_EVIDENCE"
CLETRICS_BUNDLE_SCHEMA = 1
MANIFEST_PATH = "manifest.json"
INVOICE_ROLE = "invoice_charges"
METER_ROLE = "meter_usage"
ANOMALY_ROLE = "anomaly_signals"
RECONCILIATION_ROLE = "reconciliation_signals"
_REQUIRED_ROLES = {INVOICE_ROLE, METER_ROLE}
_ALLOWED_ROLES = _REQUIRED_ROLES | {ANOMALY_ROLE, RECONCILIATION_ROLE}
_GIT_SHA1_RE = re.compile(r"[0-9a-f]{40}")
_IMAGE_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
_CURRENCY_RE = re.compile(r"[A-Z]{3}")

_CHARGE_COLUMNS = (
    "Charge_ID",
    "Counterparty",
    "Account_ID",
    "Service_ID",
    "Service_Date",
    "Actual_Amount",
)
_METER_COLUMNS = ("Charge_ID", "Meter_Record_ID", "Usage_Units")


@dataclass(frozen=True)
class CletricsBundleEntry:
    role: str
    path: str
    sha256: str
    size_bytes: int
    source_kind: str
    source_locator: str
    source_sha256: str
    source_acquired_at: str
    transformation_id: str | None = None


@dataclass(frozen=True)
class CletricsCloudBundle:
    client_id: str
    provider: str
    billing_account_id: str
    currency: str
    period_start: str
    period_end: str
    exported_at: str
    cletrics_release: str
    cletrics_commit: str | None
    cletrics_image_digest: str | None
    bundle_sha256: str
    manifest_sha256: str
    entries: tuple[CletricsBundleEntry, ...]
    charges: tuple[InvoiceCharge, ...]
    usage: tuple[UsageRecord, ...]
    signals: tuple[CloudSignal, ...]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    text = value.strip()
    if any(ord(character) < 32 for character in text):
        raise ValueError(f"{name} cannot contain control characters")
    return text


def _optional_text(name: str, value: Any) -> str | None:
    if value is None or value == "":
        return None
    return _required_text(name, value)


def _iso_date(name: str, value: Any) -> str:
    text = _required_text(name, value)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _currency(value: Any) -> str:
    text = _required_text("currency", value).upper()
    if _CURRENCY_RE.fullmatch(text) is None:
        raise ValueError("currency must be a three-letter code")
    return text


def _safe_archive_path(name: str) -> str:
    text = _required_text("entry.path", name)
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe Cletrics bundle path: {text!r}")
    return text


def _parse_json(raw: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _entry_from_manifest(
    raw: Mapping[str, Any], *, index: int
) -> CletricsBundleEntry:
    role = _required_text(f"entries[{index}].role", raw.get("role"))
    path = _safe_archive_path(
        _required_text(f"entries[{index}].path", raw.get("path"))
    )
    digest = normalize_sha256(
        f"entries[{index}].sha256",
        _required_text(f"entries[{index}].sha256", raw.get("sha256")),
    )
    size = raw.get("size_bytes")
    if type(size) is not int or size < 0:
        raise ValueError(
            f"entries[{index}].size_bytes must be a non-negative integer"
        )

    source = raw.get("source")
    if not isinstance(source, Mapping):
        raise ValueError(f"entries[{index}].source must be an object")
    source_kind = _required_text(
        f"entries[{index}].source.kind", source.get("kind")
    )
    source_locator = _required_text(
        f"entries[{index}].source.locator", source.get("locator")
    )
    source_sha = normalize_sha256(
        f"entries[{index}].source.sha256",
        _required_text(
            f"entries[{index}].source.sha256", source.get("sha256")
        ),
    )
    source_acquired_at = normalize_utc_timestamp(
        f"entries[{index}].source.acquired_at",
        _required_text(
            f"entries[{index}].source.acquired_at",
            source.get("acquired_at"),
        ),
    )
    transformation_id = _optional_text(
        f"entries[{index}].transformation_id",
        raw.get("transformation_id"),
    )
    return CletricsBundleEntry(
        role=role,
        path=path,
        sha256=digest,
        size_bytes=size,
        source_kind=source_kind,
        source_locator=source_locator,
        source_sha256=source_sha,
        source_acquired_at=source_acquired_at,
        transformation_id=transformation_id,
    )


def _parse_manifest(
    raw: bytes,
) -> tuple[Mapping[str, Any], tuple[CletricsBundleEntry, ...]]:
    manifest = _parse_json(raw, label=MANIFEST_PATH)
    if manifest.get("schema") != CLETRICS_BUNDLE_SCHEMA:
        raise ValueError("unsupported Cletrics bundle schema")
    if manifest.get("bundle_type") != CLETRICS_BUNDLE_TYPE:
        raise ValueError(
            "not a RecoveryOS Cletrics cloud-evidence bundle"
        )

    rows = manifest.get("entries")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "Cletrics bundle manifest entries must be a non-empty list"
        )
    entries: list[CletricsBundleEntry] = []
    seen_roles: set[str] = set()
    seen_paths: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"entries[{index}] must be an object")
        entry = _entry_from_manifest(row, index=index)
        if entry.role not in _ALLOWED_ROLES:
            raise ValueError(f"unsupported Cletrics bundle role: {entry.role}")
        if entry.role in seen_roles:
            raise ValueError(
                f"duplicate Cletrics bundle role: {entry.role}"
            )
        if entry.path in seen_paths or entry.path == MANIFEST_PATH:
            raise ValueError(
                f"duplicate/reserved Cletrics bundle path: {entry.path}"
            )
        seen_roles.add(entry.role)
        seen_paths.add(entry.path)
        entries.append(entry)
    missing = _REQUIRED_ROLES - seen_roles
    if missing:
        raise ValueError(
            "Cletrics bundle missing required roles: "
            + ", ".join(sorted(missing))
        )
    return manifest, tuple(entries)


def _decode_csv(
    raw: bytes, *, label: str
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8 CSV") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"{label} has no CSV header")
    return tuple(reader.fieldnames), list(reader)


def _require_columns(
    fieldnames: tuple[str, ...],
    required: tuple[str, ...],
    *,
    label: str,
) -> None:
    missing = [column for column in required if column not in fieldnames]
    if missing:
        raise ValueError(
            f"{label} missing required columns: {', '.join(missing)}"
        )


def _row_value(
    row: Mapping[str, str], column: str, *, row_number: int
) -> str:
    value = row.get(column)
    if value is None or not str(value).strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return str(value).strip()


def _entry_metadata(
    *,
    bundle_name: str,
    bundle_hash: str,
    manifest_hash: str,
    manifest: Mapping[str, Any],
    entry: CletricsBundleEntry,
) -> dict[str, Any]:
    cletrics = manifest["cletrics"]
    return {
        "source_file": entry.path,
        "cletrics_bundle": bundle_name,
        "cletrics_bundle_sha256": bundle_hash,
        "cletrics_manifest_sha256": manifest_hash,
        "cletrics_release": cletrics["release"],
        "cletrics_commit": cletrics.get("commit"),
        "cletrics_image_digest": cletrics.get("image_digest"),
        "provider": manifest["provider"],
        "billing_account_id": manifest["billing_account_id"],
        "period_start": manifest["period_start"],
        "period_end": manifest["period_end"],
        "provider_source_kind": entry.source_kind,
        "provider_source_locator": entry.source_locator,
        "provider_source_sha256": entry.source_sha256,
        "provider_source_acquired_at": entry.source_acquired_at,
        "transformation_id": entry.transformation_id,
        "normalized_entry_sha256": entry.sha256,
    }


def _load_charges(
    raw: bytes,
    *,
    bundle_name: str,
    bundle_hash: str,
    manifest_hash: str,
    manifest: Mapping[str, Any],
    entry: CletricsBundleEntry,
    verified: bool,
) -> tuple[InvoiceCharge, ...]:
    fieldnames, rows = _decode_csv(raw, label=entry.path)
    _require_columns(fieldnames, _CHARGE_COLUMNS, label=entry.path)
    base_meta = _entry_metadata(
        bundle_name=bundle_name,
        bundle_hash=bundle_hash,
        manifest_hash=manifest_hash,
        manifest=manifest,
        entry=entry,
    )
    result: list[InvoiceCharge] = []
    required = set(_CHARGE_COLUMNS)
    for row_number, row in enumerate(rows, start=2):
        provider_fields = {
            key: str(value).strip()
            for key, value in row.items()
            if key not in required
            and value is not None
            and str(value).strip()
        }
        result.append(
            InvoiceCharge(
                charge_id=_row_value(
                    row, "Charge_ID", row_number=row_number
                ),
                counterparty_id=_row_value(
                    row, "Counterparty", row_number=row_number
                ),
                account_id=_row_value(
                    row, "Account_ID", row_number=row_number
                ),
                service_id=_row_value(
                    row, "Service_ID", row_number=row_number
                ),
                service_date=_row_value(
                    row, "Service_Date", row_number=row_number
                ),
                actual_cents=dollars_to_cents(
                    _row_value(
                        row, "Actual_Amount", row_number=row_number
                    )
                ),
                source_hash=entry.sha256,
                source_locator=(
                    f"bundle://{bundle_name}/{entry.path}"
                    f"#row={row_number}"
                ),
                verified=verified,
                metadata={
                    **base_meta,
                    "row_number": row_number,
                    "provider_fields": provider_fields,
                },
            )
        )
    return tuple(result)


def _load_meter_usage(
    raw: bytes,
    *,
    bundle_name: str,
    bundle_hash: str,
    manifest_hash: str,
    manifest: Mapping[str, Any],
    entry: CletricsBundleEntry,
    verified: bool,
) -> tuple[UsageRecord, ...]:
    fieldnames, rows = _decode_csv(raw, label=entry.path)
    _require_columns(fieldnames, _METER_COLUMNS, label=entry.path)
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    rows_by_charge: dict[str, list[int]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        charge_id = _row_value(
            row, "Charge_ID", row_number=row_number
        )
        meter_id = _row_value(
            row, "Meter_Record_ID", row_number=row_number
        )
        key = (charge_id, meter_id)
        if key in seen:
            raise ValueError(
                f"row {row_number}: duplicate meter record "
                f"{meter_id!r} for charge {charge_id!r}"
            )
        seen.add(key)
        raw_units = _row_value(
            row, "Usage_Units", row_number=row_number
        )
        try:
            units = Decimal(raw_units)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"row {row_number}: Usage_Units must be numeric"
            ) from exc
        if units < 0:
            raise ValueError(
                f"row {row_number}: Usage_Units must be non-negative"
            )
        totals[charge_id] += units
        rows_by_charge[charge_id].append(row_number)

    base_meta = _entry_metadata(
        bundle_name=bundle_name,
        bundle_hash=bundle_hash,
        manifest_hash=manifest_hash,
        manifest=manifest,
        entry=entry,
    )
    result: list[UsageRecord] = []
    for charge_id in sorted(rows_by_charge):
        result.append(
            UsageRecord(
                charge_id=charge_id,
                units=str(totals[charge_id]),
                source_hash=entry.sha256,
                source_locator=(
                    f"bundle://{bundle_name}/{entry.path}"
                    f"#charge_id={charge_id}"
                ),
                verified=verified,
                metadata={
                    **base_meta,
                    "meter_rows": rows_by_charge[charge_id],
                    "meter_record_count": len(
                        rows_by_charge[charge_id]
                    ),
                    "quantity_basis": (
                        "cletrics_normalized_independent_meter_usage"
                    ),
                },
            )
        )
    return tuple(result)



def _optional_decimal(row: Mapping[str, str], column: str, *, row_number: int) -> Decimal | None:
    raw = (row.get(column) or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"row {row_number}: {column} must be numeric") from exc


def _signal_timestamp(value: str, *, row_number: int) -> str:
    raw = value.strip()
    if len(raw) == 10:
        raw = raw + "T00:00:00Z"
    return normalize_utc_timestamp(f"row {row_number} Detected_At", raw)


def _signal_id(
    supplied: str,
    *,
    signal_type: CloudSignalType,
    provider: str,
    account_id: str,
    service_id: str,
    detected_at: str,
    source_hash: str,
    row_number: int,
) -> str:
    if supplied.strip():
        return supplied.strip()
    identity = {
        "provider": provider,
        "account_id": account_id,
        "service_id": service_id,
        "detected_at": detected_at,
        "source_hash": source_hash,
        "row_number": row_number,
    }
    return (
        "cletrics:"
        + signal_type.value.lower()
        + ":"
        + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )


def _load_anomaly_signals(
    raw: bytes,
    *,
    bundle_name: str,
    manifest: Mapping[str, Any],
    entry: CletricsBundleEntry,
) -> tuple[CloudSignal, ...]:
    fieldnames, rows = _decode_csv(raw, label=entry.path)
    required = (
        "Detected_At",
        "Provider",
        "Account_ID",
        "Service_ID",
        "Severity",
        "Detection_Method",
        "Metric_Name",
    )
    _require_columns(fieldnames, required, label=entry.path)
    result: list[CloudSignal] = []
    for row_number, row in enumerate(rows, start=2):
        provider = (row.get("Provider") or "").strip() or str(manifest["provider"])
        account_id = (row.get("Account_ID") or "").strip() or str(
            manifest["billing_account_id"]
        )
        service_id = _row_value(row, "Service_ID", row_number=row_number)
        detected_at = _signal_timestamp(
            _row_value(row, "Detected_At", row_number=row_number),
            row_number=row_number,
        )
        impact = _optional_decimal(
            row, "Estimated_Cost_Impact", row_number=row_number
        )
        if impact is not None and impact < 0:
            raise ValueError(
                f"row {row_number}: Estimated_Cost_Impact must be non-negative"
            )
        impact_cents = (
            int((impact * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            if impact is not None
            else None
        )
        confidence_raw = (row.get("Confidence") or "").strip() or None
        result.append(
            CloudSignal(
                signal_id=_signal_id(
                    (row.get("Signal_ID") or ""),
                    signal_type=CloudSignalType.ANOMALY,
                    provider=provider,
                    account_id=account_id,
                    service_id=service_id,
                    detected_at=detected_at,
                    source_hash=entry.sha256,
                    row_number=row_number,
                ),
                signal_type=CloudSignalType.ANOMALY,
                provider=provider,
                account_id=account_id,
                service_id=service_id,
                detected_at=detected_at,
                detection_method=_row_value(
                    row, "Detection_Method", row_number=row_number
                ),
                source_hash=entry.sha256,
                source_locator=(
                    f"bundle://{bundle_name}/{entry.path}#row={row_number}"
                ),
                severity=(row.get("Severity") or "").strip() or None,
                resource_id=(row.get("Resource_ID") or "").strip() or None,
                region=(row.get("Region") or "").strip() or None,
                estimated_impact_cents=impact_cents,
                confidence=confidence_raw,
                metadata={
                    "metric_name": _row_value(
                        row, "Metric_Name", row_number=row_number
                    ),
                    "z_score": (row.get("Z_Score") or "").strip() or None,
                    "baseline_value": (row.get("Baseline_Value") or "").strip()
                    or None,
                    "actual_value": (row.get("Actual_Value") or "").strip()
                    or None,
                    "cletrics_source_role": ANOMALY_ROLE,
                    "estimated_amount_is_non_authoritative": True,
                },
            )
        )
    return tuple(result)


def _load_reconciliation_signals(
    raw: bytes,
    *,
    bundle_name: str,
    manifest: Mapping[str, Any],
    entry: CletricsBundleEntry,
) -> tuple[CloudSignal, ...]:
    fieldnames, rows = _decode_csv(raw, label=entry.path)
    required = (
        "Detected_At",
        "Provider",
        "Account_ID",
        "Service_ID",
        "Estimated_Cost",
        "Actual_Cost",
    )
    _require_columns(fieldnames, required, label=entry.path)
    result: list[CloudSignal] = []
    for row_number, row in enumerate(rows, start=2):
        provider = (row.get("Provider") or "").strip() or str(manifest["provider"])
        account_id = (row.get("Account_ID") or "").strip() or str(
            manifest["billing_account_id"]
        )
        service_id = _row_value(row, "Service_ID", row_number=row_number)
        detected_at = _signal_timestamp(
            _row_value(row, "Detected_At", row_number=row_number),
            row_number=row_number,
        )
        estimated = _optional_decimal(row, "Estimated_Cost", row_number=row_number)
        actual = _optional_decimal(row, "Actual_Cost", row_number=row_number)
        if estimated is None or actual is None or estimated < 0 or actual < 0:
            raise ValueError(
                f"row {row_number}: reconciliation costs must be non-negative numerics"
            )
        impact_cents = int(
            (abs(actual - estimated) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        result.append(
            CloudSignal(
                signal_id=_signal_id(
                    (row.get("Signal_ID") or ""),
                    signal_type=CloudSignalType.RECONCILIATION_DRIFT,
                    provider=provider,
                    account_id=account_id,
                    service_id=service_id,
                    detected_at=detected_at,
                    source_hash=entry.sha256,
                    row_number=row_number,
                ),
                signal_type=CloudSignalType.RECONCILIATION_DRIFT,
                provider=provider,
                account_id=account_id,
                service_id=service_id,
                detected_at=detected_at,
                detection_method="billing_reconciliation",
                source_hash=entry.sha256,
                source_locator=(
                    f"bundle://{bundle_name}/{entry.path}#row={row_number}"
                ),
                estimated_impact_cents=impact_cents,
                metadata={
                    "estimated_cost": str(estimated),
                    "actual_cost": str(actual),
                    "error_pct": (row.get("Error_Pct") or "").strip() or None,
                    "drift_direction": (row.get("Drift_Direction") or "").strip()
                    or None,
                    "sku_key": (row.get("SKU_Key") or "").strip() or None,
                    "cletrics_source_role": RECONCILIATION_ROLE,
                    "estimated_amount_is_non_authoritative": True,
                },
            )
        )
    return tuple(result)

def load_cletrics_bundle(
    path: str | Path,
    *,
    charge_source_verified: bool = False,
    meter_source_verified: bool = False,
) -> CletricsCloudBundle:
    """Load and verify a frozen Cletrics -> RecoveryOS evidence bundle.

    ZIP/manifest integrity proves which normalized data was supplied. It does
    not prove that provider evidence is authoritative. The verification flags
    are deliberately external to the bundle so Cletrics cannot promote its own
    data to VALIDATED status.
    """
    if (
        type(charge_source_verified) is not bool
        or type(meter_source_verified) is not bool
    ):
        raise ValueError(
            "Cletrics source verification flags must be boolean"
        )

    source = Path(path)
    bundle_raw = source.read_bytes()
    bundle_hash = _sha(bundle_raw)
    try:
        archive = zipfile.ZipFile(source, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"{source} is not a valid ZIP archive"
        ) from exc

    with archive:
        names = archive.namelist()
        file_names = [
            name for name in names if not name.endswith("/")
        ]
        if len(file_names) != len(set(file_names)):
            raise ValueError("duplicate Cletrics bundle entry")
        for name in file_names:
            _safe_archive_path(name)
        if MANIFEST_PATH not in file_names:
            raise ValueError(
                "Cletrics bundle missing manifest.json"
            )

        manifest_raw = archive.read(MANIFEST_PATH)
        manifest_hash = _sha(manifest_raw)
        manifest, entries = _parse_manifest(manifest_raw)

        client_id = _required_text(
            "client_id", manifest.get("client_id")
        )
        provider = _required_text(
            "provider", manifest.get("provider")
        )
        billing_account_id = _required_text(
            "billing_account_id",
            manifest.get("billing_account_id"),
        )
        currency = _currency(manifest.get("currency"))
        period_start = _iso_date(
            "period_start", manifest.get("period_start")
        )
        period_end = _iso_date(
            "period_end", manifest.get("period_end")
        )
        if period_end < period_start:
            raise ValueError(
                "period_end cannot predate period_start"
            )
        exported_at = normalize_utc_timestamp(
            "exported_at",
            _required_text(
                "exported_at", manifest.get("exported_at")
            ),
        )

        cletrics = manifest.get("cletrics")
        if not isinstance(cletrics, Mapping):
            raise ValueError(
                "cletrics manifest identity must be an object"
            )
        release = _required_text(
            "cletrics.release", cletrics.get("release")
        )
        commit = _optional_text(
            "cletrics.commit", cletrics.get("commit")
        )
        image_digest = _optional_text(
            "cletrics.image_digest",
            cletrics.get("image_digest"),
        )
        if commit is None and image_digest is None:
            raise ValueError(
                "Cletrics bundle requires commit or image_digest identity"
            )
        if (
            commit is not None
            and _GIT_SHA1_RE.fullmatch(commit.lower()) is None
        ):
            raise ValueError(
                "cletrics.commit must be a full 40-character Git SHA"
            )
        if commit is not None:
            commit = commit.lower()
        if (
            image_digest is not None
            and _IMAGE_DIGEST_RE.fullmatch(
                image_digest.lower()
            )
            is None
        ):
            raise ValueError(
                "cletrics.image_digest must be "
                "sha256:<64 lowercase hex>"
            )
        if image_digest is not None:
            image_digest = image_digest.lower()

        expected_files = {
            MANIFEST_PATH,
            *(entry.path for entry in entries),
        }
        if set(file_names) != expected_files:
            extra = sorted(set(file_names) - expected_files)
            missing = sorted(expected_files - set(file_names))
            detail = []
            if missing:
                detail.append(
                    "missing=" + ",".join(missing)
                )
            if extra:
                detail.append(
                    "unmanifested=" + ",".join(extra)
                )
            raise ValueError(
                "Cletrics bundle file-set mismatch: "
                + "; ".join(detail)
            )

        entry_raw: dict[str, bytes] = {}
        for entry in entries:
            raw = archive.read(entry.path)
            if _sha(raw) != entry.sha256:
                raise ValueError(
                    f"Cletrics bundle hash mismatch: {entry.path}"
                )
            if len(raw) != entry.size_bytes:
                raise ValueError(
                    f"Cletrics bundle size mismatch: {entry.path}"
                )
            entry_raw[entry.role] = raw

        normalized_manifest = dict(manifest)
        normalized_manifest.update(
            {
                "client_id": client_id,
                "provider": provider,
                "billing_account_id": billing_account_id,
                "currency": currency,
                "period_start": period_start,
                "period_end": period_end,
                "exported_at": exported_at,
                "cletrics": {
                    "release": release,
                    "commit": commit,
                    "image_digest": image_digest,
                },
            }
        )
        by_role = {entry.role: entry for entry in entries}
        charges = _load_charges(
            entry_raw[INVOICE_ROLE],
            bundle_name=source.name,
            bundle_hash=bundle_hash,
            manifest_hash=manifest_hash,
            manifest=normalized_manifest,
            entry=by_role[INVOICE_ROLE],
            verified=charge_source_verified,
        )
        usage = _load_meter_usage(
            entry_raw[METER_ROLE],
            bundle_name=source.name,
            bundle_hash=bundle_hash,
            manifest_hash=manifest_hash,
            manifest=normalized_manifest,
            entry=by_role[METER_ROLE],
            verified=meter_source_verified,
        )
        signal_rows: list[CloudSignal] = []
        if ANOMALY_ROLE in by_role:
            signal_rows.extend(
                _load_anomaly_signals(
                    entry_raw[ANOMALY_ROLE],
                    bundle_name=source.name,
                    manifest=normalized_manifest,
                    entry=by_role[ANOMALY_ROLE],
                )
            )
        if RECONCILIATION_ROLE in by_role:
            signal_rows.extend(
                _load_reconciliation_signals(
                    entry_raw[RECONCILIATION_ROLE],
                    bundle_name=source.name,
                    manifest=normalized_manifest,
                    entry=by_role[RECONCILIATION_ROLE],
                )
            )
        signal_index: dict[str, CloudSignal] = {}
        for signal in signal_rows:
            previous = signal_index.get(signal.signal_id)
            if previous is not None and previous.proof_hash != signal.proof_hash:
                raise ValueError(
                    f"conflicting Cletrics signal_id: {signal.signal_id}"
                )
            signal_index[signal.signal_id] = signal
        signals = tuple(signal_index[key] for key in sorted(signal_index))

    return CletricsCloudBundle(
        client_id=client_id,
        provider=provider,
        billing_account_id=billing_account_id,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        exported_at=exported_at,
        cletrics_release=release,
        cletrics_commit=commit,
        cletrics_image_digest=image_digest,
        bundle_sha256=bundle_hash,
        manifest_sha256=manifest_hash,
        entries=entries,
        charges=charges,
        usage=usage,
        signals=signals,
    )
