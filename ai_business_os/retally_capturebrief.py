"""CaptureBrief: private, read-only inspection of an *existing immutable* outcome ledger.

CaptureBrief's append/verify helpers acquire filesystem locks. This consumer
never imports those helpers, opens a source path, or writes any file. The caller
must provide an authenticated immutable *present* byte snapshot; omission and
failure are not an empty ledger. This module neither discovers a live source nor
binds source cases to customer identities or verifies payments.

Pinned producer: P00NSMASHER/capturebrief @
12d90024f053a78ead7936abf092931fce240d3e,
capturebrief_core/{model,ledger,outcomes}.py.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import threading
from typing import Any


class CaptureBriefObservationError(ValueError):
    """Redacted error; never contains submitted source content or identifiers."""


_ERROR = "CaptureBrief immutable outcome snapshot could not be validated"
_CONFIG_ERROR = "CaptureBrief snapshot reader configuration is invalid"
_LEDGER_VERSION = "capturebrief-evidence-ledger-v1"
_OUTCOME_RECORD = "CAPTUREBRIEF_OUTCOME_EVENT"
_MAX_BYTES = 16 * 1024 * 1024
_MAX_LINES = 100_000
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/#-]{2,199}\Z")
_CLASS = re.compile(r"[A-Z][A-Z0-9_]{1,63}\Z")
_SNAPSHOT_FIELDS = {"present", "content", "snapshot_sha256", "observed_at"}
_RECORD_FIELDS = {"ledger_version", "record_type", "recorded_at", "previous_record_sha256", "payload_sha256", "payload", "record_sha256"}
_EVENT_REQUIRED = {"schema_version", "case_id", "case_sha256", "event_type", "event_at", "data"}
_EVENT_OPTIONAL = {"delivery_bundle_sha256"}
_EVENT_TYPES = ("PAYMENT", "DELIVERY", "FEEDBACK", "RETRACTION", "REPEAT_REQUEST", "EFFORT")
_PAYMENT = {"PAID", "UNPAID", "REFUNDED", "UNKNOWN"}
_USEFUL = {"USEFUL", "NOT_USEFUL", "UNKNOWN"}
_EFFECT = {"CHANGED_ACTION", "CLOSED_COSTLY_UNCERTAINTY", "CONFIRMED_EXISTING_VIEW", "ALREADY_KNEW", "FALSE_POSITIVE", "NO_DECISION", "UNKNOWN"}
_REPEAT = {"REQUESTED_REPEAT", "WOULD_REPEAT", "NO_REPEAT", "UNKNOWN"}
_RETRACT = {"CRITICAL", "NONCRITICAL"}
_REASONS = {"WRONG_SOURCE", "WRONG_VERSION", "WRONG_RULE_EDITION", "BAD_APPLICABILITY", "BAD_IDENTITY", "MISREAD_PASSAGE", "MISSING_CONTROLLING_EVIDENCE", "OTHER"}
_EFFORT = {"INTAKE_SCOPE", "HISTORY_CURRENT", "PACKET_BYTES", "REFERENCE_REVIEW", "ASSUMPTION_REVIEW", "RULE_REVIEW", "DEVIATION_REVIEW", "WATCH", "DELIVERY", "CUSTOMER_COMMS", "OTHER"}
_FORBIDDEN = {"email", "company", "company_name", "buyer", "buyer_name", "customer", "customer_name", "contact", "contact_name", "phone", "address", "notes", "free_text", "roi", "pwin", "proposal_savings", "revenue_uplift"}
_GENESIS = "0" * 64


def _require(predicate: bool) -> None:
    if not predicate:
        raise CaptureBriefObservationError(_ERROR)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        _require(k not in obj)
        obj[k] = v
    return obj


def _invalid_constant(_value: str) -> None:
    _require(False)


def _canonical(value: Any) -> bytes:
    # Exactly CaptureBrief's model.canonical_json, but without importing its
    # filesystem-writing ledger/verifier.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _time(value: Any, now: datetime) -> datetime:
    _require(type(value) is str and _TIME.fullmatch(value) is not None and not value.endswith("-00:00"))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise CaptureBriefObservationError(_ERROR) from None
    _require(parsed <= now)
    return parsed


def _now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None)
    return value.astimezone(timezone.utc)


def _ref(value: Any) -> bool:
    return type(value) is str and _REF.fullmatch(value) is not None


def _clean_fields(value: Any, required: set[str], optional: set[str] | None = None) -> None:
    _require(type(value) is dict and required <= set(value) and set(value) <= required | (optional or set()))


def _event(event: Any, observed: datetime) -> tuple[str, str, str | None, datetime, datetime | None]:
    """Mirror the producer's controlled outcome types; retain no case/evidence refs."""
    _clean_fields(event, _EVENT_REQUIRED, _EVENT_OPTIONAL)
    _require(event["schema_version"] == "1.0")
    case = event["case_id"]
    _require(type(case) is str and 0 < len(case.strip()) <= 256)
    _require(_digest(event["case_sha256"]))
    kind = event["event_type"]
    _require(type(kind) is str and kind in _EVENT_TYPES)
    at = _time(event["event_at"], observed)
    bundle = event.get("delivery_bundle_sha256")
    _require(bundle is None or _digest(bundle))
    if kind in {"DELIVERY", "FEEDBACK", "RETRACTION", "REPEAT_REQUEST"}:
        _require(_digest(bundle))
    data = event["data"]
    _require(type(data) is dict and not any(str(k).lower() in _FORBIDDEN for k in data))
    delivered_at = None
    if kind == "PAYMENT":
        _clean_fields(data, {"state"}, {"amount_cents", "currency", "payment_evidence_ref"})
        _require(data["state"] in _PAYMENT)
        if data["state"] in {"PAID", "REFUNDED"}:
            _require(_ref(data.get("payment_evidence_ref")))
        amount = data.get("amount_cents")
        _require(amount is None or type(amount) is int and amount >= 0)
        if amount is not None:
            _require(type(data.get("currency")) is str and re.fullmatch(r"[A-Z]{3}", data["currency"]) is not None)
    elif kind == "DELIVERY":
        _clean_fields(data, {"started_at", "delivered_at", "delivery_evidence_ref"})
        start = _time(data["started_at"], observed)
        delivered_at = _time(data["delivered_at"], observed)
        _require(start <= delivered_at and _ref(data["delivery_evidence_ref"]))
    elif kind == "FEEDBACK":
        _clean_fields(data, {"usefulness", "action_effect", "source_limited", "finding_classes", "feedback_evidence_ref"})
        _require(data["usefulness"] in _USEFUL and data["action_effect"] in _EFFECT)
        _require(type(data["source_limited"]) is bool and _ref(data["feedback_evidence_ref"]))
        classes = data["finding_classes"]
        _require(type(classes) is list and len(classes) == len(set(map(str, classes)))
                 and all(type(c) is str and _CLASS.fullmatch(c) is not None for c in classes))
    elif kind == "RETRACTION":
        _clean_fields(data, {"severity", "reason_code", "retraction_evidence_ref"})
        _require(data["severity"] in _RETRACT and data["reason_code"] in _REASONS
                 and _ref(data["retraction_evidence_ref"]))
    elif kind == "REPEAT_REQUEST":
        _clean_fields(data, {"state", "repeat_evidence_ref"})
        _require(data["state"] in _REPEAT)
        if data["state"] != "UNKNOWN":
            _require(_ref(data["repeat_evidence_ref"]))
        elif data["repeat_evidence_ref"] is not None:
            _require(_ref(data["repeat_evidence_ref"]))
    elif kind == "EFFORT":
        _clean_fields(data, {"stage", "minutes", "effort_evidence_ref"})
        _require(data["stage"] in _EFFORT and type(data["minutes"]) is int
                 and 1 <= data["minutes"] <= 1440 and _ref(data["effort_evidence_ref"]))
    return kind, case, bundle, at, delivered_at


