"""TaxRecovery proof-bound sales/use-tax overpayment reconciliation.

This branch does not autonomously decide taxability. It compares actual tax
charged on a transaction line against a separately reviewed expected assessment
bound to the same line/date/jurisdiction/category. Verified assessments require
named professional review and rule-snapshot provenance.
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


def normalize_jurisdiction(value: str) -> str:
    return _required("jurisdiction", value).upper().replace(" ", "")


def normalize_tax_category(value: str) -> str:
    return _required("tax_category", value).upper().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class TaxTransactionLine:
    tax_line_id: str
    invoice_id: str
    purchaser_id: str
    vendor_id: str
    transaction_date: str
    jurisdiction: str
    tax_category: str
    taxable_basis_cents: int
    actual_tax_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "tax_line_id", "invoice_id", "purchaser_id", "vendor_id",
            "transaction_date", "jurisdiction", "tax_category",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("transaction_date", self.transaction_date)
        normalize_jurisdiction(self.jurisdiction)
        normalize_tax_category(self.tax_category)
        _cents("taxable_basis_cents", self.taxable_basis_cents)
        _cents("actual_tax_cents", self.actual_tax_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_jurisdiction(self) -> str:
        return normalize_jurisdiction(self.jurisdiction)

    @property
    def normalized_tax_category(self) -> str:
        return normalize_tax_category(self.tax_category)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"tax-line:{self.tax_line_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="transaction_tax_line",
            verified=self.verified,
            metadata={
                "invoice_id": self.invoice_id,
                "purchaser_id": self.purchaser_id,
                "vendor_id": self.vendor_id,
                "transaction_date": self.transaction_date,
                "jurisdiction": self.normalized_jurisdiction,
                "tax_category": self.normalized_tax_category,
                "taxable_basis_cents": self.taxable_basis_cents,
                "actual_tax_cents": self.actual_tax_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class TaxAssessment:
    assessment_id: str
    tax_line_id: str
    transaction_date: str
    jurisdiction: str
    tax_category: str
    expected_tax_cents: int
    taxability_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    rule_snapshot_date: str | None = None
    professional_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "assessment_id", "tax_line_id", "transaction_date",
            "jurisdiction", "tax_category", "taxability_basis",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("transaction_date", self.transaction_date)
        normalize_jurisdiction(self.jurisdiction)
        normalize_tax_category(self.tax_category)
        _cents("expected_tax_cents", self.expected_tax_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.rule_snapshot_date is not None:
            _iso_date("rule_snapshot_date", self.rule_snapshot_date)
        if self.verified:
            if not (
                isinstance(self.professional_reviewer_id, str)
                and self.professional_reviewer_id.strip()
            ):
                raise ValueError(
                    "verified tax assessment requires professional_reviewer_id"
                )
            if not (
                isinstance(self.rule_snapshot_date, str)
                and self.rule_snapshot_date.strip()
            ):
                raise ValueError(
                    "verified tax assessment requires rule_snapshot_date"
                )

    @property
    def normalized_jurisdiction(self) -> str:
        return normalize_jurisdiction(self.jurisdiction)

    @property
    def normalized_tax_category(self) -> str:
        return normalize_tax_category(self.tax_category)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "assessment_id": self.assessment_id,
            "tax_line_id": self.tax_line_id,
            "transaction_date": self.transaction_date,
            "jurisdiction": self.normalized_jurisdiction,
            "tax_category": self.normalized_tax_category,
            "expected_tax_cents": self.expected_tax_cents,
            "taxability_basis": self.taxability_basis,
            "source_hash": self.source_hash,
            "rule_snapshot_date": self.rule_snapshot_date,
            "professional_reviewer_id": self.professional_reviewer_id,
        }
        return RuleRef(
            rule_id="tax-assessment:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.transaction_date,
            effective_to=self.transaction_date,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            jurisdiction=self.normalized_jurisdiction,
            metadata={
                "kind": "reviewed_tax_assessment",
                "assessment_id": self.assessment_id,
                "tax_line_id": self.tax_line_id,
                "tax_category": self.normalized_tax_category,
                "expected_tax_cents": self.expected_tax_cents,
                "taxability_basis": self.taxability_basis,
                "rule_snapshot_date": self.rule_snapshot_date,
                "professional_reviewer_id": self.professional_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class TaxAuditException:
    tax_line_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class TaxAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[TaxAuditException, ...]


def audit_tax_lines(
    *,
    client_id: str,
    lines: Iterable[TaxTransactionLine],
    assessments: Iterable[TaxAssessment],
    currency: str = "USD",
) -> TaxAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    line_groups: dict[str, list[TaxTransactionLine]] = defaultdict(list)
    for line in lines:
        line_groups[line.tax_line_id].append(line)

    assessment_groups: dict[str, list[TaxAssessment]] = defaultdict(list)
    for assessment in assessments:
        assessment_groups[assessment.tax_line_id].append(assessment)

    observations: list[RecoveryObservation] = []
    exceptions: list[TaxAuditException] = []

    for tax_line_id in sorted(line_groups):
        line_values = line_groups[tax_line_id]
        if len(line_values) != 1:
            exceptions.append(TaxAuditException(
                tax_line_id,
                "DUPLICATE_TAX_LINE_ID",
                f"tax_line_id appears {len(line_values)} times; excluded",
            ))
            continue
        line = line_values[0]

        if line.purchaser_id != client_id:
            exceptions.append(TaxAuditException(
                tax_line_id,
                "PURCHASER_SCOPE_MISMATCH",
                "purchaser_id does not match Scan 360 client_id",
            ))
            continue

        assessment_values = assessment_groups.get(tax_line_id, [])
        if not assessment_values:
            exceptions.append(TaxAuditException(
                tax_line_id,
                "NO_REVIEWED_TAX_ASSESSMENT",
                "no expected tax assessment is bound to this line",
            ))
            continue
        if len(assessment_values) != 1:
            exceptions.append(TaxAuditException(
                tax_line_id,
                "CONFLICTING_TAX_ASSESSMENTS",
                f"{len(assessment_values)} expected assessments are bound to this line",
            ))
            continue
        assessment = assessment_values[0]

        mismatches: list[str] = []
        if assessment.transaction_date != line.transaction_date:
            mismatches.append("transaction_date")
        if assessment.normalized_jurisdiction != line.normalized_jurisdiction:
            mismatches.append("jurisdiction")
        if assessment.normalized_tax_category != line.normalized_tax_category:
            mismatches.append("tax_category")
        if mismatches:
            exceptions.append(TaxAuditException(
                tax_line_id,
                "TAX_ASSESSMENT_IDENTITY_MISMATCH",
                "assessment differs from transaction on: " + ", ".join(mismatches),
            ))
            continue

        if line.actual_tax_cents <= assessment.expected_tax_cents:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.TAX,
            client_id=client_id,
            counterparty_id=line.vendor_id,
            reference=line.tax_line_id,
            currency=currency,
            expected_cents=assessment.expected_tax_cents,
            actual_cents=line.actual_tax_cents,
            rule=assessment.rule_ref(),
            evidence=(line.evidence(),),
            reason="TRANSACTION_TAX_OVERPAYMENT",
            confidence_basis=(
                "verified invoice tax + professionally reviewed expected tax assessment"
                if line.verified and assessment.verified
                else "tax line/expected assessment requires verification"
            ),
            metadata={
                "invoice_id": line.invoice_id,
                "transaction_date": line.transaction_date,
                "jurisdiction": line.normalized_jurisdiction,
                "tax_category": line.normalized_tax_category,
                "taxable_basis_cents": line.taxable_basis_cents,
                "assessment_id": assessment.assessment_id,
                "taxability_basis": assessment.taxability_basis,
                "rule_snapshot_date": assessment.rule_snapshot_date,
                "professional_reviewer_id": assessment.professional_reviewer_id,
            },
        ))

    # Assessments whose line is absent are surfaced rather than silently ignored.
    for tax_line_id in sorted(set(assessment_groups) - set(line_groups)):
        exceptions.append(TaxAuditException(
            tax_line_id,
            "ASSESSMENT_WITHOUT_TAX_LINE",
            "expected assessment references a tax line absent from the supplied population",
        ))

    exceptions.sort(key=lambda item: (item.code, item.tax_line_id, item.detail))
    observations.sort(key=lambda item: (item.counterparty_id, item.reference))
    return TaxAuditBatch(tuple(observations), tuple(exceptions))
