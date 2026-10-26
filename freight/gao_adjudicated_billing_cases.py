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
    "B-189100": {
        "source_url": "https://www.gao.gov/products/b-189100",
        "decision_date": "1977-12-27",
        "carrier": "YELLOW_FREIGHT_SYSTEM",
        "reported_gbl": "A-6018184",
        "reported_gbl_date": None,  # Only April 1974, not a source-verified day.
        "reported_weight_lb": 8750,
        "reported_billed_and_paid_cents": 356718,
        "reported_gsa_audited_cents": 93280,
        "reported_gsa_deducted_cents": 263438,
        "ga_review_outcome": "GSA_CLASSIFICATION_DEDUCTION_SUSTAINED",
        "adjudicated_historical_label": LABEL_POS,
        "rate_authority": "NMFC_41050_VS_41060_SHIPPER_PHOTO_ADJUDICATION",
        "money_calculation": "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION",
    },
    "B-213717": {
        "source_url": "https://www.gao.gov/products/b-213717-0",
        "decision_date": "1984-03-20",
        "carrier": "YELLOW_FREIGHT_SYSTEM",
        "reported_gbl": None,  # Decision text does not give a safely transcribable ID.
        "reported_gbl_date": None,
        "reported_weight_lb": None,
        "reported_billed_and_paid_cents": 121209,
        "reported_gsa_audited_cents": 68678,
        "reported_gsa_deducted_cents": 52531,
        "ga_review_outcome": "GSA_CLASSIFICATION_DEDUCTION_SUSTAINED",
        "adjudicated_historical_label": LABEL_POS,
        "rate_authority": "NMFC_146315_ROCKET_LAUNCHER_VS_11800_AIRCRAFT_PARTS",
        "money_calculation": "PUBLISHER_EXPLICIT",
    },
    "B-192856": {
        "source_url": "https://www.gao.gov/products/b-192856",
        "decision_date": "1979-03-15",
        "carrier": "YELLOW_FREIGHT_SYSTEM",
        "reported_gbl": "P-7343114",
        "reported_gbl_date": None,  # Only June 1976 available, not precise date.
        "reported_weight_lb": 2040,
        "reported_billed_and_paid_cents": 109793,
        "reported_gsa_audited_cents": 15851,  # Difference, not original rate bytes.
        "reported_gsa_deducted_cents": 93942,
        "ga_review_outcome": "GSA_PHYSICAL_SAMPLE_CLASSIFICATION_DEDUCTION_SUSTAINED",
        "adjudicated_historical_label": LABEL_POS,
        "rate_authority": "RMBQ_17_B_ITEM_7521_NMFC_193820_NOT_103300",
        "money_calculation": "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION",
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
    "B-191258": {
        "source_url": "https://www.gao.gov/products/b-191258",
        "decision_date": "1978-07-07",
        "carrier": "YELLOW_FREIGHT_SYSTEM",
        "reported_gbl": None,  # Source PDF index text has ambiguous bill prefix.
        "reported_gbl_date": None,
        "reported_weight_lb": 6910,
        "reported_billed_and_paid_cents": 149760,
        "reported_gsa_audited_cents": 146430,  # An invalid GSA deduction, NOT lawful rate.
        "reported_gsa_deducted_cents": 3330,
        "ga_review_outcome": "GSA_DEDUCTION_INVALID_TRUCKLOAD_MINIMUM_WEIGHT_RULE",
        "adjudicated_historical_label": LABEL_NEG,
        "rate_authority": "ICC_RMB_127_ITEM_997_RMB_120_ITEM_610_5_24000_LB_CAPACITY_MINIMUM",
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
SOURCE_NOTES = {
    "B-191257": "GAO reports $828 paid, $796 government rate and $32 deducted; upheld route authority and settlement.",
    "B-160344": "GAO reports $275.17 paid, $139.29 allowable and $135.88 deducted in December 1965; carrier reclaim disallowed.",
    "B-189100": "GAO reports $3,567.18 originally collected and $2,634.38 deducted. The $932.80 remainder is paid-minus-deduction arithmetic ONLY, not an independently published tariff charge.",
    "B-213717": "GAO reports $1,212.09 paid, $686.78 audited and $525.31 deducted from carrier funds; GAO sustained classification based on shipper description and supporting records.",
    "B-192856": "GAO sustained a $939.42 GSA setoff from $1,097.93 collected. GAO independently examined a 13.6-ounce acoustic tile sample: 60 tiles per box equal 51 pounds; 40 boxes equal 2,040 pounds. The implied $158.51 remainder is NOT a separately custodied invoice or original tariff page.",
    "B-221594": "GAO reports $942 paid and $220.75 collected by GSA using rejected tender. Source renders audit amount with OCR ambiguity ('72L.25'); $721.25 is arithmetic implied by its stated difference. Original GBL transcription is OCR-ambiguous and deliberately omitted.",
    "B-191258": "GAO found a $33.30 GSA setoff improper: full trailer weight 6,910 pounds, rated minimum 24,000 pounds. Original $1,497.60 billed and paid; $1,464.30 is subtraction from the erroneous GSA setoff, NOT an allowable audited charge. GSA said a claim would be processed, not proof of a paid refund."
}
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
            or row["source_money_note"] != SOURCE_NOTES[row["id"]]
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
            if row["ga_review_outcome"] not in (
                "GSA_DEDUCTION_INVALID_REJECTED_TENDER",
                "GSA_DEDUCTION_INVALID_TRUCKLOAD_MINIMUM_WEIGHT_RULE",
            ):
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
