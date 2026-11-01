"""Behavioral acceptance of the existing pipeline on a fictional first buyer."""
from decimal import Decimal, ROUND_HALF_UP

from freight.commercial import historical_first_customer_rehearsal as rehearsal


def test_first_customer_runs_actual_proof_chain_and_current_thirty_percent_offer():
    out = rehearsal.run_first_customer_rehearsal()
    assert out["synthetic"] is True
    assert out["population_invoice_count"] == 8
    assert out["metrics"]["validated_finding_cents"] == 32_500
    assert out["metrics"]["realized_cents"] == 27_500
    assert out["metrics"]["fee_eligible_realized_cents"] == 7_500
    final = out["contingency_fee_after_reversal"]
    independently_expected = int((Decimal(7_500) * Decimal("0.30")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP))
    assert final["recovery_fee_cents"] == independently_expected == 2_250
    assert final["customer_net_recovery_cents"] == 25_250
    assert final["billing_authorized"] is False
    assert out["carrier_action_external_action_performed"] is False
    assert out["commercial_value_claimed"] is False
    assert out["contingency_engagement"]["external_action_authorized"] is False
    assert "pilot_fixed_fee_usd" not in out


def test_reversal_restart_and_repeated_import_cannot_double_bill():
    out = rehearsal.run_first_customer_rehearsal()
    before, after = out["contingency_fee_before_reversal"], out["contingency_fee_after_reversal"]
    assert before["recovery_fee_cents"] == 3_000
    assert before["recovery_fee_cents"] - after["recovery_fee_cents"] == 750
    assert before["settlement_snapshot_hash"] != after["settlement_snapshot_hash"]
    assert out["persistent_reporting"]["stale_report_rejected"] is True
    assert out["restart_and_replay"]["unchanged_snapshot"] is True
    assert out["restart_and_replay"]["claim_replay_already_present"] == 2
    assert out["restart_and_replay"]["fee_replay_identical"] is True


def test_missing_authority_and_duplicate_source_are_explicitly_rejected_or_held():
    out = rehearsal.run_first_customer_rehearsal()
    checks = out["adversarial_receipts"]
    assert checks["duplicate_charge"]["state"] == "BLOCKED"
    assert checks["missing_source_document"]["state"] == "BLOCKED"
    assert checks["conflicting_rates"]["validated_cents"] == 0
    assert checks["unsupported_category"]["fee_eligible_cents"] == 0
    assert checks["unapproved_fee"]["rejected"] is True
    assert checks["wrong_audit_fee"]["rejected"] is True


def test_fictional_first_customer_replay_is_deterministic():
    assert rehearsal.run_first_customer_rehearsal() == rehearsal.run_first_customer_rehearsal()


def test_report_keeps_unsupported_and_unrealized_amounts_visible():
    out = rehearsal.run_first_customer_rehearsal()
    metrics = out["metrics"]
    assert metrics["held_finding_count"] == 1
    assert metrics["held_discrepancy_cents"] == 40_000
    assert metrics["supported_unrealized_cents"] == 5_000
    from freight.pilot_reporting import PilotMetrics, render_markdown
    report = render_markdown(PilotMetrics(**metrics))
    assert "Held source findings: 1 ($400.00 unverified candidate)" in report
    assert "Supported but unrealized: **$50.00**" in report
    assert "Unresolved reviewed findings: 0" not in report
