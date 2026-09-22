"""ParcelRecovery proof-bound parcel invoice reconciliation.

This first operational adapter does not attempt to infer a carrier tariff from
raw invoice text. It compares actual parcel charges to a separately reviewed
expected assessment bound to the same shipment/service/zone/weight/date.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
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


def _decimal(name: str, value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def normalize_service(value: str) -> str:
    return _required("service_code", value).upper().replace(" ", "_").replace("-", "_")


def normalize_zone(value: str) -> str:
    return _required("zone", value).upper().replace(" ", "")


@dataclass(frozen=True)
class ParcelCharge:
    shipment_id: str
    invoice_id: str
    shipper_id: str
    carrier_id: str
    ship_date: str
    service_code: str
    zone: str
    billed_weight: str
    actual_total_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "shipment_id", "invoice_id", "shipper_id", "carrier_id", "ship_date",
            "service_code", "zone", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("ship_date", self.ship_date)
        normalize_service(self.service_code)
        normalize_zone(self.zone)
        _decimal("billed_weight", self.billed_weight)
        _cents("actual_total_cents", self.actual_total_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_service(self) -> str:
        return normalize_service(self.service_code)

    @property
    def normalized_zone(self) -> str:
        return normalize_zone(self.zone)

    @property
    def normalized_weight(self) -> str:
        return str(_decimal("billed_weight", self.billed_weight).normalize())

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"parcel-charge:{self.shipment_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="parcel_invoice_charge",
            verified=self.verified,
            metadata={
                "invoice_id": self.invoice_id,
                "shipper_id": self.shipper_id,
                "carrier_id": self.carrier_id,
                "ship_date": self.ship_date,
                "service_code": self.normalized_service,
                "zone": self.normalized_zone,
                "billed_weight": self.normalized_weight,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ParcelExpectedAssessment:
    assessment_id: str
    shipment_id: str
    carrier_id: str
    ship_date: str
    service_code: str
    zone: str
    billed_weight: str
    expected_total_cents: int
    rate_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    rate_snapshot_date: str | None = None
    rate_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "assessment_id", "shipment_id", "carrier_id", "ship_date",
            "service_code", "zone", "rate_basis", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("ship_date", self.ship_date)
        normalize_service(self.service_code)
        normalize_zone(self.zone)
        _decimal("billed_weight", self.billed_weight)
        _cents("expected_total_cents", self.expected_total_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.rate_snapshot_date is not None:
            _iso_date("rate_snapshot_date", self.rate_snapshot_date)
        if self.verified:
            if not (isinstance(self.rate_reviewer_id, str) and self.rate_reviewer_id.strip()):
                raise ValueError("verified parcel assessment requires rate_reviewer_id")
            if not (isinstance(self.rate_snapshot_date, str) and self.rate_snapshot_date.strip()):
                raise ValueError("verified parcel assessment requires rate_snapshot_date")

    @property
    def normalized_service(self) -> str:
        return normalize_service(self.service_code)

    @property
    def normalized_zone(self) -> str:
        return normalize_zone(self.zone)

    @property
    def normalized_weight(self) -> str:
        return str(_decimal("billed_weight", self.billed_weight).normalize())

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "assessment_id": self.assessment_id,
            "shipment_id": self.shipment_id,
            "carrier_id": self.carrier_id,
            "ship_date": self.ship_date,
            "service_code": self.normalized_service,
            "zone": self.normalized_zone,
            "billed_weight": self.normalized_weight,
            "expected_total_cents": self.expected_total_cents,
            "rate_basis": self.rate_basis,
            "source_hash": self.source_hash,
            "rate_snapshot_date": self.rate_snapshot_date,
            "rate_reviewer_id": self.rate_reviewer_id,
        }
        return RuleRef(
            rule_id="parcel-assessment:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.ship_date,
            effective_to=self.ship_date,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "reviewed_parcel_rate_assessment",
                "assessment_id": self.assessment_id,
                "shipment_id": self.shipment_id,
                "carrier_id": self.carrier_id,
                "service_code": self.normalized_service,
                "zone": self.normalized_zone,
                "billed_weight": self.normalized_weight,
                "expected_total_cents": self.expected_total_cents,
                "rate_basis": self.rate_basis,
                "rate_snapshot_date": self.rate_snapshot_date,
                "rate_reviewer_id": self.rate_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ParcelAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class ParcelAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[ParcelAuditException, ...]


def audit_parcel_charges(
    *,
    client_id: str,
    charges: Iterable[ParcelCharge],
    assessments: Iterable[ParcelExpectedAssessment],
    currency: str = "USD",
) -> ParcelAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    charge_groups: dict[str, list[ParcelCharge]] = defaultdict(list)
    for charge in charges:
        charge_groups[charge.shipment_id].append(charge)
    assessment_groups: dict[str, list[ParcelExpectedAssessment]] = defaultdict(list)
    for assessment in assessments:
        assessment_groups[assessment.shipment_id].append(assessment)

    observations: list[RecoveryObservation] = []
    exceptions: list[ParcelAuditException] = []

    for shipment_id in sorted(charge_groups):
        charge_values = charge_groups[shipment_id]
        if len(charge_values) != 1:
            exceptions.append(ParcelAuditException(
                shipment_id, "DUPLICATE_PARCEL_SHIPMENT_ID",
                f"shipment_id appears {len(charge_values)} times; excluded",
            ))
            continue
        charge = charge_values[0]
        if charge.shipper_id != client_id:
            exceptions.append(ParcelAuditException(
                shipment_id, "SHIPPER_SCOPE_MISMATCH",
                "shipper_id does not match Scan 360 client_id",
            ))
            continue

        candidates = assessment_groups.get(shipment_id, [])
        if not candidates:
            exceptions.append(ParcelAuditException(
                shipment_id, "NO_REVIEWED_PARCEL_ASSESSMENT",
                "no expected-rate assessment is bound to this shipment",
            ))
            continue
        if len(candidates) != 1:
            exceptions.append(ParcelAuditException(
                shipment_id, "CONFLICTING_PARCEL_ASSESSMENTS",
                f"{len(candidates)} assessments are bound to this shipment",
            ))
            continue
        assessment = candidates[0]
        mismatches: list[str] = []
        if assessment.carrier_id != charge.carrier_id:
            mismatches.append("carrier_id")
        if assessment.ship_date != charge.ship_date:
            mismatches.append("ship_date")
        if assessment.normalized_service != charge.normalized_service:
            mismatches.append("service_code")
        if assessment.normalized_zone != charge.normalized_zone:
            mismatches.append("zone")
        if assessment.normalized_weight != charge.normalized_weight:
            mismatches.append("billed_weight")
        if mismatches:
            exceptions.append(ParcelAuditException(
                shipment_id, "PARCEL_ASSESSMENT_IDENTITY_MISMATCH",
                "assessment differs from charge on: " + ", ".join(mismatches),
            ))
            continue

        if charge.actual_total_cents <= assessment.expected_total_cents:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.PARCEL,
            client_id=client_id,
            counterparty_id=charge.carrier_id,
            reference=shipment_id,
            currency=currency,
            expected_cents=assessment.expected_total_cents,
            actual_cents=charge.actual_total_cents,
            rule=assessment.rule_ref(),
            evidence=(charge.evidence(),),
            reason="PARCEL_RATE_OVERCHARGE",
            confidence_basis=(
                "verified parcel invoice + reviewed expected-rate assessment"
                if charge.verified and assessment.verified
                else "parcel invoice/expected assessment requires verification"
            ),
            metadata={
                "invoice_id": charge.invoice_id,
                "ship_date": charge.ship_date,
                "service_code": charge.normalized_service,
                "zone": charge.normalized_zone,
                "billed_weight": charge.normalized_weight,
                "assessment_id": assessment.assessment_id,
                "rate_basis": assessment.rate_basis,
                "rate_snapshot_date": assessment.rate_snapshot_date,
                "rate_reviewer_id": assessment.rate_reviewer_id,
            },
        ))

    for shipment_id in sorted(set(assessment_groups) - set(charge_groups)):
        exceptions.append(ParcelAuditException(
            shipment_id, "ASSESSMENT_WITHOUT_PARCEL_CHARGE",
            "assessment references a shipment absent from supplied invoice population",
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    observations.sort(key=lambda x: (x.counterparty_id, x.reference))
    return ParcelAuditBatch(tuple(observations), tuple(exceptions))
