"""Bounded historical GAO billing adjudications, never private customer invoice labels.

These cases use independently published GAO reviews of GSA/carrier disputes,
not independently collected original invoice, tariff, or bank bytes. A reported
government deduction must NEVER be counted as recovered RETALLY cash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).with_name("fixtures") / "gao_adjudicated_billing_cases_v1.json"
SCOPE = "THIRD_PARTY_ADJUDICATED_HISTORICAL_GSA_CARRIER_BILLING_NOT_CURRENT_CUSTOMER_TRUTH"
LABEL_POS = "HISTORICAL_OVERCHARGE_SUSTAINED"
LABEL_NEG = "HISTORICAL_AUDIT_FALSE_POSITIVE"

# Source-reviewed immutable anchors, separate from the authored JSON fixture.
# The original GAO HTML bytes, invoice face, signed BOL and bank records are NOT
# in repository custody, so this table is NOT independent source-byte proof.
PINNED = {
    "B-191257": {
        "source_url": "https://www.gao.gov/products/b-191257",
        "decision_date": "1978-07-03",
        "carrier": "YELLOW_FREIGHT_SYSTEM",
        "reported_gbl": "K-3087713",
        "reported_gbl_date": "1975-08-26",
        "reported_weight_lb": 13003,
        "reported_billed_and_paid_cents": 82800,
        "reported_gsa_audited_cents": 79600,
        "reported_gsa_deducted_cents": 3200,
        "ga_review_outcome": "GSA_OVERCHARGE_DEDUCTION_SUSTAINED",
        "adjudicated_historical_label": LABEL_POS,
        "rate_authority": "RMB_QUOTATION_19_B_ITEM_1720",
        "money_calculation": "PUBLISHER_EXPLICIT",
    },
    "B-160344": {
        "source_url": "https://www.gao.gov/products/b-160344",
        "decision_date": "1967-07-18",
        "carrier": "GEORGIA_HIGHWAY_EXPRESS",
        "reported_gbl": "B-5378637",
        "reported_gbl_date": "1962-12-19",
        "reported_weight_lb": 1485,
        "reported_billed_and_paid_cents": 27517,
        "reported_gsa_audited_cents": 13929,
        "reported_gsa_deducted_cents": 13588,
        "ga_review_outcome": "GSA_CLASSIFICATION_DEDUCTION_SUSTAINED",
        "adjudicated_historical_label": LABEL_POS,
        "rate_authority": "NMFC_ITEM_14440_CLASS400_VERSUS_12400_CLASS200",
        "money_calculation": "PUBLISHER_EXPLICIT",
    },
    "B-221594": {
        "source_url": "https://www.gao.gov/products/b-221594-0",
        "decision_date": "1986-09-29",
        "carrier": "RISS_INTERNATIONAL",
        "reported_gbl": None,  # Printed GBL is OCR-ambiguous; do not invent custody.
        "reported_gbl_date": "1983-09-07",
        "reported_weight_lb": 27792,
        "reported_billed_and_paid_cents": 94200,
        "reported_gsa_audited_cents": 72125,
        "reported_gsa_deducted_cents": 22075,
        "ga_review_outcome": "GSA_DEDUCTION_INVALID_REJECTED_TENDER",
        "adjudicated_historical_label": LABEL_NEG,
        "rate_authority": "ICC_TENDER_1544_REJECTED_BY_MTMC",
        "money_calculation": "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION",
    },
}
ROOT_KEYS = frozenset({
    "schema_version", "fixture_id", "scope", "publisher_independence",
    "source_limits", "source_common", "cases",
    "historical_government_deductions_are_retally_cash",
    "independent_original_invoice_and_bank_custody",
    "independent_current_customer_invoice_accuracy_cases",
    "verified_retally_cash_cents", "production_rate_or_dispute_actions_allowed",
    "rights_clearance_for_current_customer_engine",
})
SOURCE_KEYS = frozenset({
    "publisher", "source_format", "review_date_utc",
    "original_gao_response_bytes_sha256",
    "original_invoice_gbl_tariff_bytes_in_custody",
    "source_link_is_original_transaction_document",
    "commercial_customer_use_rights_verified",
})
CASE_KEYS = frozenset({"id", *next(iter(PINNED.values())).keys(), "source_money_note"})
RECEIPT_KEYS = frozenset({
    "scope", "schema_version", "case_count", "case_outcomes",
    "sustained_overcharges_historical_cents",
    "invalid_government_deductions_historical_cents",
    "historical_agency_deductions_total_cents_not_retally_cash",
    "external_gao_adjudicated_historical_cases",
    "source_original_invoice_rate_bank_chain_verified_cases",
    "private_customer_benchmark_truth_cases", "retally_recovered_cash_cents",
    "production_rating_or_dispute_allowed", "commercial_reuse_approved",
    "source_original_gao_response_sha256", "fixture_authored_sha256",
    "receipt_sha256",
})


class EvidenceError(ValueError):
    pass


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def validate_fixture(data: object) -> dict:
    if type(data) is not dict or frozenset(data) != ROOT_KEYS:
        raise EvidenceError("INVALID_GAO_BILLING_ROOT_SCHEMA")
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
        or data["fixture_id"] != "GAO_INDEPENDENT_HISTORICAL_FREIGHT_BILLING_ADJUDICATION_V1"
        or data["scope"] != SCOPE or type(data["source_common"]) is not dict
        or frozenset(data["source_common"]) != SOURCE_KEYS):
        raise EvidenceError("INVALID_GAO_BILLING_SOURCE_SCOPE")
    source = data["source_common"]
    if (source["publisher"] != "U.S. Government Accountability Office"
        or source["source_format"] != "OFFICIAL_GAO_PUBLIC_DECISION_TEXT"
        or source["review_date_utc"] != "2026-10-26"
        or source["original_gao_response_bytes_sha256"] is not None
        or any(source[k] is not False for k in (
            "original_invoice_gbl_tariff_bytes_in_custody",
            "source_link_is_original_transaction_document",
            "commercial_customer_use_rights_verified"))):
        raise EvidenceError("UNSUPPORTED_GAO_SOURCE_CUSTODY")
    if (type(data["publisher_independence"]) is not str
        or "not independently held" not in data["publisher_independence"]
        or type(data["source_limits"]) is not str
        or "not independently reconstructed" not in data["source_limits"]):
        raise EvidenceError("SOURCE_LIMITATIONS_MISSING")
    for k in ("historical_government_deductions_are_retally_cash",
              "independent_original_invoice_and_bank_custody",
              "production_rate_or_dispute_actions_allowed",
              "rights_clearance_for_current_customer_engine"):
        if data[k] is not False:
            raise EvidenceError("UNSUPPORTED_GAO_BILLING_PROMOTION")
    for k in ("independent_current_customer_invoice_accuracy_cases",
              "verified_retally_cash_cents"):
        if type(data[k]) is not int or data[k] != 0:
            raise EvidenceError("UNSUPPORTED_CUSTOMER_BILLING_TRUTH")
    rows = data.get("cases")
    if (type(rows) is not list or len(rows) != len(PINNED)
        or [row.get("id") if type(row) is dict else None for row in rows]
            != list(PINNED)):
        raise EvidenceError("INVALID_GAO_CASE_POPULATION")
    for row in rows:
        if frozenset(row) != CASE_KEYS:
            raise EvidenceError("INVALID_GAO_CASE_SCHEMA")
        if any(row[k] != value or type(row[k]) is not type(value)
               for k, value in PINNED[row["id"]].items()):
            raise EvidenceError("GAO_CASE_FACT_OR_DISPOSITION_TAMPERED")
        if (type(row["source_money_note"]) is not str
            or not 50 <= len(row["source_money_note"]) <= 550):
            raise EvidenceError("INVALID_GAO_SOURCE_NOTE")
        if (type(row["reported_billed_and_paid_cents"]) is not int
            or type(row["reported_gsa_audited_cents"]) is not int
            or type(row["reported_gsa_deducted_cents"]) is not int
            or row["reported_billed_and_paid_cents"] -
                row["reported_gsa_audited_cents"]
                != row["reported_gsa_deducted_cents"]):
            raise EvidenceError("GAO_BILLING_ARITHMETIC_INVALID")
        if row["adjudicated_historical_label"] == LABEL_NEG:
            if row["ga_review_outcome"] != "GSA_DEDUCTION_INVALID_REJECTED_TENDER":
                raise EvidenceError("NEGATIVE_TENDER_DISPOSITION_NOT_PRESERVED")
            if row["money_calculation"] != "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION":
                raise EvidenceError("GAO_OCR_AMOUNT_DERIVATION_NOT_DISCLOSED")
    return data


def load_fixture(path: Path = FIXTURE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("GAO_BILLING_FIXTURE_UNAVAILABLE") from exc
    return validate_fixture(data)


def make_receipt(fixture: dict | None = None) -> dict:
    data = validate_fixture(fixture) if fixture is not None else load_fixture()
    rows = data["cases"]
    pos = [r for r in rows if r["adjudicated_historical_label"] == LABEL_POS]
    neg = [r for r in rows if r["adjudicated_historical_label"] == LABEL_NEG]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "case_count": len(rows),
        "case_outcomes": [
            {"id": r["id"], "source_url": r["source_url"],
             "historical_label": r["adjudicated_historical_label"],
             "ga_review_outcome": r["ga_review_outcome"],
             "publisher_reported_deduction_cents": r["reported_gsa_deducted_cents"],
             "amount_derived_from_gao_arithmetic": (
                 r["money_calculation"] != "PUBLISHER_EXPLICIT")}
            for r in rows],
        "sustained_overcharges_historical_cents":
            sum(r["reported_gsa_deducted_cents"] for r in pos),
        "invalid_government_deductions_historical_cents":
            sum(r["reported_gsa_deducted_cents"] for r in neg),
        "historical_agency_deductions_total_cents_not_retally_cash":
            sum(r["reported_gsa_deducted_cents"] for r in rows),
        "external_gao_adjudicated_historical_cases": len(rows),
        "source_original_invoice_rate_bank_chain_verified_cases": 0,
        "private_customer_benchmark_truth_cases": 0,
        "retally_recovered_cash_cents": 0,
        "production_rating_or_dispute_allowed": False,
        "commercial_reuse_approved": False,
        "source_original_gao_response_sha256": None,
        "fixture_authored_sha256": canonical_digest(data),
    }
    return {**body, "receipt_sha256": canonical_digest(body)}


def verify_receipt(receipt: object) -> None:
    if type(receipt) is not dict or frozenset(receipt) != RECEIPT_KEYS:
        raise EvidenceError("INVALID_GAO_BILLING_RECEIPT")
    expected = make_receipt()
    if receipt != expected:
        raise EvidenceError("UNVERIFIED_GAO_BILLING_RECEIPT")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    options = parser.parse_args()
    if options.verify:
        if options.output is None:
            parser.error("--verify requires --output")
        try:
            content = json.loads(options.output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceError("MISSING_GAO_BILLING_RECEIPT") from exc
        verify_receipt(content)
        print(json.dumps({"verified": True, "scope": SCOPE}, sort_keys=True))
        return
    report = make_receipt()
    if options.output is not None:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n",
                                  encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
