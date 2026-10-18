"""Real SEC-filed shipper/carrier rate exhibits: scoped historic contract math.

This software demonstrates why a generic EIA/FedEx/UPS fuel schedule
cannot substitute for an actual governing agreement. The 2005 and 2007
contracts are THIRD PARTY historical documents, not RETALLY clients.
All illustrated gallons, miles and fuel prices are invented test inputs,
not evidenced original shipments, prices paid, invoices or recoveries.

Only original explicitly published rate rows may be used. Out-of-table
prices, missing signed amendment/current terms, mismatched fuel authority,
changed parties, or attempts to apply the same scheme to another carrier
MUST fail closed. No network, credentials or external action.
"""
from __future__ import annotations

import json
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from pathlib import Path
import re

SOURCE=Path(__file__).resolve().parent/"fixtures/public_sec_2005_2007_original_carrier_rate_contracts.json"
SCOPE="RETALLY_LAB14_ORIGINAL_SEC_HISTORICAL_CONTRACT_EXHIBITS_ONLY"
NEDAK="NEDAK_WESTERN_2007"
SWIFT="SWIFT_LOAD_SOURCE_2005"
LOCAL_FUEL="LOCAL_NONAFFILIATED_NO2_DIESEL_RETAIL_O_NEILL_NE"
DOE_FUEL="DOE_NATIONAL_AVERAGE_DIESEL_MON_OR_FEDERAL_HOLIDAY_TUE"
NEDAK_TIERS={
 "2.499":"0","2.749":"0.0003","2.999":"0.0006",
 "3.249":"0.0009","3.499":"0.0012","3.749":"0.0015",
 "3.999":"0.0018"
}
SWIFT_TIERS=[
 ("1.200","1.249",0),("1.250","1.299",1),("1.300","1.349",2),
 ("1.350","1.399",3),("1.400","1.449",4),("1.450","1.499",5),
 ("1.500","1.549",6)
]
EXPECTED={
 NEDAK:{
  "effective":"2007-07-19","shipper":"NEDAK Ethanol LLC",
  "carrier":"Western Oil Trans Inc",
  "url":"https://www.sec.gov/Archives/edgar/data/1337226/000092290707000474/form8kexh101_072507.htm",
  "fuel":LOCAL_FUEL,
 },
 SWIFT:{
  "effective":"2005-02-28","shipper":"Swift & Company, Inc.",
  "carrier":"LOAD SOURCE LOGISTICS",
  "url":"https://www.sec.gov/Archives/edgar/data/757563/000129707705000148/mcagree.htm",
  "fuel":DOE_FUEL,
 }
}
TOP_KEYS=frozenset({"schema_version","as_of_date","purpose","source_class","customer_role","contracts","shared_controls","custody_notes"})
ALL_CONTROLS={
 "actual_RETALLY_customer_contracts":0,
 "actual_RETALLY_customer_invoices":0,
 "RETALLY_verified_overcharge_cents":None,
 "RETALLY_verified_recoveries_cents":0,
 "source_excerpts_do_not_prove_current_terms":True,
 "no_price_estimate_beyond_listed_index_tiers":True,
 "synthetic_calculations_only":True,
 "disagreement_requires_actual_signed_contract_tariff_and_original_invoice":True,
 "commercial_claim_clearance":"NO_GO"
}
NEDAK_FIELDS=frozenset({
 "key","document_url","exhibit","effective_date","shipper","carrier",
 "service","units","base_rate_usd_per_unloaded_gallon","fuel_index",
 "fuel_assessment","carrier_invoice_forms","contract_supersedes_conflicting_tariff",
 "published_fuel_table","off_table_fuel_prices_proven_by_this_excerpt",
 "current_operational_status_verified","actual_billed_shipment_invoice_seen",
 "original_EDGAR_document_binary_hashed",
})
SWIFT_FIELDS=frozenset({
 "key","document_url","exhibit","effective_date","shipper","carrier",
 "service","units","fuel_index","fuel_assessment","contract_rate_precedence",
 "carrier_must_include_fuel_as_separate_invoice_line",
 "no_automatic_add_fuel_by_shipper","selected_original_published_fuel_bands",
 "off_band_fuel_prices_proven_by_this_excerpt",
 "current_operational_status_verified","actual_invoice_and_lane_Appendices_seen",
 "original_EDGAR_document_binary_hashed","carrier_signature_independently_authenticated",
})

def _fail(reason:str)->None:
    raise ValueError("SEC_CONTRACT_SOURCE_"+reason)

def _dec(s:str,places:int=3)->Decimal:
    if type(s) is not str or not re.fullmatch(r"\d+\.\d{"+str(places)+r"}",s):
        _fail("FUEL_PRICE_PRECISION_OR_TYPE")
    try:
        x=Decimal(s)
    except InvalidOperation as exc:
        raise ValueError("SEC_CONTRACT_SOURCE_BAD_DECIMAL") from exc
    if not x.is_finite():_fail("NONFINITE_FUEL_PRICE")
    return x

