"""End-to-end APRecovery file ingestion into a frozen RecoveryOS scan."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

from recoveryworks.models import Branch, canonical_hash
from recoveryworks.scan import RecoveryScanBatch, SourceManifestEntry, freeze_scan, run_scan

from .ap import APRecoveryBatch, audit_ap_recovery
from .ap_csv import (
    DEFAULT_OBLIGATION_COLUMNS,
    DEFAULT_PAYMENT_COLUMNS,
    DEFAULT_VENDOR_STATEMENT_COLUMNS,
    load_obligations_csv,
    load_payments_csv,
    load_vendor_statements_csv,
)


@dataclass(frozen=True)
class APIngestionResult:
    scan: RecoveryScanBatch
    audit: APRecoveryBatch
    payment_count: int
    obligation_count: int
    statement_count: int


def _file_hash(path: str | Path) -> tuple[Path, str]:
    source = Path(path)
    raw = source.read_bytes()
    return source, hashlib.sha256(raw).hexdigest()


def ingest_ap_exports(
    *,
    client_id: str,
    payments_path: str | Path,
    obligations_path: str | Path | None = None,
    statements_path: str | Path | None = None,
    verified_payments: bool = False,
    verified_obligations: bool = False,
    verified_statements: bool = False,
    default_effective_from: str = "1970-01-01",
    default_statement_date: str | None = None,
    currency: str = "USD",
    scan_id: str | None = None,
    payment_columns: Mapping[str, str] = DEFAULT_PAYMENT_COLUMNS,
    obligation_columns: Mapping[str, str] = DEFAULT_OBLIGATION_COLUMNS,
    statement_columns: Mapping[str, str] = DEFAULT_VENDOR_STATEMENT_COLUMNS,
) -> APIngestionResult:
    """Load AP exports and produce a frozen, reproducible RecoveryOS scan.

    Verification defaults to false. Vendor statement credits may corroborate a
    suspected duplicate or surface a standalone credit, but contradictory source
    records force review rather than silently overriding ledger math.
    """
    payments = load_payments_csv(
        payments_path,
        verified=verified_payments,
        columns=payment_columns,
    )
    obligations = ()
    if obligations_path is not None:
        obligations = load_obligations_csv(
            obligations_path,
            verified=verified_obligations,
            default_effective_from=default_effective_from,
            columns=obligation_columns,
        )
    statements = ()
    if statements_path is not None:
        statements = load_vendor_statements_csv(
            statements_path,
            verified=verified_statements,
            default_statement_date=default_statement_date,
            columns=statement_columns,
        )

    audit = audit_ap_recovery(
        client_id=client_id,
        payments=payments,
        obligations=obligations,
        statements=statements,
        currency=currency,
    )

    payment_source, payment_hash = _file_hash(payments_path)
    sources = [
        SourceManifestEntry(
            source_id="ap:payments",
            branch=Branch.AP,
            source_hash=payment_hash,
            locator=f"file://{payment_source.name}",
            kind="ap_payment_export",
        )
    ]
    source_identity = [{"kind": "payments", "hash": payment_hash}]

    if obligations_path is not None:
        obligation_source, obligation_hash = _file_hash(obligations_path)
        sources.append(SourceManifestEntry(
            source_id="ap:obligations",
            branch=Branch.AP,
            source_hash=obligation_hash,
            locator=f"file://{obligation_source.name}",
            kind="ap_obligation_export",
        ))
        source_identity.append({"kind": "obligations", "hash": obligation_hash})

    if statements_path is not None:
        statement_source, statement_hash = _file_hash(statements_path)
        sources.append(SourceManifestEntry(
            source_id="ap:vendor-statements",
            branch=Branch.AP,
            source_hash=statement_hash,
            locator=f"file://{statement_source.name}",
            kind="ap_vendor_statement_export",
        ))
        source_identity.append({"kind": "vendor_statements", "hash": statement_hash})

    effective_scan_id = scan_id or (
        "ap:" + canonical_hash({
            "schema": 1,
            "client_id": client_id,
            "sources": source_identity,
            "currency": currency.upper(),
        })[:24]
    )
    manifest = freeze_scan(
        scan_id=effective_scan_id,
        client_id=client_id,
        branches=(Branch.AP,),
        selection_rule=(
            "all supplied AP payment rows; compare invoice-level totals to supplied "
            "obligations, reconcile latest vendor-statement balances, and surface "
            "unsupported duplicate-payment clusters for human review"
        ),
        sources=sources,
    )
    scan = run_scan(manifest, audit.observations)
    return APIngestionResult(
        scan=scan,
        audit=audit,
        payment_count=len(payments),
        obligation_count=len(obligations),
        statement_count=len(statements),
    )
