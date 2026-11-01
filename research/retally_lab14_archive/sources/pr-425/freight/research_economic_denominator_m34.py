"""RETALLY Research Lab 14 / Mission 34: BEA versus Census denominator control.

Reconciles first-party BEA industry GROSS OUTPUT to original Census
EMPLOYER-INDUSTRY REVENUE for NAICS 484 2017–2024, plus first-party BLS
PPI and BEA gross-output PRICE indices. These conceptually different
nominal monetary totals are NOT counterparty invoices or separate markets.

Original publisher source replays are separately performed by M25 Census,
M29 BLS and M33 BEA. This module can verify their derived receipts in
the same CI job but must never invent the direct source access claim.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha1
from html import escape
import json
from pathlib import Path

from freight.research_evidence_gate import canon_hash
from freight.research_sas_aies_bridge import (
    report_shell as census_history,
    OFFLINE as CENSUS_OFFLINE,
    VERIFIED as CENSUS_VERIFIED,
    SOURCE_IDS as CENSUS_IDS,
)
from freight.research_bea_original_m33 import (
    report_shell as bea_original,
    OFFLINE as BEA_OFFLINE,
    VERIFIED as BEA_VERIFIED,
    BEA_ORIGINAL_SHA256,
)
from freight.research_unified_blspci import (
    report_shell as original_bls_prices,
    OFFLINE as BLS_OFFLINE,
    VERIFIED as BLS_VERIFIED,
)

BOOK=Path(__file__).parent/"research/TRUCKING_MEASURE_DENOMINATOR_M34_20261012.json"
BOOK_SHA1="1745511aaf5b95b9ad61824ae46f4596c705fdf0"
BOOK_SCOPE="LAB14_M34_CENSUS_EMPLOYER_REVENUE_VS_BEA_GROSS_OUTPUT_DENOMINATOR_GATE_NOT_FREIGHT_TAM"
SCOPE="LAB14_M34_FIRST_PARTY_TRUCKING_NOMINAL_MEASURE_RECONCILIATION_NOT_INVOICE_MARKET"
YEARS=tuple(range(2017,2025))
NAICS="484"
MIN_DATE=date(2026,10,12)
OFFLINE="M34_OFFLINE_PRIOR_VERIFIED_ORIGINAL_SOURCE_SNAPSHOTS_NO_NEW_THREE_SOURCE_REPLAY"
VERIFIED="M34_THREE_FIRST_PARTY_SOURCE_FAMILIES_FRESHLY_REPLAYED_BEA_CENSUS_BLS"
BLOCKED="M34_ONE_OR_MORE_FIRST_PARTY_SOURCE_FAMILIES_BLOCKED_NO_FULL_REPLAY"
BLS_ID="PCU484---484---"
BEA_GROSS_SHEET="TGO105-A"
BEA_PRICE_SHEET="TGO104-A"
FALSE_FLAGS=(
    "census_employer_revenue_is_complete_and_direct_subset_of_bea_gross_output_proven",
    "dollar_difference_is_missing_carrier_freight_invoices",
    "dollar_difference_is_customer_freight_bill_overcharges",
    "gross_output_and_employer_revenue_have_identical_coverage_and_weights_proven",
    "bea_price_index_and_bls_industry_net_output_ppi_are_interchangeable",
    "bea_gross_output_2017_2024_equals_freight_invoice_spending",
    "ratio_census_over_bea_is_verified_invoice_market_coverage",
    "census_revenue_can_be_added_to_bea_gross_output_without_double_counting",
    "naics484_parent_and_tl_ltl_children_can_be_summed",
    "economic_measure_mismatch_has_verified_causal_decomposition",
    "price_adjusted_revenue_proxy_is_official_real_gross_output",
    "numeric_gap_explains_freight_audit_error_rate",
    "industry_difference_is_serviceable_recovery_tam",
    "source_statistics_are_independent_customer_audit_sample",
    "external_commercial_claims_authorized",
    "private_customer_or_carrier_records_ingested",
    "all_18_real_customer_pilot_authorizations_satisfied",
    "new_lab_created","scheduled_tasks_modified",
)
PUBLISHER_SOURCES={
    "bea":("U.S. Bureau of Economic Analysis",
           "freight/research/BEA_ORIGINAL_ACCESS_M33_20261012.json",
           "501ec6d18cdc29b7ac6b7c718c1d85d5f520fafd"),
    "census":("U.S. Census Bureau",
              "freight/research/SAS_AIES_CARRIER_BRIDGE_2017_2024_20261012.json",
              "0df081d41cb519b142c1ccfcbaf9d14bd82af3d0"),
    "bls":("U.S. Bureau of Labor Statistics",
           "freight/research_unified_blspci.py",
           None),
}
EXPECTED_BEANOM=(
    "367154","401324","409425","413595",
    "490334","577292","546993","545435",
)
EXPECTED_CENSUS_ORIGINAL_SHA256={
    "revised_sas_2017_2022":"cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac",
    "linked_aies_2022_2024":"1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4",
    "aies_basic_2024":"39c4235026672e7bffdbc36292ed976726df368f2ca435219aef1c84e8e4faa6",
}
EXPECTED_CENSUS=(
    "290532.000","310688.000","314044.000","308131.000",
    "361243.000","423270.958","406651.010","402827.246",
)


def _blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _policy()->dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=BOOK_SHA1:
        raise ValueError("M34_DENOMINATOR_POLICY_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _d(value:object)->Decimal:
    if type(value) is not str:
        raise ValueError("M34_NOMINAL_MILLION_USD_WRONG_TYPE")
    try:
        amount=Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("M34_NON_DECIMAL_SOURCE_NOMINAL_DOLLARS") from exc
    if not amount.is_finite() or amount<=0 or amount>=Decimal("999999999"):
        raise ValueError("M34_NOMINAL_SOURCE_AMOUNT_NONPOSITIVE_OR_NOT_FINITE")
    return amount


def _f2(value:Decimal)->str:
    return str(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def _f3(value:Decimal)->str:
    return str(value.quantize(Decimal("0.001"),rounding=ROUND_HALF_UP))


def validate_policy(book:object,*,as_of:date)->list[str]:
    try:
        if type(book) is not dict or book!=_policy():
            return ["M34_FROZEN_SOURCE_BOOK_CHANGED_OR_EXTRA_FIELDS_ADDED"]
        failures=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            failures.append("M34_BEFORE_ORIGINAL_SOURCE_OBSERVATION_DATE")
        fixed={
            "schema_version":1,"scope":BOOK_SCOPE,
            "observed_on":"2026-10-12",
            "naics":NAICS,"industry":"Truck transportation",
            "geography":"United States","years":list(YEARS),
            "bea_gross_output_2017_2024_nominal_growth_pct":"48.56",
            "census_employer_revenue_2017_2024_nominal_growth_pct":"38.65",
            "bea_minus_census_growth_percentage_points":"9.91",
            "bea_gross_output_minus_census_nominal_2017_million_usd":"76622.000",
            "bea_gross_output_minus_census_nominal_2024_million_usd":"142607.754",
            "census_over_bea_nominal_ratio_2017_pct":"79.13",
            "census_over_bea_nominal_ratio_2024_pct":"73.85",
            "ratio_change_2024_minus_2017_percentage_points":"-5.28",
            "bea_gross_output_quantity_2017_2024_pct":"8.05",
            "bea_gross_output_price_index_2017_2024_pct":"37.49",
            "bls_parent_producer_price_2017_2024_pct":"37.04",
            "bea_vs_bls_price_index_change_percentage_points":"0.45",
            "m29_illustrative_census_ppi_real_revenue_proxy_2017_2024_pct":"1.18",
        }
        for key,value in fixed.items():
            if type(book.get(key))!=type(value) or book.get(key)!=value:
                failures.append("M34_NOMINAL_MEASURE_IDENTITY_UNITS_OR_PUBLISHED_FACTS_CHANGED:"+key)
        sources=book.get("sources")
        if type(sources) is not dict or set(sources)!=set(PUBLISHER_SOURCES):
            failures.append("M34_THREE_GOVERNMENT_PUBLISHER_LINEAGES_REQUIRED")
        else:
            for name,(pub,file,blob) in PUBLISHER_SOURCES.items():
                src=sources[name]
                if type(src) is not dict or src.get("publisher")!=pub:
                    failures.append("M34_ECONOMIC_PUBLISHER_WRONG:"+name)
                if blob is not None and (src.get("repository_source_book")!=file or
                                          src.get("repository_book_git_blob_sha1")!=blob):
                    failures.append("M34_ORIGINAL_SOURCE_CATALOG_ID_CHANGED:"+name)
        for key,want in (
            ("bea_gross_output_million_nominal_usd",EXPECTED_BEANOM),
            ("census_employer_revenue_million_nominal_usd",EXPECTED_CENSUS),
        ):
            actual=book.get(key)
            if type(actual) is not dict or set(actual)!={str(y) for y in YEARS} or (
                tuple(actual[str(y)] for y in YEARS)!=want
            ):
                failures.append("M34_EIGHT_SOURCE_YEARS_VALUES_OR_UNITS_CHANGED:"+key)
        for flag in FALSE_FLAGS:
            if book.get(flag) is not False:
                failures.append("M34_UNSUPPORTED_RECOVERY_OR_CAUSAL_MARKET_CLAIM:"+flag)
        for field,value in (
            ("real_paid_customer_invoices_observed",0),
            ("independent_actual_carrier_overcharges_detected",0),
            ("actual_cash_refunds_recovered_usd",None),
            ("recovery_market_tam_usd",None),
            ("real_freight_customers_or_buyers_contacted",0),
        ):
            if type(book.get(field))!=type(value) or book.get(field)!=value:
                failures.append("M34_FICTITIOUS_CUSTOMER_RECOVERY_EVIDENCE:"+field)
        if not (
            type(book.get("source_caveat")) is str and
            len(book["source_caveat"])>650 and
            "NOT" in book["source_caveat"] and
            "18 independent" in book["source_caveat"]
        ):
            failures.append("M34_MEASUREMENT_AND_REAL_CUSTOMER_EVIDENCE_CAVEATS_MISSING")
        return failures
    except (ValueError,TypeError,AttributeError,KeyError):
        return ["M34_UNTRUSTED_DENOMINATOR_SOURCE_REGISTRY"]


def nominal_comparison(bea:dict[int,Decimal],census:dict[int,Decimal])->list[dict]:
    """Pure nominal discrepancy arithmetic: NOT causal or a subset relation."""
    if (type(bea) is not dict or type(census) is not dict
        or set(bea)!=set(YEARS) or set(census)!=set(YEARS)):
        raise ValueError("M34_EXACTLY_EIGHT_NATIONAL_NAICS484_YEARS_REQUIRED")
    series=[]
    for year in YEARS:
        b,c=bea[year],census[year]
        if (type(b) is not Decimal or type(c) is not Decimal or
            not b.is_finite() or not c.is_finite() or b<=0 or c<=0):
            raise ValueError("M34_NATIONAL_NOMINAL_VALUE_NON_DECIMAL_OR_INVALID")
        series.append({
            "year":year,
            "bea_nominal_gross_output_million_usd":_f3(b),
            "census_employer_industry_revenue_million_usd":_f3(c),
            "bea_minus_census_nominal_difference_million_usd":_f3(b-c),
            "census_divided_by_bea_nominal_measure_ratio_pct":_f2(c/b*100),
            "ratio_is_share_of_actual_freight_invoices":False,
            "nominal_difference_is_actual_missed_invoices_or_recoverable_cash":False,
            "census_source_year_family":(
                "REVISED_2026_SAS_2017_2021" if year<=2021
                else "2024_AIES_LINKED_HISTORICAL_2022_2024"
            ),
        })
    return series


def _lineage(as_of:date)->tuple[dict,dict,dict,dict]:
    policy=_policy()
    invalid=validate_policy(policy,as_of=as_of)
    if invalid:
        raise ValueError("M34_SOURCE_DENOMINATOR_POLICY_INVALID:"+";".join(invalid))
    bea=bea_original(as_of=as_of)
    census=census_history(as_of=as_of)
    bls=original_bls_prices(as_of=as_of)
    if (bea["status"]!=BEA_OFFLINE
        or bea["original_bea_file_expected_sha256"]!=BEA_ORIGINAL_SHA256
        or bea["fresh_original_bea_publisher_xlsx_replayed_this_run"] is not False
        or bea["paid_customer_freight_invoice_rows"]!=0
        or census["source_status"]!=CENSUS_OFFLINE
        or census["census_original_replay_completed_in_this_run"] is not False
        or census["real_ltl_freight_invoice_cases_observed"]!=0
        or bls["status"]!=BLS_OFFLINE
        or bls["source_series_ids"]!=[
            "PCU484---484---","PCU484121484121","PCU484122484122"
        ]
        or bls["current_source_authenticated_month_count"]!=0
        or not (bea["human_pilot_18_independent_requirements_unmet"]
                and census["human_pilot_18_independent_requirements_unmet"]
                and bls["original_18_independent_pilot_requirements_still_unmet"])):
        raise ValueError("M34_ORIGINAL_BEA_CENSUS_BLS_SOURCE_VINTAGE_OR_PILOT_DRIFT")
    return policy,bea,census,bls


def report_shell(*,as_of:date)->dict:
    policy,bea,census,bls=_lineage(as_of)
    bea_index={row["year"]:row for row in
               bea["bea_484_2017_2024_gross_output_annual_observations"]}
    census_rows=next(x for x in census["industry_series"] if x["naics"]==NAICS)[
        "annual_revenue"
    ]
    cen_index={row["year"]:row for row in census_rows}
    bea_nom={year:Decimal(bea_index[year][
        "first_party_bea_current_dollar_gross_output_million_usd"])
        for year in YEARS}
    census_nom={year:Decimal(cen_index[year]["revenue_million_usd"])
                for year in YEARS}
    if any(
        bea_nom[y]!=_d(policy["bea_gross_output_million_nominal_usd"][str(y)])
        or census_nom[y]!=_d(policy["census_employer_revenue_million_nominal_usd"][str(y)])
        for y in YEARS
    ):
        raise ValueError("M34_EIGHT_YEAR_SOURCE_RECONCILIATION_MISMATCH")
    comparison=nominal_comparison(bea_nom,census_nom)
    first,last=comparison[0],comparison[-1]
    growth_bea=_f2((bea_nom[2024]/bea_nom[2017]-1)*100)
    growth_census=_f2((census_nom[2024]/census_nom[2017]-1)*100)
    growth_gap=_f2((bea_nom[2024]/bea_nom[2017]-
                    census_nom[2024]/census_nom[2017])*100)
    unrounded_ratio_change=(census_nom[2024]/bea_nom[2024]-
                            census_nom[2017]/bea_nom[2017])*100
    ratio_change=_f2(unrounded_ratio_change)
    if (
        first["bea_minus_census_nominal_difference_million_usd"]!="76622.000"
        or last["bea_minus_census_nominal_difference_million_usd"]!="142607.754"
        or growth_bea!="48.56" or growth_census!="38.65" or growth_gap!="9.91"
        or first["census_divided_by_bea_nominal_measure_ratio_pct"]!="79.13"
        or last["census_divided_by_bea_nominal_measure_ratio_pct"]!="73.85"
        or ratio_change!="-5.28"
    ):
        raise ValueError("M34_NOMINAL_DENOMINATOR_RECONCILIATION_CANNOT_REPRODUCE")
    ppi_parent=next(x for x in bls["industry_comparisons"] if x["naics"]==NAICS)
    bea_output_price=Decimal(bea["bea_price_index_2017_to_2024_pct"])
    bls_price=Decimal(
        ppi_parent["2017_to_2024_bls_annual_mean_output_price_change_pct"]
    )
    price_gap=_f2(bea_output_price-bls_price)
    if (price_gap!="0.45" or
        ppi_parent["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]!="1.18"):
        raise ValueError("M34_UNJUSTIFIED_PPI_PRICE_INDEX_CONCEPT_CONFLATION")
    difference_start=bea_nom[2017]-census_nom[2017]
    difference_end=bea_nom[2024]-census_nom[2024]
    r={
        "schema_version":1,"scope":SCOPE,
        "lab":14,"new_lab_created":False,"as_of":as_of.isoformat(),
        "source_status":OFFLINE,
        "bea_first_party_nominal_source":"BEA_GROSSOUTPUT_XLSX_TGO105_A_NAICS484",
        "census_first_party_nominal_source":"SAS_REVISED_2017_2021_AND_LINKED_AIES_2022_2024",
        "bls_first_party_output_price_source":"PCU484---484---",
        "nominal_usd_unit":"MILLIONS_USD_NOT_FREIGHT_INVOICES",
        "comparison_2017_to_2024":comparison,
        "bea_2017_to_2024_nominal_growth_pct":growth_bea,
        "census_2017_to_2024_nominal_growth_pct":growth_census,
        "bea_minus_census_nominal_growth_percentage_points":growth_gap,
        "bea_minus_census_nominal_2017_million_usd":_f3(difference_start),
        "bea_minus_census_nominal_2024_million_usd":_f3(difference_end),
        "bea_minus_census_nominal_gap_increase_2017_to_2024_million_usd":_f3(
            difference_end-difference_start
        ),
        "nominal_census_to_bea_measure_ratio_2017_pct":
            first["census_divided_by_bea_nominal_measure_ratio_pct"],
        "nominal_census_to_bea_measure_ratio_2024_pct":
            last["census_divided_by_bea_nominal_measure_ratio_pct"],
        "ratio_change_percentage_points":ratio_change,
        "bea_gross_output_2017_2024_real_quantity_growth_pct":
            bea["original_bea_gross_output_2017_to_2024_pct"],
        "bea_gross_output_2017_2024_price_index_growth_pct":_f2(bea_output_price),
        "bls_2017_2024_net_output_producer_price_growth_pct":_f2(bls_price),
        "bea_minus_bls_producer_price_change_difference_pp":price_gap,
        "census_bls_ppi_2017_2024_illustrative_adjusted_revenue_growth_pct":"1.18",
        "full_three_first_party_source_families_replayed_this_run":False,
        "source_families_authenticated_fresh_this_run":0,
        "source_original_replay_statuses":{
            "bea":"OFFLINE_PRIOR_FIRST_PARTY_REPLAY",
            "census":"OFFLINE_PRIOR_FIRST_PARTY_REPLAY",
            "bls":"OFFLINE_PRIOR_FIRST_PARTY_REPLAY",
        },
        "bea_original_xlsx_sha256_verified_this_run":None,
        "census_three_publisher_archives_verified_this_run":False,
        "bls_original_288_ppi_months_verified_this_run":False,
        "all_sources_have_same_economic_scope_established":False,
        "census_nominal_ratio_to_bea_is_actual_market_coverage":False,
        "nominal_gap_is_missing_carrier_invoices_or_recoverable_overcharges":False,
        "nominal_gap_has_decomposed_verified_economic_causes":False,
        "parent_484_contains_tl_and_ltl_non_additive":True,
        "bea_price_and_bls_net_output_ppi_interchangeable":False,
        "source_family_independent_paid_customer_audit":False,
        "policy_receipt_sha256":canon_hash(policy),
        "prior_m33_first_party_bea_receipt_sha256":bea["receipt_sha256"],
        "prior_m25_census_receipt_sha256":census["receipt_sha256"],
        "prior_m29_bls_ppi_receipt_sha256":bls["receipt_sha256"],
        "real_paid_customer_freight_invoices":0,
        "adjudicated_freight_invoice_errors":0,
        "retally_recovered_cash_usd":None,
        "recoverable_audit_market_tam_usd":None,
        "buyer_demand_established":False,
        "customer_or_carrier_contact_authorized":False,
        "private_customer_data_accessed":False,
        "human_pilot_18_independent_requirements_unmet":True,
        "scheduled_tasks_modified":False,
        "caveat":(
            "BEA nominal gross output for U.S. trucking NAICS 484 is an "
            "industry-production total; Census SAS/AIES employer industry "
            "revenue is a distinct employer-establishment receipts measure. "
            "The eight annual ratios/differences are descriptive arithmetic, "
            "not audited customer freight invoices, pricing errors, a "
            "market coverage estimate or a subset claim. In 2024 BEA "
            "gross output exceeds Census employer revenue by $142.607754 "
            "billion, but NOTHING establishes that difference as "
            "freight bills or recoverable funds. A true methodological "
            "and establishment coverage crosswalk is needed before "
            "causally attributing the gap. BEA real gross output price "
            "indices and BLS net-output industry PPIs measure different "
            "price universes and cannot be substituted despite similar "
            "growth. These sources also have overlapping NAICS parent "
            "and child categories; do not add them. Real customer-paid "
            "invoices, actual carrier contracts, adjudicated refunds, "
            "permissioned buyer demand and all 18 independent real-customer "
            "pilot approvals remain unmet."
        ),
    }
    r["receipt_sha256"]=canon_hash(r)
    return r


def _assert_receipt_integrity(r:object)->None:
    if not isinstance(r,dict) or not isinstance(r.get("receipt_sha256"),str):
        raise ValueError("M34_SOURCE_EVIDENCE_RECEIPT_SHAPE_INVALID")
    if r["receipt_sha256"]!=canon_hash({
        k:v for k,v in r.items() if k!="receipt_sha256"
    }):
        raise ValueError("M34_PRIOR_PUBLISHER_EVIDENCE_RECEIPT_HASH_CHANGED")


def verify_source_receipts(*,as_of:date,bea:dict,census:dict,bls:dict)->dict:
    """Audit locally generated original-source replay receipts from THIS CI job.

    This checks original direct-publisher source statuses/receipts and exact
    matched original numeric cells, not cryptographically signed external
    records. The CI invokes all three original downloaders independently.
    """
    shell=report_shell(as_of=as_of)
    rows={row["year"]:row for row in shell["comparison_2017_to_2024"]}
    for r in (bea,census,bls):
        _assert_receipt_integrity(r)
    statuses={
        "bea":bea.get("status"),
        "census":census.get("source_status"),
        "bls":bls.get("status"),
    }
    want={
        "bea":BEA_VERIFIED,
        "census":CENSUS_VERIFIED,
        "bls":BLS_VERIFIED,
    }
    family_verified={name:statuses[name]==wanted for name,wanted in want.items()}
    if statuses["bea"] not in (BEA_VERIFIED,
                              "M33_ORIGINAL_BEA_XLSX_NETWORK_UNAVAILABLE_NO_NEW_SOURCE_REPLAY"):
        raise ValueError("M34_ORIGINAL_BEA_PUBLISHER_SOURCE_STATUS_WRONG")
    if statuses["census"] not in (CENSUS_VERIFIED,
                                 "BLOCKED_CENSUS_SOURCE_NOT_REACHABLE_NO_NEW_REPLAY"):
        raise ValueError("M34_ORIGINAL_CENSUS_PUBLISHER_SOURCE_STATUS_WRONG")
    if statuses["bls"] not in (BLS_VERIFIED,
                              "M29_BLS_V2_UNAVAILABLE_NO_FRESH_THREE_INDUSTRY_SOURCE_PROOF"):
        raise ValueError("M34_ORIGINAL_BLS_PUBLISHER_SOURCE_STATUS_WRONG")
    if family_verified["bea"]:
        if (bea.get("direct_bea_original_numeric_source_authenticated") is not True
            or bea.get("fresh_original_bea_table16_year_cells_authenticated")!=8
            or bea.get("fresh_four_original_bea_tables_year_cells_authenticated")!=32
            or bea.get("fresh_original_bea_xlsx_sha256")!=BEA_ORIGINAL_SHA256):
            raise ValueError("M34_MISSING_32_FIRST_PARTY_BEA_XLSX_SOURCE_CELLS")
        actual={r["year"]:r for r in bea["bea_484_2017_2024_gross_output_annual_observations"]}
        if len(actual)!=8 or any(
            _f3(Decimal(actual[y]["first_party_bea_current_dollar_gross_output_million_usd"]))!=
            rows[y]["bea_nominal_gross_output_million_usd"] for y in YEARS
        ):
            raise ValueError("M34_FRESH_BEA_REAL_PUBLISHER_NOMINAL_SOURCE_DISAGREES")
    if family_verified["census"]:
        receipts=census.get("source_original_archive_receipts")
        if (census.get("census_original_replay_completed_in_this_run") is not True
            or type(receipts) is not list or len(receipts)!=3
            or set(x["id"] for x in receipts)!=set(CENSUS_IDS)
            or any(x.get("sha256")!=EXPECTED_CENSUS_ORIGINAL_SHA256[x["id"]]
                   for x in receipts)):
            raise ValueError("M34_MISSING_OR_CHANGED_THREE_CENSUS_ORIGINAL_ARCHIVES")
        ces=next(x for x in census["industry_series"] if x["naics"]==NAICS)
        actual={r["year"]:r for r in ces["annual_revenue"]}
        if len(actual)!=8 or any(
            _f3(Decimal(actual[y]["revenue_million_usd"]))!=
            rows[y]["census_employer_industry_revenue_million_usd"]
            for y in YEARS
        ):
            raise ValueError("M34_FRESH_CENSUS_ORIGINAL_NOMINAL_SOURCE_DISAGREES")
    if family_verified["bls"]:
        if (bls.get("current_original_bls_source_replayed_this_run") is not True
            or bls.get("current_source_authenticated_month_count")!=288
            or len(bls.get("original_bls_response_sha256") or "")!=64
            or bls.get("source_series_ids")!=[
                "PCU484---484---","PCU484121484121","PCU484122484122"
            ]):
            raise ValueError("M34_BLS_DIRECT_ORIGINAL_MONTHS_NOT_288")
        p=next(x for x in bls["industry_comparisons"] if x["naics"]==NAICS)
        if p["2017_to_2024_bls_annual_mean_output_price_change_pct"]!="37.04":
            raise ValueError("M34_FRESH_BLS_PRODUCER_PRICE_CHANGE_DRIFT")
    shell["source_original_replay_statuses"]=statuses
    shell["source_families_authenticated_fresh_this_run"]=sum(family_verified.values())
    shell["full_three_first_party_source_families_replayed_this_run"]=all(family_verified.values())
    shell["bea_original_xlsx_sha256_verified_this_run"]=(
        BEA_ORIGINAL_SHA256 if family_verified["bea"] else None
    )
    shell["census_three_publisher_archives_verified_this_run"]=family_verified["census"]
    shell["bls_original_288_ppi_months_verified_this_run"]=family_verified["bls"]
    shell["source_status"]=VERIFIED if all(family_verified.values()) else BLOCKED
    shell["fresh_source_family_receipts"]={
        key: value["receipt_sha256"] if family_verified[key] else None
        for key,value in (("bea",bea),("census",census),("bls",bls))
    }
    shell["receipt_sha256"]=canon_hash({
        k:v for k,v in shell.items() if k!="receipt_sha256"
    })
    return shell


def render_html(r:dict)->str:
    table="".join(
        "<tr><th>"+str(x["year"])+"</th><td>"+
        escape(x["bea_nominal_gross_output_million_usd"])+
        "</td><td>"+escape(x["census_employer_industry_revenue_million_usd"])+
        "</td><td>"+escape(x["bea_minus_census_nominal_difference_million_usd"])+
        "</td><td>"+escape(x["census_divided_by_bea_nominal_measure_ratio_pct"])+
        "%</td></tr>" for x in r["comparison_2017_to_2024"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | Trucking industry denominator reconciliation</title>'
        '<style>body{font:15px/1.55 system-ui;background:#f5f8f5;color:#173a2b;'
        'margin:0}main{max-width:1120px;margin:32px auto;padding:20px}'
        'table{border-collapse:collapse;background:white;width:100%}'
        'th,td{padding:11px;border-bottom:1px solid #d6dfd7;text-align:left}'
        'small{color:#587162}</style></head><body><main>'
        '<small>RETALLY / EXISTING RESEARCH LAB 14 / M34 / INTERNAL ONLY</small>'
        '<h1>BEA gross output differs from Census employer revenue</h1>'
        '<p>Original source verification in this run: <strong>'+
        escape(r["source_status"])+'</strong> — '+
        str(r["source_families_authenticated_fresh_this_run"])+
        ' of 3 original publisher source families freshly replayed. '
        'An offline result only uses previously verified immutable source catalogs.</p>'
        '<table><thead><tr><th>Year</th><th>BEA gross output ($million)</th>'
        '<th>Census employer revenue ($million)</th>'
        '<th>Difference ($million)</th>'
        '<th>Nominal measurement ratio, NOT invoice coverage</th>'
        '</tr></thead><tbody>'+table+'</tbody></table>'
        '<p><strong>2024 measurement difference: $'+
        escape(r["bea_minus_census_nominal_2024_million_usd"])+
        ' million. This is NOT a missing-freight-invoice or recoverable '
        'overcharge amount.</strong></p>'
        '<p>BEA gross-output nominal growth: '+
        escape(r["bea_2017_to_2024_nominal_growth_pct"])+
        '%. Census employer revenue growth: '+
        escape(r["census_2017_to_2024_nominal_growth_pct"])+
        '%. These differing totals have not been proved to share '
        'identical establishment and transaction coverage.</p>'
        '<p>BEA gross-output prices: '+
        escape(r["bea_gross_output_2017_2024_price_index_growth_pct"])+
        '%. BLS net-output producer-price index: '+
        escape(r["bls_2017_2024_net_output_producer_price_growth_pct"])+
        '%. Similar numerical price trends do not imply interchangeable '
        'deflators or freight bill rates.</p>'
        '<p>'+escape(r["caveat"])+'</p>'
        '<p><a href="https://apps.bea.gov/industry/Release/XLS/GDPxInd/GrossOutput.xlsx">'
        'Original BEA GrossOutput.xlsx</a> · '
        '<a href="https://www.census.gov/programs-surveys/aies.html">'
        'Census industry revenue scope</a></p>'
        '</main></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Trucking nominal industry-measure reconciliation, not freight TAM")
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--as-of-date",default=date.today().isoformat())
    m=p.add_mutually_exclusive_group(required=True)
    m.add_argument("--offline",action="store_true")
    m.add_argument("--verify-original-receipts",nargs=3,
                   metavar=("BEA_JSON","CENSUS_JSON","BLS_JSON"))
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.verify_original_receipts:
        bea,census,bls=[
            json.loads(Path(path).read_text(encoding="utf-8"))
            for path in args.verify_original_receipts
        ]
        result=verify_source_receipts(as_of=as_of,bea=bea,census=census,bls=bls)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"economic_denominator_reconciliation.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"economic_denominator_reconciliation.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":result["source_status"],
        "source_families_fresh":result["source_families_authenticated_fresh_this_run"],
        "bea_minus_census_2024_million_usd":
            result["bea_minus_census_nominal_2024_million_usd"],
        "is_actual_freight_billing_overcharge_or_tam":False,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
