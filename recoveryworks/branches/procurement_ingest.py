"""End-to-end ProcurementRecovery file ingestion into a frozen RecoveryOS scan."""
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
    load_contract_rates_csv,
    load_invoice_charges_csv,
)
from .procurement import audit_procurement_billing
from .procurement_csv import (
    DEFAULT_PROCUREMENT_QUANTITY_COLUMNS,
    load_procurement_quantities_csv,
)


@dataclass(frozen=True)
class ProcurementIngestionResult:
    scan: RecoveryScanBatch
    audit: ContractBillingBatch
    charge_count: int
    rate_count: int
    quantity_count: int


def _file_hash(path: str | Path) -> tuple[Path, str]:
    source = Path(path)
    raw = source.read_bytes()
    return source, hashlib.sha256(raw).hexdigest()


def ingest_procurement_exports(
    *,
    client_id: str,
    charges_path: str | Path,
    rates_path: str | Path,
    quantities_path: str | Path | None = None,
    verified_charges: bool = False,
    verified_rates: bool = False,
    verified_quantities: bool = False,
    currency: str = "USD",
    scan_id: str | None = None,
    charge_columns: Mapping[str, str] = DEFAULT_CHARGE_COLUMNS,
    rate_columns: Mapping[str, str] = DEFAULT_RATE_COLUMNS,
    quantity_columns: Mapping[str, str] = DEFAULT_PROCUREMENT_QUANTITY_COLUMNS,
) -> ProcurementIngestionResult:
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
    quantities = ()
    if quantities_path is not None:
        quantities = load_procurement_quantities_csv(
            quantities_path,
            verified=verified_quantities,
            columns=quantity_columns,
        )

    audit = audit_procurement_billing(
        client_id=client_id,
        charges=charges,
        rates=rates,
        quantities=quantities,
        currency=currency,
    )

    charge_source, charge_hash = _file_hash(charges_path)
    rate_source, rate_hash = _file_hash(rates_path)
    sources = [
        SourceManifestEntry(
            source_id="procurement:charges",
            branch=Branch.PROCUREMENT,
            source_hash=charge_hash,
            locator=f"file://{charge_source.name}",
            kind="procurement_supplier_charge_export",
        ),
        SourceManifestEntry(
            source_id="procurement:rates",
            branch=Branch.PROCUREMENT,
            source_hash=rate_hash,
            locator=f"file://{rate_source.name}",
            kind="procurement_contract_rate_schedule",
        ),
    ]
    identity = [
        {"kind": "charges", "hash": charge_hash},
        {"kind": "rates", "hash": rate_hash},
    ]
    if quantities_path is not None:
        quantity_source, quantity_hash = _file_hash(quantities_path)
        sources.append(SourceManifestEntry(
            source_id="procurement:quantities",
            branch=Branch.PROCUREMENT,
            source_hash=quantity_hash,
            locator=f"file://{quantity_source.name}",
            kind="procurement_received_quantity_export",
        ))
        identity.append({"kind": "quantities", "hash": quantity_hash})

    effective_scan_id = scan_id or (
        "procurement:" + canonical_hash({
            "schema": 1,
            "client_id": client_id,
            "sources": identity,
            "currency": currency.upper(),
        })[:24]
    )
    manifest = freeze_scan(
        scan_id=effective_scan_id,
        client_id=client_id,
        branches=(Branch.PROCUREMENT,),
        selection_rule=(
            "all supplied supplier charges; select exactly one effective negotiated "
            "rate by supplier/service/date and apply independent received quantity "
            "evidence when unit pricing is required"
        ),
        sources=sources,
    )
    scan = run_scan(manifest, audit.observations)
    return ProcurementIngestionResult(
        scan=scan,
        audit=audit,
        charge_count=len(charges),
        rate_count=len(rates),
        quantity_count=len(quantities),
    )
