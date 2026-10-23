"""Research Lab -> FreightRecovery v1 evaluation: reproducible, untrusted lead feed.

Only source pointers from validated source catalogs are projected. Every pointer
is exercised against the *real* rating/evidence engines on fabricated source
and shipment identities, with NO governing authority, independent BOL or bank.
This is NOT a document extractor, automatically adjudicated freight fixture,
commercial license or customer recovery approval.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.lab15_acquisition import read_ledger as read_legacy_evidence
from freight.lab15_evidence_harvester import validate_ledger as validate_legacy_candidates
from freight.priority2_evidence import review_freight_rate
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.real_world_eval_v1 import (
    fixture_sha256, load_manifest, validate_manifest,
)
from freight.unified_research_lab import (
    LEDGER, ROOT, RIGHTS, TRUTH, ResearchError, digest, read_ledger, safe_url,
    validate_ledger,
)

EVIDENCE_PATH = Path(__file__).with_name("lab15") / "evidence_ledger.json"
CANDIDATE_PATH = Path(__file__).with_name("research") / "lab15_candidate_ledger.json"
FEED_PATH = ROOT / "evaluation_feed_v1.json"
VERSION = "1.1.0"
MAX_FEED_ROWS = 300
MAX_INPUT_ROWS = 24_000
SYNTHETIC_EVENT_TIME = "2026-10-23T00:00:00.000000Z"
FORBIDDEN_SOURCE_HOSTS = frozenset({"extranet4.biggexpress.com", "cw.shipandsave.com"})


def _legacy(path: Path, kind: str) -> dict:
    if not path.is_file():
        raise ResearchError("REQUIRED_LEGACY_RESEARCH_LEDGER_MISSING:" + kind)
    if path.stat().st_size > 12_000_000:
        raise ResearchError("LEGACY_RESEARCH_LEDGER_TOO_LARGE:" + kind)
    if kind == "evidence":
        return read_legacy_evidence(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_legacy_candidates(data)


def _first_seen(value: str) -> str:
    if not isinstance(value, str) or len(value) < 10:
        raise ResearchError("INVALID_FIRST_SEEN")
    raw = value[:10]
    if date.fromisoformat(raw).isoformat() != raw:
        raise ResearchError("INVALID_FIRST_SEEN")
    return raw


def _source_kind(url: str, case_id: str | None) -> str:
    if case_id is not None:
        return "MATCHED_FROZEN_V1_REFERENCE"
    host = urlsplit(url).hostname
    if host in {"www.gao.gov", "media.cadc.uscourts.gov",
                "www2.fmc.gov", "www.fmc.gov"}:
        return "POTENTIAL_HISTORICAL_DECISION_REFERENCE"
    if host in {"www.sec.gov", "www.stb.gov", "www.eia.gov", "psc.ky.gov"}:
        return "POTENTIAL_REGULATORY_OR_RATE_REFERENCE"
    return "UNCLASSIFIED_PUBLIC_DATASET_LEAD"


def _register(rows: dict, url: str, first_seen: str, origin: str) -> bool:
    """Bounded metadata join; reject unsafe URLs instead of passing untrusted text."""
    try:
        safe_url(url)
    except (ResearchError, ValueError):
        return False
    host = urlsplit(url).hostname
    if host in FORBIDDEN_SOURCE_HOSTS:
        return False
    key = digest(url)
    if key not in rows:
        rows[key] = {
            "lead_id": key, "source_url": url, "publisher_host": host,
            "first_seen": _first_seen(first_seen), "origins": {origin},
        }
    else:
        row = rows[key]
        row["first_seen"] = min(row["first_seen"], _first_seen(first_seen))
        row["origins"].add(origin)
    return True


def synthetic_proof_gate(lead_id: str) -> dict:
    """Genuine production rate/evidence review on an explicitly fictitious record."""
    if (not isinstance(lead_id, str) or len(lead_id) != 64
            or any(x not in "0123456789abcdef" for x in lead_id)):
        raise ResearchError("INVALID_RESEARCH_LEAD_ID")
    fake_sha = sha256(("SYNTHETIC-NOT-ORIGINAL-RESEARCH-LEAD:" + lead_id).encode()).hexdigest()
    record = build_record(
        buyer_id="SYNTHETIC-RESEARCH-BUYER",
        business_unit="PUBLIC-SOURCE-NEGATIVE-PROBE",
        customer_id="SYNTHETIC-RESEARCH-CUSTOMER",
        invoice_id="SYNTHETIC-RESEARCH-INVOICE-" + lead_id[:12],
        invoice_date="2026-10-23",
        currency="USD",
        shipment=ShipmentFacts(
            shipment_id="SYNTHETIC-RESEARCH-SHIPMENT-" + lead_id[:12],
            carrier_id="SYNTHETIC-RESEARCH-CARRIER",
            mode="TL", service_date="2026-10-23",
            origin_postal="SYNTHETIC-ORIGIN",
            destination_postal="SYNTHETIC-DESTINATION",
            actual_weight_grams=1000, package_count=1,
        ),
        charges=(ChargeLine("SYNTHETIC-LINEHAUL", "TRANSPORTATION", 100),),
        sources=(SourceArtifact(
            "SYNTHETIC-SOURCE-ONLY", "NOT_AN_ORIGINAL_INVOICE",
            fake_sha, SYNTHETIC_EVENT_TIME, "BATCH",
        ),),
    )
    authority = AuthorityBook(())
    rated = rate_record(record, authority)
    strict = review_freight_rate(record, authority)
    if (rated.status != REVIEW_REQUIRED
            or rated.expected_total_cents is not None
            or rated.variance_cents is not None
            or strict.status != REVIEW_REQUIRED
            or strict.externally_verified_freight_error_cents is not None
            or strict.externally_verified_cash_recovered_cents != 0
            or strict.independent_accuracy_scored
            or "INDEPENDENT_SHIPMENT_DOCUMENT_MISSING" not in strict.blockers
            or "NO_EFFECTIVE_SHIPMENT_RATE_AUTHORITY" not in strict.blockers):
        raise ResearchError("RESEARCH_LEAD_INCORRECTLY_PROMOTED_TO_CLAIM")
    return {
        "rating_status": REVIEW_REQUIRED,
        "evidence_status": REVIEW_REQUIRED,
        "verified_freight_error_cents": None,
        "verified_cash_recovered_cents": 0,
        "synthetic_shipment_only": True,
    }


def build_feed(unified: dict, evidence: dict, legacy: dict, manifest: dict) -> dict:
    """Deterministic projection from all three *validated* collectors."""
    validate_ledger(unified)
    from freight.lab15_acquisition import validate_ledger as check_evidence
    check_evidence(evidence)
    validate_legacy_candidates(legacy)
    cases = validate_manifest(manifest)
    canonical = {v["source_url"]: key for key, v in cases.items()
                 if v["category"] != "PUBLIC_INVOICE_FACE"}
    if len(canonical) != 7:
        raise ResearchError("FROZEN_V1_OFFICIAL_REFERENCE_POPULATION_DRIFT")
    if len(unified["entries"]) + len(evidence["records"]) + len(legacy["leads"]) > MAX_INPUT_ROWS:
        raise ResearchError("RESEARCH_LEDGER_POPULATION_TOO_LARGE")
    rows = {}
    skipped = 0
    for item in unified["entries"]:
        if "freightrecovery" in item["engines"]:
            if not _register(rows, item["url"], item["first_seen"], "UNIFIED"):
                skipped += 1
    for item in evidence["records"]:
        if not _register(rows, item["url"], item["first_seen"], "LAB15_EVIDENCE"):
            skipped += 1
    for item in legacy["leads"]:
        if not _register(rows, item["url"], item["first_seen"], "LAB15_CANDIDATES"):
            skipped += 1
    all_rows = list(rows.values())
    for row in all_rows:
        case_id = canonical.get(row["source_url"])
        row["case_id"] = case_id
        row["source_kind"] = _source_kind(row["source_url"], case_id)
    # Keep exact-match frozen references first. Newest other candidates next;
    # a bounded window prevents enormous/untrusted ledgers exhausting CI.
    ranked = sorted(all_rows, key=lambda r: (
        0 if r["case_id"] else 1, "" if r["case_id"] else
        "".join(chr(57 - int(c)) for c in r["first_seen"] if c.isdigit()),
        r["lead_id"],
    ))
    selected = ranked[:MAX_FEED_ROWS]
    output = []
    for row in selected:
        probe = synthetic_proof_gate(row["lead_id"])
        output.append({
            **{k: row[k] for k in ("lead_id", "source_url", "publisher_host",
                                  "first_seen", "case_id", "source_kind")},
            "origins": sorted(row["origins"]),
            "rights_state": RIGHTS, "truth_state": TRUTH,
            "evaluation_state": "SOURCE_POINTER_WITH_SYNTHETIC_PROOF_GATE_ONLY",
            "commercial_reuse_authorized": False,
            "independent_ground_truth": False,
            "independent_payment_verified": False,
            "source_document_ingested": False,
            "model": probe,
        })
    matched = sum(row["case_id"] is not None for row in output)
    body = {
        "schema_version": 1,
        "feed_version": VERSION,
        "pack_id": manifest["pack_id"],
        "pack_version": manifest["schema_version"],
        "frozen_pack_fixture_sha256_not_original_docs": fixture_sha256(),
        "source_receipts": {
            "unified_entries_sha256": unified["entries_sha256"],
            "lab15_evidence_metadata_sha256": digest(evidence),
            "lab15_candidate_metadata_sha256": legacy["digest_sha256"],
        },
        "source_pointers_total": len(all_rows),
        "selected_for_synthetic_proof_gate": len(output),
        "omitted_for_bounded_execution": max(0, len(all_rows) - len(output)),
        "unsafe_or_unrepresentable_legacy_pointers_skipped": skipped,
        "frozen_v1_official_source_matches": matched,
        "frozen_v1_historical_cases": len(cases),
        "new_customer_proven_overcharges": None,
        "independently_scored_new_customer_cases": 0,
        "verified_recovered_cash_cents": 0,
        "customer_contacts_sent": 0,
        "production_changes": 0,
        "commercial_recovery_allowed": False,
        "candidate_sources": output,
    }
    return {**body, "feed_sha256": digest(body)}


def read_inputs(
    ledger_path: Path = LEDGER,
    evidence_path: Path = EVIDENCE_PATH,
    candidates_path: Path = CANDIDATE_PATH,
) -> tuple[dict, dict, dict]:
    return (read_ledger(ledger_path), _legacy(evidence_path, "evidence"),
            _legacy(candidates_path, "candidates"))


def validate_feed(feed: dict, unified: dict, evidence: dict,
                  legacy: dict, manifest: dict) -> None:
    if feed != build_feed(unified, evidence, legacy, manifest):
        raise ResearchError("RESEARCH_EVALUATION_FEED_CHANGED_OR_STALE")


def run(ledger: Path = LEDGER, evidence: Path = EVIDENCE_PATH,
        candidates: Path = CANDIDATE_PATH, output: Path = FEED_PATH,
        *, verify_only: bool = False) -> dict:
    unified, old, fresh = read_inputs(ledger, evidence, candidates)
    manifest = load_manifest()
    expected = build_feed(unified, old, fresh, manifest)
    if verify_only:
        validate_feed(json.loads(output.read_text(encoding="utf-8")),
                      unified, old, fresh, manifest)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(expected, indent=2, sort_keys=True) + "\n"
        if not output.exists() or output.read_text(encoding="utf-8") != body:
            output.write_text(body, encoding="utf-8")
    return {
        "version": VERSION,
        "feed_sha256": expected["feed_sha256"],
        "source_pointers_total": expected["source_pointers_total"],
        "selected_for_synthetic_proof_gate": expected["selected_for_synthetic_proof_gate"],
        "frozen_v1_official_source_matches": expected["frozen_v1_official_source_matches"],
        "omitted_for_bounded_execution": expected["omitted_for_bounded_execution"],
        "unsafe_or_unrepresentable_legacy_pointers_skipped":
            expected["unsafe_or_unrepresentable_legacy_pointers_skipped"],
        "verified_recovered_cash_cents": 0,
        "commercial_recovery_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--lab15-evidence", type=Path, default=EVIDENCE_PATH)
    parser.add_argument("--lab15-candidates", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--output", type=Path, default=FEED_PATH)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    summary = run(args.ledger, args.lab15_evidence,
                  args.lab15_candidates, args.output, verify_only=args.verify)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
