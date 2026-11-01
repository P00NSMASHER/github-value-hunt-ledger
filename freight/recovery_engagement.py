"""Machine-checkable handoff from a free audit to recovery execution.

This module records commercial and authorization hooks without pretending to be
an e-signature system or a legal agreement. Potential and approved amounts are
context only. Recovery fees are calculated exclusively from fee-eligible funds
that were actually recovered and supported by settlement evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import re

from freight.commercial_terms import (
    DEFAULT_CONTINGENCY_RECOVERY_RATE,
    calculate_recovery_fee,
    contingency_rate_label,
    normalize_contingency_rate,
)


REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,199}$")


class RecoveryEngagementState(str, Enum):
    READY_FOR_ACCEPTANCE = "READY_FOR_ACCEPTANCE"
    ACCEPTED = "ACCEPTED"


@dataclass(frozen=True)
class RecoveryEngagementRequest:
    engagement_id: str
    audit_reference: str
    buyer_id: str
    business_unit: str
    scope: str
    potential_recovery_low_cents: int
    potential_recovery_high_cents: int
    contingency_rate: Decimal | str | int | float = DEFAULT_CONTINGENCY_RECOVERY_RATE
    recovered_funds_definition: str = ""
    payment_timing: str = ""
    authorization_policy: str = "SEPARATE_ACTION_APPROVAL_REQUIRED"
    confidentiality_terms_reference: str = ""
    data_use_terms_reference: str = ""
    termination_terms_reference: str = ""
    attribution_terms_reference: str = ""
    governing_agreement_reference: str = ""
    buyer_accepted: bool = False
    freight_recovery_accepted: bool = False
    accepted_at: str | None = None


@dataclass(frozen=True)
class RecoveryEngagement:
    state: str
    engagement_id: str
    audit_reference: str
    buyer_id: str
    business_unit: str
    scope: str
    potential_recovery_low_cents: int
    potential_recovery_high_cents: int
    approved_claim_value_cents: int
    actual_recovered_cents: int
    contingency_rate: str
    contingency_rate_label: str
    recovered_funds_definition: str
    payment_timing: str
    authorization_policy: str
    external_action_authorized: bool
    confidentiality_terms_reference: str
    data_use_terms_reference: str
    termination_terms_reference: str
    attribution_terms_reference: str
    governing_agreement_reference: str
    buyer_accepted: bool
    freight_recovery_accepted: bool
    accepted_at: str | None
    engagement_hash: str


@dataclass(frozen=True)
class RecoveryFeeRecord:
    engagement_id: str
    engagement_hash: str
    settlement_evidence_reference: str
    claim_batch_hash: str
    settlement_snapshot_hash: str
    buyer_posting_evidence_reference: str | None
    billing_authorized: bool
    actual_recovered_cents: int
    fee_eligible_recovered_cents: int
    contingency_rate: str
    recovery_fee_cents: int
    customer_net_recovery_cents: int
    recorded_at: str
    record_hash: str


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _reference(name: str, value: str) -> str:
    normalized = _required(name, value)
    if not REFERENCE_RE.fullmatch(normalized):
        raise ValueError(f"{name} must be a stable non-secret reference")
    return normalized


def _money(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer number of cents")
    return value


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValueError("recorded_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("recorded_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _verify_engagement_hash(engagement: RecoveryEngagement) -> None:
    body = asdict(engagement)
    supplied_hash = body.pop("engagement_hash")
    if supplied_hash != _canonical_hash(body):
        raise ValueError("engagement hash does not match the engagement record")


def build_recovery_engagement(request: RecoveryEngagementRequest) -> RecoveryEngagement:
    """Create an acceptance-ready or accepted recovery engagement record."""
    engagement_id = _reference("engagement_id", request.engagement_id)
    audit_reference = _reference("audit_reference", request.audit_reference)
    buyer_id = _reference("buyer_id", request.buyer_id)
    business_unit = _reference("business_unit", request.business_unit)
    scope = _required("scope", request.scope)
    low = _money("potential_recovery_low_cents", request.potential_recovery_low_cents)
    high = _money("potential_recovery_high_cents", request.potential_recovery_high_cents)
    if high < low:
        raise ValueError("potential recovery high value cannot be below the low value")

    rate = normalize_contingency_rate(request.contingency_rate)
    required_term_fields = (
        "recovered_funds_definition",
        "payment_timing",
        "confidentiality_terms_reference",
        "data_use_terms_reference",
        "termination_terms_reference",
        "attribution_terms_reference",
        "governing_agreement_reference",
    )
    normalized_terms: dict[str, str] = {}
    for field in required_term_fields:
        value = getattr(request, field)
        normalized_terms[field] = (
            _reference(field, value) if field.endswith("_reference") else _required(field, value)
        )
    authorization_policy = _required("authorization_policy", request.authorization_policy)

    accepted = request.buyer_accepted and request.freight_recovery_accepted
    if accepted and not request.accepted_at:
        raise ValueError("accepted_at is required when both parties have accepted")
    if request.accepted_at and not accepted:
        raise ValueError("accepted_at cannot be set before both parties accept")
    accepted_at = _canonical_timestamp(request.accepted_at) if request.accepted_at else None
    state = (
        RecoveryEngagementState.ACCEPTED
        if accepted
        else RecoveryEngagementState.READY_FOR_ACCEPTANCE
    )

    body = {
        "state": state.value,
        "engagement_id": engagement_id,
        "audit_reference": audit_reference,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "scope": scope,
        "potential_recovery_low_cents": low,
        "potential_recovery_high_cents": high,
        "approved_claim_value_cents": 0,
        "actual_recovered_cents": 0,
        "contingency_rate": format(rate, "f"),
        "contingency_rate_label": contingency_rate_label(rate),
        "recovered_funds_definition": normalized_terms["recovered_funds_definition"],
        "payment_timing": normalized_terms["payment_timing"],
        "authorization_policy": authorization_policy,
        "external_action_authorized": False,
        "confidentiality_terms_reference": normalized_terms["confidentiality_terms_reference"],
        "data_use_terms_reference": normalized_terms["data_use_terms_reference"],
        "termination_terms_reference": normalized_terms["termination_terms_reference"],
        "attribution_terms_reference": normalized_terms["attribution_terms_reference"],
        "governing_agreement_reference": normalized_terms["governing_agreement_reference"],
        "buyer_accepted": request.buyer_accepted,
        "freight_recovery_accepted": request.freight_recovery_accepted,
        "accepted_at": accepted_at,
    }
    return RecoveryEngagement(**body, engagement_hash=_canonical_hash(body))


def record_actual_recovery(
    engagement: RecoveryEngagement,
    *,
    truth,
    incumbent,
    review_packet,
    review_routing,
    buyer_review,
    claim_batch,
    store,
    recorded_at: str,
    buyer_posting_evidence_reference: str | None = None,
) -> RecoveryFeeRecord:
    """Compute a NON-BILLABLE fee record from the actual claim/settlement proof chain.

    The inputs deliberately include no caller-entered recovered dollar amount.
    The buyer's proof-bound review and claim batch are rebuilt before reading
    the store's current, immutable settlement/reversal snapshot. This record is
    NOT an invoice, a signature verifier, or proof of externally posted funds.
    The buyer's actual credit posting, duplicate-billing controls and commercial
    rights must be independently accepted before any downstream invoice.
    """
    from freight.recovery_claim_workflow import build_recovery_claim_batch
    from freight.settlement_report import (
        assert_report_current, build_persistent_pilot_report,
    )

    _verify_engagement_hash(engagement)
    if engagement.state != RecoveryEngagementState.ACCEPTED.value:
        raise ValueError("recovery fees require an accepted engagement")
    if (engagement.buyer_id, engagement.business_unit) != (
        truth.buyer_id, truth.business_unit
    ):
        raise ValueError("engagement buyer/business-unit scope mismatch")
    if (store.buyer_id, store.business_unit) != (
        truth.buyer_id, truth.business_unit
    ):
        raise ValueError("settlement store scope mismatch")

    # A buyer-level match is insufficient: bind this commercial agreement to
    # exactly the frozen audit truth, preventing reuse across engagements.
    # The TRUTH:<sha256> contract is explicit because a decorative audit label
    # like AUDIT-001 offers no authenticated link to the evidence population.
    if engagement.audit_reference != "TRUTH:" + truth.truth_hash:
        raise ValueError("engagement audit reference does not match frozen truth")
    if not engagement.accepted_at:
        raise ValueError("accepted engagement requires an acceptance timestamp")
    accepted_at = datetime.fromisoformat(engagement.accepted_at.replace("Z", "+00:00"))
    issued_at = datetime.fromisoformat(claim_batch.issued_at.replace("Z", "+00:00"))
    if issued_at < accepted_at:
        raise ValueError("recovery claim issued before engagement acceptance")

    # Rebuild authorization lineage rather than trusting a caller-made hash or
    # a bare claim ID. Confirmed buyer reviews are checked against frozen truth,
    # review packet/routing, incumbent exclusions and claim-issuance chronology.
    independently_derived = build_recovery_claim_batch(
        truth=truth,
        incumbent=incumbent,
        review_packet=review_packet,
        review_routing=review_routing,
        buyer_review=buyer_review,
        issued_at=claim_batch.issued_at,
    )
    if claim_batch != independently_derived:
        raise ValueError("recovery claim batch does not match buyer review proofs")

    report = build_persistent_pilot_report(
        truth, incumbent, store, claim_batch.bindings, buyer_review.finding_reviews,
    )
    # A return or another writer may have changed the store after the snapshot.
    assert_report_current(report, store)

    # Also bind the reconstructed claim batch to the claims actually persisted:
    # recalculating an identical finding with a later issue timestamp must not
    # retroactively authorize a claim already issued before the agreement.
    import json
    persisted_claims = {
        item["claim_id"]: item
        for item in json.loads(report.settlement_snapshot_json)["tables"]["recovery_claims"]
    }
    for claim in claim_batch.claims:
        row = persisted_claims.get(claim.claim_id)
        if row is None or any((
            row["issued_at"] != claim.issued_at,
            row["reference"] != claim.reference,
            row["payer_id"] != claim.payer_id,
            row["payee_id"] != claim.payee_id,
            row["currency"] != claim.currency,
            row["amount_cents"] != claim.amount_cents,
            row["source_hash"] != claim.source_hash,
            bool(row["fee_disqualified"]) != claim.fee_disqualified,
        )):
            raise ValueError("persisted recovery claim does not match authorized issuance")

    fee_eligible = report.metrics.fee_eligible_realized_cents
    realized = report.metrics.realized_cents
    if fee_eligible and not buyer_posting_evidence_reference:
        raise ValueError("positive fee requires a buyer posting evidence reference")
    posting_reference = (
        _reference("buyer_posting_evidence_reference", buyer_posting_evidence_reference)
        if buyer_posting_evidence_reference else None
    )

    # No phantom claim, incumbent-known credit, or missing settlement provenance
    # may become billable through the commercial fee arithmetic.
    confirmed = {item.finding_id: item for item in claim_batch.records}
    for certificate in report.certificates:
        if not certificate.fee_eligible_cents:
            continue
        claim = confirmed.get(certificate.finding_id)
        if (
            claim is None or claim.fee_disqualified
            or claim.finding_proof_hash != certificate.finding_proof_hash
            or not certificate.settlement_proof_hashes
        ):
            raise ValueError("fee-eligible recovery lacks authorized claim proof")

    timestamp = _canonical_timestamp(recorded_at)
    breakdown = calculate_recovery_fee(
        actual_recovered_cents=realized,
        fee_eligible_recovered_cents=fee_eligible,
        contingency_rate=engagement.contingency_rate,
    )
    body = {
        "engagement_id": engagement.engagement_id,
        "engagement_hash": engagement.engagement_hash,
        "settlement_evidence_reference": "PILOTREPORT:" + report.report_hash,
        "claim_batch_hash": claim_batch.batch_hash,
        "settlement_snapshot_hash": report.settlement_snapshot_hash,
        "buyer_posting_evidence_reference": posting_reference,
        "billing_authorized": False,
        "actual_recovered_cents": breakdown.actual_recovered_cents,
        "fee_eligible_recovered_cents": breakdown.fee_eligible_recovered_cents,
        "contingency_rate": format(breakdown.contingency_rate, "f"),
        "recovery_fee_cents": breakdown.recovery_fee_cents,
        "customer_net_recovery_cents": breakdown.customer_net_recovery_cents,
        "recorded_at": timestamp,
    }
    return RecoveryFeeRecord(**body, record_hash=_canonical_hash(body))


def render_engagement_summary(engagement: RecoveryEngagement) -> str:
    """Render a plain-language internal review summary, not contract text."""
    return "\n".join(
        (
            "# Freight Recovery — Recovery Engagement Review",
            "",
            f"**State:** {engagement.state}",
            f"**Engagement:** `{engagement.engagement_id}`",
            f"**Audit reference:** `{engagement.audit_reference}`",
            f"**Contingency rate:** {engagement.contingency_rate_label} of fee-eligible actual recovered funds",
            "**Upfront recovery fee:** $0",
            "**External action authorized by this record:** false",
            "",
            "Potential recovery is planning context. It is not approved claim value or actual recovered cash, and it does not create a fee.",
            "",
            f"**Engagement hash:** `{engagement.engagement_hash}`",
            "",
            "This review record is not an e-signature system, legal advice, or a substitute for the governing agreement.",
            "",
        )
    )