def _verified_records(raw: bytes, observed: datetime) -> tuple[list[str], Counter[str], int, int, int]:
    """Verify every hash-linked record, then summarize safe event dimensions."""
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise CaptureBriefObservationError(_ERROR) from None
    if text:
        _require(text.endswith("\n"))  # Append-only producer writes complete lines.
        lines = text.splitlines()
    else:
        lines = []
    _require(len(lines) <= _MAX_LINES and all(line for line in lines))
    previous = _GENESIS
    hashes: list[str] = []
    kinds: Counter[str] = Counter()
    cases: dict[str, str] = {}
    delivery_by_case: dict[str, dict[str, datetime]] = {}
    postdelivery: list[tuple[str, str | None, datetime]] = []
    outcome_events = 0
    for line in lines:
        try:
            record = json.loads(line, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
            _clean_fields(record, _RECORD_FIELDS)
            _require(record["ledger_version"] == _LEDGER_VERSION)
            _require(type(record["record_type"]) is str and bool(record["record_type"]))
            _time(record["recorded_at"], observed)
            _require(_digest(record["previous_record_sha256"]) and record["previous_record_sha256"] == previous)
            _require(_digest(record["payload_sha256"]) and hmac.compare_digest(record["payload_sha256"], _sha(_canonical(record["payload"]))))
            _require(_digest(record["record_sha256"]))
            expected = _sha(_canonical({k: v for k, v in record.items() if k != "record_sha256"}))
            _require(hmac.compare_digest(record["record_sha256"], expected))
            previous = record["record_sha256"]
            hashes.append(previous)
            if record["record_type"] == _OUTCOME_RECORD:
                kind, case, bundle, event_at, delivered_at = _event(record["payload"], observed)
                fingerprint = record["payload"]["case_sha256"]
                _require(case not in cases or cases[case] == fingerprint)
                cases[case] = fingerprint
                kinds[kind] += 1
                outcome_events += 1
                if kind == "DELIVERY":
                    deliveries = delivery_by_case.setdefault(case, {})
                    if bundle not in deliveries or delivered_at > deliveries[bundle]:
                        deliveries[bundle] = delivered_at
                elif kind in {"FEEDBACK", "RETRACTION", "REPEAT_REQUEST"}:
                    postdelivery.append((case, bundle, event_at))
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
            raise CaptureBriefObservationError(_ERROR) from None
    unbound = sum(
        1 for case, bundle, at in postdelivery
        if bundle not in delivery_by_case.get(case, {})
        or at < delivery_by_case[case][bundle]
    )
    return hashes, kinds, outcome_events, len(cases), unbound


class CaptureBriefOutcomeReader:
    """Read a private producer-compatible snapshot without accessing live paths.

    read_snapshot() must supply {present: True, content: bytes,
    snapshot_sha256: sha256(content), observed_at: timezone-aware RFC3339}.
    It must itself authorize the read and provide a stable immutable snapshot.
    A hash match does *not* establish provider authentication or source freshness.
    Continuity lives only for the lifetime of this reader instance.
    """

    def __init__(self, read_snapshot: Callable[[], Mapping[str, Any]], *, max_age_seconds: int = 86400):
        if not callable(read_snapshot) or type(max_age_seconds) is not int or max_age_seconds <= 0:
            raise CaptureBriefObservationError(_CONFIG_ERROR)
        self._read_snapshot = read_snapshot
        self._max_age_seconds = max_age_seconds
        self._previous: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def observe(self, *, now: datetime | None = None) -> dict[str, Any]:
        with self._lock:
            try:
                current = _now(now)
                snapshot = self._read_snapshot()
                _require(isinstance(snapshot, Mapping) and set(snapshot) == _SNAPSHOT_FIELDS)
                _require(snapshot["present"] is True)
                raw = snapshot["content"]
                _require(type(raw) is bytes and len(raw) <= _MAX_BYTES)
                digest = snapshot["snapshot_sha256"]
                _require(_digest(digest) and hmac.compare_digest(_sha(raw), digest))
                observed = _time(snapshot["observed_at"], current)
                hashes, kinds, count, cases, unbound = _verified_records(raw, observed)
                previous = self._previous
                if previous is not None:
                    _require(previous["observed_at"] <= observed)
                    _require(len(hashes) >= previous["record_count"])
                    if previous["record_count"]:
                        _require(hashes[previous["record_count"]-1] == previous["head"])
                    if len(hashes) == previous["record_count"]:
                        _require(digest == previous["digest"])
                self._previous = {
                    "observed_at": observed, "record_count": len(hashes),
                    "head": hashes[-1] if hashes else _GENESIS, "digest": digest,
                }
                age = (current - observed).total_seconds()
                return {
                    "mode": "PRIVATE_READ_ONLY_SNAPSHOT_OBSERVATION",
                    "service": "capturebrief",
                    "snapshot_presence": "PRESENT_EMPTY" if not hashes else "PRESENT",
                    "observed_at": observed.isoformat(),
                    "source_age_seconds": age,
                    "freshness": "CURRENT" if age <= self._max_age_seconds else "STALE",
                    "snapshot_sha256": digest,
                    "ledger_record_count": len(hashes),
                    "ledger_head_sha256": hashes[-1] if hashes else _GENESIS,
                    "outcome_event_count": count,
                    "distinct_case_count_not_customer_count": cases,
                    "event_counts": {kind: kinds[kind] for kind in _EVENT_TYPES},
                    "unbound_postdelivery_event_count": unbound,
                    "verified_metrics": {
                        "paying_customers": None, "cash_collected": None,
                        "qualified_leads": None, "contribution_profit": None,
                    },
                    "source_authenticity": "UNVERIFIED_BY_READER",
                    "payment_settlement": "NOT_INDEPENDENTLY_VERIFIED",
                    "account_identity_binding": "NOT_CONNECTED",
                    "authority": {
                        "identity_mutation_authorized": False,
                        "external_actions_authorized": False,
                        "production_state_mutation_authorized": False,
                    },
                }
            except Exception:
                # Provider callbacks may include secrets/PII in exception text.
                raise CaptureBriefObservationError(_ERROR) from None
