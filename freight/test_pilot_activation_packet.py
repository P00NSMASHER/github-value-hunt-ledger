from freight.pilot_activation_packet import build_packet, render_markdown

def ready_input(**overrides):
    data={
        "authorization_documented":True,
        "read_only_access":True,
        "population_reproducible":True,
        "incumbent_output_sealable":True,
        "settlement_observable":True,
        "material_authority_reconstructable":True,
        "customer_identity_stable":True,
        "carrier_identity_stable":True,
        "retention_defined":True,
        "deletion_defined":True,
        "invoice_source_coverage":1.0,
        "authority_source_coverage":1.0,
        "shipment_evidence_coverage":1.0,
    }
    data.update(overrides)
    return data

def decision(**overrides):
    data={"status":"BLOCKED","route":"DEPLOYED_PILOT_BLOCKED","blockers":["deployment_team_mfa_not_enforced","customer_data_plane_not_discovered"],"conditions":[],"warnings":[]}
    data.update(overrides)
    return data

def test_ready_buyer_gets_blind_acceptance_offer_and_incumbent_request():
    p=build_packet(ready_input(),decision())
    assert p.selected_offer=="BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST"
    assert p.price_band_usd=="Custom — confirmed in writing"
    assert any(r.source_type=="incumbent_output" and r.timing=="NOW" for r in p.buyer_data_requests)

def test_conditional_readiness_routes_to_diagnostic_and_drops_blind_only_request():
    p=build_packet(ready_input(invoice_source_coverage=0.80),decision(status="BLOCKED",route="DATA_READINESS_DIAGNOSTIC",blockers=[],conditions=["invoice_source_coverage_below_95pct"]))
    assert p.selected_offer=="DATA_READINESS_DIAGNOSTIC"
    assert p.price_band_usd=="Custom — confirmed in writing"
    assert not any(r.source_type=="incumbent_output" for r in p.buyer_data_requests)

def test_packet_preserves_launch_remediation_actions():
    p=build_packet(ready_input(),decision())
    codes=[x["code"] for x in p.remediation_actions]
    assert codes[:2]==["deployment_team_mfa_not_enforced","customer_data_plane_not_discovered"]

def test_packet_requests_required_pilot_source_types():
    p=build_packet(ready_input(),decision())
    types={r.source_type for r in p.buyer_data_requests}
    assert {"invoice","authority","incumbent_output","settlement_observation"}.issubset(types)

def test_packet_has_stable_hash_and_buyer_safe_markdown():
    a=build_packet(ready_input(),decision())
    b=build_packet(ready_input(),decision())
    assert a.activation_hash==b.activation_hash
    text=render_markdown(a)
    assert "Pilot Activation Packet" in text
    assert "loaded hourly" not in text.lower()
    assert "gross margin" not in text.lower()
    assert "$5,000" not in text
    assert "$15,000" not in text
    assert "Custom — confirmed in writing" in text

def test_later_settlement_is_not_requested_as_immediate_recovery_proof():
    p=build_packet(ready_input(),decision())
    settlement=[r for r in p.buyer_data_requests if r.source_type=="settlement_observation"]
    assert len(settlement)==1
    assert settlement[0].timing=="LATER_OUTCOME"

def test_mismatched_readiness_and_launch_decision_is_rejected():
    import pytest
    with pytest.raises(ValueError,match="readiness/launch decision mismatch"):
        build_packet(ready_input(invoice_source_coverage=0.80),decision(status="BLOCKED",route="DEPLOYED_PILOT_BLOCKED"))


def test_launch_warnings_are_preserved():
    p=build_packet(ready_input(),decision(warnings=["rights_evidence_not_attached"]))
    assert p.launch_warnings==("rights_evidence_not_attached",)
    assert "rights_evidence_not_attached" in render_markdown(p)
