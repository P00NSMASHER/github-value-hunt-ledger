"""Bounded metadata-only research quality receipt; never proof of reusable evidence.

This receipt is a structural audit of untrusted public *source pointers*.
No provider documents, personal identifiers, ratings, invoices, or labels are
downloaded, stored, promoted, or inferred by this module.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from freight.unified_research_lab import (
    ENGINES, LEDGER, ROOT, ResearchError, read_ledger, validate_ledger,
)

OUTPUT = ROOT / "source_health_v1.json"
OFFICIAL_HOSTS = frozenset({
    "www.gao.gov", "media.cadc.uscourts.gov", "www2.fmc.gov", "www.fmc.gov",
    "www.sec.gov", "www.stb.gov", "www.eia.gov", "data.cityofnewyork.us",
    "sam.gov", "api.usaspending.gov", "www.penninecare.nhs.uk",
    "catalog.data.gov", "psc.ky.gov",
})
CATALOG_HOSTS = frozenset({"github.com", "zenodo.org"})
PERMIT_KNOWN_OFFTOPIC = frozenset({
    "43nn-pn8j", "pitm-atqc", "qcdj-rwhu", "fpeh-f7ci",
})
PERMIT_PATH_SUSPECT = re.compile(
    r"(restaurant|inspection|food[-_]?safety|dine[-_]?safe|yelp)", re.I
)


def _day(s: str) -> date:
    try:
        if type(s) is not str or date.fromisoformat(s).isoformat() != s:
            raise ValueError("not canonical")
        return date.fromisoformat(s)
    except ValueError as exc:
        raise ResearchError("INVALID_SOURCE_OBSERVATION_DATE") from exc


def build_receipt(ledger: dict, as_of: date) -> dict:
    """Compute aggregate, non-authoritative source readiness counters."""
    if type(as_of) is not date:
        raise ResearchError("INVALID_RECEIPT_DATE")
    validate_ledger(ledger)
    rows = ledger["entries"]
    by_engine = {e: Counter() for e in ENGINES}
    domain_counts = Counter()
    first_seen_last7 = 0
    off_topic = 0
    earliest = None
    latest = None
    cross_lane = 0
    for row in rows:
        observed = _day(row["first_seen"])
        if observed > as_of:
            raise ResearchError("FUTURE_DATED_SOURCE_OBSERVATION")
        earliest = min(observed, earliest) if earliest else observed
        latest = max(observed, latest) if latest else observed
        if as_of - timedelta(days=6) <= observed <= as_of:
            first_seen_last7 += 1
        if len(row["engines"]) > 1:
            cross_lane += 1
        host = urlsplit(row["url"]).hostname
        domain_counts[host] += 1
        for engine in row["engines"]:
            counts = by_engine[engine]
            counts["source_pointers"] += 1
            if host in OFFICIAL_HOSTS:
                counts["official_publisher_host_only"] += 1
            elif host in CATALOG_HOSTS:
                counts["third_party_catalog_host_only"] += 1
            else:
                counts["other_allowlisted_host_only"] += 1
            if engine == "permitplate" and (
                (host == "github.com" and PERMIT_PATH_SUSPECT.search(
                    urlsplit(row["url"]).path))
                or (host == "data.cityofnewyork.us"
                    and urlsplit(row["url"]).path.rsplit("/", 1)[-1]
                    in PERMIT_KNOWN_OFFTOPIC)
            ):
                counts["wrong_topic_url_heuristic_review_only"] += 1
                off_topic += 1
    lane_receipts = {}
    for engine in ENGINES:
        counts = by_engine[engine]
        lane_receipts[engine] = {
            "source_pointers": counts["source_pointers"],
            "official_publisher_host_only": counts["official_publisher_host_only"],
            "third_party_catalog_host_only": counts["third_party_catalog_host_only"],
            "other_allowlisted_host_only": counts["other_allowlisted_host_only"],
            "wrong_topic_url_heuristic_review_only":
                counts["wrong_topic_url_heuristic_review_only"],
            "independently_labeled_test_cases": 0,
            "commercial_reuse_confirmed": False,
            "usable_as_engine_ground_truth": False,
            "readiness": "UNVERIFIED_SOURCE_METADATA_ONLY",
        }
    return {
        "schema_version": 1,
        "receipt_type": "UNVERIFIED_SOURCE_CANDIDATE_QUALITY_COUNTS",
        "as_of_utc_date": as_of.isoformat(),
        "source_ledger_entries_sha256": ledger["entries_sha256"],
        "unique_source_pointers": len(rows),
        "cross_engine_shared_pointers": cross_lane,
        "first_seen_in_last_seven_calendar_days": first_seen_last7,
        "earliest_first_seen": earliest.isoformat() if earliest else None,
        "latest_first_seen": latest.isoformat() if latest else None,
        "publisher_host_counts": dict(sorted(domain_counts.items())),
        "engines": lane_receipts,
        "permitplate_wrong_topic_heuristic_flags": off_topic,
        "source_document_bytes_stored": 0,
        "verified_original_document_benchmark_truth_cases": 0,
        "independent_payment_verification_cases": 0,
        "verified_recovered_cash_cents": 0,
        "commercial_recovery_allowed": False,
        "customer_communication_actions": 0,
        "production_changes": 0,
        "limitations": [
            "Publisher host identity does not establish source authenticity, rights, relevance or ground truth.",
            "URL-only topic flags are screening heuristics, not verified classifications.",
            "Newly discovered pointers are not new independently usable test cases.",
        ],
    }


def rendered_receipt(ledger: dict, as_of: date) -> str:
    return json.dumps(build_receipt(ledger, as_of), sort_keys=True, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--as-of", type=str)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if args.as_of:
            parser.error("--as-of cannot override a published receipt")
        if not args.output.is_file():
            raise ResearchError("RESEARCH_HEALTH_RECEIPT_MISSING")
        existing = args.output.read_text(encoding="utf-8")
        doc = json.loads(existing)
        as_of = _day(doc["as_of_utc_date"])
        if as_of > datetime.now(timezone.utc).date():
            raise ResearchError("FUTURE_DATED_RESEARCH_RECEIPT")
        if existing != rendered_receipt(read_ledger(args.ledger), as_of):
            raise ResearchError("RESEARCH_HEALTH_RECEIPT_DRIFT")
        print(json.dumps({"verified": True, "as_of": as_of.isoformat(),
                          "scope": "UNVERIFIED_SOURCE_METADATA_ONLY"}))
        return
    as_of = _day(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    if as_of > datetime.now(timezone.utc).date():
        raise ResearchError("FUTURE_DATED_RESEARCH_RECEIPT")
    receipt = rendered_receipt(read_ledger(args.ledger), as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_name(args.output.name + ".tmp")
    temp.write_text(receipt, encoding="utf-8")
    temp.replace(args.output)
    document = json.loads(receipt)
    print(json.dumps({"unique_source_pointers": document["unique_source_pointers"],
                      "permitplate_heuristic_review_flags":
                          document["permitplate_wrong_topic_heuristic_flags"],
                      "scope": document["receipt_type"]}, sort_keys=True))


if __name__ == "__main__":
    main()
