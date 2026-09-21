"""Buyer-approved, scope-bound external action authorization for Freight Recovery.

This module authorizes narrowly enumerated carrier actions. It does not send
messages, move money, accept settlements, change accounts, or grant general
carrier/vendor communication authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum

from freight.contracts import TruthManifest, VALIDATED, canonical_hash
from freight.engagement_state import EngagementResolution, EngagementState
from freight.pilot_reporting import FindingReview, ReviewDisposition, verify_finding_review


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_VALIDITY_DAYS = 30


class ActionType(str, Enum):
    SUBMIT_DISPUTE = "SUBMIT_DISPUTE"
    REQUEST_CREDIT_REVIEW = "REQUEST_CREDIT_REVIEW"
    REQUEST_DOCUMENTATION = "REQUEST_DOCUMENTATION"
    REQUEST_STATUS = "REQUEST_STATUS"


class AuthorizationState(str, Enum):
    NOT_YET_ACTIVE = "NOT_YET_ACTIVE"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class ExternalActionAuthorization:
    authorization_id: str
    engagement_id: str
    buyer_id: str
    business_unit: str
    engagement_resolution_hash: str
    operative_charter_hash: str
    action_type: str
    target_carrier_id: str
    target_customer_id: str
    recipient_reference_hash: str
    action_payload_hash: str
    finding_ids: tuple[str, ...]
    finding_proof_hashes: tuple[str, ...]
    finding_review_hashes: tuple[str, ...]
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


def _verify_charter(charter: dict, resolution: EngagementResolution) -> None:
    digest = _sha("charter_hash", charter.get("charter_hash"))
    body = {k: v for k, v in charter.items() if k != "charter_hash"}
    if canonical_hash(body) != digest:
        raise ValueError("operative Charter hash mismatch")
    if digest != resolution.operative_charter_hash:
        raise ValueError("operative Charter does not match engagement resolution")
    if (
        charter.get("engagement_id"),
        charter.get("buyer_id"),
        charter.get("business_unit"),
    ) != (
        resolution.engagement_id,
        resolution.buyer_id,
        resolution.business_unit,
    ):
        raise ValueError("operative Charter scope mismatch")
    if charter.get("customer_data_authorized") is not True:
        raise ValueError("operative Charter does not authorize customer-data work")
    if charter.get("external_action_authorized") is not False:
        raise ValueError("operative Charter must not pre-authorize external action")
    _required("buyer_action_approver_role", charter.get("buyer_action_approver_role"))


def _verify_resolution(resolution: EngagementResolution) -> None:
    body = asdict(resolution)
    digest = body.pop("resolution_hash")
    _sha("resolution_hash", digest)
    if canonical_hash(body) != digest:
        raise ValueError("engagement resolution hash mismatch")
    if resolution.engagement_state != EngagementState.ACTIVE.value:
        raise ValueError("external action requires ACTIVE engagement state")
    if not resolution.customer_data_authorized:
        raise ValueError("customer data is not authorized")
    if not resolution.report_generation_allowed:
        raise ValueError("report generation is not authorized")
    if resolution.replacement_required:
        raise ValueError("replacement Charter is required")
    if resolution.external_action_authorized is not False:
        raise ValueError("engagement resolution must not pre-authorize external action")
    if resolution.external_action_policy != "SEPARATE_BUYER_APPROVAL_REQUIRED":
        raise ValueError("unexpected external-action policy")


def _verify_finding_proof(finding) -> None:
    body = {
        "schema": 2,
        "finding_id": finding.finding_id,
        "buyer_id": finding.buyer_id,
        "business_unit": finding.business_unit,
        "invoice_id": finding.invoice_id,
        "shipment_id": finding.shipment_id,
        "customer_id": finding.customer_id,
        "carrier_id": finding.carrier_id,
        "currency": finding.currency,
        "authority_id": finding.authority_id,
        "expected_cents": finding.expected_cents,
        "actual_cents": finding.actual_cents,
        "status": finding.status,
    }
    if canonical_hash(body) != finding.proof_hash:
        raise ValueError("finding proof hash mismatch: " + finding.finding_id)


def _verify_truth(truth: TruthManifest) -> None:
    authority_index = {authority.authority_id: authority for authority in truth.authorities}
    if len(authority_index) != len(truth.authorities):
        raise ValueError("duplicate authority in truth")
    for authority in truth.authorities:
        if (authority.buyer_id, authority.business_unit) != (truth.buyer_id, truth.business_unit):
            raise ValueError("authority scope mismatch in truth")
    for finding in truth.findings:
        _verify_finding_proof(finding)
        if (finding.buyer_id, finding.business_unit) != (truth.buyer_id, truth.business_unit):
            raise ValueError("finding scope mismatch in truth")
        if finding.status == VALIDATED:
            authority = authority_index.get(finding.authority_id or "")
            if authority is None:
                raise ValueError("validated finding authority missing from truth")
            if (authority.customer_id, authority.carrier_id, authority.currency) != (
                finding.customer_id, finding.carrier_id, finding.currency,
            ):
                raise ValueError("validated finding authority identity mismatch")
    body = {
        "schema": 3,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "population_hash": truth.population_hash,
        "authorities": [asdict(authority) for authority in truth.authorities],
        "findings": [asdict(finding) for finding in truth.findings],
    }
    if canonical_hash(body) != truth.truth_hash:
        raise ValueError("truth hash mismatch")


def issue_authorization(
    *,
    resolution: EngagementResolution,
    operative_charter: dict,
    truth: TruthManifest,
    reviews: tuple[FindingReview, ...],
    authorization_id: str,
    action_type: ActionType,
    target_carrier_id: str,
    target_customer_id: str,
    recipient_reference_hash: str,
    action_payload_hash: str,
    finding_ids: tuple[str, ...],
    currency: str,
    authorized_cents: int,
    approver_role: str,
    issued_on: str,
    expires_on: str,
    max_validity_days: int = MAX_VALIDITY_DAYS,
) -> ExternalActionAuthorization:
    _verify_resolution(resolution)
    _verify_charter(operative_charter, resolution)

    _required("authorization_id", authorization_id)
    _required("target_carrier_id", target_carrier_id)
    _required("target_customer_id", target_customer_id)
    _sha("recipient_reference_hash", recipient_reference_hash)
    _sha("action_payload_hash", action_payload_hash)
    _required("currency", currency)
    _required("approver_role", approver_role)

    if approver_role != operative_charter["buyer_action_approver_role"]:
        raise ValueError("approver_role does not match operative Charter")

    if (
        truth.buyer_id,
        truth.business_unit,
    ) != (
        resolution.buyer_id,
        resolution.business_unit,
    ):
        raise ValueError("truth scope mismatch")
    _verify_truth(truth)

    if not finding_ids:
        raise ValueError("at least one finding_id is required")
    normalized_ids = tuple(sorted(finding_ids))
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("duplicate finding_id in authorization")

    finding_index = {f.finding_id: f for f in truth.findings}
    review_index: dict[str, FindingReview] = {}
    for review in reviews:
        if review.finding_id in review_index:
            raise ValueError("duplicate finding review")
        review_index[review.finding_id] = review

    proof_hashes: list[str] = []
    review_hashes: list[str] = []
    validated_total = 0
    for finding_id in normalized_ids:
        finding = finding_index.get(finding_id)
        if finding is None:
            raise ValueError("authorization references unknown finding: " + finding_id)
        _verify_finding_proof(finding)
        if finding.status != VALIDATED or finding.validated_cents <= 0:
            raise ValueError("authorization requires positive VALIDATED finding: " + finding_id)
        review = review_index.get(finding_id)
        if review is None or review.disposition is not ReviewDisposition.CONFIRMED:
            raise ValueError("authorization requires CONFIRMED buyer review: " + finding_id)
        verify_finding_review(review, finding, require_bound=True)
        assert review.review_hash is not None
        review_hashes.append(review.review_hash)
        if finding.carrier_id != target_carrier_id:
            raise ValueError("finding carrier does not match target carrier")
        if finding.customer_id != target_customer_id:
            raise ValueError("finding customer does not match target customer")
        if finding.currency != currency:
            raise ValueError("finding currency mismatch")
        proof_hashes.append(finding.proof_hash)
        validated_total += finding.validated_cents

    if not isinstance(authorized_cents, int) or authorized_cents <= 0:
        raise ValueError("authorized_cents must be a positive integer")
    if authorized_cents > validated_total:
        raise ValueError("authorized_cents cannot exceed selected validated findings")

    issued = _parse_date("issued_on", issued_on)
    expires = _parse_date("expires_on", expires_on)
    if expires < issued:
        raise ValueError("expires_on cannot precede issued_on")
    if max_validity_days < 1:
        raise ValueError("max_validity_days must be positive")
    if (expires - issued).days > max_validity_days:
        raise ValueError("authorization validity exceeds internal maximum")

    body = {
        "authorization_id": authorization_id,
        "engagement_id": resolution.engagement_id,
        "buyer_id": resolution.buyer_id,
        "business_unit": resolution.business_unit,
        "engagement_resolution_hash": resolution.resolution_hash,
        "operative_charter_hash": resolution.operative_charter_hash,
        "action_type": action_type.value,
        "target_carrier_id": target_carrier_id,
        "target_customer_id": target_customer_id,
        "recipient_reference_hash": recipient_reference_hash,
        "action_payload_hash": action_payload_hash,
        "finding_ids": list(normalized_ids),
        "finding_proof_hashes": proof_hashes,
        "finding_review_hashes": review_hashes,
        "currency": currency,
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
    return ExternalActionAuthorization(
        authorization_id=authorization_id,
        engagement_id=resolution.engagement_id,
        buyer_id=resolution.buyer_id,
        business_unit=resolution.business_unit,
        engagement_resolution_hash=resolution.resolution_hash,
        operative_charter_hash=resolution.operative_charter_hash,
        action_type=action_type.value,
        target_carrier_id=target_carrier_id,
        target_customer_id=target_customer_id,
        recipient_reference_hash=recipient_reference_hash,
        action_payload_hash=action_payload_hash,
        finding_ids=normalized_ids,
        finding_proof_hashes=tuple(proof_hashes),
        finding_review_hashes=tuple(review_hashes),
        currency=currency,
        authorized_cents=authorized_cents,
        approver_role=approver_role,
        issued_on=issued_on,
        expires_on=expires_on,
        money_movement_authorized=False,
        settlement_acceptance_authorized=False,
        account_change_authorized=False,
        credential_use_authorized=False,
        general_contact_authorized=False,
        automatic_execution_authorized=False,
        authorization_hash=canonical_hash(body),
    )


def _verify_authorization(auth: ExternalActionAuthorization) -> None:
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


def revoke_authorization(
    auth: ExternalActionAuthorization,
    *,
    revocation_id: str,
    revoked_on: str,
    approver_role: str,
    reason: str,
) -> AuthorizationRevocation:
    _verify_authorization(auth)
    _required("revocation_id", revocation_id)
    _required("reason", reason)
    _required("approver_role", approver_role)
    if approver_role != auth.approver_role:
        raise ValueError("revocation approver_role mismatch")
    revoked = _parse_date("revoked_on", revoked_on)
    issued = _parse_date("issued_on", auth.issued_on)
    if revoked < issued:
        raise ValueError("revoked_on cannot precede issued_on")
    body = {
        "revocation_id": revocation_id,
        "authorization_id": auth.authorization_id,
        "authorization_hash": auth.authorization_hash,
        "revoked_on": revoked_on,
        "approver_role": approver_role,
        "reason": reason,
    }
    return AuthorizationRevocation(
        revocation_id=revocation_id,
        authorization_id=auth.authorization_id,
        authorization_hash=auth.authorization_hash,
        revoked_on=revoked_on,
        approver_role=approver_role,
        reason=reason,
        revocation_hash=canonical_hash(body),
    )


def _verify_revocation(auth: ExternalActionAuthorization, revocation: AuthorizationRevocation) -> None:
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
    auth: ExternalActionAuthorization,
    *,
    as_of_date: str,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> AuthorizationEvaluation:
    _verify_authorization(auth)
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


def assert_action_allowed(
    auth: ExternalActionAuthorization,
    *,
    as_of_date: str,
    action_type: ActionType,
    target_carrier_id: str,
    target_customer_id: str,
    recipient_reference_hash: str,
    action_payload_hash: str,
    finding_ids: tuple[str, ...],
    currency: str,
    requested_cents: int,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> None:
    evaluation = evaluate_authorization(auth, as_of_date=as_of_date, revocations=revocations)
    if not evaluation.action_allowed:
        raise ValueError("authorization is not ACTIVE: " + evaluation.state)
    if action_type.value != auth.action_type:
        raise ValueError("action_type exceeds authorization")
    if target_carrier_id != auth.target_carrier_id:
        raise ValueError("target carrier exceeds authorization")
    if target_customer_id != auth.target_customer_id:
        raise ValueError("target customer exceeds authorization")
    if recipient_reference_hash != auth.recipient_reference_hash:
        raise ValueError("recipient/routing reference exceeds authorization")
    if action_payload_hash != auth.action_payload_hash:
        raise ValueError("action payload exceeds authorization")
    if tuple(sorted(finding_ids)) != auth.finding_ids:
        raise ValueError("finding set exceeds authorization")
    if currency != auth.currency:
        raise ValueError("currency exceeds authorization")
    if not isinstance(requested_cents, int) or requested_cents <= 0:
        raise ValueError("requested_cents must be positive")
    if requested_cents > auth.authorized_cents:
        raise ValueError("requested amount exceeds authorization")


def render_markdown(auth: ExternalActionAuthorization) -> str:
    return "\n".join(
        [
            "# Freight Recovery — External Action Authorization",
            "",
            f"**Authorization:** `{auth.authorization_id}`",
            f"**Engagement:** `{auth.engagement_id}`",
            f"**Action:** {auth.action_type}",
            f"**Target carrier:** `{auth.target_carrier_id}`",
            f"**Target customer:** `{auth.target_customer_id}`",
            f"**Authorized maximum:** {auth.currency} {auth.authorized_cents / 100:,.2f}",
            f"**Issued / expires:** {auth.issued_on} / {auth.expires_on}",
            f"**Approver role:** {auth.approver_role}",
            f"**Authorization hash:** `{auth.authorization_hash}`",
            "",
            "## Exact scope",
            "",
            "- Finding IDs: " + ", ".join(auth.finding_ids),
            "- Buyer review hashes: " + ", ".join(auth.finding_review_hashes),
            f"- Recipient/routing hash: `{auth.recipient_reference_hash}`",
            f"- Action payload hash: `{auth.action_payload_hash}`",
            "",
            "## Explicitly not authorized",
            "",
            "- Money movement: **false**",
            "- Settlement acceptance: **false**",
            "- Account changes: **false**",
            "- Credential use: **false**",
            "- General carrier/vendor contact: **false**",
            "- Automatic execution: **false**",
            "",
            "This artifact authorizes only the enumerated action. It does not execute it.",
            "",
        ]
    )
