"""Red-team guard against provisional fees on unresolved source-credit returns.

All documents, people, amounts and issuer names below are synthetic. This
suite never authenticates a bank, bills a fee, or performs a real transaction.
"""
from hashlib import sha256

from freight.currency_reporting import build_currency_settlement_report
from freight.recovery_resilience import RecoveryScenario, evaluate_recovery_scenario
from freight.settlement_store import (
    ALLOCATED, REVERSED, REVIEW, RecoveryClaim, SettlementEventRecord,
    CounterEventRecord, SettlementStore,
)


def h(text: str) -> str:
    return sha256(text.encode("ascii")).hexdigest()


def store(tmp_path) -> SettlementStore:
    return SettlementStore(
        tmp_path / "synthetic-fee-quarantine.sqlite3",
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
    )


def claim(label: str, reference: str, amount: int) -> RecoveryClaim:
    return RecoveryClaim(
        label, reference, "SYN-CARRIER", "SYN-BUYER", "USD", amount,
        "2026-09-01T12:00:00Z", h("source finding:" + label),
    )


def credit(label: str, reference: str, amount: int) -> SettlementEventRecord:
    return SettlementEventRecord(
        label, reference, "SYN-CARRIER", "SYN-BUYER", "USD", amount,
        "2026-09-02T10:00:00Z", h("source credit:" + label),
        "SYNTHETIC_NOT_BANK_VERIFIED",
    )


def returned(label: str, event_id: str, amount: int) -> CounterEventRecord:
    return CounterEventRecord(
        label, event_id, "USD", amount, "2026-09-03T12:00:00Z",
        h("source return:" + label), "SYNTHETIC_PENDING_RETURN",
    )


def allocate(s: SettlementStore, label: str, event_id: str, amount: int) -> None:
    assert s.review_allocate(
        allocation_id="SYN-ALLOCATION-" + label,
        claim_id=label, event_id=event_id, amount_cents=amount,
        created_at="2026-09-02T11:00:00Z",
    ) == ALLOCATED


def view(label: str, reference: str, amount: int) -> RecoveryScenario:
    return RecoveryScenario(
        case_id=reference, claim_id=label,
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        payer_id="SYN-CARRIER", payee_id="SYN-BUYER",
        currency="USD", disputed_cents=amount,
        issued_at="2026-09-01T12:00:00Z",
        source_invoice_sha256=h("original invoice:" + label),
        source_finding_sha256=h("source finding:" + label),
    )


def inspect(s: SettlementStore, label: str, reference: str, amount: int):
    result = evaluate_recovery_scenario(
        view(label, reference, amount), as_of="2026-10-22", store=s,
    )
    assert result.externally_approved_case is False
    assert result.independently_verified_cash_cents == 0
    assert result.customer_fee_billable_cents == 0
    assert result.payment_actions_performed == 0
    assert result.carrier_contact_attempts == 0
    return result


def test_pending_partial_return_holds_fee_across_all_three_views(tmp_path):
    s = store(tmp_path)
    s.create_claim(claim("A", "INV-A", 10000))
    s.ingest_event(credit("E", "INV-A", 10000))
    allocate(s, "A", "E", 10000)
    before = build_currency_settlement_report(s)
    assert before.by_currency[0].declared_fee_eligible_net_cents == 10000
    assert s.fee_eligible_cents("A") == 10000
    s.ingest_counter(returned("R", "E", 2000))
    assert s.realized_cents("A") == 10000  # immutable declared credit
    assert s.fee_eligible_cents("A") == 0
    assert s.fee_eligible_cents() == 0
    row = build_currency_settlement_report(s).by_currency[0]
    assert row.declared_net_allocated_cents == 10000
    assert row.declared_fee_eligible_net_cents == 0
    assert row.unresolved_counter_cents == 2000
    out = inspect(s, "A", "INV-A", 10000)
    assert out.state == "RETURN_REVERSAL_REVIEW_HOLD"
    assert out.settlement.source_declared_net_cents == 10000
    assert out.settlement.source_declared_candidate_fee_cents == 0
    assert out.settlement.outstanding_return_cents == 2000
    assert "UNAPPLIED_RETURN_COULD_CHANGE_DECLARED_RECOVERY" in out.blockers


