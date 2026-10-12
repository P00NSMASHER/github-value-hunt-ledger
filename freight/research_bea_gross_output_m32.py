"""RETALLY Research Lab 14 / Mission 32: BEA real gross-output Table 16.

BEA real gross output is conceptually a different quantity from BLS real
sectoral output, GDP/value added, physical tonnage and any freight-billing
audit measure. This source is a BEA-ORIGIN series REDISTRIBUTED by DBnomics,
not an original BEA API/file authenticated by the CI runner.

No actual customer invoices, overcharges, refunds, demand or recoverable
market amounts are inferred from industry economic statistics.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash
from freight.research_bls_sectoral_output_m31 import (
    report_shell as m31_output,
    OFFLINE as M31_OFFLINE,
)
from freight.research_bea_measurement_gate import (
    report_shell as m30_measure,
    OFFLINE as M30_OFFLINE,
)
from freight.research_unified_blspci import (
    report_shell as m29_ppi,
    OFFLINE as M29_OFFLINE,
)

BOOK=Path(__file__).parent/"research/BEA_GROSS_OUTPUT_M32_20261012.json"
BOOK_SHA1="d19779679bfa793876dc2464a75e4b0f85fd2235"
SOURCE_URL="https://api.db.nomics.world/v22/series/BEA/GDPbyIndustry-16/484-A?observations=1"
PRIMARY_GUIDE="https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables"
PRIMARY_RELEASE="https://www.bea.gov/data/industries/gross-output-by-industry"
BEA_DATASET="GDPbyIndustry-16"
SOURCE_CODE="484-A"
YEARS=tuple(range(2017,2025))
MIN_DATE=date(2026,10,12)
SCOPE="LAB14_M32_BEA_TABLE16_484_REAL_GROSS_OUTPUT_SECONDARY_REPRODUCED_NOT_DIRECT_BEA"
BOOK_SCOPE="LAB14_M32_BEA_TABLE16_REAL_GROSS_OUTPUT_NAICS484_SECONDARY_NOT_PRIMARY_BEACHANGED"
OFFLINE="M32_OFFLINE_PINNED_BEAE_TABLE16_SECONDARY_SNAPSHOT_NOT_REFETCHED"
SECONDARY_VERIFIED="M32_BEA_ORIGIN_TABLE16_DB_NOMICS_DISTRIBUTOR_8_YEARS_REPRODUCED_NOT_BEAPRIMARY"
BLOCKED="M32_DBNOMICS_SECONDARY_SOURCE_UNAVAILABLE_DIRECT_BEA_ORIGINAL_STILL_UNVERIFIED"
MAX_BYTES=220_000
EXPECTED={
    2017:Decimal("100.000"),2018:Decimal("102.952"),
    2019:Decimal("102.398"),2020:Decimal("103.678"),
    2021:Decimal("109.538"),2022:Decimal("108.519"),
    2023:Decimal("107.307"),2024:Decimal("108.047"),
}
FALSE_FLAGS=(
    "bea_primary_original_484_numeric_source_authenticated",
    "source_distributor_document_completeness_independent_of_primary",
    "original_bea_real_gross_output_2017_2024_verified_without_redistributor",
    "redistributor_statistics_equivalent_to_source_contractually_guaranteed",
    "industry_data_are_customer_freight_invoices",
    "chain_type_index_is_total_nominal_carrier_revenue",
    "bea_gross_output_same_as_bea_gdp_value_added",
    "bea_real_gross_output_equals_bls_sectoral_output",
    "percent_change_discrepancy_equals_independent_model_error",
    "bea_gross_output_growth_exactly_estimating_ltl_484122",
    "real_gross_output_implies_freight_bill_overcharges",
    "three_series_are_independent_causal_estimates",
    "statistical_confidence_interval_verified",
    "public_client_recovery_claims_authorized",
    "real_customer_demand_established","new_lab_created",
    "scheduled_tasks_modified","pilot_18_independent_approvals_satisfied",
    "customer_or_carrier_private_data_accessed",
)
NULL_GUARDS=(
    "bea_primary_gross_output_series_original_bytes_sha256",
    "actual_retally_refund_cash_usd",
    "recoverable_freight_audit_market_tam_usd",
)
ZERO_GUARDS=(
    "actual_paid_customer_invoices_observed",
    "actual_independently_adjudicated_overcharges",
)


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _book()->dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_SHA1:
        raise ValueError("M32_SOURCE_BOOK_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _index_decimal(value:object)->Decimal:
    # The original secondary API JSON encodes numeric observations as finite
    # JSON int/float, never strings such as a client invoice or suppressed code.
    if type(value) not in (int,float,Decimal,str):
        raise ValueError("M32_BEAE_TABLE16_INDEX_NOT_NUMERIC")
    raw=str(value)
    if not re.fullmatch(r"\d{1,4}(?:\.\d{1,3})?",raw):
        raise ValueError("M32_BEAE_TABLE16_INDEX_NOT_FINITE_THREE_DECIMAL_VALUE")
    try: d=Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("M32_BEAE_TABLE16_INDEX_NON_DECIMAL") from exc
    if not d.is_finite() or d<=0 or d>=1000:
        raise ValueError("M32_BEAE_TABLE16_INDEX_OUTSIDE_VALID_BOUNDS")
    return d


def validate_book(book:object,*,as_of:date)->list[str]:
    try:
        if type(book) is not dict or book!=_book():
            return ["M32_PINNED_SOURCE_METADATA_CHANGED_OR_PRIVATE_FIELDS_ADDED"]
        errors=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            errors.append("M32_EVIDENCE_OBSERVED_AFTER_REQUESTED_DATE")
        originals={
            "schema_version":1,"scope":BOOK_SCOPE,
            "observed_on":"2026-10-12",
            "original_statistical_publisher":"U.S. Bureau of Economic Analysis",
            "redistributor":"DBnomics (CEPREMAP)",
            "primary_bea_methodology_url":PRIMARY_GUIDE,
            "primary_bea_gross_output_release_url":PRIMARY_RELEASE,
            "bea_release_date":"2026-09-30",
            "bea_source_table_number":16,
            "bea_original_table_name":"Chain-Type Quantity Indexes for Gross Output by Industry",
            "redistributor_api_url":SOURCE_URL,
            "redistributor_series_url":"https://db.nomics.world/BEA/GDPbyIndustry-16/484-A",
            "redistributor_dataset_id":"BEA/GDPbyIndustry-16",
            "redistributor_dataset_indexed_at":"2026-10-01T01:31:34.369Z",
            "bea_primary_data_api_current_access_state":
                "USERID_NOT_ACTIVE_OR_KEY_REQUIRED_OR_BEAI_TABLE_EXPORT_NOT_FETCHED",
            "bea_primary_original_484_numeric_source_authenticated":False,
            "source_record_series_code":SOURCE_CODE,
            "naics":"484","industry":"Truck transportation",
            "expected_period":"ANNUAL_YEAR_2017_BASE_100",
            "annual_years":list(YEARS),
            "gross_output_2017_2024_change_pct":"8.05",
            "m31_bls_real_sectoral_output_2017_2024_pct":"4.02",
            "m29_census_ppi_proxy_2017_2024_pct":"1.18",
            "bea_minus_bls_change_percentage_points":"4.03",
            "bea_minus_ppi_proxy_percentage_points":"6.87",
        }
        for k,v in originals.items():
            if type(book.get(k))!=type(v) or book.get(k)!=v:
                errors.append("M32_BEA_TABLE16_SOURCE_IDENTITY_OR_UNITS_CHANGED:"+k)
        if book.get("redistributor_requires_200_AND_ONE_EXACT_ANNUAL_SERIES") is not True:
            errors.append("M32_DIST_SOURCE_COMPLETENESS_VETO_REMOVED")
        for k in FALSE_FLAGS:
            if book.get(k) is not False:
                errors.append("M32_UNAUTHORIZED_PRIMARY_SOURCE_OR_COMMERCIAL_PROMOTION:"+k)
        for k in NULL_GUARDS:
            if book.get(k) is not None:
                errors.append("M32_FABRICATED_PRIMARY_SOURCE_OR_RECOVERY_AMOUNT:"+k)
        for k in ZERO_GUARDS:
            if type(book.get(k)) is not int or book.get(k)!=0:
                errors.append("M32_FABRICATED_PRIVATE_CARRIER_INVOICE_EVIDENCE:"+k)
        values=book.get("published_annual_index")
        if type(values) is not dict or set(values)!={str(y) for y in YEARS}:
            errors.append("M32_REQUIRED_EIGHT_ANNUAL_BEA_SOURCE_VALUES_MISSING")
        else:
            for yr in YEARS:
                if _index_decimal(values[str(yr)])!=EXPECTED[yr]:
                    errors.append("M32_BEA_TABLE16_VALUE_DRIFT:"+str(yr))
        desc=book.get("source_caveat")
        if type(desc) is not str or len(desc)<750 or "18 independent" not in desc:
            errors.append("M32_PUBLISHER_AND_REAL_INVOICE_CAVEATS_MISSING")
        return errors
    except (KeyError,TypeError,AttributeError,ValueError,OverflowError):
        return ["M32_SOURCE_BOOK_MALFORMED_OR_UNTRUSTED"]


def inspect_redistributor_json(source:object,*,book:dict)->dict:
    """Authenticate a secondary BEA-series *redistribution*, not BEA original.

    Completely disallows GDP value-added, quarterly observations, wrong
    NAICS, stale pre-Sep2026 BEA vintage, extra/missing years, and data drift.
    """
    if type(source) is not dict:
        raise ValueError("M32_EXPECTED_SECONDARY_JSON_RESPONSE")
    if source.get("errors") not in (None,[],{}):
        raise ValueError("M32_DBNOMICS_PUBLICATION_ERROR")
    dataset=source.get("dataset")
    provider=source.get("provider")
    series=source.get("series")
    if type(dataset) is not dict or type(provider) is not dict or type(series) is not dict:
        raise ValueError("M32_SOURCE_PROVIDER_DATASET_OR_SERIES_MISSING")
    if (dataset.get("code")!=BEA_DATASET or
        dataset.get("name")!="Chain-Type Quantity Indexes for Gross Output by Industry" or
        dataset.get("provider_code")!="BEA" or
        provider.get("code")!="BEA" or
        provider.get("name")!="U.S. Bureau of Economic Analysis"):
        raise ValueError("M32_BEA_GROSS_OUTPUT_TABLE16_MEASURE_IDENTITY_INCORRECT")
    # Reindexed data must have been retrieved on or after the first documented
    # 2026 annual revision. Source later updates require exact value re-review.
    indexed=dataset.get("indexed_at")
    if type(indexed) is not str or not indexed.endswith("Z") or indexed < "2026-10-01":
        raise ValueError("M32_BEA_DATASET_PRIOR_TO_SEPTEMBER_2026_REVISION")
    if series.get("num_found")!=1 or type(series.get("docs")) is not list or len(series["docs"])!=1:
        raise ValueError("M32_REQUIRE_EXACTLY_ONE_BEA_484_ANNUAL_SOURCE_SERIES")
    doc=series["docs"][0]
    if type(doc) is not dict or (
        doc.get("series_code")!=SOURCE_CODE or
        doc.get("dataset_code")!=BEA_DATASET or
        doc.get("provider_code")!="BEA" or
        doc.get("dataset_name")!="Chain-Type Quantity Indexes for Gross Output by Industry" or
        doc.get("dimensions")!={"industry":"484","FREQ":"A"} or
        doc.get("series_name")!="Truck transportation – Annually"
    ):
        raise ValueError("M32_BEA_SOURCE_NAICS_FREQUENCY_OR_VALUE_ADDED_SUBSTITUTION")
    periods=doc.get("period")
    values=doc.get("value")
    if type(periods) is not list or type(values) is not list or len(periods)!=len(values):
        raise ValueError("M32_ANNUAL_PERIOD_AND_VALUE_SOURCE_LENGTH_MISMATCH")
    found={}
    for period,val in zip(periods,values):
        if type(period) is not str or not re.fullmatch(r"(?:19|20)\d{2}",period):
            raise ValueError("M32_NONANNUAL_PERIOD_IN_GROSS_OUTPUT_QUANTITY_INDEX")
        yi=int(period)
        if yi not in YEARS:continue
        if yi in found:
            raise ValueError("M32_DUPLICATE_BEAE_SOURCE_REFERENCE_YEAR")
        v=_index_decimal(val)
        if v!=EXPECTED[yi]:
            raise ValueError("M32_BEA_TABLE16_PUBLISHED_YEAR_INDEX_DRIFT_REVIEW:"+str(yi))
        found[yi]=v
    if set(found)!=set(YEARS):
        raise ValueError("M32_INCOMPLETE_BEA_GROSS_OUTPUT_2017_2024_YEAR_SERIES")
    if found[2017]!=100:
        raise ValueError("M32_BEA_INDEX_BASE_2017_MUST_EQUAL_100")
    return {
        "source_type":"BEA_ORIGIN_DBNOMICS_THIRD_PARTY_REDISTRIBUTED",
        "original_bea_response_verified":False,
        "distributor_api_document_verified":True,
        "dataset":BEA_DATASET,"series_code":SOURCE_CODE,
        "dataset_indexed_at":indexed,
        "source_values":{str(y):str(found[y].quantize(Decimal("0.001"))) for y in YEARS},
        "annual_observations":8,
    }


def _percent(x:Decimal)->str:
    return str(x.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def _baseline(as_of:date)->tuple[dict,dict,dict,dict]:
    book=_book()
    faults=validate_book(book,as_of=as_of)
    if faults:
        raise ValueError("M32_FROZEN_BEA_TABLE16_CATALOG_INVALID: "+";".join(faults))
    prev31=m31_output(as_of=as_of)
    prev30=m30_measure(as_of=as_of)
    prev29=m29_ppi(as_of=as_of)
    if (prev31["status"]!="M31_OFFLINE_PRIOR_BLS_IP_SOURCE_OBSERVATION_NOT_FRESH_REPLAY"
        or prev31["aggregate_naics484_real_sectoral_output_2017_2024_pct"]!="4.02"
        or prev31["gross_output_original_bea_naics484_source_still_unverified"] is not True
        or prev30["bea_gross_output_original_source_status"]!="HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED"
        or prev30["bea_484_real_gross_output_2017_2024_available_for_validation"] is not False
        or prev29["status"]!="M29_OFFLINE_PRIOR_BLS_SOURCE_OBSERVATIONS_NO_FRESH_THREE_SERIES_REPLAY"
        or prev29["actual_paid_customer_freight_invoices_observed"]!=0
        or prev29["freight_recovery_market_tam_usd"] is not None
    ):
        raise ValueError("M32_PRIOR_ECONOMIC_OR_CUSTOMER_PILOT_EVIDENCE_DRIFT")
    return book,prev31,prev30,prev29


def report_shell(*,as_of:date)->dict:
    book,b31,b30,b29=_baseline(as_of)
    published={y:_index_decimal(book["published_annual_index"][str(y)]) for y in YEARS}
    bea=_percent((published[2024]/published[2017]-1)*100)
    bls=b31["aggregate_naics484_real_sectoral_output_2017_2024_pct"]
    ppi=next(x for x in b29["industry_comparisons"] if x["naics"]=="484")[
        "2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"
    ]
    gap_sectoral=_percent(Decimal(bea)-Decimal(bls))
    gap_ppi=_percent(Decimal(bea)-Decimal(ppi))
    if (bea!="8.05" or bls!="4.02" or ppi!="1.18"
        or gap_sectoral!="4.03" or gap_ppi!="6.87"):
        raise ValueError("M32_THREE_OUTPUT_MEASURES_SOURCE_COMPARISON_INCONSISTENT")
    r={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),"lab":14,
        "new_lab_created":False,"status":OFFLINE,
        "original_statistical_publisher":"U.S. Bureau of Economic Analysis",
        "redistributor":"DBnomics (CEPREMAP)",
        "economic_measure":"BEA_CHAIN_TYPE_QUANTITY_INDEX_FOR_GROSS_OUTPUT_BY_INDUSTRY",
        "bea_source_table":"GDPbyIndustry-16","bea_source_series":"484-A",
        "industry":"Truck transportation","naics":"484",
        "bea_current_release_vintage":"2026-09-30",
        "redistributor_ingestion_at":"2026-10-01T01:31:34.369Z",
        "new_secondary_source_http_replayed_in_this_run":False,
        "new_secondary_api_observations_authenticated_in_this_run":0,
        "new_secondary_source_http_raw_sha256":None,
        "direct_original_bea_table16_numeric_source_bytes_authenticated":False,
        "original_bea_publisher_source_verification_hold":True,
        "bea_2017_2024_year_index":[
            {"year":yr,"chain_type_real_gross_output_index":str(published[yr].quantize(Decimal("0.001")))}
            for yr in YEARS
        ],
        "bea_real_gross_output_2017_2024_change_pct":bea,
        "bls_real_sectoral_output_2017_2024_change_pct":bls,
        "m29_illustrative_revenue_ppi_proxy_2017_2024_change_pct":ppi,
        "bea_minus_bls_output_descriptive_gap_pp":gap_sectoral,
        "bea_minus_m29_ppi_proxy_descriptive_gap_pp":gap_ppi,
        "source_grade":"BEA_ORIGIN_DBNOMICS_SECONDARY_SNAPSHOT",
        "real_gross_output_gdp_value_added_sectoral_output_and_ppi_proxy_are_distinct":True,
        "naics_484_contains_both_long_distance_tl_and_ltl":True,
        "series_are_not_additive_or_independent_real_customer_markets":True,
        "discrepancies_are_not_independently_validated_model_errors":True,
        "primary_bea_original_source_still_blocked_from_prior_m30_31":True,
        "older_bea_value_added_vintage_is_not_a_gross_output_proxy":True,
        "frozen_secondary_source_policy_receipt_sha256":canon_hash(book),
        "m29_ppi_source_receipt_sha256":b29["receipt_sha256"],
        "m30_bea_gross_output_source_hold_receipt_sha256":b30["receipt_sha256"],
        "m31_bls_sectoral_output_source_receipt_sha256":b31["receipt_sha256"],
        "paid_customer_freight_invoices_observed":0,
        "independent_customer_carrier_overcharges_found":0,
        "eligible_refund_cash_proven_usd":None,
        "actual_retally_refunds_collected_usd":None,
        "freight_recovery_tam_usd":None,
        "real_buyer_demand_verified":False,
        "external_claims_or_customer_carrier_contact_authorized":False,
        "private_customer_data_processed":False,
        "human_pilot_18_independent_requirements_unmet":True,
        "scheduled_tasks_created_or_modified":False,
        "caveat":(
            "BEA GDP-by-Industry Table 16 is the chain-type quantity index "
            "for real GROSS OUTPUT, a different economic measure from "
            "GDP/value added, BLS sectoral output and Census-revenue/PPI "
            "annual averages. This 2017–2024 NAICS 484 industry series was "
            "retrieved from an official BEA-origin dataset as REDISTRIBUTED "
            "by DBnomics, and DBnomics publisher HTTP can be verified with "
            "SHA and exact semantic value checks. A direct authenticated "
            "original BEA API or original BEA data file was NOT retrieved, "
            "so describing this as direct primary BEA data authentication "
            "is prohibited. The reported 8.05% real gross-output growth "
            "and 4.02% BLS real sectoral output growth, versus a 1.18% "
            "illustrative Census nominal employer revenue/PPI adjustment, "
            "are descriptive differences, not controlled causal effects, "
            "statistical model errors, freight volumes, customer paid invoices "
            "or potentially recoverable refunds. NAICS 484 parent already "
            "includes the TL and LTL child sectors. No pilot authorizations "
            "or real customer billing proofs are satisfied."
        ),
    }
    r["receipt_sha256"]=canon_hash(r)
    return r


def verify_secondary(*,as_of:date,source:dict,raw_sha256:str)->dict:
    if type(raw_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}",raw_sha256):
        raise ValueError("M32_SECONDARY_HTTP_BODY_SHA256_INVALID")
    book,_,_,_=_baseline(as_of)
    receipt=inspect_redistributor_json(source,book=book)
    report=report_shell(as_of=as_of)
    report.update({
        "status":SECONDARY_VERIFIED,
        "new_secondary_source_http_replayed_in_this_run":True,
        "new_secondary_api_observations_authenticated_in_this_run":receipt["annual_observations"],
        "new_secondary_source_http_raw_sha256":raw_sha256,
        "source_grade":"BEA_ORIGIN_DB_NOMICS_THIRD_PARTY_REPLAYED_NOT_BEAPRIMARY",
        "new_secondary_semantic_receipt_sha256":canon_hash(receipt),
        "redistributor_ingestion_at":receipt["dataset_indexed_at"],
    })
    report["receipt_sha256"]=canon_hash({k:v for k,v in report.items() if k!="receipt_sha256"})
    return report


def blocked(*,as_of:date)->dict:
    r=report_shell(as_of=as_of)
    r["status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def fetch_dbnomics()->tuple[dict,str]:
    req=Request(SOURCE_URL,headers={"User-Agent":"RETALLY-Lab14-DBnomics-Secondhand-BEA-GrossOutput/1.0"})
    with urlopen(req,timeout=22) as resp:
        if resp.geturl()!=SOURCE_URL:
            raise ValueError("M32_SECONDARY_REDIRECT_OUTSIDE_ALLOWLISTED_SOURCE")
        raw=resp.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise ValueError("M32_SECONDARY_API_RESPONSE_EXCEEDS_BYTE_BOUND")
    return json.loads(raw.decode("utf-8")),sha256(raw).hexdigest()


def render_html(report:dict)->str:
    rows="".join(
        "<tr><td>"+str(x["year"])+"</td><td>"+escape(x["chain_type_real_gross_output_index"])+"</td></tr>"
        for x in report["bea_2017_2024_year_index"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | BEA gross output Table 16 source-grade evidence</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f6f9f7;color:#1b362b;'
        'margin:0}main{max-width:1080px;margin:35px auto;padding:18px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{padding:10px;border-bottom:1px solid #e0e6e1;text-align:left}'
        'small{color:#587061}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 32 / INTERNAL RESEARCH</small>'
        '<h1>BEA real gross output, trucking 484 — exact source and measurement grade</h1>'
        '<p>Current source status: <strong>'+escape(report["status"])+
        '</strong>. Data are BEA-origin Table 16 redistributed by DBnomics, '
        '<strong>NOT a directly authenticated original BEA numeric file</strong>.</p>'
        '<p>2017–2024 BEA real gross output: <strong>'+
        escape(report["bea_real_gross_output_2017_2024_change_pct"])+
        '%</strong>; BLS real sectoral output: <strong>'+
        escape(report["bls_real_sectoral_output_2017_2024_change_pct"])+
        '%</strong>; illustrative Census/BLS annual PPI revenue proxy: <strong>'+
        escape(report["m29_illustrative_revenue_ppi_proxy_2017_2024_change_pct"])+
        '%</strong>. Not interchangeable or additive measures.</p>'
        '<table><thead><tr><th>Year</th><th>BEA Table16 real gross output index '
        '(2017=100)</th></tr></thead><tbody>'+rows+'</tbody></table>'
        '<p>'+escape(report["caveat"])+'</p>'
        '<p><a href="'+SOURCE_URL+'">BEA Table 16 via DBnomics</a> · '
        '<a href="'+PRIMARY_GUIDE+'">Official BEA measurement definitions</a></p>'
        '</main></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Source-graded BEA real gross output, not customer audits")
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--as-of-date",default=date.today().isoformat())
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-secondary",action="store_true")
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_secondary:
        try:
            source,hash_=fetch_dbnomics()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_secondary(as_of=as_of,source=source,raw_sha256=hash_)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"bea_gross_output.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"bea_gross_output.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "status":report["status"],
        "secondary_api_years_reproduced":report["new_secondary_api_observations_authenticated_in_this_run"],
        "direct_bea_original_numeric_source_authenticated":False,
        "real_client_invoice_or_recovery_evidence":False,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
