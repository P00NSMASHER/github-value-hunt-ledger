"""Read-only RETALLY Group catalog and organizational overlay.

Public source metadata describes a proposed operating structure. It is never a
customer register, legal-entity registry, release approval, or financial ledger.
The existing private Business OS remains the operating source of truth.
"""

from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


CATALOG_PATH = Path(__file__).with_name("RETALLY_GROUP_V1.json")
KINDS = {"business", "product_family", "venture"}
METRICS = {"qualified_leads", "paying_customers", "cash_collected", "contribution_profit"}
WORKFLOW_IDS = (
    "inquiry", "qualified", "scoped", "ready", "fulfillment",
    "quality-reviewed", "delivered", "closed",
)
INITIAL_SERVICES = {
    "freight", "accounts-payable", "warranty-credit", "procurement",
    "rebates", "parcel", "utilities",
}
_ID = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")
_PRIVATE_SOURCE_KEY = re.compile(r"retally-src-[0-9]{8}-[a-z0-9-]+\Z")


class GroupCatalogError(ValueError):
    """The public planning catalog is invalid or asserts operating authority."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GroupCatalogError(message)


def _text(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")
    return value


def _keys(value: Any, required: set[str], label: str, optional: set[str] | None = None) -> None:
    """Keep accidental private payloads out of every public record container."""
    _require(isinstance(value, Mapping), f"{label} must be an object")
    present = set(value)
    _require(required <= present, f"{label} is missing required fields")
    _require(present <= required | (optional or set()), f"{label} has unexpected fields")


def _rows(value: Any, label: str) -> list[dict[str, Any]]:
    _require(isinstance(value, list), f"{label} must be a list")
    ids = set()
    for row in value:
        _require(isinstance(row, dict), f"{label} row must be an object")
        key = row.get("id")
        _require(isinstance(key, str) and bool(_ID.fullmatch(key)), f"invalid {label} id")
        _require(key not in ids, f"duplicate {label} id: {key}")
        ids.add(key)
    return value


def _date(value: Any, label: str) -> date:
    _require(isinstance(value, str), f"{label} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise GroupCatalogError(f"{label} must be an ISO date") from exc
    _require(parsed.isoformat() == value, f"{label} must use YYYY-MM-DD")
    return parsed


def _sources(row: dict[str, Any], as_of: date) -> None:
    sources = row.get("sources")
    _require(isinstance(sources, list), "sources must be a list")
    for source in sources:
        _keys(source, {"label", "url", "observed_on"}, "source", {"git_blob_sha"})
        _text(source.get("label"), "source label")
        url = _text(source.get("url"), "source URL")
        _require(not any(ord(c) < 32 or c == "\\" for c in url), "unsafe source URL")
        try:
            parsed = urlsplit(url)
            safe = (parsed.scheme == "https" and parsed.netloc == "github.com"
                    and parsed.username is None and parsed.password is None
                    and parsed.port is None and parsed.path.startswith("/P00NSMASHER/"))
        except ValueError:
            safe = False
        _require(safe, "sources must be public owner GitHub HTTPS references")
        _require(_date(source.get("observed_on"), "source date") <= as_of,
                 "source date cannot be later than catalog snapshot")
        if "git_blob_sha" in source:
            _require(isinstance(source["git_blob_sha"], str)
                     and bool(re.fullmatch(r"[0-9a-f]{40}", source["git_blob_sha"])),
                     "invalid source blob hash")


def _private_sources(row: dict[str, Any], as_of: date, record_keys: set[str]) -> None:
    """Accept public review references, never private provider IDs or URLs."""
    refs = row.get("private_source_refs", [])
    _require(isinstance(refs, list), "private_source_refs must be a list")
    for ref in refs:
        _keys(ref, {"record_key", "label", "source_as_of", "reviewed_on"}, "private source reference")
        key = ref.get("record_key")
        _require(isinstance(key, str) and len(key) <= 100
                 and bool(_PRIVATE_SOURCE_KEY.fullmatch(key)), "invalid private source record key")
        _require(key not in record_keys, "duplicate private source record key")
        record_keys.add(key)
        label = _text(ref.get("label"), "private source label")
        _require(label.isprintable(), "private source label must be printable single-line text")
        source_date = _date(ref.get("source_as_of"), "private source date")
        review_date = _date(ref.get("reviewed_on"), "private source review date")
        _require(source_date <= review_date, "private source date cannot be later than its review date")
        _require(review_date <= as_of, "private source review date cannot be later than catalog snapshot")


def validate_catalog(catalog: Mapping[str, Any]) -> None:
    """Validate public planning data without conferring any production authority."""
    _require(isinstance(catalog, Mapping), "catalog must be an object")
    _keys(catalog, {
        "catalog_version", "title", "mode", "as_of", "source_repository_revision",
        "divisions", "entries", "services", "shared_systems", "workflow",
        "priorities", "boundaries", "financial_metrics", "exclusions", "authority",
    }, "catalog")
    _require(type(catalog.get("catalog_version")) is int
             and catalog["catalog_version"] == 1, "unsupported catalog version")
    _require(catalog.get("mode") == "PLANNING_PREVIEW", "catalog must remain a planning preview")
    _text(catalog.get("title"), "title")
    as_of = _date(catalog.get("as_of"), "catalog date")
    revision = catalog.get("source_repository_revision")
    _require(isinstance(revision, str) and bool(re.fullmatch(r"[0-9a-f]{40}", revision)),
             "source repository revision must be an exact Git commit")
    authority = catalog.get("authority", {})
    _keys(authority, {"planning_only", "external_actions_authorized", "public_rebrand_authorized",
                      "production_state_mutation_authorized", "registration_policy"}, "authority")
    _text(authority.get("registration_policy"), "registration policy")
    _require(authority.get("planning_only") is True, "planning_only must be true")
    for key in ("external_actions_authorized", "public_rebrand_authorized", "production_state_mutation_authorized"):
        _require(authority.get(key) is False, f"{key} must be false")
    boundaries = catalog.get("boundaries", {})
    _keys(boundaries, {"live_customer_state", "legal_identity", "public_brand_rollout",
                       "new_external_spend_cents"}, "boundaries")
    _require(boundaries.get("live_customer_state") == "NOT_CONNECTED", "public catalog cannot contain live customer state")
    _require(boundaries.get("legal_identity") == "UNVERIFIED", "catalog cannot verify legal identity")
    _require(boundaries.get("public_brand_rollout") == "PLANNED", "catalog cannot activate a rebrand")
    _require(type(boundaries.get("new_external_spend_cents")) is int
             and boundaries["new_external_spend_cents"] == 0, "new external spending must remain zero")
    metrics = catalog.get("financial_metrics")
    _require(isinstance(metrics, dict) and set(metrics) == METRICS, "invalid financial metric keys")
    _require(all(value is None for value in metrics.values()), "unconnected financial metrics must be null, never inferred zero")

    divisions = _rows(catalog.get("divisions"), "division")
    _require(len(divisions) == 4, "v1 requires four operating divisions")
    for division in divisions:
        _keys(division, {"id", "name", "purpose"}, "division")
        _text(division.get("name"), "division name")
        _text(division.get("purpose"), "division purpose")
    division_ids = {row["id"] for row in divisions}
    entries = _rows(catalog.get("entries"), "entry")
    _require(bool(entries), "catalog entries cannot be empty")
    all_slugs: set[str] = set()
    private_record_keys: set[str] = set()
    for entry in entries:
        _keys(entry, {"id", "name", "division_id", "kind", "purpose", "stage", "owner_role",
                      "next_action", "evidence_status", "sources", "candidate_production_slugs",
                      "commercial_readiness"}, "entry", {"private_source_refs"})
        for field in ("name", "purpose", "stage", "owner_role", "next_action"):
            _text(entry.get(field), f"entry {field}")
        _require(entry.get("kind") in KINDS, "invalid entry kind")
        _require(entry.get("division_id") in division_ids, "entry has an unknown division")
        _require(entry.get("commercial_readiness") == "NOT_ASSESSED", "catalog does not assess commercial readiness")
        _require(entry.get("evidence_status") in {
            "REPOSITORY_DOCUMENTED", "PRIVATE_ARTIFACT_DOCUMENTED", "CONTEXT_ONLY",
        }, "invalid evidence status")
        _sources(entry, as_of)
        _private_sources(entry, as_of, private_record_keys)
        if entry["evidence_status"] == "REPOSITORY_DOCUMENTED":
            _require(bool(entry["sources"]), "repository-documented entry needs a source")
        elif entry["evidence_status"] == "PRIVATE_ARTIFACT_DOCUMENTED":
            _require(bool(entry.get("private_source_refs")),
                     "private-artifact-documented entry needs a private source reference")
        else:
            _require("private_source_refs" not in entry,
                     "context-only entry cannot carry private_source_refs")
        slugs = entry.get("candidate_production_slugs")
        _require(isinstance(slugs, list), "candidate slugs must be a list")
        for slug in slugs:
            _require(isinstance(slug, str) and bool(_ID.fullmatch(slug)), "invalid candidate production slug")
            _require(slug not in all_slugs, "candidate production slug maps to multiple catalog entries")
            all_slugs.add(slug)

    entry_ids = {entry["id"] for entry in entries}
    services = _rows(catalog.get("services"), "service")
    for service in services:
        _keys(service, {"id", "name", "initial_rollout", "scope", "business_id",
                        "commercial_readiness"}, "service")
        _text(service.get("name"), "service name")
        _text(service.get("scope"), "service scope")
        _require(type(service.get("initial_rollout")) is bool, "initial_rollout must be a Boolean")
        _require(service.get("business_id") == "retally-recovery"
                 and "retally-recovery" in entry_ids, "recovery services require their canonical business")
        _require(service.get("commercial_readiness") == "NOT_ASSESSED", "service readiness must remain separate")
    _require({s["id"] for s in services if s["initial_rollout"]} == INITIAL_SERVICES,
             "initial rollout must match the seven selected recovery services")

    systems = _rows(catalog.get("shared_systems"), "shared system")
    _require(not entry_ids.intersection(s["id"] for s in systems), "shared systems cannot be counted as businesses")
    for system in systems:
        _keys(system, {"id", "name", "purpose", "sources"}, "shared system")
        _text(system.get("name"), "shared system name")
        _text(system.get("purpose"), "shared system purpose")
        _sources(system, as_of)
        _require(bool(system["sources"]), "shared system needs a source")
    workflow = _rows(catalog.get("workflow"), "workflow")
    _require(tuple(w["id"] for w in workflow) == WORKFLOW_IDS, "workflow stages are missing or reordered")
    for stage in workflow:
        _keys(stage, {"id", "label", "owner_role", "required_evidence"}, "workflow stage")
        _text(stage.get("label"), "workflow label")
        _text(stage.get("owner_role"), "workflow owner")
        evidence = stage.get("required_evidence")
        _require(isinstance(evidence, list) and bool(evidence), "workflow requires evidence criteria")
        for item in evidence:
            _text(item, "evidence criterion")
    priorities = _rows(catalog.get("priorities"), "priority")
    for item in priorities:
        _keys(item, {"id", "title", "owner_role", "timeframe", "status", "done_when"}, "priority")
        for field in ("title", "owner_role", "timeframe", "done_when"):
            _text(item.get(field), f"priority {field}")
        _require(item.get("status") in {"PLANNED", "IN_PROGRESS"}, "v1 priorities cannot self-declare completion")
    exclusions = catalog.get("exclusions")
    _require(isinstance(exclusions, list), "exclusions must be a list")
    for exclusion in exclusions:
        _keys(exclusion, {"scope", "reason"}, "exclusion")
        _text(exclusion.get("scope"), "exclusion scope")
        _text(exclusion.get("reason"), "exclusion reason")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    validate_catalog(catalog)
    return catalog


def build_group_view(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create a deterministic public planning view; all financial metrics stay unknown."""
    data = load_catalog() if catalog is None else copy.deepcopy(dict(catalog))
    validate_catalog(data)
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    data["catalog_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    entries = data["entries"]
    data["totals"] = {
        "businesses": sum(e["kind"] == "business" for e in entries),
        "product_families": sum(e["kind"] == "product_family" for e in entries),
        "ventures": sum(e["kind"] == "venture" for e in entries),
        "shared_systems": len(data["shared_systems"]),
        "initial_recovery_services": sum(s["initial_rollout"] for s in data["services"]),
        "expansion_recovery_services": sum(not s["initial_rollout"] for s in data["services"]),
    }
    return data


def identity_candidates(
    businesses: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Suggest exact-slug organizational links, preserving all private identities.

    Several existing rows may belong under one commercial group. This is a
    reconciliation signal, not entity canonicalization or proof of legal ownership.
    Raw names, customer data, and financial values are never copied into this view.
    """
    data = load_catalog() if catalog is None else catalog
    validate_catalog(data)
    by_slug = {slug: entry["id"] for entry in data["entries"]
               for slug in entry["candidate_production_slugs"]}
    matches: dict[str, list[str]] = {}
    seen_ids, seen_slugs = set(), set()
    unmapped = 0
    for business in businesses:
        _require(isinstance(business, Mapping), "private business row must be an object")
        raw_id = business.get("id")
        _require(raw_id is not None and not isinstance(raw_id, bool), "private business row needs an id")
        row_id = _text(str(raw_id), "private record id")
        slug = _text(business.get("slug"), "private business slug")
        _require(row_id not in seen_ids and slug not in seen_slugs, "duplicate private identity row")
        seen_ids.add(row_id)
        seen_slugs.add(slug)
        if slug in by_slug:
            matches.setdefault(by_slug[slug], []).append(row_id)
        else:
            unmapped += 1
    return {
        "mode": "READ_ONLY_IDENTITY_CANDIDATES",
        "identity_mutation_authorized": False,
        "commercial_readiness_assessed": False,
        "unmapped_record_count": unmapped,
        "matches": [
            {"catalog_id": key, "private_record_ids": sorted(ids),
             "reconciliation_required": len(ids) > 1}
            for key, ids in sorted(matches.items())
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or render the public RETALLY Group planning preview.")
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("--output", type=Path, help="New HTML preview path; existing files are never overwritten.")
    args = parser.parse_args(argv)
    view = build_group_view()
    if args.command == "validate":
        if args.output is not None:
            parser.error("--output is only supported by render")
        print(json.dumps({"valid": True, "mode": view["mode"], "totals": view["totals"],
                          "catalog_sha256": view["catalog_sha256"]}, sort_keys=True))
        return 0
    if args.output is None:
        parser.error("render requires --output")
    from ai_business_os.retally_group_dashboard import render_dashboard
    html = render_dashboard(view)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(html)
    print(json.dumps({"written": str(args.output), "mode": view["mode"],
                      "live_customer_state": "NOT_CONNECTED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
