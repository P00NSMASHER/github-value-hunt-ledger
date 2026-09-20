from freight.readiness import (
    PilotReadinessInput,
    ReadinessStatus,
    assess_readiness,
)

def ready_input(**overrides):
    base = dict(
        authorization_documented=True,
        read_only_access=True,
        population_reproducible=True,
        incumbent_output_sealable=True,
        settlement_observable=True,
        material_authority_reconstructable=True,
        customer_identity_stable=True,
        carrier_identity_stable=True,
        retention_defined=True,
        deletion_defined=True,
        invoice_source_coverage=1.0,
        authority_source_coverage=1.0,
        shipment_evidence_coverage=1.0,
    )
    base.update(overrides)
    return PilotReadinessInput(**base)

def test_ready_population_routes_to_blind_acceptance_test():
    assessment = assess_readiness(ready_input())
    assert assessment.status is ReadinessStatus.READY
    assert assessment.score == 100
    assert assessment.recommended_offer == "BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST"

def test_high_score_cannot_override_missing_authorization():
    assessment = assess_readiness(ready_input(authorization_documented=False))
    assert assessment.status is ReadinessStatus.BLOCKED
    assert "buyer_authorization_missing" in assessment.blockers
    assert assessment.recommended_offer == "DATA_READINESS_DIAGNOSTIC"

def test_high_score_cannot_override_unobservable_settlement():
    assessment = assess_readiness(ready_input(settlement_observable=False))
    assert assessment.status is ReadinessStatus.BLOCKED
    assert "later_settlement_cannot_be_observed" in assessment.blockers

def test_missing_controlling_authority_is_hard_blocker():
    assessment = assess_readiness(ready_input(material_authority_reconstructable=False))
    assert assessment.status is ReadinessStatus.BLOCKED
    assert "controlling_authority_not_reconstructable" in assessment.blockers

def test_low_coverage_is_conditional_not_silently_ready():
    assessment = assess_readiness(
        ready_input(
            invoice_source_coverage=0.90,
            authority_source_coverage=0.85,
            shipment_evidence_coverage=0.75,
        )
    )
    assert assessment.status is ReadinessStatus.CONDITIONAL
    assert len(assessment.conditions) == 3
    assert assessment.recommended_offer == "DATA_READINESS_DIAGNOSTIC"

def test_score_is_deterministic():
    inp = ready_input(authority_source_coverage=0.91)
    assert assess_readiness(inp).score == assess_readiness(inp).score

def test_invalid_coverage_is_rejected():
    try:
        assess_readiness(ready_input(invoice_source_coverage=1.2))
    except ValueError as exc:
        assert "between 0 and 1" in str(exc)
    else:
        raise AssertionError("coverage > 1 should fail")
