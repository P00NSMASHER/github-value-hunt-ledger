"""Validate a private register snapshot without granting operating authority.

This module parses supplied data only. It does not create a customer store,
authenticate evidence references, execute workflow transitions, or establish
payment truth. Its observation deliberately excludes private identifiers and
free text. Snapshot freshness cannot be established by the current schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Mapping

from ai_business_os.retally_group import WORKFLOW_IDS, load_catalog, validate_catalog


class CustomerRegisterError(ValueError):
    """The supplied register violates its shape or relationship contract."""


_AUTHORITY = "ai_business_os_prod_and_approved_private_service_stores"
_REF = re.compile(r"[a-z]+:[A-Za-z0-9_-]{1,80}\Z")
_PRIVATE_REF = re.compile(r"private:[A-Za-z0-9:_-]{1,160}\Z")
_CURRENCY = re.compile(r"[A-Z]{3}\Z")
_SCHEMA_ENTRY_IDS = {
    "retally-recovery", "capturebrief", "permitplate", "rehabsignal", "sheetharbor",
    "app-factory-products", "x402-services", "scopesignal", "contractor-quote-recovery",
    "resonance", "market-surveillance",
}
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z"
)
_PAYMENTS = ("NOT_DUE", "PENDING", "PARTIAL", "PAID", "REFUNDED", "DISPUTED", "UNKNOWN")
_REFERRAL_STATUSES = (
    "PROPOSED", "PERMISSION_PENDING", "AUTHORIZED_INTERNAL_HANDOFF", "DECLINED", "CLOSED",
)
_EVIDENCE_FIELDS = (
    "agreement_ref", "customer_authorization_ref", "release_approval_ref",
    "input_manifest_ref", "quality_review_ref", "delivery_receipt_ref",
    "financial_reconciliation_ref", "retention_policy_ref",
)
_ROOT_FIELDS = {"schema_version", "storage_authority", "accounts", "engagements", "referrals"}
_ACCOUNT_FIELDS = {"account_ref", "private_contact_ref", "created_at"}
_ENGAGEMENT_FIELDS = {
    "engagement_ref", "account_ref", "catalog_entry_id", "service_ref", "owner_role",
    "stage", "payment_status", "currency", "updated_at", *_EVIDENCE_FIELDS,
}
_REFERRAL_FIELDS = {
    "referral_ref", "account_ref", "source_engagement_ref", "target_catalog_entry_id",
    "customer_permission_ref", "owner_action_approval_ref", "status", "resulting_engagement_ref",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CustomerRegisterError(message)


def _fields(value: Any, fields: set[str], message: str) -> None:
    _require(type(value) is dict and set(value) == fields, message)


def _reference(value: Any, *, private: bool = False, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    pattern = _PRIVATE_REF if private else _REF
    _require(type(value) is str and pattern.fullmatch(value) is not None,
             "customer register reference is invalid")


def _choice(value: Any, choices: Any, message: str) -> None:
    _require(type(value) is str and value in choices, message)


def _observed_time(value: datetime) -> datetime:
    _require(isinstance(value, datetime), "observation time must be timezone-aware")
    try:
        _require(value.tzinfo is not None and value.utcoffset() is not None,
                 "observation time must be timezone-aware")
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise CustomerRegisterError("observation time must be timezone-aware") from None


def _timestamp(value: Any, observed_at: datetime) -> datetime:
    _require(type(value) is str and _TIMESTAMP.fullmatch(value) is not None,
             "customer register timestamp must use timezone-aware RFC 3339 format")
    # RFC 3339 -00:00 means an unknown local offset, not a verified UTC offset.
    _require(not value.endswith("-00:00"), "customer register timestamp offset is unknown")
    try:
        parsed = datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
        parsed = parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise CustomerRegisterError("customer register timestamp is invalid") from None
    _require(parsed <= observed_at, "customer register timestamp is in the future")
    return parsed


def _validated_catalog(catalog: Mapping[str, Any] | None) -> Mapping[str, Any]:
    try:
        data = load_catalog() if catalog is None else catalog
        validate_catalog(data)
        return data
    except (OSError, TypeError, ValueError, KeyError):
        raise CustomerRegisterError("customer register catalog is invalid") from None


def _validate(register: Any, catalog: Mapping[str, Any] | None, observed_at: datetime) -> Mapping[str, Any]:
    observed_at = _observed_time(observed_at)
    data = _validated_catalog(catalog)
    _fields(register, _ROOT_FIELDS, "customer register fields are invalid")
    _require(type(register["schema_version"]) is int and register["schema_version"] == 1,
             "customer register schema version is unsupported")
    _require(type(register["storage_authority"]) is str and register["storage_authority"] == _AUTHORITY,
             "customer register storage authority is invalid")
    for key in ("accounts", "engagements", "referrals"):
        _require(type(register[key]) is list, "customer register records must be arrays")

    entry_ids = {entry["id"] for entry in data["entries"]}
    service_owners = {service["id"]: service["business_id"] for service in data["services"]}
    primary_refs: set[str] = set()

    def unique(value: Any) -> None:
        _reference(value)
        _require(value not in primary_refs, "customer register primary references must be unique")
        primary_refs.add(value)

    accounts: dict[str, datetime] = {}
    for account in register["accounts"]:
        _fields(account, _ACCOUNT_FIELDS, "customer register account fields are invalid")
        unique(account["account_ref"])
        _reference(account["private_contact_ref"], private=True, nullable=True)
        accounts[account["account_ref"]] = _timestamp(account["created_at"], observed_at)

    engagements: dict[str, dict[str, Any]] = {}
    for engagement in register["engagements"]:
        _fields(engagement, _ENGAGEMENT_FIELDS, "customer register engagement fields are invalid")
        unique(engagement["engagement_ref"])
        _reference(engagement["account_ref"])
        _require(engagement["account_ref"] in accounts, "customer register engagement account is missing")
        _choice(engagement["catalog_entry_id"], entry_ids & _SCHEMA_ENTRY_IDS,
                "customer register catalog entry is invalid")
        entry_id = engagement["catalog_entry_id"]
        service = engagement["service_ref"]
        _require(service is None or type(service) is str, "customer register service reference is invalid")
        if entry_id == "retally-recovery":
            _require(service in service_owners and service_owners[service] == entry_id,
                     "customer register recovery service is invalid")
        elif service in service_owners:
            _require(service_owners[service] == entry_id, "customer register service belongs to another entry")
        else:
            _reference(service, private=True, nullable=True)
        _require(type(engagement["owner_role"]) is str and bool(engagement["owner_role"].strip()),
                 "customer register owner role is invalid")
        _choice(engagement["stage"], WORKFLOW_IDS, "customer register stage is invalid")
        _choice(engagement["payment_status"], _PAYMENTS, "customer register payment status is invalid")
        for field in _EVIDENCE_FIELDS:
            _reference(engagement[field], private=True, nullable=True)
        currency = engagement["currency"]
        _require(currency is None or (type(currency) is str and _CURRENCY.fullmatch(currency) is not None),
                 "customer register currency is invalid")
        updated_at = _timestamp(engagement["updated_at"], observed_at)
        _require(accounts[engagement["account_ref"]] <= updated_at,
                 "customer register engagement predates its account")
        engagements[engagement["engagement_ref"]] = engagement

    for referral in register["referrals"]:
        _fields(referral, _REFERRAL_FIELDS, "customer register referral fields are invalid")
        unique(referral["referral_ref"])
        _reference(referral["account_ref"])
        _require(referral["account_ref"] in accounts, "customer register referral account is missing")
        _reference(referral["source_engagement_ref"])
        _require(referral["source_engagement_ref"] in engagements,
                 "customer register referral source is missing")
        source = engagements[referral["source_engagement_ref"]]
        _require(source["account_ref"] == referral["account_ref"],
                 "customer register referral source belongs to another account")
        _choice(referral["target_catalog_entry_id"], entry_ids,
                "customer register referral target is invalid")
        _require(referral["target_catalog_entry_id"] != source["catalog_entry_id"],
                 "customer register referral must target another catalog entry")
        for field in ("customer_permission_ref", "owner_action_approval_ref"):
            _reference(referral[field], private=True, nullable=True)
        _choice(referral["status"], _REFERRAL_STATUSES, "customer register referral status is invalid")
        result_ref = referral["resulting_engagement_ref"]
        _reference(result_ref, nullable=True)
        if result_ref is not None:
            _require(result_ref in engagements, "customer register resulting engagement is missing")
            result = engagements[result_ref]
            _require(result["account_ref"] == referral["account_ref"],
                     "customer register resulting engagement belongs to another account")
            _require(result["catalog_entry_id"] == referral["target_catalog_entry_id"],
                     "customer register resulting engagement belongs to another catalog entry")
    return data


def validate_customer_register(
    register: Any, *, catalog: Mapping[str, Any] | None = None, observed_at: datetime,
) -> None:
    """Check shape and relationships; evidence strings remain unverified.

    Recovery engagements require an exact catalog service ID. Other engagements
    permit null or an opaque ``private:`` service reference. Input timestamps
    support RFC 3339 with at most microsecond precision and a known UTC offset.
    """
    _validate(register, catalog, observed_at)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "customer register contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CustomerRegisterError("customer register contains invalid JSON numbers")


def load_customer_register_json(
    text: str, *, catalog: Mapping[str, Any] | None = None, observed_at: datetime,
) -> dict[str, Any]:
    """Parse a supplied JSON string; no private file or network access occurs."""
    _require(type(text) is str, "customer register JSON must be text")
    try:
        register = json.loads(text, object_pairs_hook=_unique_json_object, parse_constant=_reject_json_constant)
    except CustomerRegisterError:
        raise
    except (ValueError, RecursionError):
        raise CustomerRegisterError("customer register JSON is invalid") from None
    validate_customer_register(register, catalog=catalog, observed_at=observed_at)
    return register


def build_register_observation(
    register: Any, *, catalog: Mapping[str, Any] | None = None, observed_at: datetime,
) -> dict[str, Any]:
    """Count supplied declarations without exposing identities or claiming truth."""
    data = _validate(register, catalog, observed_at)
    stage_counts = dict.fromkeys(WORKFLOW_IDS, 0)
    payment_counts = dict.fromkeys(_PAYMENTS, 0)
    referral_counts = dict.fromkeys(_REFERRAL_STATUSES, 0)
    entries = {
        entry["id"]: {"catalog_entry_id": entry["id"], "engagements": 0, "referrals_received": 0}
        for entry in data["entries"]
    }
    gaps = {
        "missing_private_contact_ref": sum(a["private_contact_ref"] is None for a in register["accounts"]),
        **{f"missing_{field}": 0 for field in _EVIDENCE_FIELDS},
        "missing_currency": 0,
        "missing_referral_customer_permission_ref": 0,
        "missing_referral_owner_action_approval_ref": 0,
    }
    for engagement in register["engagements"]:
        stage_counts[engagement["stage"]] += 1
        payment_counts[engagement["payment_status"]] += 1
        entries[engagement["catalog_entry_id"]]["engagements"] += 1
        for field in _EVIDENCE_FIELDS:
            gaps[f"missing_{field}"] += engagement[field] is None
        gaps["missing_currency"] += engagement["currency"] is None
    for referral in register["referrals"]:
        referral_counts[referral["status"]] += 1
        entries[referral["target_catalog_entry_id"]]["referrals_received"] += 1
        gaps["missing_referral_customer_permission_ref"] += referral["customer_permission_ref"] is None
        gaps["missing_referral_owner_action_approval_ref"] += referral["owner_action_approval_ref"] is None
    return {
        "mode": "READ_ONLY_REGISTER_OBSERVATION",
        "source_authentication": "NOT_ASSESSED",
        "evidence_verification": "NOT_PERFORMED",
        "snapshot_freshness": "NOT_ASSESSED",
        "external_actions_authorized": False,
        "production_state_mutation_authorized": False,
        "observed_counts": {key: len(register[key]) for key in ("accounts", "engagements", "referrals")},
        "declared_stage_counts": stage_counts,
        "declared_payment_status_counts": payment_counts,
        "declared_referral_status_counts": referral_counts,
        "catalog_entry_counts": [entries[key] for key in sorted(entries)],
        "data_gap_counts": gaps,
        "verified_metrics": {
            "qualified_leads": None, "paying_customers": None,
            "cash_collected": None, "contribution_profit": None,
        },
    }
