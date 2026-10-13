"""RETALLY Lab 14 / Mission 34: BEA–Census denominator reconciliation.

Two genuine first-party government economic series, two distinct measurement
populations. The arithmetic BEA-minus-Census amount is NEVER evidence of a
missing freight invoice, an overcharge, recoverable cash, or serviceable TAM.
Fresh proof requires one BEA original XLSX and three original Census archives.
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
from freight import research_sas_aies_bridge as census_m25
from freight import research_unified_blspci as bls_m29
from freight import research_bea_original_m33 as bea_m33

BOOK = Path(__file__).parent/"research/TRUCKING_MEASURE_DENOMINATOR_M34_20261012.json"
BOOK_BLOB_SHA1 = "1745511aaf5b95b9ad61824ae46f4596c705fdf0"
SCOPE = "LAB14_M34_BEA_VS_CENSUS_NOMINAL_TRUCKING_DENOMINATOR_NOT_RECOVERABLE_TAM"
BOOK_SCOPE = "LAB14_M34_CENSUS_EMPLOYER_REVENUE_VS_BEA_GROSS_OUTPUT_DENOMINATOR_GATE_NOT_FREIGHT_TAM"
OFFLINE = "M34_OFFLINE_ORIGINAL_BEA_CENSUS_PRIOR_SNAPSHOTS_NOT_REPLAYED"
VERIFIED = "M34_DIRECT_BEA_XLSX_AND_THREE_CENSUS_ORIGINAL_ARCHIVES_REPLAYED"
BLOCKED = "M34_ORIGINAL_PUBLISHER_DOWNLOAD_UNAVAILABLE_NO_NEW_FOUR_FILE_REPLAY"
MIN_DATE = date(2026,10,12)
YEARS = tuple(range(2017,2025))
BEA = ("367154","401324","409425","413595","490334","577292","546993","545435")
CENSUS = ("290532.000","310688.000","314044.000","308131.000",
          "361243.000","423270.958","406651.010","402827.246")
FALSE_CLAIMS = (
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


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _book()->dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_BLOB_SHA1:
        raise ValueError("M34_FROZEN_ECONOMIC_SOURCE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _dec(raw:object)->Decimal:
    if type(raw) not in (int,str,Decimal):
        raise ValueError("M34_SOURCE_VALUE_NOT_EXACT_DECIMAL")
    try:
        d=Decimal(str(raw))
    except InvalidOperation as exc:
        raise ValueError("M34_INVALID_ECONOMIC_SOURCE_DECIMAL") from exc
    if not d.is_finite() or d<=0 or d>Decimal("9999999999"):
        raise ValueError("M34_ECONOMIC_SOURCE_VALUE_OUT_OF_RANGE")
    return d


def _round(d:Decimal,place:str="0.01")->str:
    return str(d.quantize(Decimal(place),rounding=ROUND_HALF_UP))


def validate_book(book:object,*,as_of:date)->list[str]:
    try:
        if type(book) is not dict or book!=_book():
            return ["M34_SOURCE_CATALOG_DRIFT_OR_ADDED_PRIVATE_EVIDENCE"]
        errors=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            errors.append("M34_EVIDENCE_BEFORE_ORIGINAL_SOURCE_OBSERVATION")
        if (book.get("schema_version")!=1 or book.get("scope")!=BOOK_SCOPE
            or book.get("naics")!="484" or book.get("years")!=list(YEARS)
            or book.get("industry")!="Truck transportation"
            or book.get("observed_on")!="2026-10-12"
            or book.get("geography")!="United States"):
            errors.append("M34_WRONG_ECONOMIC_MEASUREMENT_NAICS_DATE")
        source=book.get("sources")
        if (type(source) is not dict or set(source)!={"bea","census","bls"}
            or source["bea"].get("original_workbook_sha256")!=bea_m33.BEA_ORIGINAL_SHA256
            or source["bea"].get("unit")!="MILLION_CURRENT_USD"
            or source["bea"].get("sheet")!="TGO105-A"
            or source["census"].get("unit")!="MILLION_NOMINAL_USD_EMPLOYER_INDUSTRY"
            or source["bls"].get("series")!="PCU484---484---"):
            errors.append("M34_BEA_CENSUS_BLS_SOURCE_AUTHORITY_UNITS_DRIFT")
        for fld,values in (
            ("bea_gross_output_million_nominal_usd",BEA),
            ("census_employer_revenue_million_nominal_usd",CENSUS),
        ):
            if book.get(fld)!={str(y):values[i] for i,y in enumerate(YEARS)}:
                errors.append("M34_FROZEN_ORIGINAL_PUBLISHER_NOMINAL_VALUES_CHANGED:"+fld)
        for fld,want in (
            ("bea_gross_output_2017_2024_nominal_growth_pct","48.56"),
            ("census_employer_revenue_2017_2024_nominal_growth_pct","38.65"),
            ("bea_minus_census_growth_percentage_points","9.91"),
            ("bea_gross_output_minus_census_nominal_2017_million_usd","76622.000"),
            ("bea_gross_output_minus_census_nominal_2024_million_usd","142607.754"),
            ("census_over_bea_nominal_ratio_2017_pct","79.13"),
            ("census_over_bea_nominal_ratio_2024_pct","73.85"),
            ("ratio_change_2024_minus_2017_percentage_points","-5.28"),
            ("bea_gross_output_quantity_2017_2024_pct","8.05"),
            ("bea_gross_output_price_index_2017_2024_pct","37.49"),
            ("bls_parent_producer_price_2017_2024_pct","37.04"),
            ("bea_vs_bls_price_index_change_percentage_points","0.45"),
            ("m29_illustrative_census_ppi_real_revenue_proxy_2017_2024_pct","1.18"),
        ):
            if book.get(fld)!=want:
                errors.append("M34_FROZEN_SOURCE_GAP_OR_INDEX_CHANGED:"+fld)
        for fld in FALSE_CLAIMS:
            if book.get(fld) is not False:
                errors.append("M34_FORGED_FREIGHT_TAM_CUSTOMER_OR_MEASURE_CLAIM:"+fld)
        for fld,want in (
            ("real_paid_customer_invoices_observed",0),
            ("independent_actual_carrier_overcharges_detected",0),
            ("real_freight_customers_or_buyers_contacted",0),
            ("actual_cash_refunds_recovered_usd",None),
            ("recovery_market_tam_usd",None),
        ):
            if type(book.get(fld))!=type(want) or book.get(fld)!=want:
                errors.append("M34_FAKE_RECOVERY_OR_CUSTOMER_PROOF:"+fld)
        caveat=book.get("source_caveat")
        if type(caveat) is not str or len(caveat)<600 or "18 independent" not in caveat:
            errors.append("M34_SOURCE_SCOPE_AND_18_PILOT_WARNINGS_MISSING")
        return errors
    except (TypeError,KeyError,ValueError,AttributeError):
        return ["M34_UNTRUSTED_SOURCE_BOOK_UNREADABLE"]


def _baseline(*,as_of:date)->tuple[dict,dict,dict,dict]:
    b=_book()
    faults=validate_book(b,as_of=as_of)
    if faults:
        raise ValueError("M34_SOURCE_CATALOG_REJECTED:"+";".join(faults))
    census=census_m25.report_shell(as_of=as_of)
    bea=bea_m33.report_shell(as_of=as_of)
    bls=bls_m29.report_shell(as_of=as_of)
    if (census["source_status"]!=census_m25.OFFLINE
        or census["real_ltl_freight_invoice_cases_observed"]!=0
        or census["recoverable_freight_audit_market_usd"] is not None
        or census["human_pilot_18_independent_requirements_unmet"] is not True
        or bea["status"]!=bea_m33.OFFLINE
        or bea["original_bea_file_expected_sha256"]!=bea_m33.BEA_ORIGINAL_SHA256
        or bea["paid_customer_freight_invoice_rows"]!=0
        or bea["human_pilot_18_independent_requirements_unmet"] is not True
        or bls["status"]!=bls_m29.OFFLINE
        or bls["source_series_ids"][0]!="PCU484---484---"
        or bls["freight_recovery_market_tam_usd"] is not None):
        raise ValueError("M34_EXISTING_ORIGINAL_SOURCE_OR_CUSTOMER_PILOT_CHAIN_DRIFT")
    return b,census,bea,bls


def compare_nominal_source_rows(*,bea:dict,census:dict,book:dict)->list[dict]:
    """Eight matching years/NAICS, not identical industry survey populations."""
    matching=[x for x in census.get("industry_series",[]) if x.get("naics")=="484"]
    if len(matching)!=1:
        raise ValueError("M34_CENSUS_PARENT_INDUSTRY_MISSING_OR_DUPLICATE")
    ca=matching[0]["annual_revenue"]
    br=bea.get("bea_484_2017_2024_gross_output_annual_observations",[])
    if ([x.get("year") for x in ca]!=list(YEARS)
        or [x.get("year") for x in br]!=list(YEARS)):
        raise ValueError("M34_SOURCE_YEAR_SEQUENCE_MISSING_REORDERED_OR_DUPLICATE")
    if census.get("scope")!=census_m25.SCOPE or bea.get("scope")!=bea_m33.SCOPE:
        raise ValueError("M34_WRONG_ECONOMIC_SOURCE_SCOPE_OR_INDUSTRY")
    result=[]
    for y,a,c in zip(YEARS,br,ca):
        bn=_dec(a.get("first_party_bea_current_dollar_gross_output_million_usd"))
        cn=_dec(c.get("revenue_million_usd"))
        if bn!=_dec(book["bea_gross_output_million_nominal_usd"][str(y)]):
            raise ValueError("M34_BEA_ORIGINAL_SOURCE_ROW_VALUE_CHANGED:"+str(y))
        if cn!=_dec(book["census_employer_revenue_million_nominal_usd"][str(y)]):
            raise ValueError("M34_CENSUS_ORIGINAL_SOURCE_ROW_VALUE_CHANGED:"+str(y))
        if (c.get("year_is_linked_legacy_not_standalone_aies_survey") is not (y==2022)
            or c.get("is_customer_freight_invoice_or_recovered_cash") is not False
            or a.get("is_customer_invoice_or_recoverable_cash") is not False):
            raise ValueError("M34_FABRICATED_INDEPENDENT_2022_AIES_OR_CUSTOMER_BILL")
        result.append({
            "year":y,
            "bea_current_dollar_gross_output_million_usd":_round(bn,"0.001"),
            "census_employer_industry_revenue_million_usd":_round(cn,"0.001"),
            "bea_minus_census_arithmetic_difference_million_usd":_round(bn-cn,"0.001"),
            "census_over_bea_arithmetic_ratio_pct":_round(cn/bn*100),
            "arithmetic_difference_measures_missing_invoices":False,
            "arithmetic_ratio_measures_freight_invoice_coverage":False,
            "equal_statistical_coverage_proven":False,
            "is_real_paid_customer_invoice_or_refund":False,
            "2022_census_legacy_linked_observation":y==2022,
        })
    return result


def report_shell(*,as_of:date)->dict:
    book,census,bea,bls=_baseline(as_of=as_of)
    rows=compare_nominal_source_rows(bea=bea,census=census,book=book)
    bea_start=_dec(rows[0]["bea_current_dollar_gross_output_million_usd"])
    bea_end=_dec(rows[-1]["bea_current_dollar_gross_output_million_usd"])
    cen_start=_dec(rows[0]["census_employer_industry_revenue_million_usd"])
    cen_end=_dec(rows[-1]["census_employer_industry_revenue_million_usd"])
    bea_growth=_round((bea_end/bea_start-1)*100)
    cen_growth=_round((cen_end/cen_start-1)*100)
    bea_minus_cen_growth=_round((bea_end/bea_start-cen_end/cen_start)*100)
    arithmetic_ratio_change=_round((cen_end/bea_end-cen_start/bea_start)*100)
    price=next(x for x in bls["industry_comparisons"] if x["naics"]=="484")
    bea_price=bea["bea_price_index_2017_to_2024_pct"]
    bls_price=price["2017_to_2024_bls_annual_mean_output_price_change_pct"]
    price_delta=_round(_dec(bea_price)-_dec(bls_price))
    computed={
        "bea_gross_output_2017_2024_nominal_growth_pct":bea_growth,
        "census_employer_revenue_2017_2024_nominal_growth_pct":cen_growth,
        "bea_minus_census_growth_percentage_points":bea_minus_cen_growth,
        "bea_gross_output_minus_census_nominal_2017_million_usd":
            rows[0]["bea_minus_census_arithmetic_difference_million_usd"],
        "bea_gross_output_minus_census_nominal_2024_million_usd":
            rows[-1]["bea_minus_census_arithmetic_difference_million_usd"],
        "census_over_bea_nominal_ratio_2017_pct":
            rows[0]["census_over_bea_arithmetic_ratio_pct"],
        "census_over_bea_nominal_ratio_2024_pct":
            rows[-1]["census_over_bea_arithmetic_ratio_pct"],
        "ratio_change_2024_minus_2017_percentage_points":arithmetic_ratio_change,
        "bea_gross_output_price_index_2017_2024_pct":bea_price,
        "bls_parent_producer_price_2017_2024_pct":bls_price,
        "bea_vs_bls_price_index_change_percentage_points":price_delta,
        "m29_illustrative_census_ppi_real_revenue_proxy_2017_2024_pct":
            price["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"],
    }
    if any(computed[k]!=book[k] for k in computed):
        raise ValueError("M34_ORIGINAL_GROWTH_RATIO_PRICE_DENOMINATOR_NUMBERS_DRIFT")
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,
        "source_status":OFFLINE,
        "fresh_bea_original_workbook_replayed_this_run":False,
        "fresh_three_original_census_archives_replayed_this_run":False,
        "fresh_original_publisher_file_count":0,
        "fresh_bea_four_table_year_cells_authenticated":0,
        "fresh_census_original_source_cell_instances_authenticated":0,
        "naics":"484","industry":"Truck transportation",
        "period":list(YEARS),"unit":"MILLION_NOMINAL_USD",
        "annual_comparisons":rows,
        "bea_nominal_gross_output_2017_2024_pct":bea_growth,
        "census_nominal_employer_revenue_2017_2024_pct":cen_growth,
        "difference_in_nominal_growth_percentage_points":bea_minus_cen_growth,
        "bea_minus_census_2017_arithmetic_difference_million_usd":
            rows[0]["bea_minus_census_arithmetic_difference_million_usd"],
        "bea_minus_census_2024_arithmetic_difference_million_usd":
            rows[-1]["bea_minus_census_arithmetic_difference_million_usd"],
        "census_over_bea_2017_arithmetic_ratio_pct":
            rows[0]["census_over_bea_arithmetic_ratio_pct"],
        "census_over_bea_2024_arithmetic_ratio_pct":
            rows[-1]["census_over_bea_arithmetic_ratio_pct"],
        "ratio_change_2024_minus_2017_percentage_points":arithmetic_ratio_change,
        "bea_gross_output_price_index_2017_2024_pct":bea_price,
        "bls_producer_net_output_ppi_2017_2024_pct":bls_price,
        "bea_vs_bls_price_change_percentage_points":price_delta,
        "bea_real_gross_output_quantity_index_change_pct":
            bea["original_bea_gross_output_2017_to_2024_pct"],
        "illustrative_census_ppi_adjusted_revenue_change_pct":
            price["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"],
        "bea_census_economic_measurement_coverage_identical_proven":False,
        "arithmetic_gap_is_paid_freight_bill_or_overcharge":False,
        "census_bea_ratio_measures_addressable_freight_market":False,
        "economic_population_difference_causally_decomposed":False,
        "bea_gross_output_and_census_revenue_additive_as_markets":False,
        "bea_gross_output_price_index_and_bls_ppi_identical":False,
        "parent_484_includes_484121_truckload_and_484122_ltl":True,
        "source_family_manifest_receipts":{
            "bea_primary_workbook_sha256":bea["original_bea_file_expected_sha256"],
            "bea_m33_source_catalog_receipt_sha256":bea["source_book_receipt_sha256"],
            "census_m25_source_catalog_receipt_sha256":
                census["frozen_census_source_manifest_receipt_sha256"],
            "bls_m29_source_policy_receipt_sha256":bls["source_policy_receipt_sha256"],
        },
        "actual_paid_customer_freight_invoices_observed":0,
        "independently_adjudicated_freight_overcharges":0,
        "actual_cash_refunds_usd":None,
        "recoverable_freight_market_tam_usd":None,
        "verified_buyers_with_demand":0,
        "external_carrier_customer_contact_authorized":False,
        "private_customer_or_carrier_data_accessed":False,
        "all_18_independent_customer_pilot_requirements_unmet":True,
        "scheduled_tasks_modified":False,
        "caveat":(
            "BEA gross output and Census employer establishment revenue "
            "are both nominal industry quantities but use different "
            "statistical definitions, coverage, survey vintages and "
            "potentially establishment populations. The BEA minus Census "
            "dollar gap, their arithmetic ratio, and different growth "
            "rates do NOT establish missing freight invoices, unbilled "
            "shipments, overcharges, recoverable refunds, serviceable TAM "
            "or buyer demand. BEA gross-output prices and BLS net-output "
            "PPI are not identical deflators. Parent NAICS 484 includes "
            "TL and LTL and must not be added to either child industry. "
            "Census 2022 historical data are legacy-linked rather than "
            "a separately fielded AIES observation. Source-population "
            "differences cannot be causally decomposed with these tables. "
            "All 18 independent real-customer pilot approvals remain unmet."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_publishers(*,as_of:date,bea_xlsx:bytes,census_archives:dict[str,bytes])->dict:
    bea=bea_m33.verify_original_publisher(as_of=as_of,raw=bea_xlsx)
    census=census_m25.verify_origins(as_of=as_of,archives=census_archives)
    if (bea["status"]!=bea_m33.VERIFIED
        or bea["fresh_four_original_bea_tables_year_cells_authenticated"]!=32
        or census["source_status"]!=census_m25.VERIFIED
        or census["census_original_replay_completed_in_this_run"] is not True):
        raise ValueError("M34_ORIGINAL_BEA_CENSUS_PUBLISHER_REPLAY_NOT_VERIFIED")
    report=report_shell(as_of=as_of)
    fresh_bea={r["year"]:r for r in bea["bea_484_2017_2024_gross_output_annual_observations"]}
    fresh_census={r["year"]:r for r in next(
        x for x in census["industry_series"] if x["naics"]=="484"
    )["annual_revenue"]}
    for row in report["annual_comparisons"]:
        yr=row["year"]
        if (_dec(fresh_bea[yr]["first_party_bea_current_dollar_gross_output_million_usd"])
            !=_dec(row["bea_current_dollar_gross_output_million_usd"])
            or _dec(fresh_census[yr]["revenue_million_usd"])
            !=_dec(row["census_employer_industry_revenue_million_usd"])):
            raise ValueError("M34_FRESH_ORIGINAL_PUBLISHER_NAICS484_YEAR_VALUE_MISMATCH:"+str(yr))
    receipts=census["source_original_archive_receipts"]
    if len(receipts)!=3 or sum(
        x.get("source_tax_year_cells",0)+x.get("national_industry_year_cells",0)
        for x in receipts
    )!=48:
        raise ValueError("M34_THREE_CENSUS_ARCHIVES_48_SOURCE_INSTANCES_REQUIRED")
    report.update({
        "source_status":VERIFIED,
        "fresh_bea_original_workbook_replayed_this_run":True,
        "fresh_three_original_census_archives_replayed_this_run":True,
        "fresh_original_publisher_file_count":4,
        "fresh_bea_four_table_year_cells_authenticated":32,
        "fresh_census_original_source_cell_instances_authenticated":48,
        "new_original_publisher_receipts":{
            "bea_xlsx_sha256":bea["fresh_original_bea_xlsx_sha256"],
            "bea_four_table_semantic_receipt":bea["fresh_primary_source_semantic_receipt_sha256"],
            "census_three_archives":receipts,
        },
    })
    report["receipt_sha256"]=canon_hash({
        k:v for k,v in report.items() if k!="receipt_sha256"
    })
    return report


def blocked(*,as_of:date)->dict:
    r=report_shell(as_of=as_of)
    r["source_status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def fetch_all_origins()->tuple[bytes,dict[str,bytes]]:
    return bea_m33.fetch_original_bea(), {
        census_m25.SAS_ID:census_m25.get_source("revised_table2"),
        census_m25.HISTORY_ID:census_m25.download_aies_history(),
        census_m25.BASIC_ID:census_m25.download_aies_basic(),
    }


def render_html(r:dict)->str:
    headings="".join("<th>"+str(y)+"</th>" for y in YEARS)
    tr=""
    for col,label in (
        ("bea_current_dollar_gross_output_million_usd","BEA nominal gross output"),
        ("census_employer_industry_revenue_million_usd","Census employer revenue"),
        ("bea_minus_census_arithmetic_difference_million_usd",
         "BEA minus Census (arithmetic, NOT customer overcharges)"),
        ("census_over_bea_arithmetic_ratio_pct","Census / BEA arithmetic ratio"),
    ):
        tr+="<tr><th>"+escape(label)+"</th>"+"".join(
            "<td>"+escape(row[col])+("%" if col.endswith("_pct") else "")+"</td>"
            for row in r["annual_comparisons"]
        )+"</tr>"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab14 | BEA Census denominator mismatch</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f6f9f7;color:#173b29;'
        'margin:0}main{max-width:1150px;margin:30px auto;padding:20px}'
        'table{border-collapse:collapse;background:white;min-width:930px}'
        'th,td{border-bottom:1px solid #dce6de;padding:11px;text-align:right}'
        'th:first-child{text-align:left}.scroll{overflow-x:auto}'
        'small{color:#526e60}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 34 / INTERNAL ONLY</small>'
        '<h1>Nominal U.S. trucking BEA versus Census — different denominators</h1>'
        '<p>Original economic publisher replay: <strong>'+escape(r["source_status"])+
        '</strong>. Monetary values are million nominal USD, NOT verified '
        'customer freight invoices or recoverable billings.</p>'
        '<div class="scroll"><table><thead><tr><th>Measure</th>'+
        headings+'</tr></thead><tbody>'+tr+'</tbody></table></div>'
        '<p>BEA nominal 2017–2024 growth: '+
        escape(r["bea_nominal_gross_output_2017_2024_pct"])+
        '%; Census employer revenue growth: '+
        escape(r["census_nominal_employer_revenue_2017_2024_pct"])+
        '%. The difference in growth is '+
        escape(r["difference_in_nominal_growth_percentage_points"])+
        ' percentage points, not a verified model error or missing invoice amount.</p>'
        '<p>BEA gross-output price index: '+
        escape(r["bea_gross_output_price_index_2017_2024_pct"])+
        '%; BLS net-output PPI: '+
        escape(r["bls_producer_net_output_ppi_2017_2024_pct"])+
        '%. Similar direction is not equal price-index scope.</p>'
        '<p><strong>The dollar gap is NOT a freight-audit TAM, customer '
        'overcharge estimate, or cash recovery.</strong></p><p>'+
        escape(r["caveat"])+'</p>'
        '</main></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Source-safe BEA/Census denominator comparison")
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-originals",action="store_true")
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_originals:
        try:
            bea_xlsx,census_files=fetch_all_origins()
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_publishers(as_of=as_of,bea_xlsx=bea_xlsx,census_archives=census_files)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"trucking_denominator.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"trucking_denominator.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":result["source_status"],
        "fresh_original_publisher_files":result["fresh_original_publisher_file_count"],
        "years_reconciled":len(result["annual_comparisons"]),
        "verified_recoverable_market_tam_usd":result["recoverable_freight_market_tam_usd"],
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
