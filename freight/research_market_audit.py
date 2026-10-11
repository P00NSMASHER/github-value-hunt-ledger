"""RETALLY Lab 14 Mission 12: primary-source market estimate reconciliation.

Research-only OFFLINE checks on six manually transcribed Census CFS 2022
table rows and a dated Census press-release excerpt. There is NO download
of the raw Census archive in this module and no independent data replication.
A public survey of commodity shipments does not measure carrier invoices,
for-hire LTL specifically, freight audit revenue, customer demand or refunds.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from freight.research_evidence_gate import canon_hash
from freight.research_validation_protocols import build_protocol_report

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "research/CFS_2022_SOURCE_AUDIT_20261011.json"
SCOPE = "LAB14_CFS_2022_PUBLIC_EXCERPT_RECONCILIATION_ONLY"
SOURCE_ROWS = {
    "us.allmodes.2022": ("United States", "US", "00", "All modes", 17996782, 12169793),
    "us.truck.2022": ("United States", "US", "11", "Single-mode truck (incl. pickup)", 13222965, 8293501),
    "us.forhire.2022": ("United States", "US", "111", "For-hire truck", 8062541, 3909476),
    "us.company.2022": ("United States", "US", "112", "Company-owned truck", 4141550, 2994372),
    "us.customer.2022": ("United States", "US", "113", "Customer pickup", 1018874, 1389653),
    "south.allmodes.2022": ("South Region", "REGION", "00", "All modes", 6689859, 4919551),
}
SOURCE_META = {
    "cfs.2022.a01.table": (
        "U.S. Census Bureau",
        "https://data.census.gov/table/CFSAREA2022.CF2200A01",
        "OFFICIAL_TABLE_SEARCH_EXCERPT_NOT_COMPLETE_CSV",
    ),
    "cfs.2022.press.release": (
        "U.S. Census Bureau",
        "https://www.census.gov/newsroom/press-releases/2025/cfs-shipments-of-goods.html",
        "DIRECT_OFFICIAL_PUBLIC_RELEASE_TEXT",
    ),
    "cfs.2022.a01.directory": (
        "U.S. Census Bureau",
        "https://www2.census.gov/programs-surveys/cfs/data/2022/",
        "DIRECT_OFFICIAL_DIRECTORY_LISTING_METADATA_ONLY",
    ),
}
PRESS_NUMBERS = {
    "total_rounded_billion_tons": Decimal("12.2"),
    "total_rounded_trillion_usd": Decimal("18.0"),
    "truck_mode_weight_pct": Decimal("68.1"),
    "truck_mode_value_pct": Decimal("73.5"),
    "south_claimed_billion_tons": Decimal("1.9"),
    "south_claimed_pct_of_national_tonnage": Decimal("40.4"),
    "manufacturing_rounded_billion_tons": Decimal("4.9"),
    "manufacturing_rounded_trillion_usd": Decimal("7.1"),
    "wholesale_rounded_billion_tons": Decimal("4.1"),
    "wholesale_rounded_trillion_usd": Decimal("8.1"),
}
V_GROUPS = {"manufacturing", "wholesale", "distribution"}
VERTICAL_BINDINGS = {
    "manufacturing": ("Manufacturing establishments",
                      "press.release.2025.cfs2022.manufacturing_rounded_billion_tons"),
    "wholesale": ("Wholesale establishments",
                  "press.release.2025.cfs2022.wholesale_rounded_billion_tons"),
    "distribution": ("Warehousing and distribution auxiliaries",
                     "cfs.2022.press.release.industry_coverage_not_segment_value"),
}
OPEN_TASK_BINDINGS = {
    "GAS18_NAICS_MODE_DISTANCE": "CF2200A18",
    "GAS19_NAICS_MODE_WEIGHT": "CF2200A19",
    "CFS_A01_FULL_ROW_RECHECK": "CF2200A01",
}
OPEN_TABLES = tuple(OPEN_TASK_BINDINGS.values())
REQUIRED_ROOT_FIELDS = {
    "schema_version", "scope", "research_as_of", "survey_year",
    "reported_publication_date", "data_origin", "raw_zip_downloaded",
    "original_csv_contents_examined", "upstream_zip_sha256",
    "independent_issuer_signature_verified", "invoice_level_records_received",
    "real_buyer_data_ingested", "claim_submission_or_fee_authorized",
    "commercial_market_tam_established", "actual_ltl_invoice_spend_measured",
    "public_performance_claims_permitted", "new_lab_created", "notes",
    "sources", "table_rows", "press_release", "candidate_verticals",
    "open_research_tasks",
}
SOURCE_FIELDS = {
    "id", "publisher", "title", "url", "publication_date", "observed_on",
    "review_method", "raw_dataset_downloaded", "publisher_authenticated_digitally",
    "independently_reproduced_from_full_dataset", "scope",
}
ROW_FIELDS = {
    "id", "source_id", "geo", "geo_class", "mode_code", "mode",
    "year", "value_million_usd", "weight_thousand_tons",
}
PRESS_FIELDS = {
    "id", "source_id", "total_rounded_billion_tons",
    "total_rounded_trillion_usd", "truck_mode_weight_pct",
    "truck_mode_value_pct", "south_claimed_billion_tons",
    "south_claimed_pct_of_national_tonnage",
    "manufacturing_rounded_billion_tons",
    "manufacturing_rounded_trillion_usd",
    "wholesale_rounded_billion_tons", "wholesale_rounded_trillion_usd",
    "press_south_tonnage_consistent_with_percent",
    "claimed_price_or_invoice_field_present",
}
VERTICAL_FIELDS = {
    "id", "label", "source_field", "source_group", "research_hypothesis",
    "next_falsification", "prohibited_inference", "buyer_authorization_observed",
    "invoice_spend_measured", "carrier_mode_LTL_confirmed", "demand_validated",
    "research_priority_not_market_ranking",
}
TASK_FIELDS = {
    "id", "table_id", "official_listing_url", "research_need", "download_approved",
}
DENIED_FLAGS = {
    "raw_zip_downloaded", "original_csv_contents_examined",
    "independent_issuer_signature_verified", "real_buyer_data_ingested",
    "claim_submission_or_fee_authorized", "commercial_market_tam_established",
    "actual_ltl_invoice_spend_measured", "public_performance_claims_permitted",
    "new_lab_created",
}
FORBIDDEN_INTERPRETATION = (
    "CFS commodity shipment VALUE is not carrier freight invoice SPEND. "
    "For-hire truck is not LTL-only, and truck total includes company-owned "
    "and 2022 customer pickup. No invoice overcharge prevalence, reachable "
    "buyers, signed pricing, legitimate carrier claim, serviceable market, "
    "recovered funds or forecast is measured by this research."
)


def _iso(raw: object) -> date:
    if type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError("canonical YYYY-MM-DD required")
    day = date.fromisoformat(raw)
    if day.isoformat() != raw:
        raise ValueError("canonical YYYY-MM-DD required")
    return day


def _meaningful(raw: object, minimum: int = 25, maximum: int = 1600) -> bool:
    return type(raw) is str and minimum <= len(raw.strip()) <= maximum


def _url_matches(uri: object, required: str) -> bool:
    if type(uri) is not str or uri != required or len(uri) > 600:
        return False
    try:
        p = urlsplit(uri)
        return (
            p.scheme == "https" and bool(p.hostname) and
            p.username is None and p.password is None and p.port is None and
            not p.fragment
        )
    except ValueError:
        return False


def _pct(top: int, bottom: int) -> Decimal:
    if type(top) is not int or type(bottom) is not int or bottom <= 0:
        raise ValueError("invalid exact published denominator")
    return Decimal(top) * 100 / Decimal(bottom)


def _rounded(value: Decimal, places: str = "0.01") -> str:
    return format(value.quantize(Decimal(places), rounding=ROUND_HALF_UP), "f")


def _held_protocols(report: dict) -> bool:
    if not isinstance(report, dict):
        return False
    supplied_hash = report.get("receipt_sha256")
    return (
        type(supplied_hash) is str and
        supplied_hash == canon_hash({
            k: v for k, v in report.items() if k != "receipt_sha256"
        }) and
        report.get("scope") == "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY" and
        report.get("protocol_count") == 6 and
        report.get("external_studies_executed") == 0 and
        report.get("observed_customer_outcomes") == 0 and
        report.get("approved_preregistrations") == 0 and
        report.get("public_performance_claims_allowed") is False and
        report.get("external_actions_allowed") is False and
        report.get("new_lab_created") is False
    )


def _validate_catalog_inner(book: dict, protocols: dict, *, as_of: date) -> list[str]:
    errors: list[str] = []
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["CFS market snapshot must be schema 1 object"]
    if set(book) != REQUIRED_ROOT_FIELDS or book.get("scope") != SCOPE:
        errors.append("unauthorized CFS snapshot schema, fields or scope")
    if not _held_protocols(protocols):
        errors.append("unchanged, held Mission 7 research designs required")
    if book.get("data_origin") != "OFFICIAL_PUBLICLY_VISIBLE_TABLE_AND_PRESS_EXCERPTS_MANUALLY_REVIEWED_NOT_FULL_CSV":
        errors.append("raw archive/source replication cannot be fabricated")
    if book.get("survey_year") != 2022 or type(book.get("survey_year")) is not int:
        errors.append("unsupported survey vintage")
    if book.get("reported_publication_date") != "2025-06-26":
        errors.append("Census publication date altered")
    observed = _iso(book.get("research_as_of"))
    if observed > as_of:
        errors.append("future market observation")
    for flag in DENIED_FLAGS:
        if book.get(flag) is not False:
            errors.append(f"unapproved source truth or business use: {flag}")
    if book.get("invoice_level_records_received") != 0 or type(book.get("invoice_level_records_received")) is not int:
        errors.append("no invoice-level data acquired")
    if book.get("upstream_zip_sha256") is not None:
        errors.append("original source archive was not downloaded or hashed")
    if not _meaningful(book.get("notes"), 170):
        errors.append("explicit survey, LTL and source limitations required")

    sources = book.get("sources")
    if type(sources) is not list or len(sources) != 3:
        return errors + ["exactly three official source artifacts required"]
    observed_ids: set[str] = set()
    for i, source in enumerate(sources):
        if type(source) is not dict or set(source) != SOURCE_FIELDS:
            errors.append(f"source {i}: unexpected/missing fields")
            continue
        ident = source.get("id")
        if ident not in SOURCE_META or ident in observed_ids:
            errors.append(f"source {i}: unknown/duplicate source")
            continue
        observed_ids.add(ident)
        publisher, url, method = SOURCE_META[ident]
        if source["publisher"] != publisher or not _url_matches(source["url"], url):
            errors.append(f"{ident}: source publisher/URL spoofed")
        if source["review_method"] != method:
            errors.append(f"{ident}: source review method overstated")
        if source["publication_date"] != "2025-06-26":
            errors.append(f"{ident}: source date changed")
        if _iso(source["observed_on"]) > as_of or source["observed_on"] != book.get("research_as_of"):
            errors.append(f"{ident}: source observation date invalid")
        if (source["raw_dataset_downloaded"] is not False or
            source["publisher_authenticated_digitally"] is not False or
            source["independently_reproduced_from_full_dataset"] is not False):
            errors.append(f"{ident}: cannot claim content download, independent full replication or publisher signature")
        if not _meaningful(source.get("title"), 16) or not _meaningful(source.get("scope"), 35):
            errors.append(f"{ident}: bounded title and specific limitations required")
    if observed_ids != set(SOURCE_META):
        errors.append("original public-source register incomplete")

    rows = book.get("table_rows")
    if type(rows) is not list or len(rows) != len(SOURCE_ROWS):
        return errors + ["six exact published CFS row excerpts required"]
    rows_seen: set[str] = set()
    for n, item in enumerate(rows):
        if type(item) is not dict or set(item) != ROW_FIELDS:
            errors.append(f"row {n}: wrong row shape or units")
            continue
        ident = item.get("id")
        if ident not in SOURCE_ROWS or ident in rows_seen:
            errors.append(f"row {n}: unknown or duplicate published row")
            continue
        rows_seen.add(ident)
        expected = SOURCE_ROWS[ident]
        actual = (
            item["geo"], item["geo_class"], item["mode_code"], item["mode"],
            item["value_million_usd"], item["weight_thousand_tons"],
        )
        if actual != expected or any(type(x) is not int or x <= 0 for x in actual[4:]):
            errors.append(f"{ident}: Census row value/unit/identity changed without source review")
        if item["source_id"] != "cfs.2022.a01.table" or item["year"] != 2022 or type(item["year"]) is not int:
            errors.append(f"{ident}: unbound Census vintage or source")
    if rows_seen != set(SOURCE_ROWS):
        errors.append("missing detailed source excerpts")

    press = book.get("press_release")
    if type(press) is not dict or set(press) != PRESS_FIELDS:
        return errors + ["official press claim fields missing/unsafe"]
    if press.get("id") != "press.release.2025.cfs2022" or press.get("source_id") != "cfs.2022.press.release":
        errors.append("Census press statement not source-bound")
    for key, required in PRESS_NUMBERS.items():
        value = press.get(key)
        if (type(value) not in (int, float) or type(value) is bool or
            not Decimal(str(value)).is_finite() or
            Decimal(str(value)) != required):
            errors.append(f"Census press excerpt number modified: {key}")
    if press.get("press_south_tonnage_consistent_with_percent") is not False:
        errors.append("unresolved South regional press contradiction cannot be cleared")
    if press.get("claimed_price_or_invoice_field_present") is not False:
        errors.append("CFS press release has no verified freight billing or invoice price data")

    verticals = book.get("candidate_verticals")
    if type(verticals) is not list or len(verticals) != 3:
        return errors + ["three explicitly unproven buyer hypotheses required"]
    seen = set()
    for i, item in enumerate(verticals):
        if type(item) is not dict or set(item) != VERTICAL_FIELDS:
            errors.append(f"vertical {i}: invalid research hypothesis structure")
            continue
        ident = item.get("id")
        if ident not in V_GROUPS or ident in seen:
            errors.append(f"vertical {i}: unknown or repeated segment")
            continue
        seen.add(ident)
        label, source_field = VERTICAL_BINDINGS[ident]
        if item.get("label") != label or item.get("source_field") != source_field:
            errors.append(f"{ident}: vertical taxonomy or source field changed")
        if item.get("source_group") != "CFS_2022_SHARED_SURVEY_FAMILY":
            errors.append(f"{ident}: Census evidence cannot become independent studies")
        for key in ("buyer_authorization_observed", "invoice_spend_measured",
                    "carrier_mode_LTL_confirmed", "demand_validated"):
            if item.get(key) is not False:
                errors.append(f"{ident}: unverified buyer/LTL/revenue result promoted")
        for key in ("research_hypothesis", "next_falsification", "prohibited_inference"):
            if not _meaningful(item.get(key), 60):
                errors.append(f"{ident}: missing actionable falsification or caveat")
        if (type(item.get("research_priority_not_market_ranking")) is not int or
            item.get("research_priority_not_market_ranking") != {"manufacturing": 1, "wholesale": 2, "distribution": 3}[ident]):
            errors.append(f"{ident}: research list order changed without review")
    if seen != V_GROUPS:
        errors.append("buyer research hypotheses missing")

    tasks = book.get("open_research_tasks")
    if type(tasks) is not list or len(tasks) != 3:
        return errors + ["three original-data recheck tasks required"]
    tables = set()
    for item in tasks:
        if type(item) is not dict or set(item) != TASK_FIELDS:
            errors.append("invalid original-table research step")
            continue
        code = item.get("table_id")
        task_id = item.get("id")
        if task_id not in OPEN_TASK_BINDINGS or code != OPEN_TASK_BINDINGS[task_id] or code in tables:
            errors.append("unsupported/duplicate Census table research task or id")
        tables.add(code)
        if item.get("download_approved") is not False or not _meaningful(item.get("research_need"), 55):
            errors.append(f"{code}: cannot claim download authority or invent review")
        expected_url = ("https://www2.census.gov/programs-surveys/cfs/data/2022/"
                        if code == "CF2200A01"
                        else "https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html")
        if item.get("official_listing_url") != expected_url:
            errors.append(f"{code}: research task URL modified")
    return errors


def validate_catalog(book: dict, protocols: dict, *, as_of: date) -> list[str]:
    try:
        return _validate_catalog_inner(book, protocols, as_of=as_of)
    except (TypeError, ValueError, KeyError, AttributeError, ArithmeticError, OverflowError):
        return ["malformed or unsupported nested public-research metadata"]


def build_market_audit(*, as_of: date, book: dict | None = None,
                       protocols: dict | None = None) -> dict:
    if protocols is None:
        protocols = build_protocol_report(as_of=as_of)
    if book is None:
        book = json.loads(AUDIT.read_text(encoding="utf-8"))
    failures = validate_catalog(book, protocols, as_of=as_of)
    if failures:
        raise ValueError("INVALID_CFS_SOURCE_AUDIT: " + "; ".join(failures))
    m = {row["id"]: row for row in book["table_rows"]}
    v = {k: m[k]["value_million_usd"] for k in m}
    t = {k: m[k]["weight_thousand_tons"] for k in m}
    truck = "us.truck.2022"
    subs = ("us.forhire.2022", "us.company.2022", "us.customer.2022")
    exact_value_conserves = sum(v[k] for k in subs) == v[truck]
    exact_weight_conserves = sum(t[k] for k in subs) == t[truck]
    if not (exact_value_conserves and exact_weight_conserves):
        raise ValueError("OFFICIAL_CFS_MODE_CATEGORIES_DO_NOT_RECONCILE")

    totals = {
        "total_value_million_usd": v["us.allmodes.2022"],
        "total_weight_thousand_tons": t["us.allmodes.2022"],
        "all_single_mode_truck_value_million_usd": v[truck],
        "all_single_mode_truck_weight_thousand_tons": t[truck],
        "for_hire_truck_value_million_usd": v["us.forhire.2022"],
        "company_owned_truck_value_million_usd": v["us.company.2022"],
        "customer_pickup_value_million_usd": v["us.customer.2022"],
        "for_hire_truck_weight_thousand_tons": t["us.forhire.2022"],
        "company_owned_truck_weight_thousand_tons": t["us.company.2022"],
        "customer_pickup_weight_thousand_tons": t["us.customer.2022"],
        "truck_mode_value_components_equal_source_total": exact_value_conserves,
        "truck_mode_weight_components_equal_source_total": exact_weight_conserves,
        "truck_value_share_of_all_shipments_pct": _rounded(_pct(v[truck], v["us.allmodes.2022"])),
        "truck_weight_share_of_all_shipments_pct": _rounded(_pct(t[truck], t["us.allmodes.2022"])),
        "for_hire_truck_value_share_of_all_shipments_pct": _rounded(_pct(v["us.forhire.2022"], v["us.allmodes.2022"])),
        "for_hire_truck_weight_share_of_all_shipments_pct": _rounded(_pct(t["us.forhire.2022"], t["us.allmodes.2022"])),
        "for_hire_value_share_of_truck_total_pct": _rounded(_pct(v["us.forhire.2022"], v[truck])),
        "company_owned_value_share_of_truck_total_pct": _rounded(_pct(v["us.company.2022"], v[truck])),
        "customer_pickup_value_share_of_truck_total_pct": _rounded(_pct(v["us.customer.2022"], v[truck])),
        "for_hire_is_not_ltl_only": True,
        "truck_mode_2017_to_2022_definition_changed_customer_pickup_added": True,
        "includes_company_owned_and_customer_pickup": True,
        "survey_values_not_freight_bills": True,
        "actual_paid_ltl_freight_invoices_count": None,
        "paid_ltl_invoice_spend_usd": None,
        "freight_audit_addressable_market_usd": None,
        "verified_overcharge_prevalence": None,
        "actual_contingency_revenue_usd": None,
    }
    press = book["press_release"]
    national_billion_tons = Decimal(t["us.allmodes.2022"]) / Decimal(1000000)
    south_billion_tons = Decimal(t["south.allmodes.2022"]) / Decimal(1000000)
    south_pct = _pct(t["south.allmodes.2022"], t["us.allmodes.2022"])
    press_claim = Decimal(str(press["south_claimed_billion_tons"]))
    claimed_pct = Decimal(str(press["south_claimed_pct_of_national_tonnage"]))
    # Explicitly check both different statements against same-grain estimates.
    percent_matches_table = abs(south_pct - claimed_pct) < Decimal("0.12")
    claimed_tons_matches_table = abs(south_billion_tons - press_claim) < Decimal("0.15")
    south_conflict = percent_matches_table and not claimed_tons_matches_table
    if not south_conflict:
        raise ValueError("SOUTH_PRESS_CONTRADICTION_NO_LONGER_MATCHES_DATED_REVIEW")
    truck_weight_press_matches_table = (
        abs(_pct(t[truck], t["us.allmodes.2022"]) -
            Decimal(str(press["truck_mode_weight_pct"]))) < Decimal("0.06")
    )
    truck_value_press_matches_table = (
        abs(_pct(v[truck], v["us.allmodes.2022"]) -
            Decimal(str(press["truck_mode_value_pct"]))) < Decimal("0.06")
    )
    if not (truck_weight_press_matches_table and truck_value_press_matches_table):
        raise ValueError("TRUCK_PRESS_TOTALS_FAIL_TABLE_RECONCILIATION")
    conflict = {
        "code": "CFS_2022_SOUTH_TONNAGE_PRESS_VS_DETAILED_TABLE_CONFLICT",
        "status": "UNRESOLVED_FIRST_PARTY_PUBLICATION_CONTRADICTION",
        "geography": "South Region",
        "survey_year": 2022,
        "press_release_billion_tons": str(press_claim),
        "press_release_south_share_pct": str(claimed_pct),
        "official_detailed_table_thousand_tons": t["south.allmodes.2022"],
        "official_table_south_share_pct_calculated": _rounded(south_pct),
        "press_release_claimed_tonnage_as_share_pct_calculated": _rounded(
            press_claim / national_billion_tons * 100
        ),
        "table_share_consistent_with_press_percent": percent_matches_table,
        "press_tonnage_consistent_with_table": claimed_tons_matches_table,
        "press_number_cleared_for_use": False,
        "automatic_correction_authorized": False,
        "source_urls": [
            SOURCE_META["cfs.2022.a01.table"][1],
            SOURCE_META["cfs.2022.press.release"][1],
        ],
        "next_human_check": (
            "Inspect the full CF2200A01 original download and original press-release "
            "revisions, confirm consistent origin geography and units, and request "
            "an authoritative editorial clarification before publishing the tonnage."
        ),
    }
    hypotheses = []
    for row in book["candidate_verticals"]:
        hypotheses.append({
            "id": row["id"],
            "label": row["label"],
            "source_field": row["source_field"],
            "claim_status": "EXPLICIT_UNTESTED_BUYER_HYPOTHESIS",
            "industry_claim": row["research_hypothesis"],
            "required_falsification": row["next_falsification"],
            "scope_warning": row["prohibited_inference"],
            "actual_ltl_invoice_spend_measured": False,
            "research_priority_not_market_ranking": row["research_priority_not_market_ranking"],
            "independent_customer_evidence": 0,
            "commercial_recommendation_authorized": False,
        })
    stale = (as_of - _iso(book["research_as_of"])).days >= 90
    result = {
        "schema_version": 1, "as_of": as_of.isoformat(),
        "scope": "LAB14_SOURCE_LINKED_CFS_MARKET_AUDIT_RESEARCH_ONLY",
        "survey_year": 2022,
        "publication_on": "2025-06-26",
        "source_audit_record_sha256": canon_hash(book),
        "protocol_receipt_sha256": protocols["receipt_sha256"],
        "source_count": len(book["sources"]), "table_excerpt_rows": len(m),
        "source_review_is_stale": stale,
        "raw_zip_data_downloaded": False,
        "independent_full_table_replication_completed": False,
        "published_estimate_measurements": totals,
        "press_release_reconciliation": {
            "truck_value_pct_agrees_with_detailed_table": truck_value_press_matches_table,
            "truck_weight_pct_agrees_with_detailed_table": truck_weight_press_matches_table,
            "regional_flagged_conflicts": [conflict],
            "all_cfs_regional_statements_independently_verified": False,
        },
        "prospective_buyer_research_hypotheses": hypotheses,
        "source_request_backlog": book["open_research_tasks"],
        "market_ranking_or_recovery_tam_established": False,
        "buyer_demand_confirmed": False,
        "real_customer_or_invoice_data_ingested": False,
        "customer_contact_or_carrier_actions_allowed": False,
        "performance_marketing_claims_allowed": False,
        "existing_lab_number": 14,
        "new_lab_created": False,
        "limitations": FORBIDDEN_INTERPRETATION,
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def render_html(report: dict) -> str:
    t = report["published_estimate_measurements"]
    conflict = report["press_release_reconciliation"]["regional_flagged_conflicts"][0]
    measures = [
        ("All mode shipment goods value ($ million)", t["total_value_million_usd"]),
        ("Single-mode truck goods value ($ million)", t["all_single_mode_truck_value_million_usd"]),
        ("For-hire truck goods value ($ million)", t["for_hire_truck_value_million_usd"]),
        ("Company-owned truck goods value ($ million)", t["company_owned_truck_value_million_usd"]),
        ("Customer-pickup goods value ($ million)", t["customer_pickup_value_million_usd"]),
    ]
    tr = "".join(
        "<tr><th>" + escape(k) + "</th><td>" + f"{v:,}" + "</td></tr>"
        for k, v in measures
    )
    hypotheses = "".join(
        '<article><small>HYPOTHESIS · NOT PROVEN</small><h3>' +
        escape(x["label"]) + '</h3><p>' + escape(x["industry_claim"]) +
        '</p><p><b>Next falsification:</b> ' +
        escape(x["required_falsification"]) +
        '</p><p><b>Cannot infer:</b> ' + escape(x["scope_warning"]) +
        '</p></article>'
        for x in report["prospective_buyer_research_hypotheses"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Published Freight Market Data Audit</title><style>'
        '*{box-sizing:border-box}body{background:#f6f9f7;color:#192f26;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0}'
        'main{max-width:1080px;margin:auto;padding:34px 20px 76px}'
        'header{border-bottom:1px solid #d6e6dc;padding-bottom:24px}'
        'h1{font-size:clamp(31px,5vw,49px);letter-spacing:-.04em;line-height:1.12}'
        'article{background:white;border:1px solid #dae8df;'
        'border-radius:15px;padding:20px;margin:14px 0}'
        'small{color:#577363;font-size:12px;letter-spacing:.09em}'
        'h2{font-size:22px;margin:30px 0 14px}h3{font-size:18px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{text-align:left;padding:11px 14px;border-bottom:1px solid #dce7dd}'
        'th{font-weight:650}b{color:#117349}a{color:#106641}'
        '</style></head><body><main><header><small>RETALLY / LAB 14 / '
        'MISSION 12 / PUBLIC 2022 CFS EXCERPTS</small>'
        '<h1>Freight exposure is not freight-recovery revenue.</h1>'
        '<p>Official published CFS survey estimates were manually transcribed '
        'for source quality checks. The original ZIP was NOT downloaded, full '
        'data NOT independently reproduced, and real LTL invoices NOT inspected.</p>'
        '<p><b>For-hire truck goods share of all modes: ' +
        escape(t["for_hire_truck_value_share_of_all_shipments_pct"]) +
        '%</b> by reported value of goods. This includes non-LTL trucking '
        'and does not establish actual freight bills or audit TAM.</p></header>'
        '<h2>Source-linked shipment estimates</h2><table>' + tr +
        '</table><p>Original detailed table: <a rel="noopener noreferrer" href="' +
        escape(SOURCE_META["cfs.2022.a01.table"][1], quote=True) +
        '">CFS CF2200A01</a>. Values are $ million, not invoice charges.</p>'
        '<h2>Contradiction requiring official review</h2><article><h3>' +
        escape(conflict["code"]) + '</h3><p>The press release reports ' +
        escape(conflict["press_release_billion_tons"]) +
        ' billion tons for South (claimed ' +
        escape(conflict["press_release_south_share_pct"]) +
        '%); the detailed geographic-mode table reports ' +
        f"{conflict['official_detailed_table_thousand_tons']:,}" +
        ' thousand tons for South (calculated ' +
        escape(conflict["official_table_south_share_pct_calculated"]) +
        '%). <b>The press tonnage number remains quarantined, not auto-corrected.</b></p>'
        '<p>' + escape(conflict["next_human_check"]) +
        '</p></article><h2>Candidate buyer cohorts, not rankings</h2>' +
        hypotheses + '<footer><p><b>Limits:</b> ' +
        escape(report["limitations"]) + '</p><small>Local research receipt: ' +
        escape(report["receipt_sha256"]) +
        '. Hashes do not authenticate a Census source.</small></footer>'
        '</main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build_market_audit(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "market_source_audit.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "market_source_audit.html").write_text(
        render_html(result), encoding="utf-8"
    )
    print(json.dumps({
        "sources": result["source_count"],
        "survey_excerpt_rows": result["table_excerpt_rows"],
        "source_conflicts": len(result["press_release_reconciliation"]["regional_flagged_conflicts"]),
        "ltl_market_tam_calculated": result["market_ranking_or_recovery_tam_established"],
        "receipt": result["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
