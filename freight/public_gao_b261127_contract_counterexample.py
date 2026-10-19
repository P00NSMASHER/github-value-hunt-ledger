"""Original GAO B-261127: a mathematically apparent overcharge was legally rejected.

Research-only comparison with GAO B-197658, which involved the SAME
general question of transport units but an opposite CONTRACTUAL outcome.
Without the specific effective contract and qualified authority, arithmetic
difference is NOT an overcharge. Does not ingest private invoices or send
customer communications; static first-party publication facts only.
"""
from __future__ import annotations

import json
from pathlib import Path
from freight.public_gao_historical_collection_v1 import (
    verify_gao_1980_original_rating_arithmetic,
)

SOURCE=Path(__file__).resolve().parent/"fixtures/public_gao_b261127_canupp_tcn_gbl_1996.json"
EXPECTED={
    "schema_version":1,
    "source_kind":"GAO_ORIGINAL_PUBLISHED_CONTRACT_INTERPRETATION_DECISION",
    "source_url":"https://www.gao.gov/products/b-261127",
    "source_decision_id":"B-261127",
    "date":"1996-02-15",
    "carrier":"Canupp Trucking, Inc.",
    "historical_government_contract":"Guaranteed traffic tender 600029, MTMC/NAVMTO Note 12 and Note 14",
    "historic_gbl_number":"C-8,141,261",
    "historically_billed_note12_tcn_counts":{
        "minimum_charged_tcns":63,
        "above_breakpoint_tcns":2,
        "total_tcns":65,
    },
    "minimum_charge_cents_per_tcn":2500,
    "other_tcn_individual_charges_cents":[2850,5590],
    "reported_actual_carrier_note12_charge_cents":165940,
    "government_proposed_one_gbl_rate_cents_per_cwt":200,
    "government_proposed_gbl_weight_pounds":14320,
    "government_proposed_one_gbl_charge_cents":28640,
    "arithmetic_difference_cents_between_billing_methods":137300,
    "government_requested_note12_overcharge_determination_supported_by_final_GAO_decision":False,
    "GAO_historical_result_note12":"CARRIER_NOTE12_TCN_BILLING_UPHELD",
    "GAO_historical_result_note14":"ADDITIONAL_TERMINAL_CHARGES_DENIED_AS_DUPLICATE",
    "contract_ambiguous_shipment_term":True,
    "prior_agency_written_contract_full_copy_independently_retrieved":False,
    "agency_qualified_personnel_approved_TCN_billing_before_first_invoice":True,
    "agency_no_objection_course_of_performance_over_three_years":True,
    "carrier_reported_1062_GBLs_billed_using_TCN_method_not_independently_verified":True,
    "original_carrier_invoice_image_independently_examined":False,
    "original_rate_tender_signed_copy_independently_examined":False,
    "government_notices_of_overcharge_from_original_archive_independently_examined":False,
    "separate_bank_receipt_examined":False,
    "payment_or_refund_by_carrier_after_decision_independently_verified":False,
    "recoverable_overcharge_cents_under_GAO_note12_ruling":0,
    "retally_customer_invoice_count":0,
    "retally_recovered_cents":0,
    "present_day_private_carrier_contract_applicability":"UNVERIFIED",
    "official_legal_document_status":"PUBLISHED_GAO_DECISION_NOT_CURRENT_CUSTOMER_CONTRACT",
    "disposition":"GAO_CONTRACT_SPECIFIC_FALSE_POSITIVE_DIFFERENCE_NOT_RECOVERABLE",
}

def _fail(code:str)->None:
    raise ValueError("GAO_CONTRACT_INTERPRETATION_"+code)

