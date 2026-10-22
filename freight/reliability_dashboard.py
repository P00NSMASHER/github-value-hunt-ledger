"""Deterministic private QA and aggregate-only customer-readiness dashboard.

Never expose invoice identifiers, raw PDFs, financial claims, credentials or
unadjudicated money on a public surface. This module is for engineering CI.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from html import escape
import json
from time import perf_counter
from typing import Iterable

from freight.contracts import canonical_hash
from freight.scoped_reconciliation import (
    ScopedTxn, ScopeReconciliation, reconcile_scoped,
)
from recoveryworks.reconciliation_kernel import ReconTxn


@dataclass(frozen=True)
class ReadinessSnapshot:
    original_invoice_count: int
    original_invoice_arithmetic_exact: int
    pdf_sha256_pins_verified: int
    distinct_invoice_disclosures: int
    accounting_reference_matched: int
    accounting_cross_scope_errors: int
    independently_labeled_freight_cases: int
    unresolved_freight_cases: int
    real_freight_precision: float | None
    independently_verified_cash_recovery_cents: int
    rights_release_approved: bool
    production_deployment_approved: bool
    release_status: str
    blockers: tuple[str, ...]
    manifest_hash: str


def acceptance_snapshot(
    *,
    invoices_extracted: int,
    invoices_exact: int,
    pinned_source_files: int,
    accounting_invoice_population: int,
    accounting_matched: int,
    accounting_cross_scope_errors: int,
    freight_labeled: int,
    freight_unknown: int,
    precision: float | None,
    verified_recovery_cents: int = 0,
    rights_approved: bool = False,
    production_approved: bool = False,
) -> ReadinessSnapshot:
    numeric = (
        invoices_extracted, invoices_exact, pinned_source_files,
        accounting_invoice_population, accounting_matched, accounting_cross_scope_errors,
        freight_labeled, freight_unknown, verified_recovery_cents,
    )
    if any(type(x) is not int or x < 0 for x in numeric):
        raise ValueError("all counts/currency minor units must be nonnegative exact integers")
    if invoices_exact > invoices_extracted or accounting_matched > accounting_invoice_population:
        raise ValueError("aggregate totals violate population conservation")
    if precision is not None and (type(precision) is not float or not 0 <= precision <= 1):
        raise ValueError("freight precision must be bounded numeric or unknown")
    for val in (rights_approved, production_approved):
        if type(val) is not bool:
            raise ValueError("governance authorization must be boolean")
    blockers: list[str] = []
    if pinned_source_files < 2:
        blockers.append("ORIGINAL_SOURCE_PROVENANCE_INCOMPLETE")
    if invoices_exact != invoices_extracted:
        blockers.append("ORIGINAL_INVOICE_ARITHMETIC_INCOMPLETE")
    if accounting_matched != accounting_invoice_population or accounting_cross_scope_errors:
        blockers.append("FINANCIAL_REFERENCE_RECONCILIATION_NEEDS_REVIEW")
    if freight_labeled == 0 or freight_unknown or precision is None:
        blockers.append("REAL_FREIGHT_ACCURACY_UNPROVEN")
    if not rights_approved:
        blockers.append("COMMERCIAL_RIGHTS_NOT_RELEASED")
    if not production_approved:
        blockers.append("PRODUCTION_DEPLOYMENT_NOT_APPROVED")
    # Even a score with a narrow internal population is not independently
    # sufficient to remove the existing governed freight pilot acceptance gate.
    blockers.append("EXISTING_FREIGHT_PILOT_ACCEPTANCE_REQUIRED")
    status = "RELEASE_HOLD" if blockers else "READY_FOR_SEPARATE_ACCEPTANCE"
    body = {
        "schema": 2, "invoice_count": invoices_extracted, "exact": invoices_exact,
        "pins": pinned_source_files, "accounting_count": accounting_invoice_population,
        "matched": accounting_matched, "scoping_errors": accounting_cross_scope_errors,
        "freight_labeled": freight_labeled, "freight_unknown": freight_unknown,
        "precision": precision, "verified_recovered_cents": verified_recovery_cents,
        "rights": rights_approved, "code_quality_policy": "AUTOMATED_EVIDENCE_QA",
        "deployed": production_approved, "status": status, "blockers": blockers,
    }
    return ReadinessSnapshot(
        invoices_extracted, invoices_exact, pinned_source_files,
        accounting_invoice_population, accounting_matched,
        accounting_cross_scope_errors, freight_labeled, freight_unknown,
        precision, verified_recovery_cents,
        rights_approved, production_approved,
        status, tuple(blockers), canonical_hash(body),
    )


def html_dashboard(snapshot: ReadinessSnapshot) -> str:
    """Plain static HTML; user-controlled fields are always escaped."""
    if not isinstance(snapshot, ReadinessSnapshot):
        raise ValueError("snapshot must be validated aggregate type")
    # Rendering only aggregated counts and hold reasons; do not include payment
    # references, raw source URLs, company/vendor names or PII.
    rows = [
        ("Original invoice documents", str(snapshot.original_invoice_count)),
        ("Exact original invoice totals", str(snapshot.original_invoice_arithmetic_exact)),
        ("Source pins verified", str(snapshot.pdf_sha256_pins_verified)),
        ("General accounting invoices", str(snapshot.distinct_invoice_disclosures)),
        ("Scoped accounting matches", str(snapshot.accounting_reference_matched)),
        ("Independent freight truth labels", str(snapshot.independently_labeled_freight_cases)),
        ("Unresolved freight cases", str(snapshot.unresolved_freight_cases)),
        ("External freight precision", "NOT ESTIMABLE" if snapshot.real_freight_precision is None
         else f"{snapshot.real_freight_precision:.3f} (conditional, not release approved)"),
        ("Externally confirmed realized recovery", "Not a claim on this dashboard"),
        ("Release status", snapshot.release_status),
    ]
    table_rows = "\n".join(
        "<tr><th>" + escape(name) + "</th><td>" + escape(value) + "</td></tr>"
        for name, value in rows
    )
    holds = "".join("<li>" + escape(x) + "</li>" for x in snapshot.blockers)
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>RETALLY Evidence Quality: Internal QA</title>"
        "<meta name=\"robots\" content=\"noindex,nofollow\">"
        "<style>body{font:16px system-ui;margin:3em auto;max-width:780px}"
        "th,td{padding:.7em;border-bottom:1px solid #ddd;text-align:left}"
        "th{width:60%}table{width:100%}</style></head><body>"
        "<h1>RETALLY - internal evidence-quality assessment</h1>"
        "<p>Research-only metrics. Source-report matching does not prove bank"
        " settlement, commercial rights, freight accuracy, or collected cash.</p>"
        "<table>" + table_rows + "</table>"
        "<h2>Open acceptance holds</h2><ul>" + holds + "</ul>"
        "<p>Internal code quality uses automated evidence-based QA. External "
        "publication or deployment still requires authentic source evidence, "
        "applicable customer authorization, and separate release approval.</p>"
        "</body></html>"
    )


@dataclass(frozen=True)
class ThroughputRun:
    synthetic_invoice_count: int
    synthetic_counterparts: int
    matched_internal: int
    missing_internal: int
    cross_reference_errors: int
    deterministic_replay: bool
    median_run_seconds: float
    records_per_second: float
    stable_result_sha256: str
    production_accuracy_claim: bool = False


def synthetic_population(n: int) -> tuple[list[ScopedTxn], list[ScopedTxn]]:
    """Fixed 1-to-4 invoices per payment group; *never* real buyer data."""
    if type(n) is not int or not 1 <= n <= 150_000:
        raise ValueError("synthetic population must have 1..150000 invoices")
    invoices: list[ScopedTxn] = []
    payment: list[ScopedTxn] = []
    current = 0
    group_no = 0
    while current < n:
        group_no += 1
        count = min(1 + (group_no % 4), n-current)
        scope = f"synthetic-pmt-{group_no:07d}"
        cents_total = 0
        for i in range(count):
            cents = 1000 + ((current+i)*37) % 11_000
            cents_total += cents
            invoices.append(ScopedTxn(
                ReconTxn(f"I-{current+i}", f"{cents//100}.{cents%100:02d}",
                         "2026-07-01", "USD", scope),
                "synthetic-buyer", "synthetic-bu", "synthetic-carrier",
                "ORIGINAL_INVOICE",
            ))
        payment.append(ScopedTxn(
            ReconTxn(f"P-{group_no}", f"{cents_total//100}.{cents_total%100:02d}",
                     "2026-07-01", "USD", scope),
            "synthetic-buyer", "synthetic-bu", "synthetic-carrier",
            "CUSTOMER_DECLARATION",
        ))
        current += count
    return invoices, payment


def run_deterministic_throughput(n: int) -> ThroughputRun:
    invoices, payment = synthetic_population(n)
    durations = []
    results = []
    for ix in (0, 1):
        start = perf_counter()
        result = reconcile_scoped(
            invoices if ix == 0 else list(reversed(invoices)),
            payment if ix == 0 else list(reversed(payment)),
            group_size_limit=8, date_window_days=0)
        durations.append(max(perf_counter()-start, 1e-12))
        results.append(result)
    if any(x.matched_internal != n or x.unmatched_internal or
           x.mismatched_references or x.proven_cleared_payment_count
           for x in results):
        raise ValueError("synthetic performance run failed money/reference invariants")
    stable = results[0].result_hash == results[1].result_hash
    if not stable:
        raise ValueError("reordered deterministic reconciliation gave a different hash")
    median = sum(durations)/2
    return ThroughputRun(
        n, len(payment), results[0].matched_internal,
        results[0].unmatched_internal, results[0].mismatched_references,
        stable, round(median, 6), round(n/median, 2),
        results[0].result_hash, False,
    )


def safe_perf_json(result: ThroughputRun) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True) + "\n"
