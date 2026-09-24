"""Export Cletrics FOCUS + independent usage into a RecoveryOS evidence bundle.

The bridge consumes Cletrics' FOCUS cost export as billed-cost evidence and a
separate meter export as quantity evidence. Optional anomaly, reconciliation,
and savings CSVs are carried into the existing non-money signal plane.

The module is intentionally stdlib-only so it can run beside a self-hosted
Cletrics deployment without adding a runtime dependency to RecoveryOS.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Mapping
import zipfile

from recoveryworks.models import canonical_hash, normalize_utc_timestamp
from recoveryworks.cloud_provider import canonical_cloud_provider
from .cletrics import (
    ANOMALY_ROLE,
    CLETRICS_BUNDLE_SCHEMA,
    CLETRICS_BUNDLE_TYPE,
    INVOICE_ROLE,
    METER_ROLE,
    RECONCILIATION_ROLE,
    SAVINGS_ROLE,
)


@dataclass(frozen=True)
class CletricsSourceArtifact:
    path: Path
    kind: str
    locator: str
    acquired_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        for name in ("kind", "locator"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(
            self,
            "acquired_at",
            normalize_utc_timestamp("acquired_at", self.acquired_at),
        )


@dataclass(frozen=True)
class FocusExportMapping:
    charge_id: str = "ChargeId"
    provider: str = "ProviderName"
    billing_account: str = "BillingAccountId"
    service: str = "ServiceName"
    charge_period_start: str = "ChargePeriodStart"
    billed_cost: str = "BilledCost"
    billing_currency: str = "BillingCurrency"
    resource_id: str = "ResourceId"
    region: str = "RegionId"
    sku_id: str = "SkuId"
    invoice_id: str = "InvoiceId"
    consumed_quantity: str = "ConsumedQuantity"
    consumed_unit: str = "ConsumedUnit"
    effective_cost: str = "EffectiveCost"
    list_cost: str = "ListCost"
    contracted_cost: str = "ContractedCost"


@dataclass(frozen=True)
class CletricsExportReceipt:
    output_path: str
    bundle_sha256: str
    manifest_sha256: str
    charge_count: int
    meter_record_count: int
    signal_roles: tuple[str, ...]
    provider: str
    billing_account_id: str
    currency: str
    period_start: str
    period_end: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "bundle_sha256": self.bundle_sha256,
            "manifest_sha256": self.manifest_sha256,
            "charge_count": self.charge_count,
            "meter_record_count": self.meter_record_count,
            "signal_roles": list(self.signal_roles),
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "currency": self.currency,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_csv(source: CletricsSourceArtifact) -> tuple[bytes, tuple[str, ...], list[dict[str, str]]]:
    raw = source.path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source.path} must be UTF-8 CSV") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"{source.path} has no CSV header")
    return raw, tuple(reader.fieldnames), list(reader)


def _required(row: Mapping[str, str], column: str, *, row_number: int) -> str:
    value = row.get(column)
    if value is None or not str(value).strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return str(value).strip()


def _optional(row: Mapping[str, str], column: str) -> str | None:
    value = row.get(column)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _iso_date(name: str, value: str) -> str:
    text = value.strip()
    candidate = text[:10]
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must begin with YYYY-MM-DD") from exc


def _canonical_row_hash(row: Mapping[str, str]) -> str:
    payload = {
        str(key): "" if value is None else str(value)
        for key, value in sorted(row.items())
        if key is not None
    }
    return canonical_hash(payload)


def _csv_bytes(fieldnames: tuple[str, ...], rows: list[Mapping[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(fieldnames),
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return buffer.getvalue().encode("utf-8")


def _normalize_focus_charges(
    source: CletricsSourceArtifact,
    *,
    mapping: FocusExportMapping,
    provider_override: str | None,
    billing_account_override: str | None,
    currency_override: str | None,
) -> tuple[bytes, dict[str, str], dict[tuple[str, str, str], str], str, str, str]:
    raw, fieldnames, rows = _read_csv(source)
    required_columns = (
        mapping.provider,
        mapping.billing_account,
        mapping.service,
        mapping.charge_period_start,
        mapping.billed_cost,
        mapping.billing_currency,
    )
    missing = [name for name in required_columns if name not in fieldnames]
    if missing:
        raise ValueError(
            "Cletrics FOCUS export missing required columns: " + ", ".join(missing)
        )
    normalized_rows: list[dict[str, Any]] = []
    row_hash_to_charge: dict[str, str] = {}
    natural_key_to_charge: dict[tuple[str, str, str], str] = {}
    providers: set[str] = set()
    accounts: set[str] = set()
    currencies: set[str] = set()
    seen_charge_ids: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        provider_name = provider_override or _required(
            row, mapping.provider, row_number=row_number
        )
        account_id = billing_account_override or _required(
            row, mapping.billing_account, row_number=row_number
        )
        service_id = _required(row, mapping.service, row_number=row_number)
        service_date = _iso_date(
            mapping.charge_period_start,
            _required(row, mapping.charge_period_start, row_number=row_number),
        )
        billed_cost = _required(row, mapping.billed_cost, row_number=row_number)
        currency = (
            currency_override
            or _required(row, mapping.billing_currency, row_number=row_number)
        ).upper()

        row_hash = _canonical_row_hash(row)
        supplied_charge_id = _optional(row, mapping.charge_id)
        charge_id = supplied_charge_id or f"focus:{row_hash}"
        if charge_id in seen_charge_ids:
            raise ValueError(
                f"row {row_number}: duplicate FOCUS charge identity {charge_id!r}"
            )
        seen_charge_ids.add(charge_id)
        row_hash_to_charge[row_hash] = charge_id

        resource_id = _optional(row, mapping.resource_id)
        if resource_id:
            key = (resource_id, service_id, service_date)
            if key in natural_key_to_charge:
                natural_key_to_charge[key] = ""
            else:
                natural_key_to_charge[key] = charge_id

        providers.add(canonical_cloud_provider(provider_name))
        accounts.add(account_id)
        currencies.add(currency)
        normalized_rows.append({
            "Charge_ID": charge_id,
            "Counterparty": provider_name,
            "Account_ID": account_id,
            "Service_ID": service_id,
            "Service_Date": service_date,
            "Actual_Amount": billed_cost,
            "FOCUS_Row_Hash": row_hash,
            "Provider_Line_ID": supplied_charge_id or "",
            "Resource_ID": resource_id or "",
            "Region": _optional(row, mapping.region) or "",
            "SKU_ID": _optional(row, mapping.sku_id) or "",
            "Invoice_ID": _optional(row, mapping.invoice_id) or "",
            "Consumed_Quantity": _optional(row, mapping.consumed_quantity) or "",
            "Consumed_Unit": _optional(row, mapping.consumed_unit) or "",
            "Effective_Cost": _optional(row, mapping.effective_cost) or "",
            "List_Cost": _optional(row, mapping.list_cost) or "",
            "Contracted_Cost": _optional(row, mapping.contracted_cost) or "",
        })

    if not normalized_rows:
        raise ValueError("Cletrics FOCUS export contains no billing rows")
    if len(providers) != 1:
        raise ValueError("FOCUS export must resolve to one provider per RecoveryOS bundle")
    if len(accounts) != 1:
        raise ValueError(
            "FOCUS export must resolve to one billing account per RecoveryOS bundle"
        )
    if len(currencies) != 1:
        raise ValueError("FOCUS export must resolve to one currency per RecoveryOS bundle")

    fields = (
        "Charge_ID",
        "Counterparty",
        "Account_ID",
        "Service_ID",
        "Service_Date",
        "Actual_Amount",
        "FOCUS_Row_Hash",
        "Provider_Line_ID",
        "Resource_ID",
        "Region",
        "SKU_ID",
        "Invoice_ID",
        "Consumed_Quantity",
        "Consumed_Unit",
        "Effective_Cost",
        "List_Cost",
        "Contracted_Cost",
    )
    return (
        _csv_bytes(fields, normalized_rows),
        row_hash_to_charge,
        natural_key_to_charge,
        next(iter(providers)),
        next(iter(accounts)),
        next(iter(currencies)),
    )


def _normalize_meter(
    source: CletricsSourceArtifact,
    *,
    row_hash_to_charge: Mapping[str, str],
    natural_key_to_charge: Mapping[tuple[str, str, str], str],
) -> tuple[bytes, int]:
    _raw, fieldnames, rows = _read_csv(source)
    required = {"Meter_Record_ID", "Usage_Units"}
    missing = sorted(required - set(fieldnames))
    if missing:
        raise ValueError(
            "Cletrics independent meter export missing required columns: "
            + ", ".join(missing)
        )
    normalized: list[dict[str, str]] = []
    seen_meter_ids: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        charge_id = (_optional(row, "Charge_ID") or "").strip()
        if not charge_id:
            row_hash = (_optional(row, "FOCUS_Row_Hash") or "").strip()
            if row_hash:
                charge_id = row_hash_to_charge.get(row_hash, "")
        if not charge_id:
            resource_id = (_optional(row, "ResourceId") or _optional(row, "Resource_ID") or "")
            service_id = (_optional(row, "ServiceName") or _optional(row, "Service_ID") or "")
            usage_date_raw = (_optional(row, "UsageDate") or _optional(row, "Service_Date") or "")
            if resource_id and service_id and usage_date_raw:
                key = (resource_id, service_id, _iso_date("UsageDate", usage_date_raw))
                charge_id = natural_key_to_charge.get(key, "")
                if charge_id == "":
                    raise ValueError(
                        f"row {row_number}: meter natural key is ambiguous or unmatched"
                    )
        if not charge_id:
            raise ValueError(
                f"row {row_number}: meter row cannot be bound to a FOCUS charge"
            )

        meter_id = _required(row, "Meter_Record_ID", row_number=row_number)
        usage_units = _required(row, "Usage_Units", row_number=row_number)
        identity = (charge_id, meter_id)
        if identity in seen_meter_ids:
            raise ValueError(
                f"row {row_number}: duplicate meter identity {charge_id}/{meter_id}"
            )
        seen_meter_ids.add(identity)
        normalized.append({
            "Charge_ID": charge_id,
            "Meter_Record_ID": meter_id,
            "Usage_Units": usage_units,
            "Resource_ID": _optional(row, "ResourceId") or _optional(row, "Resource_ID") or "",
        })
    return (
        _csv_bytes(
            ("Charge_ID", "Meter_Record_ID", "Usage_Units", "Resource_ID"),
            normalized,
        ),
        len(normalized),
    )


_SIGNAL_HEADERS: dict[str, tuple[str, ...]] = {
    ANOMALY_ROLE: (
        "Detected_At",
        "Provider",
        "Account_ID",
        "Service_ID",
        "Severity",
        "Detection_Method",
        "Metric_Name",
    ),
    RECONCILIATION_ROLE: (
        "Detected_At",
        "Provider",
        "Account_ID",
        "Service_ID",
        "Estimated_Cost",
        "Actual_Cost",
    ),
    SAVINGS_ROLE: (
        "Detected_At",
        "Provider",
        "Account_ID",
        "Service_ID",
        "Savings_Category",
        "Estimated_Savings",
        "Recommendation",
        "Remediation_Action",
    ),
}


def _validate_signal_source(role: str, source: CletricsSourceArtifact) -> bytes:
    raw, fields, _rows = _read_csv(source)
    missing = [name for name in _SIGNAL_HEADERS[role] if name not in fields]
    if missing:
        raise ValueError(
            f"{role} CSV missing required columns: " + ", ".join(missing)
        )
    return raw


def _entry(
    *,
    role: str,
    path: str,
    normalized_raw: bytes,
    source: CletricsSourceArtifact,
    transformation_id: str,
) -> dict[str, Any]:
    source_raw = source.path.read_bytes()
    return {
        "role": role,
        "path": path,
        "sha256": _sha(normalized_raw),
        "size_bytes": len(normalized_raw),
        "transformation_id": transformation_id,
        "source": {
            "kind": source.kind,
            "locator": source.locator,
            "sha256": _sha(source_raw),
            "acquired_at": source.acquired_at,
        },
    }


def _write_zip_entry(archive: zipfile.ZipFile, name: str, raw: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, raw)


def export_cletrics_focus_snapshot(
    *,
    output_path: str | Path,
    client_id: str,
    focus: CletricsSourceArtifact,
    meter: CletricsSourceArtifact,
    cletrics_release: str,
    exported_at: str,
    cletrics_commit: str | None = None,
    cletrics_image_digest: str | None = None,
    anomaly: CletricsSourceArtifact | None = None,
    reconciliation: CletricsSourceArtifact | None = None,
    savings: CletricsSourceArtifact | None = None,
    mapping: FocusExportMapping = FocusExportMapping(),
    provider: str | None = None,
    billing_account_id: str | None = None,
    currency: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> CletricsExportReceipt:
    """Create a deterministic RecoveryOS Cletrics bundle from a FOCUS snapshot."""
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("client_id is required")
    if not isinstance(cletrics_release, str) or not cletrics_release.strip():
        raise ValueError("cletrics_release is required")
    exported_at = normalize_utc_timestamp("exported_at", exported_at)
    if not cletrics_commit and not cletrics_image_digest:
        raise ValueError("Cletrics commit or image digest identity is required")

    (
        charges_raw,
        row_hash_to_charge,
        natural_key_to_charge,
        derived_provider,
        derived_account,
        derived_currency,
    ) = _normalize_focus_charges(
        focus,
        mapping=mapping,
        provider_override=provider,
        billing_account_override=billing_account_id,
        currency_override=currency,
    )
    meter_raw, meter_record_count = _normalize_meter(
        meter,
        row_hash_to_charge=row_hash_to_charge,
        natural_key_to_charge=natural_key_to_charge,
    )

    # The bundle period is explicit so a source system cannot silently infer a
    # different accounting window from row ordering or sparse usage.
    if not period_start or not period_end:
        raise ValueError("period_start and period_end are required")
    period_start = _iso_date("period_start", period_start)
    period_end = _iso_date("period_end", period_end)
    if period_end < period_start:
        raise ValueError("period_end cannot predate period_start")

    entries: list[dict[str, Any]] = [
        _entry(
            role=INVOICE_ROLE,
            path="billing/charges.csv",
            normalized_raw=charges_raw,
            source=focus,
            transformation_id="cletrics-focus-to-recoveryos-v1",
        ),
        _entry(
            role=METER_ROLE,
            path="usage/meter.csv",
            normalized_raw=meter_raw,
            source=meter,
            transformation_id="cletrics-independent-meter-to-recoveryos-v1",
        ),
    ]
    payloads: dict[str, bytes] = {
        "billing/charges.csv": charges_raw,
        "usage/meter.csv": meter_raw,
    }
    optional_sources = (
        (ANOMALY_ROLE, "signals/anomaly.csv", anomaly),
        (RECONCILIATION_ROLE, "signals/reconciliation.csv", reconciliation),
        (SAVINGS_ROLE, "signals/savings.csv", savings),
    )
    signal_roles: list[str] = []
    for role, entry_path, source in optional_sources:
        if source is None:
            continue
        raw = _validate_signal_source(role, source)
        entries.append(
            _entry(
                role=role,
                path=entry_path,
                normalized_raw=raw,
                source=source,
                transformation_id=f"cletrics-{role}-passthrough-v1",
            )
        )
        payloads[entry_path] = raw
        signal_roles.append(role)

    entries.sort(key=lambda row: row["role"])
    manifest = {
        "schema": CLETRICS_BUNDLE_SCHEMA,
        "bundle_type": CLETRICS_BUNDLE_TYPE,
        "client_id": client_id.strip(),
        "provider": derived_provider,
        "billing_account_id": derived_account,
        "currency": derived_currency,
        "period_start": period_start,
        "period_end": period_end,
        "exported_at": exported_at,
        "cletrics": {
            "release": cletrics_release.strip(),
            "commit": cletrics_commit,
            "image_digest": cletrics_image_digest,
        },
        "entries": entries,
    }
    manifest_raw = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w") as archive:
        _write_zip_entry(archive, "manifest.json", manifest_raw)
        for name in sorted(payloads):
            _write_zip_entry(archive, name, payloads[name])

    bundle_raw = destination.read_bytes()
    return CletricsExportReceipt(
        output_path=str(destination),
        bundle_sha256=_sha(bundle_raw),
        manifest_sha256=_sha(manifest_raw),
        charge_count=len(row_hash_to_charge),
        meter_record_count=meter_record_count,
        signal_roles=tuple(sorted(signal_roles)),
        provider=derived_provider,
        billing_account_id=derived_account,
        currency=derived_currency,
        period_start=period_start,
        period_end=period_end,
    )


def _artifact(path: str, kind: str, acquired_at: str) -> CletricsSourceArtifact:
    source = Path(path)
    return CletricsSourceArtifact(
        path=source,
        kind=kind,
        locator=f"file://{source.name}",
        acquired_at=acquired_at,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export Cletrics FOCUS/usage data into a RecoveryOS evidence bundle."
    )
    parser.add_argument("--focus", required=True)
    parser.add_argument("--meter", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--cletrics-release", required=True)
    parser.add_argument("--cletrics-commit")
    parser.add_argument("--cletrics-image-digest")
    parser.add_argument("--exported-at", required=True)
    parser.add_argument("--period-start", required=True)
    parser.add_argument("--period-end", required=True)
    parser.add_argument("--anomaly")
    parser.add_argument("--reconciliation")
    parser.add_argument("--savings")
    args = parser.parse_args(argv)

    kwargs: dict[str, Any] = {}
    for name, role in (
        ("anomaly", "cletrics_anomaly_output"),
        ("reconciliation", "cletrics_reconciliation_output"),
        ("savings", "cletrics_savings_output"),
    ):
        value = getattr(args, name)
        if value:
            kwargs[name] = _artifact(value, role, args.exported_at)

    receipt = export_cletrics_focus_snapshot(
        output_path=args.output,
        client_id=args.client_id,
        focus=_artifact(args.focus, "cletrics_focus_export", args.exported_at),
        meter=_artifact(args.meter, "cletrics_independent_meter_export", args.exported_at),
        cletrics_release=args.cletrics_release,
        cletrics_commit=args.cletrics_commit,
        cletrics_image_digest=args.cletrics_image_digest,
        exported_at=args.exported_at,
        period_start=args.period_start,
        period_end=args.period_end,
        **kwargs,
    )
    print(json.dumps(receipt.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
