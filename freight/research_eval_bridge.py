"""Bridge unified RETALLY public-source discovery into the fixed FreightRecovery eval pack.

This is a metadata candidate feed. Source URLs and historical decisions do NOT
constitute buyer-specific invoice truth, license grants or recovery permission.
Only legacy-validated metadata is admitted, and the fixed evaluation pack is
replayed without altering its nine reference cases.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

from freight import lab15_acquisition, lab15_evidence_harvester, unified_research_lab
from freight.public_freight_corpus import SOURCES as OLD_SOURCES
from freight.public_freight_corpus import aggregate_research_receipt
from freight.real_world_eval_v1 import aggregate_receipt, load_manifest, validate_manifest

SCHEMA = 1
KIND = "UNVERIFIED_FREIGHT_EVALUATION_CANDIDATES"
SCOPE = "PUBLIC_METADATA_ONLY_NO_CUSTOMER_CLAIMS"
STATUS = "RIGHTS_AND_INDEPENDENT_EVIDENCE_PENDING"
ORIGINS = frozenset({"unified", "lab15_acquisition", "lab15_harvester"})
MAX_CANDIDATES = 10000
HERE = Path(__file__).resolve().parent
UNIFIED = HERE / "research_lab" / "leads.json"
LEGACY = HERE / "lab15" / "evidence_ledger.json"
HARVESTER = HERE / "research" / "lab15_candidate_ledger.json"
FEED = HERE / "research_lab" / "evaluation_candidates.json"


class FeedError(ValueError):
    """Reject forged or inappropriately promoted research evidence."""


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _seen(raw: str) -> str:
    if not isinstance(raw, str) or len(raw) < 10 or raw[:10].count("-") != 2:
        raise FeedError("INVALID_SOURCE_DATE")
    try:
        parsed = date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise FeedError("INVALID_SOURCE_DATE") from exc
    return parsed.isoformat()


def _publishable_locator(url: str) -> str | None:
    """Only exact public allowlisted URL paths; never preserve query/document IDs.

    Legacy sources may include dataset IDs or user-linked query strings.
    Keep a source-locator SHA to deduplicate them, not their raw contents.
    """
    try:
        candidate = unified_research_lab.safe_url(url)
    except (unified_research_lab.ResearchError, ValueError, TypeError):
        return None
    parsed = urlsplit(candidate)
    if parsed.query or parsed.fragment or "@" in parsed.path or "%40" in parsed.path.lower():
        return None
    return candidate


def _reference_urls() -> tuple[dict[str, list[str]], str]:
    manifest = load_manifest()
    cases = validate_manifest(manifest)
    lookup: dict[str, list[str]] = {}
    for key, row in cases.items():
        # Vendor invoice roots are not document identities; never infer an
        # existing invoice case from a vendor's domain or matching invoice host.
        if row["category"] != "PUBLIC_INVOICE_FACE":
            lookup.setdefault(row["source_url"], []).append("v1:" + key)
    for item in OLD_SOURCES:
        lookup.setdefault(item.url, []).append("public:" + item.key)
    return {url: sorted(set(ids)) for url, ids in lookup.items()}, digest(manifest)


def _unified(doc: dict) -> list[tuple[str, str, str, str]]:
    unified_research_lab.validate_ledger(doc)
    return [
        (r["url"], "unified", _seen(r["first_seen"]), "freightrecovery")
        for r in doc["entries"] if "freightrecovery" in r["engines"]
    ]


def _legacy(doc: dict) -> list[tuple[str, str, str, str]]:
    lab15_acquisition.validate_ledger(doc)
    return [
        (r["url"], "lab15_acquisition", _seen(r["first_seen"]), "freightrecovery")
        for r in doc["records"]
    ]


def _harvested(doc: dict) -> list[tuple[str, str, str, str]]:
    lab15_evidence_harvester.validate_ledger(doc)
    return [
        (r["url"], "lab15_harvester", _seen(r["first_seen"]), "freightrecovery")
        for r in doc["leads"]
    ]


def build_feed(unified: dict, legacy: dict, harvested: dict) -> dict:
    """Validate each independent source ledger before using any row."""
    inputs = _unified(unified) + _legacy(legacy) + _harvested(harvested)
    references, manifest_sha = _reference_urls()
    by_id: dict[str, dict] = {}
    for url, origin, first_seen, engine in inputs:
        key = sha256(url.encode("utf-8")).hexdigest()
        current = by_id.get(key)
        if current is None:
            if len(by_id) >= MAX_CANDIDATES:
                raise FeedError("TOO_MANY_CANDIDATES")
            by_id[key] = {
                "id": key,
                "url": _publishable_locator(url),
                "publisher_host": urlsplit(url).hostname,
                "first_seen": first_seen,
                "source_ledgers": [origin],
                "reference_case_ids": references.get(url, []),
                "status": STATUS,
                "original_source_bytes_sha256": None,
                "controlling_rate_verified": False,
                "independent_payment_verified": False,
                "customer_invoice_ground_truth": False,
                "commercial_use_authorized": False,
                "automatic_recovery_authorized": False,
            }
        else:
            # Same URL may legitimately appear in all three collectors.
            if (current["publisher_host"] != urlsplit(url).hostname
                    or current["url"] != _publishable_locator(url)):
                raise FeedError("SOURCE_ID_COLLISION")
            current["source_ledgers"] = sorted(set(current["source_ledgers"]) | {origin})
            current["first_seen"] = min(current["first_seen"], first_seen)
    candidates = sorted(by_id.values(), key=lambda x: x["id"])
    return {
        "schema_version": SCHEMA,
        "kind": KIND,
        "scope": SCOPE,
        "baseline_pack_version": "1.0.0",
        "baseline_pack_metadata_sha256": manifest_sha,
        "upstream_ledger_hashes": {
            "unified_entries_sha256": unified["entries_sha256"],
            "lab15_acquisition_records_sha256": digest(legacy["records"]),
            "lab15_harvester_digest_sha256": harvested["digest_sha256"],
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "candidates_sha256": digest(candidates),
        "original_customer_documents_saved": False,
        "recovery_claims_authorized": False,
        "independent_new_truth_cases": 0,
        "real_customer_cash_recovered_cents": 0,
    }


def validate_feed(feed: dict) -> None:
    if type(feed) is not dict or set(feed) != {
        "schema_version", "kind", "scope", "baseline_pack_version",
        "baseline_pack_metadata_sha256", "upstream_ledger_hashes",
        "candidate_count", "candidates", "candidates_sha256",
        "original_customer_documents_saved", "recovery_claims_authorized",
        "independent_new_truth_cases", "real_customer_cash_recovered_cents",
    }:
        raise FeedError("INVALID_FEED_SCHEMA")
    if (type(feed["schema_version"]) is not int or feed["schema_version"] != SCHEMA
            or feed["kind"] != KIND or feed["scope"] != SCOPE
            or feed["baseline_pack_version"] != "1.0.0"
            or feed["original_customer_documents_saved"] is not False
            or feed["recovery_claims_authorized"] is not False
            or type(feed["independent_new_truth_cases"]) is not int
            or feed["independent_new_truth_cases"] != 0
            or type(feed["real_customer_cash_recovered_cents"]) is not int
            or feed["real_customer_cash_recovered_cents"] != 0):
        raise FeedError("FORGED_RESEARCH_APPROVAL")
    refs, correct_manifest = _reference_urls()
    if feed["baseline_pack_metadata_sha256"] != correct_manifest:
        raise FeedError("BASELINE_PACK_CHANGED")
    digests = feed["upstream_ledger_hashes"]
    if (type(digests) is not dict or set(digests) != {
        "unified_entries_sha256", "lab15_acquisition_records_sha256",
        "lab15_harvester_digest_sha256"
    } or any(not isinstance(x, str) or len(x) != 64 or
             any(ch not in "0123456789abcdef" for ch in x)
             for x in digests.values())):
        raise FeedError("INVALID_UPSTREAM_DIGESTS")
    rows = feed["candidates"]
    if (type(rows) is not list or len(rows) > MAX_CANDIDATES
            or type(feed["candidate_count"]) is not int
            or feed["candidate_count"] != len(rows)
            or feed["candidates_sha256"] != digest(rows)):
        raise FeedError("CANDIDATE_FEED_TAMPERED")
    seen = set()
    expected_keys = {
        "id", "url", "publisher_host", "first_seen", "source_ledgers",
        "reference_case_ids", "status", "original_source_bytes_sha256",
        "controlling_rate_verified", "independent_payment_verified",
        "customer_invoice_ground_truth", "commercial_use_authorized",
        "automatic_recovery_authorized",
    }
    for item in rows:
        if type(item) is not dict or set(item) != expected_keys:
            raise FeedError("CANDIDATE_SCHEMA_BYPASS")
        key = item["id"]
        if (not isinstance(key, str) or len(key) != 64
                or any(c not in "0123456789abcdef" for c in key)
                or key in seen):
            raise FeedError("INVALID_SOURCE_ID")
        seen.add(key)
        url = item["url"]
        if url is not None and (
            not isinstance(url, str) or _publishable_locator(url) != url
            or sha256(url.encode("utf-8")).hexdigest() != key
            or urlsplit(url).hostname != item["publisher_host"]
        ):
            raise FeedError("UNTRUSTED_OR_INCORRECT_PUBLIC_URL")
        if (not isinstance(item["publisher_host"], str) or
                not item["publisher_host"] or not isinstance(item["first_seen"], str)
                or _seen(item["first_seen"]) != item["first_seen"]
                or item["status"] != STATUS
                or item["original_source_bytes_sha256"] is not None
                or any(item[k] is not False for k in (
                    "controlling_rate_verified", "independent_payment_verified",
                    "customer_invoice_ground_truth", "commercial_use_authorized",
                    "automatic_recovery_authorized",
                ))):
            raise FeedError("SOURCE_FALSE_PROOF")
        if (type(item["source_ledgers"]) is not list
                or item["source_ledgers"] != sorted(set(item["source_ledgers"]))
                or not item["source_ledgers"] or
                any(o not in ORIGINS for o in item["source_ledgers"])):
            raise FeedError("ORIGIN_PROVENANCE_INVALID")
        if (type(item["reference_case_ids"]) is not list
                or item["reference_case_ids"] != sorted(set(item["reference_case_ids"]))
                or any(not isinstance(x, str) or not x.startswith(("public:", "v1:"))
                       for x in item["reference_case_ids"])):
            raise FeedError("FALSE_REFERENCE_IDENTITIES")
        if url is not None and item["reference_case_ids"] != refs.get(url, []):
            raise FeedError("FORGED_REFERENCE_CASE")
    if [row["id"] for row in rows] != sorted(seen):
        raise FeedError("CANDIDATE_ORDER_INVALID")


def verify_against_sources(feed: dict, unified: dict, legacy: dict, harvested: dict) -> None:
    validate_feed(feed)
    expected = build_feed(unified, legacy, harvested)
    if feed != expected:
        raise FeedError("CANDIDATES_NOT_DERIVED_FROM_SOURCE_LEDGERS")


def evaluate_feed(feed: dict) -> dict:
    """Run both *fixed* real-data reference suites; newly found data stays held."""
    validate_feed(feed)
    fixed = aggregate_receipt()
    prior = aggregate_research_receipt()
    if (fixed["public_real_world_source_leads"] != 9
            or fixed["verified_new_customer_recovery_cents"] != 0
            or prior["source_leads"] != 5
            or prior["verified_new_customer_recovery_cents"] != 0):
        raise FeedError("NATIVE_ENGINE_EVIDENCE_GATES_FAILED")
    return {
        "classification": "LIVE_DISCOVERED_LEADS_HELD_FIXED_EVAL_REPLAYED",
        "candidate_feed_sha256": feed["candidates_sha256"],
        "upstream_ledger_hashes": feed["upstream_ledger_hashes"],
        "discovered_candidate_sources": feed["candidate_count"],
        "references_matched_to_existing_fixed_cases": sum(
            bool(x["reference_case_ids"]) for x in feed["candidates"]
        ),
        "unmatched_source_candidates_waiting_for_adjudication": sum(
            not x["reference_case_ids"] for x in feed["candidates"]
        ),
        "all_candidate_sources_on_rights_and_truth_hold": all(
            x["status"] == STATUS for x in feed["candidates"]
        ),
        "fixed_v1_real_world_cases_replayed": 9,
        "prior_official_source_case_families_replayed": 5,
        "new_source_numeric_claims_evaluated": 0,
        "independently_adjudicated_new_invoices": 0,
        "verified_new_customer_recovery_cents": 0,
        "real_precision": None,
        "real_recall": None,
        "customer_data_release_authorized": False,
    }


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--unified", type=Path, default=UNIFIED)
    parser.add_argument("--legacy", type=Path, default=LEGACY)
    parser.add_argument("--harvest", type=Path, default=HARVESTER)
    parser.add_argument("--feed", type=Path, default=FEED)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    unified, legacy, harvested = (
        _read(args.unified), _read(args.legacy), _read(args.harvest)
    )
    expected = build_feed(unified, legacy, harvested)
    validate_feed(expected)
    if args.action == "build":
        text = json.dumps(expected, sort_keys=True, indent=2) + "\n"
        if not args.feed.exists() or args.feed.read_text(encoding="utf-8") != text:
            args.feed.parent.mkdir(parents=True, exist_ok=True)
            args.feed.write_text(text, encoding="utf-8")
    else:
        verify_against_sources(_read(args.feed), unified, legacy, harvested)
    report = evaluate_feed(expected)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
