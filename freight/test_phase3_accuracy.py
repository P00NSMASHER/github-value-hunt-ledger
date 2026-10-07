from copy import deepcopy
from pathlib import Path

import pytest

from freight.accuracy_benchmark import (
    build_accuracy_report,
    load_fixture,
    validate_accuracy_report,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "freight" / "fixtures" / "phase3_accuracy_gold_v1.json"


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
