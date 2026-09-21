"""Bounded, all-or-nothing assembly of untrusted offline review exports.

This module only validates/combines draft proposals. It never authenticates a
reviewer, confirms a finding, persists review history, or authorizes an action.
The caller must pass the current trusted packet/routing/truth identifiers and
submit the result to the existing buyer-review workflow.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

MAX_FILE_BYTES = 1_048_576
MAX_FILE_DECISIONS = 2_000
MAX_EXPORT_FILES = 32
MAX_PACKAGE_BYTES = 16_777_216
MAX_COMBINED_DECISIONS = 20_000
MAX_REVIEW_MINUTES = 2**53 - 1
HASH = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)
CONTEXT_KEYS = ("review_packet_hash", "review_routing_hash", "truth_hash")
ROOT_KEYS = frozenset(("schema_version", "decisions", *CONTEXT_KEYS))
ROW_KEYS = frozenset(("case_hash", "disposition", "reviewer_minutes", "reviewed_at"))
DISPOSITIONS = frozenset(("CONFIRMED", "FALSE_POSITIVE", "UNRESOLVED"))


@dataclass(frozen=True)
class DraftDecision:
    case_hash: str
    disposition: str
    reviewer_minutes: int
    reviewed_at: str


@dataclass(frozen=True)
class CombinedDecisionExports:
    decisions: tuple[DraftDecision, ...]
    source_file_hashes: tuple[str, ...]
    source_file_count: int
    duplicate_file_count: int
    duplicate_decision_count: int


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON property")
        value[key] = item
    return value


def _constant(_value):
    raise ValueError("non-finite JSON numbers are not accepted")


def canonical_review_time(value: object) -> str:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError("reviewed_at must be a timezone-aware ISO timestamp")
    if value.endswith("-00:00"):
        raise ValueError("reviewed_at must use a known UTC offset")
    if not value.endswith("Z"):
        hours, minutes = int(value[-5:-3]), int(value[-2:])
        if hours > 23 or minutes > 59:
            raise ValueError("reviewed_at has an invalid UTC offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("reviewed_at must be a valid timezone-aware timestamp") from exc
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")


def merge_decision_exports(
    files: Iterable[bytes], *, review_packet_hash: str,
    review_routing_hash: str, truth_hash: str,
) -> CombinedDecisionExports:
    """Validate every file before returning any assembled draft decisions.

    Exact repeated files/decisions are idempotent. Different decisions for the
    same case fail the complete handoff, including changed effort or timestamps.
    Equivalent timezone offsets normalize to the same instant for comparison.
    Identical rows within one file remain an error, matching the single importer.
    Limits count all supplied bytes/files, including repeated files.
    """
    expected = dict(zip(CONTEXT_KEYS, (review_packet_hash, review_routing_hash, truth_hash)))
    if any(not isinstance(v, str) or not HASH.fullmatch(v) for v in expected.values()):
        raise ValueError("trusted review context must contain SHA-256 identifiers")
    if isinstance(files, (bytes, bytearray, str)):
        raise ValueError("files must be an iterable of export byte strings")
    decisions: dict[str, DraftDecision] = {}
    source_hashes: set[str] = set()
    total_bytes = file_count = duplicate_files = duplicate_decisions = 0
    for file_count, raw in enumerate(files, 1):
        if file_count > MAX_EXPORT_FILES:
            raise ValueError("too many export files")
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_FILE_BYTES:
            raise ValueError("export data must be nonempty bytes within the size limit")
        total_bytes += len(raw)
        if total_bytes > MAX_PACKAGE_BYTES:
            raise ValueError("combined export byte limit exceeded")
        digest = hashlib.sha256(raw).hexdigest()
        if digest in source_hashes:
            duplicate_files += 1
            continue
        try:
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                               parse_constant=_constant)
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("invalid export JSON") from exc
        if not isinstance(value, dict) or set(value) != ROOT_KEYS:
            raise ValueError("decision envelope schema mismatch")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("unsupported decision schema_version")
        if any(value[key] != expected[key] for key in CONTEXT_KEYS):
            raise ValueError("stale or different audit context in export")
        rows = value["decisions"]
        if not isinstance(rows, list) or len(rows) > MAX_FILE_DECISIONS:
            raise ValueError("export decisions exceed the per-file row limit")
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != ROW_KEYS:
                raise ValueError("decision row schema mismatch")
            case_hash = row["case_hash"]
            if not isinstance(case_hash, str) or not HASH.fullmatch(case_hash):
                raise ValueError("case_hash must be lowercase SHA-256")
            if case_hash in seen:
                raise ValueError("duplicate decision within one export")
            seen.add(case_hash)
            disposition = row["disposition"]
            if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
                raise ValueError("unsupported decision disposition")
            minutes = row["reviewer_minutes"]
            if type(minutes) is not int or not 0 <= minutes <= MAX_REVIEW_MINUTES:
                raise ValueError("reviewer_minutes must be a non-negative safe integer")
            decision = DraftDecision(case_hash, disposition, minutes,
                                     canonical_review_time(row["reviewed_at"]))
            existing = decisions.get(case_hash)
            if existing is not None:
                if existing != decision:
                    raise ValueError("conflicting decisions across exports; resolve explicitly")
                duplicate_decisions += 1
            else:
                if len(decisions) >= MAX_COMBINED_DECISIONS:
                    raise ValueError("combined decision limit exceeded")
                decisions[case_hash] = decision
        source_hashes.add(digest)
    if not file_count:
        raise ValueError("at least one export file is required")
    return CombinedDecisionExports(
        decisions=tuple(decisions[key] for key in sorted(decisions)),
        source_file_hashes=tuple(sorted(source_hashes)), source_file_count=file_count,
        duplicate_file_count=duplicate_files, duplicate_decision_count=duplicate_decisions,
    )
