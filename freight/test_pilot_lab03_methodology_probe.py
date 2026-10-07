"""Regression tests of actual RecoveryOS blind audit acceptance module.

Only fictional role claims and tariff figures are used; passing NEVER proves
external buyer or customer-held real invoice accuracy.
"""
from copy import deepcopy

from freight.pilot_lab03_methodology_probe import (
    assess_fictional_methodology,make_fictional_pilot,rehash,
)

def test_real_acceptance_methodology_is_executable():
    result=assess_fictional_methodology()
    assert result["status"]=="SYNTHETIC_METHOD_SMOKE_ONLY",result
    assert result["underlying_repository_gate"]=="AUDIT_QUALITY_PROVEN"
    assert result["external_customer_proof"]=="NOT_TESTED"

def test_blindness_leakage_invalidates_method():
    p=make_fictional_pilot()
    p["blindness"]["truth_owner_saw_recoveryos_before_truth_freeze"]=True
    result=assess_fictional_methodology(p)
    assert result["status"]=="SYNTHETIC_INVALID_METHOD"

def test_duplicate_review_roles_invalidates_method():
    p=make_fictional_pilot()
    p["roles"]["reviewer_a_id"]=p["roles"]["truth_owner_id"]
    assert assess_fictional_methodology(p)["status"]=="SYNTHETIC_INVALID_METHOD"

def test_truth_modified_after_hash_fails_closed():
    p=make_fictional_pilot()
    p["cases"][0]["truth_variance_cents"]=5
    assert assess_fictional_methodology(p)["status"]=="SYNTHETIC_INVALID_METHOD"

def test_candidate_output_modified_after_hash_fails_closed():
    p=make_fictional_pilot()
    p["cases"][0]["predicted_variance_cents"]=500
    assert assess_fictional_methodology(p)["status"]=="SYNTHETIC_INVALID_METHOD"

def test_missing_dual_review_evidence_fails_quality():
    p=make_fictional_pilot()
    for case in p["cases"]:
        case["reviewer_a_label"]=None
        case["reviewer_b_label"]=None
    report=assess_fictional_methodology(p)
    assert report["status"]=="SYNTHETIC_METHOD_SMOKE_ONLY"
    assert report["underlying_repository_gate"]!="AUDIT_QUALITY_PROVEN"

def test_unresolved_authority_auto_positive_fails_quality():
    p=make_fictional_pilot()
    p["cases"][0]["authority_state"]="UNRESOLVED"
    p["cases"][0]["truth_label"]="UNRESOLVED"
    p["cases"][0]["truth_variance_cents"]=0
    p["cases"][0]["reviewer_a_label"]=None
    p["cases"][0]["reviewer_b_label"]=None
    p["cases"][25]["reviewer_a_label"]="POSITIVE"
    p["cases"][25]["reviewer_b_label"]="POSITIVE"
    rehash(p)
    report=assess_fictional_methodology(p)
    assert report["underlying_repository_gate"]=="QUALITY_GATE_FAILED"
    assert "unsupported_auto" in report["failed_gates"]

def test_duplicate_net_new_economic_issue_fails_quality():
    p=make_fictional_pilot()
    p["cases"][1]["economic_issue_id"]=p["cases"][0]["economic_issue_id"]
    rehash(p)
    report=assess_fictional_methodology(p)
    assert report["underlying_repository_gate"]=="QUALITY_GATE_FAILED"
    assert "duplicate_leakage" in report["failed_gates"]

def test_incumbent_known_claim_value_excluded():
    p=make_fictional_pilot()
    p["cases"][0]["truth_incumbent_known"]=True
    rehash(p)
    report=assess_fictional_methodology(p)
    assert report["underlying_repository_gate"]=="QUALITY_GATE_FAILED"
    assert "incumbent_leakage" in report["failed_gates"]

def test_unsampled_large_population_is_insufficient():
    p=make_fictional_pilot()
    p["population"]["population_size"]=10000
    p["sampling"]["method"]="STRATIFIED_RANDOM"
    p["sampling"]["seed"]="FICTIONAL-FROZEN-SEED"
    for s in p["sampling"]["strata"]:
        s["population_count"]=5000
    report=assess_fictional_methodology(p)
    assert report["underlying_repository_gate"]=="INSUFFICIENT_EVIDENCE"

def test_reviewer_disagreement_without_adjudication_invalid():
    p=make_fictional_pilot()
    p["cases"][0]["reviewer_b_label"]="NEGATIVE"
    assert assess_fictional_methodology(p)["status"]=="SYNTHETIC_INVALID_METHOD"
