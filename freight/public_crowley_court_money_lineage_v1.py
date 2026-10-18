"""RETALLY Lab14: actual original Crowley/GSA court opinion and fiscal report lineage.

This is an OFFLINE source-document classification proof, not legal advice,
not a live court-docket or customer-contract access, and not original
bank/Treasury transaction proof.

2023 district-court text QUOTES a promise; FY2025 GSA budget independently
REPORTS making that same 2023 payment; 2025 D.C. Circuit remands the
statutory audit-scope question and cites $11.8m PARALLEL money litigation,
not an award or payment. Never sum promise+reported payment twice.
"""
from __future__ import annotations
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"fixtures/public_federal_crowley_gsa_2023_2025_original_court_timeline.json"
SCOPE="PUBLIC_FIRST_PARTY_FEDERAL_COURT_DECISIONS_AND_GSA_BUDGET_REPORTS_NOT_RETALLY"
DOCS={
 "DCD_2023_DFTS_DISTRICT":{
  "publisher":"United States District Court for the District of Columbia via official govinfo",
  "url":"https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_21-cv-02298/pdf/USCOURTS-dcd-1_21-cv-02298-2.pdf",
  "docket":"21-cv-02298","date":"2023-07-28",
 },
 "GSA_FY2025_CONGRESSIONAL":{
  "publisher":"U.S. General Services Administration",
  "url":"https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf",
  "docket":"GSA FY2025 Congressional Justification, Transportation Audits P-2/P-5",
 },
 "CADC_2025_CROWLEY_APPEAL":{
  "publisher":"United States Court of Appeals for the District of Columbia Circuit",
  "url":"https://media.cadc.uscourts.gov/opinions/docs/2025/07/23-5183-2126136.pdf",
  "docket":"23-5183","date":"2025-07-18",
 },
}
EVENTS={
 "APR2023_DFTS_PROMISE":{
  "document":"DCD_2023_DFTS_DISTRICT","date":"2023-04-21",
  "scope":"DFTS I contract",
  "cents":2960000000,"status":"GSA_PROMISED_TO_REFUND_AFTER_AUDIT_ERROR",
 },
 "FY2023_DFTS_REPORTED_PAYMENT":{
  "document":"GSA_FY2025_CONGRESSIONAL","date":"2023-09-30",
  "scope":"DFTS I contract / GSA DoD vendor transportation audit adjustment",
  "cents":2960000000,
  "status":"GSA_FY2023_PUBLISHER_REPORTS_PAYMENT_MADE_TO_DOD_VENDOR",
 },
 "APR2023_OCEAN_SEPARATE_PROMISE":{
  "document":"DCD_2023_DFTS_DISTRICT","date":"2023-04-21",
  "scope":"Ocean USC 9 separate contract",
  "cents":3584043,"status":"GSA_PROMISED_TO_REFUND_SEPARATE_CONTRACT",
 },
 "JUL2025_11_8M_PARALLEL_MONEY_CLAIM":{
  "document":"CADC_2025_CROWLEY_APPEAL","date":"2025-07-18",
  "scope":"DFTS I disputed offset claim before Court of Federal Claims No. 21-1405",
  "cents":1180000000,"status":"CROWLEY_CLAIMED_DAMAGES_NOT_MONEY_AWARDED",
 },
}

def _fail(reason:str)->None:
    raise ValueError("COURT_MONEY_EVIDENCE_"+reason)

