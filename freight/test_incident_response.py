from freight.incident_response import (
    ExposureState,
    IncidentRecord,
    IncidentSeverity,
    IncidentState,
    validate_incident,
)


GOOD_HASH = "a" * 64


def base(**overrides):
    data = dict(
        incident_id="INC-001",
        buyer_id="buyer-a",
        business_unit="bu-1",
        severity=IncidentSeverity.SEV2,
        state=IncidentState.OPEN,
        exposure_state=ExposureState.UNKNOWN,
        containment_complete=False,
        recovery_verified=False,
    )
    data.update(overrides)
    return IncidentRecord(**data)


def test_open_unknown_incident_is_valid():
    assert validate_incident(base()) == []


def test_closed_unknown_exposure_is_rejected():
    errors = validate_incident(
        base(
            state=IncidentState.CLOSED,
            containment_complete=True,
            recovery_verified=True,
            evidence_hashes=(GOOD_HASH,),
            postmortem_ref="postmortem/INC-001",
        )
    )
    assert any("exposure_state UNKNOWN" in x for x in errors)


def test_external_notification_requires_human_authorization_and_basis():
    errors = validate_incident(
        base(
            external_notification_sent=True,
            external_notification_authorized=False,
        )
    )
    assert any("explicit authorization" in x for x in errors)
    assert any("notification_basis_ref" in x for x in errors)


def test_sev2_can_close_only_with_evidence_and_postmortem():
    record = base(
        state=IncidentState.CLOSED,
        exposure_state=ExposureState.NO_EVIDENCE,
        containment_complete=True,
        recovery_verified=True,
        evidence_hashes=(GOOD_HASH,),
        postmortem_ref="postmortem/INC-001",
    )
    assert validate_incident(record) == []
