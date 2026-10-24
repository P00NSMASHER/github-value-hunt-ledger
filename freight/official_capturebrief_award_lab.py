"""Bounded original USAspending contract award readback for CaptureBrief.

Observes original public publisher award search and exact-award second reads.
This is same-source consistency, NOT an independently adjudicated contract
opportunity label, live SAM solicitation, buyer outreach, or commercial rights
proof. Raw award/recipient identifiers and publisher response bytes are never
committed, logged, or included in the persisted receipt.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from freight.unified_research_lab import (
    LEDGER, ROOT, NoRedirect, ResearchError, digest, global_dns, read_ledger,
)

SOURCE_ANCHOR = "https://api.usaspending.gov/docs/endpoints"
API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
OUTPUT = ROOT / "official_capturebrief_award_readback_v1.json"
SCOPE = "ORIGINAL_FEDERAL_CONTRACT_AWARD_SAME_PUBLISHER_READBACK_ONLY"
SCHEMA_VERSION = 1
MAX_ROWS = 12
MAX_SECOND_READS = 2
MAX_BACKREAD_ROWS = 20
MAX_RESPONSE_BYTES = 220000
FIXED_WINDOW = ("2025-10-01", "2026-09-30")
AWARD_TYPES = ("A", "B", "C", "D")
AWARD_FIELDS = ("Award ID", "Award Amount", "generated_internal_id",
                "Base Obligation Date")
HTTP_CODES = frozenset({
    "HTTP_400", "HTTP_401", "HTTP_403", "HTTP_404", "HTTP_408",
    "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504",
})
PROBE_ERROR_CODES = frozenset({
    "PUBLISHER_UNAVAILABLE", "HTTP_STATUS", "REDIRECT_BLOCKED",
    "SOURCE_JSON_INVALID", "SOURCE_TOO_LARGE", "INVALID_CONTENT_TYPE",
    "SOURCE_SCHEMA_CHANGED", "READBACK_INCOMPLETE",
}) | HTTP_CODES
CONSISTENCY = frozenset({"PUBLISHER_AWARD_READBACK_OK",
                         "PUBLISHER_AWARD_READBACK_DEGRADED"})
RECEIPT_FIELDS = frozenset({
    "schema_version", "scope", "as_of_utc_date", "publisher_host",
    "publisher_source_anchor_id", "source_endpoint_type",
    "contract_award_window", "user_commercial_reuse_attestation",
    "source_specific_commercial_reuse_verified", "status", "source_errors",
    "sample_rows", "distinct_award_internal_ids", "repeated_source_rows",
    "source_canonical_sample_sha256", "sample_net_awarded_amount_minor",
    "publisher_readbacks_attempted", "publisher_readbacks_exact",
    "publisher_readbacks_changed", "publisher_readbacks_ambiguous",
    "publisher_readbacks_missing", "publisher_readbacks_unavailable",
    "publisher_readback_error_codes", "source_payloads_stored", "recipient_identifiers_stored",
    "independent_sam_solicitation_matches", "independent_award_outcome_labels",
    "buyer_opportunity_truth", "realized_recovery_cents",
    "customer_contacts_sent", "new_paid_services", "production_changes",
    "limitations", "receipt_sha256",
})
LIMITATIONS = (
    "Public USAspending contract awards are publisher-origin facts, not SAM.gov live opportunity snapshots.",
    "A second query to the same publisher is a consistency check, not independent award adjudication.",
    "Published award amount is not a contract prospect's attainable revenue or proven payment.",
    "No original award identifiers, recipient identities, or response bodies are retained.",
    "Owner's broad reuse attestation is not independently source-specific license validation.",
)


def _query(*, exact_award_id: str | None = None) -> dict:
    filters = {
        "award_type_codes": list(AWARD_TYPES),
        "time_period": [{"start_date": FIXED_WINDOW[0],
                         "end_date": FIXED_WINDOW[1]}],
    }
    if exact_award_id is not None:
        if (type(exact_award_id) is not str
                or not re.fullmatch(r"[A-Za-z0-9_. /-]{1,90}", exact_award_id)
                or ".." in exact_award_id
                or exact_award_id.strip() != exact_award_id):
            raise ResearchError("UNSAFE_AWARD_ID_QUERY")
        # USAspending documents quote-wrapped award IDs for exact matching.
        filters["award_ids"] = ['"' + exact_award_id + '"']
    return {
        "filters": filters,
        "fields": list(AWARD_FIELDS),
        "limit": MAX_ROWS if exact_award_id is None else MAX_BACKREAD_ROWS,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
        "subawards": False,
    }


def _check_query(data: dict) -> dict:
    if type(data) is not dict:
        raise ResearchError("UNTRUSTED_SOURCE_QUERY")
    try:
        filters = data["filters"]
        if type(filters) is not dict:
            raise KeyError("filters")
        for val in filters.get("award_ids", []):
            if (type(val) is not str or len(val) < 3
                    or not val.startswith('"') or not val.endswith('"')):
                raise KeyError("award_ids")
        award_ids = filters.get("award_ids")
        if award_ids is None:
            expected = _query()
        else:
            if type(award_ids) is not list or len(award_ids) != 1:
                raise KeyError("award_ids")
            expected = _query(exact_award_id=award_ids[0][1:-1])
    except (KeyError, TypeError, ResearchError) as exc:
        raise ResearchError("UNTRUSTED_SOURCE_QUERY") from exc
    if data != expected:
        raise ResearchError("UNTRUSTED_SOURCE_QUERY")
    return data


def fetch_public_awards(query: dict) -> list[dict]:
    """One fixed-host, read-only search POST; bounded complete JSON response."""
    _check_query(query)
    global_dns("api.usaspending.gov")
    body = json.dumps(query, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(body) > 3000:
        raise ResearchError("UNTRUSTED_SOURCE_QUERY")
    req = Request(API, method="POST", data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "RETALLY-CaptureBrief-PublicResearch/1.0 bounded-GET-equivalent",
    })
    try:
        with build_opener(NoRedirect).open(req, timeout=12) as res:
            if res.status != 200 or res.geturl() != API:
                raise ResearchError("HTTP_STATUS")
            mime = res.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if mime != "application/json":
                raise ResearchError("INVALID_CONTENT_TYPE")
            if res.headers.get("Content-Encoding", "identity").lower().strip() not in ("", "identity"):
                raise ResearchError("INVALID_CONTENT_TYPE")
            raw = res.read(MAX_RESPONSE_BYTES + 1)
    except ResearchError:
        raise
    except HTTPError as exc:
        code = "HTTP_" + str(exc.code)
        raise ResearchError(code if code in HTTP_CODES else "HTTP_STATUS") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ResearchError("PUBLISHER_UNAVAILABLE") from exc
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise ResearchError("SOURCE_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("SOURCE_JSON_INVALID") from exc
    if (type(payload) is not dict or type(payload.get("results")) is not list
            or len(payload["results"]) > query["limit"]
            or any(type(row) is not dict for row in payload["results"])):
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    return payload["results"]


def _date(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}(?:T[0-9:.+-Z]{5,35})?", value):
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    try:
        date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ResearchError("SOURCE_SCHEMA_CHANGED") from exc
    return value[:10]


def _money_minor(value: object) -> int:
    if type(value) not in (int, float, str):
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    try:
        exact = Decimal(str(value))
        minor = exact * 100
    except (InvalidOperation, ValueError) as exc:
        raise ResearchError("SOURCE_SCHEMA_CHANGED") from exc
    if not exact.is_finite() or minor != minor.to_integral_value() or abs(minor) > 10**17:
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    return int(minor)


def _minimal(row: dict) -> dict:
    if type(row) is not dict:
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    internal = row.get("internal_id")
    if type(internal) is not int or not 1 <= internal < 10**16:
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    award = row.get("Award ID")
    if (type(award) is not str
            or not re.fullmatch(r"[A-Za-z0-9_. /-]{1,90}", award)
            or ".." in award
            or award.strip() != award):
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    generated = row.get("generated_internal_id")
    if generated is not None and (
            type(generated) is not str or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,180}", generated)):
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    return {
        "internal_id": internal,
        "award_id": award,
        "generated_internal_id": generated,
        "amount_minor": _money_minor(row.get("Award Amount")),
        "base_obligation_date": _date(row.get("Base Obligation Date")),
    }


def _source_id(ledger: dict) -> str:
    for row in ledger["entries"]:
        if row["url"] == SOURCE_ANCHOR and "capturebrief" in row["engines"]:
            if (row["commercial_reuse_authorized"] or row["independent_ground_truth"]
                    or row["document_bytes_stored"]):
                raise ResearchError("SOURCE_RIGHTS_ORIGINAL_BYTES_TAMPER")
            return row["id"]
    raise ResearchError("OFFICIAL_USASPENDING_ANCHOR_MISSING")


def _sample(fetcher) -> dict:
    raw = fetcher(_query())
    if type(raw) is not list or len(raw) > MAX_ROWS:
        raise ResearchError("SOURCE_SCHEMA_CHANGED")
    data = [_minimal(item) for item in raw]
    counts = Counter(v["internal_id"] for v in data)
    repeat = sum(n - 1 for n in counts.values())
    unique_candidates = [v for v in data if counts[v["internal_id"]] == 1]
    exact = changed = ambiguous = missing = unavailable = checked = 0
    unavailable_codes = Counter()
    for award in unique_candidates[:MAX_SECOND_READS]:
        checked += 1
        try:
            reread = fetcher(_query(exact_award_id=award["award_id"]))
        except ResearchError as exc:
            unavailable += 1
            code = str(exc)
            unavailable_codes[code if code in PROBE_ERROR_CODES
                              else "SOURCE_SCHEMA_CHANGED"] += 1
            continue
        if type(reread) is not list or len(reread) > MAX_BACKREAD_ROWS:
            raise ResearchError("SOURCE_SCHEMA_CHANGED")
        records = [_minimal(r) for r in reread]
        matching_internal = [r for r in records if r["internal_id"] == award["internal_id"]]
        if len(reread) == MAX_BACKREAD_ROWS or len(matching_internal) > 1:
            ambiguous += 1
        elif not matching_internal:
            missing += 1
        elif matching_internal[0] == award:
            exact += 1
        else:
            changed += 1
    return {
        "sample_rows": len(data),
        "distinct_award_internal_ids": len(counts),
        "repeated_source_rows": repeat,
        "source_canonical_sample_sha256": digest(data) if data else None,
        "sample_net_awarded_amount_minor": sum(v["amount_minor"] for v in data),
        "publisher_readbacks_attempted": checked,
        "publisher_readbacks_exact": exact,
        "publisher_readbacks_changed": changed,
        "publisher_readbacks_ambiguous": ambiguous,
        "publisher_readbacks_missing": missing,
        "publisher_readbacks_unavailable": unavailable,
        "publisher_readback_error_codes": dict(sorted(unavailable_codes.items())),
    }


def _empty_sample() -> dict:
    return {
        "sample_rows": 0, "distinct_award_internal_ids": 0,
        "repeated_source_rows": 0, "source_canonical_sample_sha256": None,
        "sample_net_awarded_amount_minor": 0,
        "publisher_readbacks_attempted": 0, "publisher_readbacks_exact": 0,
        "publisher_readbacks_changed": 0, "publisher_readbacks_ambiguous": 0,
        "publisher_readbacks_missing": 0, "publisher_readbacks_unavailable": 0,
        "publisher_readback_error_codes": {},
    }


def build_receipt(ledger: dict, *, as_of: date, fetcher=fetch_public_awards) -> dict:
    if type(as_of) is not date or as_of > datetime.now(timezone.utc).date():
        raise ResearchError("READBACK_DATE_INVALID")
    source = _source_id(ledger)
    try:
        result = _sample(fetcher)
        issue = []
        if result["repeated_source_rows"] > 0:
            issue.append("REPEATED_AWARD_SOURCE_ROWS")
        if (result["sample_rows"] == 0 or result["publisher_readbacks_attempted"] == 0
                or result["publisher_readbacks_exact"] != result["publisher_readbacks_attempted"]):
            issue.append("READBACK_INCOMPLETE")
    except ResearchError as exc:
        issue = [str(exc) if str(exc) in PROBE_ERROR_CODES
                 else "SOURCE_SCHEMA_CHANGED"]
        result = _empty_sample()
    status = "PUBLISHER_AWARD_READBACK_OK" if not issue else "PUBLISHER_AWARD_READBACK_DEGRADED"
    body = {
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "as_of_utc_date": as_of.isoformat(),
        "publisher_host": "api.usaspending.gov",
        "publisher_source_anchor_id": source,
        "source_endpoint_type": "USA_SPENDING_V2_PUBLIC_AWARD_SEARCH",
        "contract_award_window": list(FIXED_WINDOW),
        "user_commercial_reuse_attestation": "OWNER_ATTESTED_NOT_SOURCE_VERIFIED",
        "source_specific_commercial_reuse_verified": False,
        "status": status,
        "source_errors": issue,
        **result,
        "source_payloads_stored": 0,
        "recipient_identifiers_stored": 0,
        "independent_sam_solicitation_matches": 0,
        "independent_award_outcome_labels": 0,
        "buyer_opportunity_truth": False,
        "realized_recovery_cents": 0,
        "customer_contacts_sent": 0,
        "new_paid_services": 0,
        "production_changes": 0,
        "limitations": list(LIMITATIONS),
    }
    return {**body, "receipt_sha256": digest(body)}


def validate_receipt(doc: dict, ledger: dict, as_of: date) -> None:
    if type(doc) is not dict or frozenset(doc) != RECEIPT_FIELDS:
        raise ResearchError("INVALID_CAPTUREBRIEF_AWARD_RECEIPT")
    if (type(doc["schema_version"]) is not int or doc["schema_version"] != SCHEMA_VERSION
            or doc["scope"] != SCOPE or doc["publisher_host"] != "api.usaspending.gov"
            or doc["source_endpoint_type"] != "USA_SPENDING_V2_PUBLIC_AWARD_SEARCH"
            or doc["publisher_source_anchor_id"] != _source_id(ledger)
            or doc["contract_award_window"] != list(FIXED_WINDOW)
            or doc["user_commercial_reuse_attestation"] != "OWNER_ATTESTED_NOT_SOURCE_VERIFIED"
            or doc["source_specific_commercial_reuse_verified"] is not False
            or doc["buyer_opportunity_truth"] is not False
            or doc["limitations"] != list(LIMITATIONS)):
        raise ResearchError("CAPTUREBRIEF_AWARD_PROVENANCE_INVALID")
    try:
        observed = date.fromisoformat(doc["as_of_utc_date"])
    except (TypeError, ValueError) as exc:
        raise ResearchError("CAPTUREBRIEF_AWARD_PROVENANCE_INVALID") from exc
    if observed > as_of or (as_of - observed).days > 2:
        raise ResearchError("CAPTUREBRIEF_AWARD_PROVENANCE_STALE_OR_FUTURE")
    for k in ("source_payloads_stored", "recipient_identifiers_stored",
              "independent_sam_solicitation_matches", "independent_award_outcome_labels",
              "realized_recovery_cents", "customer_contacts_sent",
              "new_paid_services", "production_changes"):
        if type(doc[k]) is not int or doc[k] != 0:
            raise ResearchError("UNAUTHORIZED_CAPTUREBRIEF_OUTCOME_PROMOTION")
    for k in ("sample_rows", "distinct_award_internal_ids", "repeated_source_rows",
              "publisher_readbacks_attempted", "publisher_readbacks_exact",
              "publisher_readbacks_changed", "publisher_readbacks_ambiguous",
              "publisher_readbacks_missing", "publisher_readbacks_unavailable"):
        if type(doc[k]) is not int or not 0 <= doc[k] <= MAX_BACKREAD_ROWS:
            raise ResearchError("CAPTUREBRIEF_AWARD_POPULATION_INVALID")
    if (doc["sample_rows"] > MAX_ROWS
            or doc["distinct_award_internal_ids"] + doc["repeated_source_rows"] != doc["sample_rows"]
            or doc["publisher_readbacks_attempted"] > min(
                MAX_SECOND_READS, doc["distinct_award_internal_ids"])
            or doc["publisher_readbacks_attempted"] != sum(
                doc[k] for k in ("publisher_readbacks_exact", "publisher_readbacks_changed",
                                 "publisher_readbacks_ambiguous", "publisher_readbacks_missing",
                                 "publisher_readbacks_unavailable"))):
        raise ResearchError("CAPTUREBRIEF_AWARD_POPULATION_INVALID")
    if (type(doc["sample_net_awarded_amount_minor"]) is not int
            or abs(doc["sample_net_awarded_amount_minor"]) > 10**18):
        raise ResearchError("CAPTUREBRIEF_AWARD_POPULATION_INVALID")
    fingerprint = doc["source_canonical_sample_sha256"]
    if doc["sample_rows"]:
        if type(fingerprint) is not str or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ResearchError("CAPTUREBRIEF_AWARD_FINGERPRINT_INVALID")
    elif fingerprint is not None or doc["sample_net_awarded_amount_minor"]:
        raise ResearchError("CAPTUREBRIEF_AWARD_FINGERPRINT_INVALID")
    diagnostics = doc["publisher_readback_error_codes"]
    if (type(diagnostics) is not dict or len(diagnostics) > MAX_SECOND_READS
            or any(type(code) is not str or code not in PROBE_ERROR_CODES
                   or type(count) is not int or count < 1
                   for code, count in diagnostics.items())
            or sum(diagnostics.values()) != doc["publisher_readbacks_unavailable"]):
        raise ResearchError("UNSAFE_CAPTUREBRIEF_READBACK_TELEMETRY")
    if (type(doc["source_errors"]) is not list or len(doc["source_errors"]) > 3
            or any(type(code) is not str or code not in (
                PROBE_ERROR_CODES | frozenset({"REPEATED_AWARD_SOURCE_ROWS"}))
                   for code in doc["source_errors"])):
        raise ResearchError("UNSAFE_CAPTUREBRIEF_PROVIDER_ERROR")
    expected_ok = (doc["sample_rows"] > 0 and doc["repeated_source_rows"] == 0
                   and doc["publisher_readbacks_attempted"] > 0
                   and doc["publisher_readbacks_exact"] == doc["publisher_readbacks_attempted"]
                   and not doc["source_errors"])
    if ((doc["status"] == "PUBLISHER_AWARD_READBACK_OK") != expected_ok
            or doc["status"] not in CONSISTENCY):
        raise ResearchError("FALSE_GREEN_CAPTUREBRIEF_AWARD_READBACK")
    if doc["receipt_sha256"] != digest({k: v for k, v in doc.items()
                                       if k != "receipt_sha256"}):
        raise ResearchError("CAPTUREBRIEF_AWARD_RECEIPT_TAMPERED")


def run(*, ledger_path: Path = LEDGER, output: Path = OUTPUT,
        fetcher=fetch_public_awards, verify_only: bool = False,
        as_of: date | None = None) -> dict:
    ledger = read_ledger(ledger_path)
    today = datetime.now(timezone.utc).date()
    if verify_only:
        if not output.is_file():
            raise ResearchError("CAPTUREBRIEF_AWARD_RECEIPT_MISSING")
        try:
            doc = json.loads(output.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ResearchError("INVALID_CAPTUREBRIEF_AWARD_RECEIPT") from exc
        validate_receipt(doc, ledger, today)
    else:
        chosen = as_of or today
        if type(chosen) is not date or chosen > today:
            raise ResearchError("READBACK_DATE_INVALID")
        doc = None
        if output.is_file():
            try:
                existing = json.loads(output.read_text(encoding="utf-8"))
                validate_receipt(existing, ledger, today)
                if existing["as_of_utc_date"] == chosen.isoformat():
                    doc = existing
            except (ResearchError, json.JSONDecodeError, UnicodeDecodeError,
                    KeyError, TypeError, ValueError):
                pass
        if doc is None:
            doc = build_receipt(ledger, as_of=chosen, fetcher=fetcher)
            validate_receipt(doc, ledger, today)
            output.parent.mkdir(parents=True, exist_ok=True)
            target = output.with_name(output.name + ".tmp")
            target.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n",
                              encoding="utf-8")
            target.replace(output)
    return {
        "scope": SCOPE,
        "status": doc["status"],
        "sample_contract_awards": doc["sample_rows"],
        "distinct_publisher_award_ids": doc["distinct_award_internal_ids"],
        "sample_net_awarded_amount_minor": doc["sample_net_awarded_amount_minor"],
        "publisher_second_reads": doc["publisher_readbacks_attempted"],
        "publisher_second_reads_exact": doc["publisher_readbacks_exact"],
        "provider_error_codes": doc["source_errors"],
        "publisher_readback_error_codes": doc["publisher_readback_error_codes"],
        "independently_verified_solicitation_outcomes": 0,
        "source_specific_commercial_reuse_verified": False,
        "verified": verify_only,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(ledger_path=args.ledger, output=args.output,
                         verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
