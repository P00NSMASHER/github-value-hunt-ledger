"""Bounded first-party HTTP/source-byte provenance observations for RETALLY.

A successful origin response or fingerprint is NOT a license, an authentic
customer invoice, adjudicated positive/negative outcome or recovery evidence.
Only already-pinned public publisher URLs are requested. No crawls, customer
records, full source bodies, redirect following, or new paid APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from freight.research_source_review import PUBLIC_REVIEW_ANCHORS
from freight.unified_research_lab import (
    ENGINES, LEDGER, ROOT, NoRedirect, ResearchError, digest,
    global_dns, read_ledger, safe_url, validate_ledger,
)

OUTPUT = ROOT / "publisher_provenance_v1.json"
SCOPE = "PUBLIC_PUBLISHER_RESPONSE_OBSERVATIONS_NOT_BENCHMARK_TRUTH"
MAX_ANCHORS = 12
MAX_RESPONSE_BYTES = 262144
HEAD_TIMEOUT_SECONDS = 5
GET_TIMEOUT_SECONDS = 6
CONTENT_CLASSES = frozenset({"HTML", "JSON", "PDF", "CSV", "TEXT", "OTHER", "UNKNOWN"})
FINGERPRINT_MEDIA = frozenset({"HTML", "JSON", "PDF", "CSV", "TEXT"})
STATES = frozenset({
    "PUBLIC_CONTENT_FINGERPRINTED", "PUBLIC_HTTP_METADATA_ONLY",
    "PUBLISHER_CONTENT_TOO_LARGE", "UNSUPPORTED_SOURCE_MEDIA",
    "UNSUPPORTED_SOURCE_ENCODING", "GET_NOT_VERIFIABLE",
    "HTTP_NOT_AVAILABLE", "REDIRECT_BLOCKED", "NETWORK_UNAVAILABLE",
    "DNS_UNAVAILABLE", "NONPUBLIC_NETWORK", "UNPROBED_OFFLINE",
})
OBS_KEYS = frozenset({
    "engine", "source_id", "publisher_host", "first_seen", "probe_state",
    "head_http_status", "media_class", "content_sha256", "bytes_hashed",
    "source_document_bytes_stored", "commercial_reuse_approved",
    "independent_outcome_verified", "benchmark_ready",
})
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "as_of_utc_date", "anchor_set_sha256",
    "source_pointers_probed", "pinned_anchors_not_in_ledger",
    "publisher_http_responses_observed", "full_public_responses_fingerprinted",
    "observations", "source_document_bytes_stored",
    "commercial_reuse_approved", "independent_outcome_labels_verified",
    "independently_scored_benchmark_cases", "verified_recovered_cash_cents",
    "customer_contact_actions", "production_changes", "limitations",
    "receipt_sha256",
})
LIMITATIONS = (
    "HTTP response status only establishes what this fixed public URL returned at the observed date.",
    "A SHA-256 of a complete bounded public response is an observed-byte digest, not an official publisher signature.",
    "Public availability and metadata do not grant commercial reuse permission.",
    "No invoice, permit, solicitation, or payment is independently linked to an adjudicated outcome.",
)


def _day(value: str) -> date:
    try:
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise ValueError("non-canonical date")
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchError("INVALID_PUBLICATION_DATE") from exc


def pinned_rows(ledger: dict) -> tuple[list[dict], dict[str, int]]:
    """Allowlisted anchor intersection with an immutable validated source ledger."""
    validate_ledger(ledger)
    mapping = {item["url"]: item for item in ledger["entries"]}
    rows = []
    missing = {}
    for engine in ENGINES:
        absent = 0
        for url in PUBLIC_REVIEW_ANCHORS[engine]:
            safe_url(url)
            row = mapping.get(url)
            if row is None or engine not in row["engines"]:
                absent += 1
                continue
            rows.append({
                "engine": engine, "source_id": row["id"],
                "publisher_host": row["publisher"],
                "first_seen": row["first_seen"],
            })
        missing[engine] = absent
    if len(rows) > MAX_ANCHORS:
        raise ResearchError("PUBLIC_PROBE_BUDGET_EXCEEDED")
    return rows, missing


def fingerprint_media(mime: str) -> str:
    value = mime.split(";", 1)[0].strip().lower() if type(mime) is str else ""
    if value in {"text/html", "application/xhtml+xml"}:
        return "HTML"
    if value in {"application/json", "application/vnd.github+json"}:
        return "JSON"
    if value in {"application/pdf"}:
        return "PDF"
    if value in {"text/csv", "application/csv"}:
        return "CSV"
    if value in {"text/plain"}:
        return "TEXT"
    return "OTHER" if value else "UNKNOWN"


def _http_code(exc: HTTPError) -> int | None:
    status = getattr(exc, "code", None)
    return status if type(status) is int and 100 <= status <= 599 else None


def _safe_head_and_digest(url: str) -> dict:
    """Bounded network observer. No original bytes retained or logged."""
    if url not in {u for urls in PUBLIC_REVIEW_ANCHORS.values() for u in urls}:
        raise ResearchError("UNPINNED_EXTERNAL_REQUEST_BLOCKED")
    safe_url(url)
    try:
        global_dns(urlsplit(url).hostname or "")
    except ResearchError as exc:
        state = str(exc)
        if state not in {"DNS_UNAVAILABLE", "NONPUBLIC_NETWORK"}:
            state = "NETWORK_UNAVAILABLE"
        return {"probe_state": state, "head_http_status": None,
                "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}
    headers = {
        "User-Agent": "RETALLY-PublisherProvenance/1.0 fixed-public-sources-read-only",
        "Accept": "text/html,application/json,application/pdf,text/csv,text/plain",
        "Accept-Encoding": "identity",
    }
    opener = build_opener(NoRedirect)
    try:
        req = Request(url, method="HEAD", headers=headers)
        with opener.open(req, timeout=HEAD_TIMEOUT_SECONDS) as response:
            if response.status != 200 or response.geturl() != url:
                return {"probe_state": "HTTP_NOT_AVAILABLE", "head_http_status": None,
                        "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}
            media = fingerprint_media(response.headers.get("Content-Type", ""))
            raw_length = response.headers.get("Content-Length")
            encoding = response.headers.get("Content-Encoding", "identity").lower().strip()
    except HTTPError as exc:
        code = _http_code(exc)
        return {"probe_state": "HTTP_NOT_AVAILABLE", "head_http_status": code,
                "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}
    except ResearchError:
        return {"probe_state": "REDIRECT_BLOCKED", "head_http_status": None,
                "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}
    except (URLError, TimeoutError, OSError):
        return {"probe_state": "NETWORK_UNAVAILABLE", "head_http_status": None,
                "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}

    base = {"head_http_status": 200, "media_class": media,
            "content_sha256": None, "bytes_hashed": 0}
    if encoding not in {"", "identity"}:
        return {**base, "probe_state": "UNSUPPORTED_SOURCE_ENCODING"}
    if media not in FINGERPRINT_MEDIA:
        return {**base, "probe_state": "UNSUPPORTED_SOURCE_MEDIA"}
    if raw_length:
        try:
            length = int(raw_length)
        except ValueError:
            return {**base, "probe_state": "PUBLIC_HTTP_METADATA_ONLY"}
        if length < 0:
            return {**base, "probe_state": "PUBLIC_HTTP_METADATA_ONLY"}
        if length > MAX_RESPONSE_BYTES:
            return {**base, "probe_state": "PUBLISHER_CONTENT_TOO_LARGE"}
    try:
        req = Request(url, method="GET", headers=headers)
        with opener.open(req, timeout=GET_TIMEOUT_SECONDS) as response:
            if response.status != 200 or response.geturl() != url:
                return {**base, "probe_state": "GET_NOT_VERIFIABLE"}
            if fingerprint_media(response.headers.get("Content-Type", "")) != media:
                return {**base, "probe_state": "GET_NOT_VERIFIABLE"}
            if response.headers.get("Content-Encoding", "identity").lower().strip() not in {"", "identity"}:
                return {**base, "probe_state": "GET_NOT_VERIFIABLE"}
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ResearchError):
        return {**base, "probe_state": "GET_NOT_VERIFIABLE"}
    if not content:
        return {**base, "probe_state": "GET_NOT_VERIFIABLE"}
    if len(content) > MAX_RESPONSE_BYTES:
        return {**base, "probe_state": "PUBLISHER_CONTENT_TOO_LARGE"}
    return {**base, "probe_state": "PUBLIC_CONTENT_FINGERPRINTED",
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "bytes_hashed": len(content)}


def _observation(row: dict, probe: dict) -> dict:
    if type(probe) is not dict:
        raise ResearchError("INVALID_PUBLIC_PROBE_RESPONSE")
    keys = frozenset(probe)
    if keys != {"probe_state", "head_http_status", "media_class", "content_sha256", "bytes_hashed"}:
        raise ResearchError("INVALID_PUBLIC_PROBE_RESPONSE")
    if probe["probe_state"] not in STATES or probe["media_class"] not in CONTENT_CLASSES:
        raise ResearchError("INVALID_PUBLIC_PROBE_RESPONSE")
    if type(probe["bytes_hashed"]) is not int or not 0 <= probe["bytes_hashed"] <= MAX_RESPONSE_BYTES:
        raise ResearchError("INVALID_PUBLIC_PROBE_RESPONSE")
    if probe["head_http_status"] is not None and (
        type(probe["head_http_status"]) is not int or
        not 100 <= probe["head_http_status"] <= 599
    ):
        raise ResearchError("INVALID_PUBLIC_PROBE_RESPONSE")
    fingerprinted = probe["probe_state"] == "PUBLIC_CONTENT_FINGERPRINTED"
    if fingerprinted:
        if (probe["head_http_status"] != 200 or probe["media_class"] not in FINGERPRINT_MEDIA
                or probe["bytes_hashed"] < 1 or type(probe["content_sha256"]) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", probe["content_sha256"])):
            raise ResearchError("INVALID_PUBLISHER_FINGERPRINT")
    elif probe["content_sha256"] is not None or probe["bytes_hashed"] != 0:
        raise ResearchError("UNVERIFIED_OR_PARTIAL_RESPONSE_FINGERPRINT")
    if probe["probe_state"] in {"PUBLIC_HTTP_METADATA_ONLY", "PUBLIC_CONTENT_FINGERPRINTED",
                                "PUBLISHER_CONTENT_TOO_LARGE", "UNSUPPORTED_SOURCE_MEDIA",
                                "UNSUPPORTED_SOURCE_ENCODING", "GET_NOT_VERIFIABLE"} and (
        probe["head_http_status"] != 200
    ):
        raise ResearchError("INVALID_HEAD_STATUS")
    return {**row, **probe,
            "source_document_bytes_stored": False,
            "commercial_reuse_approved": False,
            "independent_outcome_verified": False,
            "benchmark_ready": False}


def build_receipt(ledger: dict, as_of: date, *, fetcher=None) -> dict:
    if type(as_of) is not date:
        raise ResearchError("RECEIPT_DATE_REQUIRED")
    anchors, missing = pinned_rows(ledger)
    id_to_url = {row["id"]: row["url"] for row in ledger["entries"]}
    probe_fn = fetcher or _safe_head_and_digest
    results = []
    for row in anchors:
        observations = probe_fn(id_to_url[row["source_id"]])
        results.append(_observation(row, observations))
    public_http = sum(r["head_http_status"] == 200 for r in results)
    fingerprints = sum(r["probe_state"] == "PUBLIC_CONTENT_FINGERPRINTED" for r in results)
    payload = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of_utc_date": as_of.isoformat(),
        "anchor_set_sha256": digest(anchors),
        "source_pointers_probed": len(results),
        "pinned_anchors_not_in_ledger": missing,
        "publisher_http_responses_observed": public_http,
        "full_public_responses_fingerprinted": fingerprints,
        "observations": results,
        "source_document_bytes_stored": 0,
        "commercial_reuse_approved": False,
        "independent_outcome_labels_verified": 0,
        "independently_scored_benchmark_cases": 0,
        "verified_recovered_cash_cents": 0,
        "customer_contact_actions": 0,
        "production_changes": 0,
        "limitations": list(LIMITATIONS),
    }
    return {**payload, "receipt_sha256": digest(payload)}


def _validate_receipt(doc: dict, ledger: dict, today: date) -> dict:
    if type(doc) is not dict or frozenset(doc) != RECEIPT_KEYS:
        raise ResearchError("PUBLISHER_PROVENANCE_RECEIPT_INVALID")
    if doc["scope"] != SCOPE or type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise ResearchError("PUBLISHER_PROVENANCE_RECEIPT_INVALID")
    observed = _day(doc["as_of_utc_date"])
    if observed > today:
        raise ResearchError("FUTURE_PUBLISHER_RECEIPT")
    anchors, missing = pinned_rows(ledger)
    if (doc["anchor_set_sha256"] != digest(anchors) or
            doc["pinned_anchors_not_in_ledger"] != missing or
            doc["source_pointers_probed"] != len(anchors) or
            type(doc["observations"]) is not list or
            len(doc["observations"]) != len(anchors)):
        raise ResearchError("PUBLISHER_ANCHOR_CUSTODY_MISMATCH")
    if doc["limitations"] != list(LIMITATIONS):
        raise ResearchError("PUBLISHER_PROOF_LIMITATION_TAMPERED")
    if (doc["source_document_bytes_stored"] != 0 or
            doc["commercial_reuse_approved"] is not False or
            doc["independent_outcome_labels_verified"] != 0 or
            doc["independently_scored_benchmark_cases"] != 0 or
            doc["verified_recovered_cash_cents"] != 0 or
            doc["customer_contact_actions"] != 0 or
            doc["production_changes"] != 0):
        raise ResearchError("UNAPPROVED_PUBLISHER_EVIDENCE_PROMOTION")
    expected_count = 0
    expected_fingerprints = 0
    for expected, received in zip(anchors, doc["observations"]):
        if type(received) is not dict or frozenset(received) != OBS_KEYS:
            raise ResearchError("PUBLISHER_OBSERVATION_INVALID")
        if any(received.get(field) != expected[field] for field in expected):
            raise ResearchError("PUBLISHER_OBSERVATION_CUSTODY_DRIFT")
        if any(received[field] is not False for field in (
                "source_document_bytes_stored", "commercial_reuse_approved",
                "independent_outcome_verified", "benchmark_ready")):
            raise ResearchError("UNAPPROVED_PUBLISHER_OBSERVATION_PROMOTION")
        probe = {k: received[k] for k in (
            "probe_state", "head_http_status", "media_class",
            "content_sha256", "bytes_hashed")}
        _observation(expected, probe)
        expected_count += received["head_http_status"] == 200
        expected_fingerprints += received["probe_state"] == "PUBLIC_CONTENT_FINGERPRINTED"
    if (doc["publisher_http_responses_observed"] != expected_count or
            doc["full_public_responses_fingerprinted"] != expected_fingerprints or
            doc["receipt_sha256"] != digest({k: v for k, v in doc.items() if k != "receipt_sha256"})):
        raise ResearchError("PUBLISHER_PROVENANCE_RECEIPT_DRIFT")
    return doc


def _render(doc: dict) -> str:
    return json.dumps(doc, sort_keys=True, indent=2) + "\n"


def run(*, ledger_path: Path = LEDGER, output: Path = OUTPUT,
        as_of: date | None = None, live: bool = False, verify_only: bool = False,
        fetcher=None) -> dict:
    if live and verify_only:
        raise ResearchError("MUTUALLY_EXCLUSIVE_PUBLISHER_MODES")
    ledger = read_ledger(ledger_path)
    chosen = as_of or datetime.now(timezone.utc).date()
    if type(chosen) is not date or chosen > datetime.now(timezone.utc).date():
        raise ResearchError("PUBLISHER_RECEIPT_DATE_INVALID")
    did_probe = False
    if verify_only:
        if not output.is_file():
            raise ResearchError("PUBLISHER_PROVENANCE_RECEIPT_MISSING")
        existing = output.read_text(encoding="utf-8")
        try:
            doc = json.loads(existing)
        except json.JSONDecodeError as exc:
            raise ResearchError("PUBLISHER_PROVENANCE_RECEIPT_INVALID") from exc
        _validate_receipt(doc, ledger, chosen)
        if existing != _render(doc):
            raise ResearchError("NONCANONICAL_PUBLISHER_PROVENANCE_RECEIPT")
    elif live:
        existing = None
        if output.is_file():
            try:
                previous = json.loads(output.read_text(encoding="utf-8"))
                _validate_receipt(previous, ledger, chosen)
                if _day(previous["as_of_utc_date"]) == chosen:
                    existing = previous
            except (json.JSONDecodeError, ResearchError, ValueError, KeyError, TypeError):
                existing = None
        if existing is None:
            doc = build_receipt(ledger, chosen, fetcher=fetcher)
            _validate_receipt(doc, ledger, chosen)
            output.parent.mkdir(parents=True, exist_ok=True)
            temp = output.with_name(output.name + ".tmp")
            temp.write_text(_render(doc), encoding="utf-8")
            temp.replace(output)
            did_probe = True
        else:
            doc = existing
    else:
        raise ResearchError("PUBLISHER_LIVE_OR_VERIFY_MODE_REQUIRED")
    return {
        "scope": SCOPE,
        "receipt_sha256": doc["receipt_sha256"],
        "pinned_public_sources_checked": doc["source_pointers_probed"],
        "publisher_http_responses_observed": doc["publisher_http_responses_observed"],
        "complete_bounded_public_responses_fingerprinted": doc["full_public_responses_fingerprinted"],
        "states": dict(sorted(Counter(r["probe_state"] for r in doc["observations"]).items())),
        "performed_new_network_probes": did_probe,
        "commercial_reuse_approved": False,
        "independent_outcome_labels_verified": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(ledger_path=args.ledger, output=args.output,
                         live=args.live, verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
