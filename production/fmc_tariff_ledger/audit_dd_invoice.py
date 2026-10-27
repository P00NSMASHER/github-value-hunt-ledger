#!/usr/bin/env python3
"""Deterministic FMC demurrage/detention invoice compliance screening.

This engine checks objective Part 541 billing requirements. It does not evaluate
the vacated § 541.4 proper-party rule, does not make legal conclusions, and does
not automatically assert a recovery. Positive findings are routed for human
review with the applicable charge amount as a potential relief amount.

Full Part 541 invoice-content requirements became effective May 28, 2024.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


FULL_RULE_EFFECTIVE_DATE = date(2024, 5, 28)
PART_541_URL = (
    "https://www.ecfr.gov/current/title-46/chapter-IV/"
    "subchapter-B/part-541"
)

REGULATORY_REFERENCES = [
    {
        "citation": "46 CFR 541.5",
        "purpose": "Effect of failure to include required minimum information.",
    },
    {
        "citation": "46 CFR 541.6",
        "purpose": "Required identifying, timing, rate, dispute, and certification information.",
    },
    {
        "citation": "46 CFR 541.7",
        "purpose": "30-day invoice issuance requirements, including NVOCC pass-through timing.",
    },
    {
        "citation": "46 CFR 541.8",
        "purpose": "Minimum request window and resolution timing for mitigation/refund/waiver.",
    },
    {
        "citation": "46 CFR 545.5",
        "purpose": "Reasonableness/incentive principles for demurrage and detention.",
    },
]

# § 541.4 is intentionally absent. The D.C. Circuit set it aside in 2025;
# this screening engine is limited to provisions that remained in force.


@dataclass(frozen=True)
class DDInvoiceInput:
    invoice_id: str
    billing_party_type: str  # vocc | nvocc | mto
    charge_type: str  # demurrage | detention
    invoice_date: str
    invoice_due_date: str
    total_amount: str
    currency: str

    bill_of_lading_numbers: str = ""
    container_numbers: str = ""
    movement: str = ""  # import | export
    discharge_ports: str = ""
    liability_basis: str = ""

    allowed_free_time_days: str = ""
    free_time_start_date: str = ""
    free_time_end_date: str = ""
    container_availability_date: str = ""
    earliest_return_date: str = ""
    charged_dates: str = ""

    governing_rule_reference: str = ""
    specific_rates: str = ""

    dispute_contact: str = ""
    dispute_instructions_url: str = ""
    mitigation_request_window_days: str = ""
    mitigation_resolution_window_days: str = ""
    later_resolution_date_agreed: str = ""

    certification_fmc_rules: str = ""
    certification_billing_party_no_contribution: str = ""

    charge_last_incurred_date: str = ""
    upstream_invoice_date: str = ""
    billed_party_type: str = ""  # shipper | consignee | cargo_owner | freight_forwarder | truck_operator; absent => HOLD


def parse_date(value: str, *, required: bool = False) -> date | None:
    value = (value or "").strip()
    if not value:
        if required:
            raise ValueError("required date is blank")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO date: {value!r}") from exc


def parse_decimal(value: str, *, required: bool = False) -> Decimal | None:
    value = (value or "").replace(",", "").strip()
    if not value:
        if required:
            raise ValueError("required decimal is blank")
        return None
    try:
        amount = Decimal(value)
        if not amount.is_finite():
            raise ValueError("invoice amount must be finite")
        if amount < 0:
            raise ValueError("invoice amount must be non-negative; credit memos need separate review")
        exact_cents = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount != exact_cents:
            raise ValueError("sub-cent precision would silently change the source invoice")
        return Decimal("0.00") if amount == 0 else exact_cents
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {value!r}") from exc


def truthy_statement(value: str) -> bool:
    return bool((value or "").strip())


def integer_days(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        days = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid day count: {value!r}") from exc
    if days < 0:
        raise ValueError("day count must be non-negative")
    return days


def required_content_fields(item: DDInvoiceInput) -> dict[str, bool]:
    movement = item.movement.strip().lower()
    fields = {
        "bill_of_lading_numbers": truthy_statement(item.bill_of_lading_numbers),
        "container_numbers": truthy_statement(item.container_numbers),
        "liability_basis": truthy_statement(item.liability_basis),
        "invoice_date": truthy_statement(item.invoice_date),
        "invoice_due_date": truthy_statement(item.invoice_due_date),
        "allowed_free_time_days": truthy_statement(item.allowed_free_time_days),
        "free_time_start_date": truthy_statement(item.free_time_start_date),
        "free_time_end_date": truthy_statement(item.free_time_end_date),
        "charged_dates": truthy_statement(item.charged_dates),
        "total_amount": truthy_statement(item.total_amount),
        "governing_rule_reference": truthy_statement(item.governing_rule_reference),
        "specific_rates": truthy_statement(item.specific_rates),
        "dispute_contact": truthy_statement(item.dispute_contact),
        "dispute_instructions_url": truthy_statement(item.dispute_instructions_url),
        "mitigation_request_window_days": truthy_statement(
            item.mitigation_request_window_days
        ),
        "mitigation_resolution_window_days": (
            truthy_statement(item.mitigation_resolution_window_days)
            or truthy_statement(item.later_resolution_date_agreed)
        ),
        "certification_fmc_rules": truthy_statement(item.certification_fmc_rules),
        "certification_billing_party_no_contribution": truthy_statement(
            item.certification_billing_party_no_contribution
        ),
    }

    if movement == "import":
        fields["discharge_ports"] = truthy_statement(item.discharge_ports)
        fields["container_availability_date"] = truthy_statement(
            item.container_availability_date
        )
    elif movement == "export":
        fields["earliest_return_date"] = truthy_statement(item.earliest_return_date)
    else:
        fields["movement_import_or_export"] = False

    return fields


def audit_invoice(item: DDInvoiceInput) -> dict[str, Any]:
    invoice_date = parse_date(item.invoice_date, required=True)
    assert invoice_date is not None
    total = parse_decimal(item.total_amount, required=True)
    assert total is not None

    base = {
        "invoice_id": item.invoice_id,
        "billing_party_type": item.billing_party_type.lower().strip(),
        "billed_party_type": (item.billed_party_type or "").lower().strip(),
        "charge_type": item.charge_type.lower().strip(),
        "invoice_date": invoice_date.isoformat(),
        "total_amount": str(total),
        "currency": item.currency.upper().strip(),
        "regulatory_references": REGULATORY_REFERENCES,
        "regulatory_source": PART_541_URL,
        "asserted_recovery": "0.00",
        "potential_charge_relief_amount": "0.00",
        "excluded_rule_note": (
            "No §541.4 proper-party determination is made by this engine."
        ),
    }

    if invoice_date < FULL_RULE_EFFECTIVE_DATE:
        return {
            **base,
            "status": "OUTSIDE_FULL_PART_541_EFFECTIVE_PERIOD",
            "rule_effective_date": FULL_RULE_EFFECTIVE_DATE.isoformat(),
        }

    if base["billing_party_type"] not in {"vocc", "nvocc", "mto"}:
        return {**base, "status": "INVALID_BILLING_PARTY_TYPE"}
    if base["charge_type"] not in {"demurrage", "detention"}:
        return {**base, "status": "NOT_DEMURRAGE_OR_DETENTION"}

    # 46 CFR 541.2(b) excludes billing relationships among and between
    # ocean common carriers and MTOs. Merely knowing the party types cannot
    # independently verify their legal relationship; hold rather than rate it.
    # This is a scope question, NOT the vacated 541.4 proper-party rule.
    billed_type = base["billed_party_type"]
    if billed_type in {"vocc", "nvocc", "mto"}:
        return {
            **base,
            "status": "INTERCARRIER_TERMINAL_SCOPE_REVIEW",
            "scope_note": "Potential 46 CFR 541.2(b) exclusion; billing relationship evidence required.",
        }
    if billed_type not in {
        "shipper", "consignee", "cargo_owner", "freight_forwarder",
        "truck_operator",
    }:
        return {
            **base,
            "status": "BILLING_RELATIONSHIP_UNVERIFIED_REVIEW",
            "scope_note": "Billed party category missing or unknown; cannot apply Part 541 or infer relief.",
        }

    # Numeric values and dates in a field must be valid, not merely nonblank.
    # If contradictory source dates are present, route to source review
    # without calculating an unsupported potential dollar recovery.
    source_date_issues: list[str] = []
    due = parse_date(item.invoice_due_date)
    free_start = parse_date(item.free_time_start_date)
    free_end = parse_date(item.free_time_end_date)
    for date_value in (item.container_availability_date,
                       item.earliest_return_date,
                       item.later_resolution_date_agreed):
        parse_date(date_value)
    integer_days(item.allowed_free_time_days)
    if due is not None and due < invoice_date:
        source_date_issues.append("invoice_due_date_before_invoice_date")
    if free_start is not None and free_end is not None and free_end < free_start:
        source_date_issues.append("free_time_end_before_free_time_start")

    presence = required_content_fields(item)
    missing = sorted(field for field, present in presence.items() if not present)

    request_days = integer_days(item.mitigation_request_window_days)
    resolution_days = integer_days(item.mitigation_resolution_window_days)
    dispute_issues: list[str] = []
    if request_days is not None and request_days < 30:
        dispute_issues.append("mitigation_request_window_under_30_days")
    if (
        resolution_days is not None
        and resolution_days > 30
        and not truthy_statement(item.later_resolution_date_agreed)
    ):
        dispute_issues.append(
            "mitigation_resolution_window_over_30_days_without_later_agreement"
        )

    timing_basis = None
    timing_basis_date = None
    if base["billing_party_type"] == "nvocc":
        timing_basis = "upstream_invoice_date"
        timing_basis_date = parse_date(item.upstream_invoice_date)
    else:
        timing_basis = "charge_last_incurred_date"
        timing_basis_date = parse_date(item.charge_last_incurred_date)

    late_invoice = None
    days_to_issue = None
    if timing_basis_date is not None:
        days_to_issue = (invoice_date - timing_basis_date).days
        if days_to_issue < 0:
            source_date_issues.append(
                "invoice_date_before_upstream_invoice_date"
                if base["billing_party_type"] == "nvocc"
                else "invoice_date_before_charge_last_incurred_date"
            )
        late_invoice = days_to_issue > 30
    elif base["billing_party_type"] == "nvocc":
        # A missing upstream invoice date prevents §541.7(b) timing verification;
        # it is not itself one of §541.6's invoice-content fields.
        timing_basis = "upstream_invoice_date_missing"
    else:
        timing_basis = "charge_last_incurred_date_missing"

    findings: list[dict[str, Any]] = []
    if missing:
        findings.append(
            {
                "code": "MISSING_REQUIRED_INVOICE_INFORMATION",
                "citation": "46 CFR 541.5 / 541.6",
                "missing_fields": missing,
            }
        )
    if dispute_issues:
        findings.append(
            {
                "code": "DISPUTE_WINDOW_NONCOMPLIANCE",
                "citation": "46 CFR 541.8",
                "issues": dispute_issues,
            }
        )
    if late_invoice is True and not source_date_issues:
        findings.append(
            {
                "code": "LATE_INVOICE",
                "citation": "46 CFR 541.7",
                "timing_basis": timing_basis,
                "timing_basis_date": timing_basis_date.isoformat(),
                "days_to_issue": days_to_issue,
            }
        )

    if source_date_issues:
        findings.append({
            "code": "SOURCE_DATE_INCONSISTENCY",
            "citation": None,
            "issues": source_date_issues,
        })
    relief_trigger = (bool(missing) or late_invoice is True) and not source_date_issues
    status = "COMPLIANT_ON_CHECKED_FIELDS"
    if source_date_issues:
        status = "SOURCE_TIMELINE_INCONSISTENCY_REVIEW"
    elif relief_trigger:
        status = "POTENTIAL_NO_PAYMENT_OBLIGATION_REVIEW"
    elif dispute_issues:
        status = "PROCESS_NONCOMPLIANCE_REVIEW"
    elif timing_basis_date is None:
        status = "CONTENT_COMPLETE_TIMING_UNVERIFIABLE"

    return {
        **base,
        "status": status,
        "required_field_presence": presence,
        "missing_required_fields": missing,
        "source_date_issues": source_date_issues,
        "timing_basis": timing_basis,
        "timing_basis_date": (
            timing_basis_date.isoformat() if timing_basis_date else None
        ),
        "days_to_issue": days_to_issue,
        "findings": findings,
        "potential_charge_relief_amount": str(total if relief_trigger else Decimal("0.00")),
        "review_note": (
            "Potential relief amount is the applicable D&D charge under review, not an "
            "asserted recovery. Verify source invoice, dates, amendments, customer contract, "
            "and current law before action."
        ),
    }


def load_csv(path: Path) -> list[DDInvoiceInput]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "invoice_id",
            "billing_party_type",
            "charge_type",
            "invoice_date",
            "invoice_due_date",
            "total_amount",
            "currency",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing CSV columns: {sorted(missing)}")

        fields = set(DDInvoiceInput.__dataclass_fields__)
        rows = []
        for raw in reader:
            kwargs = {
                name: (raw.get(name) or "")
                for name in fields
            }
            rows.append(DDInvoiceInput(**kwargs))
        return rows


def audit_many(items: Iterable[DDInvoiceInput]) -> list[dict[str, Any]]:
    return [audit_invoice(item) for item in items]


def main() -> int:
    p = argparse.ArgumentParser(description="Audit FMC D&D invoice compliance")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    results = audit_many(load_csv(Path(args.input_csv)))
    summary: dict[str, int] = {}
    potential = Decimal("0.00")
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1
        potential += Decimal(result["potential_charge_relief_amount"])

    payload = {
        "summary": summary,
        "asserted_recovery_total": "0.00",
        "potential_charge_relief_total": str(
            potential.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        "results": results,
    }
    Path(args.output).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "rows": len(results),
            "summary": summary,
            "potential_charge_relief_total": payload["potential_charge_relief_total"],
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
