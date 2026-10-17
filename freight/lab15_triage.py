"""RETALLY Lab 15: deterministic triage of PUBLIC SOURCE POINTERS, not audit results.

Run only over the existing metadata-only acquisition ledger. Prior research
observations are unverified descriptions. They must never be converted into
customer permissions, recovered cash, correct invoice labels, or public claims.
No network, document content, identities, or financial instructions are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from freight.lab15_acquisition import EvidenceError, read_ledger, validate_ledger

ROOT = Path(__file__).resolve().parent / "lab15"
ANNOTATIONS = ROOT / "evidence_annotations.json"
OUTPUT = ROOT / "triage_queue.json"
CLASSES = (
    "original_carrier_invoice",
    "effective_customer_rate_quote",
    "independent_shipment_document",
    "independent_payment_or_credit_receipt",
    "prior_auditor_finding",
    "independent_adjudicated_decision",
)
POINTS = {
    "original_carrier_invoice": 6,
    "effective_customer_rate_quote": 5,
    "independent_shipment_document": 3,
    "independent_payment_or_credit_receipt": 5,
    "prior_auditor_finding": 4,
    "independent_adjudicated_decision": 4,
}
REVIEW_STATE = "PREVIOUS_PUBLIC_RESEARCH_REPORTED_NOT_VERIFIED"
OUTPUT_SCOPE = "PUBLIC_METADATA_TRIAGE_ONLY_NO_AUDIT_TRUTH"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def validate_annotations(payload: dict, ledger: dict) -> dict[str, tuple[str, ...]]:
    """Fail closed on unknown sources, altered approvals or invented evidence."""
    validate_ledger(ledger)
    if (type(payload) is not dict
            or set(payload) != {"schema_version", "annotations"}
            or type(payload["schema_version"]) is not int
            or payload["schema_version"] != 1
            or type(payload["annotations"]) is not list):
        raise EvidenceError("BAD_TRIAGE_ANNOTATIONS")
    by_url = {r["url"]: r for r in ledger["records"]}
    annotations: dict[str, tuple[str, ...]] = {}
    for row in payload["annotations"]:
        if (type(row) is not dict
                or set(row) != {"url", "reported_evidence", "review_state"}
                or type(row["url"]) is not str
                or row["url"] not in by_url
                or row["url"] in annotations
                or row["review_state"] != REVIEW_STATE
                or type(row["reported_evidence"]) is not list):
            raise EvidenceError("UNTRUSTED_TRIAGE_ANNOTATION")
        evidence = row["reported_evidence"]
        if (not evidence or any(type(item) is not str or item not in CLASSES
                                for item in evidence)
                or evidence != sorted(set(evidence))):
            raise EvidenceError("INVALID_REPORTED_EVIDENCE")
        if (by_url[row["url"]]["kind"] == "DATASET_CATALOG_LEAD"
                or "original_carrier_invoice" in evidence
                and by_url[row["url"]]["kind"] == "GAO_DECISION"):
            raise EvidenceError("UNSUPPORTED_DOCUMENT_OBSERVATION")
        annotations[row["url"]] = tuple(evidence)
    return annotations


def build_queue(ledger: dict, payload: dict) -> dict:
    annotations = validate_annotations(payload, ledger)
    entries = []
    for record in ledger["records"]:
        observed = annotations.get(record["url"], ())
        score = sum(POINTS[item] for item in observed)
        missing = [item for item in CLASSES if item not in observed]
        entries.append({
            "source_id": record["id"],
            "source_url": record["url"],
            "source_kind": record["kind"],
            "first_seen": record["first_seen"],
            "public_source_fingerprint": record["sha256"],
            "reported_evidence": list(observed),
            "evidence_not_reported": missing,
            "manual_review_priority_points": score,
            "review_state": REVIEW_STATE if observed else "METADATA_LEAD_NOT_INSPECTED",
            "reuse_rights_cleared": False,
            "customer_permission_verified": False,
            "complete_original_document_chain_verified": False,
            "invoice_error_independently_verified": False,
            "real_cash_recovery_verified": False,
        })
    entries.sort(key=lambda x: (-x["manual_review_priority_points"], x["source_id"]))
    return {
        "schema_version": 1,
        "scope": OUTPUT_SCOPE,
        "source_ledger_sha256": _digest(ledger),
        "annotations_sha256": _digest(payload),
        "source_count": len(entries),
        "annotated_sources": len(annotations),
        "sources_with_complete_approved_real_case": 0,
        "sources_pending_rights_and_independent_review": len(entries),
        "entries": entries,
    }


def validate_queue(report: dict, ledger: dict, payload: dict) -> None:
    if report != build_queue(ledger, payload):
        raise EvidenceError("TRIAGE_QUEUE_NOT_SOURCE_BOUND")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=ROOT / "evidence_ledger.json")
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    ledger = read_ledger(args.ledger)
    payload = json.loads(args.annotations.read_text(encoding="utf-8"))
    result = build_queue(ledger, payload)
    validate_queue(result, ledger, payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "source_count": result["source_count"],
        "annotated_sources": result["annotated_sources"],
        "approved_real_case_count": result["sources_with_complete_approved_real_case"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
