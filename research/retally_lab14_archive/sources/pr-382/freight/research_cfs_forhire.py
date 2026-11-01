"""RETALLY Mission 16: strict offline original CFS sector-for-hire extraction.

No network, customers, carrier claims, invoices, market sizing, deployment, or
public performance. Original Census A18/A19 ZIP SHA-256 must match the previously
observed 2022 releases. All CI fixture archives are explicitly synthetic only.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
import re

from freight.research_cfs_archive_verifier import (
    _archive_members, _parse_tabular, _read_archive, digest_bytes,
)
from freight.research_cfs_industry_quality import (
    BOOK as M14_BOOK, OFFICIAL_PROFILES, INDEPENDENTLY_OBSERVED_TOTALS,
    validate_manifest,
)
from freight.research_evidence_gate import canon_hash
from freight.research_industry_comparison import build_comparison

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "research" / "CFS_FORHIRE_REPLAY_PLAN_20261011.json"
SCOPE = "RETALLY_LAB14_CFS_2022_FORHIRE_VERIFICATION_NOT_CI_REPLAYED"
INDUSTRIES = ("31-33", "42", "4931")
MODES = ("00", "111")
FILES = {
    "CF2200A18": ("SHIPDIST", "001", "CF2200A18.dat", 7312,
                  "a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5", 93390),
    "CF2200A19": ("SHIPWT", "01", "CF2200A19.dat", 6782,
                  "fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d", 107682),
}
BUCKETS = tuple(f"{n:02d}" for n in range(2, 11))
RESEARCH_DATES = ("2026-10-11", "2022")
FIELDS = {
    "schema_version", "scope", "observed_on", "year", "universe",
    "source_family", "source_files", "geo", "naics", "modes",
    "distance_nonoverlapping_buckets", "weight_nonoverlapping_buckets",
    "original_data_bytes_stored_in_git", "raw_original_sources_replayed_in_ci",
    "industry_forhire_values_independently_reproduced_here",
    "original_archive_publisher_digital_signature_verified",
    "real_ltl_invoice_values_measured", "real_ltl_buyer_or_recovery_claim_authorized",
    "no_new_lab", "exact_units", "release_rule", "acquisition_backlog",
}
FALSE_FLAGS = (
    "original_data_bytes_stored_in_git",
    "raw_original_sources_replayed_in_ci",
    "industry_forhire_values_independently_reproduced_here",
    "original_archive_publisher_digital_signature_verified",
    "real_ltl_invoice_values_measured",
    "real_ltl_buyer_or_recovery_claim_authorized",
)
REQUIRED_COLS = {
    "#GEOTYPE", "ST", "GEO_ID", "NAICS2017", "DMODE", "YEAR",
    "VAL", "VAL_F", "TON", "TON_F", "VAL_S", "VAL_S_F",
    "TON_S", "TON_S_F",
}


def _iso(raw: object) -> date:
    if type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError("NONCANONICAL_CFS_DATE")
    value = date.fromisoformat(raw)
    if raw != value.isoformat():
        raise ValueError("NONCANONICAL_CFS_DATE")
    return value


def _assert_valid_plan_inner(plan: dict, original: dict, *, as_of: date) -> list[str]:
    issues = []
    if type(plan) is not dict or plan.get("schema_version") != 1:
        return ["mission 16 expects a schema-1 source manifest"]
    if set(plan) != FIELDS or plan.get("scope") != SCOPE:
        issues.append("mission 16 provenance/scope fields changed")
    try:
        if _iso(plan.get("observed_on")) != date(2026, 10, 11):
            issues.append("original source observation date altered")
        if _iso(plan.get("observed_on")) > as_of:
            issues.append("source observation is in the future")
    except ValueError:
        issues.append("malformed source observation date")
    if plan.get("year") != "2022" or plan.get("universe") != "US_CFS_2022_SURVEYED_ORIGIN_ESTABLISHMENTS":
        issues.append("incompatible CFS vintage or survey universe")
    if plan.get("source_family") != "SINGLE_CFS_2022_SURVEY_NOT_INDEPENDENT_VALIDATION":
        issues.append("source lineage falsely certified as independent")
    if (plan.get("naics") != list(INDUSTRIES) or
        plan.get("modes") != list(MODES) or
        plan.get("distance_nonoverlapping_buckets") != list(BUCKETS) or
        plan.get("weight_nonoverlapping_buckets") != list(BUCKETS) or
        plan.get("geo") != {"geotype": "01", "geo_id": "0100000US", "state": "00"}):
        issues.append("national NAICS/mode/stratum source grain altered")
    for key in FALSE_FLAGS:
        if plan.get(key) is not False:
            issues.append(f"{key}: fabricated original data or commercial authority")
    if plan.get("no_new_lab") is not True:
        issues.append("a new Lab 15 is not authorized")
    if plan.get("exact_units") != {
        "value": "MILLIONS_USD_OF_GOODS_SHIPPED_NOT_INVOICE_SPEND",
        "weight": "THOUSAND_TONS_OF_GOODS_SHIPPED_NOT_LTL_FEES",
        "cv": "PERCENT_CFS_COEFFICIENT_OF_VARIATION_NOT_AUDIT_ERROR_RATE",
    }:
        issues.append("Census source units misrepresented")
    files = plan.get("source_files")
    if type(files) is not list or len(files) != 2:
        return issues + ["both fixed A18 and A19 original-source files required"]
    for i, file in enumerate(files):
        name = list(FILES)[i]
        _, total, member, count, sha, size = FILES[name]
        if (type(file) is not dict or set(file) !=
            {"id", "url", "member", "sha256", "bytes", "dimension", "total_stratum", "n_rows"}):
            issues.append(name + ": invalid source metadata schema")
            continue
        if (file.get("id") != name or
            file.get("url") != f"https://www2.census.gov/programs-surveys/cfs/data/2022/{name}.zip" or
            file.get("member") != member or file.get("sha256") != sha or
            type(file.get("bytes")) is not int or file.get("bytes") != size or
            file.get("dimension") != FILES[name][0] or
            file.get("total_stratum") != total or
            type(file.get("n_rows")) is not int or file.get("n_rows") != count):
            issues.append(name + ": original Census source identity or fingerprint changed")
    if (type(plan.get("release_rule")) is not str or len(plan["release_rule"]) < 160 or
        type(plan.get("acquisition_backlog")) is not list or
        len(plan["acquisition_backlog"]) != 4 or
        any(type(x) is not str or len(x) < 60 for x in plan["acquisition_backlog"])):
        issues.append("source gates or authorization limitations erased")
    issues.extend(validate_manifest(original, as_of=as_of))
    return issues


def validate_plan(plan: dict, original: dict, *, as_of: date) -> list[str]:
    try:
        return _assert_valid_plan_inner(plan, original, as_of=as_of)
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
        return ["malformed or adversarial industry source metadata"]


def _metric(value: str, flag: str, cv: str, cv_flag: str, *, name: str) -> dict:
    if any(type(x) is not str for x in (value, flag, cv, cv_flag)):
        raise ValueError("NONSTRING_CENSUS_ESTIMATE")
    flag, cv_flag = flag.strip(), cv_flag.strip()
    if flag not in ("", "S", "Z", "D", "N", "X", "-"):
        raise ValueError("UNKNOWN_CENSUS_FLAG")
    if cv_flag not in ("", "S", "Z", "D", "N", "X", "-"):
        raise ValueError("UNKNOWN_CENSUS_CV_FLAG")
    if flag:
        return {
            "name": name, "quantity": None, "flag": flag, "cv_percent": None,
            "quality": "ROUNDED_ZERO_UNKNOWN_EXACT_VALUE" if flag == "Z"
                       else "SUPPRESSED_OR_UNSUITABLE_UNPUBLISHED_ESTIMATE",
        }
    s = value.strip().replace(",", "")
    if not re.fullmatch(r"\d{1,15}", s):
        return {
            "name": name, "quantity": None, "flag": "",
            "cv_percent": None, "quality": "SOURCE_VALUE_MISSING_OR_INVALID",
        }
    try:
        number = Decimal(cv.strip()) if cv.strip() and not cv_flag else None
    except InvalidOperation:
        number = None
    if number is not None and (not number.is_finite() or number < 0 or number > 1000):
        number = None
    return {
        "name": name, "quantity": int(s), "flag": "",
        "cv_percent": str(number) if number is not None else None,
        "quality": "PUBLISHED_NUMERIC_ESTIMATE_CV_AVAILABLE"
                   if number is not None else
                   "PUBLISHED_NUMERIC_ESTIMATE_CV_UNAVAILABLE",
    }


def _ratio(num: int, den: int) -> str:
    if type(num) is not int or type(den) is not int or den <= 0 or num < 0 or num > den:
        raise ValueError("BAD_CFS_RATIO_DENOMINATOR")
    return str((Decimal(num)*100/Decimal(den)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP))


def _source_rows(raw: bytes, table: str, *, synthetic: bool) -> dict:
    if table not in FILES:
        raise ValueError("UNSUPPORTED_CFS_INDUSTRY_TABLE")
    if not isinstance(raw, bytes) or len(raw) > 2*1024*1024:
        raise ValueError("UNBOUNDED_OR_NONBINARY_ARCHIVE")
    axis, total, member, expected_count, sha, nbytes = FILES[table]
    if not synthetic and (len(raw) != nbytes or digest_bytes(raw) != sha):
        raise ValueError("OFFICIAL_CFS_ORIGINAL_ZIP_HASH_MISMATCH")
    members, archive = _archive_members(raw)
    if member not in {x["member"] for x in members}:
        raise ValueError("OFFICIAL_CFS_DAT_MEMBER_NOT_FOUND")
    header, rows = _parse_tabular(archive, member)
    if not (REQUIRED_COLS | {axis}) <= set(header):
        raise ValueError("MISSING_CFS_NAICS_MODE_CV_OR_STRATUM_COLUMN")
    if not synthetic:
        if len(rows) != expected_count or "|".join(header) != OFFICIAL_PROFILES[table]["header"]:
            raise ValueError("CFS_ORIGINAL_HEADER_OR_DATA_ROW_COUNT_CHANGED")
    selected = {}
    for row in rows:
        if (row["#GEOTYPE"] != "01" or row["ST"] != "00" or
            row["GEO_ID"] != "0100000US"):
            continue
        if row["YEAR"] != "2022":
            raise ValueError("CFS_NATIONAL_SOURCE_VINTAGE_MISMATCH")
        naics, mode, bucket = row["NAICS2017"], row["DMODE"], row[axis]
        if naics not in INDUSTRIES or mode not in MODES:
            continue
        if bucket != total and bucket not in BUCKETS:
            raise ValueError("UNEXPECTED_CFS_FORHIRE_STRATUM")
        key = (naics, mode, bucket)
        if key in selected:
            raise ValueError("DUPLICATED_CFS_INDUSTRY_MODE_BUCKET")
        selected[key] = {
            "naics": naics, "mode": mode, "axis": axis,
            "bucket": bucket,
            "value": _metric(row["VAL"], row["VAL_F"], row["VAL_S"],
                             row["VAL_S_F"], name="goods_value_million_usd"),
            "weight": _metric(row["TON"], row["TON_F"], row["TON_S"],
                              row["TON_S_F"], name="shipment_thousand_tons"),
        }
    missing = [
        (naics, mode, total) for naics in INDUSTRIES for mode in MODES
        if (naics, mode, total) not in selected
    ]
    if missing:
        raise ValueError("MISSING_INDUSTRY_MODE_TOTAL_FROM_ORIGINAL")
    return {
        "table_id":table, "axis":axis, "total_code":total,
        "raw_zip_sha256":digest_bytes(raw),
        "synthetic_data_only":synthetic,
        "source_rows_examined":len(rows),
        "selected":selected,
    }


def _value_if_clear(row: dict, measure: str) -> int | None:
    value = row[measure]
    return value["quantity"] if value["flag"] == "" else None


def _bucket_fraction(data: dict, naics: str, group: tuple[str,...]) -> dict:
    total = data["selected"][(naics,"111",data["total_code"])]
    total_value = _value_if_clear(total,"value")
    pieces = [
        data["selected"].get((naics,"111",code)) for code in BUCKETS
    ]
    if total_value is None or any(x is None for x in pieces):
        return {"percent_of_forhire_goods_value":None,
                "status":"HOLD_INCOMPLETE_OR_SUPPRESSED_BUCKET_FRAME"}
    values = [_value_if_clear(r,"value") for r in pieces]
    if any(v is None for v in values):
        return {"percent_of_forhire_goods_value":None,
                "status":"HOLD_INCOMPLETE_OR_SUPPRESSED_BUCKET_FRAME"}
    by_code=dict(zip(BUCKETS,values))
    if abs(sum(values)-total_value) > len(BUCKETS):
        return {"percent_of_forhire_goods_value":None,
                "status":"HOLD_BUCKET_DENOMINATOR_OR_ROUNDING_MISMATCH"}
    numerator=sum(by_code[k] for k in group)
    try:
        p=_ratio(numerator,total_value)
    except ValueError:
        return {"percent_of_forhire_goods_value":None,
                "status":"HOLD_ZERO_OR_INCOMPATIBLE_DENOMINATOR"}
    return {
        "percent_of_forhire_goods_value":p,
        "status":"DESCRIPTIVE_SOURCE_FRACTION_NO_STATISTICAL_CLAIM",
    }


def _reconcile(a18: dict, a19: dict) -> list[dict]:
    comparisons=[]
    for naics in INDUSTRIES:
        a={}
        for mode in MODES:
            x=a18["selected"][(naics,mode,"001")]
            y=a19["selected"][(naics,mode,"01")]
            same=all(
                x[k]["quantity"] == y[k]["quantity"] and
                x[k]["flag"] == y[k]["flag"]
                for k in ("value","weight")
            )
            if not same:
                raise ValueError("CFS_A18_A19_INCOMPATIBLE_NATIONAL_TOTALS")
            a[mode]=x
        all_mode=a["00"]
        reference=INDEPENDENTLY_OBSERVED_TOTALS[(naics,"00")]
        if (all_mode["value"]["quantity"],all_mode["weight"]["quantity"]) != reference:
            raise ValueError("CFS_M14_ALL_MODE_PUBLISHED_TOTAL_MISMATCH")
        forhire=a["111"]
        v=_value_if_clear(forhire,"value")
        t=_value_if_clear(forhire,"weight")
        allv=_value_if_clear(all_mode,"value")
        allt=_value_if_clear(all_mode,"weight")
        if v is not None and allv is not None and v > allv:
            raise ValueError("CFS_FORHIRE_EXCEEDS_ALL_MODE_VALUE")
        if t is not None and allt is not None and t > allt:
            raise ValueError("CFS_FORHIRE_EXCEEDS_ALL_MODE_WEIGHT")
        if any(v is None for v in (v,t,allv,allt)):
            value_pct=None
            ton_pct=None
            status="HOLD_UNPUBLISHABLE_OR_UNKNOWN_NUMERIC_ESTIMATE"
        else:
            value_pct=_ratio(v,allv)
            ton_pct=_ratio(t,allt)
            status="DESCRIPTIVE_FORHIRE_GOODS_SHARE_NOT_LTL"
        comparisons.append({
            "naics2017":naics,"survey_year":2022,
            "value_million_usd_goods_all_modes":allv,
            "weight_thousand_tons_all_modes":allt,
            "forhire_goods_value_million_usd":v,
            "forhire_weight_thousand_tons":t,
            "forhire_value_cv_percent":forhire["value"]["cv_percent"],
            "forhire_weight_cv_percent":forhire["weight"]["cv_percent"],
            "forhire_value_source_flag":forhire["value"]["flag"],
            "forhire_weight_source_flag":forhire["weight"]["flag"],
            "forhire_share_of_sector_shipped_goods_value_pct":value_pct,
            "forhire_share_of_sector_shipped_tonnage_pct":ton_pct,
            "distance_under_250_miles_goods_value_share":_bucket_fraction(
                a18,naics,("02","03","04")
            ),
            "shipment_weight_500_to_9999lbs_goods_value_share":_bucket_fraction(
                a19,naics,("05","06","07")
            ),
            "adjudication":status,
            "precision_limitation":"Ratio covariance and confidence interval not known; even unflagged CFS survey estimates cannot certify LTL freight spending.",
            "verified_paid_ltl_invoice_count":None,
            "recoverable_overcharges_usd":None,
            "ltl_only_modal_classification_established":False,
        })
    return comparisons


def replay_source_pair(*, a18_zip: bytes, a19_zip: bytes, as_of: date,
                       synthetic_test: bool=False) -> dict:
    """Only hash-matched original ZIPs can receive an ORIGINAL evidence label."""
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    base=json.loads(M14_BOOK.read_text(encoding="utf-8"))
    errors=validate_plan(plan,base,as_of=as_of)
    if errors:
        raise ValueError("INVALID_CFS_FORHIRE_PLAN: "+"; ".join(errors))
    a18=_source_rows(a18_zip,"CF2200A18",synthetic=synthetic_test)
    a19=_source_rows(a19_zip,"CF2200A19",synthetic=synthetic_test)
    comparisons=_reconcile(a18,a19)
    report={
        "schema_version":1,
        "scope":("LAB14_SYNTHETIC_FORHIRE_PARSER_TEST_NOT_REAL_CENSUS"
                 if synthetic_test else
                 "LAB14_CFS_ORIGINAL_HASH_MATCHED_FORHIRE_SECTOR_REPLAY"),
        "as_of":as_of.isoformat(),
        "original_Census_ZIPs_hash_replayed":not synthetic_test,
        "archive_sha256":{
            "CF2200A18":a18["raw_zip_sha256"],
            "CF2200A19":a19["raw_zip_sha256"],
        },
        "national_2022_mode_111_direct_sector_cells":len(comparisons),
        "industry_results":comparisons,
        "physical_zip_files_committed_to_repository":False,
        "same_underlying_CFS_survey_not_independent_datasets":True,
        "paid_ltl_invoice_spend_confirmed":False,
        "customer_demand_confirmed":False,
        "recovery_revenue_estimated":False,
        "customer_or_carrier_action_allowed":False,
        "no_new_lab_created":True,
        "existing_lab_number":14,
        "boundary":"Direct national for-hire CFS goods observations, only when derived from exact pinned raw source bytes. These are neither an LTL-only market nor customer invoices, recoverable overcharges, commercial results or legal authority.",
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def build_readiness(*, as_of: date) -> dict:
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    base=json.loads(M14_BOOK.read_text(encoding="utf-8"))
    errors=validate_plan(plan,base,as_of=as_of)
    if errors:
        raise ValueError("INVALID_CFS_FORHIRE_PLAN: "+"; ".join(errors))
    prior=build_comparison(as_of=as_of)
    report={
        "schema_version":1,"as_of":as_of.isoformat(),
        "scope":"LAB14_CFS_FORHIRE_SECTOR_REPLAY_AWAITING_ORIGINAL_ZIPS",
        "plan_receipt_sha256":canon_hash(plan),
        "original_cfs_industry_receipt_sha256":canon_hash(base),
        "mission15_national_goods_comparison_receipt_sha256":prior["receipt_sha256"],
        "original_source_hashes_verified_remotely":{x["id"]:x["sha256"] for x in plan["source_files"]},
        "source_files_replayed_in_ci":0,
        "source_industry_forhire_rows_reproduced_in_ci":0,
        "sectors_with_verified_forhire_numerators":0,
        "sectors_with_published_quality_controlled_CVs":0,
        "source_total_rows_to_reconcile":12,
        "industry_research_targets":[
            {
                "naics2017":c,"source_mode_code":"111",
                "forhire_value_million_usd":None,
                "forhire_weight_thousand_tons":None,
                "goods_value_share_pct":None,
                "under_250mi_goods_value_pct":None,
                "weight_500_9999lbs_goods_value_pct":None,
                "reason":"Original CFS A18/A19 industry x for-hire direct rows not independently replayed in this GitHub run.",
            }
            for c in INDUSTRIES
        ],
        "approval":"BLOCKED_NO_INDUSTRY_MODE_SOURCE_BYTE_REPLAY",
        "no_inferred_ltl_only_transport_classification":True,
        "no_real_customer_invoice_records_used":True,
        "no_paid_ltl_invoice_spend_available":True,
        "no_recoverable_overcharges_observed":True,
        "no_unauthorized_external_actions":True,
        "source_fetch_or_scheduler_enabled":False,
        "existing_lab_number":14,
        "new_lab_created":False,
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def render_html(report: dict) -> str:
    pieces=[]
    for r in report.get("industry_results",report.get("industry_research_targets",[])):
        label=r["naics2017"]
        value=r.get("forhire_goods_value_million_usd",r.get("forhire_value_million_usd"))
        pieces.append(
            "<tr><th>"+escape(label)+"</th><td>"+
            escape(str(value) if value is not None else "Unverified")+
            "</td><td>"+escape(str(r.get("adjudication","Original source replay pending")))+
            "</td></tr>"
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | For-Hire Evidence Gate</title><style>'
        '*{box-sizing:border-box}body{background:#f6f9f7;color:#15352a;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0}'
        'main{max-width:1040px;margin:auto;padding:34px 20px 64px}'
        'h1{font-size:clamp(30px,5vw,46px);line-height:1.12}'
        'table{width:100%;border-collapse:collapse}td,th{text-align:left;'
        'padding:12px;border-bottom:1px solid #dce8df}'
        'article{background:white;border:1px solid #dce8df;border-radius:15px;padding:22px}'
        'small{font-size:12px;color:#507063}</style></head>'
        '<body><main><small>RETALLY / LAB 14 / MISSION 16</small>'
        '<h1>For-hire industry evidence must come from the original source.</h1>'
        '<p>All-mode goods volume is known; NAICS-specific for-hire goods and'
        ' distance/weight distributions require exact A18/A19 original ZIP'
        ' replay. Suppression, missing CV and NAICS hierarchy must remain'
        ' visible. No LTL-only invoices, buyer demand or recoveries are'
        ' established.</p><article><h2>Industry verification</h2>'
        '<table><thead><tr><th>NAICS 2017</th><th>For-hire goods value ($m)</th>'
        '<th>Research status</th></tr></thead><tbody>'+
        "".join(pieces)+'</tbody></table>'
        '<p>Public source ZIP downloads are never performed by CI. Synthetic'
        ' parser checks never authorize real customer or commercial claims.</p>'
        '</article><footer><small>Integrity receipt: '+
        escape(report["receipt_sha256"])+
        ' (local consistency, not Census publisher signature)</small></footer>'
        '</main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--a18-zip",type=Path)
    parser.add_argument("--a19-zip",type=Path)
    args=parser.parse_args()
    if bool(args.a18_zip)!=bool(args.a19_zip):
        parser.error("both original ZIPs are required together")
    result=(
        replay_source_pair(
            a18_zip=_read_archive(args.a18_zip),
            a19_zip=_read_archive(args.a19_zip),
            as_of=args.as_of_date,
        )
        if args.a18_zip else build_readiness(as_of=args.as_of_date)
    )
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"cfs_forhire_replay.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"cfs_forhire_replay.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "scope":result["scope"],
        "source_rows_reproduced_in_ci":result.get("source_industry_forhire_rows_reproduced_in_ci",0),
        "receipt":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
