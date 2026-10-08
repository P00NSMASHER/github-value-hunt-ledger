"""Internal qualification for free freight-recovery audit requests.

The public form collects the inputs but does not expose this routing logic.  A
human may always override the result after reviewing the submitted context.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QualificationState(str, Enum):
    QUALIFIED = "QUALIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    LOW_EXPECTED_RECOVERY = "LOW_EXPECTED_RECOVERY"
    HIGH_PRIORITY_RECOVERY_CANDIDATE = "HIGH_PRIORITY_RECOVERY_CANDIDATE"


@dataclass(frozen=True)
class AuditLeadProfile:
    annual_freight_spend_usd: int
    monthly_shipments: int
    invoice_count: int
    history_months: int
    carrier_count: int
    mode_count: int
    has_invoice_export: bool
    has_rate_authority: bool
    has_shipment_records: bool
    has_payment_evidence: bool
    # None means the prior-auditor status has not been verified.
    previously_audited: bool | None = None
    known_or_suspected_issue: bool = False

    def __post_init__(self):
        for field in (
            "annual_freight_spend_usd",
            "monthly_shipments",
            "invoice_count",
            "history_months",
            "carrier_count",
            "mode_count",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(field + " must be a non-negative integer")
        # Never interpret text such as "false" as evidence being present.
        for field in (
            "has_invoice_export", "has_rate_authority", "has_shipment_records",
            "has_payment_evidence", "previously_audited",
            "known_or_suspected_issue",
        ):
            value = getattr(self, field)
            if field == "previously_audited" and value is None:
                continue  # Unknown stays unqualified until manually resolved.
            if type(value) is not bool:
                raise ValueError(field + " must be a boolean")


@dataclass(frozen=True)
class QualificationDecision:
    state: QualificationState
    reasons: tuple[str, ...]
    recommended_next_step: str


def qualify_free_audit(profile: AuditLeadProfile) -> QualificationDecision:
    reasons: list[str] = []
    core_records = profile.has_invoice_export and profile.has_rate_authority
    corroborating_records = profile.has_shipment_records or profile.has_payment_evidence

    if profile.invoice_count == 0 or profile.history_months == 0 or not profile.has_invoice_export:
        if profile.invoice_count == 0:
            reasons.append("no_invoice_population")
        if profile.history_months == 0:
            reasons.append("no_history_period")
        if not profile.has_invoice_export:
            reasons.append("invoice_export_unavailable")
        return QualificationDecision(
            QualificationState.INSUFFICIENT_DATA,
            tuple(reasons),
            "Request the minimum invoice population and history details before analyst work.",
        )

    # The standard scale-based routes must not silently override an incumbent
    # auditor or already-reviewed population. No incremental recovery is
    # presumed until a human verifies the prior scope and claim entitlement.
    if profile.previously_audited is not False:
        reasons.append(
            "prior_audit_overlap_check" if profile.previously_audited is True
            else "prior_audit_status_unverified"
        )
        if not profile.has_rate_authority:
            reasons.append("rate_authority_needs_review")
        if not corroborating_records:
            reasons.append("supporting_records_need_review")
        return QualificationDecision(
            QualificationState.NEEDS_REVIEW,
            tuple(reasons),
            "Verify prior audit status, open claims and incumbent rights before substantive work.",
        )

    # High spending does not identify a claimable shipment. The client must
    # identify a freight mode and at least one billed carrier before the
    # economic-scale fast paths can classify a prospect as qualified.
    scope_reasons = []
    if profile.mode_count == 0:
        scope_reasons.append("freight_mode_unidentified")
    if profile.carrier_count == 0:
        scope_reasons.append("carrier_identity_unidentified")
    if scope_reasons:
        if not profile.has_rate_authority:
            scope_reasons.append("rate_authority_needs_review")
        if not corroborating_records:
            scope_reasons.append("supporting_records_need_review")
        return QualificationDecision(
            QualificationState.NEEDS_REVIEW,
            tuple(scope_reasons),
            "Identify a freight mode, billed carrier and governing documents before qualifying any pilot.",
        )

    scaled = profile.annual_freight_spend_usd >= 1_000_000 or profile.monthly_shipments >= 250
    large_scale = (
        profile.annual_freight_spend_usd >= 5_000_000
        or profile.monthly_shipments >= 1_000
        or profile.invoice_count >= 2_500
    )
    ready = core_records and corroborating_records and profile.history_months >= 3

    if large_scale and ready and (profile.known_or_suspected_issue or profile.carrier_count >= 2):
        reasons.extend(("large_recoverable_population", "records_ready"))
        return QualificationDecision(
            QualificationState.HIGH_PRIORITY_RECOVERY_CANDIDATE,
            tuple(reasons),
            "Prioritize scope confirmation and an approved secure intake route.",
        )

    if scaled and ready:
        reasons.extend(("economically_relevant_scale", "records_ready"))
        return QualificationDecision(
            QualificationState.QUALIFIED,
            tuple(reasons),
            "Confirm scope and issue an approved secure intake route.",
        )

    if (
        profile.annual_freight_spend_usd < 250_000
        and profile.monthly_shipments < 50
        and profile.invoice_count < 100
        and not profile.known_or_suspected_issue
    ):
        reasons.append("small_population_without_known_issue")
        return QualificationDecision(
            QualificationState.LOW_EXPECTED_RECOVERY,
            tuple(reasons),
            "Use a lightweight review queue and avoid open-ended analyst work.",
        )

    if not profile.has_rate_authority:
        reasons.append("rate_authority_needs_review")
    if not corroborating_records:
        reasons.append("supporting_records_need_review")
    if not reasons:
        reasons.append("manual_economic_review")
    return QualificationDecision(
        QualificationState.NEEDS_REVIEW,
        tuple(reasons),
        "Review data readiness and likely recovery value before approving upload.",
    )
