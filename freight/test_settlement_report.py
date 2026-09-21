"""Synthetic accounting cases for persistent report integration."""
import json
from dataclasses import replace

import pytest

from freight.contracts import (
    AuthorityRef, PopulationRow, VALIDATED, canonical_hash, freeze_population,
    freeze_truth, make_finding, open_incumbent_output, seal_incumbent_submission,
)
from freight.pilot_reporting import FindingReview, ReviewDisposition
from freight.settlement_report import (
    ClaimFindingBinding, assert_report_current, build_persistent_pilot_report,
    render_persistent_markdown,
)
from freight.settlement_store import (
    CounterEventRecord, RecoveryClaim, SettlementEventRecord, SettlementStore,
)


def case(tmp_path, *, incumbent_ids=(), currency="USD"):
    population = freeze_population("buyer", "unit", "synthetic population", [
        PopulationRow(f"invoice-{i}", f"shipment-{i}", "customer", "carrier", currency, f"source-{i}")
        for i in range(2)
    ])
    findings = [make_finding(
        finding_id=f"finding-{i}", buyer_id="buyer", business_unit="unit",
        invoice_id=f"invoice-{i}", shipment_id=f"shipment-{i}", customer_id="customer",
        carrier_id="carrier", currency=currency, authority_id="authority",
        expected_cents=10000, actual_cents=12500, status=VALIDATED,
    ) for i in range(2)]
    truth = freeze_truth(population, [
        AuthorityRef("authority", "buyer", "unit", "customer", "carrier", currency, "authority-source"),
    ], findings)
    incumbent = open_incumbent_output(
        population=population, truth=truth,
        submission=seal_incumbent_submission(population, "incumbent-source"), finding_ids=incumbent_ids,
    )
    store = SettlementStore(tmp_path / "settlements.sqlite3", buyer_id="buyer", business_unit="unit")
    return truth, incumbent, store


def claim_for(finding, *, disqualified=False):
    return RecoveryClaim(
        "claim-" + finding.finding_id, finding.invoice_id, finding.carrier_id, finding.customer_id,
        finding.currency, finding.validated_cents, "2026-09-01T00:00:00Z", finding.proof_hash, disqualified,
    )


def add_claim(store, finding, *, disqualified=False):
    claim = claim_for(finding, disqualified=disqualified)
    store.create_claim(claim)
    return ClaimFindingBinding(claim.claim_id, finding.finding_id, finding.proof_hash)


def pay(store, finding, *, event_id="payment-1", cents=2500, payer="carrier", reference=None):
    store.ingest_event(SettlementEventRecord(
        event_id, reference or finding.invoice_id, payer, "customer", finding.currency,
        cents, "2026-09-02T00:00:00Z", "settlement-source-" + event_id,
    ))
    store.review_allocate(
        allocation_id="allocation-" + event_id, claim_id="claim-" + finding.finding_id,
        event_id=event_id, amount_cents=cents, created_at="2026-09-02T01:00:00Z",
    )


def return_payment(store, *, cents=2500, counter_id="return-1", apply=True):
    store.ingest_counter(CounterEventRecord(
        counter_id, "payment-1", "USD", cents, "2026-09-03T00:00:00Z", "return-source-" + counter_id,
    ))
    if apply:
        return store.auto_apply_counter(counter_id, created_at="2026-09-03T01:00:00Z")


