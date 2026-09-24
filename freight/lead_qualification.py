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
    previously_audited: bool = False
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
    if profile.previously_audited:
        reasons.append("prior_audit_overlap_check")
    if not reasons:
        reasons.append("manual_economic_review")
    return QualificationDecision(
        QualificationState.NEEDS_REVIEW,
        tuple(reasons),
        "Review data readiness and likely recovery value before approving upload.",
    )
