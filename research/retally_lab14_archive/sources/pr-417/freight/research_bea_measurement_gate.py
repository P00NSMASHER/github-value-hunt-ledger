"""RETALLY Lab 14 Mission 30: BEA real-output vs real-GDP measurement gate.

Important distinctions:
- Industry gross output is NOT real GDP/value added.
- Official real gross output would be the relevant independent output
  benchmark for an illustrative Census revenue/BLS PPI construction,
  but original BEA 484 gross-output values have NOT been authenticated.
- The BEA/FRED 2025 and 2026 REAL GDP/VALUE ADDED figures refer to
  different publication vintages. A revised sign is not an audit result.
- No customer invoices, bill mistakes, refunds, demand, TAM or real-output
  model validation are proven by any of these sources.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash
from freight.research_unified_blspci import (
    report_shell as m29_offline,
    OFFLINE as M29_OFFLINE,
)

BOOK = Path(__file__).parent / "research/BEA_TRUCKING_MEASURE_COMPATIBILITY_M30_20261012.json"
BOOK_SHA1 = "384217f53378d75fb80dc29ec608bfa545cafc92"
SCOPE = "LAB14_M30_BEA_MEASUREMENT_VINTAGE_COMPATIBILITY_GATE_NOT_REAL_GROSS_OUTPUT"
BOOK_SCOPE = "LAB14_BEA_REAL_GROSS_OUTPUT_VS_VALUE_ADDED_COMPATIBILITY_GATE"
MIN_DATE = date(2026,10,12)
OFFLINE = "M30_OFFLINE_BEA_DEFINITIONS_PREVIOUSLY_VERIFIED_GROSS_OUTPUT_VALUES_HELD"
VERIFIED = "M30_FIRST_PARTY_BEA_MEASURE_DEFINITIONS_REPLAYED_GROSS_OUTPUT_VALUES_STILL_HELD"
BLOCKED = "M30_BEA_MEASURE_DEFINITIONS_PUBLISHER_NETWORK_UNAVAILABLE_GROSS_OUTPUT_HELD"
DEC = Decimal
MAX_HTML=150_000
REQUIRED_FALSE = (
    "current_value_added_gdp_is_real_gross_output",
    "producer_price_index_adjusted_census_revenue_is_official_real_output",
    "bea_value_added_measure_sufficient_to_certify_ppi_revenue_proxy",
    "reauthorize_external_business_claims",
    "source_2025_bea_index_can_replace_2026_revision",
    "original_gross_output_484_source_verified",
    "original_bea_value_added_data_bytes_replayed_in_ci",
    "gdp_and_gross_output_are_same_denominator",
    "ppi_proxy_minus_value_added_delta_as_statistical_validation_allowed",
    "be_a_real_gross_output_ltl_484122_direct_source_confirmed",
    "client_paid_freight_invoices_observed",
    "independent_freight_invoice_overcharges",
    "all_18_customer_pilot_approvals_satisfied",
    "new_lab_created",
    "scheduled_tasks_modified",
    "private_client_data_ingested",
)
REQUIRED_NULL = (
    "bea_real_gross_output_484_2017_2024_values",
    "actual_cash_recovered_usd",
    "recoverable_freight_market_tam_usd",
)


def _blob(raw: bytes) -> str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _book() -> dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=BOOK_SHA1:
        raise ValueError("M30_BEA_SOURCE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_book(book: object, *, as_of:date) -> list[str]:
    try:
        if type(book) is not dict or book != _book():
            return ["M30_ORIGINAL_BEA_ECONOMIC_SOURCE_OR_CLAIM_DRIFT"]
        problems=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            problems.append("M30_BEA_OBSERVATION_TIME_TRAVEL")
        if (book.get("schema_version")!=1 or book.get("scope")!=BOOK_SCOPE
            or book.get("industry_naics")!="484"
            or book.get("current_bea_release_date")!="2026-09-30"
            or book.get("bea_real_gross_output_484_2017_2024_source_status")!=
                 "HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED"):
            problems.append("M30_BEA_INDUSTRY_PUBLISHER_RELEASE_OR_GROSS_OUTPUT_HOLD_INVALID")
        for flag in REQUIRED_FALSE:
            if book.get(flag) is not False and not (
                flag in ("client_paid_freight_invoices_observed",
                         "independent_freight_invoice_overcharges") and
                type(book.get(flag)) is int and book.get(flag)==0
            ):
                problems.append("M30_INCOMPATIBLE_REAL_OUTPUT_OR_FAKE_CUSTOMER_PROOF:"+flag)
        for field in REQUIRED_NULL:
            if book.get(field) is not None:
                problems.append("M30_UNVERIFIED_BEA_OUTPUT_OR_RECOVERY_DOLLARS:"+field)
        if (book.get("reauthorize_external_business_claims") is not False
            or book.get("buyer_demand_proven") is not False):
            problems.append("M30_UNAUTHORIZED_COMMERCIAL_CLAIM")
        pages=book.get("source_replay_ci_result")
        if pages!={
            "bea_measure_definitions":"VERIFIED_FIRST_PARTY_HTML",
            "bea_gross_output_home_page":"VERIFIED_FIRST_PARTY_HTML",
            "fred_bea_real_gdp_index":"BLOCKED_TIMEOUT",
            "fred_bea_real_gdp_chained_dollars":"BLOCKED_TIMEOUT",
            "fred_bea_csv":"BLOCKED_TIMEOUT",
        }:
            problems.append("M30_FRED_OR_BEA_SOURCE_REPLAY_PROVENANCE_MISREPRESENTED")
        old=book.get("bea_real_value_added_2025_vintage")
        newer=book.get("bea_real_value_added_2026_vintage")
        if (old["year_values"]["2017"]!="100.000" or
            old["year_values"]["2024"]!="101.406" or
            newer["year_values"]["2017"]!=177967 or
            newer["year_values"]["2024"]!=173669 or
            newer["last_updated"]!="2026-09-30" or
            old["last_updated"]!="2025-09-26"):
            problems.append("M30_INDUSTRY_484_GDP_VALUE_ADDED_VINTAGES_NOT_AUTHENTICATED")
        if (book["bea_2025_to_2026_2024_index_revision_percentage_points"]!="-3.821"
            or book["bea_alternative_current_index_secondary_web_observation"][
                "value_2024"]!="97.585"):
            problems.append("M30_2026_REVISED_SOURCE_VINTAGE_INCORRECT")
        for key, url in (
            ("bea_definitions_source",
             "https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables"),
            ("bea_gross_output_source",
             "https://www.bea.gov/data/industries/gross-output-by-industry"),
        ):
            src=book.get(key)
            if type(src) is not dict or src.get("url")!=url or (
                src.get("source_type")!="FIRST_PARTY_BEA" or
                src.get("source_http_verified_in_ci") is not True or
                len(src.get("source_html_sha256_at_probe",""))!=64
            ):
                problems.append("M30_OFFICIAL_BEA_DEFINITIONS_PROVENANCE_CORRUPT:"+key)
        if type(book.get("source_caveat")) is not str or len(book["source_caveat"])<900:
            problems.append("M30_BEA_MEASURE_AND_CUSTOMER_LIMITATIONS_MISSING")
        return problems
    except (TypeError,KeyError,ValueError,AttributeError):
        return ["M30_INVALID_OR_MALFORMED_SOURCE_CATALOG"]


def _percent(part: Decimal, whole: Decimal) -> str:
    if whole<=0:raise ValueError("M30_INVALID_BEA_OUTPUT_DENOMINATOR")
    return str(((part/whole-1)*100).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def measure_compatible(*, claimed: str, benchmark: str) -> bool:
    """Only exactly gross-output industry quantities could validate output volume.

    BEA real GDP (value added) includes intermediate-input subtraction; it
    must not be used as a certification test for nominal-revenue/PPI proxies.
    """
    if claimed!="ILLUSTRATIVE_CENSUS_EMPLOYER_REVENUE_BLS_PPI_PROXY":
        raise ValueError("M30_UNKNOWN_MODEL_MEASURE")
    if benchmark=="BEA_REAL_GDP_VALUE_ADDED_BY_INDUSTRY":
        return False
    if benchmark=="FRED_DISTRIBUTED_BEA_REAL_GDP_VALUE_ADDED":
        return False
    if benchmark=="BEA_CHAIN_QUANTITY_REAL_GROSS_OUTPUT_484":
        # Conceptually closest, but exact coverage, vintage, source values,
        # and comparable weighting need independent review even then.
        return False
    raise ValueError("M30_UNSUPPORTED_BEA_BENCHMARK_CATEGORY")


def _prior(as_of:date) -> tuple[dict,dict]:
    book=_book()
    faults=validate_book(book,as_of=as_of)
    if faults:
        raise ValueError("M30_FROZEN_BEA_BENCHMARK_SOURCE_INVALID: "+"; ".join(faults))
    prior=m29_offline(as_of=as_of)
    if (prior["status"]!=M29_OFFLINE
        or prior["source_series_ids"]!=[
            "PCU484---484---","PCU484121484121","PCU484122484122"]
        or prior["actual_paid_customer_freight_invoices_observed"]!=0
        or prior["freight_recovery_market_tam_usd"] is not None
        or not prior["original_18_independent_pilot_requirements_still_unmet"]):
        raise ValueError("M30_PRIOR_BLS_INDEX_REVENUE_PROVENANCE_OR_PILOT_GATE_DRIFT")
    return book,prior


def report_shell(*,as_of:date) -> dict:
    b,prior=_prior(as_of)
    # Always recompute from anchored observations, not a claimed growth field.
    old_index=DEC(b["bea_real_value_added_2025_vintage"]["year_values"]["2024"])
    current=b["bea_real_value_added_2026_vintage"]["year_values"]
    old_growth=str((old_index-100).quantize(DEC("0.01"),rounding=ROUND_HALF_UP))
    new_growth=_percent(DEC(current["2024"]),DEC(current["2017"]))
    current_index=DEC(current["2024"])*100/DEC(current["2017"])
    difference_index=DEC(b["bea_alternative_current_index_secondary_web_observation"]["value_2024"])-old_index
    if old_growth!="1.41" or new_growth!="-2.42" or (
        current_index-DEC("97.585")
    ).copy_abs()>DEC("0.001") or difference_index!=DEC("-3.821"):
        raise ValueError("M30_BEA_2026_REVISION_NOT_REPRODUCED")
    proxy=next(x for x in prior["industry_comparisons"] if x["naics"]=="484")[
        "2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]
    if proxy!="1.18":
        raise ValueError("M30_BLS_PPI_REVENUE_INPUT_CHANGED")
    contrast=(DEC(proxy)-DEC(new_growth)).quantize(DEC("0.01"),rounding=ROUND_HALF_UP)
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,
        "status":OFFLINE,
        "bea_original_measure_definitions_verified_in_this_run":False,
        "bea_first_party_definitions_sha256_this_run":None,
        "bea_first_party_gross_output_home_sha256_this_run":None,
        "bea_484_real_gross_output_original_values_authenticated_this_run":False,
        "bea_484_real_gross_output_2017_2024_available_for_validation":False,
        "bea_gross_output_original_source_status":"HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED",
        "bea_source_definitions_first_party_ci_probe_success":True,
        "bea_gdp_value_added_secondary_source_provenance":"FRED_ALFRED_WEB_OBSERVED_NOT_DIRECT_BEA_ORIGINAL_DATA_REPLAY",
        "fred_bea_numeric_source_replayed_in_this_ci":False,
        "bea_value_added_2025_vintage_2024_index_2017eq100":str(old_index),
        "bea_value_added_2026_vintage_2024_index_2017eq100":str(DEC("97.585")),
        "bea_value_added_2025_vintage_2017_to_2024_growth_pct":old_growth,
        "bea_value_added_2026_vintage_2017_to_2024_growth_pct":new_growth,
        "bea_real_value_added_2024_index_revision_points":str(difference_index),
        "census_bls_484_price_adjusted_revenue_proxy_2017_2024_pct":proxy,
        "proxy_minus_bea_real_value_added_growth_points_noncomparable":str(contrast),
        "proxy_vs_bea_value_added_difference_is_model_error":False,
        "bea_value_added_gdp_and_real_gross_output_equivalent":False,
        "economic_measurement_compatibility_verdict":"HOLD_BEA_REAL_GROSS_OUTPUT_NOT_AUTHENTICATED_NO_QUANTITATIVE_MODEL_VALIDATION",
        "bea_real_gdp_2025_vintage_is_not_latest":True,
        "bea_real_gdp_value_added_cannot_certify_gross_revenue_deflator":True,
        "bea_original_measure_definition_receipt_sha256":canon_hash({
            "bea_definitions":b["bea_definitions_source"],
            "bea_gross_output":b["bea_gross_output_source"],
        }),
        "frozen_measure_catalog_receipt_sha256":canon_hash(b),
        "prior_m29_direct_bls_source_receipt_sha256":prior["receipt_sha256"],
        "real_invoice_rows_validated":0,
        "actual_adjudicated_customer_billing_errors":0,
        "recoverable_freight_market_tam_usd":None,
        "cash_collected_from_recoveries_usd":None,
        "real_buyers_proven":0,
        "external_marketing_or_carrier_contact_authorized":False,
        "all_18_real_customer_pilot_requirements_unmet":True,
        "scheduled_tasks_modified":False,
        "caveat":(
            "First-party BEA measurement definitions were downloaded in an "
            "earlier GitHub job, but the new original BEA real gross-output "
            "quantity index for NAICS 484 and 2017–2024 has not been downloaded "
            "or validated. Published GDP by industry is REAL VALUE ADDED "
            "(gross output minus intermediate inputs), NOT real gross output. "
            "FRED/ALFRED web-observed historical and Sept 2026 revised GDP "
            "value-added figures changed 2024 real GDP growth from +1.41% "
            "to -2.42%, but those are BEA-origin data redistributed by the "
            "Federal Reserve, not independent original BEA source bytes in this "
            "execution (FRED HTTP timed out). Mission 29's +1.18% annual-PPI "
            "price-adjusted Census employer-revenue proxy cannot be certified "
            "as genuine real gross output or rejected as wrong by comparing "
            "against real VALUE ADDED. The 3.60-point descriptive difference "
            "is not a model error, confidence interval, freight shipping volume, "
            "paid customer invoice sampling, legal overcharge or recoverable cash."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def _fetch_document(url:str) -> bytes:
    if url not in (
        "https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables",
        "https://www.bea.gov/data/industries/gross-output-by-industry",
    ):
        raise ValueError("M30_UNAUTHORIZED_BEA_SOURCE_URL")
    req=Request(url,headers={"User-Agent":"RETALLY-Lab14-BEA-Methods-Source-QA/1.0"})
    with urlopen(req,timeout=18) as resp:
        if resp.geturl()!=url:
            raise ValueError("M30_BEA_SOURCE_REDIRECTED")
        raw=resp.read(MAX_HTML+1)
    if len(raw)>MAX_HTML:
        raise ValueError("M30_BEA_DOCUMENT_BYTES_OVERSIZE")
    return raw


def verify_bea_methods(*,as_of:date,definition_html:bytes,gross_html:bytes)->dict:
    if any(type(raw) is not bytes or len(raw)>MAX_HTML or not raw
           for raw in (definition_html,gross_html)):
        raise ValueError("M30_INVALID_FIRST_PARTY_BEA_ORIGINAL_DOCUMENT_BYTES")
    definition=definition_html.decode("utf-8").lower()
    gross=gross_html.decode("utf-8").lower()
    for term in ("gross output by industry","value added by industry",
                 "chain-type quantity indexes for gross output",
                 "intermediate inputs"):
        if term not in definition:
            raise ValueError("M30_BEA_ORIGINAL_DEFINITIONS_MISSING:"+term)
    if "gross output by industry" not in gross or (
        "sales" not in gross or "industry" not in gross
    ):
        raise ValueError("M30_BEA_FIRST_PARTY_GROSS_OUTPUT_PAGE_NOT_IDENTIFIED")
    r=report_shell(as_of=as_of)
    r["status"]=VERIFIED
    r["bea_original_measure_definitions_verified_in_this_run"]=True
    r["bea_first_party_definitions_sha256_this_run"]=sha256(definition_html).hexdigest()
    r["bea_first_party_gross_output_home_sha256_this_run"]=sha256(gross_html).hexdigest()
    # Crucially DO NOT assert new real gross-output 2017–24 data were read:
    assert r["bea_484_real_gross_output_original_values_authenticated_this_run"] is False
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def blocked(*,as_of:date)->dict:
    r=report_shell(as_of=as_of)
    r["status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def render_html(report:dict)->str:
    def v(k): return escape(str(report[k]))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | BEA gross-output versus value-added decision gate</title>'
        '<style>body{font:16px/1.6 system-ui;background:#f7faf7;color:#16382a;'
        'margin:0}main{max-width:1080px;margin:32px auto;padding:20px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{border-bottom:1px solid #d4e2d5;padding:12px;text-align:left}'
        'small{color:#566e60}</style></head><body><main>'
        '<small>RETALLY / LAB 14 / MISSION 30 / INTERNAL RESEARCH ONLY</small>'
        '<h1>BEA real gross output is not industry GDP/value added</h1>'
        '<p>Official BEA measurement source status: <strong>'+v("status")+
        '</strong>. Real gross-output annual industry source: <strong>'+
        v("bea_gross_output_original_source_status")+'</strong>.</p>'
        '<table><thead><tr><th>Economic measurement</th>'
        '<th>2017–2024 change</th><th>Source and compatibility</th></tr></thead>'
        '<tbody><tr><th>Mission 29 Census revenues / BLS PPI</th><td>'+
        v("census_bls_484_price_adjusted_revenue_proxy_2017_2024_pct")+
        '%</td><td>Illustrative employer gross-revenue proxy, NOT real output</td></tr>'
        '<tr><th>BEA real GDP VALUE ADDED (2025 vintage)</th><td>'+
        v("bea_value_added_2025_vintage_2017_to_2024_growth_pct")+
        '%</td><td>Superseded; wrong vintage for current claims</td></tr>'
        '<tr><th>BEA real GDP VALUE ADDED (2026 revision)</th><td>'+
        v("bea_value_added_2026_vintage_2017_to_2024_growth_pct")+
        '%</td><td>Secondary-source, not gross output, FRED not CI-replayed</td></tr>'
        '<tr><th>BEA real GROSS OUTPUT</th><td>Not available</td>'
        '<td>Primary NAICS 484 quantity series not yet source-authenticated</td></tr>'
        '</tbody></table><p><strong>Compatibility verdict:</strong> '+
        v("economic_measurement_compatibility_verdict")+'</p>'
        '<p>'+v("caveat")+'</p>'
        '<p><a href="https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables">'
        'Official BEA real gross output vs value-added measurement definitions</a></p>'
        '</main></body></html>'
    )


def main() -> None:
    ap=argparse.ArgumentParser(description="BEA real-output source compatibility and vintage hold")
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--as-of-date",default=date.today().isoformat())
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-bea-definitions",action="store_true")
    args=ap.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_bea_definitions:
        try:
            definition=_fetch_document(
                "https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables"
            )
            gross=_fetch_document(
                "https://www.bea.gov/data/industries/gross-output-by-industry"
            )
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_bea_methods(as_of=as_of,definition_html=definition,gross_html=gross)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"bea_measure_compatibility.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (args.out/"bea_measure_compatibility.html").write_text(
        render_html(result),encoding="utf-8")
    print(json.dumps({
        "source_status":result["status"],
        "fresh_official_bea_methods_replayed":result[
            "bea_original_measure_definitions_verified_in_this_run"],
        "original_real_gross_output_authenticated":False,
        "bea_real_value_added_not_model_validation":True,
        "customer_invoice_or_recovery_proof":False,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
