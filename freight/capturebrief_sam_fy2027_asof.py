"""Research-only SAM.gov archived-opportunity original-byte and as-of chronology lab.

Use a first-party-listed, fixed public FY2027 archive object. Read source bytes
ephemerally, refuse redirects, require complete identity-encoded HTTP 200, and
publish aggregate evidence only. An archive observed on Oct 24 does not prove
a notice was visible when it was originally posted or an award was signed.
No customer messages, source approval, real award labels or production writes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from freight.unified_research_lab import (
    ROOT, NoRedirect, ResearchError, digest, global_dns,
)

SOURCE_URL = (
    "https://s3.amazonaws.com/falextracts/Contract%20Opportunities/"
    "Archived%20Data/FY2027_archived_opportunities.csv"
)
SOURCE_LISTING = (
    "https://sam.gov/data-services/Contract%20Opportunities/"
    "Archived%20Data?privacy=Public"
)
CAPTUREBRIEF_REFERENCE = (
    "P00NSMASHER/capturebrief/research/"
    "fy2027_original_bytes_observation_20261019.json"
)
PREVIOUS_PUBLIC_REFERENCE_SHA256 = (
    "7b4e00e3156248db9dcca767431bb6c5d4168aeeb2abc707ab12c0f9e61d71ce"
)
PREVIOUS_PUBLIC_REFERENCE_SIZE = 1607260
PREVIOUS_PUBLIC_REFERENCE_ROWS = 1104
OUTPUT = ROOT / "capturebrief_sam_fy2027_asof_v1.json"
SCOPE = "PUBLIC_FY2027_ARCHIVE_SOURCE_CHRONOLOGY_NOT_AWARD_TRUTH"
# Bounded FY2027 archive growth; original publisher size may still exceed this cap.
# Fail closed on oversize, row overflow, truncation, redirects and schema drift.
MAX_ORIGINAL_BYTES = 8_000_000
MAX_ORIGINAL_ROWS = 8000
REQUIRED_COLUMNS = frozenset({
    "NoticeId", "Sol#", "PostedDate", "Type", "Active",
    "AAC Code", "Office", "Link",
})
ALLOWED_ERRORS = frozenset({
    "SOURCE_HTTP_ERROR", "SOURCE_REDIRECT_BLOCKED", "SOURCE_UNAVAILABLE",
    "SOURCE_TOO_LARGE", "SOURCE_MEDIA_UNSUPPORTED", "SOURCE_ENCODING_UNSUPPORTED",
    "SOURCE_INCOMPLETE", "SOURCE_CSV_UNDECODABLE", "SOURCE_CSV_SCHEMA_INVALID",
    "SOURCE_UNKNOWN", "DNS_UNAVAILABLE", "NONPUBLIC_NETWORK",
    "SOURCE_SOLICITATION_CONTROL_QUARANTINED",
})
STATUS_OK = "PUBLIC_ARCHIVE_ROWS_OBSERVED_NOT_PRODUCTION_APPROVED"
STATUS_PARTIAL = "PUBLIC_ARCHIVE_WITH_QUARANTINED_SOLICITATION_FIELD"
STATUS_DEGRADED = "PUBLIC_ARCHIVE_UNAVAILABLE_OR_INVALID"
HOLD = "SOURCE_HISTORY_UNREVIEWED_NO_CUSTOMER_RELEASE"
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "source", "first_party_catalog_listing",
    "prior_full_byte_observation_reference", "observed_at_utc",
    "research_only_catalog_state", "source_status",
    "source_error_codes", "current_source_size_bytes", "current_source_sha256",
    "matches_oct19_full_original_byte_digest",
    "oct19_reference_original_sha256", "oct19_reference_observed_rows",
    "source_rows", "unique_original_notice_ids",
    "repeated_notice_identifiers", "source_rows_with_solicitation",
    "source_rows_quarantined_solicitation_control",
    "source_rows_with_posted_date", "source_rows_posted_after_observation_day",
    "source_issuer_ambiguous_solicitation_families",
    "asof_award_join_candidates_count",
    "independently_verified_preaward_opportunity_cases",
    "independent_cross_source_award_outcomes",
    "fy2027_full_catalog_approved", "owner_rights_attestation",
    "source_specific_reuse_rights_verified",
    "original_archive_bytes_persisted", "original_opportunity_ids_persisted",
    "customer_contact_actions", "new_paid_services",
    "production_changes", "limitations", "receipt_sha256",
})
LIMITATIONS = (
    "Published PostedDate is an issuer-declared date, not proof the source was publicly accessible that day.",
    "A later original-file observation cannot retroactively establish preaward availability.",
    "One FY2027 archive file cannot establish a fully approved SAM.gov active and multi-year history.",
    "No SAM opportunity-to-USAspending award identity has been independently joined or adjudicated.",
    "Source-specific commercial permissions and third-party data contracts are not verified by this receipt.",
)


def _utc_at(value: datetime) -> str:
    if type(value) is not datetime or value.tzinfo is None:
        raise ResearchError("SOURCE_OBSERVATION_TIME_INVALID")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _fail(code: str) -> ResearchError:
    return ResearchError(code if code in ALLOWED_ERRORS else "SOURCE_UNKNOWN")


def fetch_original() -> bytes:
    """Read only the fixed public object observed in the upstream source listing."""
    p = urlsplit(SOURCE_URL)
    if (p.scheme != "https" or p.hostname != "s3.amazonaws.com"
            or p.query or p.fragment or p.username or p.password):
        raise ResearchError("SOURCE_IDENTITY_INVALID")
    global_dns("s3.amazonaws.com")
    request = Request(SOURCE_URL, method="GET", headers={
        "User-Agent": "RETALLY-CaptureBrief-Research/1.0 bounded-public-csv",
        "Accept-Encoding": "identity",
        "Accept": "text/csv,application/octet-stream,text/plain",
    })
    try:
        with build_opener(NoRedirect).open(request, timeout=15) as response:
            if response.status != 200 or response.geturl() != SOURCE_URL:
                raise _fail("SOURCE_REDIRECT_BLOCKED")
            if response.headers.get("Content-Range"):
                raise _fail("SOURCE_INCOMPLETE")
            if response.headers.get("Content-Encoding", "identity").strip().lower() != "identity":
                raise _fail("SOURCE_ENCODING_UNSUPPORTED")
            media = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
            if media not in {"text/csv", "text/plain", "application/octet-stream",
                             "application/vnd.ms-excel"}:
                raise _fail("SOURCE_MEDIA_UNSUPPORTED")
            declared = response.headers.get("Content-Length")
            expected = None
            if declared not in (None, ""):
                try:
                    expected = int(declared)
                except ValueError as exc:
                    raise _fail("SOURCE_INCOMPLETE") from exc
                if expected < 1:
                    raise _fail("SOURCE_INCOMPLETE")
                if expected > MAX_ORIGINAL_BYTES:
                    raise _fail("SOURCE_TOO_LARGE")
            original = response.read(MAX_ORIGINAL_BYTES + 1)
    except ResearchError:
        raise
    except HTTPError as exc:
        raise _fail("SOURCE_HTTP_ERROR") from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise _fail("SOURCE_UNAVAILABLE") from exc
    if not original or (expected is not None and len(original) != expected):
        raise _fail("SOURCE_INCOMPLETE")
    if len(original) > MAX_ORIGINAL_BYTES:
        raise _fail("SOURCE_TOO_LARGE")
    return original


def _decode_csv(raw: bytes) -> str:
    if type(raw) is not bytes or not raw:
        raise _fail("SOURCE_CSV_UNDECODABLE")
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            return raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise _fail("SOURCE_CSV_UNDECODABLE") from exc
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="strict")


def _source_token(value: object, *, max_len: int = 180) -> str:
    if type(value) is not str or len(value) > max_len:
        raise _fail("SOURCE_CSV_SCHEMA_INVALID")
    if (any(unicodedata.category(c).startswith("C") for c in value)
            or unicodedata.normalize("NFC", value) != value):
        raise _fail("SOURCE_CSV_SCHEMA_INVALID")
    return " ".join(value.split()).strip()


def _posted_date(value: str) -> date | None:
    s = _source_token(value, max_len=80)
    if not s:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d\d-\d\d(?:[T ][0-9:.+\-Z]{2,36})?", s):
            return date.fromisoformat(s[:10])
        if re.fullmatch(r"\d\d/\d\d/\d{4}", s):
            return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        pass
    return None


def parse_archive(raw: bytes, *, observed_at: datetime) -> dict:
    """Hash all bytes and validate full CSV; output no row identifiers."""
    as_of = datetime.fromisoformat(_utc_at(observed_at)).date()
    try:
        reader = csv.DictReader(
            io.StringIO(_decode_csv(raw), newline=""),
            restkey="_extra", strict=True,
        )
        columns = reader.fieldnames
        if (type(columns) is not list or len(columns) != len(set(columns))
                or not REQUIRED_COLUMNS.issubset(columns)
                or any(type(x) is not str or not x.strip() or x == "_extra"
                       for x in columns)):
            raise _fail("SOURCE_CSV_SCHEMA_INVALID")
        seen_notice: set[str] = set()
        duplicates = 0
        with_sol = 0
        quarantined_solicitation = 0
        with_posted = 0
        posted_in_future = 0
        issuer_by_sol: dict[str, set[tuple[str, str]]] = defaultdict(set)
        row_count = 0
        for row in reader:
            if (type(row) is not dict or "_extra" in row
                    or any(row.get(c) is None for c in columns)):
                raise _fail("SOURCE_CSV_SCHEMA_INVALID")
            row_count += 1
            if row_count > MAX_ORIGINAL_ROWS:
                raise _fail("SOURCE_TOO_LARGE")
            notice = _source_token(row["NoticeId"], max_len=128).upper()
            if not notice:
                raise _fail("SOURCE_CSV_SCHEMA_INVALID")
            if notice in seen_notice:
                duplicates += 1
            else:
                seen_notice.add(notice)
            try:
                solicitation = _source_token(row["Sol#"], max_len=180).upper()
            except ResearchError:
                # Treat a control character in publisher data as an observed,
                # counted source anomaly, never an independently usable key.
                quarantined_solicitation += 1
                solicitation = ""
            if solicitation:
                with_sol += 1
                agency = _source_token(row["AAC Code"], max_len=80).upper()
                office = _source_token(row["Office"], max_len=140).upper()
                issuer_by_sol[solicitation].add((agency, office))
            posted = _posted_date(row["PostedDate"])
            if posted is not None:
                with_posted += 1
                if posted > as_of:
                    posted_in_future += 1
            # Source descriptions, contact emails, origin links, NoticeIds,
            # solicitation numbers and row bytes never escape this scope.
    except (csv.Error, UnicodeDecodeError, ValueError) as exc:
        raise _fail("SOURCE_CSV_SCHEMA_INVALID") from exc
    if row_count == 0:
        raise _fail("SOURCE_CSV_SCHEMA_INVALID")
    return {
        "current_source_size_bytes": len(raw),
        "current_source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_rows": row_count,
        "unique_original_notice_ids": len(seen_notice),
        "repeated_notice_identifiers": duplicates,
        "source_rows_with_solicitation": with_sol,
        "source_rows_quarantined_solicitation_control": quarantined_solicitation,
        "source_rows_with_posted_date": with_posted,
        "source_rows_posted_after_observation_day": posted_in_future,
        "source_issuer_ambiguous_solicitation_families": sum(
            1 for issuers in issuer_by_sol.values()
            if len(issuers) != 1 or any(not a or not o for a, o in issuers)
        ),
    }


def assess_cross_source_chronology(
    sam_action: dict, award: dict, *, source_observed_at: datetime,
) -> str:
    """Never turn archive retrospective membership into a preaward truth label.

    Caller must provide independently authenticated same-issuer identifiers;
    otherwise the exact solicitation number is ambiguous by construction.
    This pure function does not contact either agency and stores no IDs.
    """
    source_day = datetime.fromisoformat(_utc_at(source_observed_at)).date()
    if type(sam_action) is not dict or type(award) is not dict:
        return "MALFORMED_SOURCE_UNKNOWN"
    def clean(value: object) -> str:
        if type(value) is not str:
            return ""
        if len(value) > 180:
            return ""
        return " ".join(value.upper().split()).strip()
    sol = clean(sam_action.get("solicitation_number"))
    target = clean(award.get("solicitation_identifier"))
    agency = clean(sam_action.get("agency_code"))
    other_agency = clean(award.get("matched_issuer_agency_code"))
    office = clean(sam_action.get("office"))
    other_office = clean(award.get("matched_issuer_office"))
    if not sol or not target or sol != target:
        return "UNMATCHED_OR_UNKNOWN"
    if not agency or not other_agency or not office or not other_office:
        return "ISSUER_NOT_INDEPENDENTLY_MATCHED"
    if agency != other_agency or office != other_office:
        return "ISSUER_CONFLICT"
    try:
        posted = _posted_date(sam_action.get("posted_date"))
        signed = _posted_date(award.get("award_date_signed"))
    except ResearchError:
        return "SOURCE_DATE_UNKNOWN"
    if posted is None or signed is None:
        return "SOURCE_DATE_UNKNOWN"
    if posted >= signed:
        return "FUTURE_POSTED_NOTICE_NOT_PREAWARD"
    if source_day >= signed:
        # Crucial anti-leakage guard: PostedDate is not proof the specific
        # archived source was captured before the award happened.
        return "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF"
    return "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY"


def build_receipt(*, observed_at: datetime, fetcher=fetch_original) -> dict:
    utc = _utc_at(observed_at)
    try:
        body = parse_archive(fetcher(), observed_at=observed_at)
        if body["source_rows_quarantined_solicitation_control"]:
            status = STATUS_PARTIAL
            errors = ["SOURCE_SOLICITATION_CONTROL_QUARANTINED"]
        else:
            status, errors = STATUS_OK, []
    except ResearchError as exc:
        status = STATUS_DEGRADED
        code = str(exc)
        errors = [code if code in ALLOWED_ERRORS else "SOURCE_UNKNOWN"]
        body = {
            "current_source_size_bytes": 0,
            "current_source_sha256": None,
            "source_rows": 0,
            "unique_original_notice_ids": 0,
            "repeated_notice_identifiers": 0,
            "source_rows_with_solicitation": 0,
            "source_rows_quarantined_solicitation_control": 0,
            "source_rows_with_posted_date": 0,
            "source_rows_posted_after_observation_day": 0,
            "source_issuer_ambiguous_solicitation_families": 0,
        }
    receipt = {
        "schema_version": 1,
        "scope": SCOPE,
        "source": SOURCE_URL,
        "first_party_catalog_listing": SOURCE_LISTING,
        "prior_full_byte_observation_reference": CAPTUREBRIEF_REFERENCE,
        "observed_at_utc": utc,
        "research_only_catalog_state": HOLD,
        "source_status": status,
        "source_error_codes": errors,
        **body,
        "matches_oct19_full_original_byte_digest": (
            body["current_source_sha256"] == PREVIOUS_PUBLIC_REFERENCE_SHA256
        ),
        "oct19_reference_original_sha256": PREVIOUS_PUBLIC_REFERENCE_SHA256,
        "oct19_reference_observed_rows": PREVIOUS_PUBLIC_REFERENCE_ROWS,
        "asof_award_join_candidates_count": 0,
        "independently_verified_preaward_opportunity_cases": 0,
        "independent_cross_source_award_outcomes": 0,
        "fy2027_full_catalog_approved": False,
        "owner_rights_attestation": "OWNER_ATTESTED_NOT_SOURCE_VERIFIED",
        "source_specific_reuse_rights_verified": False,
        "original_archive_bytes_persisted": 0,
        "original_opportunity_ids_persisted": 0,
        "customer_contact_actions": 0,
        "new_paid_services": 0,
        "production_changes": 0,
        "limitations": list(LIMITATIONS),
    }
    return {**receipt, "receipt_sha256": digest(receipt)}


def validate_receipt(doc: dict, *, now: datetime) -> None:
    observed_now = datetime.fromisoformat(_utc_at(now))
    if type(doc) is not dict or frozenset(doc) != RECEIPT_KEYS:
        raise ResearchError("ARCHIVE_RECEIPT_INVALID")
    if (type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or doc["scope"] != SCOPE or doc["source"] != SOURCE_URL
            or doc["first_party_catalog_listing"] != SOURCE_LISTING
            or doc["prior_full_byte_observation_reference"] != CAPTUREBRIEF_REFERENCE
            or doc["research_only_catalog_state"] != HOLD
            or doc["oct19_reference_original_sha256"] != PREVIOUS_PUBLIC_REFERENCE_SHA256
            or doc["oct19_reference_observed_rows"] != PREVIOUS_PUBLIC_REFERENCE_ROWS
            or doc["fy2027_full_catalog_approved"] is not False
            or doc["source_specific_reuse_rights_verified"] is not False
            or doc["owner_rights_attestation"] != "OWNER_ATTESTED_NOT_SOURCE_VERIFIED"
            or doc["limitations"] != list(LIMITATIONS)):
        raise ResearchError("ARCHIVE_AUTHORITY_OR_SOURCE_DRIFT")
    try:
        obs = datetime.fromisoformat(doc["observed_at_utc"])
    except (ValueError, TypeError) as exc:
        raise ResearchError("ARCHIVE_RECEIPT_TIME_INVALID") from exc
    if (obs.tzinfo is None or obs.utcoffset().total_seconds() != 0
            or obs > observed_now or (observed_now - obs).total_seconds() > 172800):
        raise ResearchError("ARCHIVE_RECEIPT_STALE_OR_FUTURE")
    for k in ("asof_award_join_candidates_count",
              "independently_verified_preaward_opportunity_cases",
              "independent_cross_source_award_outcomes",
              "original_archive_bytes_persisted", "original_opportunity_ids_persisted",
              "customer_contact_actions", "new_paid_services", "production_changes"):
        if type(doc[k]) is not int or doc[k] != 0:
            raise ResearchError("ARCHIVE_UNAPPROVED_EVIDENCE_PROMOTION")
    for k in ("source_rows", "unique_original_notice_ids",
              "repeated_notice_identifiers", "source_rows_with_solicitation",
              "source_rows_quarantined_solicitation_control",
              "source_rows_with_posted_date", "source_rows_posted_after_observation_day",
              "source_issuer_ambiguous_solicitation_families"):
        if type(doc[k]) is not int or not 0 <= doc[k] <= MAX_ORIGINAL_ROWS:
            raise ResearchError("ARCHIVE_ROW_COUNT_INVALID")
    if (doc["unique_original_notice_ids"] + doc["repeated_notice_identifiers"]
            != doc["source_rows"]
            or (doc["source_rows_with_solicitation"] +
                doc["source_rows_quarantined_solicitation_control"]) > doc["source_rows"]
            or doc["source_rows_with_posted_date"] > doc["source_rows"]
            or doc["source_rows_posted_after_observation_day"] > doc["source_rows_with_posted_date"]
            or doc["source_issuer_ambiguous_solicitation_families"] >
                doc["source_rows_with_solicitation"]):
        raise ResearchError("ARCHIVE_SOURCE_POPULATION_INVALID")
    if type(doc["source_error_codes"]) is not list or any(
            type(x) is not str or x not in ALLOWED_ERRORS for x in doc["source_error_codes"]
    ) or len(doc["source_error_codes"]) > 1:
        raise ResearchError("ARCHIVE_SOURCE_ERROR_INVALID")
    if doc["source_status"] in (STATUS_OK, STATUS_PARTIAL):
        if (doc["source_rows"] < 1
                or type(doc["current_source_size_bytes"]) is not int
                or not 1 <= doc["current_source_size_bytes"] <= MAX_ORIGINAL_BYTES
                or type(doc["current_source_sha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", doc["current_source_sha256"])):
            raise ResearchError("ARCHIVE_FALSE_GREEN")
        issues = doc["source_rows_quarantined_solicitation_control"]
        if (doc["source_status"] == STATUS_OK and
                (issues != 0 or doc["source_error_codes"])):
            raise ResearchError("ARCHIVE_FALSE_GREEN")
        if (doc["source_status"] == STATUS_PARTIAL and
                (issues == 0 or doc["source_error_codes"] !=
                 ["SOURCE_SOLICITATION_CONTROL_QUARANTINED"])):
            raise ResearchError("ARCHIVE_FALSE_GREEN")
    elif doc["source_status"] == STATUS_DEGRADED:
        if (doc["source_rows"] != 0 or doc["current_source_sha256"] is not None
                or doc["current_source_size_bytes"] != 0
                or doc["source_rows_quarantined_solicitation_control"] != 0
                or len(doc["source_error_codes"]) != 1):
            raise ResearchError("ARCHIVE_FALSE_GREEN")
    else:
        raise ResearchError("ARCHIVE_SOURCE_STATUS_INVALID")
    if doc["matches_oct19_full_original_byte_digest"] is not (
            doc["current_source_sha256"] == PREVIOUS_PUBLIC_REFERENCE_SHA256):
        raise ResearchError("ARCHIVE_PREVIOUS_BYTE_PROOF_MISREPRESENTED")
    if doc["receipt_sha256"] != digest({
            k: v for k, v in doc.items() if k != "receipt_sha256"
    }):
        raise ResearchError("ARCHIVE_RECEIPT_HASH_INVALID")


def run(*, output: Path = OUTPUT, fetcher=fetch_original,
        now: datetime | None = None, verify_only: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    normalized_now = datetime.fromisoformat(_utc_at(now))
    if verify_only:
        if not output.is_file():
            raise ResearchError("ARCHIVE_RECEIPT_MISSING")
        try:
            receipt = json.loads(output.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ResearchError("ARCHIVE_RECEIPT_INVALID") from exc
        validate_receipt(receipt, now=normalized_now)
    else:
        receipt = None
        if output.is_file():
            try:
                previous = json.loads(output.read_text(encoding="utf-8"))
                validate_receipt(previous, now=normalized_now)
                if previous["observed_at_utc"][:10] == normalized_now.date().isoformat():
                    receipt = previous
            except (ResearchError, ValueError, TypeError, KeyError, UnicodeDecodeError):
                pass
        if receipt is None:
            receipt = build_receipt(observed_at=normalized_now, fetcher=fetcher)
            validate_receipt(receipt, now=normalized_now)
            output.parent.mkdir(parents=True, exist_ok=True)
            temp = output.with_name(output.name + ".tmp")
            temp.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
            temp.replace(output)
    return {
        "scope": SCOPE,
        "source_status": receipt["source_status"],
        "source_rows": receipt["source_rows"],
        "unique_notice_ids": receipt["unique_original_notice_ids"],
        "source_rows_quarantined_solicitation_control":
            receipt["source_rows_quarantined_solicitation_control"],
        "original_source_bytes": receipt["current_source_size_bytes"],
        "source_digest_matches_historical_oct19": receipt[
            "matches_oct19_full_original_byte_digest"
        ],
        "source_error_codes": receipt["source_error_codes"],
        "observed_at_utc": receipt["observed_at_utc"],
        "real_cross_source_award_labels": 0,
        "production_catalog_approved": False,
        "verified": verify_only,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    print(json.dumps(run(output=args.output, verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
