"""Fail-closed incident-record validation for Freight Recovery.

This is a planning/reference control, not proof of a deployed SOC/IR program.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class IncidentSeverity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentState(str, Enum):
    OPEN = "OPEN"
    CONTAINED = "CONTAINED"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"


class ExposureState(str, Enum):
    UNKNOWN = "UNKNOWN"
    NO_EVIDENCE = "NO_EVIDENCE"
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"


@dataclass(frozen=True)
class IncidentRecord:
    incident_id: str
    buyer_id: str
    business_unit: str
    severity: IncidentSeverity
    state: IncidentState
    exposure_state: ExposureState
    containment_complete: bool
    recovery_verified: bool
    evidence_hashes: tuple[str, ...] = ()
    external_notification_sent: bool = False
    external_notification_authorized: bool = False
    notification_basis_ref: str | None = None
    postmortem_ref: str | None = None


def validate_incident(record: IncidentRecord) -> list[str]:
    errors: list[str] = []
    for name in ("incident_id", "buyer_id", "business_unit"):
        value = getattr(record, name)
        if not isinstance(value, str) or not value.strip():
            errors.append(name + " is required")

    for digest in record.evidence_hashes:
        if not SHA256_RE.fullmatch(digest):
            errors.append("evidence_hashes must contain lowercase SHA-256 values")

    if record.state in {IncidentState.CONTAINED, IncidentState.RECOVERED, IncidentState.CLOSED}:
        if not record.containment_complete:
            errors.append("contained/recovered/closed state requires containment_complete")

    if record.state in {IncidentState.RECOVERED, IncidentState.CLOSED}:
        if not record.recovery_verified:
            errors.append("recovered/closed state requires recovery_verified")

    if record.state is IncidentState.CLOSED:
        if record.exposure_state is ExposureState.UNKNOWN:
            errors.append("closed incident cannot leave exposure_state UNKNOWN")
        if not record.postmortem_ref or not record.postmortem_ref.strip():
            errors.append("closed incident requires postmortem_ref")
        if record.severity in {IncidentSeverity.SEV1, IncidentSeverity.SEV2} and not record.evidence_hashes:
            errors.append("SEV1/SEV2 closure requires preserved evidence hashes")

    if record.external_notification_sent:
        if not record.external_notification_authorized:
            errors.append("external notification requires explicit authorization")
        if not record.notification_basis_ref or not record.notification_basis_ref.strip():
            errors.append("external notification requires notification_basis_ref")

    return errors