def verified_source_exhibits()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>26000:
        _fail("INVALID_INPUT_PATH")
    try:
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError("SEC_CONTRACT_SOURCE_INVALID_JSON") from exc
    if (type(data) is not dict or frozenset(data)!=TOP_KEYS
        or type(data["schema_version"]) is not int or data["schema_version"]!=1
        or data["as_of_date"]!="2026-10-18"
        or data["purpose"]!="real_original_SEC_filed_historical_shipper_carrier_contract_rate_source_not_invoice"
        or data["source_class"]!="SEC_FILED_HISTORICAL_CONTRACT_OR_FORM_EXHIBITS"
        or data["customer_role"]!="EXTERNAL_TO_RETALLY"
        or type(data.get("custody_notes")) is not list
        or len(data["custody_notes"])!=4
        or not all(type(x) is str and len(x)>=60 for x in data["custody_notes"])
        or data["shared_controls"]!=ALL_CONTROLS
        or type(data["contracts"]) is not list or len(data["contracts"])!=2):
        _fail("INVALID_SOURCE_OR_FINANCIAL_CLAIM")
    contracts={}
    for x in data["contracts"]:
        if type(x) is not dict or x.get("key") not in EXPECTED:
            _fail("UNKNOWN_OR_DUPLICATED_AGREEMENT")
        key=x["key"]
        if key in contracts or frozenset(x)!=(NEDAK_FIELDS if key==NEDAK else SWIFT_FIELDS):
            _fail("UNKNOWN_OR_DUPLICATED_AGREEMENT")
        ref=EXPECTED[key]
        if (x["document_url"]!=ref["url"] or x["effective_date"]!=ref["effective"]
            or x["shipper"]!=ref["shipper"] or x["carrier"]!=ref["carrier"]
            or x["fuel_index"]!=ref["fuel"]):
            _fail("SHIPPERS_OR_AGREEMENT_OR_FUEL_AUTHORITY_CHANGED")
        if key==NEDAK:
            steps=x["published_fuel_table"]
            if (x["base_rate_usd_per_unloaded_gallon"]!="0.01299"
                or x["units"]!="USD per gallon of ethanol unloaded"
                or x["contract_supersedes_conflicting_tariff"] is not True
                or x["off_table_fuel_prices_proven_by_this_excerpt"] is not False
                or x["current_operational_status_verified"] is not False
                or x["actual_billed_shipment_invoice_seen"] is not False
                or x["original_EDGAR_document_binary_hashed"] is not False
                or x["carrier_invoice_forms"]!=["freight_bill","EDI_as_invoice"]
                or x["exhibit"]!="EX-10.1, Exhibit A Transportation Rate/Bulk Fuel Surcharge"
                or type(steps) is not list or len(steps)!=7):
                _fail("NEDAK_RATE_OR_SCOPE_CHANGED")
            seen={}
            for row in steps:
                if (type(row) is not dict or frozenset(row)!={"price_usd_per_gallon","surcharge_usd_per_unloaded_gallon"}
                    or type(row["price_usd_per_gallon"]) is not str or type(row["surcharge_usd_per_unloaded_gallon"]) is not str):
                    _fail("UNEXPECTED_NEDAK_PRICE_ROW")
                price=row["price_usd_per_gallon"]
                if price in seen:_fail("DUPLICATE_NEDAK_FUEL_TIER")
                seen[price]=row["surcharge_usd_per_unloaded_gallon"]
            if seen!=NEDAK_TIERS:_fail("NEDAK_FUEL_SOURCE_TIER_MISMATCH")
        else:
            bands=x["selected_original_published_fuel_bands"]
            if (x["units"]!="USD surcharge per loaded mile"
                or x["contract_rate_precedence"]!=["Appendix J","Appendix I","Appendix K"]
                or x["carrier_must_include_fuel_as_separate_invoice_line"] is not True
                or x["no_automatic_add_fuel_by_shipper"] is not True
                or x["off_band_fuel_prices_proven_by_this_excerpt"] is not False
                or x["current_operational_status_verified"] is not False
                or x["actual_invoice_and_lane_Appendices_seen"] is not False
                or x["original_EDGAR_document_binary_hashed"] is not False
                or x["carrier_signature_independently_authenticated"] is not False
                or x["exhibit"]!="EX-10.8 Motor Carrier Transportation Agreement, Appendix D Fuel Surcharge Policy"
                or type(bands) is not list or len(bands)!=len(SWIFT_TIERS)):
                _fail("SWIFT_RATE_OR_SCOPE_CHANGED")
            seen=[]
            for row in bands:
                if (type(row) is not dict or frozenset(row)!={"min_usd_per_gallon","max_usd_per_gallon","surcharge_cents_per_mile"} 
                    or type(row["surcharge_cents_per_mile"]) is not int):
                    _fail("SWIFT_RATE_ROW_INVALID")
                seen.append((row["min_usd_per_gallon"],row["max_usd_per_gallon"],row["surcharge_cents_per_mile"]))
            if seen!=SWIFT_TIERS:_fail("SWIFT_FUEL_SOURCE_TIER_MISMATCH")
        contracts[key]=x
    if set(contracts)!=set(EXPECTED):_fail("MISSING_AGREEMENT")
    return contracts

