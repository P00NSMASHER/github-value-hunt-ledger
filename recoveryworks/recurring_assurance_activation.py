"""Monthly assurance activation readiness after a verified pilot closeout.

This half-step requires explicit external recurring-service authorization. It
does not start service, schedule invoices, perform provider calls, or authorize
provider mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from recoveryworks.commercial_agreement_gate import FinalizedCommercialAgreementReceipt
from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_charter import RecoveryWorksPilotCharter
from recoveryworks.pilot_closeout_acknowledgment import (
    ContinuationInterest,
    PilotCloseoutAcknowledgment,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} cannot contain control characters")
    return value


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class ExternalRecurringAssuranceAuthorizationReceipt:
    receipt_id: str
    agreement_receipt_proof_hash: str
    closeout_acknowledgment_proof_hash: str
    charter_proof_hash: str
    engagement_id: str
    buyer_id: str
    business_unit: str
    billing_account_scope: tuple[str, ...]
    provider_scope: tuple[str, ...]
    currency: str
    monthly_assurance_fee_cents: int
    service_start_at: str
    service_end_at: str
    authorization_reference: str
    source_hash: str
    source_locator: str
    verified: bool
    externally_authorized: bool
    monthly_cadence_authorized: bool
    provider_write_access_authorized: bool = False
    automatic_invoice_authorized: bool = False
    customer_scope_expansion_authorized: bool = False
    created_by_recoveryworks: bool = False

    def __post_init__(self) -> None:
        for name in (
            "engagement_id", "buyer_id", "business_unit", "currency",
            "authorization_reference", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "agreement_receipt_proof_hash",
            "closeout_acknowledgment_proof_hash",
            "charter_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        accounts = tuple(sorted(_text("billing_account", x) for x in self.billing_account_scope))
        providers = tuple(sorted(_text("provider", x).lower() for x in self.provider_scope))
        if not accounts or not providers:
            raise ValueError("recurring assurance scope cannot be empty")
        object.__setattr__(self, "billing_account_scope", accounts)
        object.__setattr__(self, "provider_scope", providers)
        if (
            type(self.monthly_assurance_fee_cents) is not int
            or self.monthly_assurance_fee_cents < 0
        ):
            raise ValueError("monthly_assurance_fee_cents must be non-negative")
        for name in ("service_start_at", "service_end_at"):
            object.__setattr__(
                self, name, normalize_utc_timestamp(name, getattr(self, name))
            )
        if _instant(self.service_end_at) <= _instant(self.service_start_at):
            raise ValueError("service_end_at must follow service_start_at")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if not self.verified or not self.externally_authorized:
            raise ValueError("recurring assurance authorization must be externally verified")
        if not self.monthly_cadence_authorized:
            raise ValueError("monthly cadence must be explicitly authorized")
        if (
            self.provider_write_access_authorized
            or self.automatic_invoice_authorized
            or self.customer_scope_expansion_authorized
            or self.created_by_recoveryworks
        ):
            raise ValueError(
                "recurring authorization cannot enable mutation, auto-invoicing, "
                "scope expansion, or self-authorization"
            )
        expected = "recoveryworks-recurring-assurance-authorization:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind recurring assurance authorization")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "agreement_receipt_proof_hash": self.agreement_receipt_proof_hash,
            "closeout_acknowledgment_proof_hash":
                self.closeout_acknowledgment_proof_hash,
            "charter_proof_hash": self.charter_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "billing_account_scope": list(self.billing_account_scope),
            "provider_scope": list(self.provider_scope),
            "currency": self.currency,
            "monthly_assurance_fee_cents": self.monthly_assurance_fee_cents,
            "service_start_at": self.service_start_at,
            "service_end_at": self.service_end_at,
            "authorization_reference": self.authorization_reference,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "externally_authorized": True,
            "monthly_cadence_authorized": True,
            "provider_write_access_authorized": False,
            "automatic_invoice_authorized": False,
            "customer_scope_expansion_authorized": False,
            "created_by_recoveryworks": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_external_recurring_assurance_authorization(
    charter: RecoveryWorksPilotCharter,
    closeout_ack: PilotCloseoutAcknowledgment,
    agreement: FinalizedCommercialAgreementReceipt,
    *,
    service_start_at: str,
    service_end_at: str,
    authorization_reference: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
    externally_authorized: bool,
) -> ExternalRecurringAssuranceAuthorizationReceipt:
    if closeout_ack.engagement_id != charter.engagement_id:
        raise ValueError("closeout acknowledgment engagement mismatch")
    if closeout_ack.buyer_id != charter.buyer_id:
        raise ValueError("closeout acknowledgment buyer mismatch")
    if closeout_ack.proof_hash != agreement.closeout_acknowledgment_proof_hash:
        raise ValueError("agreement does not bind closeout acknowledgment")
    if agreement.charter_proof_hash != charter.proof_hash:
        raise ValueError("agreement does not bind charter")
    if closeout_ack.continuation_interest is not ContinuationInterest.REVIEW_MONTHLY_ASSURANCE:
        raise ValueError("buyer did not express monthly assurance continuation interest")
    if not agreement.monthly_assurance_separately_accepted:
        raise ValueError("finalized agreement did not separately accept monthly assurance")
    if agreement.monthly_assurance_fee_cents <= 0:
        raise ValueError("monthly assurance fee must be positive for recurring activation")
    identity = {
        "schema": 1,
        "agreement_receipt_proof_hash": agreement.proof_hash,
        "closeout_acknowledgment_proof_hash": closeout_ack.proof_hash,
        "charter_proof_hash": charter.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "business_unit": charter.business_unit,
        "billing_account_scope": sorted(charter.billing_account_scope),
        "provider_scope": sorted(x.lower() for x in charter.provider_scope),
        "currency": agreement.currency,
        "monthly_assurance_fee_cents": agreement.monthly_assurance_fee_cents,
        "service_start_at": normalize_utc_timestamp(
            "service_start_at", service_start_at
        ),
        "service_end_at": normalize_utc_timestamp(
            "service_end_at", service_end_at
        ),
        "authorization_reference": _text(
            "authorization_reference", authorization_reference
        ),
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": verified,
        "externally_authorized": externally_authorized,
        "monthly_cadence_authorized": True,
        "provider_write_access_authorized": False,
        "automatic_invoice_authorized": False,
        "customer_scope_expansion_authorized": False,
        "created_by_recoveryworks": False,
    }
    return ExternalRecurringAssuranceAuthorizationReceipt(
        receipt_id="recoveryworks-recurring-assurance-authorization:"
        + canonical_hash(identity),
        agreement_receipt_proof_hash=agreement.proof_hash,
        closeout_acknowledgment_proof_hash=closeout_ack.proof_hash,
        charter_proof_hash=charter.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        business_unit=charter.business_unit,
        billing_account_scope=tuple(charter.billing_account_scope),
        provider_scope=tuple(charter.provider_scope),
        currency=agreement.currency,
        monthly_assurance_fee_cents=agreement.monthly_assurance_fee_cents,
        service_start_at=service_start_at,
        service_end_at=service_end_at,
        authorization_reference=authorization_reference,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=verified,
        externally_authorized=externally_authorized,
        monthly_cadence_authorized=True,
        provider_write_access_authorized=False,
        automatic_invoice_authorized=False,
        customer_scope_expansion_authorized=False,
        created_by_recoveryworks=False,
    )


@dataclass(frozen=True)
class RecurringAssuranceActivationReadiness:
    readiness_id: str
    authorization_receipt_proof_hash: str
    agreement_receipt_proof_hash: str
    closeout_acknowledgment_proof_hash: str
    charter_proof_hash: str
    engagement_id: str
    buyer_id: str
    business_unit: str
    billing_account_scope: tuple[str, ...]
    provider_scope: tuple[str, ...]
    currency: str
    monthly_assurance_fee_cents: int
    service_start_at: str
    service_end_at: str
    cadence: str = "MONTHLY"
    service_started: bool = False
    invoice_schedule_started: bool = False
    provider_calls_started: bool = False
    provider_mutation_authorized: bool = False
    external_action_performed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "authorization_receipt_proof_hash",
            "agreement_receipt_proof_hash",
            "closeout_acknowledgment_proof_hash",
            "charter_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if self.cadence != "MONTHLY":
            raise ValueError("recurring assurance readiness cadence must be MONTHLY")
        if (
            self.service_started
            or self.invoice_schedule_started
            or self.provider_calls_started
            or self.provider_mutation_authorized
            or self.external_action_performed
        ):
            raise ValueError("recurring assurance readiness cannot start service/actions")
        expected = "recoveryworks-recurring-assurance-readiness:" + canonical_hash(
            self._identity()
        )
        if self.readiness_id != expected:
            raise ValueError("readiness_id does not bind recurring assurance readiness")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "authorization_receipt_proof_hash":
                self.authorization_receipt_proof_hash,
            "agreement_receipt_proof_hash": self.agreement_receipt_proof_hash,
            "closeout_acknowledgment_proof_hash":
                self.closeout_acknowledgment_proof_hash,
            "charter_proof_hash": self.charter_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "billing_account_scope": list(self.billing_account_scope),
            "provider_scope": list(self.provider_scope),
            "currency": self.currency,
            "monthly_assurance_fee_cents": self.monthly_assurance_fee_cents,
            "service_start_at": self.service_start_at,
            "service_end_at": self.service_end_at,
            "cadence": "MONTHLY",
            "service_started": False,
            "invoice_schedule_started": False,
            "provider_calls_started": False,
            "provider_mutation_authorized": False,
            "external_action_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "readiness_id": self.readiness_id,
            "proof_hash": self.proof_hash,
            "state": "MONTHLY_ASSURANCE_ACTIVATION_READY",
        }


def build_recurring_assurance_activation_readiness(
    charter: RecoveryWorksPilotCharter,
    closeout_ack: PilotCloseoutAcknowledgment,
    agreement: FinalizedCommercialAgreementReceipt,
    authorization: ExternalRecurringAssuranceAuthorizationReceipt,
) -> RecurringAssuranceActivationReadiness:
    if authorization.charter_proof_hash != charter.proof_hash:
        raise ValueError("recurring authorization charter mismatch")
    if authorization.closeout_acknowledgment_proof_hash != closeout_ack.proof_hash:
        raise ValueError("recurring authorization closeout acknowledgment mismatch")
    if authorization.agreement_receipt_proof_hash != agreement.proof_hash:
        raise ValueError("recurring authorization agreement mismatch")
    if (
        authorization.engagement_id != charter.engagement_id
        or authorization.buyer_id != charter.buyer_id
        or authorization.business_unit != charter.business_unit
    ):
        raise ValueError("recurring authorization buyer/engagement scope mismatch")
    if tuple(authorization.billing_account_scope) != tuple(sorted(charter.billing_account_scope)):
        raise ValueError("recurring authorization billing account scope mismatch")
    if tuple(authorization.provider_scope) != tuple(sorted(x.lower() for x in charter.provider_scope)):
        raise ValueError("recurring authorization provider scope mismatch")
    if (
        authorization.currency != agreement.currency
        or authorization.monthly_assurance_fee_cents
        != agreement.monthly_assurance_fee_cents
    ):
        raise ValueError("recurring authorization commercial terms mismatch")

    identity = {
        "schema": 1,
        "authorization_receipt_proof_hash": authorization.proof_hash,
        "agreement_receipt_proof_hash": agreement.proof_hash,
        "closeout_acknowledgment_proof_hash": closeout_ack.proof_hash,
        "charter_proof_hash": charter.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "business_unit": charter.business_unit,
        "billing_account_scope": list(authorization.billing_account_scope),
        "provider_scope": list(authorization.provider_scope),
        "currency": agreement.currency,
        "monthly_assurance_fee_cents": agreement.monthly_assurance_fee_cents,
        "service_start_at": authorization.service_start_at,
        "service_end_at": authorization.service_end_at,
        "cadence": "MONTHLY",
        "service_started": False,
        "invoice_schedule_started": False,
        "provider_calls_started": False,
        "provider_mutation_authorized": False,
        "external_action_performed": False,
    }
    return RecurringAssuranceActivationReadiness(
        readiness_id="recoveryworks-recurring-assurance-readiness:"
        + canonical_hash(identity),
        authorization_receipt_proof_hash=authorization.proof_hash,
        agreement_receipt_proof_hash=agreement.proof_hash,
        closeout_acknowledgment_proof_hash=closeout_ack.proof_hash,
        charter_proof_hash=charter.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        business_unit=charter.business_unit,
        billing_account_scope=authorization.billing_account_scope,
        provider_scope=authorization.provider_scope,
        currency=agreement.currency,
        monthly_assurance_fee_cents=agreement.monthly_assurance_fee_cents,
        service_start_at=authorization.service_start_at,
        service_end_at=authorization.service_end_at,
        cadence="MONTHLY",
        service_started=False,
        invoice_schedule_started=False,
        provider_calls_started=False,
        provider_mutation_authorized=False,
        external_action_performed=False,
    )
