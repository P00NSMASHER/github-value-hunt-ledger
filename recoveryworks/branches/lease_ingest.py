"""End-to-end LeaseRecovery file ingestion into a frozen RecoveryOS scan."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

from recoveryworks.models import Branch, canonical_hash
from recoveryworks.scan import RecoveryScanBatch, SourceManifestEntry, freeze_scan, run_scan

from .contract_billing import ContractBillingBatch
from .contract_billing_csv import (
    DEFAULT_CHARGE_COLUMNS,
    DEFAULT_RATE_COLUMNS,
    DEFAULT_USAGE_COLUMNS,
    load_contract_rates_csv,
    load_invoice_charges_csv,
    load_usage_csv,
)
from .lease import audit_lease_billing
from .lease_csv import DEFAULT_AREA_COLUMNS, load_lease_area_csv


@dataclass(frozen=True)
class LeaseIngestionResult:
    scan: RecoveryScanBatch
    audit: ContractBillingBatch
    charge_count: int
    rate_count: int
    quantity_count: int


def _file_hash(path: str | Path) -> tuple[Path, str]:
    source = Path(path)
    raw = source.read_bytes()
    return source, hashlib.sha256(raw).hexdigest()


def ingest_lease_exports(
    *,
    client_id: str,
    charges_path: str | Path,
    rates_path: str | Path,
    area_path: str | Path | None = None,
    usage_path: str | Path | None = None,
    verified_charges: bool = False,
    verified_rates: bool = False,
    verified_area: bool = False,
    verified_usage: bool = False,
    currency: str = "USD",
    scan_id: str | None = None,
    charge_columns: Mapping[str, str] = DEFAULT_CHARGE_COLUMNS,
    rate_columns: Mapping[str, str] = DEFAULT_RATE_COLUMNS,
    area_columns: Mapping[str, str] = DEFAULT_AREA_COLUMNS,
    usage_columns: Mapping[str, str] = DEFAULT_USAGE_COLUMNS,
) -> LeaseIngestionResult:
    """Load landlord charges, lease rates, and independent quantity evidence.

    Exactly one of area_path or usage_path may be supplied. Fixed-only lease
    rates do not require either. Area/usage-based rates fail closed when the
    corresponding quantity evidence is missing.
    """
    if area_path is not None and usage_path is not None:
        raise ValueError("provide only one of area_path or usage_path")

    charges = load_invoice_charges_csv(
        charges_path,
        verified=verified_charges,
        columns=charge_columns,
    )
    rates = load_contract_rates_csv(
        rates_path,
        verified=verified_rates,
        columns=rate_columns,
    )

    quantity = ()
    if area_path is not None:
        quantity = load_lease_area_csv(
            area_path,
            verified=verified_area,
            columns=area_columns,
        )
    elif usage_path is not None:
        quantity = load_usage_csv(
            usage_path,
            verified=verified_usage,
            columns=usage_columns,
        )

    audit = audit_lease_billing(
        client_id=client_id,
        charges=charges,
        rates=rates,
        area=quantity,
        currency=currency,
    )

    charge_source, charge_hash = _file_hash(charges_path)
    rate_source, rate_hash = _file_hash(rates_path)
    sources = [
        SourceManifestEntry(
            source_id="lease:charges",
            branch=Branch.LEASE,
            source_hash=charge_hash,
            locator=f"file://{charge_source.name}",
            kind="lease_charge_export",
        ),
        SourceManifestEntry(
            source_id="lease:rates",
            branch=Branch.LEASE,
            source_hash=rate_hash,
            locator=f"file://{rate_source.name}",
            kind="lease_rate_schedule",
        ),
    ]
    identity = [
        {"kind": "charges", "hash": charge_hash},
        {"kind": "rates", "hash": rate_hash},
    ]

    if area_path is not None:
        area_source, area_hash = _file_hash(area_path)
        sources.append(SourceManifestEntry(
            source_id="lease:area",
            branch=Branch.LEASE,
            source_hash=area_hash,
            locator=f"file://{area_source.name}",
            kind="lease_area_snapshot",
        ))
        identity.append({"kind": "area", "hash": area_hash})
    elif usage_path is not None:
        usage_source, usage_hash = _file_hash(usage_path)
        sources.append(SourceManifestEntry(
            source_id="lease:usage",
            branch=Branch.LEASE,
            source_hash=usage_hash,
            locator=f"file://{usage_source.name}",
            kind="lease_allocation_usage",
        ))
        identity.append({"kind": "usage", "hash": usage_hash})

    effective_scan_id = scan_id or (
        "lease:" + canonical_hash({
            "schema": 1,
            "client_id": client_id,
            "sources": identity,
            "currency": currency.upper(),
        })[:24]
    )
    manifest = freeze_scan(
        scan_id=effective_scan_id,
        client_id=client_id,
        branches=(Branch.LEASE,),
        selection_rule=(
            "all supplied landlord charges; select exactly one effective lease "
            "rate by counterparty/service/date and apply independently supplied "
            "area/allocation evidence when unit pricing is required"
        ),
        sources=sources,
    )
    scan = run_scan(manifest, audit.observations)
    return LeaseIngestionResult(
        scan=scan,
        audit=audit,
        charge_count=len(charges),
        rate_count=len(rates),
        quantity_count=len(quantity),
    )
