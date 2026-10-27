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
from datetime import date
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
    "official_enforcement_order_url":
        "https://www2.fmc.gov/readingroom/docs/26-13/"
        "%2801%29%2026-13%20Order%20to%20Show%20Cause%20%28public%29.pdf",
    "official_order_payment_made_date_index_excerpt": "2026-08-31",
    "official_order_late_payment_days_index_excerpt": 223,
    "official_order_pdf_bytes_acquired": False,
    "fmc_enforcement_record_index_publicnow":
        "https://www.publicnow.com/view/AEF607AD7C75FCEEFC7781A0221E6505C1BC79B9",
    "reported_actual_customer_payment_received_date": "2026-08-31",
    "reported_payment_lifecycle_source":
        "OFFICIAL_FMC_ORDER_SEARCH_INDEX_EXCERPT_PLUS_INDEPENDENT_MEDIA_REPORTS_NOT_ORIGINAL_ORDER_PDF_OR_BANK_BYTES",
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
# Official 2024 FMC decision and finality notice are independent original source
# descriptions of the bilateral settlement, NOT original signed agreement
# bytes or a carrier accounts-receivable writeoff readback.
LEADER = {
    "case_id": "FMC_2015(I)",
    "claimant": "LEADER_COMMERCE_CORP_DBA_INFINITY_FREIGHT_AND_LOGISTICS",
    "respondent": "MEDITERRANEAN_SHIPPING_COMPANY_USA_INC",
    "shipment_public_bill_of_lading": "MEDUUP205245",
    "original_shipment_origin": "BALTIMORE_USA",
    "original_shipment_destination": "MANAUS_BRAZIL",
    "small_claim_filed_notice_date": "2024-07-31",
    "respondent_submitted_signed_settlement_date": "2024-10-17",
    "original_order_served": "2024-11-08",
    "official_order_url": "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20-Order%20of%20Dismissal.pdf",
    "final_notice_served": "2024-12-10",
    "official_final_notice_url": "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20Not.%20Not%20Review.pdf",
    "settled_final_state": "FMC_APPROVED_BILATERALLY_SIGNED_SETTLEMENT_AND_DISMISSED_WITH_PREJUDICE_ADMINISTRATIVELY_FINAL",
    "fmc_describes_both_parties_signed_settlement": True,
    "signed_settlement_original_bytes_independently_held": False,
    "original_invoice_bol_bank_and_tariff_bytes_in_retally_custody": False,
    "complaint_alleged_low_water_fee_usd_cents": 300000,
    "complaint_alleged_other_extra_fee_usd_cents": 14000,
    "msc_settlement_promise_cancel_OUTSTANDING_UNPAID_demurrage_usd_cents": 465000,
    "msc_settlement_promise_end_collection": True,
    "independent_msc_receivable_writeoff_ledger_confirmation": False,
    "claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_freight_usd_cents": 300000,
    "claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_late_fee_brl_centavos": 70000,
    "cross_currency_addition_or_implicit_conversion_permitted": False,
    "original_bank_evidence_of_previous_claimant_payments_in_retally_custody": False,
    "settlement_result_verified_cash_refund_usd_cents": None,
    "independent_refund_or_tender_bank_receipt_verified": False,
    "liability_finding_original_fees_unlawful": False,
    "claimant_original_economic_loss_independently_verified": False,
    "third_party_contract_rights_for_retally_use": False,
}

