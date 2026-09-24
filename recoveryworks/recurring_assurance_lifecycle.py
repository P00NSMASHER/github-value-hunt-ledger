"""Governed recurring monthly-assurance service lifecycle.

This module turns a previously verified recurring-assurance readiness artifact
into an internal service state. Activation and deactivation are explicit,
proof-bound operator receipts. Neither state authorizes automatic invoicing,
provider mutation, customer-scope mutation, or any external action.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.recurring_assurance_activation import RecurringAssuranceActivationReadiness


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


class RecurringAssuranceLifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


@dataclass(frozen=True)
class RecurringAssuranceServiceActivationReceipt:
    receipt_id: str
    readiness_id: str
    readiness_proof_hash: str
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
    activated_at: str
    operator_id: str
    activation_reference: str
    internal_operator_authorized: bool
    automatic_invoice_schedule_enabled: bool = False
    provider_mutation_enabled: bool = False
    customer_scope_mutation_enabled: bool = False
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "readiness_id", "engagement_id", "buyer_id", "business_unit",
            "currency", "operator_id", "activation_reference",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "readiness_proof_hash", "authorization_receipt_proof_hash",
            "agreement_receipt_proof_hash",
            "closeout_acknowledgment_proof_hash", "charter_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        accounts = tuple(
            sorted(_text("billing_account", x) for x in self.billing_account_scope)
        )
        providers = tuple(
            sorted(_text("provider", x).lower() for x in self.provider_scope)
        )
        if not accounts or not providers:
            raise ValueError("recurring assurance lifecycle scope cannot be empty")
        object.__setattr__(self, "billing_account_scope", accounts)
        object.__setattr__(self, "provider_scope", providers)
        object.__setattr__(self, "currency", self.currency.upper())
        if (
            type(self.monthly_assurance_fee_cents) is not int
            or self.monthly_assurance_fee_cents <= 0
        ):
            raise ValueError("monthly_assurance_fee_cents must be positive")
        for name in ("service_start_at", "service_end_at", "activated_at"):
            object.__setattr__(
                self, name, normalize_utc_timestamp(name, getattr(self, name))
            )
        if _instant(self.service_end_at) <= _instant(self.service_start_at):
            raise ValueError("service_end_at must follow service_start_at")
        if not (
            _instant(self.service_start_at)
            <= _instant(self.activated_at)
            < _instant(self.service_end_at)
        ):
            raise ValueError("activation must occur inside authorized service window")
        if self.internal_operator_authorized is not True:
            raise ValueError("recurring assurance activation requires authorized operator")
        if (
            self.automatic_invoice_schedule_enabled
            or self.provider_mutation_enabled
            or self.customer_scope_mutation_enabled
            or self.external_actions_performed
        ):
            raise ValueError(
                "recurring assurance lifecycle cannot enable automatic billing, "
                "provider/scope mutation, or external actions"
            )
        expected = "recoveryworks-recurring-assurance-service-activation:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind recurring assurance activation")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "readiness_id": self.readiness_id,
            "readiness_proof_hash": self.readiness_proof_hash,
            "authorization_receipt_proof_hash": self.authorization_receipt_proof_hash,
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
            "activated_at": self.activated_at,
            "operator_id": self.operator_id,
            "activation_reference": self.activation_reference,
            "internal_operator_authorized": True,
            "automatic_invoice_schedule_enabled": False,
            "provider_mutation_enabled": False,
            "customer_scope_mutation_enabled": False,
            "external_actions_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_recurring_assurance_service_activation(
    readiness: RecurringAssuranceActivationReadiness,
    *,
    activated_at: str,
    operator_id: str,
    activation_reference: str,
    internal_operator_authorized: bool,
) -> RecurringAssuranceServiceActivationReceipt:
    identity = {
        "schema": 1,
        "readiness_id": readiness.readiness_id,
        "readiness_proof_hash": readiness.proof_hash,
        "authorization_receipt_proof_hash": readiness.authorization_receipt_proof_hash,
        "agreement_receipt_proof_hash": readiness.agreement_receipt_proof_hash,
        "closeout_acknowledgment_proof_hash":
            readiness.closeout_acknowledgment_proof_hash,
        "charter_proof_hash": readiness.charter_proof_hash,
        "engagement_id": readiness.engagement_id,
        "buyer_id": readiness.buyer_id,
        "business_unit": readiness.business_unit,
        "billing_account_scope": list(readiness.billing_account_scope),
        "provider_scope": list(readiness.provider_scope),
        "currency": readiness.currency.upper(),
        "monthly_assurance_fee_cents": readiness.monthly_assurance_fee_cents,
        "service_start_at": readiness.service_start_at,
        "service_end_at": readiness.service_end_at,
        "activated_at": normalize_utc_timestamp("activated_at", activated_at),
        "operator_id": _text("operator_id", operator_id),
        "activation_reference": _text("activation_reference", activation_reference),
        "internal_operator_authorized": internal_operator_authorized,
        "automatic_invoice_schedule_enabled": False,
        "provider_mutation_enabled": False,
        "customer_scope_mutation_enabled": False,
        "external_actions_performed": False,
    }
    return RecurringAssuranceServiceActivationReceipt(
        receipt_id="recoveryworks-recurring-assurance-service-activation:"
        + canonical_hash(identity),
        readiness_id=readiness.readiness_id,
        readiness_proof_hash=readiness.proof_hash,
        authorization_receipt_proof_hash=readiness.authorization_receipt_proof_hash,
        agreement_receipt_proof_hash=readiness.agreement_receipt_proof_hash,
        closeout_acknowledgment_proof_hash=
            readiness.closeout_acknowledgment_proof_hash,
        charter_proof_hash=readiness.charter_proof_hash,
        engagement_id=readiness.engagement_id,
        buyer_id=readiness.buyer_id,
        business_unit=readiness.business_unit,
        billing_account_scope=readiness.billing_account_scope,
        provider_scope=readiness.provider_scope,
        currency=readiness.currency,
        monthly_assurance_fee_cents=readiness.monthly_assurance_fee_cents,
        service_start_at=readiness.service_start_at,
        service_end_at=readiness.service_end_at,
        activated_at=activated_at,
        operator_id=operator_id,
        activation_reference=activation_reference,
        internal_operator_authorized=internal_operator_authorized,
        automatic_invoice_schedule_enabled=False,
        provider_mutation_enabled=False,
        customer_scope_mutation_enabled=False,
        external_actions_performed=False,
    )


@dataclass(frozen=True)
class RecurringAssuranceServiceDeactivationReceipt:
    receipt_id: str
    activation_receipt_id: str
    activation_receipt_proof_hash: str
    readiness_proof_hash: str
    engagement_id: str
    buyer_id: str
    deactivated_at: str
    operator_id: str
    deactivation_reference: str
    reason: str
    internal_operator_authorized: bool
    automatic_refund_or_credit_enabled: bool = False
    provider_mutation_enabled: bool = False
    customer_scope_mutation_enabled: bool = False
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "activation_receipt_id", "engagement_id", "buyer_id", "operator_id",
            "deactivation_reference", "reason",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("activation_receipt_proof_hash", "readiness_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self,
            "deactivated_at",
            normalize_utc_timestamp("deactivated_at", self.deactivated_at),
        )
        if self.internal_operator_authorized is not True:
            raise ValueError("recurring assurance deactivation requires authorized operator")
        if (
            self.automatic_refund_or_credit_enabled
            or self.provider_mutation_enabled
            or self.customer_scope_mutation_enabled
            or self.external_actions_performed
        ):
            raise ValueError(
                "recurring assurance deactivation cannot trigger billing/provider actions"
            )
        expected = "recoveryworks-recurring-assurance-service-deactivation:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind recurring assurance deactivation")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "activation_receipt_id": self.activation_receipt_id,
            "activation_receipt_proof_hash": self.activation_receipt_proof_hash,
            "readiness_proof_hash": self.readiness_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "deactivated_at": self.deactivated_at,
            "operator_id": self.operator_id,
            "deactivation_reference": self.deactivation_reference,
            "reason": self.reason,
            "internal_operator_authorized": True,
            "automatic_refund_or_credit_enabled": False,
            "provider_mutation_enabled": False,
            "customer_scope_mutation_enabled": False,
            "external_actions_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_recurring_assurance_service_deactivation(
    activation: RecurringAssuranceServiceActivationReceipt,
    *,
    deactivated_at: str,
    operator_id: str,
    deactivation_reference: str,
    reason: str,
    internal_operator_authorized: bool,
) -> RecurringAssuranceServiceDeactivationReceipt:
    normalized_deactivated = normalize_utc_timestamp("deactivated_at", deactivated_at)
    if _instant(normalized_deactivated) < _instant(activation.activated_at):
        raise ValueError("deactivation cannot predate activation")
    identity = {
        "schema": 1,
        "activation_receipt_id": activation.receipt_id,
        "activation_receipt_proof_hash": activation.proof_hash,
        "readiness_proof_hash": activation.readiness_proof_hash,
        "engagement_id": activation.engagement_id,
        "buyer_id": activation.buyer_id,
        "deactivated_at": normalized_deactivated,
        "operator_id": _text("operator_id", operator_id),
        "deactivation_reference": _text(
            "deactivation_reference", deactivation_reference
        ),
        "reason": _text("reason", reason),
        "internal_operator_authorized": internal_operator_authorized,
        "automatic_refund_or_credit_enabled": False,
        "provider_mutation_enabled": False,
        "customer_scope_mutation_enabled": False,
        "external_actions_performed": False,
    }
    return RecurringAssuranceServiceDeactivationReceipt(
        receipt_id="recoveryworks-recurring-assurance-service-deactivation:"
        + canonical_hash(identity),
        activation_receipt_id=activation.receipt_id,
        activation_receipt_proof_hash=activation.proof_hash,
        readiness_proof_hash=activation.readiness_proof_hash,
        engagement_id=activation.engagement_id,
        buyer_id=activation.buyer_id,
        deactivated_at=normalized_deactivated,
        operator_id=operator_id,
        deactivation_reference=deactivation_reference,
        reason=reason,
        internal_operator_authorized=internal_operator_authorized,
        automatic_refund_or_credit_enabled=False,
        provider_mutation_enabled=False,
        customer_scope_mutation_enabled=False,
        external_actions_performed=False,
    )


@dataclass(frozen=True)
class RecurringAssuranceServiceLifecycle:
    lifecycle_id: str
    readiness_id: str
    readiness_proof_hash: str
    activation_receipt_proof_hash: str
    deactivation_receipt_proof_hash: str | None
    engagement_id: str
    buyer_id: str
    business_unit: str
    billing_account_scope: tuple[str, ...]
    provider_scope: tuple[str, ...]
    currency: str
    monthly_assurance_fee_cents: int
    service_start_at: str
    service_end_at: str
    active_from: str
    active_until: str | None
    state: RecurringAssuranceLifecycleState
    automatic_invoice_schedule_enabled: bool = False
    provider_mutation_enabled: bool = False
    customer_scope_mutation_enabled: bool = False
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        for name in ("readiness_proof_hash", "activation_receipt_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if self.deactivation_receipt_proof_hash is not None:
            object.__setattr__(
                self,
                "deactivation_receipt_proof_hash",
                normalize_sha256(
                    "deactivation_receipt_proof_hash",
                    self.deactivation_receipt_proof_hash,
                ),
            )
        if not isinstance(self.state, RecurringAssuranceLifecycleState):
            raise ValueError("state must be RecurringAssuranceLifecycleState")
        if self.state is RecurringAssuranceLifecycleState.ACTIVE:
            if (
                self.deactivation_receipt_proof_hash is not None
                or self.active_until is not None
            ):
                raise ValueError("active lifecycle cannot include deactivation")
        else:
            if (
                self.deactivation_receipt_proof_hash is None
                or self.active_until is None
            ):
                raise ValueError("deactivated lifecycle requires deactivation proof/time")
        if (
            self.automatic_invoice_schedule_enabled
            or self.provider_mutation_enabled
            or self.customer_scope_mutation_enabled
            or self.external_actions_performed
        ):
            raise ValueError(
                "recurring lifecycle snapshot cannot authorize external consequences"
            )
        expected = "recoveryworks-recurring-assurance-service-lifecycle:" + canonical_hash(
            self._identity()
        )
        if self.lifecycle_id != expected:
            raise ValueError("lifecycle_id does not bind recurring assurance lifecycle")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "readiness_id": self.readiness_id,
            "readiness_proof_hash": self.readiness_proof_hash,
            "activation_receipt_proof_hash": self.activation_receipt_proof_hash,
            "deactivation_receipt_proof_hash": self.deactivation_receipt_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "billing_account_scope": list(self.billing_account_scope),
            "provider_scope": list(self.provider_scope),
            "currency": self.currency,
            "monthly_assurance_fee_cents": self.monthly_assurance_fee_cents,
            "service_start_at": self.service_start_at,
            "service_end_at": self.service_end_at,
            "active_from": self.active_from,
            "active_until": self.active_until,
            "state": self.state.value,
            "automatic_invoice_schedule_enabled": False,
            "provider_mutation_enabled": False,
            "customer_scope_mutation_enabled": False,
            "external_actions_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "lifecycle_id": self.lifecycle_id,
            "proof_hash": self.proof_hash,
        }


def build_recurring_assurance_service_lifecycle(
    readiness: RecurringAssuranceActivationReadiness,
    activation: RecurringAssuranceServiceActivationReceipt,
    deactivation: RecurringAssuranceServiceDeactivationReceipt | None = None,
) -> RecurringAssuranceServiceLifecycle:
    if (
        activation.readiness_id != readiness.readiness_id
        or activation.readiness_proof_hash != readiness.proof_hash
    ):
        raise ValueError("activation does not bind exact recurring readiness")
    checks = (
        ("authorization proof", activation.authorization_receipt_proof_hash,
         readiness.authorization_receipt_proof_hash),
        ("agreement proof", activation.agreement_receipt_proof_hash,
         readiness.agreement_receipt_proof_hash),
        ("closeout acknowledgment proof",
         activation.closeout_acknowledgment_proof_hash,
         readiness.closeout_acknowledgment_proof_hash),
        ("charter proof", activation.charter_proof_hash, readiness.charter_proof_hash),
        ("engagement", activation.engagement_id, readiness.engagement_id),
        ("buyer", activation.buyer_id, readiness.buyer_id),
        ("business unit", activation.business_unit, readiness.business_unit),
        ("currency", activation.currency, readiness.currency),
        ("monthly fee", activation.monthly_assurance_fee_cents,
         readiness.monthly_assurance_fee_cents),
        ("service start", activation.service_start_at, readiness.service_start_at),
        ("service end", activation.service_end_at, readiness.service_end_at),
    )
    for label, actual, expected in checks:
        if actual != expected:
            raise ValueError(f"activation {label} mismatch")
    if activation.billing_account_scope != readiness.billing_account_scope:
        raise ValueError("activation billing account scope mismatch")
    if activation.provider_scope != readiness.provider_scope:
        raise ValueError("activation provider scope mismatch")

    if deactivation is not None:
        if (
            deactivation.activation_receipt_id != activation.receipt_id
            or deactivation.activation_receipt_proof_hash != activation.proof_hash
        ):
            raise ValueError("deactivation does not bind exact activation")
        if deactivation.readiness_proof_hash != readiness.proof_hash:
            raise ValueError("deactivation recurring readiness mismatch")
        if (
            deactivation.engagement_id != readiness.engagement_id
            or deactivation.buyer_id != readiness.buyer_id
        ):
            raise ValueError("deactivation buyer/engagement mismatch")
        state = RecurringAssuranceLifecycleState.DEACTIVATED
        deactivation_hash = deactivation.proof_hash
        active_until = deactivation.deactivated_at
    else:
        state = RecurringAssuranceLifecycleState.ACTIVE
        deactivation_hash = None
        active_until = None

    identity = {
        "schema": 1,
        "readiness_id": readiness.readiness_id,
        "readiness_proof_hash": readiness.proof_hash,
        "activation_receipt_proof_hash": activation.proof_hash,
        "deactivation_receipt_proof_hash": deactivation_hash,
        "engagement_id": readiness.engagement_id,
        "buyer_id": readiness.buyer_id,
        "business_unit": readiness.business_unit,
        "billing_account_scope": list(readiness.billing_account_scope),
        "provider_scope": list(readiness.provider_scope),
        "currency": readiness.currency,
        "monthly_assurance_fee_cents": readiness.monthly_assurance_fee_cents,
        "service_start_at": readiness.service_start_at,
        "service_end_at": readiness.service_end_at,
        "active_from": activation.activated_at,
        "active_until": active_until,
        "state": state.value,
        "automatic_invoice_schedule_enabled": False,
        "provider_mutation_enabled": False,
        "customer_scope_mutation_enabled": False,
        "external_actions_performed": False,
    }
    return RecurringAssuranceServiceLifecycle(
        lifecycle_id="recoveryworks-recurring-assurance-service-lifecycle:"
        + canonical_hash(identity),
        readiness_id=readiness.readiness_id,
        readiness_proof_hash=readiness.proof_hash,
        activation_receipt_proof_hash=activation.proof_hash,
        deactivation_receipt_proof_hash=deactivation_hash,
        engagement_id=readiness.engagement_id,
        buyer_id=readiness.buyer_id,
        business_unit=readiness.business_unit,
        billing_account_scope=readiness.billing_account_scope,
        provider_scope=readiness.provider_scope,
        currency=readiness.currency,
        monthly_assurance_fee_cents=readiness.monthly_assurance_fee_cents,
        service_start_at=readiness.service_start_at,
        service_end_at=readiness.service_end_at,
        active_from=activation.activated_at,
        active_until=active_until,
        state=state,
        automatic_invoice_schedule_enabled=False,
        provider_mutation_enabled=False,
        customer_scope_mutation_enabled=False,
        external_actions_performed=False,
    )
