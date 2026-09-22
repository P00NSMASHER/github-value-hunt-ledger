#!/usr/bin/env python3
"""Assemble one evidence-first FreightRecovery review case.

This composes existing deterministic engines without upgrading their conclusions:
- contract base-rate authority envelope;
- NVOCC pass-through markup screening;
- FMC demurrage/detention invoice-compliance screening.

Potential amounts are review candidates, not asserted recoveries. If the same invoice
line triggers multiple theories, its candidate amounts are NOT added together; the
case upper bound uses the maximum candidate amount per line to avoid obvious double
counting.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import audit_dd_invoice
import audit_pass_through
import shipment_authority


def dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal: {value!r}") from exc


def base_rate_review(
    envelope: dict[str, Any],
    base_charge: dict[str, Any] | None,
) -> dict[str, Any]:
    if not base_charge:
        return {
            "status": "NO_BASE_CHARGE_INPUT",
            "invoice_line_id": None,
            "potential_review_amount": "0.00",
        }

    line_id = str(base_charge.get("invoice_line_id") or "BASE")
    invoice_id = str(base_charge.get("invoice_id") or "").strip() or None
    billed = dec(base_charge["billed_amount"])
    quantity = dec(base_charge.get("quantity") or "1")
    rate = envelope["base_rate_authority"]

    result = {
        "invoice_id": invoice_id,
        "invoice_line_id": line_id,
        "billed_amount": str(billed),
        "quantity": str(quantity),
        "potential_review_amount": "0.00",
        "asserted_recovery": "0.00",
        "authority_envelope_status": envelope["status"],
    }

    if rate.get("status") != "RESOLVED":
        return {
            **result,
            "status": "BASE_RATE_AUTHORITY_UNRESOLVED",
            "authority_status": rate.get("status"),
        }

    basis = (rate.get("rate_basis") or "").lower()
    if quantity != Decimal("1.00") and "container" not in basis:
        return {
            **result,
            "status": "BASE_RATE_BASIS_REVIEW_REQUIRED",
            "rate_basis": rate.get("rate_basis"),
        }

    unit_rate = dec(rate["amount_value"])
    expected = (unit_rate * quantity).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    delta = (billed - expected).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    result.update(
        {
            "expected_unit_rate": str(unit_rate),
            "expected_total": str(expected),
            "rate_basis": rate.get("rate_basis"),
            "contract_evidence": rate.get("contract_candidates", []),
            "benchmark_context": rate.get("benchmark_context", {}),
        }
    )
    if delta <= 0:
        return {**result, "status": "NO_BASE_RATE_OVERAGE"}

    return {
        **result,
        "status": "POTENTIAL_BASE_RATE_VARIANCE_REVIEW",
        "potential_review_amount": str(delta),
    }


def _pass_through_item(data: dict[str, Any]) -> audit_pass_through.AuditInput:
    fields = audit_pass_through.AuditInput.__dataclass_fields__
    kwargs = {name: data.get(name, fields[name].default) for name in fields}
    return audit_pass_through.AuditInput(**kwargs)


def _dd_item(data: dict[str, Any]) -> audit_dd_invoice.DDInvoiceInput:
    fields = audit_dd_invoice.DDInvoiceInput.__dataclass_fields__
    kwargs = {name: data.get(name, fields[name].default) for name in fields}
    return audit_dd_invoice.DDInvoiceInput(**kwargs)


def consolidate_candidates(
    base_review: dict[str, Any],
    pass_through: list[dict[str, Any]],
    dd_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """Consolidate review candidates without counting overlapping theories twice.

    Line-level theories are first collapsed to the maximum candidate amount per
    invoice line. Those distinct line maxima are summed within a known invoice.
    A whole-invoice D&D candidate can overlap every line in that invoice, so the
    invoice upper bound is max(sum(line candidates), whole-invoice candidate).

    If a positive whole-invoice candidate exists while positive line candidates
    lack invoice scope, overlap cannot be proven or excluded. In that case the
    engine abstains from emitting a combined numeric no-double-count total.
    """

    line_entries: dict[tuple[str | None, str], dict[str, Any]] = {}
    invoice_candidates: dict[str, dict[str, Any]] = {}

    def clean_invoice_id(value: Any) -> str | None:
        text_value = str(value or "").strip()
        return text_value or None

    def add_line(
        invoice_id: str | None,
        line_id: str | None,
        finding_type: str,
        amount: Any,
        status: str,
    ) -> None:
        if not line_id:
            return
        invoice_id = clean_invoice_id(invoice_id)
        value = dec(amount)
        key = (invoice_id, str(line_id))
        entry = line_entries.setdefault(
            key,
            {
                "invoice_id": invoice_id,
                "invoice_line_id": str(line_id),
                "candidate_amounts": [],
                "finding_types": [],
                "statuses": [],
            },
        )
        entry["candidate_amounts"].append(str(value))
        entry["finding_types"].append(finding_type)
        entry["statuses"].append(status)

    def add_invoice(
        invoice_id: str | None,
        finding_type: str,
        amount: Any,
        status: str,
    ) -> None:
        invoice_id = clean_invoice_id(invoice_id)
        if not invoice_id:
            return
        value = dec(amount)
        entry = invoice_candidates.setdefault(
            invoice_id,
            {
                "invoice_id": invoice_id,
                "candidate_amounts": [],
                "finding_types": [],
                "statuses": [],
            },
        )
        entry["candidate_amounts"].append(str(value))
        entry["finding_types"].append(finding_type)
        entry["statuses"].append(status)

    add_line(
        base_review.get("invoice_id"),
        base_review.get("invoice_line_id"),
        "BASE_RATE",
        base_review.get("potential_review_amount", "0"),
        base_review.get("status", "UNKNOWN"),
    )
    for row in pass_through:
        add_line(
            row.get("invoice_id"),
            row.get("invoice_line_id"),
            "PASS_THROUGH",
            row.get("potential_markup_delta", "0"),
            row.get("status", "UNKNOWN"),
        )
    for row in dd_reviews:
        add_invoice(
            row.get("invoice_id"),
            "DEMURRAGE_DETENTION_INVOICE",
            row.get("potential_charge_relief_amount", "0"),
            row.get("status", "UNKNOWN"),
        )

    line_rows: list[dict[str, Any]] = []
    line_sums_by_invoice: dict[str, Decimal] = {}
    unscoped_line_total = Decimal("0.00")
    positive_unscoped_lines = False

    for (invoice_id, line_id), entry in sorted(
        line_entries.items(),
        key=lambda item: ((item[0][0] or ""), item[0][1]),
    ):
        values = [dec(value) for value in entry["candidate_amounts"]]
        upper = max(values) if values else Decimal("0.00")
        if invoice_id is None:
            unscoped_line_total += upper
            positive_unscoped_lines = positive_unscoped_lines or upper > 0
        else:
            line_sums_by_invoice[invoice_id] = (
                line_sums_by_invoice.get(invoice_id, Decimal("0.00")) + upper
            )
        line_rows.append(
            {
                **entry,
                "candidate_upper_bound_no_double_count": str(upper),
            }
        )

    invoice_rows: list[dict[str, Any]] = []
    scoped_total = Decimal("0.00")
    positive_whole_invoice_candidate = False
    invoice_ids = sorted(set(line_sums_by_invoice) | set(invoice_candidates))
    for invoice_id in invoice_ids:
        line_total = line_sums_by_invoice.get(invoice_id, Decimal("0.00"))
        invoice_entry = invoice_candidates.get(invoice_id)
        invoice_values = (
            [dec(value) for value in invoice_entry["candidate_amounts"]]
            if invoice_entry
            else []
        )
        whole_invoice_upper = (
            max(invoice_values) if invoice_values else Decimal("0.00")
        )
        positive_whole_invoice_candidate = (
            positive_whole_invoice_candidate or whole_invoice_upper > 0
        )
        upper = max(line_total, whole_invoice_upper)
        scoped_total += upper
        invoice_rows.append(
            {
                "invoice_id": invoice_id,
                "line_level_candidate_sum": str(line_total),
                "whole_invoice_candidate_max": str(whole_invoice_upper),
                "candidate_upper_bound_no_double_count": str(upper),
                "whole_invoice_finding_types": (
                    invoice_entry["finding_types"] if invoice_entry else []
                ),
                "whole_invoice_statuses": (
                    invoice_entry["statuses"] if invoice_entry else []
                ),
            }
        )

    scope_incomplete = positive_whole_invoice_candidate and positive_unscoped_lines
    combined = None
    if not scope_incomplete:
        combined = str(
            (scoped_total + unscoped_line_total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        )

    return {
        "status": (
            "OVERLAP_SCOPE_INCOMPLETE"
            if scope_incomplete
            else "CONSOLIDATED"
        ),
        "lines": line_rows,
        "invoice_scopes": invoice_rows,
        "unscoped_line_candidate_total": str(unscoped_line_total),
        "potential_review_upper_bound_no_double_count": combined,
        "asserted_recovery_total": "0.00",
        "overlap_policy": {
            "line_theories_use_max_per_line": True,
            "distinct_lines_sum_within_known_invoice": True,
            "whole_invoice_vs_line_sum_uses_max": True,
            "missing_invoice_scope_with_whole_invoice_candidate_abstains": True,
        },
    }


def assemble_case(
    rate_conn: sqlite3.Connection,
    fmc_conn: sqlite3.Connection,
    case: dict[str, Any],
) -> dict[str, Any]:
    shipment = case["shipment"]
    envelope = shipment_authority.build_envelope(
        rate_conn,
        fmc_conn,
        fmc_organization_no=shipment["fmc_organization_no"],
        shipment_date=shipment["shipment_date"],
        origin=shipment["origin"],
        destination=shipment["destination"],
        container_type=shipment["container_type"],
        currency=shipment.get("currency", "USD"),
        rule_types=shipment.get("rule_types"),
    )

    base = base_rate_review(envelope, case.get("base_charge"))

    pass_results = []
    for row in case.get("pass_through_lines", []):
        pass_results.append(
            audit_pass_through.audit_one(
                fmc_conn,
                _pass_through_item(row),
            )
        )

    dd_results = [
        audit_dd_invoice.audit_invoice(_dd_item(row))
        for row in case.get("dd_invoices", [])
    ]

    consolidated = consolidate_candidates(base, pass_results, dd_results)
    blockers = list(envelope.get("blockers", []))
    if any(
        result["status"].startswith(("AMBIGUOUS_", "UNDATED_", "NO_EFFECTIVE_"))
        for result in pass_results
    ):
        blockers.append("PASS_THROUGH_AUTHORITY_GAPS")
    if any(
        result["status"] == "CONTENT_COMPLETE_TIMING_UNVERIFIABLE"
        for result in dd_results
    ):
        blockers.append("DD_TIMING_EVIDENCE_GAP")

    return {
        "case_id": case.get("case_id"),
        "status": (
            "REVIEW_PACKET_READY_WITH_GAPS"
            if blockers
            else "REVIEW_PACKET_READY"
        ),
        "asserted_recovery_total": "0.00",
        "shipment_authority": envelope,
        "base_rate_review": base,
        "pass_through_reviews": pass_results,
        "demurrage_detention_reviews": dd_results,
        "candidate_consolidation": consolidated,
        "blockers": sorted(set(blockers)),
        "review_policy": {
            "potential_amounts_are_not_asserted_recovery": True,
            "same_invoice_line_findings_are_not_additive": True,
            "human_review_required_before_money_assertion": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build FreightRecovery evidence review case")
    p.add_argument("--rate-db", required=True)
    p.add_argument("--fmc-db", required=True)
    p.add_argument("--case-json", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    case = json.loads(Path(args.case_json).read_text(encoding="utf-8"))
    rate_conn = sqlite3.connect(args.rate_db)
    rate_conn.row_factory = sqlite3.Row
    fmc_conn = sqlite3.connect(args.fmc_db)
    fmc_conn.row_factory = sqlite3.Row
    result = assemble_case(rate_conn, fmc_conn, case)
    rate_conn.close()
    fmc_conn.close()

    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    Path(args.output).write_text(payload, encoding="utf-8")
    print(json.dumps(
        {
            "case_id": result["case_id"],
            "status": result["status"],
            "potential_review_upper_bound_no_double_count":
                result["candidate_consolidation"][
                    "potential_review_upper_bound_no_double_count"
                ],
            "asserted_recovery_total": result["asserted_recovery_total"],
            "blockers": result["blockers"],
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
