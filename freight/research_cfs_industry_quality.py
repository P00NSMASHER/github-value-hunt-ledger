"""RETALLY Lab 14 Mission 14: CFS industry-mode data quality and provenance.

Offline only. The U.S. Census 2022 CF2200A18 and A19 tables measure
commodity-shipment VALUE and WEIGHT, NOT freight invoice spend, LTL volume,
customer demand or fee recovery. This module can inspect only explicitly
provided original local ZIP bytes or fabricated test ZIPs. Routine CI never
downloads Census archives or ingests customer records.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_cfs_archive_verifier import (
    _archive_members, _parse_tabular, digest_bytes, _read_archive,
)

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "research" / "CFS_A18_A19_INDUSTRY_RECEIPT_20261011.json"
SCOPE = "LAB14_CFS_INDUSTRY_PUBLIC_SOURCE_METADATA_AND_QUALITY_HOLD"
LISTING = "https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html"
PUB_YEAR = "2025-06-26"
TABLES = {
    "CF2200A18": {
        "zip_url": "https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A18.zip",
        "member": "CF2200A18.dat", "axis": "SHIPDIST",
        "index_rows": 7312,
        "grain": "NAICS2017_X_DMODE_X_SHIPDIST_US_2022",
    },
    "CF2200A19": {
        "zip_url": "https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A19.zip",
        "member": "CF2200A19.dat", "axis": "SHIPWT",
        "index_rows": 6782,
        "grain": "NAICS2017_X_DMODE_X_SHIPWT_US_2022",
    },
}
ROOT_FIELDS = {
    "schema_version", "scope", "observed_on", "survey_year",
    "publication_on", "observation_method",
    "original_source_binary_stored_in_repo", "raw_data_ingested_in_ci",
    "any_customer_or_carrier_records", "actual_ltl_invoice_spend_measured",
    "invoice_error_prevalence_established",
    "buyer_opportunity_ranking_authorized",
    "freight_audit_market_revenue_established",
    "external_contact_or_financial_actions_allowed",
    "publisher_signature_verified", "official_archives",
    "research_segments", "required_followups", "legal_boundary",
}
ARCHIVE_FIELDS = {
    "table_id", "name", "url", "source_index_url", "dataset_grain",
    "published_table_row_count", "original_zip_size_bytes",
    "original_zip_sha256", "original_archive_observed_by_read_only_browser",
    "local_ci_replay_of_original", "table_member",
    "original_member_structure_inspected", "source_limit",
}
SEGMENT_IDS = {
    "manufacturing": ("31-33", 1),
    "wholesale": ("42", 2),
    "warehousing": ("493", 3),
}
SEGMENT_FIELDS = {
    "id", "category", "candidate_naics_groups", "rank",
    "hypothesis", "falsifier", "demand_verified",
    "customer_invoice_count_verified", "lfv_market_opportunity_usd",
}
BLOCKED = (
    "original_source_binary_stored_in_repo", "raw_data_ingested_in_ci",
    "any_customer_or_carrier_records", "actual_ltl_invoice_spend_measured",
    "invoice_error_prevalence_established",
    "buyer_opportunity_ranking_authorized",
    "freight_audit_market_revenue_established",
    "external_contact_or_financial_actions_allowed",
    "publisher_signature_verified",
)
# VALID flags are not themselves proof that individual numerators are
# statistically precise. A Census suppression/footnote is never numeric zero.
ALLOWED_SAMPLE_STATUS = {
    "PUBLISHED_ESTIMATE", "CENSUS_FLAGGED_ESTIMATE",
    "MISSING_OR_NONNUMERIC_SOURCE_ESTIMATE",
}
BASE_FIELDS = {
    "NAICS2017", "DMODE", "YEAR", "VAL", "TON",
    "VAL_F", "TON_F", "VAL_S", "TON_S",
}


def _is_date(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _has_text(value: object, minimum=10, maximum=700) -> bool:
    return type(value) is str and minimum <= len(value.strip()) <= maximum


def _has_quality_snapshot(book: dict, *, as_of: date) -> list[str]:
    problems = []
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["schema 1 metadata object required"]
    if set(book) != ROOT_FIELDS or book.get("scope") != SCOPE:
        problems.append("source inventory scope or fields cannot change silently")
    if (not _is_date(book.get("observed_on")) or
        book["observed_on"] > as_of.isoformat()):
        problems.append("date is invalid or from the future")
    if book.get("survey_year") != 2022 or type(book.get("survey_year")) is not int:
        problems.append("source vintage was changed")
    if book.get("publication_on") != PUB_YEAR:
        problems.append("published date is not original 2025 CFS final")
    if book.get("observation_method") != "PUBLIC_OFFICIAL_CENSUS_INDEX_PLUS_READ_ONLY_ORIGINAL_ARCHIVE_REVIEW":
        problems.append("source method mislabeled or unauthorized")
    for field in BLOCKED:
        if book.get(field) is not False:
            problems.append(field + ": unauthorized business/source claim")
    if not _has_text(book.get("legal_boundary"), 130):
        problems.append("no explicit freight billing vs goods value boundary")
    archives = book.get("official_archives")
    if type(archives) is not list or len(archives) != len(TABLES):
        return problems + ["exactly two CFS public table archive records required"]
    seen = set()
    for row in archives:
        if type(row) is not dict or set(row) != ARCHIVE_FIELDS:
            problems.append("malformed source record or extra customer fields")
            continue
        name = row.get("table_id")
        if type(name) is not str or name in seen or name not in TABLES:
            problems.append("unknown/repeated table ID")
            continue
        seen.add(name)
        expected = TABLES[name]
        if (row.get("url") != expected["zip_url"] or
            row.get("source_index_url") != LISTING or
            row.get("dataset_grain") != expected["grain"] or
            row.get("table_member") != expected["member"] or
            row.get("published_table_row_count") != expected["index_rows"]):
            problems.append(name + ": official provenance/grain/count drift")
        if row.get("local_ci_replay_of_original") is not False:
            problems.append(name + ": CI did not replay original ZIP")
        inspected = row.get("original_archive_observed_by_read_only_browser")
        if inspected is not True and inspected is not False:
            problems.append(name + ": observation needs explicit true/false")
        if row.get("original_member_structure_inspected") is not inspected:
            problems.append(name + ": source archive format claim inconsistent")
        size = row.get("original_zip_size_bytes")
        digest = row.get("original_zip_sha256")
        if inspected is True:
            if (type(size) is not int or not 10000 <= size <= 2*1024*1024 or
                type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest)):
                problems.append(name + ": inspected raw file must have real source byte size/hash")
        elif size is not None or digest is not None:
            problems.append(name + ": unverifiable source checksum fabricated")
        if not _has_text(row.get("source_limit"), 65):
            problems.append(name + ": source limitation missing")
    if seen != set(TABLES):
        problems.append("both original CFS public source identities must be present")
    segments=book.get("research_segments")
    if type(segments) is not list or len(segments)!=3:
        return problems+["three bounded industry hypotheses required"]
    seen_ids=set()
    for item in segments:
        if type(item) is not dict or set(item) != SEGMENT_FIELDS:
            problems.append("malformed buyer industry hypothesis")
            continue
        ident=item.get("id")
        if type(ident) is not str or ident not in SEGMENT_IDS or ident in seen_ids:
            problems.append("invalid or repeated industry hypothesis ID")
            continue
        seen_ids.add(ident)
        naics, priority=SEGMENT_IDS[ident]
        if item.get("candidate_naics_groups") != [naics] or item.get("rank") != priority or type(item.get("rank")) is not int:
            problems.append(ident + ": false or changed NAICS research mapping")
        for field in ("demand_verified",):
            if item.get(field) is not False:
                problems.append(ident + ": buyer demand cannot self-certify")
        if (item.get("customer_invoice_count_verified") != 0 or
            type(item.get("customer_invoice_count_verified")) is not int or
            item.get("lfv_market_opportunity_usd") is not None):
            problems.append(ident + ": no LTL invoice spend or recovery TAM")
        if (not _has_text(item.get("hypothesis"), 90) or
            not _has_text(item.get("falsifier"), 90)):
            problems.append(ident + ": falsifiable buyer research required")
    if seen_ids != set(SEGMENT_IDS):
        problems.append("segment census incomplete")
    follow=book.get("required_followups")
    if (type(follow) is not list or len(follow)!=6 or
        any(not _has_text(s, 70) for s in follow)):
        problems.append("six public-source and human-study blockers required")
    return problems


def validate_manifest(book: dict, *, as_of: date) -> list[str]:
    try:
        return _has_quality_snapshot(book, as_of=as_of)
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
        return ["malformed nested public Census industry metadata"]


def _estimate(value: str, flag: str, cv: str, cv_flag: str) -> dict:
    if type(value) is not str or type(flag) is not str:
        raise ValueError("NON_STRING_CFS_ESTIMATE")
    if flag.strip() not in ("", "S", "D", "N", "X", "Z", "-"):
        raise ValueError("UNKNOWN_CENSUS_ESTIMATE_FLAG")
    if flag.strip():
        return {"value":None, "status":"CENSUS_FLAGGED_ESTIMATE",
                "flag":flag.strip(), "cv":None, "cv_available":False}
    if not re.fullmatch(r"[0-9]{1,15}", value.replace(",", "").strip()):
        return {"value":None, "status":"MISSING_OR_NONNUMERIC_SOURCE_ESTIMATE",
                "flag":flag.strip(), "cv":None, "cv_available":False}
    val=int(value.replace(",", "").strip())
    try:
        cv_val=Decimal(cv.strip()) if cv.strip() and not cv_flag.strip() else None
    except InvalidOperation:
        cv_val=None
    if cv_val is not None and (cv_val<0 or cv_val>10000 or not cv_val.is_finite()):
        cv_val=None
    return {"value":val, "status":"PUBLISHED_ESTIMATE", "flag":"",
            "cv":str(cv_val) if cv_val is not None else None,
            "cv_available":cv_val is not None}


def _original_source_profile(raw: bytes, table: str, manifest: dict,
                             *, synthetic: bool) -> dict:
    if table not in TABLES:
        raise ValueError("UNKNOWN_CENSUS_INDUSTRY_TABLE")
    spec=TABLES[table]
    meta=next(x for x in manifest["official_archives"] if x["table_id"]==table)
    if not synthetic:
        if not meta["original_archive_observed_by_read_only_browser"]:
            raise ValueError("NO_INDEPENDENT_REMOTE_SOURCE_FINGERPRINT")
        if len(raw)!=meta["original_zip_size_bytes"] or digest_bytes(raw)!=meta["original_zip_sha256"]:
            raise ValueError("ORIGINAL_CFS_INDUSTRY_ARCHIVE_SHA256_MISMATCH")
    members, archive=_archive_members(raw)
    if spec["member"] not in {m["member"] for m in members}:
        raise ValueError("EXPECTED_OFFICIAL_DAT_MEMBER_MISSING")
    header, rows=_parse_tabular(archive, spec["member"])
    axis=spec["axis"]
    required=BASE_FIELDS | {axis}
    if not required<=set(header):
        raise ValueError("MISSING_CENSUS_NAICS_MODE_AXIS_OR_QUALITY_FIELD")
    if len(rows)>25000 or not rows:
        raise ValueError("CFS_ROW_VOLUME_OUT_OF_BOUNDS")
    measured=Counter()
    known_keys=set()
    by_naics=Counter()
    by_mode=Counter()
    selected=[]
    groups={k:[] for k in SEGMENT_IDS}
    axes=set()
    flag_samples=[]
    original_2022_rows=0
    for row in rows:
        if row["YEAR"]!="2022":
            raise ValueError("CFS_INDUSTRY_WRONG_YEAR")
        naics=row["NAICS2017"].strip()
        mode=row["DMODE"].strip()
        stratum=row[axis].strip()
        if not naics or not mode or not stratum or len(naics)>40 or len(mode)>12 or len(stratum)>35:
            raise ValueError("MISSING_INDUSTRY_MODE_OR_STRATUM")
        # Exact cross-tab keys; never sum across levels or totals.
        compound=(naics, mode, stratum)
        if compound in known_keys:
            raise ValueError("CFS_DUPLICATE_CROSSTAB_CLAIM")
        known_keys.add(compound)
        original_2022_rows+=1
        by_naics[naics]+=1
        by_mode[mode]+=1
        axes.add(stratum)
        v=_estimate(row["VAL"],row["VAL_F"],row["VAL_S"],row.get("VAL_S_F",""))
        t=_estimate(row["TON"],row["TON_F"],row["TON_S"],row.get("TON_S_F",""))
        measured["value:"+v["status"]]+=1
        measured["weight:"+t["status"]]+=1
        if not v["cv_available"]:
            measured["value:CV_NOT_ESTABLISHED"]+=1
        if not t["cv_available"]:
            measured["weight:CV_NOT_ESTABLISHED"]+=1
        if v["flag"] or t["flag"]:
            if len(flag_samples)<9:
                flag_samples.append({"naics":naics,"mode":mode,"stratum":stratum,
                                    "value_flag":v["flag"],"weight_flag":t["flag"]})
        if naics in ("31-33", "42", "493") and mode in ("00","11","111","112","113") and len(groups[naics])<15:
            groups[naics].append({
                "naics2017":naics, "mode":mode, "stratum":stratum,
                "goods_value_million_usd":v["value"],
                "goods_value_flag":v["flag"],
                "goods_value_cv":v["cv"],
                "shipment_weight_thousand_tons":t["value"],
                "shipment_weight_flag":t["flag"],
                "weight_cv":t["cv"],
                "not_invoice_spend_or_ltl_only":True,
            })
    # The publisher's index count is an initial expected-shape diagnostic,
    # not source authenticity. Exact arithmetic can differ by valid revisions.
    observed_n=original_2022_rows
    report={
        "table_id":table,"source_member":spec["member"],
        "archive_sha256":digest_bytes(raw),"original_source_hash_matched":not synthetic,
        "scope":"SYNTHETIC_QA_ONLY" if synthetic else "ORIGINAL_PUBLIC_CENSUS_ZIP_HASH_REPLAYED",
        "source_rows_examined":observed_n,"publisher_index_rows":spec["index_rows"],
        "source_index_count_matches_exactly":observed_n==spec["index_rows"],
        "total_distinct_naics_codes":len(by_naics),
        "total_distinct_mode_codes":len(by_mode),
        "total_distinct_strata":len(axes),
        "sample_value_quality_counts":dict(sorted((k,v) for k,v in measured.items() if k.startswith("value:"))),
        "sample_weight_quality_counts":dict(sorted((k,v) for k,v in measured.items() if k.startswith("weight:"))),
        "example_suppressed_or_flagged_cells":flag_samples,
        "industry_examples":groups,
        "invoice_billing_revenue_verified":False,
        "totaling_nested_industry_or_transport_modes_authorized":False,
        "statistical_precision_cleared_from_cvs":False,
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def profile_local_zip(*, raw: bytes, table_id: str, as_of: date,
                      synthetic_test: bool=False, manifest: dict|None=None) -> dict:
    if manifest is None:
        manifest=json.loads(BOOK.read_text(encoding="utf-8"))
    errors=validate_manifest(manifest,as_of=as_of)
    if errors:
        raise ValueError("INVALID_CFS_INDUSTRY_MANIFEST: "+"; ".join(errors))
    return _original_source_profile(raw,table_id,manifest,synthetic=synthetic_test)


def build_readiness(*, as_of: date) -> dict:
    book=json.loads(BOOK.read_text(encoding="utf-8"))
    errors=validate_manifest(book,as_of=as_of)
    if errors:
        raise ValueError("INVALID_CFS_INDUSTRY_MANIFEST: "+"; ".join(errors))
    sources=[]
    for row in book["official_archives"]:
        sources.append({
            "table_id":row["table_id"],"grain":row["dataset_grain"],
            "original_zip_url":row["url"],
            "published_table_row_count":row["published_table_row_count"],
            "original_source_downloaded_or_inspected_in_external_browser":row["original_archive_observed_by_read_only_browser"],
            "original_source_archive_bytes_replayed_in_ci":False,
            "remote_observed_zip_sha256":row["original_zip_sha256"],
            "remote_observed_zip_size_bytes":row["original_zip_size_bytes"],
            "original_publisher_signature_verified":False,
            "survey_goods_value_units":"USD_MILLIONS_OF_GOODS_NOT_FREIGHT_SPEND",
            "survey_weight_units":"THOUSAND_TONS_NOT_LTL_INVOICE_CHARGES",
            "statistical_flags_and_uncertainty_must_be_preserved":True,
            "annual_ltl_invoice_revenue_or_recoveries_not_measured":True,
        })
    report={
        "schema_version":1,"scope":"LAB14_CFS_INDUSTRY_SOURCE_READINESS_NO_CI_DOWNLOAD",
        "as_of":as_of.isoformat(),"book_receipt_sha256":canon_hash(book),
        "survey_year":2022,"published_on":PUB_YEAR,
        "public_archive_leads":len(sources),"sources":sources,
        "source_rows_from_full_files_replayed_in_ci":0,
        "real_customer_invoices":0,"source_quality_flags_dismissed":0,
        "market_share_claims_approved":0,"verified_paid_ltl_spend_usd":None,
        "buyer_demand_verified":False,"recovery_tam_calculated":False,
        "candidate_segments":[{
            "id":x["id"],"priority_for_data_gap_research_not_market_rank":x["rank"],
            "candidate_naics2017":x["candidate_naics_groups"],
            "hypothesis":x["hypothesis"],
            "falsification":x["falsifier"],
            "verified_paid_ltl_invoice_count":0,
            "buying_propensity_known":False,
        } for x in book["research_segments"]],
        "next_review_steps":book["required_followups"],
        "existing_lab_number":14,"new_lab_created":False,
        "network_or_scheduler_enabled":False,
        "public_market_or_recovery_claims_allowed":False,
        "boundary":book["legal_boundary"],
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def render_html(report:dict)->str:
    cards=[]
    for source in report["sources"]:
        cards.append(
            '<article><small>'+escape(source["table_id"])+
            ' · ORIGINAL ARCHIVE</small><h2>'+escape(source["grain"].replace("_"," "))+
            '</h2><p>Published table index rows: '+
            str(source["published_table_row_count"])+
            '</p><p>Remote public original archived data inspected: '+
            ("yes" if source["original_source_downloaded_or_inspected_in_external_browser"] else "not established")+
            '</p><p>Original ZIP SHA: '+
            escape(str(source["remote_observed_zip_sha256"]))+
            '</p><p>Raw source reprocessed by this CI run: no. Goods value '
            'is not carrier invoices or fee revenue.</p></article>'
        )
    hypotheses="".join(
        '<article><h3>'+escape(v["id"].title())+'</h3><p>'+escape(v["hypothesis"])+
        '</p><p><b>Independent test needed:</b> '+escape(v["falsification"])+
        '</p><p>Buyer demand confirmed: no.</p></article>'
        for v in report["candidate_segments"]
    )
    return (
      '<!doctype html><html lang="en"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1">'
      '<title>RETALLY | Industry Source Integrity</title><style>'
      '*{box-sizing:border-box}body{background:#f6f9f7;color:#1d392b;'
      'font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0}'
      'main{max-width:1050px;margin:auto;padding:30px 18px 64px}'
      'h1{font-size:clamp(31px,5vw,47px);line-height:1.1;letter-spacing:-.045em}'
      'h2{font-size:19px}h3{font-size:17px}'
      'article{background:white;border:1px solid #dce8dd;'
      'border-radius:14px;padding:20px;margin:14px 0}'
      'small{color:#577265;font-size:12px}'
      'p{overflow-wrap:anywhere}</style></head>'
      '<body><main><small>RETALLY / LAB 14 / MISSION 14 / SOURCE RESEARCH</small>'
      '<h1>Industry exposure is not invoice opportunity.</h1>'
      '<p>2022 public Census survey table observations only. Mode/industry/weight '
      'and distance strata overlap. Suppressed or non-comparable values must not '
      'be silently treated as zero. No paid LTL invoice spend, error rate, buyer '
      'demand or recoverable contingent fees have been validated.</p>'
      + "".join(cards) +
      '<h2>Buyer data-gap hypotheses</h2>'+hypotheses+
      '<footer><small>Local inventory digest: '+
      escape(report["receipt_sha256"])+
      ' (not a Census publisher signature)</small></footer>'
      '</main></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--zip",type=Path)
    parser.add_argument("--table",choices=sorted(TABLES))
    parser.add_argument("--synthetic-test",action="store_true")
    args=parser.parse_args()
    if bool(args.zip)!=bool(args.table):
        parser.error("--zip and --table must be supplied together")
    if args.synthetic_test and not args.zip:
        parser.error("--synthetic-test requires an explicitly supplied local zip")
    report=(profile_local_zip(raw=_read_archive(args.zip),table_id=args.table,
                              as_of=args.as_of_date,synthetic_test=args.synthetic_test)
            if args.zip else build_readiness(as_of=args.as_of_date))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"cfs_industry_quality.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if "sources" in report:
        (args.out/"cfs_industry_quality.html").write_text(
            render_html(report),encoding="utf-8")
    print(json.dumps({
        "scope":report["scope"],
        "receipt":report["receipt_sha256"]
    },sort_keys=True))


if __name__=="__main__":
    main()
