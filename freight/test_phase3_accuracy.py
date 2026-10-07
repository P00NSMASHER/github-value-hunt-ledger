from copy import deepcopy
import json
from pathlib import Path

import pytest

from freight.accuracy_benchmark import (
    build_accuracy_report,
    load_fixture,
    report_dict,
    validate_accuracy_report,
)
from freight.accuracy_evidence import (
    validate_baseline,
    validate_fixture_against_baseline,
    validate_runtime_report,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "freight" / "fixtures" / "phase3_accuracy_gold_v1.json"
BASELINE = ROOT / "freight" / "PHASE3_ACCURACY_BASELINE.json"


def test_phase3_gold_set_is_exact_and_fail_closed():
    fixture = load_fixture(FIXTURE)
    report = build_accuracy_report(fixture)
    validate_accuracy_report(report)

    assert report.gold_id == "recoveryos-phase3-accuracy-v1"
    assert len(report.gold_fixture_hash) == 64
    assert report.rating["case_count"] == 20
    assert report.rating["false_positive"] == 0
    assert report.rating["false_negative"] == 0
    assert report.rating["precision"] == 1.0
    assert report.rating["recall"] == 1.0
    assert report.rating["exact_financial_state_accuracy"] == 1.0
    assert report.rating["review_routing_accuracy"] == 1.0
    assert report.authority_resolution["accuracy"] == 1.0
    assert report.incumbent_attribution["accuracy"] == 1.0
    assert report.incumbent_attribution["duplicate_suppression_accuracy"] == 1.0
    assert report.payment_lifecycle["valid_state_and_money_accuracy"] == 1.0
    assert report.payment_lifecycle["invalid_transition_rejection_accuracy"] == 1.0
    assert report.evidence_traceability["accuracy"] == 1.0


def test_gold_set_spans_every_supported_mode():
    fixture = load_fixture(FIXTURE)
    modes = {case["record"]["mode"] for case in fixture["rating_cases"]}
    assert modes == {"PARCEL", "LTL", "TL", "INTERMODAL", "AIR", "OCEAN"}


def test_tampered_gold_dollar_expectation_is_detected():
    fixture = deepcopy(load_fixture(FIXTURE))
    fixture["rating_cases"][0]["expected"]["variance_cents"] += 1
    report = build_accuracy_report(fixture)
    with pytest.raises(ValueError, match="rating metric below exact gold conformance"):
        validate_accuracy_report(report)


def test_tampered_attribution_expectation_is_detected():
    fixture = deepcopy(load_fixture(FIXTURE))
    fixture["attribution"]["candidates"][3]["expected_net_new_cents"] = 2999
    report = build_accuracy_report(fixture)
    with pytest.raises(ValueError, match="incumbent-attribution gold conformance"):
        validate_accuracy_report(report)


def test_tampered_payment_expectation_is_detected():
    fixture = deepcopy(load_fixture(FIXTURE))
    settled = next(case for case in fixture["payment_cases"] if case["id"] == "settled")
    settled["expected_settled_cents"] = 9999
    report = build_accuracy_report(fixture)
    with pytest.raises(ValueError, match="payment lifecycle state/money gold conformance"):
        validate_accuracy_report(report)


def test_committed_accuracy_baseline_matches_frozen_fixture_and_runtime():
    fixture = load_fixture(FIXTURE)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    report = build_accuracy_report(fixture)
    assert report.gold_fixture_hash == "6da44c566a8e7d495b2e7fce80508529fa598232077b690f60c4b1804b2274a7"
    assert report.report_hash == "83f642e4448a0c17735efdcb046325ce50a08728298084dc981db3df0fd57ecd"
    assert validate_baseline(baseline) == []
    assert validate_fixture_against_baseline(fixture, baseline) == []
    assert validate_runtime_report(report_dict(report), baseline) == []
    assert baseline["external_blind_validation"]["state"] == "PENDING_EXTERNAL_CUSTOMER_EVIDENCE"


def test_accuracy_baseline_cannot_silently_accept_fixture_replacement():
    fixture = load_fixture(FIXTURE)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline["gold_fixture_hash"] = "0" * 64
    errors = validate_fixture_against_baseline(fixture, baseline)
    assert "fixture hash differs from frozen accuracy baseline" in errors
