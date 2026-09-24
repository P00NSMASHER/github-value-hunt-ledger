"""Verified pilot kickoff authorization over an accepted prelaunch charter.

This module does not create buyer consent. It verifies a separately supplied
authorization receipt and turns it into an internal kickoff gate for read-only
customer-data processing. External recovery actions, outreach, invoicing, and
provider mutation remain unauthorized.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_charter import (
    PilotCharterState,
    RecoveryWorksPilotCharter,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _iso_date(name: str, value: str) -> str:
    raw = _text(name, value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class ExternalPilotKickoffAuthorization:
    authorization_id: str
    charter_id: str
    charter_proof_hash: str
    engagement_id: str
    buyer_id: str
    authorized_by: str
    authorized_at: str
    expires_at: str
    processing_purpose: str
    billing_account_scope: tuple[str, ...]
    provider_scope: tuple[str, ...]
    source_date_start: str
    source_date_end: str
    retention_until: str
    source_hash: str
    source_locator: str
    verified: bool
    customer_data_processing_authorized: bool = True
    kickoff_authorized: bool = True
    outreach_authorized: bool = False
    external_action_authorized: bool = False
    provider_mutation_authorized: bool = False
    invoice_authorized: bool = False
    payment_collection_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "charter_id", "engagement_id", "buyer_id", "authorized_by",
            "processing_purpose", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "charter_proof_hash",
            normalize_sha256("charter_proof_hash", self.charter_proof_hash),
        )
        authorized = normalize_utc_timestamp("authorized_at", self.authorized_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        retention = normalize_utc_timestamp("retention_until", self.retention_until)
        if _instant(expires) <= _instant(authorized):
            raise ValueError("kickoff authorization must expire after authorization")
        if _instant(retention) < _instant(authorized):
            raise ValueError("retention_until cannot predate authorization")
        object.__setattr__(self, "authorized_at", authorized)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(self, "retention_until", retention)
        start = _iso_date("source_date_start", self.source_date_start)
        end = _iso_date("source_date_end", self.source_date_end)
        if end < start:
            raise ValueError("source_date_end cannot precede source_date_start")
        object.__setattr__(self, "source_date_start", start)
        object.__setattr__(self, "source_date_end", end)
        accounts = tuple(sorted({_text("billing_account_scope", x) for x in self.billing_account_scope}))
        providers = tuple(sorted({_text("provider_scope", x).lower() for x in self.provider_scope}))
        if not accounts or not providers:
            raise ValueError("kickoff authorization requires account and provider scope")
        object.__setattr__(self, "billing_account_scope", accounts)
        object.__setattr__(self, "provider_scope", providers)
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("kickoff authorization receipt must be verified")
        if self.processing_purpose != "READ_ONLY_RECOVERYWORKS_PILOT":
            raise ValueError("unsupported kickoff processing purpose")
        if not self.customer_data_processing_authorized or not self.kickoff_authorized:
            raise ValueError("kickoff receipt must explicitly authorize data processing and kickoff")
        if (
            self.outreach_authorized
            or self.external_action_authorized
            or self.provider_mutation_authorized
            or self.invoice_authorized
            or self.payment_collection_authorized
        ):
            raise ValueError("kickoff authorization cannot authorize downstream consequential actions")
        expected = "recoveryworks-pilot-kickoff-authorization:" + canonical_hash(
            self._identity()
        )
        if self.authorization_id != expected:
            raise ValueError("authorization_id does not bind kickoff authorization")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "charter_id": self.charter_id,
            "charter_proof_hash": self.charter_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "authorized_by": self.authorized_by,
            "authorized_at": self.authorized_at,
            "expires_at": self.expires_at,
            "processing_purpose": self.processing_purpose,
            "billing_account_scope": list(self.billing_account_scope),
            "provider_scope": list(self.provider_scope),
            "source_date_start": self.source_date_start,
            "source_date_end": self.source_date_end,
            "retention_until": self.retention_until,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "customer_data_processing_authorized": True,
            "kickoff_authorized": True,
            "outreach_authorized": False,
            "external_action_authorized": False,
            "provider_mutation_authorized": False,
            "invoice_authorized": False,
            "payment_collection_authorized": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_external_pilot_kickoff_authorization(
    charter: RecoveryWorksPilotCharter,
    *,
    authorized_by: str,
    authorized_at: str,
    expires_at: str,
    retention_until: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> ExternalPilotKickoffAuthorization:
    if charter.state is not PilotCharterState.PRELAUNCH_ACCEPTED:
        raise ValueError("pilot charter is not fully acknowledged")
    if not verified:
        raise ValueError("kickoff authorization receipt must be verified")
    identity = {
        "schema": 1,
        "charter_id": charter.charter_id,
        "charter_proof_hash": charter.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "authorized_by": _text("authorized_by", authorized_by),
        "authorized_at": normalize_utc_timestamp("authorized_at", authorized_at),
        "expires_at": normalize_utc_timestamp("expires_at", expires_at),
        "processing_purpose": "READ_ONLY_RECOVERYWORKS_PILOT",
        "billing_account_scope": sorted(charter.billing_account_scope),
        "provider_scope": sorted(x.lower() for x in charter.provider_scope),
        "source_date_start": charter.source_date_start,
        "source_date_end": charter.source_date_end,
        "retention_until": normalize_utc_timestamp("retention_until", retention_until),
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": True,
        "customer_data_processing_authorized": True,
        "kickoff_authorized": True,
        "outreach_authorized": False,
        "external_action_authorized": False,
        "provider_mutation_authorized": False,
        "invoice_authorized": False,
        "payment_collection_authorized": False,
    }
    return ExternalPilotKickoffAuthorization(
        authorization_id="recoveryworks-pilot-kickoff-authorization:"
        + canonical_hash(identity),
        charter_id=charter.charter_id,
        charter_proof_hash=charter.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        authorized_by=authorized_by,
        authorized_at=authorized_at,
        expires_at=expires_at,
        processing_purpose="READ_ONLY_RECOVERYWORKS_PILOT",
        billing_account_scope=charter.billing_account_scope,
        provider_scope=charter.provider_scope,
        source_date_start=charter.source_date_start,
        source_date_end=charter.source_date_end,
        retention_until=retention_until,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=True,
    )


@dataclass(frozen=True)
class PilotKickoffGate:
    gate_id: str
    charter_id: str
    charter_proof_hash: str
    kickoff_authorization_proof_hash: str
    engagement_id: str
    buyer_id: str
    checked_at: str
    customer_data_processing_authorized: bool = True
    kickoff_authorized: bool = True
    external_action_authorized: bool = False
    provider_mutation_authorized: bool = False
    outreach_authorized: bool = False
    invoice_authorized: bool = False
    payment_collection_authorized: bool = False

    def __post_init__(self) -> None:
        for name in ("charter_proof_hash", "kickoff_authorization_proof_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at))
        if not self.customer_data_processing_authorized or not self.kickoff_authorized:
            raise ValueError("kickoff gate must represent authorized read-only processing")
        if (
            self.external_action_authorized
            or self.provider_mutation_authorized
            or self.outreach_authorized
            or self.invoice_authorized
            or self.payment_collection_authorized
        ):
            raise ValueError("kickoff gate cannot authorize downstream consequential actions")
        expected = "recoveryworks-pilot-kickoff-gate:" + canonical_hash(self._identity())
        if self.gate_id != expected:
            raise ValueError("gate_id does not bind kickoff gate")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "charter_id": self.charter_id,
            "charter_proof_hash": self.charter_proof_hash,
            "kickoff_authorization_proof_hash": self.kickoff_authorization_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "checked_at": self.checked_at,
            "customer_data_processing_authorized": True,
            "kickoff_authorized": True,
            "external_action_authorized": False,
            "provider_mutation_authorized": False,
            "outreach_authorized": False,
            "invoice_authorized": False,
            "payment_collection_authorized": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "gate_id": self.gate_id,
            "proof_hash": self.proof_hash,
            "state": "PILOT_KICKOFF_AUTHORIZED_READ_ONLY",
        }


def build_pilot_kickoff_gate(
    charter: RecoveryWorksPilotCharter,
    authorization: ExternalPilotKickoffAuthorization,
    *,
    checked_at: str,
) -> PilotKickoffGate:
    if charter.state is not PilotCharterState.PRELAUNCH_ACCEPTED:
        raise ValueError("pilot charter is not fully acknowledged")
    if authorization.charter_id != charter.charter_id:
        raise ValueError("kickoff authorization charter id mismatch")
    if authorization.charter_proof_hash != charter.proof_hash:
        raise ValueError("kickoff authorization charter proof mismatch")
    if authorization.engagement_id != charter.engagement_id:
        raise ValueError("kickoff authorization engagement mismatch")
    if authorization.buyer_id != charter.buyer_id:
        raise ValueError("kickoff authorization buyer mismatch")
    if tuple(sorted(authorization.billing_account_scope)) != tuple(sorted(charter.billing_account_scope)):
        raise ValueError("kickoff authorization billing-account scope mismatch")
    if tuple(sorted(authorization.provider_scope)) != tuple(sorted(x.lower() for x in charter.provider_scope)):
        raise ValueError("kickoff authorization provider scope mismatch")
    if authorization.source_date_start != charter.source_date_start:
        raise ValueError("kickoff authorization source start mismatch")
    if authorization.source_date_end != charter.source_date_end:
        raise ValueError("kickoff authorization source end mismatch")
    checked = normalize_utc_timestamp("checked_at", checked_at)
    if _instant(checked) < _instant(authorization.authorized_at):
        raise ValueError("kickoff gate cannot predate authorization")
    if _instant(checked) >= _instant(authorization.expires_at):
        raise ValueError("kickoff authorization expired")
    identity = {
        "schema": 1,
        "charter_id": charter.charter_id,
        "charter_proof_hash": charter.proof_hash,
        "kickoff_authorization_proof_hash": authorization.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "checked_at": checked,
        "customer_data_processing_authorized": True,
        "kickoff_authorized": True,
        "external_action_authorized": False,
        "provider_mutation_authorized": False,
        "outreach_authorized": False,
        "invoice_authorized": False,
        "payment_collection_authorized": False,
    }
    return PilotKickoffGate(
        gate_id="recoveryworks-pilot-kickoff-gate:" + canonical_hash(identity),
        charter_id=charter.charter_id,
        charter_proof_hash=charter.proof_hash,
        kickoff_authorization_proof_hash=authorization.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        checked_at=checked,
    )
