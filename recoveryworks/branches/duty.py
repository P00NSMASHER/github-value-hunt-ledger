"""DutyRecovery customs-assessment reconciliation.

This branch does not classify goods or decide which Chapter 99 layers stack.
It compares actual entry-line assessments against a separately reviewed expected
assessment that is bound to the same entry line, HTS code, origin, and import
date. Customs filing/refund action remains behind professional review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def normalize_hts(value: str) -> str:
    text = _required("hts_code", value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 4 or len(digits) > 10:
        raise ValueError("hts_code must contain 4-10 digits")
    return digits


def normalize_origin(value: str) -> str:
    text = _required("origin_country", value).upper()
    if len(text) != 2 or not text.isalpha():
        raise ValueError("origin_country must be ISO alpha-2")
    return text


@dataclass(frozen=True)
class DutyEntryLine:
    entry_line_id: str
    entry_id: str
    importer_id: str
    broker_id: str
    import_date: str
    hts_code: str
    origin_country: str
    actual_total_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "entry_line_id", "entry_id", "importer_id", "broker_id",
            "import_date", "hts_code", "origin_country",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _date("import_date", self.import_date)
        normalize_hts(self.hts_code)
        normalize_origin(self.origin_country)
        _cents("actual_total_cents", self.actual_total_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_hts(self) -> str:
        return normalize_hts(self.hts_code)

    @property
    def normalized_origin(self) -> str:
        return normalize_origin(self.origin_country)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"duty-entry:{self.entry_line_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="customs_entry_line",
            verified=self.verified,
            metadata={
                "entry_id": self.entry_id,
                "importer_id": self.importer_id,
                "broker_id": self.broker_id,
                "import_date": self.import_date,
                "hts_code": self.normalized_hts,
                "origin_country": self.normalized_origin,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class DutyAssessment:
    assessment_id: str
    entry_line_id: str
    import_date: str
    hts_code: str
    origin_country: str
    base_duty_cents: int
    additional_duty_cents: int
    mpf_cents: int
    hmf_cents: int
    other_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    schedule_snapshot_date: str | None = None
    professional_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "assessment_id", "entry_line_id", "import_date", "hts_code",
            "origin_country", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _date("import_date", self.import_date)
        normalize_hts(self.hts_code)
        normalize_origin(self.origin_country)
        for name in (
            "base_duty_cents", "additional_duty_cents", "mpf_cents",
            "hmf_cents", "other_cents",
        ):
            _cents(name, getattr(self, name))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.schedule_snapshot_date is not None:
            _date("schedule_snapshot_date", self.schedule_snapshot_date)
        if self.verified and not (
            isinstance(self.professional_reviewer_id, str)
            and self.professional_reviewer_id.strip()
        ):
            raise ValueError(
                "verified duty assessment requires professional_reviewer_id"
            )

    @property
    def normalized_hts(self) -> str:
        return normalize_hts(self.hts_code)

    @property
    def normalized_origin(self) -> str:
        return normalize_origin(self.origin_country)

    @property
    def expected_total_cents(self) -> int:
        return (
            self.base_duty_cents
            + self.additional_duty_cents
            + self.mpf_cents
            + self.hmf_cents
            + self.other_cents
        )

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "assessment_id": self.assessment_id,
            "entry_line_id": self.entry_line_id,
            "import_date": self.import_date,
            "hts_code": self.normalized_hts,
            "origin_country": self.normalized_origin,
            "expected_total_cents": self.expected_total_cents,
            "components": {
                "base_duty_cents": self.base_duty_cents,
                "additional_duty_cents": self.additional_duty_cents,
                "mpf_cents": self.mpf_cents,
                "hmf_cents": self.hmf_cents,
                "other_cents": self.other_cents,
            },
            "source_hash": self.source_hash,
            "schedule_snapshot_date": self.schedule_snapshot_date,
            "professional_reviewer_id": self.professional_reviewer_id,
        }
        return RuleRef(
            rule_id="duty-assessment:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.import_date,
            effective_to=self.import_date,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            jurisdiction="US",
            metadata={
                "kind": "reviewed_customs_assessment",
                "assessment_id": self.assessment_id,
                "hts_code": self.normalized_hts,
                "origin_country": self.normalized_origin,
                "schedule_snapshot_date": self.schedule_snapshot_date,
                "professional_reviewer_id": self.professional_reviewer_id,
                "expected_total_cents": self.expected_total_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class DutyAuditException:
    entry_line_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class DutyAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[DutyAuditException, ...]


def audit_duty_entries(
    *,
    client_id: str,
    entries: Iterable[DutyEntryLine],
    assessments: Iterable[DutyAssessment],
    currency: str = "USD",
) -> DutyAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    assessment_index: dict[str, DutyAssessment] = {}
    conflicts: set[str] = set()
    for assessment in assessments:
        existing = assessment_index.get(assessment.entry_line_id)
        if existing is None:
            assessment_index[assessment.entry_line_id] = assessment
        elif existing != assessment:
            conflicts.add(assessment.entry_line_id)

    observations: list[RecoveryObservation] = []
    exceptions: list[DutyAuditException] = []

    for entry in sorted(entries, key=lambda item: item.entry_line_id):
        if entry.entry_line_id in conflicts:
            exceptions.append(DutyAuditException(
                entry.entry_line_id,
                "CONFLICTING_ASSESSMENTS",
                "multiple different expected assessments exist for this entry line",
            ))
            continue

        assessment = assessment_index.get(entry.entry_line_id)
        if assessment is None:
            exceptions.append(DutyAuditException(
                entry.entry_line_id,
                "NO_REVIEWED_ASSESSMENT",
                "no expected assessment is bound to this entry line",
            ))
            continue

        mismatches: list[str] = []
        if assessment.import_date != entry.import_date:
            mismatches.append("import_date")
        if assessment.normalized_hts != entry.normalized_hts:
            mismatches.append("hts_code")
        if assessment.normalized_origin != entry.normalized_origin:
            mismatches.append("origin_country")
        if mismatches:
            exceptions.append(DutyAuditException(
                entry.entry_line_id,
                "ASSESSMENT_IDENTITY_MISMATCH",
                "assessment differs from entry on: " + ", ".join(mismatches),
            ))
            continue

        expected = assessment.expected_total_cents
        if entry.actual_total_cents <= expected:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.DUTY,
            client_id=client_id,
            counterparty_id=entry.broker_id,
            reference=entry.entry_line_id,
            currency=currency,
            expected_cents=expected,
            actual_cents=entry.actual_total_cents,
            rule=assessment.rule_ref(),
            evidence=(entry.evidence(),),
            reason="CUSTOMS_ASSESSMENT_OVERPAYMENT",
            confidence_basis=(
                "verified entry + professionally reviewed expected assessment"
                if entry.verified and assessment.verified
                else "entry/expected assessment requires verification"
            ),
            metadata={
                "entry_id": entry.entry_id,
                "importer_id": entry.importer_id,
                "hts_code": entry.normalized_hts,
                "origin_country": entry.normalized_origin,
                "import_date": entry.import_date,
                "assessment_id": assessment.assessment_id,
                "expected_components": {
                    "base_duty_cents": assessment.base_duty_cents,
                    "additional_duty_cents": assessment.additional_duty_cents,
                    "mpf_cents": assessment.mpf_cents,
                    "hmf_cents": assessment.hmf_cents,
                    "other_cents": assessment.other_cents,
                },
                "schedule_snapshot_date": assessment.schedule_snapshot_date,
                "professional_reviewer_id": assessment.professional_reviewer_id,
            },
        ))

    return DutyAuditBatch(tuple(observations), tuple(exceptions))
