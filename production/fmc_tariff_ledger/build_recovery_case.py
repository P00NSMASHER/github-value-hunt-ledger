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
    by_line: dict[str, dict[str, Any]] = {}

    def add(line_id: str | None, finding_type: str, amount: Any, status: str) -> None:
        if not line_id:
            return
        value = dec(amount)
        entry = by_line.setdefault(
            line_id,
            {
                "invoice_line_id": line_id,
                "candidate_amounts": [],
                "finding_types": [],
                "statuses": [],
            },
        )
        entry["candidate_amounts"].append(str(value))
        entry["finding_types"].append(finding_type)
        entry["statuses"].append(status)

    add(
        base_review.get("invoice_line_id"),
        "BASE_RATE",
        base_review.get("potential_review_amount", "0"),
        base_review.get("status", "UNKNOWN"),
    )
    for row in pass_through:
        add(
            row.get("invoice_line_id"),
            "PASS_THROUGH",
            row.get("potential_markup_delta", "0"),
            row.get("status", "UNKNOWN"),
        )
    for row in dd_reviews:
        add(
            row.get("invoice_id"),
            "DEMURRAGE_DETENTION_INVOICE",
            row.get("potential_charge_relief_amount", "0"),
            row.get("status", "UNKNOWN"),
        )

    total = Decimal("0.00")
    rows = []
    for line_id, entry in sorted(by_line.items()):
        values = [dec(value) for value in entry["candidate_amounts"]]
        upper = max(values) if values else Decimal("0.00")
        total += upper
        rows.append(
            {
                **entry,
                "candidate_upper_bound_no_double_count": str(upper),
            }
        )
    return {
        "lines": rows,
        "potential_review_upper_bound_no_double_count": str(
            total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        "asserted_recovery_total": "0.00",
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
