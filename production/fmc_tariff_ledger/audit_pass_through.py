#!/usr/bin/env python3
"""Evidence-first NVOCC pass-through charge audit.

This module is a deterministic screening engine, not a legal conclusion.
It requires:
1. entity-specific, effectively-dated NVOCC tariff evidence for pass-through treatment;
2. the billed charge/category to be represented in that evidence;
3. effectively-dated upstream VOCC tariff evidence;
4. one unambiguous upstream monetary rate for the requested rule/currency/basis.

Only then can it compute a potential markup delta. Separate NVOCC service fees remain
outside the pass-through comparison and must be reviewed as distinct line items.

Regulatory references (current rule text should always be verified at review time):
- 46 CFR 520.7(a)(3)(iv)
- 46 CFR 520.7(c)
- 46 CFR 520.7(h)
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

import resolve


REGULATORY_REFERENCES = [
    {
        "citation": "46 CFR 520.7(a)(3)(iv)",
        "url": "https://www.ecfr.gov/current/title-46/chapter-IV/subchapter-B/part-520/section-520.7",
        "purpose": "NVOCC cross-reference of published/effective VOCC surcharges, assessorial charges, and GRIs; listed categories; no markup above cost; separate service fee distinction.",
    },
    {
        "citation": "46 CFR 520.7(c)",
        "url": "https://www.ecfr.gov/current/title-46/chapter-IV/subchapter-B/part-520/section-520.7",
        "purpose": "Shipment uses rates, charges, and rules in effect on cargo-receipt date.",
    },
    {
        "citation": "46 CFR 520.7(h)",
        "url": "https://www.ecfr.gov/current/title-46/chapter-IV/subchapter-B/part-520/section-520.7",
        "purpose": "Collection-agent pass-through of specified upstream ocean-carrier charges; listed categories; no markup above cost.",
    },
]

CATEGORY_TERMS = {
    "demurrage": ("demurrage",),
    "detention": ("detention",),
    "free_time": ("free time", "free days"),
    "storage": ("storage",),
    "terminal_handling": ("terminal", "terminal handling", "thc"),
    "wharfage": ("wharfage",),
    "dockage": ("dockage",),
    "documentation": ("documentation", "document", "bill of lading", "b/l"),
    "fuel_surcharge": ("fuel", "bunker", "baf", "surcharge"),
    "chassis": ("chassis",),
    "reefer": ("reefer", "refrigerat", "genset"),
    "hazardous": ("hazardous", "hazmat", "dangerous goods", "dg"),
    "congestion": ("congestion",),
    "security": ("security", "isps"),
    "seal": ("seal",),
    "equipment": ("equipment",),
    "inland_haulage": ("inland haulage", "merchant haulage", "carrier haulage"),
    "cfs": ("cfs", "container freight station"),
    "general_rate": ("general rate increase", "gri", "surcharge", "assessorial", "accessorial"),
    "canal_toll": ("canal", "toll"),
}


@dataclass(frozen=True)
class AuditInput:
    invoice_line_id: str
    nvocc_organization_no: str
    upstream_vocc_organization_no: str
    cargo_received_date: str
    rule_type: str
    billed_amount: str
    currency: str
    invoice_id: str = ""
    quantity: str = "1"
    unit: str | None = None
    separately_disclosed_service_fee: str = "0"


def money(value: str | int | float | Decimal) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc


def quantity(value: str | int | float | Decimal) -> Decimal:
    try:
        q = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid quantity: {value!r}") from exc
    if q <= 0:
        raise ValueError("quantity must be > 0")
    return q


def category_is_listed(rule_type: str, pass_through_candidates: list[dict[str, Any]]) -> bool:
    needles = CATEGORY_TERMS.get(rule_type, (rule_type.replace("_", " "),))
    for candidate in pass_through_candidates:
        text = (candidate.get("evidence_excerpt") or "").lower()
        if any(needle.lower() in text for needle in needles):
            return True
    return False


def _unit_matches(requested: str | None, candidate: str | None) -> bool:
    if not requested:
        return True
    if not candidate:
        return False

    def norm(value: str) -> str:
        return (
            value.lower()
            .replace("calendar ", "")
            .replace("/", "per ")
            .replace("-", " ")
            .replace("  ", " ")
            .strip()
        )

    return norm(requested) in norm(candidate) or norm(candidate) in norm(requested)


def unique_monetary_rate(
    result: dict[str, Any],
    currency: str,
    requested_unit: str | None,
) -> tuple[str, Decimal | None, list[dict[str, Any]]]:
    if result.get("status") != "RESOLVED":
        return result.get("status", "UNRESOLVED"), None, []

    candidates = [
        candidate
        for candidate in result.get("candidates", [])
        if candidate.get("term_kind") == "money"
        and (candidate.get("currency") or "").upper() == currency.upper()
        and _unit_matches(requested_unit, candidate.get("unit"))
        and candidate.get("amount_value") is not None
    ]
    rates: dict[Decimal, list[dict[str, Any]]] = {}
    for candidate in candidates:
        try:
            value = money(candidate["amount_value"])
        except ValueError:
            continue
        rates.setdefault(value, []).append(candidate)

    if not rates:
        return "NO_MONETARY_RATE", None, candidates
    if len(rates) > 1:
        return "AMBIGUOUS_PRICE", None, candidates
    value = next(iter(rates))
    return "RESOLVED", value, rates[value]


def audit_one(conn: sqlite3.Connection, item: AuditInput) -> dict[str, Any]:
    currency = item.currency.upper().strip()
    billed = money(item.billed_amount)
    q = quantity(item.quantity)
    separate_fee = money(item.separately_disclosed_service_fee)

    nvocc_pass = resolve.resolve_rule(
        conn,
        item.nvocc_organization_no,
        item.cargo_received_date,
        "pass_through",
        min_confidence=0.78,
    )

    base = {
        "invoice_id": item.invoice_id or None,
        "invoice_line_id": item.invoice_line_id,
        "nvocc_organization_no": item.nvocc_organization_no,
        "upstream_vocc_organization_no": item.upstream_vocc_organization_no,
        "cargo_received_date": item.cargo_received_date,
        "rule_type": item.rule_type,
        "currency": currency,
        "billed_amount": str(billed),
        "quantity": str(q),
        "unit": item.unit,
        "separately_disclosed_service_fee": str(separate_fee),
        "regulatory_references": REGULATORY_REFERENCES,
        "nvocc_pass_through_authority": nvocc_pass,
        "asserted_recovery": "0.00",
    }

    nvocc_status = nvocc_pass.get("status")
    if nvocc_status == "AMBIGUOUS_AUTHORITY":
        return {**base, "status": "AMBIGUOUS_NVOCC_AUTHORITY"}
    if nvocc_status == "UNDATED_ONLY":
        return {**base, "status": "UNDATED_NVOCC_PASSTHROUGH_RULE"}
    if nvocc_status != "RESOLVED":
        return {**base, "status": "NO_PROVEN_NVOCC_PASSTHROUGH_RULE"}

    if not category_is_listed(item.rule_type, nvocc_pass.get("candidates", [])):
        return {**base, "status": "CHARGE_CATEGORY_NOT_PROVEN_LISTED"}

    upstream = resolve.resolve_rule(
        conn,
        item.upstream_vocc_organization_no,
        item.cargo_received_date,
        item.rule_type,
        currency=currency,
        min_confidence=0.80,
    )
    base["upstream_rule_authority"] = upstream

    if upstream.get("status") == "AMBIGUOUS_AUTHORITY":
        return {**base, "status": "AMBIGUOUS_UPSTREAM_AUTHORITY"}
    if upstream.get("status") == "UNDATED_ONLY":
        return {**base, "status": "UNDATED_UPSTREAM_RULE"}
    if upstream.get("status") != "RESOLVED":
        return {**base, "status": "NO_EFFECTIVE_UPSTREAM_RULE"}

    rate_status, upstream_rate, rate_evidence = unique_monetary_rate(
        upstream,
        currency,
        item.unit,
    )
    base["upstream_price_evidence"] = rate_evidence
    if rate_status != "RESOLVED" or upstream_rate is None:
        return {**base, "status": rate_status}

    upstream_total = (upstream_rate * q).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    delta = (billed - upstream_total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    base.update(
        {
            "upstream_unit_rate": str(upstream_rate),
            "upstream_expected_total": str(upstream_total),
            "potential_markup_delta": str(max(delta, Decimal("0.00"))),
        }
    )

    if delta <= 0:
        return {**base, "status": "NO_PASS_THROUGH_OVERAGE"}

    # A separate, explicitly disclosed service fee is intentionally not netted
    # against the pass-through charge. It remains a separate item for contract/tariff review.
    return {
        **base,
        "status": "POTENTIAL_PASS_THROUGH_MARKUP_REVIEW",
        "review_note": (
            "Evidence supports a billed pass-through amount above one unambiguous "
            "upstream effective rate. Human review must confirm invoice classification, "
            "billing basis/slab, customer contract precedence, and that any NVOCC service "
            "fee is truly separate before asserting a recovery."
        ),
    }


def audit_many(conn: sqlite3.Connection, items: Iterable[AuditInput]) -> list[dict[str, Any]]:
    return [audit_one(conn, item) for item in items]


def load_csv(path: Path) -> list[AuditInput]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "invoice_line_id",
            "nvocc_organization_no",
            "upstream_vocc_organization_no",
            "cargo_received_date",
            "rule_type",
            "billed_amount",
            "currency",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing CSV columns: {sorted(missing)}")

        items = []
        for row in reader:
            items.append(
                AuditInput(
                    invoice_line_id=row["invoice_line_id"],
                    nvocc_organization_no=row["nvocc_organization_no"],
                    upstream_vocc_organization_no=row["upstream_vocc_organization_no"],
                    cargo_received_date=row["cargo_received_date"],
                    rule_type=row["rule_type"],
                    billed_amount=row["billed_amount"],
                    currency=row["currency"],
                    invoice_id=row.get("invoice_id") or "",
                    quantity=row.get("quantity") or "1",
                    unit=row.get("unit") or None,
                    separately_disclosed_service_fee=(
                        row.get("separately_disclosed_service_fee") or "0"
                    ),
                )
            )
        return items


def main() -> int:
    p = argparse.ArgumentParser(description="Audit NVOCC pass-through tariff charges")
    p.add_argument("--db", required=True)
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    results = audit_many(conn, load_csv(Path(args.input_csv)))
    conn.close()

    summary: dict[str, int] = {}
    for row in results:
        summary[row["status"]] = summary.get(row["status"], 0) + 1

    payload = {
        "summary": summary,
        "asserted_recovery_total": "0.00",
        "results": results,
    }
    Path(args.output).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary": summary, "rows": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
