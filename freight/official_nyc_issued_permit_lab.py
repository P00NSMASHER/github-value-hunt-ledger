"""Original NYC DOB NOW issued-permit publisher data: bounded, read-only readback.

This validates original official JSON records and repeat GET consistency,
not the user's commercial rights, contractor intent, buyer demand, or any
independently adjudicated outcome. Public row content stays in runner memory;
only source-level counts and SHA-256 receipts enter the research branch.
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
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, build_opener

from freight.unified_research_lab import (
    LEDGER, ROOT, NoRedirect, ResearchError, digest, global_dns, read_ledger,
)

OFFICIAL_HOST = "data.cityofnewyork.us"
DATASET_ID = "rbx6-tga4"
SOURCE_URL = "https://data.cityofnewyork.us/d/" + DATASET_ID
RESOURCE_PATH = "/resource/" + DATASET_ID + ".json"
API = "https://" + OFFICIAL_HOST + RESOURCE_PATH
NYC_SOURCE_TERMS = "https://www.nyc.gov/opendata/get-started/FAQs"
OUTPUT = ROOT / "official_nyc_issued_permit_replay_v1.json"
SCOPE = "ORIGINAL_NYC_PERMIT_SOURCE_READBACK_NOT_INDEPENDENT_OUTCOME"
MAX_BODY_BYTES = 160_000
MAX_ROWS = 20
MAX_READBACK = 3
FIELDS = ("tracking_number", "job_filing_number", "work_permit", "issued_date", "permit_status")
QUERY_WHERE = "issued_date IS NOT NULL AND tracking_number IS NOT NULL"
QUERY_ORDER = "issued_date DESC,tracking_number DESC"
ALLOWED_STATES = frozenset({
    "PUBLISHER_READBACK_OK", "PUBLISHER_READBACK_DEGRADED",
    "PUBLISHER_UNAVAILABLE", "SOURCE_SCHEMA_CHANGED",
})
PROBE_CODES = frozenset({
    "PUBLISHER_UNAVAILABLE", "HTTP_STATUS", "REDIRECT_BLOCKED",
    "INVALID_CONTENT_TYPE", "SOURCE_TOO_LARGE", "SOURCE_JSON_INVALID",
    "SCHEMA_CHANGED", "DUPLICATE_SAMPLE_KEY", "READBACK_SOURCE_MISMATCH",
    "READBACK_NOT_FOUND", "INVALID_TRACKING_NUMBER",
})
KNOWN_NOT_ISSUED_TEXT = "permit is not yet issued"


def query_url(*, tracking_number: str | int | None = None) -> str:
    args = {
        "$select": ",".join(FIELDS),
        "$limit": str(MAX_ROWS),
    }
    if tracking_number is None:
        args["$where"] = QUERY_WHERE
        args["$order"] = QUERY_ORDER
    else:
        if type(tracking_number) is int:
            if not 1 <= tracking_number < 10**15:
                raise ResearchError("INVALID_TRACKING_NUMBER")
            token = str(tracking_number)
        elif type(tracking_number) is str and re.fullmatch(r"[A-Za-z0-9-]{3,32}", tracking_number):
            token = "'" + tracking_number + "'"
        else:
            raise ResearchError("INVALID_TRACKING_NUMBER")
        args["$where"] = "tracking_number = " + token
    return API + "?" + urlencode(args)


def _validate_target(url: str) -> str:
    if type(url) is not str:
        raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    p = urlsplit(url)
    if (p.scheme != "https" or p.netloc != OFFICIAL_HOST or p.path != RESOURCE_PATH
            or p.fragment or p.username or p.password):
        raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    query = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
    if set(query) not in ({"$select", "$limit", "$where", "$order"},
                         {"$select", "$limit", "$where"}):
        raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    if any(len(v) != 1 for v in query.values()):
        raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    if query.get("$select") != [",".join(FIELDS)]:
        raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    if query.get("$order") == [QUERY_ORDER]:
        if url != query_url():
            raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    else:
        expression = query.get("$where", [""])[0]
        if query.get("$limit") != [str(MAX_ROWS)]:
            raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
        part = expression.removeprefix("tracking_number = ")
        if part.isdigit():
            expected = query_url(tracking_number=int(part))
        elif re.fullmatch(r"'[A-Za-z0-9-]{3,32}'", part):
            expected = query_url(tracking_number=part[1:-1])
        else:
            raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
        if url != expected:
            raise ResearchError("PUBLIC_DATASET_TARGET_INVALID")
    return url


def fetch_rows(url: str) -> list[dict]:
    """Only a narrowly predeclared original publisher dataset and fields."""
    _validate_target(url)
    global_dns(OFFICIAL_HOST)
    req = Request(url, method="GET", headers={
        "Accept": "application/json", "Accept-Encoding": "identity",
        "User-Agent": "RETALLY-Research/1.0 original public dataset read-only",
    })
    try:
        with build_opener(NoRedirect).open(req, timeout=10) as r:
            if r.status != 200 or r.geturl() != url:
                raise ResearchError("HTTP_STATUS")
            media = r.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if media not in {"application/json", "application/vnd.socrata+json"}:
                raise ResearchError("INVALID_CONTENT_TYPE")
            if r.headers.get("Content-Encoding", "identity").lower().strip() not in {"", "identity"}:
                raise ResearchError("INVALID_CONTENT_TYPE")
            raw = r.read(MAX_BODY_BYTES + 1)
    except ResearchError:
        raise
    except HTTPError as exc:
        raise ResearchError("HTTP_STATUS") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ResearchError("PUBLISHER_UNAVAILABLE") from exc
    if not raw or len(raw) > MAX_BODY_BYTES:
        raise ResearchError("SOURCE_TOO_LARGE")
    try:
        items = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("SOURCE_JSON_INVALID") from exc
    if type(items) is not list or len(items) > MAX_ROWS or any(type(x) is not dict for x in items):
        raise ResearchError("SCHEMA_CHANGED")
    return items


def _date(value: object, as_of: date) -> str:
    if type(value) is not str or len(value) > 40:
        raise ResearchError("SCHEMA_CHANGED")
    if not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z?)?",
            value):
        raise ResearchError("SCHEMA_CHANGED")
    raw = value[:10]
    try:
        dt = date.fromisoformat(raw)
    except ValueError as exc:
        raise ResearchError("SCHEMA_CHANGED") from exc
    if dt > as_of or dt.year < 2016:
        raise ResearchError("SCHEMA_CHANGED")
    return raw


def _minimal(row: dict, as_of: date) -> dict:
    if type(row) is not dict:
        raise ResearchError("SCHEMA_CHANGED")
    ident = row.get("tracking_number")
    if type(ident) is int:
        if not 1 <= ident < 10**15:
            raise ResearchError("SCHEMA_CHANGED")
    elif type(ident) is str:
        if not re.fullmatch(r"[A-Za-z0-9-]{3,32}", ident):
            raise ResearchError("SCHEMA_CHANGED")
    else:
        raise ResearchError("SCHEMA_CHANGED")
    job = row.get("job_filing_number")
    permit = row.get("work_permit")
    if type(job) is not str or not re.fullmatch(r"[A-Za-z0-9-]{3,48}", job):
        raise ResearchError("SCHEMA_CHANGED")
    if type(permit) is not str or not 1 <= len(permit) <= 90:
        raise ResearchError("SCHEMA_CHANGED")
    status = row.get("permit_status")
    if status is not None and (type(status) is not str or len(status) > 90):
        raise ResearchError("SCHEMA_CHANGED")
    sequence = row.get("sequence_number")
    if sequence is not None and (type(sequence) not in (str, int)
                                 or len(str(sequence)) > 12
                                 or not re.fullmatch(r"[A-Za-z0-9-]{1,12}", str(sequence))):
        raise ResearchError("SCHEMA_CHANGED")
    return {
        "tracking_number": ident,
        "job_filing_number": job,
        "work_permit": permit,
        "sequence_number": str(sequence) if sequence is not None else None,
        "issued_date": _date(row.get("issued_date"), as_of),
        "permit_status": status,
    }


def _key(row: dict) -> tuple[str, str, str, str | None]:
    # One tracking number can cover multiple work permits or sequences.
    return (str(row["tracking_number"]), row["job_filing_number"],
            row["work_permit"], row["sequence_number"])


def _classification(row: dict) -> str:
    if KNOWN_NOT_ISSUED_TEXT in row["work_permit"].lower():
        return "PUBLISHER_NOT_YET_ISSUED_MARKER"
    # A dated record in an approved-permits dataset does not independently
    # establish buyer opportunity, contractor demand or current permit validity.
    return "PUBLISHER_ISSUE_DATE_PRESENT"


def _source_anchor(ledger: dict) -> str:
    for row in ledger["entries"]:
        if row["url"] == SOURCE_URL and "permitplate" in row["engines"]:
            if row["commercial_reuse_authorized"] or row["independent_ground_truth"]:
                raise ResearchError("FORGED_PUBLISHER_SOURCE_RIGHTS")
            return row["id"]
    raise ResearchError("APPROVED_PERMIT_SOURCE_NOT_IN_LEDGER")


def _process(fetcher, as_of: date) -> dict:
    rows = fetcher(query_url())
    if type(rows) is not list or len(rows) > MAX_ROWS:
        raise ResearchError("SCHEMA_CHANGED")
    examples = [_minimal(row, as_of) for row in rows]
    # The live publisher can legitimately include repeated permit snapshots.
    # They count as repeat rows, not independent permits or schema corruption.
    key_counts = Counter(_key(row) for row in examples)
    repeated = sum(n - 1 for n in key_counts.values())
    distinct = len(key_counts)
    unique_for_readback = [
        row for row in examples if key_counts[_key(row)] == 1
    ]
    matched = missing = changed = ambiguous = unavailable = checked = 0
    for row in unique_for_readback[:MAX_READBACK]:
        checked += 1
        try:
            readback = fetcher(query_url(tracking_number=row["tracking_number"]))
        except ResearchError:
            unavailable += 1
            continue
        if type(readback) is not list or len(readback) > MAX_ROWS:
            raise ResearchError("SCHEMA_CHANGED")
        normalized = [_minimal(x, as_of) for x in readback]
        exact = [x for x in normalized if x == row]
        # Re-read pagination might be capped. Even an exact match is ambiguous
        # when publisher records fill the whole window or repeat exactly.
        if len(readback) == MAX_ROWS or len(exact) > 1:
            ambiguous += 1
        elif len(exact) == 1:
            matched += 1
        elif any(_key(x) == _key(row) for x in normalized):
            changed += 1
        else:
            missing += 1
    classifications = {
        "publisher_issue_date_present": sum(
            _classification(x) == "PUBLISHER_ISSUE_DATE_PRESENT" for x in examples),
        "publisher_not_yet_issued_marker": sum(
            _classification(x) == "PUBLISHER_NOT_YET_ISSUED_MARKER" for x in examples),
    }
    return {
        "sample_count": len(examples),
        "sample_unique_source_identities": distinct,
        "sample_repeated_source_rows": repeated,
        "sample_canonical_sha256": digest(examples),
        "readback_checked": checked,
        "readback_exact_match": matched,
        "readback_changed": changed,
        "readback_missing": missing,
        "readback_ambiguous": ambiguous,
        "readback_unavailable": unavailable,
        "publisher_status_classifications": classifications,
    }

def build_receipt(ledger: dict, *, as_of: date,
                  fetcher=fetch_rows) -> dict:
    if type(as_of) is not date or as_of > datetime.now(timezone.utc).date():
        raise ResearchError("INVALID_AS_OF_DATE")
    anchor = _source_anchor(ledger)
    try:
        proof = _process(fetcher, as_of)
        issues = []
        if proof["sample_repeated_source_rows"] > 0:
            issues.append("DUPLICATE_SOURCE_IDENTITIES")
        if (proof["readback_checked"] == 0 or
                proof["readback_exact_match"] != proof["readback_checked"]):
            issues.append("PUBLISHER_ROW_READBACK_INCOMPLETE")
        status = ("PUBLISHER_REPLAY_OK"
                  if proof["sample_count"] > 0 and not issues
                  else "PUBLISHER_REPLAY_DEGRADED")
    except ResearchError as exc:
        if str(exc) in {"SCHEMA_CHANGED"}:
            raise
        issues = [str(exc) if str(exc) in {
            "PUBLISHER_UNAVAILABLE", "HTTP_STATUS", "REDIRECT_BLOCKED",
            "INVALID_CONTENT_TYPE", "SOURCE_TOO_LARGE", "SOURCE_JSON_INVALID",
            "DNS_UNAVAILABLE", "NONPUBLIC_NETWORK",
        } else "PUBLIC_SOURCE_READBACK_UNAVAILABLE"]
        status = "PUBLISHER_REPLAY_DEGRADED"
        proof = {
            "sample_count": 0, "sample_unique_source_identities": 0,
            "sample_repeated_source_rows": 0, "sample_canonical_sha256": None,
            "readback_checked": 0, "readback_exact_match": 0,
            "readback_changed": 0, "readback_missing": 0,
            "readback_ambiguous": 0, "readback_unavailable": 0,
            "publisher_status_classifications": {
                "publisher_issue_date_present": 0,
                "publisher_not_yet_issued_marker": 0,
            },
        }
    base = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of_utc_date": as_of.isoformat(),
        "official_dataset_id": DATASET_ID,
        "official_source_id": anchor,
        "official_source_url": SOURCE_URL,
        "published_source_terms": NYC_SOURCE_TERMS,
        "user_commercial_reuse_attestation": "OWNER_ATTESTED_NOT_SOURCE_VERIFIED",
        "source_specific_commercial_license_verified": False,
        "status": status,
        "source_errors": issues,
        **proof,
        "sample_original_rows_stored": 0,
        "independent_issuance_outcome_labels": 0,
        "buyer_opportunity_ground_truth": False,
        "external_customer_contacts": 0,
        "new_paid_services": 0,
        "production_changes": 0,
        "notes": (
            "Dated original publisher records and second reads are factual "
            "source-consistency checks, not commercial-use clearance, "
            "independently adjudicated permit truth or buyer demand."
        ),
    }
    return {**base, "receipt_sha256": digest(base)}


def _check(receipt: dict, ledger: dict, now: date) -> None:
    if type(receipt) is not dict:
        raise ResearchError("INVALID_READBACK_RECEIPT")
    anchor = _source_anchor(ledger)
    required = set(build_receipt_keys())
    if set(receipt) != required:
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if (type(receipt["schema_version"]) is not int or
            receipt["official_dataset_id"] != DATASET_ID or
            receipt["official_source_id"] != anchor or
            receipt["official_source_url"] != SOURCE_URL or
            receipt["published_source_terms"] != NYC_SOURCE_TERMS or
            receipt["scope"] != SCOPE or
            receipt["schema_version"] != 1 or
            receipt["user_commercial_reuse_attestation"] !=
                "OWNER_ATTESTED_NOT_SOURCE_VERIFIED" or
            receipt["source_specific_commercial_license_verified"] is not False or
            receipt["buyer_opportunity_ground_truth"] is not False):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if (type(receipt["sample_original_rows_stored"]) is not int or
            receipt["sample_original_rows_stored"] != 0 or
            type(receipt["independent_issuance_outcome_labels"]) is not int or
            receipt["independent_issuance_outcome_labels"] != 0 or
            type(receipt["new_paid_services"]) is not int or
            receipt["new_paid_services"] != 0 or
            type(receipt["external_customer_contacts"]) is not int or
            receipt["external_customer_contacts"] != 0 or
            type(receipt["production_changes"]) is not int or
            receipt["production_changes"] != 0):
        raise ResearchError("UNAUTHORIZED_PROOF_PROMOTION")
    observed = date.fromisoformat(receipt["as_of_utc_date"])
    if observed > now or (now - observed).days > 2:
        raise ResearchError("STALE_OR_FUTURE_READBACK_RECEIPT")
    for x in ("sample_count", "sample_unique_source_identities",
              "sample_repeated_source_rows", "readback_checked",
              "readback_exact_match", "readback_changed", "readback_missing",
              "readback_ambiguous", "readback_unavailable"):
        if type(receipt[x]) is not int or not 0 <= receipt[x] <= MAX_ROWS:
            raise ResearchError("INVALID_READBACK_RECEIPT")
    if (receipt["sample_unique_source_identities"] +
            receipt["sample_repeated_source_rows"] != receipt["sample_count"]):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if receipt["readback_checked"] != (
            receipt["readback_exact_match"] + receipt["readback_changed"]
            + receipt["readback_missing"] + receipt["readback_ambiguous"]
            + receipt["readback_unavailable"]):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if receipt["readback_checked"] > min(
            MAX_READBACK,
            receipt["sample_unique_source_identities"]):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    c = receipt["publisher_status_classifications"]
    if (type(c) is not dict or
            set(c) != {"publisher_issue_date_present", "publisher_not_yet_issued_marker"}
            or any(type(v) is not int or v < 0 for v in c.values())
            or sum(c.values()) != receipt["sample_count"]):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if receipt["status"] not in {"PUBLISHER_REPLAY_OK", "PUBLISHER_REPLAY_DEGRADED"}:
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if (receipt["status"] == "PUBLISHER_REPLAY_OK" and (
            receipt["sample_count"] < 1 or
            receipt["readback_checked"] < 1 or
            receipt["readback_checked"] != receipt["readback_exact_match"] or
            receipt["sample_repeated_source_rows"] or
            receipt["source_errors"])):
        raise ResearchError("FALSE_GREEN_PUBLISHER_READBACK")
    if receipt["sample_count"] and (
            type(receipt["sample_canonical_sha256"]) is not str or
            not re.fullmatch(r"[a-f0-9]{64}", receipt["sample_canonical_sha256"])):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if receipt["sample_count"] == 0 and receipt["sample_canonical_sha256"] is not None:
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if (type(receipt["source_errors"]) is not list or
            len(receipt["source_errors"]) > 5 or
            any(type(x) is not str or x not in {
                "PUBLISHER_UNAVAILABLE", "HTTP_STATUS", "REDIRECT_BLOCKED",
                "INVALID_CONTENT_TYPE", "SOURCE_TOO_LARGE", "SOURCE_JSON_INVALID",
                "DNS_UNAVAILABLE", "NONPUBLIC_NETWORK",
                "PUBLIC_SOURCE_READBACK_UNAVAILABLE",
                "PUBLISHER_ROW_READBACK_INCOMPLETE",
                "DUPLICATE_SOURCE_IDENTITIES",
            } for x in receipt["source_errors"])):
        raise ResearchError("UNSAFE_READBACK_DIAGNOSTICS")
    if type(receipt["notes"]) is not str or not receipt["notes"].startswith(
            "Dated original publisher records"):
        raise ResearchError("INVALID_READBACK_RECEIPT")
    if receipt["receipt_sha256"] != digest({
            k: v for k, v in receipt.items() if k != "receipt_sha256"}):
        raise ResearchError("READBACK_RECEIPT_TAMPERED")


def build_receipt_keys() -> tuple[str, ...]:
    return (
        "schema_version", "scope", "as_of_utc_date", "official_dataset_id",
        "official_source_id", "official_source_url", "published_source_terms",
        "user_commercial_reuse_attestation",
        "source_specific_commercial_license_verified", "status", "source_errors",
        "sample_count", "sample_unique_source_identities",
        "sample_repeated_source_rows", "sample_canonical_sha256",
        "readback_checked", "readback_exact_match", "readback_changed",
        "readback_missing", "readback_ambiguous", "readback_unavailable",
        "publisher_status_classifications", "sample_original_rows_stored",
        "independent_issuance_outcome_labels", "buyer_opportunity_ground_truth",
        "external_customer_contacts", "new_paid_services", "production_changes",
        "notes", "receipt_sha256",
    )


def run(*, ledger_path: Path = LEDGER, output: Path = OUTPUT,
        fetcher=fetch_rows, verify_only: bool = False,
        as_of: date | None = None) -> dict:
    ledger = read_ledger(ledger_path)
    today = datetime.now(timezone.utc).date()
    if verify_only:
        if not output.is_file():
            raise ResearchError("READBACK_RECEIPT_MISSING")
        try:
            receipt = json.loads(output.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ResearchError("INVALID_READBACK_RECEIPT") from exc
        _check(receipt, ledger, today)
    else:
        chosen = as_of or today
        if type(chosen) is not date or chosen > today:
            raise ResearchError("INVALID_AS_OF_DATE")
        receipt = None
        if output.is_file():
            try:
                former = json.loads(output.read_text(encoding="utf-8"))
                _check(former, ledger, today)
                if former["as_of_utc_date"] == chosen.isoformat():
                    receipt = former
            except (ResearchError, json.JSONDecodeError, UnicodeDecodeError,
                    KeyError, TypeError, ValueError):
                pass
        if receipt is None:
            receipt = build_receipt(ledger, as_of=chosen, fetcher=fetcher)
            _check(receipt, ledger, today)
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name + ".tmp")
            temporary.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
            temporary.replace(output)
    return {
        "status": receipt["status"],
        "source_rows_replayed": receipt["sample_count"],
        "distinct_publisher_source_identities": receipt["sample_unique_source_identities"],
        "repeated_publisher_source_rows": receipt["sample_repeated_source_rows"],
        "original_publisher_second_reads": receipt["readback_checked"],
        "ambiguous_or_unavailable_second_reads": (
            receipt["readback_ambiguous"] + receipt["readback_unavailable"]),
        "publisher_consistent_reads": receipt["readback_exact_match"],
        "publisher_data_changed": receipt["readback_changed"],
        "source_specific_rights_verified": False,
        "independent_labels": 0,
        "scope": SCOPE,
        "verified": verify_only,
        "errors": receipt["source_errors"],
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
