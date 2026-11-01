"""Historical CBCA 1317 and 3467 government freight payment/offset chronology.

Independent Board decisions report transportation payments, overcharge notices,
Treasury offsets and/or rejected recovery demands. This is NOT original invoice
custody, legally current private rate authority, paid carrier refund, modern
customer ground truth, or RETALLY recovered cash.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from freight.unified_research_lab import ResearchError, digest, safe_url

FIXTURE = Path(__file__).with_name("fixtures") / "cbca_rail_detention_timeline_v1.json"
SCOPE = "OFFICIAL_CBCA_GOVERNMENT_FREIGHT_BILLING_AND_TIMELINESS_DECISIONS_NOT_CUSTOMER_BENCHMARK"
ROOT_PINNED = {
    "schema_version": 1,
    "fixture_id": "RETALLY_CBCA_1317_3467_SHIPMENT_PAYMENT_TIMELINES_V1",
    "scope": SCOPE,
    "publisher": "U.S. Civilian Board of Contract Appeals",
    "as_of_source_review_date": "2026-10-26",
    "original_official_pdf_bytes_acquired": False,
    "original_official_pdf_sha256": None,
    "original_bol_invoice_contract_or_tender_bytes_held": False,
    "independent_bank_or_repayment_statement_held": False,
    "independent_modern_customer_invoice_ground_truth_cases": 0,
    "commercial_customer_engine_use_approved": False,
    "retally_recovered_cash_cents": 0,
}
UP_URL = ("https://www.cbca.gov/files/decisions/2009/"
          "GILMORE_10-29-09_1317-RATE__UNION_PACIFIC_RAILROAD_508.pdf")
TQL_URL = ("https://www.cbca.gov/files/decisions/2014/"
           "ZISCHKAU_05-14-14_CBCA%203467-RATE__IN_THE_MATTER_OF_TOTAL_QUALITY_LOGISTICS_LLC_.pdf")

# Independent authored source-review oracle. The first money column in the
# Board's published table is alleged OVERCHARGE, NOT total original invoice.
# Exact BOL identifiers are public official decision text, not customer records.
UP_ROWS = (
    ("W45QQ90009822", 1793654, "2005-01-20", 1793654, "2008-06-16"),
    ("W45QQ90009825", 1314805, "2005-01-20", 1314805, "2008-06-16"),
    ("W45QQ90009832", 2194247, "2005-02-11", 2194247, "2008-10-15"),
    ("W45QQ90009833", 878744, "2005-02-02", 878744, "2008-04-15"),
    ("W45QQ90009838", 438849, "2005-02-11", 438849, "2008-04-15"),
    ("W45QQ90009856", 877698, "2005-02-11", 877698, "2008-04-15"),
    ("W45QQ90009858", 436990, "2005-02-11", 436990, "2008-04-15"),
    ("W67G230008416", 330460, "2004-01-27", 330460, "2008-10-10"),
    ("W67G230008417", 479879, "2004-02-05", 479879, "2008-10-10"),
    ("W5CQRF0017135", 466531, "2004-02-09", 466531, "2008-10-10"),
    ("W45QQ90006106", 1207383, "2004-03-01", 1197902, "2008-10-31"),
    ("W45QQ90006013", 3342164, "2004-02-06", 3325916, "2008-10-31"),
)
ROW_FIELDS = ("public_gbl_id_from_board_table",
              "government_alleged_overcharge_cents",
              "carrier_bill_paid_date_board_reported",
              "treasury_offset_collected_cents",
              "treasury_offset_date_board_reported")
UP_FACTS = {
    "case_id": "CBCA-1317-RATE",
    "decision_date": "2009-10-29",
    "official_url": UP_URL,
    "carrier": "UNION_PACIFIC_RAILROAD",
    "government_shipper": "US_DEPARTMENT_OF_DEFENSE",
    "source_table_zero_based_pdf_page": 2,
    "original_legal_issue": "UNTIMELY_FEDERAL_GOVERNMENT_OVERCHARGE_DEDUCTIONS_ON_PAID_RAIL_TRANSPORTATION",
    "statutory_rule_at_case_date": "31_USC_3726_D_THREE_YEARS_AFTER_BILL_PAID",
    "source_document_table_header_money_type": "GOVERNMENT_ALLEGED_OVERCHARGE_NOT_ORIGINAL_INVOICE_FACE_AMOUNT",
    "board_conclusion": "TWELVE_TREASURY_DEDUCTIONS_TOO_LATE_MUST_BE_REFUNDED",
    "underlying_tariff_overcharge_merits_adjudicated": False,
    "issued_refund_order_reported": True,
    "actual_refund_cleared_bank_receipt_verified": False,
    "initial_74_bol_notices_reported": 74,
    "initial_claims_settled_by_parties_reported": 67,
    "added_claims_during_proceedings": 5,
}
TQL_FACTS = {
    "case_id": "CBCA-3467-RATE",
    "decision_date": "2014-05-14",
    "official_url": TQL_URL,
    "carrier": "TOTAL_QUALITY_LOGISTICS_LLC",
    "historical_gsa_tender_reference": "GSA_STOS_100_D_ITEM_325",
    "shipment_count_2010": 4,
    "shipment_count_2011": 75,
    "government_initially_accepted_paid_invoice_count": 9,
    "government_later_challenged_paid_invoice_count": 70,
    "government_original_paid_invoice_and_bol_support_acknowledged_in_board_record": True,
    "original_signed_bol_and_itemized_invoice_bytes_in_retally_custody": False,
    "reported_gsa_demand_variants_cents": [33989573, 33989575],
    "source_variance_locations": [
        "PAGE_5_PARAGRAPH_CARRIER_PAYMENT_DEMAND",
        "PAGE_6_FINAL_DECISION_PARAGRAPH",
    ],
    "amount_discrepancy_cents": 2,
    "board_conclusion": "GSA_OVERCHARGE_NOTICES_INVALID_GSA_PREVIOUSLY_AUTHORIZED_AND_PAID_DETENTION",
    "gsa_recoupment_actually_received_from_carrier_verified": False,
    "later_carrier_refund_or_credit_verified": False,
    "modern_customer_detention_authority_verified": False,
}
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "cbca_decision_count", "up_public_bol_rows",
    "up_initial_74_notices_no_case_population_promotion",
    "up_original_claims_resolved_before_hearing",
    "up_additional_claims_during_proceedings",
    "up_board_reported_alleged_overcharge_total_cents_NOT_invoice_total",
    "up_board_reported_treasury_offsets_taken_cents_NOT_retally_refund",
    "up_allegation_minus_offsets_cents",
    "up_late_offset_rows", "up_board_ordered_refund_but_no_bank_receipt",
    "up_merits_of_underlying_tariff_dispute_not_decided",
    "up_original_bol_identifiers_authored_sha256_NOT_pdf_source_hash",
    "tql_paid_transport_invoice_shipments_reported",
    "tql_initially_accepted_invoice_count", "tql_challenged_invoice_count",
    "tql_contradictory_notice_amounts_cents_NOT_normalized",
    "tql_amount_variance_cents", "tql_gsa_notices_invalidated",
    "tql_government_recoupment_received_not_verified",
    "original_official_pdf_source_sha256",
    "original_invoice_bol_tender_bytes_held", "modern_customer_truth_cases",
    "independent_carrier_refunds_bank_verified_cases", "commercial_use_approved",
    "retally_cash_recovered_cents", "source_fixture_authored_sha256_NOT_original_pdf",
    "receipt_sha256",
})


def load_fixture(path: Path = FIXTURE) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("CBCA_TIMELINE_FILE_INVALID_OR_MISSING") from exc
    return validate_fixture(doc)


def validate_fixture(doc: object) -> dict:
    if type(doc) is not dict or set(doc) != set(ROOT_PINNED) | {
        "union_pacific_2009", "total_quality_logistics_2014"
    }:
        raise ResearchError("CBCA_TIMELINE_SCHEMA_INVALID")
    for key, value in ROOT_PINNED.items():
        if type(doc[key]) is not type(value) or doc[key] != value:
            raise ResearchError("CBCA_TIMELINE_UNVERIFIED_CUSTODY_OR_CUSTOMER_CLAIMS")
    up, tql = doc["union_pacific_2009"], doc["total_quality_logistics_2014"]
    if type(up) is not dict or set(up) != set(UP_FACTS) | {"rows"}:
        raise ResearchError("CBCA_UP_CASE_SCHEMA_INVALID")
    if type(tql) is not dict or set(tql) != set(TQL_FACTS):
        raise ResearchError("CBCA_TQL_CASE_SCHEMA_INVALID")
    for item, independent in ((up, UP_FACTS), (tql, TQL_FACTS)):
        for key, value in independent.items():
            if type(item[key]) is not type(value) or item[key] != value:
                raise ResearchError("CBCA_DECISION_FACT_OR_MONEY_FORGED")
        if safe_url(item["official_url"]) != item["official_url"]:
            raise ResearchError("CBCA_OFFICIAL_SOURCE_URL_INVALID")
    if (type(up["rows"]) is not list or len(up["rows"]) != len(UP_ROWS)
            or len({r[0] for r in UP_ROWS}) != len(UP_ROWS)):
        raise ResearchError("CBCA_UP_BOL_ROW_COUNT_OR_IDENTITY_INVALID")
    for row, expected_values in zip(up["rows"], UP_ROWS, strict=True):
        if type(row) is not dict or set(row) != set(ROW_FIELDS):
            raise ResearchError("CBCA_UP_BOL_COLUMNS_INVALID")
        expected = dict(zip(ROW_FIELDS, expected_values, strict=True))
        if any(type(row[k]) is not type(v) or row[k] != v
               for k, v in expected.items()):
            raise ResearchError("CBCA_UP_BOL_AMOUNT_OR_DATE_TAMPERED")
        paid = date.fromisoformat(row["carrier_bill_paid_date_board_reported"])
        deducted = date.fromisoformat(row["treasury_offset_date_board_reported"])
        if deducted <= paid.replace(year=paid.year+3):
            raise ResearchError("CBCA_UP_DEDUCTION_NOT_LATER_THAN_THREE_YEARS")
    if (sum(r[1] for r in UP_ROWS) != 13761404
            or sum(r[3] for r in UP_ROWS) != 13735675
            or sum(r[1]-r[3] for r in UP_ROWS) != 25729
            or up["initial_74_bol_notices_reported"]
             - up["initial_claims_settled_by_parties_reported"]
             + up["added_claims_during_proceedings"] != len(UP_ROWS)
            or tql["shipment_count_2010"]+tql["shipment_count_2011"] != 79
            or (tql["government_initially_accepted_paid_invoice_count"]
                + tql["government_later_challenged_paid_invoice_count"]) != 79
            or tql["reported_gsa_demand_variants_cents"][1]
             - tql["reported_gsa_demand_variants_cents"][0] != 2):
        raise ResearchError("CBCA_TIMELINE_MONEY_POPULATION_OR_CONFLICT_INVALID")
    return doc


def make_receipt(fixture: dict | None = None) -> dict:
    source = load_fixture() if fixture is None else validate_fixture(fixture)
    up, tql = source["union_pacific_2009"], source["total_quality_logistics_2014"]
    rows = up["rows"]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "cbca_decision_count": 2,
        "up_public_bol_rows": len(rows),
        "up_initial_74_notices_no_case_population_promotion": 74,
        "up_original_claims_resolved_before_hearing": 67,
        "up_additional_claims_during_proceedings": 5,
        "up_board_reported_alleged_overcharge_total_cents_NOT_invoice_total": sum(
            row["government_alleged_overcharge_cents"] for row in rows),
        "up_board_reported_treasury_offsets_taken_cents_NOT_retally_refund": sum(
            row["treasury_offset_collected_cents"] for row in rows),
        "up_allegation_minus_offsets_cents": sum(
            row["government_alleged_overcharge_cents"]
            - row["treasury_offset_collected_cents"] for row in rows),
        "up_late_offset_rows": sum(
            date.fromisoformat(row["treasury_offset_date_board_reported"])
            > date.fromisoformat(row["carrier_bill_paid_date_board_reported"]).replace(
                year=date.fromisoformat(
                    row["carrier_bill_paid_date_board_reported"]).year+3)
            for row in rows),
        "up_board_ordered_refund_but_no_bank_receipt": True,
        "up_merits_of_underlying_tariff_dispute_not_decided": True,
        "up_original_bol_identifiers_authored_sha256_NOT_pdf_source_hash": digest(
            [row["public_gbl_id_from_board_table"] for row in rows]),
        "tql_paid_transport_invoice_shipments_reported": 79,
        "tql_initially_accepted_invoice_count": 9,
        "tql_challenged_invoice_count": 70,
        "tql_contradictory_notice_amounts_cents_NOT_normalized":
            tql["reported_gsa_demand_variants_cents"],
        "tql_amount_variance_cents": 2,
        "tql_gsa_notices_invalidated": True,
        "tql_government_recoupment_received_not_verified": True,
        "original_official_pdf_source_sha256": None,
        "original_invoice_bol_tender_bytes_held": False,
        "modern_customer_truth_cases": 0,
        "independent_carrier_refunds_bank_verified_cases": 0,
        "commercial_use_approved": False,
        "retally_cash_recovered_cents": 0,
        "source_fixture_authored_sha256_NOT_original_pdf": digest(source),
    }
    return {**body, "receipt_sha256": digest(body)}


def verify_receipt(receipt: object) -> dict:
    if type(receipt) is not dict or set(receipt) != RECEIPT_KEYS or receipt != make_receipt():
        raise ResearchError("CBCA_TIMELINE_RECEIPT_FORGED")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if args.output is None:
            parser.error("--verify needs --output")
        try:
            receipt = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ResearchError("CBCA_TIMELINE_RECEIPT_UNAVAILABLE") from exc
        verified = verify_receipt(receipt)
    else:
        verified = make_receipt()
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(verified, indent=2, sort_keys=True)+"\n",
                                   encoding="utf-8")
    print(json.dumps({
        "rows": verified["up_public_bol_rows"],
        "board_reported_treasury_offsets_cents":
            verified["up_board_reported_treasury_offsets_taken_cents_NOT_retally_refund"],
        "total_quality_disputed_invoice_count": verified["tql_challenged_invoice_count"],
        "customer_truth_cases": 0, "retally_cash_recovered_cents": 0,
        "verified": args.verify,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
