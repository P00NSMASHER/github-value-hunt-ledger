import json
import pytest
from dataclasses import asdict

from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_amendment import AmendmentState, build_amendment, from_dict

def ready_input():
    return {"authorization_documented":True,"read_only_access":True,"population_reproducible":True,"incumbent_output_sealable":True,"settlement_observable":True,"material_authority_reconstructable":True,"customer_identity_stable":True,"carrier_identity_stable":True,"retention_defined":True,"deletion_defined":True,"invoice_source_coverage":1.0,"authority_source_coverage":1.0,"shipment_evidence_coverage":1.0}

def activation(status="READY",route="CONTROLLED_MANUAL_BLIND_PILOT",warnings=None):
    p=build_packet(ready_input(),{"status":status,"route":route,"blockers":[],"conditions":[],"warnings":warnings or []})
    return json.loads(json.dumps(asdict(p)))

def charter_request(**overrides):
    d={"engagement_id":"ENG-001","buyer_id":"buyer-a","business_unit":"bu-1","population_rule":"August approved invoices","source_date_start":"2026-08-01","source_date_end":"2026-08-31","carrier_scope":["carrier-1","carrier-2"],"mode_scope":["parcel","LTL"],"fixed_fee_usd":20000,"buyer_truth_owner_role":"Director Transportation","buyer_action_approver_role":"VP Supply Chain","freight_engagement_owner_role":"Pilot Lead","buyer_acknowledges_scope":True,"buyer_acknowledges_blind_protocol":True,"buyer_acknowledges_report_totals_separate":True,"buyer_acknowledges_no_guaranteed_recovery":True,"freight_acknowledges_no_external_action_without_buyer_approval":True}
    d.update(overrides)
    return charter_from_dict(d)

def base_charter():
    return json.loads(json.dumps(asdict(build_charter(activation(),charter_request()))))

def req(**overrides):
    d={"amendment_id":"AMD-001","reason":"Buyer requested scope update","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"CFO"}
    d.update(overrides)
    return from_dict(d)

def test_accepted_role_change_requires_replacement_but_not_new_activation():
    a=build_amendment(base_charter(),req())
    assert a.amendment_state==AmendmentState.ACCEPTED_REPLACEMENT_REQUIRED.value
    assert a.requires_reacknowledgment is True
    assert a.requires_new_activation is False
    assert a.requires_launch_revalidation is False
    assert a.kickoff_suspended is True
    assert a.customer_data_authorized is False

def test_material_scope_change_requires_readiness_launch_and_new_activation():
    a=build_amendment(base_charter(),req(population_rule="August and September approved invoices",buyer_action_approver_role=None))
    assert a.requires_readiness_revalidation is True
    assert a.requires_launch_revalidation is True
    assert a.requires_new_activation is True

def test_unacknowledged_change_stays_pending():
    a=build_amendment(base_charter(),req(buyer_acknowledges_change=False))
    assert a.amendment_state==AmendmentState.PENDING_ACKNOWLEDGMENT.value
    assert a.kickoff_suspended is False

def test_no_change_is_rejected():
    with pytest.raises(ValueError,match="at least one Charter field"):
        build_amendment(base_charter(),req(buyer_action_approver_role="VP Supply Chain"))

def test_tampered_base_charter_is_rejected():
    c=base_charter(); c["fixed_fee_usd"]=1
    with pytest.raises(ValueError,match="charter hash mismatch"):
        build_amendment(c,req())

def test_scope_change_cannot_use_same_activation_hash():
    base=base_charter()
    replacement=json.loads(json.dumps(asdict(build_charter(activation(),charter_request(population_rule="Expanded scope")))))
    with pytest.raises(ValueError,match="new Activation Packet"):
        build_amendment(base,req(population_rule="Expanded scope",buyer_action_approver_role=None),replacement)

def test_role_change_can_be_superseded_by_replacement_charter_same_activation():
    base=base_charter()
    replacement=json.loads(json.dumps(asdict(build_charter(activation(),charter_request(buyer_action_approver_role="CFO")))))
    a=build_amendment(base,req(),replacement)
    assert a.amendment_state==AmendmentState.SUPERSEDED_BY_REPLACEMENT.value
    assert a.replacement_charter_hash==replacement["charter_hash"]
    assert a.customer_data_authorized is True
    assert a.external_action_authorized is False

def test_material_scope_change_can_be_superseded_only_by_new_activation_and_matching_charter():
    base=base_charter()
    new_activation=activation(warnings=["scope-revalidated"])
    replacement=json.loads(json.dumps(asdict(build_charter(new_activation,charter_request(population_rule="Expanded scope")))))
    a=build_amendment(base,req(population_rule="Expanded scope",buyer_action_approver_role=None),replacement)
    assert a.amendment_state==AmendmentState.SUPERSEDED_BY_REPLACEMENT.value
    assert a.requires_new_activation is True
    assert a.customer_data_authorized is True

def test_out_of_band_fee_requires_new_activation_and_price_band():
    a=build_amendment(base_charter(),req(fixed_fee_usd=30000,buyer_action_approver_role=None))
    assert a.requires_new_activation is True
    replacement=json.loads(json.dumps(asdict(build_charter(activation(),charter_request()))))
    with pytest.raises(ValueError):
        build_amendment(base_charter(),req(fixed_fee_usd=30000,buyer_action_approver_role=None),replacement)