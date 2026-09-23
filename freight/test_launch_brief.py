from freight.launch_brief import build_brief, render_markdown

def D(status="BLOCKED",route="DEPLOYED_PILOT_BLOCKED",blockers=(),conditions=(),warnings=()):
    return {"status":status,"route":route,"blockers":list(blockers),"conditions":list(conditions),"warnings":list(warnings)}

def test_current_deployment_blockers_become_prioritized_actions():
    brief=build_brief(D(blockers=("deployment_team_mfa_not_enforced","customer_data_plane_not_discovered")))
    codes=[a.code for a in brief.actions]
    assert codes==["deployment_team_mfa_not_enforced","customer_data_plane_not_discovered"]
    assert all(a.priority=="P0" for a in brief.actions)
    assert brief.actions[0].owner=="ACCOUNT OWNER"

def test_buyer_readiness_blocker_points_to_buyer_action():
    brief=build_brief(D(route="DATA_READINESS_DIAGNOSTIC",blockers=("buyer_authorization_missing",)))
    assert brief.actions[0].owner=="BUYER / COMMERCIAL"
    assert "authorization" in brief.actions[0].title.lower()

def test_separate_environment_condition_is_actionable():
    brief=build_brief(D(status="CONDITIONAL",route="SEPARATE_ENVIRONMENT_PENDING",conditions=("separate_environment_evidence_manifest_missing",)))
    action=brief.actions[0]
    assert action.priority=="P0"
    assert "SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json" in " ".join(action.evidence_required)

def test_unknown_blocker_never_disappears():
    brief=build_brief(D(blockers=("future_unknown_blocker",)))
    assert len(brief.actions)==1
    assert brief.actions[0].code=="future_unknown_blocker"
    assert brief.actions[0].category=="UNMAPPED_REVIEW"

def test_rights_blocker_points_to_executed_permission_evidence():
    code=(
        "rights_evidence:emoss08/Trenova: controlled pilot requires attached "
        "and verified executed permission evidence"
    )
    brief=build_brief(D(blockers=(code,)))
    action=brief.actions[0]
    assert action.priority=="P0"
    assert action.category=="RIGHTS_DILIGENCE"
    assert action.owner=="OWNER / LEGAL REVIEW"
    assert "ATTACHED_VERIFIED" in " ".join(action.evidence_required)

def test_ready_brief_has_no_actions_and_stable_hash():
    d=D(status="READY",route="CONTROLLED_MANUAL_BLIND_PILOT")
    a=build_brief(d)
    b=build_brief(d)
    assert a.actions==()
    assert a.brief_hash==b.brief_hash
    assert "READY" in render_markdown(a)

def test_duplicate_gate_codes_are_deduplicated():
    brief=build_brief(D(blockers=("deployment_team_mfa_not_enforced",),conditions=("deployment_team_mfa_not_enforced",)))
    assert len(brief.actions)==1

def test_warning_is_preserved():
    brief=build_brief(D(warnings=("rights_evidence_not_attached",)))
    assert brief.warnings==("rights_evidence_not_attached",)
