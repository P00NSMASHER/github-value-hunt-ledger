"""Private, read-only observations over existing Business OS source records.

Counts describe records visible to the injected database executor. They are not
settlement evidence, verified customer totals, or approved group attribution.
This module never changes the public planning catalog or renders private HTML.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping

from ai_business_os.retally_group import build_group_view, load_catalog


class GroupObservationError(ValueError):
    """Invalid private observation; messages never include supplied field values."""


_DIGEST = re.compile(r"[0-9a-fA-F]{64}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,99}")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3])(?::[0-5]\d)?)"
)
_COUNTS = ("customer_records", "financial_event_records", "external_outcome_records")
_SNAPSHOT_KEYS = {
    "schema_fingerprint", "observed_at", "businesses",
    "unattributed_external_outcome_records",
}
_BUSINESS_KEYS = {"id", "slug", *_COUNTS}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GroupObservationError(message)


def _exact_keys(value: Any, keys: set[str], message: str) -> None:
    _require(isinstance(value, Mapping) and set(value) == keys, message)


def _count(value: Any) -> int:
    _require(type(value) is int and 0 <= value <= 2**63 - 1,
             "record counts must be nonnegative integers")
    return value


def _time(value: Any) -> datetime:
    if type(value) is str:
        _require(_TIMESTAMP.fullmatch(value) is not None
                 and not value.endswith(("-00", "-00:00")),
                 "observation time must have a valid known offset")
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, OverflowError):
            raise GroupObservationError("observation time must be an aware timestamp") from None
    _require(isinstance(value, datetime) and value.tzinfo is not None
             and value.utcoffset() is not None,
             "observation time must be an aware timestamp")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise GroupObservationError("observation time must be an aware timestamp") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field in private observation")
        result[key] = value
    return result


def normalize_source_snapshot(
    snapshot: Mapping[str, Any], *, expected_schema_fingerprint: str,
) -> dict[str, Any]:
    """Validate the exact minimal SQL result; detach it from mutable input."""
    _require(type(expected_schema_fingerprint) is str
             and _DIGEST.fullmatch(expected_schema_fingerprint) is not None,
             "expected schema fingerprint must be a SHA-256 digest")
    _exact_keys(snapshot, _SNAPSHOT_KEYS, "unexpected or missing source snapshot fields")
    fingerprint = snapshot["schema_fingerprint"]
    _require(type(fingerprint) is str and _DIGEST.fullmatch(fingerprint) is not None,
             "source schema fingerprint must be a SHA-256 digest")
    _require(fingerprint.lower() == expected_schema_fingerprint.lower(),
             "production schema drift in group source snapshot")
    businesses = snapshot["businesses"]
    if type(businesses) is str:
        try:
            businesses = json.loads(businesses, object_pairs_hook=_unique_object)
        except (ValueError, TypeError):
            raise GroupObservationError("business observation must be valid unambiguous JSON") from None
    _require(type(businesses) is list, "business observation must be an array")
    ids: set[str] = set()
    slugs: set[str] = set()
    normalized = []
    for business in businesses:
        _exact_keys(business, _BUSINESS_KEYS, "unexpected or missing business observation fields")
        record_id, slug = business["id"], business["slug"]
        _require(type(record_id) is str and _ID.fullmatch(record_id) is not None,
                 "invalid private business identifier")
        _require(type(slug) is str and _SLUG.fullmatch(slug) is not None,
                 "invalid private business slug")
        _require(record_id not in ids and slug not in slugs,
                 "duplicate private business identity")
        ids.add(record_id)
        slugs.add(slug)
        normalized.append({"id": record_id, "slug": slug,
                           **{key: _count(business[key]) for key in _COUNTS}})
    return {
        "schema_fingerprint": fingerprint.lower(),
        "observed_at": _time(snapshot["observed_at"]).isoformat(),
        "businesses": sorted(normalized, key=lambda row: (row["slug"], row["id"])),
        "unattributed_external_outcome_records": _count(
            snapshot["unattributed_external_outcome_records"]),
    }


def build_private_group_observation(
    snapshot: Mapping[str, Any], *, expected_schema_fingerprint: str,
    catalog: Mapping[str, Any] | None = None,
    now: datetime | None = None, max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Make unresolved source-to-group links visible without approving them.

Freshness means query observation age, not the age or completeness of all
business activity. Unknown/unmapped businesses are counted without disclosure.
"""
    _require(type(max_age_seconds) is int and max_age_seconds > 0,
             "maximum observation age must be a positive integer")
    current = _time(datetime.now(timezone.utc) if now is None else now)
    source = normalize_source_snapshot(
        snapshot, expected_schema_fingerprint=expected_schema_fingerprint)
    observed = _time(source["observed_at"])
    _require(observed <= current, "source observation time is in the future")
    data = load_catalog() if catalog is None else copy.deepcopy(dict(catalog))
    public_view = build_group_view(data)
    candidates = {
        slug: entry["id"] for entry in data["entries"]
        for slug in entry["candidate_production_slugs"]
    }
    by_entry: dict[str, list[dict[str, Any]]] = {}
    unmapped = 0
    for business in source["businesses"]:
        entry_id = candidates.get(business["slug"])
        if entry_id is None:
            unmapped += 1
            continue
        by_entry.setdefault(entry_id, []).append({
            "private_business_id": business["id"],
            "source_slug": business["slug"],
            "observed_record_counts": {key: business[key] for key in _COUNTS},
        })
    entries = []
    for entry in data["entries"]:
        rows = by_entry.get(entry["id"], [])
        status = ("NO_SOURCE_MATCH" if not rows else
                  "REVIEW_REQUIRED" if len(rows) == 1 else "MULTIPLE_SOURCE_RECORDS")
        entries.append({
            "catalog_id": entry["id"], "division_id": entry["division_id"],
            "binding_status": status, "binding_approved": False,
            "candidate_businesses": rows,
        })
    serialized = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    age = (current - observed).total_seconds()
    return {
        "mode": "PRIVATE_READ_ONLY_SOURCE_OBSERVATION",
        "source_schema": "ai_business_os_prod",
        "schema_fingerprint": source["schema_fingerprint"],
        "catalog_sha256": public_view["catalog_sha256"],
        "source_snapshot_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "observed_at": source["observed_at"],
        "evaluated_at": current.isoformat(),
        "freshness": "CURRENT" if age <= max_age_seconds else "STALE",
        "observation_age_seconds": age,
        "coverage": "RECORDS_VISIBLE_TO_PRIVATE_EXECUTOR_ONLY",
        "query_consistency": "SINGLE_STATEMENT_SOURCE_SNAPSHOT",
        "observed_business_records": len(source["businesses"]),
        "matched_catalog_entries": len(by_entry),
        "unmatched_catalog_entries": len(entries) - len(by_entry),
        "unmapped_business_records": unmapped,
        "unattributed_external_outcome_records": source["unattributed_external_outcome_records"],
        "entries": entries,
        "verified_metrics": {
            "qualified_leads": None, "paying_customers": None,
            "cash_collected": None, "contribution_profit": None,
        },
        "authority": {
            "identity_mutation_authorized": False,
            "external_actions_authorized": False,
            "production_state_mutation_authorized": False,
            "financial_verification_performed": False,
        },
    }
