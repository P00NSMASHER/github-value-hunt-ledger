"""Original GAO B-192974: wrongful freight-setoff example.

A historical government offset was ACTUALLY APPLIED, but GAO later found
$5,141.05 of it improper under the then-applicable bankruptcy law.
A government collection event must not automatically become legally
retained financial recovery. GAO's instruction to allow a carrier claim
is also NOT independent bank evidence of reimbursement paid.

This read-only original-source validator cannot authorize any action.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_gao_b192974_wrongful_setoff_1979.json"

PINS={
 "schema_version":1,
 "source":"U.S. Government Accountability Office, Comptroller General decision",
 "case_id":"B-192974",
 "decision_date":"1979-03-29",
 "source_original_pdf":"https://www.gao.gov/assets/b-192974.pdf",
 "source_original_summary":"https://www.gao.gov/products/b-192974",
 "source_pages":4,
 "matter":"Yellow Freight System, Inc., successor to Braswell Motor Freight Lines, Inc.",
 "bankruptcy_petition_date":"1976-12-02",
 "bankruptcy_plan_confirmation_date":"1977-07-20",
 "carrier_successor_merger_date":"1978-09-21",
 "prepetition_proof_of_claim_filed_cents":143024,
 "other_unfiled_prepetition_overcharge_claims_cents":747308,
 "prepetition_payable_bills_proper_setoff_cents":214759,
 "postpetition_payable_bills_improper_setoff_cents":514105,
 "original_setoff_was_executed_as_reported":True,
 "postpetition_setoff_legally_upheld":False,
 "prepetition_setoff_legally_upheld":True,
 "reimbursement_claim_should_be_allowed_if_otherwise_correct":True,
 "independent_payment_back_to_carrier_verified":False,
 "retally_customer_payment_recovered_cents":0,
 "net_GAO_retained_overcharge_collections_reported_as_final_cents":None,
 "numeric_buckets_not_interchangeable":True,
 "source_full_pdf_bytes_sha256_verified":False,
 "original_carrier_accounts_or_invoices_examined":False,
 "law_currently_applicable_to_private_commercial_shipper":"NOT_ASSESSED",
 "evidence_tier":"PUBLISHED_GAO_SETTLEMENT_REVERSAL_OR_DISALLOWANCE_NOT_PROVEN_REFUND",
 "publication_scope":"Historical government-carrier Bankruptcy Act case, not a universal present-day rule.",
 "no_current_customer_or_financial_authority":True,
}
EXACT_FINDINGS=(
 "Pre-petition overcharge debts may not be set off against post-petition carrier payable obligations: statutory mutuality absent under the then-applicable Bankruptcy Act.",
 "GAO held pre-petition payables of $2,147.59 properly set off against pre-petition claims.",
 "Claims neither properly filed nor proved in bankruptcy were discharged; successor held no enforceable legal obligation for those additional claims under the facts examined.",
 "GAO recommended GSA allow the successor's $5,141.05 claim if otherwise correct; that is not independent proof GSA actually paid it.",
)

def verified_historical_reversal()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>12_000:
        raise ValueError("GAO_SETTLEMENT_REVERSAL_UNTRUSTED_FILE")
    try:
        raw=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as e:
        raise ValueError("GAO_SETTLEMENT_REVERSAL_INVALID_JSON") from e
    if (type(raw) is not dict or set(raw)!=set(PINS)|{"GAO_findings"}
        or any(type(raw.get(key)) is not type(val) or raw.get(key)!=val
               for key,val in PINS.items())
        or raw.get("GAO_findings")!=list(EXACT_FINDINGS)):
        raise ValueError("GAO_SETTLEMENT_REVERSAL_ORIGINAL_FACT_CHANGED")
    if PINS["prepetition_payable_bills_proper_setoff_cents"]<=0 or (
        PINS["postpetition_payable_bills_improper_setoff_cents"]<=0):
        raise ValueError("GAO_SETTLEMENT_REVERSAL_BROKEN_CASE_ARITHMETIC")

    return {
      "scope":"GAO_1979_APPLIED_OFFSET_LATER_DISALLOWED_NOT_RETALLY_RECOVERY",
      "original_decisions":1,
      "prepetition_allowable_setoff_cents_reported":214759,
      "postpetition_GOVERNMENT_applied_offset_LATER_DISALLOWED_cents":514105,
      "original_offset_was_reported_executed":True,
      "illegal_postpetition_offset_is_valid_permanent_recovery":False,
      "GAO_said_allow_carrier_claim_if_otherwise_correct":True,
      "independent_carrier_repayment_bank_receipt_obtained":False,
      "government_original_overcharge_claims_not_automatically_enforceable":True,
      "government_final_net_collections_credible_cents":None,
      "current_private_shipment_setoff_authorized":False,
      "not_included_in_GAO_approved_historical_collection_tally":True,
      "real_RETALLY_customer_invoice_count":0,
      "actual_RETALLY_cash_recovered_cents":0,
      "original_pdf_full_bytes_not_hashed":True,
      "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(verified_historical_reversal(),sort_keys=True,indent=2))
