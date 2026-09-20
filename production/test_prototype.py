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
