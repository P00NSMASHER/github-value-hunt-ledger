"""Independent GAO original freight rate-line arithmetic and correction review.

1967 government B-160344: $275.17 paid at 1,485 lb and $18.53/cwt;
government documentary classification correction changes rating to $9.38/cwt,
GAO states $139.29 allowable and $135.88 already deducted.

1976 government B-186603: one original Washington DC GBL origin rebutted by
independent manufacturer/location evidence (actual Canton MS); a $133.28
deduction already occurred, but GAO says allow carrier's claim *if otherwise
correct*. A second blanket bill within that GAO decision remains SEPARATE.
None is a RETALLY customer, privately authorized tariff or recovered cash.

The source data is public government decision text, NOT independent original
carrier bill/tariff pages, signed private contracts, or bank statements.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

SOURCE=Path(__file__).resolve().parent/"fixtures/public_gao_rate_reclassification_and_origin_rebuttal_20261018.json"
PUBLISHER="U.S. Government Accountability Office"
ROOT_FIELDS={"schema_version","reviewed_utc_date","publisher","research_scope","sources",
             "source_evidence_level","general_prohibitions",
             "retally_actual_customer_invoices","retally_verified_recoveries_cents",
             "bank_or_treasury_receipts_independently_examined",
             "verified_commercial_recovery_clearance"}
B160344={
    "decision_id":"B-160344","date":"1967-07-18",
    "url":"https://www.gao.gov/products/b-160344",
    "document_reference":"Government Bill of Lading B-5378637; carrier bill 141",
    "shipment_origin_and_destination":"Akron, OH to Warner Robins Air Force Base, GA",
    "source_shipment_date":"1962-12-19",
    "freight_paid_month":"1963-03",
    "freight_claimed_original_paid_cents":27517,
    "actual_reported_weight_pounds":1485,
    "original_claimed_nmfc_item":"14440","original_claimed_class":"400",
    "original_claimed_rate_cents_per_100_pounds":1853,
    "government_accepted_nmfc_item":"12400","government_accepted_class":"200",
    "government_accepted_rate_cents_per_100_pounds":938,
    "later_government_bill_of_lading_correction_month":"1964-02",
    "later_document_correction_is_after_original_payment":True,
    "government_audited_allowable_cents":13929,
    "determined_overcharge_cents":13588,
    "refund_voluntarily_made_for_selected_bill":False,
    "government_applied_setoff_cents":13588,
    "setoff_date":"1965-12",
    "carrier_reclaim_disallowed_in_source":True,
    "authoritative_classification_reason":"Airframe nose essential to C-130 flight, not principally a ground radar antenna enclosure; contemporaneous Air Force technical statement",
    "original_bol_scan_independently_inspected":False,
    "contract_nmfc_original_page_independently_inspected":False,
    "historical_federal_decision_not_current_tariff_authority":True
}
BLANKETS={
 "original_bill_of_lading":"D-8271398",
 "shipment_date":"1972-06-23",
 "freight_shipment":"1,624 lb blankets, Clearfield UT to Gallup NM",
 "government_reported_offset_cents":5765,
 "subsequently_issued_carrier_settlement_certificate_cents":2290,
 "certificate_issue_date_stated_in_decision":"1976-02-29",
 "certificate_actual_payment_or_carrier_receipt_verified":False,
 "original_bill_of_lading_scan_independently_inspected":False,
 "separate_transaction_not_part_of_chair_shipment":True
}
CHAIRS={
 "original_bill_of_lading":"F-7349731",
 "shipment_date":"1972-12-21",
 "freight_shipment":"40 chairs, 2,800 lb, to Brooklyn VA hospital",
 "government_reported_original_paid_cents":39816,
 "bill_of_lading_origin":"Washington DC",
 "corroborated_actual_origin":"Canton Mississippi",
 "original_bill_of_lading_origin_rebutted":True,
 "manufacturer_corrob_scope":"Manufacturer stated DC was an ordering office, not a factory; Canton was a production point",
 "government_reported_offset_cents":13328,
 "GAO_decision":"GSA SHOULD ALLOW carrier claim for $133.28 IF OTHERWISE CORRECT",
 "carrier_repayment_bank_receipt_verified":False,
 "original_bill_of_lading_scan_independently_inspected":False,
 "government_claimed_overcharge_is_still_valid_after_ruling":False,
 "origin_correction_does_not_prove_other_customer_rate":True
}
B186603={
 "decision_id":"B-186603","date":"1976-12-22",
 "url":"https://www.gao.gov/products/b-186603",
 "issues":[BLANKETS,CHAIRS],
 "no_aggregate_recovery_claim_across_unrelated_bills":True,
 "government_source_only_not_private_customer_contract":True
}
SCOPE="TWO_GAO_PUBLISHED_HISTORICAL_RATE_AND_DOCUMENT_CORRECTION_CASES"
EVIDENCE_LEVEL="ORIGINAL_GAO_PUBLIC_DECISION_TEXT_NOT_INDEPENDENT_ORIGINAL_BILL_TARIFF_OR_TREASURY"

def _deny(reason:str)->None:
    raise ValueError("GAO_RATING_SOURCE_"+reason)

def _money(x:object)->int:
    if type(x) is not int or not 0<=x<100_000_000:
        _deny("INVALID_MONEY_INTEGER")
    return x

def _bill_cents(weight_lb:int,rate_cents_per_100_lb:int)->int:
    if any(type(x) is not int or x<=0 for x in (weight_lb,rate_cents_per_100_lb)):
        _deny("INVALID_WEIGHT_OR_RATE")
    return int((Decimal(weight_lb)*Decimal(rate_cents_per_100_lb)/Decimal(100))
               .quantize(Decimal("1"),rounding=ROUND_HALF_UP))

def reviewed_source()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>15_000:
        _deny("UNTRUSTED_SOURCE_FILE")
    try:
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as e:
        raise ValueError("GAO_RATING_SOURCE_BAD_JSON") from e
    if (type(data) is not dict or set(data)!=ROOT_FIELDS
        or type(data["schema_version"]) is not int or data["schema_version"]!=1
        or data["reviewed_utc_date"]!="2026-10-18"
        or data["publisher"]!=PUBLISHER or data["research_scope"]!=SCOPE
        or data["source_evidence_level"]!=EVIDENCE_LEVEL
        or any(type(data[k]) is not int or data[k]!=0 for k in (
            "retally_actual_customer_invoices","retally_verified_recoveries_cents",
            "bank_or_treasury_receipts_independently_examined"))
        or data["verified_commercial_recovery_clearance"] is not False
        or not isinstance(data["general_prohibitions"],list)
        or len(data["general_prohibitions"])!=6
        or any(type(x) is not str or len(x)<35 for x in data["general_prohibitions"])
        or type(data["sources"]) is not list or len(data["sources"])!=2
        or data["sources"][0]!=B160344 or data["sources"][1]!=B186603):
        _deny("DOCUMENT_OR_CUSTOMER_AUTHORITY_CHANGED")
    x,y=data["sources"]
    if (_bill_cents(x["actual_reported_weight_pounds"],
                    x["original_claimed_rate_cents_per_100_pounds"])
        !=_money(x["freight_claimed_original_paid_cents"])
        or _bill_cents(x["actual_reported_weight_pounds"],
                       x["government_accepted_rate_cents_per_100_pounds"])
        !=_money(x["government_audited_allowable_cents"])
        or x["freight_claimed_original_paid_cents"]-
           x["government_audited_allowable_cents"] != x["determined_overcharge_cents"]
        or x["determined_overcharge_cents"]!=x["government_applied_setoff_cents"]):
        _deny("RATING_ARITHMETIC_MISMATCH")
    shipment=date.fromisoformat(x["source_shipment_date"])
    paid=date.fromisoformat(x["freight_paid_month"]+"-01")
    correction=date.fromisoformat(x["later_government_bill_of_lading_correction_month"]+"-01")
    offset=date.fromisoformat(x["setoff_date"]+"-01")
    decided=date.fromisoformat(x["date"])
    if not (shipment < paid < correction < offset < decided):
        _deny("DOCUMENT_CORRECTION_CHRONOLOGY")
    blankets,chairs=y["issues"]
    if (blankets["original_bill_of_lading"]==chairs["original_bill_of_lading"]
        or not blankets["separate_transaction_not_part_of_chair_shipment"]
        or chairs["bill_of_lading_origin"]==chairs["corroborated_actual_origin"]
        or chairs["carrier_repayment_bank_receipt_verified"] is not False
        or chairs["government_claimed_overcharge_is_still_valid_after_ruling"] is not False
        or _money(chairs["government_reported_offset_cents"])!=13328
        or _money(blankets["government_reported_offset_cents"])!=5765
        or _money(blankets["subsequently_issued_carrier_settlement_certificate_cents"])!=2290):
        _deny("SOURCE_ORIGIN_OR_SETTLEMENT_DISTINCTION")
    return data

def report()->dict:
    documents=reviewed_source()["sources"]
    charge=documents[0]
    other=documents[1]
    return {
     "scope":"TWO_ORIGINAL_GAO_DOCUMENTARY_RATING_CASES_RESEARCH_ONLY",
     "original_GAO_published_decisions_reviewed":2,
     "distinct_GBL_references_in_decisions":3,
     "government_B160344_actual_reported_weight_lb":charge["actual_reported_weight_pounds"],
     "government_B160344_claimed_paid_cents":charge["freight_claimed_original_paid_cents"],
     "government_B160344_allowable_cents":charge["government_audited_allowable_cents"],
     "government_B160344_reported_collection_by_setoff_cents":charge["government_applied_setoff_cents"],
     "government_B160344_paid_date_precedes_corrected_description":True,
     "government_B186603_chair_GBL_origin_disproved":True,
     "government_B186603_chair_13328_setoff_origin_basis_rebutted_claim_allowance_conditional":True,
     "government_B186603_chair_repayment_bank_receipt_verified":False,
     "government_B186603_blanket_5765_offset_separately_recorded":True,
     "government_B186603_blanket_2290_certificate_not_proved_paid":True,
     "all_event_net_cash_totals_explicitly_UNVERIFIED":True,
     "source_contains_noncustomer_historical_government_bills_only":True,
     "original_transport_bol_scans_and_NMFC_tariff_not_inspected":True,
     "current_commercial_rating_authority":"NOT_ESTABLISHED",
     "real_RETALLY_client_invoices":0,
     "real_RETALLY_customer_overcharges_cents":0,
     "real_RETALLY_customer_recoveries_cents":0,
     "commercial_release":"NO_GO"
    }

if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2))
