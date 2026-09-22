"""End-to-end UtilityRecovery file ingestion into a frozen RecoveryOS scan."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

from recoveryworks.models import Branch, canonical_hash
from recoveryworks.scan import RecoveryScanBatch, SourceManifestEntry, freeze_scan, run_scan

from .utility import UtilityAuditBatch, audit_utility_bills
from .utility_io import (
    DEFAULT_BILL_COLUMNS,
    load_simple_tariff_definitions_json,
    load_utility_bills_csv,
)


@dataclass(frozen=True)
class UtilityIngestionResult:
    scan: RecoveryScanBatch
    audit: UtilityAuditBatch
    bill_count: int
    tariff_count: int


def _file_hash(path: str | Path) -> tuple[Path, str]:
    source = Path(path)
    raw = source.read_bytes()
    return source, hashlib.sha256(raw).hexdigest()


def ingest_utility_exports(
    *,
    client_id: str,
    bills_path: str | Path,
    tariffs_path: str | Path,
    utility_id: str,
    default_effective_from: str,
    jurisdiction: str | None = None,
    verified_bills: bool = False,
    verified_tariffs: bool = False,
    currency: str = "USD",
    scan_id: str | None = None,
    bill_columns: Mapping[str, str] = DEFAULT_BILL_COLUMNS,
) -> UtilityIngestionResult:
    """Load utility bill/tariff files and run a frozen deterministic audit.

    Unsupported tariff logic still fails closed in the tariff loader. Service
    periods, when supplied, control tariff-version selection; bill date is only
    a fallback for exports without service-period fields.
    """
    bills = load_utility_bills_csv(
        bills_path,
        verified=verified_bills,
        columns=bill_columns,
    )
    tariffs = load_simple_tariff_definitions_json(
        tariffs_path,
        utility_id=utility_id,
        verified=verified_tariffs,
        default_effective_from=default_effective_from,
        jurisdiction=jurisdiction,
    )
    audit = audit_utility_bills(
        client_id=client_id,
        bills=bills,
        tariffs=tariffs,
        currency=currency,
    )

    bill_source, bill_hash = _file_hash(bills_path)
    tariff_source, tariff_hash = _file_hash(tariffs_path)
    sources = (
        SourceManifestEntry(
            source_id="utility:bills",
            branch=Branch.UTILITY,
            source_hash=bill_hash,
            locator=f"file://{bill_source.name}",
            kind="utility_bill_export",
        ),
        SourceManifestEntry(
            source_id="utility:tariffs",
            branch=Branch.UTILITY,
            source_hash=tariff_hash,
            locator=f"file://{tariff_source.name}",
            kind="utility_tariff_definition",
        ),
    )
    effective_scan_id = scan_id or (
        "utility:" + canonical_hash({
            "schema": 1,
            "client_id": client_id,
            "utility_id": utility_id,
            "bill_hash": bill_hash,
            "tariff_hash": tariff_hash,
            "currency": currency.upper(),
        })[:24]
    )
    manifest = freeze_scan(
        scan_id=effective_scan_id,
        client_id=client_id,
        branches=(Branch.UTILITY,),
        selection_rule=(
            "all supplied utility bills; apply exactly one deterministic tariff "
            "version covering the service period when present, otherwise bill date; "
            "overlapping, partial, missing, or unsupported tariff logic fails closed"
        ),
        sources=sources,
    )
    scan = run_scan(manifest, audit.observations)
    return UtilityIngestionResult(
        scan=scan,
        audit=audit,
        bill_count=len(bills),
        tariff_count=len(tariffs),
    )
