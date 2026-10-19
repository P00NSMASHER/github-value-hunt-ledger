"""GAO B-186603 (1976): erroneous origin written on a Government BOL.

First-party published decision describes TWO distinct freight disputes:
(1) $133.28 was deducted from an originally $398.16 paid invoice,
    but the written Washington, DC shipment origin was rebutted by
    manufacturer/agency evidence showing actual shipment from Canton, MS.
    GAO said allow carrier refund claim IF OTHERWISE CORRECT.
(2) For a separate shipment, $57.65 was deducted and GSA issued a
    $22.90 settlement certificate; no independent payment receipt.
NEITHER is a RETALLY recovery nor independently proved refund paid.
"""
from __future__ import annotations
import json
from pathlib import Path

SOURCE=Path(__file__).resolve().parent/"fixtures/public_gao_b186603_wrong_gbl_origin_1976.json"
ORIGINAL="https://www.gao.gov/products/b-186603"

def _fail(code:str)->None:
    raise ValueError("GAO_BOL_ORIGIN_"+code)

def verified_original_gao_origin_decision()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>15000:
        _fail("SOURCE_NOT_A_BOUNDED_FILE")
    try:
        d=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("GAO_BOL_ORIGIN_SOURCE_READ_ERROR") from exc
    keys={"schema_version","issuer","source_url","decision_id","decision_date",
          "carrier","historical_shipment_disputes",
          "max_original_overcharge_amount_proved_valid_per_decision_cents",
          "actual_carrier_refunds_paid_verified_cents",
          "two_distinct_GBLs_must_not_be_combined_as_a_single_recovered_balance",
          "RETALLY_original_customer_invoices_verified","RETALLY_recoveries_cents",
          "legal_status","note"}
    if (type(d) is not dict or set(d)!=keys or type(d.get("schema_version")) is not int
        or d["schema_version"]!=1
        or d["issuer"]!="U.S. Government Accountability Office"
        or d["source_url"]!=ORIGINAL or d["decision_id"]!="B-186603"
        or d["decision_date"]!="1976-12-22"
        or d["carrier"]!="Navajo Freight Lines, Inc."
        or d["max_original_overcharge_amount_proved_valid_per_decision_cents"] is not None
        or d["actual_carrier_refunds_paid_verified_cents"] is not None
        or d["two_distinct_GBLs_must_not_be_combined_as_a_single_recovered_balance"] is not True
        or type(d["RETALLY_original_customer_invoices_verified"]) is not int
        or d["RETALLY_original_customer_invoices_verified"]!=0
        or type(d["RETALLY_recoveries_cents"]) is not int
        or d["RETALLY_recoveries_cents"]!=0
        or d["legal_status"]!="GAO_1976_ORIGINAL_BOL_ORIGIN_REBUTTED_AND_REPAYMENT_ONLY_CONDITIONAL"
        or type(d["historical_shipment_disputes"]) is not list
        or len(d["historical_shipment_disputes"])!=2):
        _fail("ORIGINAL_DECISION_CLASSIFICATION_CHANGED")
    x,y=d["historical_shipment_disputes"]
    if (type(x) is not dict or type(y) is not dict
        or set(x)!=set(["GBL","date","product","units","weight_lb","published_bill_of_lading_origin","agency_investigated_actual_origin","destination","original_freight_payment_cents","gsa_applied_setoff_cents","GAO_conclusion","payment_back_to_carrier_proven","independent_original_BOL_or_carrier_PRO_scan_examined","carrier_original_PRO_mentioned","documentation_evidence","originally_typed_destination_and_origin_are_verified_same_document"])
        or set(y)!=set(["GBL","date","product","units","weight_lb","published_bill_of_lading_origin","agency_investigated_actual_origin","destination","original_freight_payment_cents","gsa_applied_setoff_cents","GAO_conclusion","settlement_certificate_issued_cents","settlement_certificate_paid_back_to_carrier_verified"])
        or x.get("GBL")!="F-7349731"
        or x.get("date")!="1972-12-21"
        or x.get("product")!="40 arm chairs"
        or type(x.get("units")) is not int or x["units"]!=40
        or type(x.get("weight_lb")) is not int or x["weight_lb"]!=2800
        or x.get("published_bill_of_lading_origin")!="Washington, D.C."
        or x.get("agency_investigated_actual_origin")!="Canton, Mississippi"
        or x.get("destination")!="Veterans Administration Hospital, Brooklyn, New York"
        or type(x.get("original_freight_payment_cents")) is not int
        or x["original_freight_payment_cents"]!=39816
        or type(x.get("gsa_applied_setoff_cents")) is not int
        or x["gsa_applied_setoff_cents"]!=13328
        or x.get("GAO_conclusion")!="ORIGIN_PRESUMPTION_REBUTTED_ALLOW_CARRIER_CLAIM_IF_OTHERWISE_CORRECT"
        or x.get("payment_back_to_carrier_proven") is not False
        or x.get("independent_original_BOL_or_carrier_PRO_scan_examined") is not False
        or x.get("carrier_original_PRO_mentioned")!="75741955"
        or x.get("originally_typed_destination_and_origin_are_verified_same_document") is not False
        or type(x.get("documentation_evidence")) is not list
        or len(x["documentation_evidence"])!=3
        or any(type(t) is not str for t in x["documentation_evidence"])):
        _fail("WRONG_WAYBILL_ORIGIN_OR_OFFSET_FACTS")
    if (y.get("GBL")!="D-8271398" or y.get("date")!="1972-06-23"
        or y.get("product")!="blankets NOI" or y.get("units") is not None
        or type(y.get("weight_lb")) is not int or y["weight_lb"]!=1624
        or y.get("published_bill_of_lading_origin")!="Clearfield, Utah"
        or y.get("agency_investigated_actual_origin")!="NOT_REINVESTIGATED_IN_THIS_DECISION"
        or y.get("destination")!="Gallup, New Mexico"
        or y.get("original_freight_payment_cents") is not None
        or type(y.get("gsa_applied_setoff_cents")) is not int
        or y["gsa_applied_setoff_cents"]!=5765
        or y.get("GAO_conclusion")!="GSA_ISSUED_SETTLEMENT_CERTIFICATE_FOR_22_90"
        or type(y.get("settlement_certificate_issued_cents")) is not int
        or y["settlement_certificate_issued_cents"]!=2290
        or y.get("settlement_certificate_paid_back_to_carrier_verified") is not False):
        _fail("SEPARATE_1972_SHIPMENT_FACTS_CHANGED")
    if x["original_freight_payment_cents"]<=x["gsa_applied_setoff_cents"]:
        _fail("INVALID_HISTORICAL_PAID_AMOUNT")
    return {
        "source":"ORIGINAL_GAO_B_186603_1976_NOT_CUSTOMER_INVOICES",
        "original_decisions":1,
        "distinct_GBLs_in_decision":2,
        "carrier_government_payment_for_chairs_cents":39816,
        "government_applied_offset_based_on_incorrect_origin_cents":13328,
        "documented_BOL_origin":"Washington, D.C.",
        "GAO_established_actual_origin":"Canton, Mississippi",
        "GAO_rebutted_BOL_presumption_with_independent_shipment_evidence":True,
        "GAO_conditional_carrier_reimbursement_claim_cents":13328,
        "carrier_repayment_proven_cents":None,
        "separate_blanket_GBL_applied_setoff_cents":5765,
        "separate_blanket_settlement_certificate_issued_cents":2290,
        "separate_blanket_settlement_certificate_paid_verified":False,
        "cannot_add_amounts_from_separate_shipments_as_one_recovery":True,
        "original_BOL_scan_or_carrier_PRO_full_bytes_independently_verified":False,
        "shipper_origin_may_differ_from_order_office_or_BOL_text":True,
        "not_proof_of_current_rate_or_private_right_of_setoff":True,
        "retally_customer_invoices_examined":0,
        "retally_verified_recovered_cents":0,
        "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(verified_original_gao_origin_decision(),sort_keys=True,indent=2))
