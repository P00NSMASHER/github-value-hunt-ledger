"""RETALLY Lab 14: publicly adjudicated FMC order is NOT recovered cash.

Original federal court/agency notice, no original private invoice data.
No customer contact, refunds or legal enforcement actions are available.
"""
import json
from pathlib import Path

SOURCE=Path(__file__).resolve().parent/"fixtures/public_fmc_2030i_reparations_final_notice_2026.json"
EXPECTED={
    "case_reference":"FMC_2030(I)",
    "issuer":"US Federal Maritime Commission",
    "original_document_url":"https://www2.fmc.gov/readingroom/docs/2030%28I%29/%2815%29%202030%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf",
    "notice_type":"NOTICE_NOT_TO_REVIEW_INITIAL_DECISION",
    "notice_served_date":"2026-04-28",
    "initial_decision_date":"2026-03-27",
    "admin_final_as_of_notice_date":True,
    "respondent_organization":"Formula Global Mobility",
    "payment_order_due_date":"2026-05-13",
    "adjudicated_reparations_cents":866879,
    "adjudicated_interest_cents":98572,
    "final_payment_order_cents":965451,
}
FLAGS={
    "original_government_order_indexed_text_confirmed":True,
    "original_pdf_full_bytes_downloaded_and_hashed":False,
    "original_invoice_and_tariff_independently_replayed":False,
    "third_party_payment_receipt_inspected":False,
    "proof_order_paid_or_settled":False,
    "actual_money_recovered_cents":None,
    "retally_customer_invoices_inspected":0,
    "retally_customer_recoveries_cents":0,
}

def verified_public_order()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>9000:
        raise ValueError("FMC_ORDER_UNVERIFIED_SOURCE")
    try:
        facts=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("FMC_ORDER_UNREADABLE_SOURCE") from exc
    allowed=set(EXPECTED)|set(FLAGS)|{
        "schema_version","allowable_interpretation","source_legal_scope"
    }
    if (type(facts) is not dict or set(facts)!=allowed
        or type(facts.get("schema_version")) is not int
        or facts["schema_version"]!=1
        or any(type(facts.get(k)) is not type(v) or facts[k]!=v
               for k,v in {**EXPECTED,**FLAGS}.items())
        or facts.get("allowable_interpretation")!=
        "Real third-party agency final administrative reparations order; NOT confirmed paid, not RETALLY revenue or recovery, not original customer invoice data."
        or not isinstance(facts.get("source_legal_scope"),str)):
        raise ValueError("FMC_ORDER_EVIDENCE_OR_PAYMENT_STATUS_CHANGED")
    awarded=facts["adjudicated_reparations_cents"]+facts["adjudicated_interest_cents"]
    if awarded!=facts["final_payment_order_cents"]:
        raise ValueError("FMC_ORDER_MONEY_DOES_NOT_RECONCILE")
    return {
        "scope":"THIRD_PARTY_PUBLIC_ADJUDICATED_ORDER_NO_RETALLY_CUSTOMER",
        "documented_final_reparations_order_cents":awarded,
        "documented_reparations_cents":facts["adjudicated_reparations_cents"],
        "documented_interest_cents":facts["adjudicated_interest_cents"],
        "administratively_final_as_of_2026_04_28":True,
        "agency_order_to_pay_due_2026_05_13":True,
        "claimant_bank_or_payment_receipt_confirmed":False,
        "actual_payment_verified_cents":None,
        "retally_validated_recovery_cents":0,
        "retally_invoice_data_used":False,
        "legal_precedent_for_other_case_automatically_applicable":False,
        "customer_recovery_or_marketing_authority":"NOT_ESTABLISHED",
    }

if __name__=="__main__":
    print(json.dumps(verified_public_order(),sort_keys=True,indent=2))
