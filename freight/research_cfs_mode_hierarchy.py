"""Mission 16: bounded, source-linked CFS 2022 for-hire truck research (Lab 14).

The raw selected rows came from a public GitHub mirror, not a re-download of
the originally browser-observed Census ZIP. Only exact national Census 2022
NAICS × DMODE 111 rows are admitted. These goods-shipped survey values do NOT
measure LTL-only freight bills, payable rates, buyer eligibility or recoveries.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha1
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_industry_comparison import build_comparison

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "research" / "CFS_FORHIRE_NAICS_BUCKETS_20261011.json"
SCOPE = "LAB14_CFS_ORIGINAL_SURVEY_GRAIN_GITHUB_MIRROR_RESEARCH_ONLY"
REPORT_SCOPE = "LAB14_CFS_FORHIRE_MODE_RESEARCH_NOT_LTL_BILLING"
ORIGINAL_SURVEY_LINEAGE = "A18_A19_SHARED_CFS_2022_SURVEY_NOT_TWO_INDEPENDENT_SAMPLES"
EXPECTED_BOOK_BLOB_SHA1 = "f433ea77903596501ac51dc3baad99e40ce8db84"
NAICS_CODES = ("31-33", "42", "4931")
NAICS_LABELS = {
    "31-33": "Manufacturing establishments",
    "42": "Wholesale trade establishments",
    "4931": "CFS 4931/484 combined reported category (NOT only warehouses)",
}
EXPECTED_TOTALS = {
    "31-33": (3799845, 1740594, "1.8", "2.3"),
    "42": (3341533, 1348938, "3.2", "5.3"),
    "4931": (635089, 140628, "7.5", "9.8"),
}
TABLES = {
    "CF2200A18": {
        "axis": "SHIPDIST",
        "total": "001",
        "codes": ("001", "02", "03", "04", "05", "06", "07", "08", "09", "10"),
        "original_zip_sha256": "a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5",
        "original_zip_size_bytes": 93390,
        "mirror_git_blob_sha1": "5e80c8e9a9242fbf776ed141abaf22e6cd16a5e4",
        "mirror_file_bytes": 1040806,
        "mirror_file_row_count": 7312,
    },
    "CF2200A19": {
        "axis": "SHIPWT",
        "total": "01",
        "codes": ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10"),
        "original_zip_sha256": "fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d",
        "original_zip_size_bytes": 107682,
        "mirror_git_blob_sha1": "c781c71eab0898d7939a0eba60966b9bedafebd7",
        "mirror_file_bytes": 1017567,
        "mirror_file_row_count": 6782,
    },
}
MANIFEST_FLAGS = {
    "ci_original_official_archives_downloaded",
    "actual_customer_or_invoice_files_used",
    "public_recovery_market_or_buyer_rankings_authorized",
    "real_ltl_invoice_spend_known",
    "publisher_signatures_validated",
    "third_party_mirror_is_same_as_verified_original_zip_bytes",
    "commercial_claims_allowed",
    "new_lab_created",
    "noncomparable_or_suppressed_cells_zeroed",
}
BOOK_KEYS = {
    "schema_version", "scope", "observed_on", "survey_year", "geography",
    "mode_code", "mode_label", "source_independence", "data_provenance",
    "source_mirror_repository", "source_government_notes",
    "source_methodology", "combined_naics_note", "census_2017_2022_notes",
    "source_tables", "selected_source_rows", *MANIFEST_FLAGS,
}
SOURCE_FIELDS = {
    "table_id", "axis", "total_stratum_code", "source_official_zip_url",
    "browser_observed_original_zip_sha256",
    "browser_observed_original_zip_size_bytes", "mirror_raw_file_url",
    "mirror_git_blob_sha1", "mirror_file_bytes", "mirror_file_row_count",
    "source_lineage_expected", "raw_mirror_bytes_not_stored_in_research_repo",
    "exact_original_raw_dat_hash_unverified", "unique_selected_sector_count",
    "source_row_count_in_excerpt",
}
ROW_FIELDS = {
    "table_id", "naics2017", "sector_label", "mode_code",
    "stratum_code", "stratum_label", "goods_value_million_usd",
    "goods_value_flag", "tonnage_thousand_tons", "tonnage_flag",
    "goods_value_cv_pct", "goods_value_cv_flag",
    "tonnage_cv_pct", "tonnage_cv_flag",
}
EXPECTED_FLAGGED = {
    ("CF2200A18", "4931", "09", "tonnage_flag"): "S",
    ("CF2200A19", "4931", "10", "goods_value_flag"): "S",
    ("CF2200A19", "4931", "10", "tonnage_flag"): "S",
}
EXPIRY_DAYS = 90


def _git_blob_sha1(b: bytes) -> str:
    return sha1(b"blob " + str(len(b)).encode("ascii") + b"\0" + b).hexdigest()


def _iso(text: object) -> date:
    if type(text) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("ISO date required")
    result = date.fromisoformat(text)
    if result.isoformat() != text:
        raise ValueError("canonical ISO date required")
    return result


def _meaningful(text: object, minimum: int = 20, maximum: int = 1000) -> bool:
    return type(text) is str and minimum <= len(text.strip()) <= maximum


def _whole(number: object) -> bool:
    return type(number) is int and 0 <= number <= 25_000_000


def _cv(raw: object, raw_flag: object) -> Decimal | None:
    if raw_flag != "":
        if raw_flag not in ("S", "Z", "N"):
            raise ValueError("UNRECOGNIZED_CENSUS_CV_FLAG")
        return None
    if type(raw) is not str or not re.fullmatch(r"\d{1,3}(?:\.\d{1,3})?", raw):
        raise ValueError("INVALID_CENSUS_CV_FIELD")
    cv = Decimal(raw)
    if not cv.is_finite() or cv > 100:
        raise ValueError("IMPOSSIBLE_CENSUS_CV")
    return cv


def _pct(a: int, b: int) -> str:
    if not _whole(a) or not _whole(b) or b == 0 or a > b:
        raise ValueError("CFS_NUMERATOR_DENOMINATOR_OR_UNIT_MISMATCH")
    return str((Decimal(a) * 100 / Decimal(b)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ))


def _validate_inner(book: dict, *, as_of: date) -> list[str]:
    errors=[]
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["invalid versioned CFS source snapshot"]
    if set(book) != BOOK_KEYS or book.get("scope") != SCOPE:
        errors.append("source manifest structure or research boundary altered")
    try:
        if _iso(book.get("observed_on")) != date(2026, 10, 11):
            errors.append("public mirror capture date shifted")
        if _iso(book.get("observed_on")) > as_of:
            errors.append("mirror capture date cannot be in the future")
    except ValueError:
        errors.append("invalid source observation date")
    if type(book.get("survey_year")) is not int or book["survey_year"] != 2022:
        errors.append("incompatible Census survey vintage")
    if book.get("geography") != {
        "#GEOTYPE":"01", "GEO_ID":"0100000US", "ST":"00",
        "GEO_LABEL":"United States",
    }:
        errors.append("geographic population/geography changed")
    if book.get("mode_code") != "111" or book.get("mode_label") != (
        "For-hire truck (includes TL and LTL; not LTL-only)"
    ):
        errors.append("for-hire trucking cannot be called LTL-only")
    for flag in MANIFEST_FLAGS:
        if book.get(flag) is not False:
            errors.append("unapproved data, publisher, source or money claim: "+flag)
    if book.get("source_independence") != ORIGINAL_SURVEY_LINEAGE:
        errors.append("one shared CFS survey must not be double-counted")
    if book.get("source_mirror_repository") != "https://github.com/noobifyLol/CAD_AI":
        errors.append("unverified source mirror identity")
    if book.get("source_government_notes") != "https://data.census.gov/table/CFSAREA2022.CF2200A18":
        errors.append("source caveat official URL replaced")
    if book.get("source_methodology") != (
        "https://www2.census.gov/programs-surveys/cfs/technical-documentation/"
        "methodology/2022%20Commodity%20Flow%20Survey%20Methodology.pdf"
    ):
        errors.append("original Census methodology link absent")
    if not _meaningful(book.get("combined_naics_note"), 100) or (
        "NAICS 484" not in book["combined_naics_note"] or
        "4931" not in book["combined_naics_note"] or
        "captive" not in book["combined_naics_note"]
    ):
        errors.append("mixed 4931/484 NAICS caveat must remain conspicuous")
    if not _meaningful(book.get("census_2017_2022_notes"), 100):
        errors.append("CFS distance and category changes must be declared")
    if not _meaningful(book.get("data_provenance"), 80):
        errors.append("third-party mirror cannot masquerade as authentic ZIP bytes")

    tables = book.get("source_tables")
    if type(tables) is not list or len(tables) != 2:
        return errors + ["both original 2022 CFS table metadata sources required"]
    seen_tables=set()
    for obj in tables:
        if type(obj) is not dict or set(obj) != SOURCE_FIELDS:
            errors.append("unexpected or omitted Census source table metadata")
            continue
        t = obj.get("table_id")
        if t not in TABLES or t in seen_tables:
            errors.append("repeated or unknown Census table source")
            continue
        seen_tables.add(t)
        exp=TABLES[t]
        expected_path=f"outputs/phase2b_healthcare_tam_som/cfs_raw/{t}/{t}.dat"
        if (obj.get("axis") != exp["axis"] or
            obj.get("total_stratum_code") != exp["total"] or
            obj.get("source_official_zip_url") !=
                f"https://www2.census.gov/programs-surveys/cfs/data/2022/{t}.zip" or
            obj.get("browser_observed_original_zip_sha256") != exp["original_zip_sha256"] or
            obj.get("browser_observed_original_zip_size_bytes") != exp["original_zip_size_bytes"] or
            obj.get("mirror_raw_file_url") !=
                "https://raw.githubusercontent.com/noobifyLol/CAD_AI/master/"+expected_path or
            obj.get("mirror_git_blob_sha1") != exp["mirror_git_blob_sha1"] or
            obj.get("mirror_file_bytes") != exp["mirror_file_bytes"] or
            obj.get("mirror_file_row_count") != exp["mirror_file_row_count"] or
            obj.get("source_lineage_expected") !=
                "BOTH_TABLES_REPRESENT_SAME_2022_CFS_UNIVERSE" or
            obj.get("raw_mirror_bytes_not_stored_in_research_repo") is not True or
            obj.get("exact_original_raw_dat_hash_unverified") is not True or
            obj.get("unique_selected_sector_count") != 3 or
            obj.get("source_row_count_in_excerpt") != 30):
            errors.append("falsified original/mirror source identity, units or complete row grain")
    if seen_tables != set(TABLES):
        errors.append("missing original Census table")

    rows=book.get("selected_source_rows")
    if type(rows) is not list or len(rows) != 60:
        return errors + ["all sixty official-formatted mode 111 source cells required"]
    seen_rows=set()
    for i, obj in enumerate(rows):
        if type(obj) is not dict or set(obj) != ROW_FIELDS:
            errors.append(f"row {i}: unknown raw source columns/customer data")
            continue
        t,n,b=obj.get("table_id"),obj.get("naics2017"),obj.get("stratum_code")
        if t not in TABLES or n not in NAICS_CODES or type(b) is not str:
            errors.append(f"row {i}: wrong Census category or version")
            continue
        if b not in TABLES[t]["codes"]:
            errors.append(f"row {i}: wrong weight/distance bucket")
        key=(t,n,b)
        if key in seen_rows:
            errors.append(f"row {i}: duplicate NAICS/mode/stratum key")
        seen_rows.add(key)
        if obj.get("mode_code") != "111" or not _meaningful(obj.get("stratum_label"), 2, 120):
            errors.append(f"row {i}: mode/stratum label unsafe")
        if not _meaningful(obj.get("sector_label"), 6, 120):
            errors.append(f"row {i}: missing source NAICS label")
        for measure,flag in (
            ("goods_value_million_usd","goods_value_flag"),
            ("tonnage_thousand_tons","tonnage_flag"),
        ):
            val=obj.get(measure)
            if not _whole(val):
                errors.append(f"row {i}: invalid numeric goods/tonnage source unit")
            expected=EXPECTED_FLAGGED.get((t,n,b,flag),"")
            if obj.get(flag) != expected:
                errors.append(f"row {i}: source Census S/Z quality flag altered")
        for value_flag,raw,cv_flag in (
            ("goods_value_flag","goods_value_cv_pct","goods_value_cv_flag"),
            ("tonnage_flag","tonnage_cv_pct","tonnage_cv_flag"),
        ):
            try:
                v=_cv(obj.get(raw),obj.get(cv_flag))
                if obj.get(value_flag) and v is not None:
                    errors.append(f"row {i}: published suppressed cell cannot claim CV")
            except (ValueError,InvalidOperation):
                errors.append(f"row {i}: corrupt coefficient-of-variation")
        # CFS raw nonpublishable "0" is a numeric placeholder, not an exact zero.
        if (obj.get("goods_value_flag") == "S" and obj.get("goods_value_million_usd") != 0 or
            obj.get("tonnage_flag") == "S" and obj.get("tonnage_thousand_tons") != 0):
            errors.append(f"row {i}: inconsistent S source placeholder")
    expected_rows={(t,n,b) for t,meta in TABLES.items()
                   for n in NAICS_CODES for b in meta["codes"]}
    if seen_rows != expected_rows:
        errors.append("source inventory does not cover three NAICS x ten buckets x both tables")
    for t,spec in TABLES.items():
        for n in NAICS_CODES:
            totals=[r for r in rows if isinstance(r,dict) and
                    (r.get("table_id"),r.get("naics2017"),r.get("stratum_code"))
                    ==(t,n,spec["total"])]
            if len(totals) != 1:
                errors.append("one clean total per Census table and NAICS required")
                continue
            row=totals[0]; val,ton,cvv,cvt=EXPECTED_TOTALS[n]
            if (row.get("goods_value_million_usd")!=val or
                row.get("tonnage_thousand_tons")!=ton or
                row.get("goods_value_flag") != "" or
                row.get("tonnage_flag") != "" or
                row.get("goods_value_cv_pct")!=cvv or
                row.get("tonnage_cv_pct")!=cvt):
                errors.append("Census mode 111 total disagrees across A18/A19 or source receipts")
    return errors


def validate_catalog(book: dict, *, as_of: date) -> list[str]:
    try:
        return _validate_inner(book,as_of=as_of)
    except (TypeError,AttributeError,ValueError,InvalidOperation,KeyError,OverflowError):
        return ["malformed, impossible or untrusted Census hierarchy source book"]


def _qualified(row: dict, metric: str) -> int | None:
    if metric == "value":
        return (row["goods_value_million_usd"] if row["goods_value_flag"] == ""
                else None)
    return (row["tonnage_thousand_tons"] if row["tonnage_flag"] == "" else None)


def _partition(rows: list[dict], total: int, metric: str) -> dict:
    eligible=[r for r in rows if _qualified(r,metric) is not None]
    suppressed=[r["stratum_code"] for r in rows if _qualified(r,metric) is None]
    summed=sum(_qualified(r,metric) for r in eligible)
    # Each published integer rounding can differ by one. Never derive a hidden
    # suppressed cell by subtracting visible sums from a published total.
    delta=summed-total if not suppressed else None
    if not suppressed and abs(delta)>len(rows):
        raise ValueError("SOURCE_PARTITION_ARITHMETIC_RECONCILIATION_FAILED")
    return {
        "sub_bucket_count":len(rows),
        "unflagged_bucket_count":len(eligible),
        "suppressed_or_qualified_buckets":suppressed,
        "all_bucket_totals_publishable":not bool(suppressed),
        "all_unflagged_rows_sum_million_or_thousand":summed,
        "difference_from_total_due_to_published_rounding":delta,
        "hidden_residual_imputed":False,
        "partition_is_statistically_certified":False,
    }


def _component_pct(buckets: list[dict], codes: tuple[str,...],
                   total: int, metric: str) -> str | None:
    rows=[r for r in buckets if r["stratum_code"] in codes]
    if len(rows)!=len(codes) or any(_qualified(r,metric) is None for r in rows):
        return None
    numerator=sum(_qualified(r,metric) for r in rows)
    return _pct(numerator,total)


def _read_book() -> dict:
    raw=BOOK.read_bytes()
    if _git_blob_sha1(raw) != EXPECTED_BOOK_BLOB_SHA1:
        raise ValueError("SOURCE_ROW_SNAPSHOT_BLOB_CHANGED_RECHECK_CENSUS_MIRROR")
    return json.loads(raw.decode("utf-8"))


def build_forhire(*,as_of:date,book:dict|None=None,
                  prior:dict|None=None) -> dict:
    if book is None:
        book=_read_book()
    if prior is None:
        prior=build_comparison(as_of=as_of)
    problems=validate_catalog(book,as_of=as_of)
    if problems:
        raise ValueError("INVALID_CFS_MODE_SOURCE: "+"; ".join(problems))
    if (prior.get("scope") != "LAB14_DIRECT_CFS_INDUSTRY_COMPARISON_RESEARCH_ONLY" or
        prior.get("receipt_sha256") != canon_hash({
            k:v for k,v in prior.items() if k!="receipt_sha256"
        }) or
        prior.get("n_industries") != 3 or
        prior.get("actual_invoice_bills_counted") != 0 or
        prior.get("ltl_market_tam_usd") is not None or
        prior.get("same_survey_not_independent_sources") is not True):
        raise ValueError("SOURCE_M15_RESEARCH_DENOMINATOR_UNTRUSTED")
    prior_sectors={r["naics2017"]:r for r in prior["industry_comparisons"]}
    if set(prior_sectors)!=set(NAICS_CODES):
        raise ValueError("M15_INDUSTRY_NAICS_MISMATCH")
    all_rows=book["selected_source_rows"]
    sector_results=[]
    for n in NAICS_CODES:
        per_table={}
        for t,meta in TABLES.items():
            arr=[r for r in all_rows if r["table_id"]==t and r["naics2017"]==n]
            total=next(x for x in arr if x["stratum_code"]==meta["total"])
            other=[r for r in arr if r is not total]
            per_table[t]=(total,other)
        a18=per_table["CF2200A18"][0]
        a19=per_table["CF2200A19"][0]
        for key in (
            "goods_value_million_usd","tonnage_thousand_tons",
            "goods_value_flag","tonnage_flag",
            "goods_value_cv_pct","tonnage_cv_pct",
        ):
            if a18[key]!=a19[key]:
                raise ValueError("A18_A19_TOTALS_OR_COEFFICIENTS_DISAGREE")
        val,ton=a18["goods_value_million_usd"],a18["tonnage_thousand_tons"]
        ref=prior_sectors[n]
        all_val=ref["value_million_usd_goods_shipped"]
        all_ton=ref["weight_thousand_tons_goods_shipped"]
        if val>all_val or ton>all_ton:
            raise ValueError("FORHIRE_SECTOR_MORE_THAN_ALL_MODES")
        d=per_table["CF2200A18"][1]
        w=per_table["CF2200A19"][1]
        sector_results.append({
            "naics2017":n,
            "label":NAICS_LABELS[n],
            "combined_naics_484_and_captive_warehouse_population":n=="4931",
            "survey_year":2022,"mode_code":"111",
            "mode_name":"FOR_HIRE_TRUCK_NOT_LTL_ONLY",
            "all_modes_goods_value_million_usd":all_val,
            "for_hire_goods_value_million_usd":val,
            "for_hire_goods_value_pct_of_this_sectors_all_mode_goods":_pct(val,all_val),
            "all_modes_weight_thousand_tons":all_ton,
            "for_hire_weight_thousand_tons":ton,
            "for_hire_weight_pct_of_sector_all_mode_weight":_pct(ton,all_ton),
            "published_for_hire_value_cv_pct":a18["goods_value_cv_pct"],
            "published_for_hire_weight_cv_pct":a18["tonnage_cv_pct"],
            "cv_not_statistical_significance_or_margin_of_error":True,
            "distance_less_than_250mi_for_hire_goods_value_share_pct":
                _component_pct(d,("02","03","04"),val,"value"),
            "distance_measurement":"GREAT_CIRCLE_DISTANCE_NOT_ROAD_MILES",
            "shipment_500_to_9999lbs_for_hire_goods_value_share_pct":
                _component_pct(w,("05","06","07"),val,"value"),
            "weight_measurement":"SHIPMENT_SIZE_BANDS_NOT_LTL_CLASSIFICATION",
            "distance_by_goods_value_partition":_partition(d,val,"value"),
            "distance_by_weight_partition":_partition(d,ton,"weight"),
            "shipment_size_by_goods_value_partition":_partition(w,val,"value"),
            "shipment_size_by_weight_partition":_partition(w,ton,"weight"),
            "within_sector_forhire_ltl_only_paid_invoice_spend_usd":None,
            "customer_claims_or_recoveries_count":0,
            "buyer_demand_proven":False,
            "joint_distance_and_weight_distribution_known":False,
            "joint_distribution_cannot_be_computed_from_separate_marginals":True,
        })
    qa={
        "source_selected_rows":len(all_rows),
        "source_tables":len(TABLES),
        "survey_independence":"SAME_CFS2022_SURVEY_A18_A19_MARGINALS",
        "mirror_reference_only":True,
        "mirror_row_reproduction_against_original_census_dat_completed":False,
        "nationwide_primary_sources_observed_in_browser_previous_mission":True,
        "original_zip_hashes_carried_forward_not_recomputed_this_run":True,
        "all_twelve_total_cells_agree_between_mirrors":True,
        "suppressed_example_distance_4931_bucket09_weight":"S",
        "suppressed_example_shipment_weight_4931_bucket10_goods_and_weight":"S",
        "rounding_tolerance_units":"ONE_PUBLISHED_INTEGER_PER_BUCKET;NO_RESIDUAL_IMPUTATION",
        "no_ltl_market_revenue_or_actual_customer_validation":True,
    }
    report={
        "schema_version":1,
        "scope":REPORT_SCOPE,
        "as_of":as_of.isoformat(),
        "frozen_source_row_receipt_sha256":canon_hash(book),
        "prior_m15_receipt_sha256":prior["receipt_sha256"],
        "source_provenance":"THIRD_PARTY_MIRROR_SOURCE_CROSSCHECKED_BETWEEN_A18_A19_AND_M14_TOTALS_NOT_OFFICIAL_ZIP_BYTE_REPLAY",
        "census_2022_quality_note_4931_includes_naics_484":True,
        "original_census_methodology_noted":True,
        "three_sector_forhire_results":sector_results,
        "qa":qa,
        "source_primary_zip_bytes_replayed_in_this_ci_run":False,
        "physical_original_Census_ZIP_repo_stored":False,
        "actual_paid_ltl_invoices_observed":0,
        "market_size_or_recovery_rates_established":False,
        "public_sector_ranking_or_marketing_claims_allowed":False,
        "carrier_contact_or_money_actions_authorized":False,
        "automatic_external_source_fetch_or_schedule":False,
        "existing_lab_number":14,
        "new_lab_created":False,
        "caveat":(
            "Shipment goods value, mode 111 for-hire movements and weight/distance "
            "marginals are NOT LTL carrier invoice spend or jointly distributed "
            "route/size records. Reported NAICS 4931 includes NAICS 484 truck "
            "transportation and only captive warehousing auxiliaries in this CFS "
            "frame; public-service warehouses excluded. Original Census ZIP bytes "
            "were inspected in earlier read-only browser work, but these extra "
            "mirror sector bucket rows are not independently rehashed against "
            "publisher ZIP. Suppressed values are unknown, not zero."
        ),
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def render_html(report: dict) -> str:
    def show(x):return "Not established" if x is None else escape(str(x))
    tr="".join(
        "<tr><th>"+escape(r["label"])+"</th><td>"+
        f"{r['for_hire_goods_value_million_usd']:,}"+"</td><td>"+
        show(r["for_hire_goods_value_pct_of_this_sectors_all_mode_goods"])+
        "%</td><td>"+show(r["distance_less_than_250mi_for_hire_goods_value_share_pct"])+
        "%</td><td>"+show(r["shipment_500_to_9999lbs_for_hire_goods_value_share_pct"])+
        "%</td></tr>" for r in report["three_sector_forhire_results"]
    )
    warnings="".join(
        '<article><h3>'+escape(r["label"])+'</h3><p>Published value CV '+
        escape(r["published_for_hire_value_cv_pct"])+
        '%; weight CV '+escape(r["published_for_hire_weight_cv_pct"])+
        '% (not an invoice-error confidence interval).</p><p>'+
        ('**Census 4931 also groups truck transportation NAICS 484.** '
         if r["combined_naics_484_and_captive_warehouse_population"] else '')+
        'Distance buckets fully publishable by value: '+
        ('yes' if r["distance_by_goods_value_partition"]["all_bucket_totals_publishable"] else 'no')+
        '; by tonnage: '+
        ('yes' if r["distance_by_weight_partition"]["all_bucket_totals_publishable"] else 'no')+
        '. Weight-category buckets fully publishable by value: '+
        ('yes' if r["shipment_size_by_goods_value_partition"]["all_bucket_totals_publishable"] else 'no')+
        '.</p></article>'
        for r in report["three_sector_forhire_results"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Census For-Hire Source Detail</title><style>'
        '*{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;'
        'background:#f6f9f7;color:#1d352a;margin:0}'
        'main{max-width:1130px;margin:auto;padding:30px 18px 70px}'
        'h1{font-size:clamp(31px,5vw,47px);line-height:1.1}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{padding:13px 10px;border-bottom:1px solid #d7e5db;text-align:left}'
        'article{border:1px solid #dce8dd;background:white;border-radius:12px;'
        'padding:17px;margin:14px 0}small{color:#577265;font-size:12px}'
        '</style></head><body><main><small>RETALLY / LAB 14 / MISSION 16 '
        '/ SOURCE RESEARCH ONLY</small><h1>For-hire trucking is not LTL billing.</h1>'
        '<p>Mode 111 goods-shipment estimates by origin-industry NAICS, '
        'cross-matched in two public Census-format tables mirrored on GitHub. '
        'The source is NOT an original Census ZIP byte replay in CI; '
        'some quality-flagged strata cannot be summed, and published CVs do '
        'not measure customer invoicing error.</p><table><thead><tr>'
        '<th>Reported CFS sector</th><th>For-hire goods value ($m)</th>'
        '<th>For-hire share of all-mode goods</th>'
        '<th>Value in trips below 250 miles</th>'
        '<th>Value in shipment size 500–9,999 lbs</th>'
        '</tr></thead><tbody>'+tr+'</tbody></table>'
        '<p>The two percentage distributions are separate marginals, '
        'NOT the proportion of shipments satisfying both criteria. Distances '
        'are great-circle miles, NOT traveled road miles; shipment weight '
        'alone does not identify LTL service.</p>'+warnings+
        '<p><b>Missing:</b> actual paid LTL bills, shipper permissions, '
        'verified overcharges, recoverable cash and buyer demand. No '
        'market or marketing claims are authorized.</p>'
        '<footer><small>Local research integrity receipt '+
        escape(report["receipt_sha256"])+
        ' — not a publisher-signed source or independent audited customer outcome.'
        '</small></footer></main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    r=build_forhire(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"cfs_forhire_industry.json").write_text(
        json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.out/"cfs_forhire_industry.html").write_text(
        render_html(r),encoding="utf-8")
    print(json.dumps({
        "scope":r["scope"],"sectors":len(r["three_sector_forhire_results"]),
        "source_rows":r["qa"]["source_selected_rows"],
        "customer_records":r["actual_paid_ltl_invoices_observed"],
        "receipt":r["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
