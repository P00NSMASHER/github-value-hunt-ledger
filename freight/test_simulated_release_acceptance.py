"""Rehearsal never mints real-customer approvals, even with forged proof-looking hashes."""
from freight.simulated_release_acceptance import run_simulated_acceptance

def test_fabricated_roles_bank_and_rates_cannot_approve_real_release():
    r=run_simulated_acceptance()
    assert r["kind"]=="SYNTHETIC_ONLY_NO_REAL_BANK_OR_RATE_OR_ADJUDICATION"
    assert r["scenario_count"]==7
    assert r["all_controls_pass"] is True
    assert all(r["control_results"].values())
    assert r["source_attested_bank_minor"]==18700
    assert r["externally_verified_bank_minor"]==0
    assert r["claimable_freight_recovery_minor"]==0
    assert r["realized_freight_recovery_minor"]==0
    assert r["simulation_conditional_precision"]==1.0
    assert r["external_real_freight_precision"] is None
    assert r["original_real_cases_unknown"]==110
    assert r["production_release_status"]=="RELEASE_HOLD"
    assert r["true_external_approval_observed"] is False
    assert r==run_simulated_acceptance()
