"""Fictional first-customer pilot against actual RecoveryOS blind-audit policy.

This is a methodological smoke harness, NOT customer-owned blinded evidence.
A successful internal policy report is deliberately remapped to synthetic-only,
never made a real buyer-facing audit-quality claim.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from freight.audit_acceptance import (
    build_report, recoveryos_output_hash, sample_hash,
    truth_manifest_hash, validate_pilot,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "freight/AUDIT_ACCEPTANCE_POLICY_V2.json"


def make_fictional_pilot() -> dict:
    cases = []
    for i in range(240):
        truth = "POSITIVE" if i < 60 else "NEGATIVE"
        prediction = truth if i < 220 else "REVIEW"
        stratum = "LTL|SIMULATED|MID" if i < 120 else "PARCEL|SIMULATED|LOW"
        reviewed = i in set(range(25)) | set(range(60,85))
        cases.append({
            "case_id": f"FICTIONAL-PILOT-{i:04d}",
            "stratum_key": stratum,
            "truth_label": truth,
            "truth_variance_cents": 1000 if truth=="POSITIVE" else 0,
            "predicted_label": prediction,
            "predicted_variance_cents": 1000 if prediction=="POSITIVE" else (0 if prediction=="NEGATIVE" else None),
            "confidence_ppm": 990000 if prediction!="REVIEW" else 600000,
            "authority_state": "VERIFIED", "source_complete": True,
            "economic_issue_id": f"SYNTHETIC-ISSUE-{i:04d}",
            "truth_incumbent_known": False,
            "predicted_net_new_cents": 1000 if prediction=="POSITIVE" else 0,
            "reviewer_a_label": truth if reviewed else None,
            "reviewer_b_label": truth if reviewed else None,
            "adjudication_note": None,
        })
    return {
        "schema_version":2,"protocol_id":"recoveryos-blind-audit-acceptance-v2",
        "roles":{
            "truth_owner_id":"FICTIONAL-TRUTH-OWNER",
            "reviewer_a_id":"FICTIONAL-REVIEWER-A",
            "reviewer_b_id":"FICTIONAL-REVIEWER-B",
            "recoveryos_operator_id":"FICTIONAL-OPERATOR",
        },
        "blindness":{
            "truth_owner_saw_recoveryos_before_truth_freeze":False,
            "recoveryos_team_saw_truth_before_output_freeze":False,
            "sample_selected_before_recoveryos_output":True,
            "dual_review_selected_before_recoveryos_output":True,
            "truth_owner_independent_of_recoveryos_builder":True,
        },
        "timeline":{
            "population_frozen_at":"2026-10-01T00:00:00Z",
            "truth_frozen_at":"2026-10-03T00:00:00Z",
            "recoveryos_output_frozen_at":"2026-10-02T00:00:00Z",
            "incumbent_output_frozen_at":"2026-10-02T00:00:00Z",
            "joint_unseal_at":"2026-10-04T00:00:00Z",
        },
        "population":{
            "population_size":240,"sample_size":240,"population_hash":"a"*64,
            "sample_hash":sample_hash([c["case_id"] for c in cases]),
            "truth_manifest_hash":truth_manifest_hash(cases),
            "recoveryos_output_hash":recoveryos_output_hash(cases),
            "incumbent_output_hash":"b"*64,
        },
        "sampling":{
            "method":"CENSUS","seed":None,
            "strata":[
                {"key":"LTL|SIMULATED|MID","population_count":120,"sample_target":120},
                {"key":"PARCEL|SIMULATED|LOW","population_count":120,"sample_target":120},
            ]
        },
        "cases":cases,
    }


def rehash(pilot:dict)->None:
    cases=pilot["cases"]
    pilot["population"]["truth_manifest_hash"]=truth_manifest_hash(cases)
    pilot["population"]["recoveryos_output_hash"]=recoveryos_output_hash(cases)
    pilot["population"]["sample_hash"]=sample_hash([c["case_id"] for c in cases])


def assess_fictional_methodology(pilot:dict|None=None)->dict:
    policy=json.loads(POLICY.read_text(encoding="utf-8"))
    data=deepcopy(pilot if pilot is not None else make_fictional_pilot())
    errors=validate_pilot(data,policy)
    if errors:
        return {"status":"SYNTHETIC_INVALID_METHOD","internal_method_errors":errors,
                "external_customer_proof":"NOT_TESTED"}
    report=build_report(data,policy)
    return {
        "status":"SYNTHETIC_METHOD_SMOKE_ONLY",
        "underlying_repository_gate":report["status"],
        "failed_gates":report["failed_gates"],
        "external_customer_proof":"NOT_TESTED",
        "realized_customer_recovery":"NOT_TESTED",
        "warning":"FICTIONAL role assertions and template labels are not buyer-independent evidence.",
    }


if __name__=="__main__":
    print(json.dumps(assess_fictional_methodology(),indent=2))
