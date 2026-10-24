"""Four-engine public-source review priorities. Metadata is NOT evaluated truth.

Ranks existing allowlisted source URLs for further provenance, rights and
independent-outcome research. Does not inspect third-party source bytes, assign
commercial permissions, label invoices, or evaluate engine predictions.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from freight.research_lab_health import CATALOG_HOSTS, OFFICIAL_HOSTS
from freight.unified_research_lab import (
    ENGINES, LEDGER, ROOT, ResearchError, digest, read_ledger, validate_ledger,
    permitplate_url_in_scope,
)

OUTPUT = ROOT / "source_review_queue_v1.json"
MAX_REVIEW_PER_ENGINE = 8
SCOPE = "PUBLIC_URL_REVIEW_ONLY_NEITHER_RIGHTS_NOR_TRUTH_APPROVED"
# Verified community-created NYC Open Data derivatives (publisher portal, 2026-10-23).
# Review-only provenance. The original NYC DOB dataset remains separately eligible.
NYC_UNENDORSED_DERIVATIVE_VIEW_IDS = frozenset({"qnmk-7xra", "un34-bxqh"})

PUBLIC_REVIEW_ANCHORS = {
    "freightrecovery": (
        "https://www.gao.gov/products/b-160344",
        "https://www.gao.gov/products/b-143246",
        # Control against the overruled 1984 ruling and controlling 1986 reconsideration.
        "https://www.gao.gov/products/b-215958",
        "https://www.gao.gov/products/b-215958-2",
        "https://www.stb.gov/reports-data/waybill/",
    ),
    "permitplate": (
        "https://data.cityofnewyork.us/d/rbx6-tga4",
        "https://data.cityofnewyork.us/d/w9ak-ipjd",
        "https://data.cityofnewyork.us/d/ipu4-2q9a",
    ),
    "capturebrief": (
        "https://sam.gov/opportunities",
        "https://api.usaspending.gov/docs/endpoints",
    ),
    "recoveryos": (
        "https://www.penninecare.nhs.uk/download_file/5855/277",
    ),
}
PATH_TOPIC_HINTS = {
    "freightrecovery": re.compile(r"(freight|ltl|carrier|trucking|tariff|ship(?:ment|ping)|bill[-_]?of[-_]?lading)", re.I),
    "permitplate": re.compile(r"(dob|nyc[-_]?permit|building[-_]?permit|construction[-_]?filing|permit[-_]?issu)", re.I),
    "capturebrief": re.compile(r"(solicitation|government[-_]?contract|federal[-_]?contract|sam[-_]?gov|procurement|rfp)", re.I),
    "recoveryos": re.compile(r"(accounts[-_]?payable|invoice|vendor[-_]?payment|supplier[-_]?spend|reconcil|pennine)", re.I),
}
# Missing evidence is a stated requirement for a usable benchmark, not a claim
# that any missing item is obtainable from the indexed public URLs.
EVIDENCE_GAPS = {
    "freightrecovery": (
        "ORIGINAL_INVOICE_CUSTODY_NOT_ESTABLISHED",
        "BUYER_SPECIFIC_EFFECTIVE_RATE_AUTHORITY_MISSING",
        "INDEPENDENT_SHIPMENT_AND_BOL_LINK_MISSING",
        "PAYMENT_OR_CREDIT_CHAIN_MISSING",
        "ADJUDICATED_POSITIVE_AND_NEGATIVE_LABELS_MISSING",
    ),
    "permitplate": (
        "ORIGINAL_PERMIT_RECORD_CUSTODY_NOT_ESTABLISHED",
        "APPLICATION_VERSUS_ISSUANCE_SCOPE_NOT_ADJUDICATED",
        "INDEPENDENT_PERMIT_STATUS_AND_JOIN_NOT_ESTABLISHED",
        "HELD_OUT_OPPORTUNITY_OUTCOME_LABELS_MISSING",
    ),
    "capturebrief": (
        "ORIGINAL_SOLICITATION_AMENDMENT_CUSTODY_NOT_ESTABLISHED",
        "RELEASE_TIME_AS_OF_HISTORY_NOT_VERIFIED",
        "AWARD_OUTCOME_LINKAGE_NOT_ADJUDICATED",
        "INDEPENDENT_POSITIVE_AND_NEGATIVE_LABELS_MISSING",
    ),
    "recoveryos": (
        "ORIGINAL_INVOICE_PAYMENT_SOURCE_CUSTODY_NOT_ESTABLISHED",
        "EFFECTIVE_VENDOR_CONTRACT_TERMS_MISSING",
        "INDEPENDENT_PAYMENT_AND_CREDIT_CHAIN_MISSING",
        "ADJUDICATED_OVERPAYMENT_AND_CLEAN_LABELS_MISSING",
    ),
}
REVIEW_CODES = (
    "PUBLICATION_PROVENANCE_AND_DOCUMENT_TYPE_REVIEW_REQUIRED",
    "REUSE_RIGHTS_REVIEW_REQUIRED",
    "ENGINE_SPECIFIC_AUTHORITY_AND_OUTCOME_REVIEW_REQUIRED",
)


def _observed_day(value: str, as_of: date) -> date:
    try:
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise ValueError("not canonical ISO day")
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchError("REVIEW_SOURCE_DATE_INVALID") from exc
    if day > as_of:
        raise ResearchError("REVIEW_SOURCE_FUTURE_DATED")
    return day


def _classify(engine: str, row: dict) -> tuple[int, str]:
    host = row["publisher"]
    url = row["url"]
    path = urlsplit(url).path
    if (engine == "permitplate" and host == "data.cityofnewyork.us"
            and path.rstrip("/").rsplit("/", 1)[-1] in NYC_UNENDORSED_DERIVATIVE_VIEW_IDS):
        return 4, "NYC_COMMUNITY_CREATED_DERIVATIVE_VIEW_REVIEW_ONLY"
    if host in OFFICIAL_HOSTS:
        if url in PUBLIC_REVIEW_ANCHORS[engine]:
            return 0, "PINNED_PUBLIC_ANCHOR_URL_ONLY"
        return 1, "OFFICIAL_PUBLISHER_HOST_URL_ONLY"
    if host in CATALOG_HOSTS and PATH_TOPIC_HINTS[engine].search(path):
        return 2, "THIRD_PARTY_URL_TOPIC_HINT_ONLY"
    return 3, "UNCLASSIFIED_THIRD_PARTY_CATALOG_URL_ONLY"


def build_queue(ledger: dict, as_of: date) -> dict:
    """Validated cross-engine selection; rankings are NOT evidentiary labels."""
    if type(as_of) is not date:
        raise ResearchError("REVIEW_DATE_REQUIRED")
    validate_ledger(ledger)
    ranked = {engine: [] for engine in ENGINES}
    exclusions = {engine: 0 for engine in ENGINES}
    for row in ledger["entries"]:
        _observed_day(row["first_seen"], as_of)
        for engine in row["engines"]:
            if engine == "permitplate" and not permitplate_url_in_scope(row["url"]):
                # Keep historic catalog untouched; suppress irrelevant links
                # only from this non-binding research review queue.
                exclusions[engine] += 1
                continue
            order, category = _classify(engine, row)
            ranked[engine].append((order, row["id"], row, category))
    lanes = {}
    for engine in ENGINES:
        choices = sorted(ranked[engine], key=lambda r: (r[0], r[1]))
        queued = []
        for _, _, row, category in choices[:MAX_REVIEW_PER_ENGINE]:
            queued.append({
                "source_id": row["id"],
                "public_source_url": row["url"],
                "publisher_host": row["publisher"],
                "first_seen": row["first_seen"],
                "rank_reason": category,
                "source_provenance_verified": False,
                "original_document_bytes_copied": False,
                "commercial_reuse_authorized": False,
                "independent_ground_truth": False,
                "benchmark_ready": False,
                "review_gates": list(REVIEW_CODES),
            })
        classes = {
            "pinned_public_anchor_url_only": sum(x[0] == 0 for x in choices),
            "official_publisher_host_url_only": sum(x[0] == 1 for x in choices),
            "third_party_path_topic_hints_only": sum(x[0] == 2 for x in choices),
            "unclassified_third_party_catalogs_only": sum(x[0] == 3 for x in choices),
            "known_nyc_community_derivative_views_review_only": sum(x[0] == 4 for x in choices),
        }
        lanes[engine] = {
            "catalog_source_associations": len(choices) + exclusions[engine],
            "url_only_topic_exclusions_not_deleted": exclusions[engine],
            "unverified_candidates_after_url_screen": len(choices),
            "ranked_for_manual_evidence_review": len(queued),
            "candidate_classes": classes,
            "priority_review_queue": queued,
            "independent_benchmark_truth_cases_from_queue": 0,
            "commercial_use_approved": False,
            "missing_benchmark_evidence": list(EVIDENCE_GAPS[engine]),
            "readiness": "URL_POINTERS_ONLY_NO_EVIDENCE_PROMOTION",
        }
    payload = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of_utc_date": as_of.isoformat(),
        "source_ledger_entries_sha256": ledger["entries_sha256"],
        "unique_public_source_references": len(ledger["entries"]),
        "max_review_candidates_per_engine": MAX_REVIEW_PER_ENGINE,
        "engines": lanes,
        "external_document_bytes_saved": 0,
        "real_customer_cases_promoted": 0,
        "independent_outcome_labels_promoted": 0,
        "verified_recovered_cash_cents": 0,
        "commercial_recovery_allowed": False,
        "customer_contact_actions": 0,
        "production_changes": 0,
        "ranking_scope_warning": (
            "Public URL host and path rankings are not evidence of publisher "
            "authenticity, record relevance, source rights or accuracy."
        ),
    }
    return {**payload, "queue_sha256": digest(payload)}


def render_queue(ledger: dict, as_of: date) -> str:
    return json.dumps(build_queue(ledger, as_of), sort_keys=True, indent=2) + "\n"


def _parse_date(value: str) -> date:
    try:
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise ValueError("bad")
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchError("REVIEW_AS_OF_DATE_INVALID") from exc


def run(*, ledger_path: Path = LEDGER, output: Path = OUTPUT,
        as_of: date | None = None, verify_only: bool = False) -> dict:
    ledger = read_ledger(ledger_path)
    if verify_only:
        if not output.is_file():
            raise ResearchError("REVIEW_QUEUE_MISSING")
        existing = output.read_text(encoding="utf-8")
        try:
            stored = json.loads(existing)
            chosen = _parse_date(stored["as_of_utc_date"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ResearchError("REVIEW_QUEUE_INVALID") from exc
    else:
        chosen = as_of or datetime.now(timezone.utc).date()
    if type(chosen) is not date or chosen > datetime.now(timezone.utc).date():
        raise ResearchError("REVIEW_DATE_FUTURE_OR_INVALID")
    expected = render_queue(ledger, chosen)
    if verify_only:
        if existing != expected:
            raise ResearchError("REVIEW_QUEUE_STALE_OR_CHANGED")
    elif not output.is_file() or output.read_text(encoding="utf-8") != expected:
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_name(output.name + ".tmp")
        temp.write_text(expected, encoding="utf-8")
        temp.replace(output)
    result = json.loads(expected)
    return {
        "scope": SCOPE, "verified": verify_only,
        "source_count": result["unique_public_source_references"],
        "queue_sha256": result["queue_sha256"],
        "per_engine_queued": {
            engine: result["engines"][engine]["ranked_for_manual_evidence_review"]
            for engine in ENGINES
        },
        "rights_confirmed": False, "independent_truth_confirmed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--as-of")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify and args.as_of is not None:
        parser.error("--as-of not allowed in verification mode")
    day = _parse_date(args.as_of) if args.as_of else None
    print(json.dumps(run(ledger_path=args.ledger, output=args.output,
                         as_of=day, verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
