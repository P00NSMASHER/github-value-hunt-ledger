from datetime import datetime, timedelta, timezone
from prototype import *

def score(evidence=5, rights=5): return CommercialScore(5,5,5,4,evidence,rights)
def candidate(verdict=Verdict.PASS, **kwargs):
    return CandidateRecord("c1","https://github.com/o/r","deadbeef",score(),
        VerificationRecord(verdict=verdict,frozen_snapshot_hash="abc",**kwargs))

def test_master_candidate_requires_independent_verifier():
    assert evaluate_promotion(CandidateRecord("c1","u","sha",score(),None)).state is CandidateState.VERIFICATION_PENDING

def test_readme_only_core_claim_cannot_promote():
    assert evaluate_promotion(candidate(core_claim_readme_only=True)).state is CandidateState.WATCH

def test_sensitive_contamination_fails_closed():
    assert evaluate_promotion(candidate(sensitive_source_contamination=True)).state is CandidateState.REJECTED

def test_clean_verified_high_score_becomes_master_candidate_not_master():
    assert evaluate_promotion(candidate()).state is CandidateState.MASTER_CANDIDATE

def test_exact_revision_is_mandatory():
    c=CandidateRecord("c1","u",None,score(),VerificationRecord(Verdict.PASS,"snap"))
    assert evaluate_promotion(c).state is CandidateState.REJECTED

def test_evidence_manifest_detects_mutation():
    ev=EvidenceItem("e1","u","sha","file.py:10","abc","SOURCE")
    m=freeze_evidence_manifest("c1","o/r","sha",["claim"],[ev])
    assert verify_manifest(m); m["claims"].append("mutated"); assert not verify_manifest(m)

def test_one_success_stays_local():
    assert evaluate_skill_promotion(SkillVerification(frozenset({"t1"})))[0] is SkillState.LOCAL

def test_two_successes_only_stage_skill():
    assert evaluate_skill_promotion(SkillVerification(frozenset({"t1","t2"})))[0] is SkillState.STAGED

def test_heldout_and_canary_required_before_global():
    base=dict(distinct_success_task_ids=frozenset({"t1","t2"}),heldout_tasks=5,heldout_passes=5,
              adversarial_task_passed=True,adjacent_domain_task_passed=True,curator_approved=True)
    assert evaluate_skill_promotion(SkillVerification(**base,canary_hunters=2))[0] is SkillState.CANARY
    assert evaluate_skill_promotion(SkillVerification(**base,canary_hunters=3))[0] is SkillState.GLOBAL

def test_skill_regression_quarantines():
    v=SkillVerification(distinct_success_task_ids=frozenset({"t1","t2"}),heldout_tasks=5,heldout_passes=5,
        heldout_regressions=1,adversarial_task_passed=True,adjacent_domain_task_passed=True)
    assert evaluate_skill_promotion(v)[0] is SkillState.QUARANTINED

def test_lease_prevents_duplicate_work_and_recovers_stale():
    b=LeaseBook(); t=datetime(2026,9,20,tzinfo=timezone.utc)
    a=b.claim("task","hunter-a",60,t); assert a
    assert b.claim("task","hunter-b",60,t+timedelta(seconds=10)) is None
    assert b.recoverable(t+timedelta(seconds=61))==["task"]
    c=b.claim("task","hunter-b",60,t+timedelta(seconds=61)); assert c and c.generation>a.generation


def freight_request(**overrides):
    base=dict(
        stage_gate="EXP-001",
        gap_id="FRT-AUTH-001",
        trigger="AUTHORITY_CONNECTOR",
        category="ACCESSORIAL_ADDENDUM_CONNECTOR",
        evidence_to_change_decision="Customer pilot cannot reconstruct one carrier addendum.",
        why_existing_stack_insufficient="Existing RateCon path does not contain the incorporated schedule.",
        stop_condition="Stop after exact addendum source/version is reproducibly acquired.",
        broad_search=False,
    )
    base.update(overrides)
    return FreightWorkRequest(**base)

def active_freight_gap(**overrides):
    base=dict(
        gap_id="FRT-AUTH-001",
        status="ACTIVE_SEARCH",
        search_allowed=True,
        allowed_triggers=frozenset({"AUTHORITY_CONNECTOR","PAYING_CUSTOMER_GAP"}),
    )
    base.update(overrides)
    return FreightGapAuthorization(**base)

def test_freight_specific_exp001_gap_is_allowed():
    assert evaluate_freight_work_request(
        freight_request(), active_freight_gap()
    ).decision is FreightWorkDecision.ALLOW

def test_unregistered_freight_gap_is_denied():
    result=evaluate_freight_work_request(freight_request(), None)
    assert result.decision is FreightWorkDecision.DENY
    assert "gap_id_not_registered" in result.reasons

def test_registered_dormant_gap_is_denied():
    result=evaluate_freight_work_request(
        freight_request(),
        active_freight_gap(status="DORMANT_TRIGGERED",search_allowed=False),
    )
    assert result.decision is FreightWorkDecision.DENY
    assert "registered_gap_not_active_search" in result.reasons
    assert "registered_gap_search_not_allowed" in result.reasons

def test_freight_broad_search_is_denied():
    result=evaluate_freight_work_request(freight_request(broad_search=True),active_freight_gap())
    assert result.decision is FreightWorkDecision.DENY
    assert "broad_freight_search_frozen" in result.reasons

def test_freight_generic_tms_hunt_is_denied():
    result=evaluate_freight_work_request(freight_request(category="GENERIC_TMS"),active_freight_gap())
    assert result.decision is FreightWorkDecision.DENY
    assert "generic_freight_subsystem_blocked" in result.reasons

def test_freight_work_requires_named_gap_and_stop_condition():
    result=evaluate_freight_work_request(
        freight_request(gap_id="",stop_condition=""),
        active_freight_gap(gap_id=""),
    )
    assert result.decision is FreightWorkDecision.DENY
    assert "named_gap_id_required" in result.reasons
    assert "stop_condition_required" in result.reasons

def test_freight_work_must_link_to_exp001():
    result=evaluate_freight_work_request(freight_request(stage_gate="EXP-999"),active_freight_gap())
    assert result.decision is FreightWorkDecision.DENY
    assert "freight_work_must_link_to_exp001" in result.reasons
