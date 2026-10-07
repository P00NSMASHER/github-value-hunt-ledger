import json
from copy import deepcopy
from pathlib import Path

from freight.customer_readiness import (
    summarize_simulation,
    validate_readiness,
    validate_simulation,
)


ROOT = Path(__file__).resolve().parents[1]
SIMULATION = ROOT / "freight" / "PHASE3_SYNTHETIC_CUSTOMER_SIMULATION_2026-10-07.json"
READINESS = ROOT / "freight" / "PHASE3_ENTERPRISE_READINESS_2026-10-07.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_synthetic_customer_simulation_is_valid_and_conservative():
    simulation = load(SIMULATION)
    assert validate_simulation(simulation) == []
    summary = summarize_simulation(simulation)
    assert summary["buyers"] == 3
    assert summary["bots"] == 12
    assert summary["decisions"] == {
        "CONDITIONAL": 6,
        "APPROVE_PILOT": 3,
        "BLOCKED": 3,
    }
    assert summary["customer_evidence"] is False
    assert summary["verdict"] == "SCOPED_PILOT_SELLABLE_ENTERPRISE_ROLLOUT_NOT_YET_READY"


def test_current_enterprise_readiness_preserves_external_customer_boundary():
    readiness = load(READINESS)
    assert validate_readiness(readiness) == []
    assert readiness["commercial_readiness"]["scoped_second_look_pilot"] == (
        "READY_WITH_BUYER_AUTHORIZATION_AND_DATA_READINESS"
    )
    assert readiness["commercial_readiness"]["broad_enterprise_rollout"] == "NOT_READY"
    assert readiness["workstreams"]["blind_real_customer_accuracy"]["state"] == "PENDING_EXTERNAL"
    assert readiness["workstreams"]["realized_recovery_customer_proof"]["state"] == "PENDING_EXTERNAL"


def test_simulated_company_must_remain_fictional():
    simulation = deepcopy(load(SIMULATION))
    simulation["buyer_archetypes"][0]["fictional"] = False
    errors = validate_simulation(simulation)
    assert any("buyer must be marked fictional" in error for error in errors)


def test_ai_simulation_must_disclose_non_independence():
    simulation = deepcopy(load(SIMULATION))
    simulation["generator"]["independent_of_builder"] = True
    errors = validate_simulation(simulation)
    assert "AI buyer simulation must disclose that it is not independent" in errors


def test_enterprise_rollout_cannot_be_self_promoted_to_ready():
    readiness = deepcopy(load(READINESS))
    readiness["commercial_readiness"]["broad_enterprise_rollout"] = "READY"
    errors = validate_readiness(readiness)
    assert "broad enterprise rollout must remain NOT_READY" in errors


def test_real_customer_proof_cannot_be_promoted_from_synthetic_simulation():
    readiness = deepcopy(load(READINESS))
    readiness["workstreams"]["blind_real_customer_accuracy"]["state"] = "COMPLETE_SYNTHETIC"
    errors = validate_readiness(readiness)
    assert any("blind_real_customer_accuracy: must remain PENDING_EXTERNAL" in error for error in errors)