AWARD_KEYS = frozenset({"multiplicity", "principal_cents_each", "interest_cents_each"})
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "fmc_cases",
    "bridgewell_initial_claim_cents", "bridgewell_final_principal_cents",
    "bridgewell_final_interest_as_of_notice_cents",
    "bridgewell_final_ordered_total_cents", "bridgewell_award_components_not_invoice_count",
    "bridgewell_reported_late_customer_payment_date",
    "bridgewell_official_order_payment_made_index_excerpt_date",
    "bridgewell_official_order_late_days",
    "bridgewell_original_enforcement_order_pdf_in_custody",
    "bridgewell_bank_receipt_confirmed",
    "bridgewell_actual_bank_receipt_cents",
    "bridgewell_payment_evidence_tier",
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
    "leader_public_bol_authored_digest_NOT_original_BOL_hash",
    "leader_settlement_order_date", "leader_admin_final_notice_date",
    "leader_both_signatures_described_by_FMC_not_original_in_custody",
    "leader_demurrage_UNPAID_cancelled_under_settlement_usd_cents",
    "leader_actual_carrier_ledger_cancellation_verified",
    "leader_previously_paid_freight_refund_rights_waived_usd_cents",
    "leader_previously_paid_late_fee_refund_rights_waived_brl_centavos",
    "leader_usd_brl_conversion_or_sum_allowed",
    "leader_refund_received_bank_verified_usd_cents",
    "leader_complaint_allegations_unadjudicated_usd_cents",
    "leader_original_settlement_and_customer_bank_docs_held",
    "leader_refund_rights_released_not_new_cash_awarded",
    "leader_fmc_order_adjudicated_illegal_billing_amount_cents",
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
        "bridgewell_cosco", "hp_logistics_quote_dispute",
        "leader_commerce_msc_signed_settlement"
    }:
        raise ResearchError("FMC_ROOT_SCHEMA_INVALID")
    for key, val in ROOT.items():
        if type(doc[key]) is not type(val) or doc[key] != val:
            raise ResearchError("FMC_ROOT_FINANCIAL_OR_RIGHTS_FORGED")
    bridge, hp = doc["bridgewell_cosco"], doc["hp_logistics_quote_dispute"]
    leader = doc["leader_commerce_msc_signed_settlement"]
    if type(bridge) is not dict or set(bridge) != set(BRIDGEWELL) | {
        "reparation_award_groups"
    }:
        raise ResearchError("FMC_BRIDGEWELL_SCHEMA_INVALID")
    exact({k: v for k, v in bridge.items() if k != "reparation_award_groups"},
          BRIDGEWELL, "BRIDGEWELL")
    exact(hp, HPL, "HPL")
    exact(leader, LEADER, "LEADER")
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
        or (date.fromisoformat(bridge["official_order_payment_made_date_index_excerpt"])
            - date.fromisoformat(bridge["payment_due_date"])).days != 223
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
                bridge["official_enforcement_order_url"],
                hp["official_initial_decision_url"],
                leader["official_order_url"],
                leader["official_final_notice_url"]):
        if safe_url(url) != url:
            raise ResearchError("FMC_UNSAFE_OFFICIAL_DECISION_URL")
    if not (
        date.fromisoformat(leader["small_claim_filed_notice_date"])
        < date.fromisoformat(leader["respondent_submitted_signed_settlement_date"])
        < date.fromisoformat(leader["original_order_served"])
        < date.fromisoformat(leader["final_notice_served"])
    ):
        raise ResearchError("FMC_SETTLEMENT_CHRONOLOGY_INVALID")
    if (leader["msc_settlement_promise_cancel_OUTSTANDING_UNPAID_demurrage_usd_cents"] != 465000
            or leader["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_freight_usd_cents"] != 300000
            or leader["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_late_fee_brl_centavos"] != 70000
            or leader["settlement_result_verified_cash_refund_usd_cents"] is not None):
        raise ResearchError("FMC_WAIVER_CANCELLATION_OR_CASH_TAMPERED")
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
    leader = d["leader_commerce_msc_signed_settlement"]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "fmc_cases": [
            {"id": bridge["case_id"],
             "initial_decision": bridge["official_initial_decision_url"],
             "administratively_final_notice": bridge["official_final_notice_url"],
             "status": "FMC_FINAL_AWARD;_AGENCY_ORDER_INDEX_EXCERPT_CARRIER_PAID;_CUSTOMER_RECEIPT_SECONDARY_ONLY;_BANK_UNVERIFIED"},
            {"id": hp["case_id"], "initial_decision": hp["official_initial_decision_url"],
             "status": "NO_REPARATIONS_IN_INITIAL_DECISION_FINALITY_UNVERIFIED"},
            {"id": leader["case_id"],
             "initial_decision": leader["official_order_url"],
             "administratively_final_notice": leader["official_final_notice_url"],
             "status": "BILATERAL_SETTLEMENT_APPROVED_AND_FINAL_UNPAID_DEBT_CANCELLED_AND_PREVIOUSLY_PAID_REFUND_CLAIMS_WAIVED_NO_NEW_CASH"}
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
        "bridgewell_official_order_payment_made_index_excerpt_date":
            bridge["official_order_payment_made_date_index_excerpt"],
        "bridgewell_official_order_late_days":
            bridge["official_order_late_payment_days_index_excerpt"],
        "bridgewell_original_enforcement_order_pdf_in_custody": False,
        "bridgewell_bank_receipt_confirmed": False,
        "bridgewell_actual_bank_receipt_cents": None,
        "bridgewell_payment_evidence_tier":
            "OFFICIAL_FMC_ORDER_INDEX_EXCERPT_CARRIER_PAID_SECONDARY_CUSTOMER_RECEIPT_BANK_UNVERIFIED",
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
        "leader_public_bol_authored_digest_NOT_original_BOL_hash":
            digest(leader["shipment_public_bill_of_lading"]),
        "leader_settlement_order_date": leader["original_order_served"],
        "leader_admin_final_notice_date": leader["final_notice_served"],
        "leader_both_signatures_described_by_FMC_not_original_in_custody": True,
        "leader_demurrage_UNPAID_cancelled_under_settlement_usd_cents":
            leader["msc_settlement_promise_cancel_OUTSTANDING_UNPAID_demurrage_usd_cents"],
        "leader_actual_carrier_ledger_cancellation_verified": False,
        "leader_previously_paid_freight_refund_rights_waived_usd_cents":
            leader["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_freight_usd_cents"],
        "leader_previously_paid_late_fee_refund_rights_waived_brl_centavos":
            leader["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_late_fee_brl_centavos"],
        "leader_usd_brl_conversion_or_sum_allowed": False,
        "leader_refund_received_bank_verified_usd_cents": None,
        "leader_complaint_allegations_unadjudicated_usd_cents": [
            leader["complaint_alleged_low_water_fee_usd_cents"],
            leader["complaint_alleged_other_extra_fee_usd_cents"],
        ],
        "leader_original_settlement_and_customer_bank_docs_held": False,
        "leader_refund_rights_released_not_new_cash_awarded": True,
        "leader_fmc_order_adjudicated_illegal_billing_amount_cents": None,
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