def synthetic_quote(*,agreement:str,fuel_index:str,fuel_price_usd:str,
                    gallons_unloaded:int|None=None,miles:int|None=None)->dict:
    """This is ONLY a hypothetical published-EXHIBIT arithmetic illustration.

    It never verifies a historical or current actual diesel quotation,
    shipment tender, amended contract, carrier invoice or overcharge.
    """
    contracts=verified_source_exhibits()
    if type(agreement) is not str or agreement not in contracts:
        _fail("UNSUPPORTED_CONTRACT")
    doc=contracts[agreement]
    if fuel_index!=doc["fuel_index"]:
        _fail("INCOMPATIBLE_FUEL_INDEX_OR_AUTHORITY")
    price=_dec(fuel_price_usd)
    if agreement==NEDAK:
        if type(gallons_unloaded) is not int or not 1<=gallons_unloaded<=100_000 or miles is not None:
            _fail("WRONG_QUANTITY_OR_UNITS")
        fuel=NEDAK_TIERS.get(fuel_price_usd)
        if fuel is None:_fail("PRICE_NOT_EXACTLY_SHOWN_IN_ORIGINAL_EXHIBIT")
        base=Decimal("0.01299")*Decimal(gallons_unloaded)
        surcharge=Decimal(fuel)*Decimal(gallons_unloaded)
        amount=(base+surcharge).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
        result={"agreement":agreement,"source_index":LOCAL_FUEL,"hypothetical_gallons_unloaded":gallons_unloaded,
            "hypothetical_diesel_price_usd":fuel_price_usd,
            "source_base_rate_usd_per_unloaded_gallon":"0.01299",
            "source_surcharge_per_unloaded_gallon_usd":fuel,
            "hypothetical_unamended_freight_charge_usd":str(amount)}
    else:
        if type(miles) is not int or not 1<=miles<=10_000 or gallons_unloaded is not None:
            _fail("WRONG_QUANTITY_OR_UNITS")
        matches=[n for low,high,n in SWIFT_TIERS if Decimal(low)<=price<=Decimal(high)]
        if len(matches)!=1:_fail("PRICE_OUTSIDE_EXPLICIT_SOURCE_BANDS")
        surcharge=Decimal(matches[0])*Decimal(miles)/Decimal(100)
        result={"agreement":agreement,"source_index":DOE_FUEL,
                "hypothetical_miles":miles,"hypothetical_index_price_usd":fuel_price_usd,
                "source_surcharge_cents_per_mile":matches[0],
                "hypothetical_FUEL_ONLY_charge_usd":str(surcharge.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),
                "full_freight_charge_status":"UNVERIFIED_MISSING_APPLICABLE_LANE_RATE_APPENDIX"}
    return {**result,
        "calculation_type":"SYNTHETIC_ARITHMETIC_NOT_A_REAL_SHIPMENT",
        "contract_current_operational_status":"UNVERIFIED",
        "historic_fuel_price_actually_observed":False,
        "full_customer_agreement_and_amendments_verified":False,
        "actual_invoice_compared":False,
        "RETALLY_overcharge_or_recovery_cents":None,
        "commercial_claim_clearance":"NO_GO"}

def report()->dict:
    docs=verified_source_exhibits()
    a=synthetic_quote(agreement=NEDAK,fuel_index=LOCAL_FUEL,
       fuel_price_usd="2.749",gallons_unloaded=1000)
    b=synthetic_quote(agreement=SWIFT,fuel_index=DOE_FUEL,
       fuel_price_usd="1.275",miles=150)
    if a["hypothetical_unamended_freight_charge_usd"]!="13.29" or b["hypothetical_FUEL_ONLY_charge_usd"]!="1.50":
        _fail("SYNTHETIC_SOURCE_ARITHMETIC_CHANGED")
    return {"scope":SCOPE,"independently_published_original_SEC_agreements":len(docs),
            "historical_governing_index_methods":{x:docs[x]["fuel_index"] for x in sorted(docs)},
            "NEDAK_2007_published_rate_rows":len(NEDAK_TIERS),
            "SWIFT_2005_selected_fuel_bands":len(SWIFT_TIERS),
            "NEDAK_illustration_not_actual_invoice":a,
            "SWIFT_illustration_not_actual_invoice":b,
            "wrong_contract_index_must_fail":True,
            "current_signed_amendments_and_invoices_unverified":True,
            "2026_EIA_prices_not_approved_for_2007_local_index":True,
            "actual_RETALLY_customer_invoices":0,
            "actual_RETALLY_overcharge_cents":None,
            "actual_RETALLY_recovery_cents":0,
            "commercial_claim_clearance":"NO_GO"}

if __name__=="__main__":
    print(json.dumps(report(),indent=2,sort_keys=True))