def _read()->dict:
    if SRC.is_symlink() or not SRC.is_file() or SRC.stat().st_size>26000:
        _fail("UNTRUSTED_OR_OVERSIZE_INPUT")
    try:data=json.loads(SRC.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as ex:
        raise ValueError("COURT_MONEY_EVIDENCE_INVALID_JSON") from ex
    if type(data) is not dict or frozenset(data)!={
        "schema_version","reviewed_utc_date","subject","scope","contracts",
        "source_documents","publisher_reported_events","appellate_decision",
        "duplicate_and_netting_policy","proof_limits",
    } or type(data.get("schema_version")) is not int or data["schema_version"]!=1:
        _fail("SOURCE_DOCUMENT_SCHEMA_CHANGED")
    if (data["reviewed_utc_date"]!="2026-10-18"
        or data["subject"]!="CROWLEY_GOVERNMENT_SERVICES_DFTS_GSA_FREIGHT_AUDIT_CONTRACT_DISPUTE"
        or data["scope"]!=SCOPE
        or data["contracts"]!={"main":"DoD USTRANSCOM DFTS I","separate":"Ocean USC 9"}):
        _fail("SOURCE_AND_CONTRACT_SCOPE_CHANGED")
    return data

def verified_original_court_money_timeline()->dict:
    data=_read()
    originals=data["source_documents"]
    if type(originals) is not list or len(originals)!=3:
        _fail("THREE_SOURCE_RECORDS_REQUIRED")
    seen=set()
    for doc in originals:
        if type(doc) is not dict or type(doc.get("id")) is not str or doc["id"] not in DOCS:
            _fail("UNKNOWN_ORIGINAL_COURT_SOURCE")
        key=doc["id"]
        if key in seen:_fail("DUPLICATED_SOURCE")
        seen.add(key)
        exp=DOCS[key]
        if (doc.get("publisher")!=exp["publisher"]
            or doc.get("official_url")!=exp["url"]
            or doc.get("case_docket")!=exp["docket"]
            or doc.get("full_original_source_pdf_downloaded_and_sha_verified") is not False
            or type(doc.get("page_location")) is not str
            or len(doc["page_location"])<20):
            _fail("ORIGINAL_PUBLISHER_OR_PROVENANCE_CHANGED")
        if key=="GSA_FY2025_CONGRESSIONAL":
            if (frozenset(doc)!={
                "id","publisher","official_url","case_docket","page_location",
                "full_original_source_pdf_downloaded_and_sha_verified",
                "document_fiscal_budget_year","exact_publisher_release_date_unverified",
            } or type(doc["document_fiscal_budget_year"]) is not int
                or doc["document_fiscal_budget_year"]!=2025
                or doc["exact_publisher_release_date_unverified"] is not True):
                _fail("UNSUPPORTED_GSA_PUBLICATION_DATE")
        elif (frozenset(doc)!={"id","publisher","official_url","case_docket","decided",
                "page_location","full_original_source_pdf_downloaded_and_sha_verified"}
              or doc["decided"]!=exp["date"]):
            _fail("ORIGINAL_COURT_DECISION_DATE_CHANGED")
    if seen!=set(DOCS):_fail("MISSING_GOVERNMENT_SOURCE")
    events=data["publisher_reported_events"]
    if type(events) is not list or len(events)!=4:
        _fail("MISSING_OR_ADDED_FINANCIAL_EVENT")
    seen=set()
    for item in events:
        if type(item) is not dict or item.get("event_id") not in EVENTS:
            _fail("UNKNOWN_FINANCIAL_EVENT")
        key=item["event_id"]
        if key in seen:_fail("DUPLICATED_EVENT")
        seen.add(key)
        exp=EVENTS[key]
        required={"event_id","basis_document","event_date","money_scope",
                  "amount_cents","currency","state","remittance_verified_independently"}
        if key=="FY2023_DFTS_REPORTED_PAYMENT":
            required|={"event_date_represents_fiscal_year_end_not_transaction_date"}
        elif key=="JUL2025_11_8M_PARALLEL_MONEY_CLAIM":
            required.remove("remittance_verified_independently")
            required|={"claim_paid_by_government_as_of_opinion_verified",
                       "independent_later_2026_case_resolution_checked"}
        elif key=="APR2023_OCEAN_SEPARATE_PROMISE":
            required|={"actual_payment_verified"}
        else:
            required|={"actual_payment_recovered_from_this_court_quote"}
        if (frozenset(item)!=required
            or item["basis_document"]!=exp["document"]
            or item["event_date"]!=exp["date"]
            or item["money_scope"]!=exp["scope"]
            or type(item["amount_cents"]) is not int
            or item["amount_cents"]!=exp["cents"]
            or item["currency"]!="USD"
            or item["state"]!=exp["status"]):
            _fail("DATE_SCOPE_OR_FINANCIAL_CLAIM_CHANGED")
        for k in required:
            if k.endswith("_verified") or k.startswith("independent_later_") or k in {
                "remittance_verified_independently",
                "claim_paid_by_government_as_of_opinion_verified",
                "actual_payment_recovered_from_this_court_quote",
            }:
                if item[k] is not False:_fail("UNVERIFIED_MONEY_PROMOTED")
        if key=="FY2023_DFTS_REPORTED_PAYMENT" and (
            item["event_date_represents_fiscal_year_end_not_transaction_date"] is not True
        ):
            _fail("FISCAL_DATE_MISATTRIBUTED")
    if seen!=set(EVENTS):_fail("CASE_TIMELINE_INCOMPLETE")
    court=data["appellate_decision"]
    if type(court) is not dict or frozenset(court)!={
        "source_id","decision_date","opinion_form","holding_limited_to",
        "lower_court_scope_ruling_reversed","remanded_for_further_proceedings",
        "dollar_damages_awarded_in_this_appeal_cents",
        "parallel_11_8m_damages_claim_resolved_by_this_appeal",
        "private_company_auditing_authority_granted",
        "RETALLY_private_contract_remedies_established",
    } or (court["source_id"]!="CADC_2025_CROWLEY_APPEAL"
        or court["decision_date"]!="2025-07-18"
        or court["opinion_form"]!="SPLIT_PANEL_MAJORITY_WITH_DISSENT"
        or court["holding_limited_to"]!=
          "31 U.S.C. § 3726(b) permits GSA to audit transportation bills presented by carriers/freight forwarders; Crowley as intermediary was neither, so GSA could not use that authority for Crowley DFTS bills"
        or court["lower_court_scope_ruling_reversed"] is not True
        or court["remanded_for_further_proceedings"] is not True
        or type(court["dollar_damages_awarded_in_this_appeal_cents"]) is not int
        or court["dollar_damages_awarded_in_this_appeal_cents"]!=0
        or court["parallel_11_8m_damages_claim_resolved_by_this_appeal"] is not False
        or court["private_company_auditing_authority_granted"] is not False
        or court["RETALLY_private_contract_remedies_established"] is not False):
        _fail("LATER_APPELLATE_HOLDING_OR_MONEY_STATUS_CHANGED")
    policy=data["duplicate_and_netting_policy"]
    if type(policy) is not dict or frozenset(policy)!={
        "APR2023_promise_and_FY2023_reported_payment_same_underlying_29_6m",
        "must_not_sum_these_two_as_59_2m",
        "separately_promised_Ocean_35840_43_status_not_upgraded_to_paid",
        "litigation_11_8m_not_recognized_as_paid_award",
        "upstream_GSA_FY2023_amounts_rounded_millions_not_exact_cents",
        "cannot_make_comprehensive_net_Crowley_restitution_total_without_external_records",
    } or not all(value is True for value in policy.values()):
        _fail("FINANCIAL_NETTING_OR_DUPLICATION_UNSAFE")
    proof=data["proof_limits"]
    if type(proof) is not dict or frozenset(proof)!={
        "original_court_pdf_full_bytes_sha_verified","original_GSA_pdf_full_bytes_sha_verified",
        "actual_bank_or_Treasury_transfer_statement_examined",
        "complete_2026_case_docket_checked","RETALLY_customer_source_invoices",
        "RETALLY_customer_verified_recovered_cents",
        "published_statutory_holding_does_not_authorize_private_carrier_offsets",
        "true_customer_overpayment_claim_proven","commercial_claim_clearance",
    } or not (
        proof["original_court_pdf_full_bytes_sha_verified"] is False
        and proof["original_GSA_pdf_full_bytes_sha_verified"] is False
        and proof["actual_bank_or_Treasury_transfer_statement_examined"] is False
        and proof["complete_2026_case_docket_checked"] is False
        and type(proof["RETALLY_customer_source_invoices"]) is int
        and proof["RETALLY_customer_source_invoices"]==0
        and type(proof["RETALLY_customer_verified_recovered_cents"]) is int
        and proof["RETALLY_customer_verified_recovered_cents"]==0
        and proof["published_statutory_holding_does_not_authorize_private_carrier_offsets"] is True
        and proof["true_customer_overpayment_claim_proven"] is False
        and proof["commercial_claim_clearance"]=="NO_GO"
    ):
        _fail("BANK_CUSTODY_AND_CUSTOMER_STATUS_NOT_PROVEN")
    return data

def report()->dict:
    source=verified_original_court_money_timeline()
    events={x["event_id"]:x for x in source["publisher_reported_events"]}
    paid=events["FY2023_DFTS_REPORTED_PAYMENT"]["amount_cents"]
    promised=events["APR2023_DFTS_PROMISE"]["amount_cents"]
    if paid!=promised or paid!=2960000000:
        _fail("PAID_AND_PROMISED_29_6M_ARE_NOT_SAME")
    return {
        "scope":"ORIGINAL_2023_2025_COURT_BUDGET_SOURCES_PUBLIC_ONLY",
        "source_documents":len(source["source_documents"]),
        "source_timeline_events":len(events),
        "2023_DFTS_29_6m_refund_promise_and_GSA_paid_report_same_money":True,
        "GSA_FY2023_reported_vendor_refund_approx_cents":paid,
        "GSA_FY2023_bank_transfer_receipt_independently_authenticated":False,
        "2023_separate_Ocean_USC9_refund_only_promised_cents":events["APR2023_OCEAN_SEPARATE_PROMISE"]["amount_cents"],
        "2023_Ocean_USC9_bank_payment_verified":False,
        "2025_11_8m_Claims_Court_damages_claim_cents":events["JUL2025_11_8M_PARALLEL_MONEY_CLAIM"]["amount_cents"],
        "2025_11_8m_claim_was_awarded_or_paid_by_appeal":False,
        "current_2026_parallel_docket_resolution":None,
        "DCCircuit_2025_limited_GSA_audit_to_carriers_and_freight_forwarders":True,
        "Crowley_this_case_not_a_carrier_or_forwarder":True,
        "private_RETALLY_can_issue_statutory_GSA_offsets":False,
        "underlying_2023_promise_duplicates_2023_budget_reported_payment":True,
        "must_not_double_count_29_6m_as_59_2m":True,
        "original_invoice_and_customer_payment_custody_verified":False,
        "RETALLY_customer_invoices_ever_verified":0,
        "RETALLY_customer_cash_recovered_cents":0,
        "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2))
