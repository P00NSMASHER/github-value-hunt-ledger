"""Customer-friendly CSV intake for APRecovery.

The source files are hashed by RecoveryWorks. Verification is supplied by the
operator/control plane, never trusted from a CSV column.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from typing import Any

from .engines.ap import APInvoice, APPayment, detect_ap_overpayments
from .ledger import RecoveryLedger
from .models import Branch
from .packets import build_client_portfolio_packet, build_recovery_packet, submission_ready
from .scan import SourceManifestEntry, freeze_scan, run_scan


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def money_to_cents(value: str) -> int:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("money value is required")
    try:
        amount = Decimal(value.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc
    if amount < 0:
        raise ValueError("money value must be non-negative")
    quantized = amount.quantize(Decimal("0.01"))
    if quantized != amount:
        raise ValueError("money value cannot contain fractions smaller than one cent")
    return int(quantized * 100)


def _bool(value: str, field: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"{field} must be true/false")


def _rows(path: Path, required: set[str]):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or ())
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"{path.name} missing required columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            yield row_number, row


def load_ap_invoices_csv(
    path: str | Path,
    *,
    verified: bool,
) -> tuple[tuple[APInvoice, ...], str]:
    source = Path(path)
    source_hash = sha256_file(source)
    required = {"vendor_id", "invoice_id", "invoice_date", "amount", "currency"}
    invoices = []
    for row_number, row in _rows(source, required):
        invoices.append(APInvoice(
            vendor_id=row["vendor_id"],
            invoice_id=row["invoice_id"],
            invoice_date=row["invoice_date"],
            amount_cents=money_to_cents(row["amount"]),
            currency=row["currency"],
            source_hash=source_hash,
            locator=f"file://{source.resolve()}#row={row_number}",
            verified=verified,
        ))
    return tuple(invoices), source_hash


def load_ap_payments_csv(
    path: str | Path,
    *,
    verified: bool,
) -> tuple[tuple[APPayment, ...], str]:
    source = Path(path)
    source_hash = sha256_file(source)
    required = {
        "vendor_id", "invoice_id", "payment_id", "payment_date",
        "amount", "currency", "posted",
    }
    payments = []
    for row_number, row in _rows(source, required):
        payments.append(APPayment(
            vendor_id=row["vendor_id"],
            invoice_id=row["invoice_id"],
            payment_id=row["payment_id"],
            payment_date=row["payment_date"],
            amount_cents=money_to_cents(row["amount"]),
            currency=row["currency"],
            source_hash=source_hash,
            locator=f"file://{source.resolve()}#row={row_number}",
            verified=verified,
            posted=_bool(row["posted"], "posted"),
        ))
    return tuple(payments), source_hash


def execute_ap_csv_scan(
    *,
    scan_id: str,
    client_id: str,
    invoices_path: str | Path,
    payments_path: str | Path,
    invoices_verified: bool,
    payments_verified: bool,
    selection_rule: str = "all rows in supplied AP invoice and payment exports",
) -> tuple[dict[str, Any], RecoveryLedger]:
    invoices, invoice_hash = load_ap_invoices_csv(
        invoices_path,
        verified=invoices_verified,
    )
    payments, payment_hash = load_ap_payments_csv(
        payments_path,
        verified=payments_verified,
    )
    observations = detect_ap_overpayments(
        client_id=client_id,
        invoices=invoices,
        payments=payments,
    )

    manifest = freeze_scan(
        scan_id=scan_id,
        client_id=client_id,
        branches=(Branch.AP,),
        selection_rule=selection_rule,
        sources=(
            SourceManifestEntry(
                source_id="ap-invoices",
                branch=Branch.AP,
                source_hash=invoice_hash,
                locator=f"file://{Path(invoices_path).resolve()}",
                kind="ap_invoice_export",
            ),
            SourceManifestEntry(
                source_id="ap-payments",
                branch=Branch.AP,
                source_hash=payment_hash,
                locator=f"file://{Path(payments_path).resolve()}",
                kind="ap_payment_export",
            ),
        ),
    )
    batch = run_scan(manifest, observations)
    ledger = RecoveryLedger()
    records = tuple(ledger.add(finding) for finding in batch.findings)
    packets = tuple(build_recovery_packet(record) for record in records)
    portfolio = build_client_portfolio_packet(ledger, client_id)

    result = {
        "schema": 1,
        "input_mode": "ap_csv",
        "scan_id": scan_id,
        "client_id": client_id,
        "manifest_hash": manifest.manifest_hash,
        "batch_hash": batch.batch_hash,
        "invoice_source_hash": invoice_hash,
        "payment_source_hash": payment_hash,
        "invoice_rows": len(invoices),
        "payment_rows": len(payments),
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "audit_head": ledger.audit_head,
        "portfolio": portfolio,
        "findings": [{
            "finding_id": packet.finding_id,
            "reference": packet.reference,
            "case_state": packet.case_state,
            "currency": packet.currency,
            "potential_recovery_cents": packet.potential_recovery_cents,
            "packet_hash": packet.packet_hash,
            "submission_ready": submission_ready(packet),
        } for packet in packets],
    }
    return result, ledger
