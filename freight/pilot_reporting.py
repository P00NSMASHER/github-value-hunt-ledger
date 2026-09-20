"""Pilot reporting derived from frozen Freight Recovery proof objects."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from freight.contracts import IncumbentOutput, RecoveryLedger, TruthManifest, VALIDATED


class ReviewDisposition(str, Enum):
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class FindingReview:
    finding_id: str
    disposition: ReviewDisposition
    reviewer_minutes: int = 0

    def __post_init__(self):
        if self.reviewer_minutes < 0:
            raise ValueError("reviewer_minutes must be non-negative")


@dataclass(frozen=True)
class PilotMetrics:
    reviewed_discrepancy_cents: int
    validated_finding_cents: int
    challenger_only_validated_cents: int
    realized_cents: int
    fee_eligible_realized_cents: int
    false_positive_cents: int
    unresolved_validated_cents: int
    finding_count: int
    validated_finding_count: int
    challenger_only_finding_count: int
    false_positive_count: int
    unresolved_review_count: int
    reviewer_minutes: int

    @property
    def reviewer_hours(self) -> float:
        return round(self.reviewer_minutes / 60, 2)


def _positive_variance(finding) -> int:
    return max(finding.actual_cents - finding.expected_cents, 0)


def build_pilot_metrics(
    truth: TruthManifest,
    incumbent: IncumbentOutput,
    ledger: RecoveryLedger,
    reviews: tuple[FindingReview, ...] = (),
) -> PilotMetrics:
    if incumbent.truth_hash != truth.truth_hash:
        raise ValueError("incumbent output truth hash mismatch")
    if incumbent.population_hash != truth.population_hash:
        raise ValueError("incumbent output population hash mismatch")

    findings = {finding.finding_id: finding for finding in truth.findings}
    incumbent_ids = set(incumbent.finding_ids)

    review_index: dict[str, FindingReview] = {}
    for review in reviews:
        if review.finding_id not in findings:
            raise ValueError("review references unknown finding: " + review.finding_id)
        if review.finding_id in review_index:
            raise ValueError("duplicate review: " + review.finding_id)
        review_index[review.finding_id] = review

    reviewed_discrepancy = sum(_positive_variance(f) for f in findings.values())
    validated = [f for f in findings.values() if f.status == VALIDATED]
    challenger_only = [f for f in validated if f.finding_id not in incumbent_ids]

    validated_cents = sum(f.validated_cents for f in validated)
    challenger_cents = sum(f.validated_cents for f in challenger_only)

    false_positive_cents = 0
    unresolved_validated_cents = 0
    false_positive_count = 0
    unresolved_review_count = 0
    reviewer_minutes = 0

    for review in reviews:
        reviewer_minutes += review.reviewer_minutes
        finding = findings[review.finding_id]
        if review.disposition is ReviewDisposition.FALSE_POSITIVE:
            false_positive_count += 1
            false_positive_cents += finding.validated_cents
        elif review.disposition is ReviewDisposition.UNRESOLVED:
            unresolved_review_count += 1
            unresolved_validated_cents += finding.validated_cents

    certs = [ledger.certificate(finding_id) for finding_id in sorted(findings)]
    realized = sum(cert.realized_cents for cert in certs)
    fee_eligible = sum(cert.fee_eligible_cents for cert in certs)

    if realized > validated_cents:
        raise AssertionError("realized recovery cannot exceed validated findings")
    if fee_eligible > realized:
        raise AssertionError("fee-eligible recovery cannot exceed realized recovery")
    if fee_eligible > challenger_cents:
        raise AssertionError(
            "fee-eligible recovery cannot exceed challenger-only validated findings"
        )

    return PilotMetrics(
        reviewed_discrepancy_cents=reviewed_discrepancy,
        validated_finding_cents=validated_cents,
        challenger_only_validated_cents=challenger_cents,
        realized_cents=realized,
        fee_eligible_realized_cents=fee_eligible,
        false_positive_cents=false_positive_cents,
        unresolved_validated_cents=unresolved_validated_cents,
        finding_count=len(findings),
        validated_finding_count=len(validated),
        challenger_only_finding_count=len(challenger_only),
        false_positive_count=false_positive_count,
        unresolved_review_count=unresolved_review_count,
        reviewer_minutes=reviewer_minutes,
    )


def dollars(cents: int) -> str:
    return "$" + format(cents / 100, ",.2f")


def render_markdown(metrics: PilotMetrics) -> str:
    return "\n".join(
        [
            "# Freight Audit Acceptance Test — Pilot Metrics",
            "",
            "## Financial totals",
            "- Reviewed discrepancy: **" + dollars(metrics.reviewed_discrepancy_cents) + "**",
            "- Validated finding: **" + dollars(metrics.validated_finding_cents) + "**",
            "- Challenger-only validated: **" + dollars(metrics.challenger_only_validated_cents) + "**",
            "- Uniquely attributable realized: **" + dollars(metrics.realized_cents) + "**",
            "- Fee-eligible realized: **" + dollars(metrics.fee_eligible_realized_cents) + "**",
            "",
            "These totals are intentionally non-interchangeable. Discrepancy and validated dollars are not realized savings.",
            "",
            "## Review quality",
            "- Findings: " + str(metrics.finding_count),
            "- Validated findings: " + str(metrics.validated_finding_count),
            "- Challenger-only findings: " + str(metrics.challenger_only_finding_count),
            "- False-positive findings: " + str(metrics.false_positive_count) + " (" + dollars(metrics.false_positive_cents) + ")",
            "- Unresolved reviewed findings: " + str(metrics.unresolved_review_count) + " (" + dollars(metrics.unresolved_validated_cents) + ")",
            "- Reviewer effort: " + str(metrics.reviewer_minutes) + " minutes (" + format(metrics.reviewer_hours, ".2f") + " hours)",
        ]
    ) + "\n"
