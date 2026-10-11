"""Mission 9: public freight dataset provenance and rights readiness (existing Lab 14).

This module processes ONLY a frozen, manually inspected PUBLIC METADATA registry.
No source file, invoice or licensed third-party specification is downloaded.
A visible website / GitHub tree does not grant redistribution or benchmark rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

from freight.research_evidence_gate import canon_hash
from freight.research_validation_protocols import build_protocol_report

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "research" / "PUBLIC_FREIGHT_DATA_CANDIDATES_20261010.json"
SCOPE = "RETALLY_LAB14_PUBLIC_METADATA_ONLY_NO_DATA_ADMISSION"
DATA_GRAINS = {
    "PUBLIC_USE_SHIPMENT_MICRODATA",
    "ESTIMATED_AGGREGATE_FLOW",
    "PUBLISHED_AGGREGATE_STATISTICS",
    "PUBLISHED_EDI_EXAMPLE_NOT_A_REAL_VERIFIED_INVOICE",
    "STANDARD_DESCRIPTION_ONLY",
}
SOURCE_KINDS = {
    "OFFICIAL_FEDERAL_DATASET", "PUBLISHER_ILLUSTRATIVE_EXAMPLE",
    "PUBLIC_GITHUB_REPOSITORY", "STANDARDS_DEFINITION",
}
FALSE_SOURCE_FLAGS = (
    "source_content_downloaded", "data_bytes_examined",
    "rights_cleared_for_internal_reuse", "rights_cleared_for_redistribution",
    "privacy_clearance_completed", "independent_invoice_ground_truth_present",
    "independent_recovery_ground_truth_present",
    "may_support_customer_accuracy_claims", "any_customer_case_ingested",
)
REQUIRED_SOURCE_KEYS = {
    "id", "name", "publisher", "url", "documentation_url",
    "source_kind", "grain", "availability", "rights_evidence",
    "release_on", "file_size_display", "allowable_research_track",
    "linked_protocols", "source_basis", "limitations", "next_action",
    "reviewed_on", "source_content_downloaded", "data_bytes_examined",
    "checksum_of_downloaded_bytes", "rights_cleared_for_internal_reuse",
    "rights_cleared_for_redistribution", "privacy_clearance_completed",
    "independent_invoice_ground_truth_present",
    "independent_recovery_ground_truth_present",
    "may_support_customer_accuracy_claims", "any_customer_case_ingested",
    "lineage_family",
}
EXPECTED = {
    "census.cfs2022.pums": {
        "url": "https://www.census.gov/data/datasets/2022/econ/cfs/historical-datasets.html",
        "grain": "PUBLIC_USE_SHIPMENT_MICRODATA",
        "kind": "OFFICIAL_FEDERAL_DATASET",
        "rights": "PUBLIC_USE_LABEL_TERMS_AND_REUSE_SCOPE_REVIEW_PENDING",
        "lineage": "CFS_FAF_2022_INTERDEPENDENT", "protocol": "M7-04",
    },
    "bts.faf6.regional": {
        "url": "https://www.bts.gov/faf",
        "grain": "ESTIMATED_AGGREGATE_FLOW",
        "kind": "OFFICIAL_FEDERAL_DATASET",
        "rights": "FEDERAL_PUBLIC_DOWNLOAD_RIGHTS_SCOPE_REVIEW_PENDING",
        "lineage": "CFS_FAF_2022_INTERDEPENDENT", "protocol": "M7-04",
    },
    "census.cfs2022.api": {
        "url": "https://www.census.gov/data/developers/data-sets/cfs/2022.html",
        "grain": "PUBLISHED_AGGREGATE_STATISTICS",
        "kind": "OFFICIAL_FEDERAL_DATASET",
        "rights": "FEDERAL_API_AND_REUSE_TERMS_REVIEW_PENDING",
        "lineage": "CFS_FAF_2022_INTERDEPENDENT", "protocol": "M7-04",
    },
    "census.cfs2022.tables": {
        "url": "https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html",
        "grain": "PUBLISHED_AGGREGATE_STATISTICS",
        "kind": "OFFICIAL_FEDERAL_DATASET",
        "rights": "PUBLISHED_TABLE_TERMS_REVIEW_PENDING",
        "lineage": "CFS_FAF_2022_INTERDEPENDENT", "protocol": "M7-04",
    },
    "edifabric.edi210.sample": {
        "url": "https://www.edifabric.com/docs/transactions/x12-210.html",
        "grain": "PUBLISHED_EDI_EXAMPLE_NOT_A_REAL_VERIFIED_INVOICE",
        "kind": "PUBLISHER_ILLUSTRATIVE_EXAMPLE",
        "rights": "THIRD_PARTY_REPUBLICATION_LICENSE_NOT_ESTABLISHED",
        "lineage": "EDIFABRIC_210_EXAMPLE_ORIGIN_UNCERTAIN", "protocol": "M7-05",
    },
    "github.freighttrust.x12examples": {
        "url": "https://github.com/freighttrust/X12-Examples",
        "grain": "PUBLISHED_EDI_EXAMPLE_NOT_A_REAL_VERIFIED_INVOICE",
        "kind": "PUBLIC_GITHUB_REPOSITORY",
        "rights": "NO_ROOT_LICENSE_OBSERVED_AND_UPSTREAM_PROVENANCE_UNRESOLVED",
        "lineage": "EDIFABRIC_210_EXAMPLE_ORIGIN_UNCERTAIN", "protocol": "M7-05",
    },
    "x12.210.definition": {
        "url": "https://x12.org/node/4210",
        "grain": "STANDARD_DESCRIPTION_ONLY",
        "kind": "STANDARDS_DEFINITION",
        "rights": "PROPRIETARY_STANDARD_CONTENT_RIGHTS_NOT_CLEARED",
        "lineage": "X12_STANDARDS_DESCRIPTION_REFERENCE", "protocol": "M7-05",
    },
}
PRIORITY = (
    "census.cfs2022.pums", "bts.faf6.regional", "edifabric.edi210.sample",
    "github.freighttrust.x12examples", "census.cfs2022.api",
    "census.cfs2022.tables", "x12.210.definition",
)


def _iso(value: object) -> date:
    if type(value) is not str:
        raise ValueError("ISO date string required")
    day = date.fromisoformat(value)
    if day.isoformat() != value:
        raise ValueError("canonical ISO date required")
    return day


def _https_url(value: object) -> bool:
    if type(value) is not str or len(value) > 450 or any(ord(c) < 32 for c in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and bool(u.hostname) and
                u.username is None and u.password is None and u.port is None and
                not u.fragment and not u.query and not u.path.startswith("//"))
    except ValueError:
        return False


def _text(value: object, minimum: int = 20, maximum: int = 2500) -> bool:
    return type(value) is str and minimum <= len(value.strip()) <= maximum


def validate_catalog(book: dict, protocols: dict, *, as_of: date) -> list[str]:
    """Fail closed on invented source authority, licenses, datasets and ground truth."""
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["schema_version must be 1"]
    errors: list[str] = []
    top_keys = {
        "schema_version", "scope", "research_as_of", "purpose", "selection_policy",
        "data_imports_authorized", "automatic_network_requests_authorized",
        "real_invoice_accuracy_claims_authorized", "actual_invoice_benchmark_count",
        "datasets_reproduced_locally", "sources",
    }
    if set(book) != top_keys:
        errors.append("unexpected top-level source policy fields")
    if book.get("scope") != SCOPE:
        errors.append("source catalog outside frozen research-only scope")
    try:
        if _iso(book.get("research_as_of")) > as_of:
            errors.append("future metadata review date")
    except ValueError:
        errors.append("invalid metadata review date")
    for key in ("purpose", "selection_policy"):
        if not _text(book.get(key), 40):
            errors.append(f"missing explicit {key}")
    for key in ("data_imports_authorized", "automatic_network_requests_authorized",
                "real_invoice_accuracy_claims_authorized"):
        if book.get(key) is not False:
            errors.append(f"unauthorized {key}")
    for key in ("actual_invoice_benchmark_count", "datasets_reproduced_locally"):
        if type(book.get(key)) is not int or book[key] != 0:
            errors.append(f"{key} must be exact zero; no data acquired")
    if (type(protocols) is not dict or
        protocols.get("scope") != "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY" or
        type(protocols.get("external_studies_executed")) is not int or
        protocols.get("external_studies_executed") != 0 or
        protocols.get("public_performance_claims_allowed") is not False or
        protocols.get("external_actions_allowed") is not False or
        protocols.get("new_lab_created") is not False or
        protocols.get("receipt_sha256") != canon_hash({
            k:v for k,v in protocols.items() if k != "receipt_sha256"
        })):
        return errors + ["unmodified, held Mission 7 protocol report required"]
    prototype_ids = {p.get("experiment_id") for p in protocols.get("protocols", [])
                     if isinstance(p, dict)}
    if len(prototype_ids) != 6 or not {"M7-04", "M7-05"} <= prototype_ids:
        return errors + ["six Mission 7 protocol dependencies missing"]
    rows = book.get("sources")
    if type(rows) is not list or len(rows) != len(EXPECTED):
        return errors + ["exact seven-source review snapshot required"]
    seen = set()
    for i, s in enumerate(rows):
        if type(s) is not dict:
            errors.append(f"source {i}: record must be object")
            continue
        ident = s.get("id")
        if type(ident) is not str or ident not in EXPECTED or ident in seen:
            errors.append(f"source {i}: duplicate/unknown identifier")
            continue
        seen.add(ident)
        ref = EXPECTED[ident]
        if set(s) != REQUIRED_SOURCE_KEYS:
            errors.append(f"{ident}: unexpected fields or missing source gate")
            continue
        if s["url"] != ref["url"] or not _https_url(s["url"]):
            errors.append(f"{ident}: source URL provenance mismatched")
        if not _https_url(s["documentation_url"]):
            errors.append(f"{ident}: unsafe documentation URL")
        try:
            url_host = (urlsplit(s["documentation_url"]).hostname
                        if type(s["documentation_url"]) is str else None)
        except ValueError:
            url_host = None
        allowed_hosts = {"www.census.gov", "www.bts.gov", "rosap.ntl.bts.gov",
                         "support.edifabric.com", "github.com", "x12.org"}
        if url_host not in allowed_hosts:
            errors.append(f"{ident}: documentation host outside approved review set")
        if s["source_kind"] != ref["kind"] or s["source_kind"] not in SOURCE_KINDS:
            errors.append(f"{ident}: authority/source type changed")
        if s["grain"] != ref["grain"] or s["grain"] not in DATA_GRAINS:
            errors.append(f"{ident}: dataset grain laundered")
        if s["rights_evidence"] != ref["rights"]:
            errors.append(f"{ident}: rights falsely cleared or altered")
        if s["lineage_family"] != ref["lineage"]:
            errors.append(f"{ident}: source dependence concealed")
        if s["linked_protocols"] != [ref["protocol"]]:
            errors.append(f"{ident}: unapproved research protocol claim")
        for key in ("name", "publisher", "availability", "file_size_display",
                    "allowable_research_track"):
            if not _text(s[key], minimum=8, maximum=300):
                errors.append(f"{ident}: missing scoped {key}")
        for key in ("source_basis", "limitations", "next_action"):
            if not _text(s[key], minimum=50):
                errors.append(f"{ident}: missing bounded {key}")
        try:
            if _iso(s["reviewed_on"]) > as_of:
                errors.append(f"{ident}: source metadata observed in future")
            if s["release_on"] is not None:
                if _iso(s["release_on"]) > _iso(s["reviewed_on"]):
                    errors.append(f"{ident}: release date after source observation")
        except ValueError:
            errors.append(f"{ident}: invalid source or release date")
        for flag in FALSE_SOURCE_FLAGS:
            if s[flag] is not False:
                errors.append(f"{ident}: forbidden verification/admission claim {flag}")
        if s["checksum_of_downloaded_bytes"] is not None:
            errors.append(f"{ident}: no bytes downloaded, so byte hash cannot exist")
    if seen != set(EXPECTED):
        errors.append("one or more original public source IDs missing")
    return errors


def build_readiness(*, as_of: date, book: dict | None = None,
                    protocols: dict | None = None) -> dict:
    if book is None:
        book = json.loads(BOOK.read_text(encoding="utf-8"))
    if protocols is None:
        protocols = build_protocol_report(as_of=as_of)
    errors = validate_catalog(book, protocols, as_of=as_of)
    if errors:
        raise ValueError("INVALID_PUBLIC_FREIGHT_SOURCE_CATALOG: " + "; ".join(errors))
    by_id = {s["id"]: s for s in book["sources"]}
    review = []
    for position, ident in enumerate(PRIORITY, start=1):
        row = by_id[ident]
        review.append({
            "source_id": ident,
            "research_priority_ordinal_not_market_quality": position,
            "publisher": row["publisher"],
            "name": row["name"],
            "source_url": row["url"],
            "documented_grain": row["grain"],
            "license_status": row["rights_evidence"],
            "data_access": row["availability"],
            "release_on": row["release_on"],
            "reviewed_on": row["reviewed_on"],
            "related_methods": row["linked_protocols"],
            "lineage_family": row["lineage_family"],
            "next_operator_review": row["next_action"],
            "limitations": row["limitations"],
            "status": "PUBLIC_METADATA_CATALOGUED_NOT_ADMITTED",
            "real_invoice_ground_truth_available": False,
            "can_run_customer_accuracy_benchmark": False,
            "dataset_bytes_examined": False,
            "license_cleared": False,
            "import_or_republish_allowed": False,
            "decision_blockers": [
                "DOWNLOAD_AND_SHA256_SOURCE_BYTES_ABSENT",
                "SOURCE_SPECIFIC_LICENSE_AND_REUSE_SCOPE_NOT_APPROVED",
                "PRIVACY_SECURITY_AND_SAMPLE_SCOPE_REVIEW_NOT_COMPLETED",
                "NO_INDEPENDENT_BILLED_VS_CONTRACT_VS_PAID_REFERENCE_LABELS",
            ],
        })
    counts = dict(sorted(Counter(s["grain"] for s in book["sources"]).items()))
    lineage_counts = dict(sorted(Counter(s["lineage_family"]
                                        for s in book["sources"]).items()))
    method_coverage = {}
    for i in range(1, 7):
        pid = f"M7-0{i}"
        linked = [r["source_id"] for r in review if pid in r["related_methods"]]
        method_coverage[pid] = {
            "metadata_leads": linked, "candidate_count": len(linked),
            "independent_real_world_benchmark_sets": 0,
            "method_is_verified": False,
        }
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "LAB14_PUBLIC_DATA_DISCOVERY_AND_RIGHTS_HOLD",
        "catalog_sha256": canon_hash(book),
        "protocol_report_sha256": protocols["receipt_sha256"],
        "source_leads": len(review),
        "source_grain_counts": counts,
        "lineage_family_counts": lineage_counts,
        "related_protocols": method_coverage,
        "review_queue": review,
        "rights_cleared_reuse_count": 0,
        "datasets_imported": 0,
        "invoice_ground_truth_benchmarks": 0,
        "independently_verified_recovery_benchmarks": 0,
        "live_customer_or_carrier_data_used": False,
        "external_source_content_fetched": False,
        "automated_network_or_schedule": False,
        "public_performance_claims_allowed": False,
        "new_lab_created": False,
        "existing_lab_number": 14,
        "limitations": (
            "Federal shipment estimates and public-use samples do not contain a "
            "verified carrier invoice-versus-contract overcharge oracle. EDI "
            "examples and public repositories are not reusable by default. "
            "An unsourced data set, privacy review, rights grant, file digest "
            "or verified customer result cannot be invented by this registry."
        ),
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def render_html(report: dict) -> str:
    cards = []
    for r in report["review_queue"]:
        cards.append(
            '<article><small>RESEARCH RANK ' +
            str(r["research_priority_ordinal_not_market_quality"]) +
            ' · NOT ADMITTED</small><h2>' + escape(r["name"]) +
            '</h2><p>' + escape(r["publisher"]) + '</p><p><b>Grain:</b> ' +
            escape(r["documented_grain"].replace("_", " ")) +
            '</p><p><b>Rights status:</b> ' + escape(r["license_status"]) +
            '</p><p><b>Limitation:</b> ' + escape(r["limitations"]) +
            '</p><p><b>Operator review:</b> ' + escape(r["next_operator_review"]) +
            '</p><a href="' + escape(r["source_url"], quote=True) +
            '" rel="noopener noreferrer">Inspect original source</a></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Freight Data Readiness</title><style>'
        '*{box-sizing:border-box}body{margin:0;background:#f5f8f6;'
        'font:15px/1.55 system-ui,-apple-system,sans-serif;color:#182d24}'
        'main{max-width:1100px;margin:auto;padding:30px 18px 72px}'
        'h1{font-size:clamp(30px,5vw,48px);letter-spacing:-.04em;line-height:1.13}'
        'article{background:#fff;border:1px solid #d9e6db;border-radius:16px;'
        'padding:22px;margin:18px 0}h2{font-size:22px;line-height:1.25}'
        'small{font-size:12px;letter-spacing:.10em;color:#52765e}'
        'a{color:#136b45;text-decoration:underline}p{overflow-wrap:anywhere}'
        '</style></head><body><main><small>RETALLY / LAB 14 / MISSION 9</small>'
        '<h1>Real data needs real provenance.</h1>'
        '<p>Seven public source leads; zero approved data imports, zero customer '
        'invoice error labels, zero externally proven recovery results. All '
        'rights, content integrity, privacy and benchmark gates remain blocked.</p>'
        '<p>BTS/CFS/FAF datasets share underlying data and must not be counted '
        'as independent freight markets. Public EDI examples and GitHub source '
        'are not automatically licensed or evidence of actual billing errors.</p>' +
        "".join(cards) + '<footer><small>Metadata receipt: ' +
        escape(report["receipt_sha256"]) +
        ' · Local consistency only, not third-party verification.</small>'
        '</footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_readiness(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "freight_data_readiness.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "freight_data_readiness.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({"leads": report["source_leads"],
                      "imports": report["datasets_imported"],
                      "real_invoice_benchmarks": report["invoice_ground_truth_benchmarks"],
                      "receipt": report["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
