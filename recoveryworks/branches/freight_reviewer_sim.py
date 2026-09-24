"""Deterministic simulated-human review gate for freight evidence packets.

This is not a claim that software is a human reviewer. It is an explicit
simulation of the checklist a careful freight analyst should be able to execute
from the packet alone.

The central release question is:
Can a reviewer reach the correct disposition from the packet without manually
reconstructing the shipment from systems outside the packet?

For VALIDATED cases that means independently checking identity, exact arithmetic,
controlling authority, source evidence, and absence of blockers.
For REVIEW cases it means independently verifying why the case must remain
blocked/remediation-only without reconstructing or approving the dollars.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Iterable

from recoveryworks.models import FindingState, canonical_hash

from .freight_case import (
    FreightReviewCase,
    FreightReviewPacket,
    RESOLVE_AUTHORITY,
    RESOLVE_SOURCE_INTEGRITY,
    REVIEW_VALIDATED_CANDIDATE,
)
from .freight_validation import (
    FreightAdversarialScenario,
    adversarial_scenarios,
    build_adversarial_packet,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

VERIFIED_SELF_CONTAINED = "VERIFIED_SELF_CONTAINED"
BLOCKED_SELF_CONTAINED = "BLOCKED_SELF_CONTAINED"
NO_MONEY_CASE_SELF_CONTAINED = "NO_MONEY_CASE_SELF_CONTAINED"
NOT_SELF_CONTAINED = "NOT_SELF_CONTAINED"

GO = "GO"
NO_GO = "NO_GO"


@dataclass(frozen=True)
class SimulatedReviewerCheck:
    check_id: str
    passed: bool
    observation: str
    check_hash: str


@dataclass(frozen=True)
class SimulatedCaseReview:
    case_id: str
    finding_id: str
    state: str
    verdict: str
    manual_reconstruction_required: bool
    checks: tuple[SimulatedReviewerCheck, ...]
    failed_check_ids: tuple[str, ...]
    review_hash: str


@dataclass(frozen=True)
class SimulatedPacketReview:
    scenario_id: str
    packet_hash: str
    packet_verdict: str
    case_count: int
    reviewed_case_count: int
    self_contained_case_count: int
    manual_reconstruction_case_count: int
    no_money_packet: bool
    supplemental_finding_count: int
    checks: tuple[SimulatedReviewerCheck, ...]
    case_reviews: tuple[SimulatedCaseReview, ...]
    review_hash: str


@dataclass(frozen=True)
class SimulatedHumanReleaseGate:
    scenario_count: int
    packet_review_count: int
    case_count: int
    validated_case_count: int
    review_case_count: int
    no_money_packet_count: int
    self_contained_case_count: int
    manual_reconstruction_case_count: int
    failed_case_count: int
    failed_packet_count: int
    release_gate: str
    required_self_contained_rate: float
    actual_self_contained_rate: float
    packet_reviews: tuple[SimulatedPacketReview, ...]
    gate_hash: str


def _check(check_id: str, passed: bool, observation: str) -> SimulatedReviewerCheck:
    body = {
        "schema": 1,
        "check_id": check_id,
        "passed": bool(passed),
        "observation": observation,
    }
    return SimulatedReviewerCheck(
        check_id=check_id,
        passed=bool(passed),
        observation=observation,
        check_hash=canonical_hash(body),
    )


def _iso_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _authority_covers_service_day(case: FreightReviewCase) -> bool:
    if case.authority is None:
        return False
    service = _iso_day(case.service_date)
    start = _iso_day(case.authority.effective_from)
    end = _iso_day(case.authority.effective_to) if case.authority.effective_to else None
    if service is None or start is None:
        return False
    return start <= service and (end is None or service <= end)


def _source_evidence(case: FreightReviewCase):
    return tuple(item for item in case.evidence if item.role == "SOURCE_DOCUMENT")


def _authority_evidence(case: FreightReviewCase):
    return tuple(item for item in case.evidence if item.role == "AUTHORITY")


def _detector_evidence(case: FreightReviewCase):
    return tuple(item for item in case.evidence if item.role == "DETECTOR_OUTPUT")


def _identity_checks(case: FreightReviewCase) -> tuple[SimulatedReviewerCheck, ...]:
    return (
        _check(
            "IDENTITY_INVOICE",
            bool(case.invoice_number),
            f"Invoice identity is {case.invoice_number or 'missing'}.",
        ),
        _check(
            "IDENTITY_LOAD",
            bool(case.load_id),
            f"Load identity is {case.load_id or 'missing'}.",
        ),
        _check(
            "IDENTITY_CARRIER",
            bool(case.invoice_carrier_name or case.counterparty_id),
            "Carrier/counterparty identity is present."
            if (case.invoice_carrier_name or case.counterparty_id)
            else "Carrier/counterparty identity is missing.",
        ),
        _check(
            "IDENTITY_LANE",
            bool(case.origin and case.destination),
            (
                f"Lane is {case.origin} -> {case.destination}."
                if case.origin and case.destination
                else "Origin/destination lane is incomplete."
            ),
        ),
        _check(
            "IDENTITY_SERVICE_DATE",
            _iso_day(case.service_date) is not None,
            f"Service date is {case.service_date or 'missing/invalid'}.",
        ),
        _check(
            "IDENTITY_CHARGE",
            bool(case.finding_type and case.normalized_category),
            (
                f"Charge context is {case.finding_type}/{case.normalized_category}."
                if case.finding_type and case.normalized_category
                else "Charge type/category is incomplete."
            ),
        ),
    )


def _evidence_checks(case: FreightReviewCase) -> tuple[SimulatedReviewerCheck, ...]:
    source = _source_evidence(case)
    authority = _authority_evidence(case)
    detector = _detector_evidence(case)
    all_evidence = case.evidence
    return (
        _check(
            "EVIDENCE_DETECTOR",
            len(detector) == 1 and detector[0].verified,
            f"Detector evidence count={len(detector)}; verified={all(x.verified for x in detector)}.",
        ),
        _check(
            "EVIDENCE_SOURCE_DOCUMENTS",
            len(source) >= 1 and all(item.verified for item in source),
            f"Verified source-document evidence count={sum(item.verified for item in source)}/{len(source)}.",
        ),
        _check(
            "EVIDENCE_LOCATORS",
            bool(all_evidence) and all(bool(item.locator) for item in all_evidence),
            "Every attached evidence item has a locator."
            if all_evidence and all(item.locator for item in all_evidence)
            else "At least one attached evidence item lacks a locator.",
        ),
        _check(
            "EVIDENCE_HASHES",
            bool(all_evidence) and all(_SHA256_RE.fullmatch(item.source_hash) for item in all_evidence),
            "Every attached evidence item carries a canonical SHA-256."
            if all_evidence and all(_SHA256_RE.fullmatch(item.source_hash) for item in all_evidence)
            else "At least one evidence hash is missing or malformed.",
        ),
        _check(
            "EVIDENCE_AUTHORITY",
            (
                bool(authority) and all(item.verified for item in authority)
                if case.state == FindingState.VALIDATED.value
                else True
            ),
            (
                f"Verified authority evidence count={sum(item.verified for item in authority)}/{len(authority)}."
                if case.state == FindingState.VALIDATED.value
                else "Authority evidence is not required to approve REVIEW dollars; the case remains blocked."
            ),
        ),
    )


def _validated_checks(case: FreightReviewCase) -> tuple[SimulatedReviewerCheck, ...]:
    calc = case.calculation
    arithmetic_ok = (
        calc.component_billed_cents is not None
        and calc.component_expected_cents is not None
        and calc.component_billed_cents - calc.component_expected_cents
        == calc.candidate_recovery_cents
        and calc.candidate_recovery_cents > 0
    )
    authority = case.authority
    return (
        _check(
            "CALC_EXACT",
            arithmetic_ok,
            (
                f"{calc.component_billed_cents} - {calc.component_expected_cents} = "
                f"{calc.candidate_recovery_cents} cents."
                if arithmetic_ok
                else "Exact component billed-vs-expected arithmetic is not reproducible from the packet."
            ),
        ),
        _check(
            "AUTHORITY_ATTACHED",
            authority is not None and authority.verified_controlling,
            "A verified controlling authority is attached."
            if authority is not None and authority.verified_controlling
            else "Verified controlling authority is missing.",
        ),
        _check(
            "AUTHORITY_SOURCE_HASH",
            (
                authority is not None
                and _SHA256_RE.fullmatch(authority.source_hash) is not None
                and (
                    authority.authority_document_source_hash is None
                    or _SHA256_RE.fullmatch(authority.authority_document_source_hash) is not None
                )
            ),
            "Authority source hashes are canonical."
            if authority is not None
            else "Authority source hashes cannot be checked because authority is missing.",
        ),
        _check(
            "AUTHORITY_EFFECTIVE_DATE",
            _authority_covers_service_day(case),
            (
                f"Authority effective window covers service date {case.service_date}."
                if _authority_covers_service_day(case)
                else "Authority effective window cannot be shown to cover the service date."
            ),
        ),
        _check(
            "NO_BLOCKERS",
            not case.integrity_blockers and not case.authority_blockers,
            "No integrity or authority blockers remain."
            if not case.integrity_blockers and not case.authority_blockers
            else "Integrity or authority blockers remain.",
        ),
        _check(
            "VALIDATED_ACTION_HINT",
            case.action_hint == REVIEW_VALIDATED_CANDIDATE,
            f"Action hint is {case.action_hint}.",
        ),
    )


def _review_checks(case: FreightReviewCase) -> tuple[SimulatedReviewerCheck, ...]:
    blockers = tuple(case.integrity_blockers) + tuple(case.authority_blockers)
    expected_action = (
        RESOLVE_SOURCE_INTEGRITY
        if case.integrity_blockers
        else RESOLVE_AUTHORITY
    )
    return (
        _check(
            "REVIEW_BLOCKER_VISIBLE",
            bool(blockers),
            (
                "Visible blocker(s): " + ", ".join(blockers)
                if blockers
                else "No explicit blocker explains why this case is REVIEW."
            ),
        ),
        _check(
            "REVIEW_ACTION_HINT",
            case.action_hint == expected_action,
            f"Action hint is {case.action_hint}; expected {expected_action}.",
        ),
        _check(
            "REVIEW_NOT_PROMOTED",
            case.authority is None,
            "No controlling authority is attached to the blocked case."
            if case.authority is None
            else "A controlling authority is attached even though the case remains blocked.",
        ),
        _check(
            "REVIEW_DOLLARS_NOT_VALIDATED",
            case.state == FindingState.REVIEW.value,
            f"Case state is {case.state}.",
        ),
    )


def _boundary_checks(case: FreightReviewCase) -> tuple[SimulatedReviewerCheck, ...]:
    return (
        _check(
            "NO_EXTERNAL_ACTION",
            case.external_action_allowed is False,
            "Packet does not authorize external action."
            if case.external_action_allowed is False
            else "Packet incorrectly allows external action.",
        ),
        _check(
            "NO_REALIZED_RECOVERY_CLAIM",
            case.realized_recovery_asserted is False,
            "Packet does not claim realized recovery."
            if case.realized_recovery_asserted is False
            else "Packet incorrectly claims realized recovery.",
        ),
    )


def simulate_human_case_review(case: FreightReviewCase) -> SimulatedCaseReview:
    """Simulate the explicit checklist a careful freight reviewer would execute."""
    checks = list(_identity_checks(case))
    checks.extend(_evidence_checks(case))
    if case.state == FindingState.VALIDATED.value:
        checks.extend(_validated_checks(case))
    else:
        checks.extend(_review_checks(case))
    checks.extend(_boundary_checks(case))

    failed = tuple(item.check_id for item in checks if not item.passed)
    if failed:
        verdict = NOT_SELF_CONTAINED
        manual = True
    elif case.state == FindingState.VALIDATED.value:
        verdict = VERIFIED_SELF_CONTAINED
        manual = False
    else:
        verdict = BLOCKED_SELF_CONTAINED
        manual = False

    body = {
        "schema": 1,
        "case_id": case.case_id,
        "finding_id": case.finding_id,
        "state": case.state,
        "verdict": verdict,
        "manual_reconstruction_required": manual,
        "check_hashes": [item.check_hash for item in checks],
        "failed_check_ids": list(failed),
    }
    return SimulatedCaseReview(
        case_id=case.case_id,
        finding_id=case.finding_id,
        state=case.state,
        verdict=verdict,
        manual_reconstruction_required=manual,
        checks=tuple(checks),
        failed_check_ids=failed,
        review_hash=canonical_hash(body),
    )


def simulate_human_packet_review(
    scenario_id: str,
    packet: FreightReviewPacket,
) -> SimulatedPacketReview:
    """Review one packet as a simulated human, including no-money packets."""
    case_reviews = tuple(simulate_human_case_review(case) for case in packet.cases)
    packet_checks: list[SimulatedReviewerCheck] = []

    packet_checks.append(_check(
        "PACKET_HASH",
        _SHA256_RE.fullmatch(packet.packet_hash) is not None,
        "Packet carries a canonical content hash.",
    ))
    packet_checks.append(_check(
        "PACKET_TOTALS",
        (
            packet.candidate_recovery_cents
            == packet.validated_candidate_cents + packet.review_candidate_cents
        ),
        (
            f"Candidate={packet.candidate_recovery_cents}; "
            f"validated={packet.validated_candidate_cents}; "
            f"review={packet.review_candidate_cents}."
        ),
    ))
    packet_checks.append(_check(
        "PACKET_BOUNDARY",
        all(
            not case.external_action_allowed and not case.realized_recovery_asserted
            for case in packet.cases
        ),
        "No case authorizes action or asserts realized recovery.",
    ))

    no_money_packet = packet.case_count == 0
    if no_money_packet:
        packet_checks.append(_check(
            "NO_MONEY_TOTAL",
            (
                packet.candidate_recovery_cents == 0
                and packet.validated_candidate_cents == 0
                and packet.review_candidate_cents == 0
            ),
            "No-money packet carries zero candidate, validated, and review dollars.",
        ))
        packet_checks.append(_check(
            "NO_MONEY_CONTEXT",
            bool(packet.supplemental_findings),
            (
                f"Supplemental context count={len(packet.supplemental_findings)}."
                if packet.supplemental_findings
                else "No supplemental context explains the no-money result."
            ),
        ))

    failed_packet_checks = [item.check_id for item in packet_checks if not item.passed]
    failed_cases = [item for item in case_reviews if item.manual_reconstruction_required]

    if failed_packet_checks or failed_cases:
        verdict = NOT_SELF_CONTAINED
    elif no_money_packet:
        verdict = NO_MONEY_CASE_SELF_CONTAINED
    else:
        verdict = VERIFIED_SELF_CONTAINED

    body = {
        "schema": 1,
        "scenario_id": scenario_id,
        "packet_hash": packet.packet_hash,
        "packet_verdict": verdict,
        "case_review_hashes": [item.review_hash for item in case_reviews],
        "packet_check_hashes": [item.check_hash for item in packet_checks],
    }
    return SimulatedPacketReview(
        scenario_id=scenario_id,
        packet_hash=packet.packet_hash,
        packet_verdict=verdict,
        case_count=packet.case_count,
        reviewed_case_count=len(case_reviews),
        self_contained_case_count=sum(
            not item.manual_reconstruction_required for item in case_reviews
        ),
        manual_reconstruction_case_count=sum(
            item.manual_reconstruction_required for item in case_reviews
        ),
        no_money_packet=no_money_packet,
        supplemental_finding_count=packet.supplemental_finding_count,
        checks=tuple(packet_checks),
        case_reviews=case_reviews,
        review_hash=canonical_hash(body),
    )


def run_simulated_human_release_gate(
    scenarios: Iterable[FreightAdversarialScenario] | None = None,
    *,
    required_self_contained_rate: float = 1.0,
) -> SimulatedHumanReleaseGate:
    """Run the simulated reviewer over the frozen adversarial validation matrix."""
    if not 0.0 <= required_self_contained_rate <= 1.0:
        raise ValueError("required_self_contained_rate must be between 0 and 1")

    frozen = tuple(scenarios or adversarial_scenarios())
    packet_reviews = []
    for scenario in frozen:
        _mapping, _findings, packet = build_adversarial_packet(scenario)
        packet_reviews.append(
            simulate_human_packet_review(scenario.scenario_id, packet)
        )
    reviews = tuple(packet_reviews)
    case_reviews = tuple(
        case_review
        for packet_review in reviews
        for case_review in packet_review.case_reviews
    )

    case_count = len(case_reviews)
    self_contained = sum(
        not item.manual_reconstruction_required for item in case_reviews
    )
    actual_rate = self_contained / case_count if case_count else 1.0
    failed_packets = sum(
        item.packet_verdict == NOT_SELF_CONTAINED for item in reviews
    )
    failed_cases = sum(
        item.manual_reconstruction_required for item in case_reviews
    )
    release = (
        GO
        if (
            actual_rate >= required_self_contained_rate
            and failed_packets == 0
            and failed_cases == 0
        )
        else NO_GO
    )

    body = {
        "schema": 1,
        "scenario_ids": [item.scenario_id for item in frozen],
        "packet_review_hashes": [item.review_hash for item in reviews],
        "required_self_contained_rate": required_self_contained_rate,
        "actual_self_contained_rate": actual_rate,
        "release_gate": release,
    }
    return SimulatedHumanReleaseGate(
        scenario_count=len(frozen),
        packet_review_count=len(reviews),
        case_count=case_count,
        validated_case_count=sum(
            item.state == FindingState.VALIDATED.value for item in case_reviews
        ),
        review_case_count=sum(
            item.state == FindingState.REVIEW.value for item in case_reviews
        ),
        no_money_packet_count=sum(item.no_money_packet for item in reviews),
        self_contained_case_count=self_contained,
        manual_reconstruction_case_count=failed_cases,
        failed_case_count=failed_cases,
        failed_packet_count=failed_packets,
        release_gate=release,
        required_self_contained_rate=required_self_contained_rate,
        actual_self_contained_rate=actual_rate,
        packet_reviews=reviews,
        gate_hash=canonical_hash(body),
    )


def render_simulated_human_gate_markdown(
    gate: SimulatedHumanReleaseGate,
) -> str:
    lines = [
        "# RecoveryOS Freight — Simulated Human Reviewer Gate",
        "",
        f"- Release gate: **{gate.release_gate}**",
        f"- Scenarios reviewed: **{gate.scenario_count}**",
        f"- Money-bearing cases reviewed: **{gate.case_count}**",
        f"- Validated cases: **{gate.validated_case_count}**",
        f"- Review/remediation cases: **{gate.review_case_count}**",
        f"- No-money packets: **{gate.no_money_packet_count}**",
        f"- Self-contained cases: **{gate.self_contained_case_count}/{gate.case_count}**",
        f"- Manual reconstruction required: **{gate.manual_reconstruction_case_count}**",
        f"- Required self-contained rate: **{gate.required_self_contained_rate:.0%}**",
        f"- Actual self-contained rate: **{gate.actual_self_contained_rate:.0%}**",
        f"- Gate hash: `{gate.gate_hash}`",
        "",
        "This is a deterministic simulation of a human review checklist, not a real human sign-off.",
        "",
    ]
    for packet in gate.packet_reviews:
        lines.extend([
            f"## {packet.scenario_id} — {packet.packet_verdict}",
            f"- Packet: `{packet.packet_hash}`",
            f"- Cases: **{packet.case_count}**",
            f"- Supplemental findings: **{packet.supplemental_finding_count}**",
        ])
        for case in packet.case_reviews:
            lines.extend([
                f"- Case `{case.case_id}`: **{case.verdict}**",
                (
                    "  - Manual reconstruction required: **yes**"
                    if case.manual_reconstruction_required
                    else "  - Manual reconstruction required: **no**"
                ),
            ])
            if case.failed_check_ids:
                lines.append(
                    "  - Failed checks: **" + ", ".join(case.failed_check_ids) + "**"
                )
        lines.append("")
    return "\\n".join(lines)


__all__ = [
    "BLOCKED_SELF_CONTAINED",
    "GO",
    "NO_GO",
    "NO_MONEY_CASE_SELF_CONTAINED",
    "NOT_SELF_CONTAINED",
    "SimulatedCaseReview",
    "SimulatedHumanReleaseGate",
    "SimulatedPacketReview",
    "SimulatedReviewerCheck",
    "VERIFIED_SELF_CONTAINED",
    "render_simulated_human_gate_markdown",
    "run_simulated_human_release_gate",
    "simulate_human_case_review",
    "simulate_human_packet_review",
]
