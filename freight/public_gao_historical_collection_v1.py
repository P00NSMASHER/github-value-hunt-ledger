"""RETALLY Lab 14 — authentic GAO historical government collection accounts.

These publicly published GAO decisions report historical carrier refunds,
applied offsets/setoffs, contemplated deductions and reimbursement orders.
They are NOT original freight-invoice images, third-party bank statements,
RETALLY customer collections, current tariff authority or a recovery model.

Completely offline, read-only; no secrets, purchases, outreach or mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_gao_historical_freight_collections_20261018.json"
SCOPE="HISTORICAL_US_GOVERNMENT_FREIGHT_AUDITS_NOT_RETALLY_CLIENTS"
PUBLISHER="U.S. Government Accountability Office"
TIER="GAO_REPORTED_REFUND_OR_APPLIED_SET_OFF_NOT_INDEPENDENT_BANK_RECEIPT"
EVENTS=frozenset({"GOVERNMENT_APPLIED_SET_OFF","CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT"})
MAIN_KEYS=frozenset({
 "schema_version","reviewed_at_utc","publisher","source_mode","settlement_proof_tier",
 "scope","external_original_bills_of_lading_examined",
 "independent_Treasury_or_carrier_bank_transaction_statements_examined",
 "actual_retally_client_invoices","actual_retally_customer_recoveries_cents",
 "cases","explicit_source_limits"
})
CASE_KEYS=frozenset({
 "case_id","decision_date","source_url","historical_context",
 "originally_paid_cents","final_agency_assessed_overcharge_cents",
 "gao_reported_collection_events","outstanding_or_future_collection_cents",
 "carrier_reimbursement_authorized_but_payment_unverified_cents",
 "supplemental_carrier_claim_amount_variants_cents",
 "original_bill_of_lading_independently_examined"
})
EVENT_KEYS=frozenset({"kind","amount_cents"})

# Fixed facts transcribed and checked against ORIGINAL GAO publication pages.
# Historical administrative accounts are stronger than unpaid award notices,
# but remain weaker than a separately authenticated bank/Treasury ledger.
EXPECTED={
    "A-14046":{
        "date":"1926-04-23","path":"14046","original":88963,
        "assessed":12775,"events":[("GOVERNMENT_APPLIED_SET_OFF",8358)],
        "future":4417,"possible_carrier_return":0,"disputed_variants":[],
    },
    "B-146511":{
        "date":"1965-06-02","path":"b-146511-2","original":15205,
        "assessed":2074,"events":[("GOVERNMENT_APPLIED_SET_OFF",2074)],
        "future":0,"possible_carrier_return":0,"disputed_variants":[2070,2076],
    },
    "B-148465":{
        "date":"1962-08-27","path":"b-148465","original":54688,
        "assessed":6122,"events":[("GOVERNMENT_APPLIED_SET_OFF",6122)],
        "future":0,"possible_carrier_return":0,"disputed_variants":[],
    },
    "B-148981":{
        "date":"1962-11-29","path":"b-148981","original":175500,
        "assessed":13444,
        "events":[("CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT",13444)],
        "future":0,"possible_carrier_return":0,"disputed_variants":[],
    },
    "B-152324":{
        "date":"1964-04-21","path":"b-152324-0","original":183525,
        "assessed":125477,"events":[
            ("CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT",51450),
            ("GOVERNMENT_APPLIED_SET_OFF",74027),
        ],"future":0,"possible_carrier_return":0,"disputed_variants":[],
    },
    "B-166167":{
        "date":"1969-08-14","path":"b-166167","original":423177,
        "assessed":301632,"events":[("GOVERNMENT_APPLIED_SET_OFF",301632)],
        "future":0,"possible_carrier_return":105083,"disputed_variants":[],
    },
}


def _fail(reason:str)->None:
    raise ValueError("GAO_COLLECTION_PROOF_"+reason)


def _strict_cents(value:object)->int:
    if type(value) is not int or value<0 or value>100_000_000:
        _fail("UNREVIEWED_MONEY_FIELD")
    return value


def verified_gao_cases()->list[dict]:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>32_000:
        _fail("UNTRUSTED_SOURCE_FILE")
    try:
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("GAO_COLLECTION_PROOF_INVALID_JSON") from exc
    if (type(data) is not dict or frozenset(data)!=MAIN_KEYS
        or data["schema_version"]!=1 or type(data["schema_version"]) is not int
        or data["reviewed_at_utc"]!="2026-10-18"
        or data["publisher"]!=PUBLISHER or data["scope"]!=SCOPE
        or data["source_mode"]!="PRIMARY_GAO_PUBLISHED_ADMINISTRATIVE_DECISIONS_TEXT"
        or data["settlement_proof_tier"]!=TIER
        or any(type(data[k]) is not int or data[k]!=0 for k in (
            "external_original_bills_of_lading_examined",
            "independent_Treasury_or_carrier_bank_transaction_statements_examined",
            "actual_retally_client_invoices","actual_retally_customer_recoveries_cents"))
        or type(data["explicit_source_limits"]) is not list
        or len(data["explicit_source_limits"])!=5
        or not all(type(x) is str and len(x)>40 for x in data["explicit_source_limits"])
        or type(data["cases"]) is not list or len(data["cases"])!=len(EXPECTED)):
        _fail("SOURCE_CLASSIFICATION_OR_SCOPE_CHANGED")
    seen=set()
    for row in data["cases"]:
        if type(row) is not dict or frozenset(row)!=CASE_KEYS:
            _fail("UNEXPECTED_CASE_FIELDS")
        case_id=row.get("case_id")
        if type(case_id) is not str or case_id not in EXPECTED or case_id in seen:
            _fail("UNKNOWN_DUPLICATE_CASE")
        seen.add(case_id)
        pin=EXPECTED[case_id]
        if (row["decision_date"]!=pin["date"]
            or row["source_url"]!="https://www.gao.gov/products/"+pin["path"]
            or type(row["historical_context"]) is not str
            or not 30<=len(row["historical_context"])<=300
            or row["original_bill_of_lading_independently_examined"] is not False
            or _strict_cents(row["originally_paid_cents"])!=pin["original"]
            or _strict_cents(row["final_agency_assessed_overcharge_cents"])!=pin["assessed"]
            or _strict_cents(row["outstanding_or_future_collection_cents"])!=pin["future"]
            or _strict_cents(row["carrier_reimbursement_authorized_but_payment_unverified_cents"])
               !=pin["possible_carrier_return"]
            or row["supplemental_carrier_claim_amount_variants_cents"]!=pin["disputed_variants"]):
            _fail("ORIGINAL_GAO_CASE_FACT_MISMATCH")
        events=row["gao_reported_collection_events"]
        if type(events) is not list or len(events)!=len(pin["events"]):
            _fail("SOURCE_EVENT_COUNT_MISMATCH")
        pairs=[]
        for ev in events:
            if (type(ev) is not dict or frozenset(ev)!=EVENT_KEYS
                or ev["kind"] not in EVENTS):
                _fail("INVALID_GAO_EVENT")
            pairs.append((ev["kind"],_strict_cents(ev["amount_cents"])))
        if pairs!=pin["events"] or any(amount<=0 for _,amount in pairs):
            _fail("MISSTATED_AGENCY_RECORDED_COLLECTION")
        if (sum(amount for _,amount in pairs) + row["outstanding_or_future_collection_cents"]
            !=row["final_agency_assessed_overcharge_cents"]):
            _fail("ASSESSED_VS_COLLECTED_OR_PENDING_ARITHMETIC")
        if (row["originally_paid_cents"]<row["final_agency_assessed_overcharge_cents"]):
            _fail("HISTORICAL_AMOUNT_EXCEEDS_ORIGINAL_PAYMENT")

    if seen!=set(EXPECTED):
        _fail("SOURCE_CASE_COVERAGE_CHANGED")
    fixed={x["case_id"]:x for x in data["cases"]}
    # In B-152324, one GAO-described shipment had original $1835.25,
    # refund $514.50, applied deduction $740.27, allowing $580.48.
    if fixed["B-152324"]["originally_paid_cents"]-sum(
        ev["amount_cents"] for ev in fixed["B-152324"]["gao_reported_collection_events"]
    )!=58048:
        _fail("SAME_SHIPMENT_CHARGES_NOT_RECONCILED")
    # B-166167: $1050.83 authorized for later repayment TO THE CARRIER;
    # no proof a refund certificate was actually paid, so no final net claim.
    if fixed["B-166167"]["carrier_reimbursement_authorized_but_payment_unverified_cents"]!=105083:
        _fail("UNVERIFIED_REVERSAL_AMOUNT_CHANGED")
    return data["cases"]


def public_collection_report()->dict:
    rows=verified_gao_cases()
    events=[e for row in rows for e in row["gao_reported_collection_events"]]
    by_type={kind:sum(e["kind"]==kind for e in events) for kind in sorted(EVENTS)}
    if len(events)!=7 or by_type!={"CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT":2,"GOVERNMENT_APPLIED_SET_OFF":5}:
        _fail("REPORT_EVENT_CENSUS_INCONSISTENT")
    return {
        "scope":"LAB14_ORIGINAL_GAO_GOVERNMENT_COLLECTION_CASES_NOT_CUSTOMER_SAVINGS",
        "publisher":"U.S. Government Accountability Office",
        "historical_distinct_decisions":len(rows),
        "gao_reported_collection_events":len(events),
        "agency_reported_collection_modes":by_type,
        "cases_with_uncollected_future_deduction":1,
        "cases_with_carrier_refund_authorized_but_unverified_paid":1,
        "cases_with_disputed_amount_variants":1,
        "source_transcribed_historical_collection_report_not_payment_bank_proof":True,
        "full_original_invoice_images_compared":False,
        "actual_carrier_account_bank_or_Treasury_posting_independently_verified":False,
        "final_unreversed_net_government_recovery_total_cents":None,
        "real_RETALLY_customer_invoices_examined":0,
        "real_RETALLY_customer_recoveries_cents":0,
        "market_accuracy_or_recoverable_rate_inferred":False,
        "different_government_vs_private_shipper_legal_authority":True,
        "commercial_claim_clearance":"NO_GO",
    }


def main()->None:
    print(json.dumps(public_collection_report(),sort_keys=True,indent=2))


if __name__=="__main__":
    main()