def test_reconciled_return_restores_only_supported_fee_candidate(tmp_path):
    s = store(tmp_path)
    s.create_claim(claim("A", "INV-A", 10000))
    s.ingest_event(credit("E", "INV-A", 10000))
    allocate(s, "A", "E", 10000)
    s.ingest_counter(returned("R", "E", 2000))
    assert s.fee_eligible_cents() == 0
    assert s.auto_apply_counter(
        "R", created_at="2026-09-03T13:00:00Z",
    ).status == REVERSED
    assert s.realized_cents() == 8000
    assert s.fee_eligible_cents() == 8000
    row = build_currency_settlement_report(s).by_currency[0]
    assert row.declared_net_allocated_cents == 8000
    assert row.declared_fee_eligible_net_cents == 8000
    assert row.unresolved_counter_cents == 0
    out = inspect(s, "A", "INV-A", 10000)
    assert out.settlement.source_declared_candidate_fee_cents == 8000
    assert out.settlement.outstanding_return_cents == 0


def test_shared_credit_return_is_once_per_event_not_per_claim(tmp_path):
    s = store(tmp_path)
    s.create_claim(claim("A", "INV-A", 6000))
    s.create_claim(claim("B", "INV-A", 4000))
    s.ingest_event(credit("E", "INV-A", 10000))
    allocate(s, "A", "E", 6000)
    allocate(s, "B", "E", 4000)
    s.ingest_counter(returned("R", "E", 2000))
    assert s.auto_apply_counter(
        "R", created_at="2026-09-03T13:00:00Z",
    ).status == REVIEW
    assert s.realized_cents() == 10000
    assert s.fee_eligible_cents("A") == 0
    assert s.fee_eligible_cents("B") == 0
    assert s.fee_eligible_cents() == 0
    row = build_currency_settlement_report(s).by_currency[0]
    assert row.unresolved_counter_cents == 2000
    assert row.declared_fee_eligible_net_cents == 0
    a = inspect(s, "A", "INV-A", 6000)
    b = inspect(s, "B", "INV-A", 4000)
    assert a.settlement.source_declared_candidate_fee_cents == 0
    assert b.settlement.source_declared_candidate_fee_cents == 0
    assert a.settlement.outstanding_return_cents == 0
    assert b.settlement.outstanding_return_cents == 0
    assert a.settlement.unattributed_shared_return_event_ids
    assert a.settlement.unattributed_shared_return_event_ids == (
        b.settlement.unattributed_shared_return_event_ids
    )


def test_unrelated_event_fee_stays_available_during_other_return_hold(tmp_path):
    s = store(tmp_path)
    s.create_claim(claim("A", "INV-A", 10000))
    s.create_claim(claim("B", "INV-B", 3000))
    s.ingest_event(credit("E-A", "INV-A", 10000))
    s.ingest_event(credit("E-B", "INV-B", 3000))
    allocate(s, "A", "E-A", 10000)
    allocate(s, "B", "E-B", 3000)
    s.ingest_counter(returned("R-A", "E-A", 2000))
    assert s.realized_cents() == 13000
    assert s.fee_eligible_cents("A") == 0
    assert s.fee_eligible_cents("B") == 3000
    assert s.fee_eligible_cents() == 3000
    row = build_currency_settlement_report(s).by_currency[0]
    assert row.declared_fee_eligible_net_cents == 3000
    assert row.unresolved_counter_cents == 2000
    assert inspect(s, "A", "INV-A", 10000).settlement.source_declared_candidate_fee_cents == 0
    assert inspect(s, "B", "INV-B", 3000).settlement.source_declared_candidate_fee_cents == 3000


def test_independent_120_case_oracle_requires_zero_fee_during_pending_return():
    from freight.priority4_adversarial_lab import (
        independent_oracle, make_plan, CREDIT_MODES,
    )

    plans = (make_plan(i) for i in range(120))
    eligible_pending = [
        p for p in plans if p.credit_mode == "PENDING_RETURN" and p.ordinal % 11
    ]
    assert eligible_pending  # compare against separately synthesized expected state
    for p in eligible_pending:
        oracle = independent_oracle(p)
        assert oracle.pending_return_cents > 0
        assert oracle.fee_base_cents == 0
        assert oracle.settled_net_cents > 0
    assert "PENDING_RETURN" in CREDIT_MODES
    settled = next(
        p for p in (make_plan(i) for i in range(120))
        if p.credit_mode == "FULL_CREDIT" and p.ordinal % 11
    )
    baseline = independent_oracle(settled)
    assert baseline.pending_return_cents == 0
    assert baseline.fee_base_cents == baseline.settled_net_cents > 0
