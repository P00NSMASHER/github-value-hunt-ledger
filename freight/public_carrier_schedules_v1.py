"""RETALLY Lab 14: dated PUBLIC carrier fuel-surcharge reference facts.

Facts reproduced from official FedEx Freight, UPS and Union Pacific sites.
Neither publicly advertised schedules nor EIA pump-price indices substitute
for an actual customer's signed terms, tariff applicability or invoice proof.
Research only: no carrier outreach, payments or automated rating.
"""
from __future__ import annotations

import csv
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation
from pathlib import Path
import re

from freight.public_faf6_eia_v1 import read_eia_rows

HERE=Path(__file__).resolve().parent
CSV=HERE/"fixtures/public_carrier_fuel_schedule_20261017.csv"
COLUMNS=("carrier_service","effective_start","surcharge_percent",
         "referenced_eia_us_week","referenced_eia_us_usd_per_gallon","official_source")
CARRIER_URLS={
 "FEDEX_FREIGHT_LTL":{
  "https://www.fedexfreight.com/fragments/fuel-surcharge-table",
  "https://www.fedexfreight.com/en-us/support-resources/tariffs-rates-information/fuel-surcharges"},
 "UPS_DOMESTIC_GROUND":{
  "https://www.ups.com/us/en/support/shipping-support/shipping-costs-rates/fuel-surcharges"},
 "UNION_PACIFIC_DOMESTIC_INTERMODAL":{
  "https://www.up.com/announcements/intermodal/2026/PR2026-66"},
}
FROZEN_RATES={
 ("FEDEX_FREIGHT_LTL","2026-09-09"):"55.4",
 ("FEDEX_FREIGHT_LTL","2026-09-16"):"58.6",
 ("FEDEX_FREIGHT_LTL","2026-09-23"):"61.0",
 ("FEDEX_FREIGHT_LTL","2026-09-30"):"59.6",
 ("FEDEX_FREIGHT_LTL","2026-10-07"):"57.7",
 ("FEDEX_FREIGHT_LTL","2026-10-14"):"57.50",
 ("UPS_DOMESTIC_GROUND","2026-09-07"):"27.50",
 ("UPS_DOMESTIC_GROUND","2026-09-14"):"28.50",
 ("UPS_DOMESTIC_GROUND","2026-09-21"):"29.50",
 ("UPS_DOMESTIC_GROUND","2026-09-28"):"30.25",
 ("UNION_PACIFIC_DOMESTIC_INTERMODAL","2026-10-12"):"58.0",
}
RETAIL_INDEX=re.compile(r"^\d+\.\d{3}$")
PERCENT=re.compile(r"^\d{1,3}\.\d{1,2}$")


def _fail(code: str) -> None:
    raise ValueError("CARRIER_PUBLIC_REFERENCE_"+code)


def read_carrier_rates() -> list[dict[str,str]]:
    if CSV.is_symlink() or not CSV.is_file() or CSV.stat().st_size>16_000:
        _fail("UNTRUSTED_FIXTURE_PATH")
    try:
        with CSV.open("r",encoding="utf-8-sig",newline="") as stream:
            reader=csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                _fail("UNREVIEWED_FIELD_ADDITION")
            rows=list(reader)
    except (UnicodeError,csv.Error) as e:
        raise ValueError("CARRIER_PUBLIC_REFERENCE_MALFORMED_SOURCE") from e
    if len(rows)!=len(FROZEN_RATES):
        _fail("MISSING_OR_EXTRA_SOURCE_ROWS")
    eia={(row["week_ending_monday"],row["area"]):row["usd_per_gallon"]
         for row in read_eia_rows()}
    seen=set()
    for row in rows:
        if set(row)!=set(COLUMNS) or any(type(v) is not str for v in row.values()):
            _fail("UNREVIEWED_FIELD_ADDITION")
        carrier,day=row["carrier_service"],row["effective_start"]
        key=(carrier,day)
        if key in seen or key not in FROZEN_RATES:
            _fail("DUPLICATE_OR_UNREVIEWED_EFFECTIVE_DATE")
        seen.add(key)
        if row["official_source"] not in CARRIER_URLS.get(carrier,()):
            _fail("UNVERIFIED_ORIGIN_AUTHORITY")
        if row["surcharge_percent"]!=FROZEN_RATES[key] or not PERCENT.fullmatch(row["surcharge_percent"]):
            _fail("PUBLISHED_PERCENT_MISMATCH")
        try:
            pct=Decimal(row["surcharge_percent"])
            d=date.fromisoformat(day)
        except (InvalidOperation,ValueError) as e:
            raise ValueError("CARRIER_PUBLIC_REFERENCE_INVALID_FIELD") from e
        if not pct.is_finite() or pct<0 or pct>100:
            _fail("IMPOSSIBLE_PERCENT")
        if carrier=="FEDEX_FREIGHT_LTL":
            if d.weekday()!=2:
                _fail("INAPPLICABLE_EFFECTIVE_DAY")
            index_week=row["referenced_eia_us_week"]
            try:
                index_date=date.fromisoformat(index_week)
            except ValueError as e:
                raise ValueError("CARRIER_PUBLIC_REFERENCE_INVALID_INDEX_DATE") from e
            if index_date!=d-timedelta(days=2) or index_date.weekday()!=0:
                _fail("WRONG_EIA_LAG")
            price=row["referenced_eia_us_usd_per_gallon"]
            if not RETAIL_INDEX.fullmatch(price) or eia.get((index_week,"US"))!=price:
                _fail("EIA_INDEX_ORIGINAL_SOURCE_MISMATCH")
        else:
            if d.weekday()!=0:
                _fail("INAPPLICABLE_EFFECTIVE_DAY")
            if row["referenced_eia_us_week"] or row["referenced_eia_us_usd_per_gallon"]:
                _fail("UNSUPPORTED_CARRIER_INDEX_PROVENANCE")
    if seen!=set(FROZEN_RATES):
        _fail("MISSING_EFFECTIVE_DATE")
    return rows


def public_schedule_report() -> dict:
    rows=read_carrier_rates()
    return {
        "scope":"RETALLY_LAB14_DATED_PUBLISHED_CARRIER_FACTS_ONLY",
        "carrier_source_families":3,
        "source_rows":len(rows),
        "fedex_freight_eia_weekly_pairs":len([r for r in rows if r["carrier_service"]=="FEDEX_FREIGHT_LTL"]),
        "ups_domestic_ground_observations":len([r for r in rows if r["carrier_service"]=="UPS_DOMESTIC_GROUND"]),
        "union_pacific_intermodal_announcements":len([r for r in rows if r["carrier_service"]=="UNION_PACIFIC_DOMESTIC_INTERMODAL"]),
        "last_observed_as_of":"2026-10-17",
        "customer_agreement_still_controls":True,
        "public_surcharge_is_not_billed_invoice_charge":True,
        "not_continuous_current_rates":True,
        "verified_customer_invoice_count":0,
        "verified_overcharge_cents":None,
        "financial_recovery_authorized":False,
        "commercial_claim_clearance":"NOT_ESTABLISHED",
    }


if __name__=="__main__":
    import json
    print(json.dumps(public_schedule_report(),indent=2,sort_keys=True))