def test_partial_return_reduces_realized_and_fee_amounts_without_mutating_history(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    before = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    return_payment(store, cents=600)
    after = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert (before.metrics.realized_cents, before.metrics.fee_eligible_realized_cents) == (2500, 2500)
    assert (after.metrics.realized_cents, after.metrics.fee_eligible_realized_cents) == (1900, 1900)
    assert before.metrics.validated_finding_cents == after.metrics.validated_finding_cents == 5000
    assert before.settlement_snapshot_hash != after.settlement_snapshot_hash
    assert before.report_hash != after.report_hash
    assert json.loads(before.settlement_snapshot_json)["tables"]["reversal_edges"] == []
    assert "net of applied returns/reversals" in render_persistent_markdown(after)


def test_full_return_and_replacement_payment_reconcile_to_current_net(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    return_payment(store)
    returned = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert returned.metrics.realized_cents == returned.metrics.fee_eligible_realized_cents == 0
    pay(store, truth.findings[0], event_id="replacement")
    replacement = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert replacement.metrics.realized_cents == store.realized_cents() == 2500
    assert replacement.metrics.fee_eligible_realized_cents == store.fee_eligible_cents() == 2500


def test_deterministic_report_does_not_write_or_reallocate(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    snapshot = store.report_snapshot_json()
    first = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    second = build_persistent_pilot_report(
        truth, incumbent, store, (binding,), expected_snapshot_hash=first.settlement_snapshot_hash,
    )
    assert first == second
    assert store.report_snapshot_json() == snapshot
    assert_report_current(first, store)


def test_existing_return_must_be_resolved_before_recovery_is_reported(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    return_payment(store, cents=100, apply=False)
    with pytest.raises(ValueError, match="unresolved counter"):
        build_persistent_pilot_report(truth, incumbent, store, (binding,))


def test_ambiguous_batch_return_cannot_leave_optimistic_report_totals(tmp_path):
    truth, incumbent, store = case(tmp_path)
    bindings = tuple(add_claim(store, finding) for finding in truth.findings)
    store.ingest_event(SettlementEventRecord(
        "payment-1", "batch-reference", "carrier", "customer", "USD", 5000,
        "2026-09-02T00:00:00Z", "batch-source",
    ))
    for index, binding in enumerate(bindings):
        store.review_allocate(allocation_id=f"allocation-{index}", claim_id=binding.claim_id,
                              event_id="payment-1", amount_cents=2500, created_at="2026-09-02T01:00:00Z")
    assert return_payment(store, cents=100).status == "REVIEW"
    with pytest.raises(ValueError, match="unresolved counter"):
        build_persistent_pilot_report(truth, incumbent, store, bindings)


def test_incumbent_recovery_stays_non_fee_eligible_after_return(tmp_path):
    truth, incumbent, store = case(tmp_path, incumbent_ids=("finding-0",))
    binding = add_claim(store, truth.findings[0], disqualified=True)
    pay(store, truth.findings[0])
    return_payment(store, cents=500)
    report = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert report.metrics.realized_cents == 2000
    assert report.metrics.fee_eligible_realized_cents == 0


def test_incumbent_claim_with_fee_eligibility_is_rejected(tmp_path):
    truth, incumbent, store = case(tmp_path, incumbent_ids=("finding-0",))
    binding = add_claim(store, truth.findings[0])
    with pytest.raises(ValueError, match="incumbent claim"):
        build_persistent_pilot_report(truth, incumbent, store, (binding,))


@pytest.mark.parametrize("change, message", [
    ({"source_hash": "unrelated-claim-evidence"}, "exact frozen finding proof"),
    ({"reference": "other-invoice"}, "identity/currency"),
    ({"payer_id": "other-carrier"}, "identity/currency"),
    ({"currency": "EUR"}, "identity/currency"),
    ({"amount_cents": 2600}, "capacity"),
])
def test_arbitrary_claim_cannot_become_frozen_finding_proof(tmp_path, change, message):
    truth, incumbent, store = case(tmp_path)
    finding = truth.findings[0]
    claim = replace(claim_for(finding), **change)
    store.create_claim(claim)
    binding = ClaimFindingBinding(claim.claim_id, finding.finding_id, finding.proof_hash)
    with pytest.raises(ValueError, match=message):
        build_persistent_pilot_report(truth, incumbent, store, (binding,))


def test_wrong_settlement_party_is_rejected_before_review_allocation(tmp_path):
    truth, _incumbent, store = case(tmp_path)
    add_claim(store, truth.findings[0])
    with pytest.raises(ValueError, match="payer/payee mismatch"):
        pay(store, truth.findings[0], payer="different-carrier")
    assert store.realized_cents() == 0


def test_duplicate_and_missing_bindings_are_rejected(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    with pytest.raises(ValueError, match="one-to-one"):
        build_persistent_pilot_report(truth, incumbent, store, (binding, binding))
    with pytest.raises(ValueError, match="missing its explicit binding"):
        build_persistent_pilot_report(truth, incumbent, store, ())


def test_truth_proof_changes_and_wrong_scope_are_rejected(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    with pytest.raises(ValueError, match="frozen finding proof"):
        build_persistent_pilot_report(truth, incumbent, store, (replace(binding, finding_proof_hash="stale"),))
    changed_truth = replace(truth, findings=(replace(truth.findings[0], actual_cents=13000), truth.findings[1]))
    with pytest.raises(ValueError, match="proof hash mismatch"):
        build_persistent_pilot_report(changed_truth, incumbent, store, (binding,))
    other = SettlementStore(store.path, buyer_id="other-buyer", business_unit="unit")
    with pytest.raises(ValueError, match="store scope mismatch"):
        build_persistent_pilot_report(truth, incumbent, other, (binding,))


def test_non_usd_report_and_unresolved_claim_review_are_rejected(tmp_path):
    truth, incumbent, store = case(tmp_path, currency="EUR")
    binding = add_claim(store, truth.findings[0])
    with pytest.raises(ValueError, match="USD"):
        build_persistent_pilot_report(truth, incumbent, store, (binding,))
    with pytest.raises(ValueError, match="unresolved or false-positive"):
        build_persistent_pilot_report(truth, incumbent, store, (binding,), (
            FindingReview("finding-0", ReviewDisposition.UNRESOLVED),
        ))


def test_stale_snapshot_is_rejected_before_reuse(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    report = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    return_payment(store)
    with pytest.raises(ValueError, match="snapshot changed"):
        assert_report_current(report, store)
    with pytest.raises(ValueError, match="snapshot changed"):
        build_persistent_pilot_report(
            truth, incumbent, store, (binding,), expected_snapshot_hash=report.settlement_snapshot_hash,
        )


def test_snapshot_is_scope_bound_and_unrelated_buyer_writes_do_not_change_it(tmp_path):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    report = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    other = SettlementStore(store.path, buyer_id="other-buyer", business_unit="unit")
    other.create_claim(claim_for(truth.findings[0]))
    assert_report_current(report, store)
    snapshot = json.loads(store.report_snapshot_json())
    assert all(row["buyer_id"] == "buyer" for rows in snapshot["tables"].values() for row in rows)


def test_snapshot_tables_share_one_database_revision_during_concurrent_return(tmp_path, monkeypatch):
    truth, incumbent, store = case(tmp_path)
    binding = add_claim(store, truth.findings[0])
    pay(store, truth.findings[0])
    writer = SettlementStore(store.path, buyer_id="buyer", business_unit="unit")
    original_connect = store._connect
    wrote_return = False

    def connect_with_concurrent_writer():
        conn = original_connect()

        def trace(statement):
            nonlocal wrote_return
            if "SELECT * FROM allocations" in statement and not wrote_return:
                wrote_return = True
                return_payment(writer)

        conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(store, "_connect", connect_with_concurrent_writer)
    before = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert wrote_return
    assert before.metrics.realized_cents == 2500
    assert json.loads(before.settlement_snapshot_json)["tables"]["counter_events"] == []
    after = build_persistent_pilot_report(truth, incumbent, store, (binding,))
    assert after.metrics.realized_cents == 0
    assert canonical_hash(json.loads(after.settlement_snapshot_json)) == after.settlement_snapshot_hash
