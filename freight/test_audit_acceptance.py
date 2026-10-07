from copy import deepcopy
import json
from pathlib import Path

from freight.audit_acceptance import (
    build_report,
    recoveryos_output_hash,
    sample_hash,
    truth_manifest_hash,
    validate_pilot,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "freight" / "AUDIT_ACCEPTANCE_POLICY_V2.json"


def _policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def _case(index: int, truth: str, prediction: str, stratum: str) -> dict:
    truth_cents = 1000 if truth == "POSITIVE" else 0
    predicted_cents = 1000 if prediction == "POSITIVE" else (0 if prediction == "NEGATIVE" else None)
    return {
        "case_id": f"case-{index:04d}",
        "stratum_key": stratum,
        "truth_label": truth,
        "truth_variance_cents": truth_cents,
        "predicted_label": prediction,
        "predicted_variance_cents": predicted_cents,
        "confidence_ppm": 990000 if prediction != "REVIEW" else 600000,
        "authority_state": "VERIFIED",
        "source_complete": True,
        "economic_issue_id": f"issue-{index:04d}",
        "truth_incumbent_known": False,
        "predicted_net_new_cents": 1000 if prediction == "POSITIVE" else 0,
        "reviewer_a_label": truth if index < 50 else None,
        "reviewer_b_label": truth if index < 50 else None,
        "adjudication_note": None,
    }


def _pilot() -> dict:
    cases = []
    for index in range(240):
        truth = "POSITIVE" if index < 60 else "NEGATIVE"
        prediction = truth
        if index >= 220:
            prediction = "REVIEW"
        stratum = "LTL|A|MID" if index < 120 else "PARCEL|B|LOW"
        cases.append(_case(index, truth, prediction, stratum))

    return {
        "schema_version": 2,
        "protocol_id": "recoveryos-blind-audit-acceptance-v2",
        "roles": {
            "truth_owner_id": "truth-owner",
            "reviewer_a_id": "reviewer-a",
            "reviewer_b_id": "reviewer-b",
            "recoveryos_operator_id": "recoveryos-operator",
        },
        "blindness": {
            "truth_owner_saw_recoveryos_before_truth_freeze": False,
            "recoveryos_team_saw_truth_before_output_freeze": False,
            "sample_selected_before_recoveryos_output": True,
            "truth_owner_independent_of_recoveryos_builder": True,
        },
        "timeline": {
            "population_frozen_at": "2026-10-01T00:00:00Z",
            "truth_frozen_at": "2026-10-03T00:00:00Z",
            "recoveryos_output_frozen_at": "2026-10-02T00:00:00Z",
            "incumbent_output_frozen_at": "2026-10-02T00:00:00Z",
            "joint_unseal_at": "2026-10-04T00:00:00Z",
        },
        "population": {
            "population_size": 240,
            "sample_size": 240,
            "population_hash": "a" * 64,
            "sample_hash": sample_hash([case["case_id"] for case in cases]),
            "truth_manifest_hash": truth_manifest_hash(cases),
            "recoveryos_output_hash": recoveryos_output_hash(cases),
            "incumbent_output_hash": "b" * 64,
        },
        "sampling": {
            "method": "CENSUS",
            "seed": None,
            "strata": [
                {
                    "key": "LTL|A|MID",
                    "population_count": 120,
                    "sample_target": 120,
                },
                {
                    "key": "PARCEL|B|LOW",
                    "population_count": 120,
                    "sample_target": 120,
                },
            ],
        },
        "cases": cases,
    }


def _refresh_hashes(pilot: dict) -> None:
    pilot["population"]["sample_hash"] = sample_hash(
        [case["case_id"] for case in pilot["cases"]]
    )
    pilot["population"]["truth_manifest_hash"] = truth_manifest_hash(
        pilot["cases"]
    )
    pilot["population"]["recoveryos_output_hash"] = recoveryos_output_hash(
        pilot["cases"]
    )


def test_policy_is_machine_valid():
    assert validate_policy(_policy()) == []


def test_clean_blind_population_can_reach_quality_proven():
    report = build_report(_pilot(), _policy())
    assert report["status"] == "AUDIT_QUALITY_PROVEN"
    assert report["failed_gates"] == []
    assert report["metrics"]["classification"]["false_positive"] == 0
    assert report["metrics"]["classification"]["false_negative"] == 0
    assert report["metrics"]["reviewer_agreement"]["kappa"] == 1.0
    assert report["metrics"]["calibration"]["ece"] < 0.02


def test_blindness_violation_invalidates_method_before_scoring():
    pilot = _pilot()
    pilot["blindness"]["truth_owner_saw_recoveryos_before_truth_freeze"] = True
    errors = validate_pilot(pilot, _policy())
    assert any("blindness violation" in error for error in errors)


def test_truth_hash_tamper_is_detected():
    pilot = _pilot()
    pilot["cases"][0]["truth_variance_cents"] += 1
    errors = validate_pilot(pilot, _policy())
    assert "truth_manifest_hash does not match case truth" in errors


def test_output_hash_tamper_is_detected():
    pilot = _pilot()
    pilot["cases"][0]["predicted_variance_cents"] += 1
    errors = validate_pilot(pilot, _policy())
    assert "recoveryos_output_hash does not match case output" in errors


def test_false_positive_dollars_can_fail_even_when_case_accuracy_looks_high():
    pilot = _pilot()
    target = next(
        case
        for case in pilot["cases"]
        if case["truth_label"] == "NEGATIVE"
        and case["predicted_label"] == "NEGATIVE"
    )
    target["predicted_label"] = "POSITIVE"
    target["predicted_variance_cents"] = 100000
    target["predicted_net_new_cents"] = 100000
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["status"] == "INSUFFICIENT_OR_FAILED"
    assert "false_positive_dollars" in report["failed_gates"]


def test_large_false_negative_dollar_miss_fails_dollar_gate():
    pilot = _pilot()
    target = pilot["cases"][0]
    target["truth_variance_cents"] = 250000
    target["predicted_label"] = "NEGATIVE"
    target["predicted_variance_cents"] = 0
    target["predicted_net_new_cents"] = 0
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["status"] == "INSUFFICIENT_OR_FAILED"
    assert "false_negative_dollars" in report["failed_gates"]


def test_unresolved_authority_cannot_auto_decide_money():
    pilot = _pilot()
    pilot["cases"][0]["authority_state"] = "UNRESOLVED"
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["metrics"]["sample"]["unsupported_auto_decisions"] == 1
    assert "unsupported_auto" in report["failed_gates"]


def test_incumbent_known_value_cannot_be_credited_as_net_new():
    pilot = _pilot()
    pilot["cases"][0]["truth_incumbent_known"] = True
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["metrics"]["dollars"]["incumbent_credit_leakage_cents"] == 1000
    assert "incumbent_leakage" in report["failed_gates"]


def test_duplicate_economic_issue_cannot_receive_net_new_credit_twice():
    pilot = _pilot()
    pilot["cases"][1]["economic_issue_id"] = pilot["cases"][0]["economic_issue_id"]
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["metrics"]["dollars"]["duplicate_net_new_leakage_cents"] == 1000
    assert "duplicate_leakage" in report["failed_gates"]


def test_underpowered_sample_is_not_quality_proven():
    pilot = _pilot()
    pilot["cases"] = pilot["cases"][:100]
    pilot["population"]["population_size"] = 100
    pilot["population"]["sample_size"] = 100
    pilot["sampling"]["strata"] = [
        {
            "key": "LTL|A|MID",
            "population_count": 100,
            "sample_target": 100,
        }
    ]
    for case in pilot["cases"]:
        case["stratum_key"] = "LTL|A|MID"
    _refresh_hashes(pilot)
    report = build_report(pilot, _policy())
    assert report["status"] == "INSUFFICIENT_OR_FAILED"
    assert "sample_adjudicated" in report["failed_gates"]


def test_reviewer_disagreement_requires_documented_adjudication():
    pilot = _pilot()
    pilot["cases"][0]["reviewer_b_label"] = "NEGATIVE"
    errors = validate_pilot(pilot, _policy())
    assert any("reviewer disagreement requires adjudication_note" in error for error in errors)
