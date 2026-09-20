import json
import pytest
from dataclasses import asdict

from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import CharterState, build_charter, from_dict, render_markdown

def ready_input():
    return {
        "authorization_documented":True,"read_only_access":True,"population_reproducible":True,
        "incumbent_output_sealable":True,"settlement_observable":True,
        "material_authority_reconstructable":True,"customer_identity_stable":True,
        "carrier_identity_stable":True,"retention_defined":True,"deletion_defined":True,
        "invoice_source_coverage":1.0,"authority_source_coverage":1.0,"shipment_evidence_coverage":1.0,
    }

def activation(status="BLOCKED",route="DEPLOYED_PILOT_BLOCKED"):
    p=build_packet(ready_input(),{"status":status,"route":route,"blockers":[],"conditions":[],"warnings":[]})
    return json.loads(json.dumps(asdict(p)))

def request(**overrides):
    data={
        "engagement_id":"ENG-001","buyer_id":"buyer-a","business_unit":"bu-1",
        "population_rule":"All parcel/LTL invoices posted in August 2026 for approved carriers.",
        "source_date_start":"2026-08-01","source_date_end":"2026-08-31",
        "carrier_scope":["carrier-1","carrier-2"],"mode_scope":["parcel","LTL"],
        "fixed_fee_usd":20000,
        "buyer_truth_owner_role":"Director of Transportation",
        "buyer_action_approver_role":"VP Supply Chain",
        "freight_engagement_owner_role":"Pilot Lead",
        "buyer_acknowledges_scope":True,
        "buyer_acknowledges_blind_protocol":True,
        "buyer_acknowledges_report_totals_separate":True,
        "buyer_acknowledges_no_guaranteed_recovery":True,
        "freight_acknowledges_no_external_action_without_buyer_approval":True,
    }
    data.update(overrides)
    return from_dict(data)

def test_blocked_launch_can_be_prelaunch_accepted_but_not_authorized():
    c=build_charter(activation(),request())
    assert c.charter_state==CharterState.PRELAUNCH_ACCEPTED.value
    assert c.customer_data_authorized is False
    assert c.external_action_authorized is False

def test_ready_launch_with_all_acknowledgments_authorizes_kickoff_only():
    c=build_charter(activation("READY","CONTROLLED_MANUAL_BLIND_PILOT"),request())
    assert c.charter_state==CharterState.KICKOFF_AUTHORIZED.value
    assert c.customer_data_authorized is True
    assert c.external_action_authorized is False
    assert c.external_action_policy=="SEPARATE_BUYER_APPROVAL_REQUIRED"

def test_missing_acknowledgment_prevents_acceptance():
    c=build_charter(activation(),request(buyer_acknowledges_no_guaranteed_recovery=False))
    assert c.charter_state==CharterState.PENDING_ACKNOWLEDGMENT.value
    assert c.customer_data_authorized is False

def test_fee_must_stay_inside_activation_packet_band():
    with pytest.raises(ValueError,match="published price band"):
        build_charter(activation(),request(fixed_fee_usd=30000))

def test_activation_hash_is_verified():
    p=activation()
    p["price_band_usd"]="$1–$2 fixed"
    with pytest.raises(ValueError,match="activation packet hash mismatch"):
        build_charter(p,request())

def test_scope_dates_must_be_ordered():
    with pytest.raises(ValueError,match="cannot precede"):
        build_charter(activation(),request(source_date_start="2026-09-01",source_date_end="2026-08-01"))

def test_scope_requires_carrier_and_mode():
    with pytest.raises(ValueError,match="carrier_scope"):
        build_charter(activation(),request(carrier_scope=[]))
    with pytest.raises(ValueError,match="mode_scope"):
        build_charter(activation(),request(mode_scope=[]))

def test_charter_hash_is_deterministic_and_markdown_preserves_boundary():
    a=build_charter(activation(),request())
    b=build_charter(activation(),request())
    assert a.charter_hash==b.charter_hash
    text=render_markdown(a)
    assert "Carrier/vendor contact or money-moving action authorized by this charter: **false**" in text
    assert "not an e-signature system" in text