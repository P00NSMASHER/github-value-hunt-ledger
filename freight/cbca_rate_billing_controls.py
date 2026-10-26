"""Source-bound CBCA motor/HHG freight billing decision controls, read-only.

The CBCA decisions independently adjudicate government carrier disputes.
Neither a rejected GSA overcharge assessment nor an unpaid carrier claim
is an independently authorized RETALLY customer refund or rate benchmark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.unified_research_lab import ResearchError, digest, safe_url

FIXTURE = Path(__file__).with_name("fixtures") / "cbca_rate_billing_controls_v1.json"
SCOPE = "INDEPENDENT_GOVERNMENT_CARRIER_RATE_CASE_DECISIONS_ONLY_NOT_CUSTOMER_INVOICE_TRUTH"
ROOT_PINNED = {
    "schema_version": 1,
    "fixture_id": "RETALLY_CBCA_INDEPENDENT_HISTORICAL_BILLING_ADJUDICATION_CONTROLS_V1",
    "scope": SCOPE,
    "official_decision_index": "https://www.cbca.gov/decisions/rate.html",
    "publisher": "U.S. Civilian Board of Contract Appeals",
    "reviewed_at_utc_date": "2026-10-26",
    "source_decision_pdf_bytes_acquired": False,
    "source_decision_pdf_sha256": None,
    "official_decision_page_images_independently_verified": False,
    "original_carrier_invoices_weight_tickets_tenders_and_bank_records_held": False,
    "independent_private_customer_invoice_rate_and_bank_chain_verified": False,
    "commercial_reuse_approved_for_retally_customers": False,
    "customer_accuracy_scoring_permitted": False,
    "retally_real_customer_cases_verified": 0,
    "retally_verified_cash_recovered_cents": 0,
}
# These independently reviewed official decision facts deliberately do not
# assert custody of the actual invoice, PDF HTTP response, original tender,
# payment trace, or later carrier refund.
PINNED = (
    {
        "case_id": "CBCA-6578-RATE",
        "decision_date": "2020-08-06",
        "official_decision_url":
            "https://www.cbca.gov/files/decisions/2020/"
            "SULLIVAN_08-06-20_6578-RATE__AARE_LOGISTICS%2C_LLC%20%28Decision%29.pdf",
        "carrier": "AARE_LOGISTICS_LLC",
        "dispute_kind":
            "GSA_RETROSPECTIVE_OVERCHARGE_ASSESSMENT_AFTER_CARRIER_INVOICE_PAYMENT",
        "shipment_year": 2014,
        "gsa_notices_under_actual_adjudication": 7,
        "gsa_total_notices_described": 115,
        "appealed_carrier_repayment_to_gsa_cents_reported": 1554908,
        "board_disposition":
            "CARRIER_REIMBURSEMENT_CLAIM_GRANTED_AS_GSA_OVERCHARGE_ASSESSMENTS_UNSUPPORTED",
        "decision_label":
            "NEGATIVE_GSA_OVERCHARGE_ASSERTION_SEVEN_SHIPMENTS_ONLY",
        "additional_108_notice_outcomes": "NOT_ADJUDICATED_BY_THIS_DECISION",
        "original_governing_tender_pages_in_custody": False,
        "actual_carrier_refund_or_credit_received_cents": None,
        "actual_retally_recovered_cash_cents": 0,
        "modern_customer_overcharge_amount_cents": None,
    },
    {
        "case_id": "CBCA-8051-RATE",
        "decision_date": "2024-08-08",
        "official_decision_url":
            "https://www.cbca.gov/files/decisions/2024/"
            "LESTER_08-08-24_8051-RATE__JAMES_FORWARDING_COMPANY_INC%20%28DECISION%29.pdf",
        "carrier": "JAMES_FORWARDING_COMPANY_INC",
        "dispute_kind":
            "UNPAID_ORIGINAL_CARRIER_INVOICE_PREPAYMENT_DENIAL_AND_DELAYED_CLAIM",
        "shipment_year": 2018,
        "original_invoice_date": "2018-09-26",
        "prepayment_denial_date": "2018-10-02",
        "disputed_unpaid_invoice_cents_reported": 1459569,
        "missing_weight_ticket_on_initial_payment_review": True,
        "earliest_documented_claim_response_year": 2023,
        "board_disposition":
            "UNPAID_CARRIER_CLAIM_DENIED_UNTIMELY_WITHOUT_PROVEN_NOTICE_PREJUDICE",
        "decision_label":
            "NEGATIVE_UNPAID_INVOICE_IS_NOT_VALID_OVERCHARGE_OR_RECOVERED_CASH",
        "original_invoice_weight_ticket_or_bank_record_bytes_in_custody": False,
        "independently_verified_customer_payment_cents": None,
        "actual_retally_recovered_cash_cents": 0,
        "modern_customer_overcharge_amount_cents": None,
    },
)
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "case_count", "decision_outcomes",
    "gsa_overcharge_notices_invalidated_count",
    "government_notice_assessment_cents_rejected_by_board_not_retally_cash",
    "other_gsa_notices_not_adjudicated_here",
    "unpaid_original_invoices_denied_by_board_case_count",
    "time_barred_carrier_claim_cents_not_recoverable",
    "verified_carrier_refund_received_cents", "private_customer_invoice_truth_cases",
    "source_original_pdf_sha256", "commercial_reuse_approved",
    "verified_retally_cash_recovery_cents", "source_fixture_authored_sha256_not_pdf_hash",
    "receipt_sha256",
})


def load_fixture(path: Path = FIXTURE) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("CBCA_OFFICIAL_CASEPACK_MISSING_OR_INVALID") from exc
    return validate_fixture(doc)


def validate_fixture(doc: object) -> dict:
    if type(doc) is not dict or frozenset(doc) != frozenset(ROOT_PINNED) | {"cases"}:
        raise ResearchError("CBCA_CASEPACK_SCHEMA_INVALID")
    for field, value in ROOT_PINNED.items():
        if type(doc[field]) is not type(value) or doc[field] != value:
            raise ResearchError("CBCA_UNSUPPORTED_SOURCE_CUSTODY_OR_CLAIMS")
    if safe_url(doc["official_decision_index"]) != doc["official_decision_index"]:
        raise ResearchError("CBCA_UNSAFE_SOURCE_INDEX")
    rows = doc["cases"]
    if type(rows) is not list or len(rows) != len(PINNED):
        raise ResearchError("CBCA_CASE_POPULATION_INVALID")
    for item, independent in zip(rows, PINNED, strict=True):
        if type(item) is not dict or frozenset(item) != frozenset(independent):
            raise ResearchError("CBCA_CASE_SCHEMA_INVALID")
        for field, value in independent.items():
            if type(item[field]) is not type(value) or item[field] != value:
                raise ResearchError("CBCA_CASE_AMOUNT_OR_DISPOSITION_FORGED")
        if safe_url(item["official_decision_url"]) != item["official_decision_url"]:
            raise ResearchError("CBCA_UNSAFE_SOURCE_CASE_URL")
        if item["actual_retally_recovered_cash_cents"] != 0:
            raise ResearchError("CBCA_UNSUPPORTED_RETALLY_CASH")
    first, second = rows
    if (first["gsa_total_notices_described"]
          - first["gsa_notices_under_actual_adjudication"] != 108
        or first["actual_carrier_refund_or_credit_received_cents"] is not None
        or second["prepayment_denial_date"] < second["original_invoice_date"]
        or second["modern_customer_overcharge_amount_cents"] is not None):
        raise ResearchError("CBCA_HISTORICAL_OUTCOME_OR_SCOPE_INVALID")
    return doc


def make_receipt(fixture: dict | None = None) -> dict:
    source = load_fixture() if fixture is None else validate_fixture(fixture)
    first, second = source["cases"]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "case_count": len(source["cases"]),
        "decision_outcomes": [
            {"case_id": item["case_id"], "official_decision_url": item["official_decision_url"],
             "decision_date": item["decision_date"],
             "independent_adjudication_label": item["decision_label"],
             "board_disposition": item["board_disposition"],
             "verified_customer_overcharge_cents": None,
             "verified_retally_recovered_cash_cents": 0}
            for item in source["cases"]
        ],
        "gsa_overcharge_notices_invalidated_count": 7,
        "government_notice_assessment_cents_rejected_by_board_not_retally_cash":
            first["appealed_carrier_repayment_to_gsa_cents_reported"],
        "other_gsa_notices_not_adjudicated_here":
            first["gsa_total_notices_described"]
            - first["gsa_notices_under_actual_adjudication"],
        "unpaid_original_invoices_denied_by_board_case_count": 1,
        "time_barred_carrier_claim_cents_not_recoverable":
            second["disputed_unpaid_invoice_cents_reported"],
        "verified_carrier_refund_received_cents": None,
        "private_customer_invoice_truth_cases": 0,
        "source_original_pdf_sha256": None,
        "commercial_reuse_approved": False,
        "verified_retally_cash_recovery_cents": 0,
        "source_fixture_authored_sha256_not_pdf_hash": digest(source),
    }
    return {**body, "receipt_sha256": digest(body)}


def verify_receipt(doc: object) -> dict:
    if (type(doc) is not dict or frozenset(doc) != RECEIPT_KEYS
            or doc != make_receipt()):
        raise ResearchError("CBCA_UNSUPPORTED_OR_TAMPERED_RECEIPT")
    return doc


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--verify", action="store_true")
    args = cli.parse_args()
    if args.verify:
        if args.output is None:
            cli.error("--verify requires --output")
        try:
            row = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ResearchError("CBCA_CASE_RECEIPT_UNAVAILABLE") from exc
        result = verify_receipt(row)
    else:
        result = make_receipt()
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
    print(json.dumps({
        "cases": result["case_count"],
        "rejected_overcharge_notices": result["gsa_overcharge_notices_invalidated_count"],
        "unpaid_carrier_claims_denied": result["unpaid_original_invoices_denied_by_board_case_count"],
        "private_customer_truth_cases": 0,
        "retally_cash_recovered_cents": 0,
        "verified": args.verify,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