def verify_1996_original_source()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>14000:
        _fail("UNTRUSTED_SOURCE")
    try:
        doc=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError("GAO_CONTRACT_INTERPRETATION_UNREADABLE_FIXTURE") from exc
    if type(doc) is not dict or set(doc)!=set(EXPECTED):
        _fail("UNEXPECTED_SOURCE_FIELDS")
    for key,val in EXPECTED.items():
        actual=doc.get(key)
        if type(actual) is not type(val) or actual!=val:
            _fail("ORIGINAL_SOURCE_OR_CONTRACT_FACT_CHANGED")
    parts=doc["historically_billed_note12_tcn_counts"]
    quantities=doc["other_tcn_individual_charges_cents"]
    if (type(parts) is not dict or type(quantities) is not list
        or any(type(v) is not int or v<=0 for v in quantities)
        or any(type(v) is not int or v<=0 for v in parts.values())):
        _fail("BILLING_COMPONENTS_INVALID")
    if parts["total_tcns"]!=parts["minimum_charged_tcns"]+parts["above_breakpoint_tcns"]:
        _fail("TCN_COUNT_NOT_RECONCILED")
    if parts["above_breakpoint_tcns"]!=len(quantities):
        _fail("ADDITIONAL_TCN_CHARGES_NOT_RECONCILED")
    carrier_charge=parts["minimum_charged_tcns"]*doc["minimum_charge_cents_per_tcn"]+sum(quantities)
    government_charge=(doc["government_proposed_gbl_weight_pounds"]
                       *doc["government_proposed_one_gbl_rate_cents_per_cwt"])//100
    # The exact cited GBL weight is a whole number of cwt (14320 pounds)
    # so no rounding convention is invented.
    if (doc["government_proposed_gbl_weight_pounds"]%100!=20
        or carrier_charge!=doc["reported_actual_carrier_note12_charge_cents"]
        or government_charge!=doc["government_proposed_one_gbl_charge_cents"]
        or carrier_charge-government_charge!=doc["arithmetic_difference_cents_between_billing_methods"]
        or doc["recoverable_overcharge_cents_under_GAO_note12_ruling"]!=0):
        _fail("PUBLISHED_ARITHMETIC_OR_GAO_DISPOSITION_MISMATCH")
    return {
        "source":"GAO_B_261127_ORIGINAL_PUBLIC_DECISION_1996",
        "historical_decision_date":doc["date"],
        "original_government_bill_of_lading_number":doc["historic_gbl_number"],
        "carrier_reported_note12_charges_cents":carrier_charge,
        "government_proposed_note12_charges_cents":government_charge,
        "numerical_difference_cents":carrier_charge-government_charge,
        "gaomajority_note12_carrier_billing_upheld":True,
        "gaodecision_note14_additional_charges_denied_as_duplicate":True,
        "prebilling_government_guidance_controls_specific_contract_interpretation":True,
        "course_of_performance_requires_contextual_review":True,
        "GAO_sustained_alleged_note12_overcharge":False,
        "GAO_case_supported_recoverable_note12_overcharge_cents":0,
        "real_original_invoice_or_signed_contract_scans_examined":False,
        "independent_bank_settlement_record_examined":False,
        "present_day_private_freight_rate_applicability":"UNVERIFIED",
        "retally_verified_customer_invoice_count":0,
        "retally_real_recovery_cents":0,
        "commercial_claim":"NO_GO",
    }

def compare_opposite_contract_interpretations()->dict:
    """Contrasting original GAO cases: same issue type, opposite outcomes.

    One old public case was a documented government refund+setoff; the other
    upheld the carrier's higher charge. The comparison is NEVER a global
    rule that every split bill is an overcharge or every TCN charge allowed.
    """
    favorable=verify_gao_1980_original_rating_arithmetic()
    adverse=verify_1996_original_source()
    if (favorable["scope"]!="1980_ORIGINAL_GAO_HISTORICAL_TARIFF_DISPUTE_ARITHMETIC_ONLY"
        or favorable["GAO_correct_one_lot_charge_cents"]!=617063
        or favorable["sum_original_historical_collections_cents"]!=164979
        or favorable["independent_bank_or_Treasury_receipt_examined"] is not False
        or adverse["numerical_difference_cents"]!=137300
        or adverse["gaomajority_note12_carrier_billing_upheld"] is not True
        or adverse["GAO_case_supported_recoverable_note12_overcharge_cents"]!=0):
        _fail("OPPOSITE_GAO_DECISION_CROSS_SOURCE_GUARD_FAILED")
    return {
        "scope":"TWO_ORIGINAL_GAO_DECISIONS_DIFFERENT_TENDERS_AND_CONTRACTS",
        "historical_1980_government_reported_refund_and_setoff_cents":164979,
        "historical_1996_apparent_charge_difference_cents":137300,
        "historical_1996_GAO_rejected_overcharge_cents":137300,
        "historical_1996_GAO_sustained_note12_overcharge_cents":0,
        "same_source_authority_or_tariff_in_both_cases":False,
        "one_bill_of_lading_always_equals_a_single_chargeable_shipment":False,
        "notice_of_overcharge_amount_is_not_conclusive":True,
        "prebilling_government_approved_methods_must_be_reviewed":True,
        "contract_effective_terms_must_be_independently_proven":True,
        "never_transfer_1980_government_authority_to_private_customer":True,
        "original_customer_invoices_checked":0,
        "verified_RETALLY_recoveries_cents":0,
        "retally_prospect_contact_or_recovery_authorized":False,
        "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(compare_opposite_contract_interpretations(),sort_keys=True,indent=2))
