import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from freight.competitive_matrix import (
    summarize_matrix,
    validate_competitor_evidence,
    validate_matrix,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "freight" / "PHASE3_COMPETITIVE_MATRIX_2026-10-07.json"
EVIDENCE_PATH = ROOT / "freight" / "PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json"


def load_matrix():
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def load_evidence():
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_current_competitive_evidence_and_matrix_are_valid():
    matrix = load_matrix()
    evidence = load_evidence()
    assert validate_matrix(matrix) == []
    assert validate_competitor_evidence(evidence, as_of=date(2026, 10, 7)) == []


def test_current_matrix_is_critical_not_self_awarded():
    summary = summarize_matrix(load_matrix())
    assert summary.recoveryos_rank > 1
    assert summary.weighted_scores["RecoveryOS"] == 56.0
    assert summary.ranking[0] == "nVision Global"
    assert set(summary.recoveryos_number_one_dimensions) == {
        "second_look_attribution",
        "evidence_provenance",
    }
    assert len(summary.recoveryos_gap_dimensions) == 12


def test_weights_cannot_drift_from_100():
    matrix = deepcopy(load_matrix())
    matrix["dimensions"][0]["weight"] += 1
    assert "dimension weights must sum to 100" in validate_matrix(matrix)


def test_score_must_stay_inside_defined_scale():
    matrix = deepcopy(load_matrix())
    matrix["vendors"]["RecoveryOS"]["scores"]["payment_execution"]["score"] = 6
    errors = validate_matrix(matrix)
    assert any("score must be integer 0..5" in error for error in errors)


def test_competitor_evidence_expires_instead_of_becoming_evergreen_truth():
    evidence = load_evidence()
    errors = validate_competitor_evidence(evidence, as_of=date(2027, 1, 6))
    assert "competitor evidence is stale" in errors


def test_missing_competitor_source_is_rejected():
    evidence = deepcopy(load_evidence())
    evidence["competitors"]["Loop"]["sources"] = []
    errors = validate_competitor_evidence(evidence, as_of=date(2026, 10, 7))
    assert any("Loop: at least one first-party source required" in error for error in errors)
