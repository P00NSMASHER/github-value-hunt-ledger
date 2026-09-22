"""Scope-bound external action authorization shared by RecoveryWorks branches.

An authorization is evidence that a customer-approved reviewer allowed one exact
class of recovery action. It does not perform the action. Every authorization is
bound to the reviewed ledger state, finding proof, branch, counterparty, routing
reference, payload, currency, amount ceiling, and validity window.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import re
from typing import TYPE_CHECKING

from .engagement import (
    RecoveryEngagementCharter,
    assert_engagement_allows_action_approval,
)
from .models import Branch, CaseState, FindingState, RecoveryFinding, canonical_hash

if TYPE_CHECKING:
    from .ledger import LedgerRecord

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_VALIDITY_DAYS = 30


class RecoveryActionType(str, Enum):
    SUBMIT_DISPUTE = "SUBMIT_DISPUTE"
    SUBMIT_APPEAL = "SUBMIT_APPEAL"
    REQUEST_RECONSIDERATION = "REQUEST_RECONSIDERATION"
    REQUEST_CREDIT_REVIEW = "REQUEST_CREDIT_REVIEW"
    REQUEST_VENDOR_REFUND = "REQUEST_VENDOR_REFUND"
    REQUEST_CREDIT_MEMO = "REQUEST_CREDIT_MEMO"
    SUBMIT_CHANGE_CLAIM = "SUBMIT_CHANGE_CLAIM"
    SUBMIT_TIME_EXTENSION_REQUEST = "SUBMIT_TIME_EXTENSION_REQUEST"
    REQUEST_CUSTOMS_REVIEW = "REQUEST_CUSTOMS_REVIEW"
    REQUEST_BROKER_REVIEW = "REQUEST_BROKER_REVIEW"
    REQUEST_DOCUMENTATION = "REQUEST_DOCUMENTATION"
    REQUEST_STATUS = "REQUEST_STATUS"


ALLOWED_ACTIONS: dict[Branch, frozenset[RecoveryActionType]] = {
    Branch.FREIGHT: frozenset({
        RecoveryActionType.SUBMIT_DISPUTE,
        RecoveryActionType.REQUEST_CREDIT_REVIEW,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
    Branch.PAYER: frozenset({
        RecoveryActionType.SUBMIT_APPEAL,
        RecoveryActionType.REQUEST_RECONSIDERATION,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
    Branch.UTILITY: frozenset({
        RecoveryActionType.SUBMIT_DISPUTE,
        RecoveryActionType.REQUEST_CREDIT_REVIEW,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
    Branch.AP: frozenset({
        RecoveryActionType.REQUEST_VENDOR_REFUND,
        RecoveryActionType.REQUEST_CREDIT_MEMO,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
    Branch.CONSTRUCTION: frozenset({
        RecoveryActionType.SUBMIT_CHANGE_CLAIM,
        RecoveryActionType.SUBMIT_TIME_EXTENSION_REQUEST,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
    Branch.DUTY: frozenset({
        RecoveryActionType.REQUEST_CUSTOMS_REVIEW,
        RecoveryActionType.REQUEST_BROKER_REVIEW,
        RecoveryActionType.REQUEST_DOCUMENTATION,
        RecoveryActionType.REQUEST_STATUS,
    }),
}


class AuthorizationState(str, Enum):
    NOT_YET_ACTIVE = "NOT_YET_ACTIVE"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class RecoveryActionAuthorization:
    authorization_id: str
    client_id: str
    engagement_id: str
    engagement_charter_hash: str
    branch: str
    finding_id: str
    finding_proof_hash: str
    reviewed_record_hash: str
    action_type: str
    target_counterparty_id: str
    recipient_reference_hash: str
    action_payload_hash: str
    currency: str
    authorized_cents: int
    approver_role: str
    issued_on: str
    expires_on: str
    money_movement_authorized: bool
    settlement_acceptance_authorized: bool
    account_change_authorized: bool
    credential_use_authorized: bool
    general_contact_authorized: bool
    automatic_execution_authorized: bool
    authorization_hash: str


@dataclass(frozen=True)
class AuthorizationRevocation:
    revocation_id: str
    authorization_id: str
    authorization_hash: str
    revoked_on: str
    approver_role: str
    reason: str
    revocation_hash: str


@dataclass(frozen=True)
class AuthorizationEvaluation:
    state: str
    authorization_id: str
    as_of_date: str
    authorization_hash: str
    revocation_hash: str | None
    action_allowed: bool


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _sha(name: str, value: str) -> str:
    value = _required(name, value)
    if not SHA256_RE.fullmatch(value):
        raise ValueError(name + " must be lowercase SHA-256")
    return value


def _parse_date(name: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(name + " must be ISO date YYYY-MM-DD") from exc


def _verify_authorization_hash(auth: RecoveryActionAuthorization) -> None:
    body = asdict(auth)
    digest = body.pop("authorization_hash")
    _sha("authorization_hash", digest)
    if canonical_hash(body) != digest:
        raise ValueError("authorization hash mismatch")
    for field in (
        "money_movement_authorized",
        "settlement_acceptance_authorized",
        "account_change_authorized",
        "credential_use_authorized",
        "general_contact_authorized",
        "automatic_execution_authorized",
    ):
        if getattr(auth, field) is not False:
            raise ValueError(field + " must remain false")


def issue_authorization(
    record: "LedgerRecord",
    engagement: RecoveryEngagementCharter,
    *,
    authorization_id: str,
    action_type: RecoveryActionType,
    target_counterparty_id: str,
    recipient_reference_hash: str,
    action_payload_hash: str,
    authorized_cents: int,
    approver_role: str,
    issued_on: str,
    expires_on: str,
    max_validity_days: int = MAX_VALIDITY_DAYS,
) -> RecoveryActionAuthorization:
    finding = record.finding
    if record.case_state is not CaseState.VALIDATED:
        raise ValueError("authorization issuance requires VALIDATED ledger state")
    if finding.state is not FindingState.VALIDATED:
        raise ValueError("authorization issuance requires validated finding proof")
    if not record.reviewer_approved or not record.reviewer_id:
        raise ValueError("authorization issuance requires human reviewer approval")
    _required("authorization_id", authorization_id)
    assert_engagement_allows_action_approval(
        engagement,
        client_id=finding.client_id,
        branch=finding.branch,
        approver_role=approver_role,
        as_of_date=issued_on,
    )
    _required("target_counterparty_id", target_counterparty_id)
    _sha("recipient_reference_hash", recipient_reference_hash)
    _sha("action_payload_hash", action_payload_hash)
    _required("approver_role", approver_role)
    if target_counterparty_id != finding.counterparty_id:
        raise ValueError("authorization counterparty mismatch")
    if action_type not in ALLOWED_ACTIONS[finding.branch]:
        raise ValueError("action type is not allowed for recovery branch")
    if type(authorized_cents) is not int or authorized_cents <= 0:
        raise ValueError("authorized_cents must be positive integer cents")
    if authorized_cents > finding.potential_recovery_cents:
        raise ValueError("authorized_cents exceeds validated potential recovery")

    issued = _parse_date("issued_on", issued_on)
    expires = _parse_date("expires_on", expires_on)
    if expires < issued:
        raise ValueError("expires_on cannot precede issued_on")
    if max_validity_days < 1:
        raise ValueError("max_validity_days must be positive")
    if (expires - issued).days > max_validity_days:
        raise ValueError("authorization validity exceeds internal maximum")
    if expires > _parse_date("engagement expires_on", engagement.expires_on):
        raise ValueError("authorization cannot outlive engagement charter")

    body = {
        "authorization_id": authorization_id,
        "client_id": finding.client_id,
        "engagement_id": engagement.engagement_id,
        "engagement_charter_hash": engagement.charter_hash,
        "branch": finding.branch.value,
        "finding_id": finding.finding_id,
        "finding_proof_hash": finding.proof_hash,
        "reviewed_record_hash": record.record_hash,
        "action_type": action_type.value,
        "target_counterparty_id": target_counterparty_id,
        "recipient_reference_hash": recipient_reference_hash,
        "action_payload_hash": action_payload_hash,
        "currency": finding.currency,
        "authorized_cents": authorized_cents,
        "approver_role": approver_role,
        "issued_on": issued_on,
        "expires_on": expires_on,
        "money_movement_authorized": False,
        "settlement_acceptance_authorized": False,
        "account_change_authorized": False,
        "credential_use_authorized": False,
        "general_contact_authorized": False,
        "automatic_execution_authorized": False,
    }
    return RecoveryActionAuthorization(
        **body,
        authorization_hash=canonical_hash(body),
    )


def revoke_authorization(
    auth: RecoveryActionAuthorization,
    *,
    revocation_id: str,
    revoked_on: str,
    approver_role: str,
    reason: str,
) -> AuthorizationRevocation:
    _verify_authorization_hash(auth)
    _required("revocation_id", revocation_id)
    _required("reason", reason)
    _required("approver_role", approver_role)
    if approver_role != auth.approver_role:
        raise ValueError("revocation approver_role mismatch")
    revoked = _parse_date("revoked_on", revoked_on)
    if revoked < _parse_date("issued_on", auth.issued_on):
        raise ValueError("revoked_on cannot precede issued_on")
    body = {
        "revocation_id": revocation_id,
        "authorization_id": auth.authorization_id,
        "authorization_hash": auth.authorization_hash,
        "revoked_on": revoked_on,
        "approver_role": approver_role,
        "reason": reason,
    }
    return AuthorizationRevocation(**body, revocation_hash=canonical_hash(body))


def _verify_revocation(auth: RecoveryActionAuthorization, revocation: AuthorizationRevocation) -> None:
    body = asdict(revocation)
    digest = body.pop("revocation_hash")
    _sha("revocation_hash", digest)
    if canonical_hash(body) != digest:
        raise ValueError("revocation hash mismatch")
    if revocation.authorization_id != auth.authorization_id:
        raise ValueError("revocation authorization_id mismatch")
    if revocation.authorization_hash != auth.authorization_hash:
        raise ValueError("revocation authorization_hash mismatch")
    if revocation.approver_role != auth.approver_role:
        raise ValueError("revocation approver_role mismatch")


def evaluate_authorization(
    auth: RecoveryActionAuthorization,
    finding: RecoveryFinding,
    *,
    as_of_date: str,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> AuthorizationEvaluation:
    _verify_authorization_hash(auth)
    if auth.client_id != finding.client_id:
        raise ValueError("authorization client mismatch")
    if auth.branch != finding.branch.value:
        raise ValueError("authorization branch mismatch")
    if auth.finding_id != finding.finding_id:
        raise ValueError("authorization finding mismatch")
    if auth.finding_proof_hash != finding.proof_hash:
        raise ValueError("authorization finding proof mismatch")
    if auth.target_counterparty_id != finding.counterparty_id:
        raise ValueError("authorization counterparty mismatch")
    if auth.currency != finding.currency:
        raise ValueError("authorization currency mismatch")
    try:
        action_type = RecoveryActionType(auth.action_type)
    except ValueError as exc:
        raise ValueError("unknown authorization action type") from exc
    if action_type not in ALLOWED_ACTIONS[finding.branch]:
        raise ValueError("authorization action is outside branch policy")
    if auth.authorized_cents <= 0 or auth.authorized_cents > finding.potential_recovery_cents:
        raise ValueError("authorization amount exceeds finding")

    as_of = _parse_date("as_of_date", as_of_date)
    issued = _parse_date("issued_on", auth.issued_on)
    expires = _parse_date("expires_on", auth.expires_on)

    matching: list[AuthorizationRevocation] = []
    seen: set[str] = set()
    for revocation in revocations:
        _verify_revocation(auth, revocation)
        if revocation.revocation_hash in seen:
            raise ValueError("duplicate revocation hash")
        seen.add(revocation.revocation_hash)
        matching.append(revocation)
    if len(matching) > 1:
        raise ValueError("multiple revocations for one authorization")

    revocation = matching[0] if matching else None
    if as_of < issued:
        state = AuthorizationState.NOT_YET_ACTIVE
    elif revocation is not None and as_of >= _parse_date("revoked_on", revocation.revoked_on):
        state = AuthorizationState.REVOKED
    elif as_of > expires:
        state = AuthorizationState.EXPIRED
    else:
        state = AuthorizationState.ACTIVE

    return AuthorizationEvaluation(
        state=state.value,
        authorization_id=auth.authorization_id,
        as_of_date=as_of_date,
        authorization_hash=auth.authorization_hash,
        revocation_hash=revocation.revocation_hash if revocation else None,
        action_allowed=state is AuthorizationState.ACTIVE,
    )


def assert_authorization_matches_reviewed_record(
    auth: RecoveryActionAuthorization,
    record: "LedgerRecord",
    *,
    as_of_date: str,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> None:
    if record.case_state is not CaseState.VALIDATED:
        raise ValueError("authorization requires VALIDATED ledger state")
    if not record.reviewer_approved:
        raise ValueError("authorization requires reviewer approval")
    if auth.reviewed_record_hash != record.record_hash:
        raise ValueError("authorization is not bound to current reviewed record")
    evaluation = evaluate_authorization(
        auth,
        record.finding,
        as_of_date=as_of_date,
        revocations=revocations,
    )
    if not evaluation.action_allowed:
        raise ValueError("authorization is not ACTIVE: " + evaluation.state)


def assert_action_allowed(
    auth: RecoveryActionAuthorization,
    finding: RecoveryFinding,
    *,
    as_of_date: str,
    action_type: RecoveryActionType,
    target_counterparty_id: str,
    recipient_reference_hash: str,
    action_payload_hash: str,
    currency: str,
    requested_cents: int,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> None:
    evaluation = evaluate_authorization(
        auth,
        finding,
        as_of_date=as_of_date,
        revocations=revocations,
    )
    if not evaluation.action_allowed:
        raise ValueError("authorization is not ACTIVE: " + evaluation.state)
    if action_type.value != auth.action_type:
        raise ValueError("action_type exceeds authorization")
    if target_counterparty_id != auth.target_counterparty_id:
        raise ValueError("target counterparty exceeds authorization")
    if recipient_reference_hash != auth.recipient_reference_hash:
        raise ValueError("recipient/routing reference exceeds authorization")
    if action_payload_hash != auth.action_payload_hash:
        raise ValueError("action payload exceeds authorization")
    if currency != auth.currency:
        raise ValueError("currency exceeds authorization")
    if type(requested_cents) is not int or requested_cents <= 0:
        raise ValueError("requested_cents must be positive")
    if requested_cents > auth.authorized_cents:
        raise ValueError("requested amount exceeds authorization")


def authorization_to_dict(auth: RecoveryActionAuthorization) -> dict:
    return asdict(auth)


def authorization_from_dict(data: dict) -> RecoveryActionAuthorization:
    return RecoveryActionAuthorization(**data)


def revocation_to_dict(revocation: AuthorizationRevocation) -> dict:
    return asdict(revocation)


def revocation_from_dict(data: dict) -> AuthorizationRevocation:
    return AuthorizationRevocation(**data)
