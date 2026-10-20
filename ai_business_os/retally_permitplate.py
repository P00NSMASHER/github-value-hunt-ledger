"""Read an immutable PermitPlate NYC snapshot and emit aggregate observations.

The two injected functions provide a revision and file bytes; this module has
no repository, credential, environment, payment-provider or write capability.
Git blob digests and producer seals check consistency, not the caller's or
writer's authenticity. The nine-hour default is a local observation policy,
not a PermitPlate NYC service promise or an independently verified payment SLA.

Contract source: P00NSMASHER/permitplate-nyc at
7be09a82249ab1ef6b6a9de7402690dbefd47f5e, pipeline/curated-stripe-onboarding.js
and pipeline/subscriber-profile.js. Unsupported producer shapes fail closed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
import re
import threading
from typing import Any

from ai_business_os.retally_customer_register import build_register_observation


class PermitPlateError(ValueError):
    """A fixed, non-identifying reader configuration or observation error."""


SOURCE_CONTRACT_COMMIT = "7be09a82249ab1ef6b6a9de7402690dbefd47f5e"
LEDGER_PATH = "state/curated-onboarding-ledger.json"
ANCHOR_PATH = "state/curated-onboarding-anchor.json"
_VERSION = "PermitPlate-private-checkout-intake-v1.0.0"
_ANCHOR_VERSION = "PermitPlate-private-checkout-anchor-v1.0.0"
_ERROR = "PermitPlate NYC observation failed closed"
_CONFIG_ERROR = "PermitPlate NYC reader configuration is invalid"
_MAX_SOURCE_BYTES = 16 * 1024 * 1024
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z"
)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+\Z")
_STATES = ("PENDING_FOUNDER_REVIEW", "HOLD_SUBSCRIPTION_CHANGED")
_CATEGORIES = {"POS", "Insurance", "Equipment", "Hood/Fire", "Waste", "Pest", "Linen", "Distribution"}
_BOROUGHS = ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island")
_CALENDAR = "America/New_York weekdays only; holiday adjustment requires review"
_FILE_FIELDS = {"commit_sha", "blob_sha", "content"}
_LEDGER_FIELDS = {"version", "initializedAt", "checkedAt", "subscriptions", "ledgerFingerprint"}
_ANCHOR_FIELDS = {"version", "initializedAt", "baselineLedgerFingerprint", "anchorFingerprint"}
_SUBSCRIPTION_FIELDS = {
    "subscriptionId", "checkoutSessionId", "recipientEmail", "category", "boroughs",
    "starterSnapshotEnabled", "stripeCustomerId", "profileFingerprint", "baselineAt",
    "firstBriefTargetDate", "targetDateCalendar", "state", "transportAllowed",
    "ownerAuthorizationGranted", "firstDiscoveredAt",
}
_EVIDENCE_FIELDS = (
    "agreement_ref", "customer_authorization_ref", "release_approval_ref",
    "input_manifest_ref", "quality_review_ref", "delivery_receipt_ref",
    "financial_reconciliation_ref", "retention_policy_ref",
)
_HMAC_DOMAIN = b"retally\x00permitplate-nyc\x00curated-onboarding-v1\x00"


def _require(condition: bool) -> None:
    if not condition:
        raise PermitPlateError(_ERROR)


def _fields(value: Any, expected: set[str]) -> None:
    _require(type(value) is dict and set(value) == expected)


def _digest(value: Any, pattern: re.Pattern[str]) -> bool:
    return type(value) is str and pattern.fullmatch(value) is not None


def _id(value: Any, prefix: str) -> bool:
    return type(value) is str and re.fullmatch(prefix + r"_[A-Za-z0-9_]{6,170}", value) is not None


def _timestamp(value: Any, observed_at: datetime) -> datetime:
    _require(type(value) is str and _TIMESTAMP.fullmatch(value) is not None)
    _require(not value.endswith("-00:00"))
    parsed = datetime.fromisoformat(value.upper().replace("Z", "+00:00")).astimezone(timezone.utc)
    _require(parsed <= observed_at)
    return parsed


def _observation_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _invalid_number(value: str) -> None:
    # This producer format has no numeric fields, including inside entries.
    raise PermitPlateError(_ERROR)


def _producer_json(value: Any) -> str:
    """Match the producer's stable()/JSON.stringify for its nonnumeric format.

    JavaScript sorts keys by UTF-16 code units, not Unicode code points. Valid
    Unicode strings are emitted directly; JSON control escapes match Python's
    compact encoder. Lone surrogates are deliberately rejected by UTF-8 encoding.
    Numeric values have no place in this contract, avoiding cross-runtime number
    rounding/serialization ambiguities entirely.
    """
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        return "{" + ",".join(_producer_json(key) + ":" + _producer_json(value[key]) for key in keys) + "}"
    if type(value) is list:
        return "[" + ",".join(_producer_json(item) for item in value) + "]"
    _require(value is None or type(value) in (str, bool))
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    encoded.encode("utf-8")
    return encoded


def _seal(value: dict[str, Any]) -> str:
    return hashlib.sha256(_producer_json(value).encode("utf-8")).hexdigest()


def _validate_snapshot(ledger: Any, anchor: Any, now: datetime) -> tuple[datetime, dict[str, datetime]]:
    _fields(ledger, _LEDGER_FIELDS)
    _fields(anchor, _ANCHOR_FIELDS)
    _require(ledger["version"] == _VERSION and anchor["version"] == _ANCHOR_VERSION)
    initialized = _timestamp(ledger["initializedAt"], now)
    checked = _timestamp(ledger["checkedAt"], now)
    _require(initialized <= checked)
    _require(anchor["initializedAt"] == ledger["initializedAt"])
    for data, field in ((ledger, "ledgerFingerprint"), (anchor, "anchorFingerprint")):
        _require(_digest(data[field], _SHA256))
        _require(hmac.compare_digest(data[field], _seal({key: value for key, value in data.items() if key != field})))
    baseline = {
        "version": _VERSION, "initializedAt": ledger["initializedAt"],
        "checkedAt": ledger["initializedAt"], "subscriptions": {},
    }
    _require(_digest(anchor["baselineLedgerFingerprint"], _SHA256))
    _require(hmac.compare_digest(anchor["baselineLedgerFingerprint"], _seal(baseline)))
    subscriptions = ledger["subscriptions"]
    _require(type(subscriptions) is dict)
    sessions: set[str] = set()
    profiles: set[str] = set()
    discovered: dict[str, datetime] = {}
    for subscription_id, row in subscriptions.items():
        _fields(row, _SUBSCRIPTION_FIELDS)
        _require(_id(subscription_id, "sub") and row["subscriptionId"] == subscription_id)
        _require(_id(row["checkoutSessionId"], "cs"))
        _require(row["checkoutSessionId"] not in sessions)
        sessions.add(row["checkoutSessionId"])
        _require(row["stripeCustomerId"] is None or _id(row["stripeCustomerId"], "cus"))
        _require(_digest(row["profileFingerprint"], _SHA256) and row["profileFingerprint"] not in profiles)
        profiles.add(row["profileFingerprint"])
        email = row["recipientEmail"]
        _require(type(email) is str and 3 <= len(email) <= 254 and email == email.strip())
        _require(_EMAIL.fullmatch(email) is not None and all(ord(char) >= 32 and ord(char) != 127 for char in email))
        _require(type(row["category"]) is str and row["category"] in _CATEGORIES)
        boroughs = row["boroughs"]
        _require(type(boroughs) is list and 1 <= len(boroughs) <= len(_BOROUGHS))
        _require(all(type(item) is str and item in _BOROUGHS for item in boroughs))
        _require(boroughs == [borough for borough in _BOROUGHS if borough in boroughs])
        _require(type(row["starterSnapshotEnabled"]) is bool)
        _require(type(row["state"]) is str and row["state"] in _STATES)
        _require(row["transportAllowed"] is False and row["ownerAuthorizationGranted"] is False)
        baseline_at = _timestamp(row["baselineAt"], now)
        discovered_at = _timestamp(row["firstDiscoveredAt"], now)
        _require(baseline_at <= discovered_at and initialized <= discovered_at <= checked)
        target = row["firstBriefTargetDate"]
        _require(type(target) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", target) is not None)
        date.fromisoformat(target)  # A target can legitimately be in the future.
        _require(row["targetDateCalendar"] == _CALENDAR)
        discovered[subscription_id] = discovered_at
    return checked, discovered


class PermitPlateNYCReader:
    """Observe the exact NYC ledger/anchor pair through caller-supplied reads.

    ``read_file(commit_sha, path)`` must return exactly ``commit_sha``,
    ``blob_sha`` and UTF-8 ``content``. One immutable revision is resolved per
    observation. Returned metadata cannot independently prove reader identity
    or repository membership. All supplier errors are replaced by fixed errors.

    Successful calls retain only HMAC continuity tokens and source revision
    metadata in process memory. Later calls refuse clock rollback, removed
    subscriptions or immutable subscriber changes. Source state transitions,
    including a hold returning to pending review, remain observable. Continuity
    checks compare the immediately previous successful observation; they do not
    retain an unbounded revision history. Continuity across different reader
    instances requires a separately trusted checkpoint.
    """

    def __init__(
        self,
        resolve_revision: Callable[[], str],
        read_file: Callable[[str, str], Mapping[str, str]],
        *,
        pseudonym_key: bytes,
        max_age_seconds: int = 32400,
    ) -> None:
        if (not callable(resolve_revision) or not callable(read_file)
                or type(pseudonym_key) is not bytes or len(pseudonym_key) < 32
                or type(max_age_seconds) is not int or max_age_seconds <= 0):
            raise PermitPlateError(_CONFIG_ERROR)
        self._resolve_revision = resolve_revision
        self._read_file = read_file
        self._key = pseudonym_key
        self._max_age_seconds = max_age_seconds
        self._previous: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def _token(self, kind: str, identity: str) -> str:
        return hmac.new(self._key, _HMAC_DOMAIN + kind.encode("ascii") + b"\x00" + identity.encode("utf-8"), hashlib.sha256).hexdigest()

    def _read(self, revision: str, path: str) -> tuple[dict[str, Any], str]:
        result = self._read_file(revision, path)
        _require(isinstance(result, Mapping))
        result = dict(result)
        _fields(result, _FILE_FIELDS)
        _require(type(result["commit_sha"]) is str and result["commit_sha"] == revision)
        _require(_digest(result["blob_sha"], _SHA1) and type(result["content"]) is str)
        content = result["content"].encode("utf-8")
        _require(len(content) <= _MAX_SOURCE_BYTES)
        blob = hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\x00" + content).hexdigest()
        _require(hmac.compare_digest(blob, result["blob_sha"]))
        parsed = json.loads(
            result["content"], object_pairs_hook=_pairs, parse_constant=_invalid_number,
            parse_int=_invalid_number, parse_float=_invalid_number,
        )
        return parsed, blob

    def _continuity(
        self, ledger: dict[str, Any], checked: datetime, observed_at: datetime,
        revision: str, ledger_blob: str, anchor_blob: str,
    ) -> dict[str, Any]:
        identities = {
            self._token("engagement:subscription", key): self._token(
                "continuity:immutable-subscription",
                _producer_json({field: value for field, value in row.items() if field != "state"}),
            )
            for key, row in ledger["subscriptions"].items()
        }
        previous = self._previous
        if previous is not None:
            _require(previous["initialized_at"] == ledger["initializedAt"])
            _require(previous["checked_at"] <= checked)
            _require(previous["observed_at"] <= observed_at)
            if previous["revision"] == revision:
                _require(previous["ledger_blob"] == ledger_blob and previous["anchor_blob"] == anchor_blob)
            if previous["checked_at"] == checked:
                _require(previous["ledger_fingerprint"] == ledger["ledgerFingerprint"])
            _require(all(identities.get(key) == value for key, value in previous["identities"].items()))
        return {
            "initialized_at": ledger["initializedAt"], "checked_at": checked,
            "ledger_fingerprint": ledger["ledgerFingerprint"], "identities": identities,
            "observed_at": observed_at, "revision": revision,
            "ledger_blob": ledger_blob, "anchor_blob": anchor_blob,
        }

    def _register(
        self, ledger: dict[str, Any], checked: datetime, discovered: dict[str, datetime],
    ) -> tuple[dict[str, Any], int, int]:
        accounts: dict[str, dict[str, Any]] = {}
        account_times: dict[str, datetime] = {}
        customer_refs: set[str] = set()
        surrogate_refs: set[str] = set()
        engagements = []
        for subscription_id, row in sorted(ledger["subscriptions"].items()):
            if row["stripeCustomerId"] is None:
                identity = self._token("account:subscription-surrogate", subscription_id)
                surrogate_refs.add(identity)
            else:
                identity = self._token("account:stripe-customer", row["stripeCustomerId"])
                customer_refs.add(identity)
            account_ref = "account:nyc_" + identity
            created = discovered[subscription_id]
            if account_ref not in accounts or created < account_times[account_ref]:
                accounts[account_ref] = {"account_ref": account_ref, "private_contact_ref": None, "created_at": _iso(created)}
                account_times[account_ref] = created
            engagements.append({
                "engagement_ref": "engagement:nyc_" + self._token("engagement:subscription", subscription_id),
                "account_ref": account_ref, "catalog_entry_id": "permitplate",
                "service_ref": "private:permitplate:nyc_curated", "owner_role": "CHIEF_OF_STAFF",
                "stage": "inquiry", "payment_status": "UNKNOWN", "currency": None,
                "updated_at": _iso(checked), **{field: None for field in _EVIDENCE_FIELDS},
            })
        register = {
            "schema_version": 1,
            "storage_authority": "ai_business_os_prod_and_approved_private_service_stores",
            "accounts": [accounts[key] for key in sorted(accounts)],
            "engagements": engagements, "referrals": [],
        }
        return register, len(customer_refs), len(surrogate_refs)

    def observe(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Return allowlisted aggregates only; never return the transient register.

        ``read_observed_at`` timestamps this read, while ``source_checked_at``
        and ``source_age_seconds`` describe the retained provider observation.
        Reading old bytes now does not make their source observation current.
        Every engagement remains an inquiry with unknown current payment state.
        """
        try:
            with self._lock:
                revision = self._resolve_revision()
                _require(_digest(revision, _SHA1))
                ledger, ledger_blob = self._read(revision, LEDGER_PATH)
                anchor, anchor_blob = self._read(revision, ANCHOR_PATH)
                observed_at = _observation_time(now)
                checked, discovered = _validate_snapshot(ledger, anchor, observed_at)
                continuity = self._continuity(ledger, checked, observed_at, revision, ledger_blob, anchor_blob)
                register, customers, surrogates = self._register(ledger, checked, discovered)
                register_observation = build_register_observation(register, observed_at=observed_at)
                age = (observed_at - checked).total_seconds()
                state_counts = {state: 0 for state in _STATES}
                for row in ledger["subscriptions"].values():
                    state_counts[row["state"]] += 1
                source_observation = {
                    "mode": "READ_ONLY_PERMITPLATE_NYC_OBSERVATION",
                    "source_contract_commit": SOURCE_CONTRACT_COMMIT,
                    "source_version": _VERSION,
                    "source_revision": revision,
                    "ledger_blob_sha": ledger_blob,
                    "anchor_blob_sha": anchor_blob,
                    "ledger_fingerprint": ledger["ledgerFingerprint"],
                    "source_authentication": "CALLER_SUPPLIED_READERS_NOT_INDEPENDENTLY_AUTHENTICATED",
                    "immutable_revision_consistent": True,
                    "integrity": "CHECKED",
                    "continuity": "PREVIOUS_SUCCESSFUL_OBSERVATION_CHECKED" if self._previous is not None else "INITIAL_OBSERVATION",
                    "source_checked_at": _iso(checked),
                    "read_observed_at": _iso(observed_at),
                    "source_age_seconds": age,
                    "freshness": "CURRENT" if age <= self._max_age_seconds else "STALE",
                    "freshness_policy": "LOCAL_OBSERVATION_POLICY_NOT_SOURCE_SLA",
                    "max_source_age_seconds": self._max_age_seconds,
                    "source_state_counts": state_counts,
                    "held_subscriptions": state_counts["HOLD_SUBSCRIPTION_CHANGED"],
                    "account_identity_scope": "SOURCE_SERVICE_ONLY_NO_CROSS_BUSINESS_MERGE",
                    "source_customer_accounts": customers,
                    "subscription_surrogate_accounts": surrogates,
                    "live_payment_verification": "NOT_PERFORMED",
                    "evidence_verification": "NOT_PERFORMED",
                    "external_actions_authorized": False,
                    "production_state_mutation_authorized": False,
                }
                self._previous = continuity
                return {"register_observation": register_observation, "source_observation": source_observation}
        except Exception:
            # Supplier errors may contain tokens, private URLs or whole records.
            # No supplier/error text, exception chaining or record data escapes.
            raise PermitPlateError(_ERROR) from None
