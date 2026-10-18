"""Read-only RETALLY Lab14 evidence gate for original GAO B-197184.

The original two-page 1980 GAO letter and internal memorandum report GSA
actually deducted $475.36 against Yellow Freight, later acknowledged the
setoff was improper, and GAO dismissed the carrier's review as moot.
Conditional claim allowance is not proof that a refund was paid.

Never gives legal advice, authorizes an offset, or declares RETALLY recoveries.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"fixtures/public_gao_b197184_improper_deduction_1980.json"

PINS={
 "schema_version":1,
 "provenance_type":"US_GAO_ORIGINAL_CORRESPONDENCE_AND_INTERNAL_MEMORANDUM",
 "source_publisher":"US General Accounting Office / Comptroller General, Office of General Counsel",
 "original_report_pdf":"https://www.gao.gov/assets/b-197184.pdf",
 "decision_reference":"B-197184",
 "original_document_date":"1980-03-26",
 "publisher_original_pdf_pages":2,
 "plaintiff_carrier_reported":"Yellow Freight System, Inc.",
 "earlier_carrier_reported":"Braswell Motor Freight Lines, Inc.",
 "government_agency_that_applied_setoff":"General Services Administration",
 "billed_government_bill_of_lading":"K-5405056",
 "reported_original_bill_of_lading_date":"1976-11-15",
 "reported_original_shipper_liability_petition_date":"1976-12-02",
 "old_overcharge_collected_by":"Braswell Motor Freight Lines, Inc.",
 "deduction_applied_against":"Yellow Freight System, Inc.",
 "deduction_reported_already_applied_cents":47536,
 "original_carrier_requested_review_at_GAO":True,
 "GSA_acknowledged_original_setoff_improper":True,
 "GAO_review_dismissed_as_moot":True,
 "GAO_reported_claim_allowable_if_otherwise_proper":True,
 "original_claim_payment_to_carrier_actually_verified":False,
 "original_invoice_or_bill_of_lading_independently_examined":False,
 "independent_treasury_or_bank_disbursement_seen":False,
 "contemporaneous_GAO_original_document_text_examined":True,
 "source_full_pdf_bytes_sha256_verified":False,
 "published_letter_statements_are_not_independent_bank_payment_proof":True,
 "legally_retained_government_net_recovery_cents":None,
 "actual_payment_back_to_carrier_cents":None,
 "RETALLY_real_customer_invoices_examined":0,
 "RETALLY_real_customer_recoveries_cents":0,
 "case_law_not_automatically_applicable_to_private_2026_carriers":True,
 "source_summary":"GAO recorded an earlier $475.36 GSA deduction against Yellow Freight for an alleged overcharge previously collected by Braswell; GSA later acknowledged the setoff was improper, and GAO dismissed Yellow's review as moot with conditional claim allowance, without independent proof of repayment.",
 "evidence_class":"ORIGINAL_GAO_IMPROPER_COLLECTED_OFFSET_LATER_CONCEDED_NOT_PAYMENT_VERIFIED",
 "data_use":"INTERNAL_LAB14_NEGATIVE_CONTROL_RESEARCH_ONLY",
}

def verified_improper_offset()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>10000:
        raise ValueError("GAO_B197184_UNTRUSTED_SOURCE")
    try:
        source=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as e:
        raise ValueError("GAO_B197184_MALFORMED_SOURCE") from e
    if (type(source) is not dict or frozenset(source)!=frozenset(PINS)
        or any(type(source.get(k)) is not type(v) or source[k]!=v
               for k,v in PINS.items())):
        raise ValueError("GAO_B197184_SOURCE_FACT_OR_REPAYMENT_STATUS_CHANGED")
    return {
        "scope":"GAO_1980_WRONGFULLY_APPLIED_GOVERNMENT_OFFSET_NO_RETALLY_CASH",
        "original_decision_count":1,
        "published_original_GAO_letter_and_memo_verified_text":True,
        "original_offset_reported_applied_cents":47536,
        "GSA_later_admitted_setoff_wrong":True,
        "GAO_review_closed_as_moot":True,
        "GAO_claim_allowable_subject_to_other_propriety":True,
        "carrier_actual_repayment_confirmed":False,
        "confirmed_carrier_bank_disbursement_cents":None,
        "permanent_legally_retained_government_collection_cents":None,
        "original_full_pdf_SHA256_not_verified":True,
        "historical_specific_bankruptcy_liability_not_current_private_legal_authority":True,
        "distinct_from_GAO_B192974_larger_improper_setoff":True,
        "not_a_separate_RETALLY_customer_case":True,
        "real_RETALLY_customer_invoice_count":0,
        "real_RETALLY_cash_recovered_cents":0,
        "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(verified_improper_offset(),sort_keys=True,indent=2))
