"""Source-bound GAO motor-freight numerical evidence; NOT contemporary invoice truth.

This module uses five named public GAO decisions, preserving reported amounts,
historical tariff contexts, ambiguous totals, and explicit litigation caveats.
It neither downloads original invoice documents nor establishes commercial
reuse permission, present-day customer overcharges or recoveries.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from freight.unified_research_lab import ROOT, ResearchError, digest, safe_url

FIXTURE = Path(__file__).with_name("fixtures") / "gao_motor_freight_numeric_v1.json"
OUTPUT = ROOT / "gao_motor_freight_numeric_v1.json"
SCOPE = "GAO_HISTORICAL_DECISION_LEVEL_NUMERIC_EVIDENCE_NOT_CUSTOMER_INVOICE_TRUTH"
RIGHTS = "https://www.gao.gov/copyright"

# Independent, fixed source-review controls prevent an altered fixture (even
# with a recomputed manifest hash) from manufacturing numerical truth.
PINNED = {
    "B-191257": {
        "decision_date": "1978-07-03",
        "official_url": "https://www.gao.gov/products/b-191257",
        "historical_issue": "CARRIER_ROUTE_TENDER_APPLICABILITY",
        "historical_tariff": "ROCKY_MOUNTAIN_MOTOR_TARIFF_BUREAU_QUOTATION_19_B_ITEM_1720",
        "shipment_count": 1, "reported_paid_cents": 82800,
        "reported_audit_charge_cents": 79600,
        "reported_offset_deduction_cents": 3200,
        "reported_paid_rate_cents_per_cwt": None,
        "reported_alternative_rate_cents_per_cwt": None,
        "claim_amount_variants_cents": [],
        "decision_as_published": "GSA_SETTLEMENT_SUSTAINED",
        "further_review_explicitly_reserved": False,
        "per_shipment_deduction_allocation_known": True,
    },
    "B-152744": {
        "decision_date": "1964-04-29",
        "official_url": "https://www.gao.gov/products/b-152744-0",
        "historical_issue": "EXCLUSIVE_USE_VS_TRUCKLOAD_FULL_VEHICLE",
        "historical_tariff": "EASTERN_CENTRAL_MOTOR_CARRIERS_ASSOCIATION_TARIFF_35_D_ITEM_84",
        "shipment_count": 1, "reported_paid_cents": 61180,
        "reported_audit_charge_cents": None,
        "reported_offset_deduction_cents": 12220,
        "reported_paid_rate_cents_per_cwt": None,
        "reported_alternative_rate_cents_per_cwt": None,
        "claim_amount_variants_cents": [],
        "decision_as_published": "CARRIER_RECLAIM_DISALLOWED_PENDING_RELATED_LITIGATION",
        "further_review_explicitly_reserved": True,
        "per_shipment_deduction_allocation_known": True,
    },
    "B-148465": {
        "decision_date": "1962-08-27",
        "official_url": "https://www.gao.gov/products/b-148465",
        "historical_issue": "MISROUTING_AND_CARRIER_RATE_RESPONSIBILITY",
        "historical_tariff": "ROCKY_MOUNTAIN_MOTOR_TARIFF_BUREAU_TRANSCONTINENTAL_CLASS_TARIFF_21_B_ITEM_300",
        "shipment_count": 1, "reported_paid_cents": 54688,
        "reported_audit_charge_cents": None,
        "reported_offset_deduction_cents": 6122,
        "reported_paid_rate_cents_per_cwt": None,
        "reported_alternative_rate_cents_per_cwt": None,
        "claim_amount_variants_cents": [],
        "decision_as_published": "CARRIER_RECLAIM_DISALLOWED_WITH_SUPREME_COURT_REVIEW_CAVEAT",
        "further_review_explicitly_reserved": True,
        "per_shipment_deduction_allocation_known": True,
    },
    "B-143048": {
        "decision_date": "1960-09-01",
        "official_url": "https://www.gao.gov/products/b-143048",
        "historical_issue": "MISROUTING_TWO_HOUSEHOLD_GOODS_SHIPMENTS",
        "historical_tariff": "ROCKY_MOUNTAIN_MOTOR_TARIFF_BUREAU_US_GOVERNMENT_QUOTATION_43_D_ITEM_6980",
        "shipment_count": 2, "reported_paid_cents": None,
        "reported_audit_charge_cents": None,
        "reported_offset_deduction_cents": 13030,
        "reported_paid_rate_cents_per_cwt": 1069,
        "reported_alternative_rate_cents_per_cwt": 765,
        "claim_amount_variants_cents": [],
        "decision_as_published": "GSA_SETTLEMENT_SUSTAINED_TWO_SHIPMENTS_AGGREGATE_ONLY",
        "further_review_explicitly_reserved": False,
        "per_shipment_deduction_allocation_known": False,
    },
    "B-146511": {
        "decision_date": "1965-06-02",
        "official_url": "https://www.gao.gov/products/b-146511-2",
        "historical_issue": "BILL_OF_LADING_NOTATION_CEILING_RECLAIM",
        "historical_tariff": "CALIFORNIA_RAILROAD_COMMISSION_TARIFF_2",
        "shipment_count": 1, "reported_paid_cents": 15205,
        "reported_audit_charge_cents": None,
        "reported_offset_deduction_cents": 2074,
        "reported_paid_rate_cents_per_cwt": None,
        "reported_alternative_rate_cents_per_cwt": None,
        "claim_amount_variants_cents": [2070, 2074, 2076],
        "decision_as_published": "CARRIER_RECONSIDERATION_REFUSED_REPORTED_CLAIM_AMOUNTS_CONFLICT",
        "further_review_explicitly_reserved": False,
        "per_shipment_deduction_allocation_known": True,
    },
}
COMMON = {
    "publisher": "U.S. Government Accountability Office",
    "source_kind": "PUBLIC_GAO_DECISION_HTML_TEXT",
    "source_original_bytes_sha256": None,
    "commercial_reuse_approved_for_customer_engine": False,
    "modern_rate_authority": False,
    "independent_original_invoice_custody": False,
}
EXPECTED_ROOT = frozenset({
    "schema_version", "fixture_id", "scope", "publisher",
    "rights_reference_url", "as_of_decision_status", "cases", "limitations",
    "commercial_reuse_approved_for_customer_engine", "original_document_bytes_stored",
    "real_customer_invoice_records", "independent_invoice_outcome_labels",
    "verified_retally_recovered_cash_cents",
})
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "observed_at_utc_date", "case_count",
    "case_receipts", "exact_publisher_stated_arithmetic_cases",
    "historical_reported_deductions_sum_cents_not_retally_revenue",
    "multi_shipment_aggregate_cases", "conflicting_amount_cases",
    "explicit_later_review_caveat_cases",
    "source_fixture_authored_sha256_not_publisher_bytes",
    "source_original_document_bytes_stored", "historical_only",
    "source_specific_commercial_rights_verified",
    "independent_customer_invoice_truth_cases", "verified_retally_recovered_cash_cents",
    "production_engine_changes", "customer_contact_actions", "limitations",
    "receipt_sha256",
})


def load_fixture(path: Path | None = None) -> dict:
    path = FIXTURE if path is None else path
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("GAO_NUMERIC_FIXTURE_MISSING_OR_INVALID") from exc
    validate_fixture(result)
    return result


def validate_fixture(doc: dict) -> None:
    if type(doc) is not dict or frozenset(doc) != EXPECTED_ROOT:
        raise ResearchError("GAO_NUMERIC_FIXTURE_SCHEMA_INVALID")
    if (type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or doc["fixture_id"] != "GAO_MOTOR_FREIGHT_REPORTED_NUMERIC_DECISIONS_V1"
            or doc["scope"] != SCOPE
            or doc["publisher"] != "U.S. Government Accountability Office"
            or doc["rights_reference_url"] != RIGHTS
            or doc["as_of_decision_status"] !=
                "PUBLISHER_REPORTED_HISTORICAL_ONLY_FURTHER_LITIGATION_NOT_EXHAUSTIVELY_CHECKED"
            or type(doc["limitations"]) is not list or len(doc["limitations"]) != 6
            or doc["commercial_reuse_approved_for_customer_engine"] is not False
            or doc["original_document_bytes_stored"] != 0
            or doc["real_customer_invoice_records"] != 0
            or doc["independent_invoice_outcome_labels"] != 0
            or doc["verified_retally_recovered_cash_cents"] != 0):
        raise ResearchError("GAO_NUMERIC_FIXTURE_CLAIMS_UNSUPPORTED")
    cases = doc.get("cases")
    if type(cases) is not list or len(cases) != len(PINNED):
        raise ResearchError("GAO_NUMERIC_CASE_COUNT_MISMATCH")
    if [case.get("case_number") if type(case) is dict else None
            for case in cases] != list(PINNED):
        raise ResearchError("GAO_NUMERIC_CASE_ORDER_OR_ID_MISMATCH")
    for item in cases:
        ident = item["case_number"]
        if frozenset(item) != frozenset({"case_number", *PINNED[ident], *COMMON}):
            raise ResearchError("GAO_NUMERIC_CASE_SCHEMA_INVALID")
        if any(type(value) is bool or type(value) is float
               for key, value in item.items()
               if key.endswith("_cents") and value is not None):
            raise ResearchError("GAO_NUMERIC_AMOUNT_TYPE_INVALID")
        if ({k: item[k] for k in PINNED[ident]} != PINNED[ident]
                or any(item[k] != val for k, val in COMMON.items())):
            raise ResearchError("GAO_NUMERIC_CASE_SOURCE_OR_AMOUNT_TAMPERED")
        if safe_url(item["official_url"]) != item["official_url"]:
            raise ResearchError("GAO_NUMERIC_SOURCE_URL_INVALID")
        if (item["reported_audit_charge_cents"] is not None
                and item["reported_paid_cents"] -
                item["reported_audit_charge_cents"] !=
                item["reported_offset_deduction_cents"]):
            raise ResearchError("GAO_NUMERIC_REPORTED_ARITHMETIC_MISMATCH")


def make_receipt(at_date: date, *, fixture: dict | None = None) -> dict:
    if (type(at_date) is not date
            or at_date < date(2026, 10, 24)
            or at_date > datetime.now(timezone.utc).date()):
        raise ResearchError("GAO_NUMERIC_RECEIPT_DATE_INVALID")
    source = load_fixture() if fixture is None else fixture
    validate_fixture(source)
    rows = []
    for item in source["cases"]:
        confirmed_numeric = item["reported_audit_charge_cents"] is not None
        rows.append({
            "case_number": item["case_number"],
            "official_url": item["official_url"],
            "decision_date": item["decision_date"],
            "shipment_count": item["shipment_count"],
            "reported_paid_cents": item["reported_paid_cents"],
            "reported_audit_charge_cents": item["reported_audit_charge_cents"],
            "reported_offset_deduction_cents": item["reported_offset_deduction_cents"],
            "numeric_reconciliation": ("EXACT_PUBLISHER_REPORTED_CHARGES_MATCH"
                                       if confirmed_numeric else
                                       "NO_EXACT_AUDITED_CHARGE_RECONSTRUCTION"),
            "per_shipment_allocation_supported": item["per_shipment_deduction_allocation_known"],
            "future_review_caveat": item["further_review_explicitly_reserved"],
            "reported_claim_amount_conflict": bool(item["claim_amount_variants_cents"]),
            "historical_decision_as_published": item["decision_as_published"],
            "historical_tariff": item["historical_tariff"],
            "independent_original_invoice_custody": False,
            "modern_tariff_rule": False,
            "customer_recovery_cents": 0,
        })
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "observed_at_utc_date": at_date.isoformat(),
        "case_count": len(rows),
        "case_receipts": rows,
        "exact_publisher_stated_arithmetic_cases":
            sum(r["numeric_reconciliation"] == "EXACT_PUBLISHER_REPORTED_CHARGES_MATCH" for r in rows),
        "historical_reported_deductions_sum_cents_not_retally_revenue":
            sum(r["reported_offset_deduction_cents"] for r in rows),
        "multi_shipment_aggregate_cases": sum(r["shipment_count"] > 1 for r in rows),
        "conflicting_amount_cases": sum(r["reported_claim_amount_conflict"] for r in rows),
        "explicit_later_review_caveat_cases": sum(r["future_review_caveat"] for r in rows),
        "source_fixture_authored_sha256_not_publisher_bytes":
            digest(source),
        "source_original_document_bytes_stored": 0,
        "historical_only": True,
        "source_specific_commercial_rights_verified": False,
        "independent_customer_invoice_truth_cases": 0,
        "verified_retally_recovered_cash_cents": 0,
        "production_engine_changes": 0,
        "customer_contact_actions": 0,
        "limitations": source["limitations"],
    }
    return {**body, "receipt_sha256": digest(body)}


def validate_receipt(doc: dict, *, at_date: date | None = None) -> dict:
    if type(doc) is not dict or frozenset(doc) != RECEIPT_KEYS:
        raise ResearchError("GAO_NUMERIC_RECEIPT_SCHEMA_INVALID")
    try:
        observed = date.fromisoformat(doc["observed_at_utc_date"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ResearchError("GAO_NUMERIC_RECEIPT_DATE_INVALID") from exc
    today = at_date or datetime.now(timezone.utc).date()
    if observed > today or (today - observed).days > 2:
        raise ResearchError("GAO_NUMERIC_RECEIPT_STALE_OR_FUTURE")
    if make_receipt(observed) != doc:
        raise ResearchError("GAO_NUMERIC_RECEIPT_TAMPERED")
    return doc


def run(*, output: Path = OUTPUT, verify_only: bool = False,
        at_date: date | None = None) -> dict:
    if verify_only:
        if not output.is_file():
            raise ResearchError("GAO_NUMERIC_RECEIPT_MISSING")
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResearchError("GAO_NUMERIC_RECEIPT_INVALID") from exc
        validate_receipt(data, at_date=at_date)
    else:
        data = make_receipt(at_date or datetime.now(timezone.utc).date())
        output.parent.mkdir(parents=True, exist_ok=True)
        target = output.with_suffix(".tmp")
        target.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        target.replace(output)
    return {
        "case_count": data["case_count"],
        "reported_exact_arithmetic_cases": data["exact_publisher_stated_arithmetic_cases"],
        "multi_shipment_aggregate_cases": data["multi_shipment_aggregate_cases"],
        "reported_amount_conflict_cases": data["conflicting_amount_cases"],
        "explicit_future_review_caveat_cases": data["explicit_later_review_caveat_cases"],
        "independent_customer_invoice_truth_cases": 0,
        "verified_retally_recovered_cash_cents": 0,
        "commercial_reuse_approved_for_customer_engine": False,
        "verified": verify_only,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(output=args.output, verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
