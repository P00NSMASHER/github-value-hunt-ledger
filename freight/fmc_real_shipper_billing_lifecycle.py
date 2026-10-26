"""FMC public shipper billing outcomes, never RETALLY customer or bank truth.

FMC 2022(I): real shipper's demurrage/detention payments, final reparations
including interest, then a later payment reported by the FMC in independent
coverage of its October 2026 enforcement order. Actual bank transfer and
interest paid are NOT in RETALLY custody.
FMC 2025(I): a sharp invoice/quote gap without a reparations award.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.unified_research_lab import ResearchError, digest, safe_url

FIXTURE = Path(__file__).with_name("fixtures") / "fmc_real_shipper_billing_lifecycle_v1.json"
SCOPE = "FMC_THIRD_PARTY_ADJUDICATED_REAL_SHIPPER_CHARGES_NOT_RETALLY_CUSTOMERS_OR_ORIGINAL_BANK_CUSTODY"
ROOT = {
    "schema_version": 1,
    "fixture_id": "RETALLY_FMC_2022I_2025I_INDEPENDENT_REAL_SHIPPER_EVIDENCE_LIFECYCLE_V1",
    "scope": SCOPE,
    "review_utc_date": "2026-10-26",
    "public_publisher": "U.S. Federal Maritime Commission",
    "official_pdf_bytes_acquired": False,
    "official_pdf_source_sha256": None,
    "original_customer_invoice_and_bank_bytes_acquired": False,
    "source_specific_commercial_reuse_verified": False,
    "retally_independent_customer_invoice_truth_cases": 0,
    "retally_cash_recovered_cents": 0,
}
BRIDGEWELL = {
    "case_id": "FMC_2022(I)",
    "claimant": "AGRIBUSINESS_HOLDINGS_LP_DBA_BRIDGEWELL_AGRIBUSINESS",
    "respondent": "COSCO_SHIPPING_LINES_CO_LTD",
    "shipment_year": 2022,
    "initial_claim_date": "2024-12-17",
    "initial_decision_served": "2025-09-29",
    "official_initial_decision_url":
        "https://www2.fmc.gov/readingroom/docs/2022%28I%29/"
        "%2801%29%202022%28I%29%20Initial%20Decision.pdf",
    "official_final_notice_served": "2026-01-05",
    "official_final_notice_url":
        "https://www2.fmc.gov/readingroom/docs/2022%28I%29/"
        "%2802%29%202022%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf",
    "adjudication": "INVALID_DEMURRAGE_DETENTION_INVOICE_CONTENT_REPARATIONS_GRANTED",
    "original_reparation_claim_cents": 4378000,
    "reparations_principal_cents": 2432880,
    "interest_through_january_5_2026_cents": 396051,
    "administratively_final_amount_due_cents": 2828931,
    "payment_due_date": "2026-01-20",
    "later_enforcement_docket": "FMC_26-13",
    "later_order_to_show_cause_date": "2026-10-02",
    "fmc_original_enforcement_order_document_id": 145944,
    "fmc_enforcement_record_index_publicnow":
        "https://www.publicnow.com/view/AEF607AD7C75FCEEFC7781A0221E6505C1BC79B9",
    "reported_actual_customer_payment_received_date": "2026-08-31",
    "reported_payment_lifecycle_source":
        "INDEPENDENT_MEDIA_REPORTS_OF_OCTOBER_2_2026_FMC_ORDER_NOT_ORIGINAL_BANK_OR_ORDER_PDF_BYTES",
    "secondary_confirmation_source":
        "https://www.seatrade-maritime.com/regulations/"
        "fmc-targets-cosco-with-millions-in-late-payment-fines",
    "second_secondary_confirmation_source":
        "https://splash247.com/fmc-threatens-cosco-with-16-7m-penalty-over-delayed-payment/",
    "exact_customer_received_amount_cents_independently_bank_verified": None,
    "interest_actually_received_cents_independently_verified": None,
    "civil_penalty_assessed_cents_at_review_date": None,
    "penalty_order_finalized_at_review_date": False,
    "government_reported_late_reparation_payment": True,
    "applicable_to_private_domestic_motor_freight_tariffs": False,
}
AWARD_GROUPS = (
    (3, 54450, 9115),
    (1, 150750, 24994),
    (1, 193050, 31923),
    (1, 235350, 38712),
    (1, 235350, 38560),
    (1, 552600, 90540),
    (1, 21780, 3546),
    (1, 880650, 140431),
)
HPL = {
    "case_id": "FMC_2025(I)",
    "initial_decision_served": "2025-08-07",
    "official_initial_decision_url":
        "https://www2.fmc.gov/readingroom/docs/2025%28I%29/"
        "%2801%29%202025%28I%29%20Initial%20Decision.pdf",
    "claimant": "HP_LOGISTICS_CO_LTD",
    "respondents": ["CITI_FREIGHT_LOGISTICS_INC", "BEST_INTERNATIONAL_CARGO_INC"],
    "initial_quote_cents": 4320000,
    "additional_parts_discussed_cents": 1100000,
    "claimed_revised_quote_cents": 5420000,
    "final_invoiced_amount_cents": 7780000,
    "quote_vs_invoice_difference_cents": 2360000,
    "additional_demurrage_detention_claim_cents": 229500,
    "total_reparations_sought_cents": 2589500,
    "initial_decision_section_41102_c_violated": False,
    "initial_decision_BIC_40501_a_1_tariff_publication_violation": True,
    "initial_decision_CFL_violation_found": False,
    "initial_decision_reparations_awarded_cents": 0,
    "administrative_finality_separately_verified": False,
    "later_customer_refund_verified_cents": None,
    "independent_full_original_quote_invoice_BOL_payment_chain_in_retally_custody": False,
}
AWARD_KEYS = frozenset({"multiplicity", "principal_cents_each", "interest_cents_each"})
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "fmc_cases",
    "bridgewell_initial_claim_cents", "bridgewell_final_principal_cents",
    "bridgewell_final_interest_as_of_notice_cents",
    "bridgewell_final_ordered_total_cents", "bridgewell_award_components_not_invoice_count",
    "bridgewell_reported_late_customer_payment_date",
    "bridgewell_later_payment_reported_NOT_verified_bank_receipt",
    "bridgewell_exact_received_cash_and_interest_unverified",
    "bridgewell_civil_penalties_imposed_cents",
    "bridgewell_current_private_motor_freight_authority",
    "hpl_initial_quote_cents", "hpl_claimed_amended_quote_cents",
    "hpl_final_invoice_cents", "hpl_invoice_vs_quote_difference_cents",
    "hpl_claimed_reparations_cents",
    "hpl_initial_decision_reparations_awarded_cents",
    "hpl_initial_decision_tariff_publication_violation",
    "hpl_initial_decision_section_41102_c_violation",
    "hpl_final_status_independently_verified",
    "original_fmc_pdf_bytes_and_private_invoices_held",
    "modern_retally_invoice_accuracy_labels", "commercial_customer_reuse_approved",
    "retally_recovered_cash_cents", "source_authored_fixture_SHA256_NOT_FMC_pdf_hash",
    "original_official_pdf_sha256", "receipt_sha256",
})


def exact(item: object, expected: dict, kind: str) -> None:
    if type(item) is not dict or set(item) != set(expected):
        raise ResearchError("FMC_"+kind+"_SCHEMA_INVALID")
    for key, value in expected.items():
        if type(item[key]) is not type(value) or item[key] != value:
            raise ResearchError("FMC_"+kind+"_SOURCE_OR_PAYMENT_CLAIM_FORGED")


def validate_fixture(doc: object) -> dict:
    if type(doc) is not dict or set(doc) != set(ROOT) | {
        "bridgewell_cosco", "hp_logistics_quote_dispute"
    }:
        raise ResearchError("FMC_ROOT_SCHEMA_INVALID")
    for key, val in ROOT.items():
        if type(doc[key]) is not type(val) or doc[key] != val:
            raise ResearchError("FMC_ROOT_FINANCIAL_OR_RIGHTS_FORGED")
    bridge, hp = doc["bridgewell_cosco"], doc["hp_logistics_quote_dispute"]
    if type(bridge) is not dict or set(bridge) != set(BRIDGEWELL) | {
        "reparation_award_groups"
    }:
        raise ResearchError("FMC_BRIDGEWELL_SCHEMA_INVALID")
    exact({k: v for k, v in bridge.items() if k != "reparation_award_groups"},
          BRIDGEWELL, "BRIDGEWELL")
    exact(hp, HPL, "HPL")
    groups = bridge["reparation_award_groups"]
    if type(groups) is not list or len(groups) != len(AWARD_GROUPS):
        raise ResearchError("FMC_AWARD_GROUP_POPULATION_INVALID")
    for row, expected in zip(groups, AWARD_GROUPS, strict=True):
        if type(row) is not dict or frozenset(row) != AWARD_KEYS:
            raise ResearchError("FMC_AWARD_GROUP_SCHEMA_INVALID")
        target = dict(zip(("multiplicity", "principal_cents_each",
                           "interest_cents_each"), expected, strict=True))
        if any(type(row[k]) is not int or row[k] != target[k] for k in target):
            raise ResearchError("FMC_AWARD_GROUP_MONEY_TAMPERED")
    principal = sum(r[0] * r[1] for r in AWARD_GROUPS)
    interest = sum(r[0] * r[2] for r in AWARD_GROUPS)
    if (principal != 2432880 or interest != 396051
        or principal + interest != 2828931
        or hp["initial_quote_cents"] + hp["additional_parts_discussed_cents"]
           != hp["claimed_revised_quote_cents"]
        or hp["final_invoiced_amount_cents"] - hp["claimed_revised_quote_cents"]
           != hp["quote_vs_invoice_difference_cents"]
        or hp["quote_vs_invoice_difference_cents"] +
           hp["additional_demurrage_detention_claim_cents"]
           != hp["total_reparations_sought_cents"]):
        raise ResearchError("FMC_CHARGE_OR_INTEREST_ARITHMETIC_INVALID")
    for url in (bridge["official_initial_decision_url"],
                bridge["official_final_notice_url"],
                hp["official_initial_decision_url"]):
        if safe_url(url) != url:
            raise ResearchError("FMC_UNSAFE_OFFICIAL_DECISION_URL")
    return doc


def load_fixture(path: Path = FIXTURE) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("FMC_FIXTURE_MISSING_OR_INVALID") from exc
    return validate_fixture(doc)


def make_receipt(*, fixture: dict | None = None) -> dict:
    d = load_fixture() if fixture is None else validate_fixture(fixture)
    bridge, hp = d["bridgewell_cosco"], d["hp_logistics_quote_dispute"]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "fmc_cases": [
            {"id": bridge["case_id"],
             "initial_decision": bridge["official_initial_decision_url"],
             "administratively_final_notice": bridge["official_final_notice_url"],
             "status": "FMC_AWARDED_AND_ORDERED;_LATER_CUSTOMER_RECEIPT_AGENCY_REPORTED_SECONDARY_ONLY"},
            {"id": hp["case_id"], "initial_decision": hp["official_initial_decision_url"],
             "status": "NO_REPARATIONS_IN_INITIAL_DECISION_FINALITY_UNVERIFIED"}
        ],
        "bridgewell_initial_claim_cents": bridge["original_reparation_claim_cents"],
        "bridgewell_final_principal_cents": bridge["reparations_principal_cents"],
        "bridgewell_final_interest_as_of_notice_cents":
            bridge["interest_through_january_5_2026_cents"],
        "bridgewell_final_ordered_total_cents":
            bridge["administratively_final_amount_due_cents"],
        "bridgewell_award_components_not_invoice_count":
            sum(row["multiplicity"] for row in bridge["reparation_award_groups"]),
        "bridgewell_reported_late_customer_payment_date":
            bridge["reported_actual_customer_payment_received_date"],
        "bridgewell_later_payment_reported_NOT_verified_bank_receipt": True,
        "bridgewell_exact_received_cash_and_interest_unverified": True,
        "bridgewell_civil_penalties_imposed_cents": None,
        "bridgewell_current_private_motor_freight_authority": False,
        "hpl_initial_quote_cents": hp["initial_quote_cents"],
        "hpl_claimed_amended_quote_cents": hp["claimed_revised_quote_cents"],
        "hpl_final_invoice_cents": hp["final_invoiced_amount_cents"],
        "hpl_invoice_vs_quote_difference_cents": hp["quote_vs_invoice_difference_cents"],
        "hpl_claimed_reparations_cents": hp["total_reparations_sought_cents"],
        "hpl_initial_decision_reparations_awarded_cents":
            hp["initial_decision_reparations_awarded_cents"],
        "hpl_initial_decision_tariff_publication_violation":
            hp["initial_decision_BIC_40501_a_1_tariff_publication_violation"],
        "hpl_initial_decision_section_41102_c_violation":
            hp["initial_decision_section_41102_c_violated"],
        "hpl_final_status_independently_verified": False,
        "original_fmc_pdf_bytes_and_private_invoices_held": False,
        "modern_retally_invoice_accuracy_labels": 0,
        "commercial_customer_reuse_approved": False,
        "retally_recovered_cash_cents": 0,
        "source_authored_fixture_SHA256_NOT_FMC_pdf_hash": digest(d),
        "original_official_pdf_sha256": None,
    }
    return {**body, "receipt_sha256": digest(body)}


def verify_receipt(receipt: object) -> dict:
    if type(receipt) is not dict or set(receipt) != RECEIPT_KEYS or receipt != make_receipt():
        raise ResearchError("FMC_RECEIPT_FORGED_OR_UNSUPPORTED")
    return receipt


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--verify", action="store_true")
    args = cli.parse_args()
    if args.verify:
        if args.output is None:
            cli.error("--verify requires --output")
        try:
            value = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ResearchError("FMC_RECEIPT_NOT_FOUND") from exc
        result = verify_receipt(value)
    else:
        result = make_receipt()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n",
                                   encoding="utf-8")
    print(json.dumps({
        "fmc_cases": len(result["fmc_cases"]),
        "historical_award_total_cents": result["bridgewell_final_ordered_total_cents"],
        "later_customer_payment_government_reported": result[
            "bridgewell_later_payment_reported_NOT_verified_bank_receipt"],
        "actual_external_bank_bytes_in_custody": False,
        "retally_cash_recovered_cents": result["retally_recovered_cash_cents"],
        "verified": args.verify
    }, sort_keys=True))


if __name__ == "__main__":
    main()
