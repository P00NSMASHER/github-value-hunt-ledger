import json
import pytest
from dataclasses import asdict

from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_amendment import build_amendment, from_dict as amendment_from_dict
from freight.engagement_state import EngagementState, resolve_engagement

def ready_input():
    return {"authorization_documented":True,"read_only_access":True,"population_reproducible":True,"incumbent_output_sealable":True,"settlement_observable":True,"material_authority_reconstructable":True,"customer_identity_stable":True,"carrier_identity_stable":True,"retention_defined":True,"deletion_defined":True,"invoice_source_coverage":1.0,"authority_source_coverage":1.0,"shipment_evidence_coverage":1.0}

def activation(status="READY",route="CONTROLLED_MANUAL_BLIND_PILOT",warnings=None):
    p=build_packet(ready_input(),{"status":status,"route":route,"blockers":[],"conditions":[],"warnings":warnings or []})
    return json.loads(json.dumps(asdict(p)))

def charter_req(**overrides):
    d={"engagement_id":"ENG-001","buyer_id":"buyer-a","business_unit":"bu-1","population_rule":"August approved invoices","source_date_start":"2026-08-01","source_date_end":"2026-08-31","carrier_scope":["carrier-1"],"mode_scope":["LTL"],"fixed_fee_usd":20000,"buyer_truth_owner_role":"Truth Owner","buyer_action_approver_role":"Approver","freight_engagement_owner_role":"Pilot Lead","buyer_acknowledges_scope":True,"buyer_acknowledges_blind_protocol":True,"buyer_acknowledges_report_totals_separate":True,"buyer_acknowledges_no_guaranteed_recovery":True,"freight_acknowledges_no_external_action_without_buyer_approval":True}
    d.update(overrides)
    return charter_from_dict(d)

def charter(**overrides):
    return json.loads(json.dumps(asdict(build_charter(activation(**{k:v for k,v in overrides.items() if k in {"status","route","warnings"}}),charter_req(**{k:v for k,v in overrides.items() if k not in {"status","route","warnings"}})))))

def amendment(base,**overrides):
    d={"amendment_id":"AMD-001","reason":"role change","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"New Approver"}
    d.update(overrides)
    req=amendment_from_dict(d)
    return json.loads(json.dumps(asdict(build_amendment(base,req))))

def test_kickoff_authorized_charter_resolves_active():
    c=charter()
    r=resolve_engagement(c)
    assert r.engagement_state==EngagementState.ACTIVE.value
    assert r.customer_data_authorized is True
    assert r.audit_processing_allowed is True
    assert r.external_action_authorized is False

def test_prelaunch_charter_resolves_prelaunch():
    c=charter(status="BLOCKED",route="DEPLOYED_PILOT_BLOCKED")
    r=resolve_engagement(c)
    assert r.engagement_state==EngagementState.PRELAUNCH.value
    assert r.report_generation_allowed is False

def test_pending_unacknowledged_amendment_does_not_suspend_active_charter():
    c=charter()
    a=amendment(c,buyer_acknowledges_change=False)
    r=resolve_engagement(c,[a])
    assert r.engagement_state==EngagementState.ACTIVE_WITH_PENDING_AMENDMENT.value
    assert r.customer_data_authorized is True
    assert r.replacement_required is False

def test_accepted_amendment_suspends_processing_until_replacement():
    c=charter()
    a=amendment(c)
    r=resolve_engagement(c,[a])
    assert r.engagement_state==EngagementState.SUSPENDED_PENDING_REPLACEMENT.value
    assert r.customer_data_authorized is False
    assert r.audit_processing_allowed is False
    assert r.report_generation_allowed is False
    assert r.settlement_processing_allowed is False
    assert r.replacement_required is True

def test_superseded_amendment_resolves_replacement_charter():
    base=charter()
    replacement=charter(buyer_action_approver_role="New Approver")
    req=amendment_from_dict({"amendment_id":"AMD-001","reason":"role change","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"New Approver"})
    superseded=json.loads(json.dumps(asdict(build_amendment(base,req,replacement))))
    r=resolve_engagement(base,[superseded],[replacement])
    assert r.engagement_state==EngagementState.ACTIVE.value
    assert r.operative_charter_hash==replacement["charter_hash"]
    assert r.customer_data_authorized is True

def test_multi_step_replacement_chain_resolves_latest_charter():
    base=charter()
    c2=charter(buyer_action_approver_role="Approver 2")
    r1=amendment_from_dict({"amendment_id":"AMD-001","reason":"role change","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"Approver 2"})
    a1=json.loads(json.dumps(asdict(build_amendment(base,r1,c2))))
    c3=charter(buyer_action_approver_role="Approver 3")
    r2=amendment_from_dict({"amendment_id":"AMD-002","reason":"role change","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"Approver 3"})
    a2=json.loads(json.dumps(asdict(build_amendment(c2,r2,c3))))
    r=resolve_engagement(base,[a1,a2],[c2,c3])
    assert r.engagement_state==EngagementState.ACTIVE.value
    assert r.operative_charter_hash==c3["charter_hash"]
    assert len(r.resolution_path)==5

def test_multiple_amendments_on_same_base_fail_closed():
    c=charter()
    a1=amendment(c,buyer_acknowledges_change=False,amendment_id="A1")
    a2=amendment(c,buyer_acknowledges_change=False,amendment_id="A2")
    with pytest.raises(ValueError,match="multiple Amendments"):
        resolve_engagement(c,[a1,a2])

def test_dangling_replacement_hash_fails_closed():
    base=charter()
    replacement=charter(buyer_action_approver_role="New Approver")
    req=amendment_from_dict({"amendment_id":"AMD-001","reason":"role change","buyer_acknowledges_change":True,"freight_acknowledges_change":True,"buyer_action_approver_role":"New Approver"})
    superseded=json.loads(json.dumps(asdict(build_amendment(base,req,replacement))))
    with pytest.raises(ValueError,match="replacement Charter hash is not supplied"):
        resolve_engagement(base,[superseded],[])

def test_tampered_amendment_hash_is_rejected():
    c=charter()
    a=amendment(c)
    a["kickoff_suspended"]=False
    with pytest.raises(ValueError,match="Amendment hash mismatch"):
        resolve_engagement(c,[a])