"""InsuranceRecovery reviewed commercial/property claim reconciliation.

This branch does not autonomously determine coverage, valuation, causation, or
policy interpretation. A separately reviewed coverage assessment establishes the
expected net payment for a claim line; verified settlement evidence establishes
what the insurer actually paid.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def normalize_coverage_category(value: str) -> str:
    return _required("coverage_category", value).upper().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class InsuranceClaimLine:
    claim_line_id: str
    claimant_id: str
    insurer_id: str
    policy_id: str
    loss_date: str
    coverage_category: str
    claimed_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "claim_line_id", "claimant_id", "insurer_id", "policy_id",
            "loss_date", "coverage_category", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("loss_date", self.loss_date)
        normalize_coverage_category(self.coverage_category)
        _cents("claimed_cents", self.claimed_cents)
        if self.claimed_cents <= 0:
            raise ValueError("claimed_cents must be positive")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_coverage_category(self) -> str:
        return normalize_coverage_category(self.coverage_category)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"insurance-claim:{self.claim_line_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="insurance_claim_line",
            verified=self.verified,
            metadata={
                "claimant_id": self.claimant_id,
                "insurer_id": self.insurer_id,
                "policy_id": self.policy_id,
                "loss_date": self.loss_date,
                "coverage_category": self.normalized_coverage_category,
                "claimed_cents": self.claimed_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class InsuranceCoverageAssessment:
    assessment_id: str
    claim_line_id: str
    policy_id: str
    loss_date: str
    coverage_category: str
    expected_net_payment_cents: int
    coverage_basis: str
    policy_effective_from: str
    policy_effective_to: str | None
    source_hash: str
    source_locator: str
    verified: bool
    policy_snapshot_date: str | None = None
    qualified_reviewer_id: str | None = None
    qualification_basis: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "assessment_id", "claim_line_id", "policy_id", "loss_date",
            "coverage_category", "coverage_basis", "policy_effective_from",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        loss = _iso_date("loss_date", self.loss_date)
        start = _iso_date("policy_effective_from", self.policy_effective_from)
        end = (
            _iso_date("policy_effective_to", self.policy_effective_to)
            if self.policy_effective_to is not None
            else None
        )
        if end is not None and end < start:
            raise ValueError("policy_effective_to cannot precede policy_effective_from")
        if loss < start or (end is not None and loss > end):
            raise ValueError("loss_date is outside reviewed policy effective period")
        normalize_coverage_category(self.coverage_category)
        _cents("expected_net_payment_cents", self.expected_net_payment_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.policy_snapshot_date is not None:
            _iso_date("policy_snapshot_date", self.policy_snapshot_date)
        if self.verified:
            if not (
                isinstance(self.qualified_reviewer_id, str)
                and self.qualified_reviewer_id.strip()
            ):
                raise ValueError(
                    "verified insurance assessment requires qualified_reviewer_id"
                )
            if not (
                isinstance(self.qualification_basis, str)
                and self.qualification_basis.strip()
            ):
                raise ValueError(
                    "verified insurance assessment requires qualification_basis"
                )
            if not (
                isinstance(self.policy_snapshot_date, str)
                and self.policy_snapshot_date.strip()
            ):
                raise ValueError(
                    "verified insurance assessment requires policy_snapshot_date"
                )

    @property
    def normalized_coverage_category(self) -> str:
        return normalize_coverage_category(self.coverage_category)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "assessment_id": self.assessment_id,
            "claim_line_id": self.claim_line_id,
            "policy_id": self.policy_id,
            "loss_date": self.loss_date,
            "coverage_category": self.normalized_coverage_category,
            "expected_net_payment_cents": self.expected_net_payment_cents,
            "coverage_basis": self.coverage_basis,
            "policy_effective_from": self.policy_effective_from,
            "policy_effective_to": self.policy_effective_to,
            "source_hash": self.source_hash,
            "policy_snapshot_date": self.policy_snapshot_date,
            "qualified_reviewer_id": self.qualified_reviewer_id,
            "qualification_basis": self.qualification_basis,
        }
        return RuleRef(
            rule_id="insurance-assessment:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.policy_effective_from,
            effective_to=self.policy_effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "reviewed_insurance_coverage_assessment",
                "assessment_id": self.assessment_id,
                "claim_line_id": self.claim_line_id,
                "policy_id": self.policy_id,
                "loss_date": self.loss_date,
                "coverage_category": self.normalized_coverage_category,
                "expected_net_payment_cents": self.expected_net_payment_cents,
                "coverage_basis": self.coverage_basis,
                "policy_snapshot_date": self.policy_snapshot_date,
                "qualified_reviewer_id": self.qualified_reviewer_id,
                "qualification_basis": self.qualification_basis,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class InsuranceSettlement:
    settlement_id: str
    claim_line_id: str
    amount_paid_cents: int
    payment_date: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "settlement_id", "claim_line_id", "payment_date",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("payment_date", self.payment_date)
        _cents("amount_paid_cents", self.amount_paid_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"insurance-settlement:{self.settlement_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="insurance_settlement",
            verified=self.verified,
            metadata={
                "claim_line_id": self.claim_line_id,
                "payment_date": self.payment_date,
                "amount_paid_cents": self.amount_paid_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class InsuranceAuditException:
    claim_line_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class InsuranceAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[InsuranceAuditException, ...]


def audit_insurance_claims(
    *,
    client_id: str,
    claim_lines: Iterable[InsuranceClaimLine],
    assessments: Iterable[InsuranceCoverageAssessment],
    settlements: Iterable[InsuranceSettlement],
    currency: str = "USD",
) -> InsuranceAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    line_groups: dict[str, list[InsuranceClaimLine]] = defaultdict(list)
    for line in claim_lines:
        line_groups[line.claim_line_id].append(line)

    assessment_groups: dict[str, list[InsuranceCoverageAssessment]] = defaultdict(list)
    for assessment in assessments:
        assessment_groups[assessment.claim_line_id].append(assessment)

    settlement_groups: dict[str, list[InsuranceSettlement]] = defaultdict(list)
    settlement_id_counts: dict[str, int] = defaultdict(int)
    for settlement in settlements:
        settlement_groups[settlement.claim_line_id].append(settlement)
        settlement_id_counts[settlement.settlement_id] += 1

    duplicate_settlement_ids = {
        settlement_id
        for settlement_id, count in settlement_id_counts.items()
        if count > 1
    }

    observations: list[RecoveryObservation] = []
    exceptions: list[InsuranceAuditException] = []

    for settlement_id in sorted(duplicate_settlement_ids):
        exceptions.append(InsuranceAuditException(
            settlement_id,
            "DUPLICATE_INSURANCE_SETTLEMENT_ID",
            (
                f"settlement_id appears {settlement_id_counts[settlement_id]} times; "
                "affected claim lines are excluded"
            ),
        ))

    for claim_line_id in sorted(line_groups):
        lines = line_groups[claim_line_id]
        if len(lines) != 1:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "DUPLICATE_INSURANCE_CLAIM_LINE_ID",
                f"claim_line_id appears {len(lines)} times; excluded",
            ))
            continue
        line = lines[0]

        if line.claimant_id != client_id:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "INSURANCE_CLAIMANT_SCOPE_MISMATCH",
                "claimant_id does not match Scan 360 client_id",
            ))
            continue

        assessments_for_line = assessment_groups.get(claim_line_id, [])
        if not assessments_for_line:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "NO_REVIEWED_COVERAGE_ASSESSMENT",
                "no reviewed expected coverage assessment is bound to this claim line",
            ))
            continue
        if len(assessments_for_line) != 1:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "CONFLICTING_COVERAGE_ASSESSMENTS",
                f"{len(assessments_for_line)} assessments are bound to this claim line",
            ))
            continue
        assessment = assessments_for_line[0]

        mismatches: list[str] = []
        if assessment.policy_id != line.policy_id:
            mismatches.append("policy_id")
        if assessment.loss_date != line.loss_date:
            mismatches.append("loss_date")
        if assessment.normalized_coverage_category != line.normalized_coverage_category:
            mismatches.append("coverage_category")
        if mismatches:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "COVERAGE_ASSESSMENT_IDENTITY_MISMATCH",
                "assessment differs from claim line on: " + ", ".join(mismatches),
            ))
            continue

        if assessment.expected_net_payment_cents > line.claimed_cents:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "EXPECTED_PAYMENT_EXCEEDS_CLAIMED",
                "reviewed expected net payment exceeds supplied claimed amount",
            ))
            continue

        settlements_for_line = settlement_groups.get(claim_line_id, [])
        if not settlements_for_line:
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "NO_INSURANCE_SETTLEMENT_EVIDENCE",
                "actual insurer payment cannot be established",
            ))
            continue
        if any(
            settlement.settlement_id in duplicate_settlement_ids
            for settlement in settlements_for_line
        ):
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "CLAIM_BLOCKED_BY_DUPLICATE_SETTLEMENT",
                "duplicate settlement IDs prevent reliable received-payment calculation",
            ))
            continue
        if any(
            _iso_date("payment_date", settlement.payment_date)
            < _iso_date("loss_date", line.loss_date)
            for settlement in settlements_for_line
        ):
            exceptions.append(InsuranceAuditException(
                claim_line_id,
                "SETTLEMENT_PRECEDES_LOSS",
                "settlement evidence predates the loss date",
            ))
            continue

        actual_cents = sum(s.amount_paid_cents for s in settlements_for_line)
        if assessment.expected_net_payment_cents <= actual_cents:
            continue

        evidence = (
            line.evidence(),
            *tuple(
                settlement.evidence()
                for settlement in sorted(
                    settlements_for_line, key=lambda item: item.settlement_id
                )
            ),
        )
        fully_verified = assessment.verified and all(ref.verified for ref in evidence)

        observations.append(RecoveryObservation(
            branch=Branch.INSURANCE,
            client_id=client_id,
            counterparty_id=line.insurer_id,
            reference=line.claim_line_id,
            currency=currency,
            expected_cents=assessment.expected_net_payment_cents,
            actual_cents=actual_cents,
            rule=assessment.rule_ref(),
            evidence=evidence,
            reason="INSURANCE_CLAIM_UNDERPAYMENT",
            confidence_basis=(
                "verified claim + professionally reviewed policy assessment + settlement evidence"
                if fully_verified
                else "claim/coverage/settlement evidence requires verification"
            ),
            metadata={
                "policy_id": line.policy_id,
                "loss_date": line.loss_date,
                "coverage_category": line.normalized_coverage_category,
                "claimed_cents": line.claimed_cents,
                "assessment_id": assessment.assessment_id,
                "coverage_basis": assessment.coverage_basis,
                "policy_effective_from": assessment.policy_effective_from,
                "policy_effective_to": assessment.policy_effective_to,
                "policy_snapshot_date": assessment.policy_snapshot_date,
                "qualified_reviewer_id": assessment.qualified_reviewer_id,
                "qualification_basis": assessment.qualification_basis,
                "settlement_ids": [
                    settlement.settlement_id for settlement in settlements_for_line
                ],
            },
        ))

    for claim_line_id in sorted(set(assessment_groups) - set(line_groups)):
        exceptions.append(InsuranceAuditException(
            claim_line_id,
            "ASSESSMENT_WITHOUT_CLAIM_LINE",
            "coverage assessment references a claim line absent from the supplied population",
        ))

    exceptions.sort(key=lambda item: (item.code, item.claim_line_id, item.detail))
    observations.sort(key=lambda item: (item.counterparty_id, item.reference))
    return InsuranceAuditBatch(tuple(observations), tuple(exceptions))
