"""RT05 adversarial regression: a recorded dispute hold cannot be evaded by
backdating the caller-controlled allocation timestamp.

All identities, amounts and proof hashes are synthetic; no actual customer,
claim, recovery, cash settlement, fees or external actions are authorized.
"""
from hashlib import sha256

from freight.settlement_store import (
    ALLOCATED, REVIEW, RecoveryClaim, SettlementEventRecord, SettlementStore,
)


def digest(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def claim(identity: str, reference: str, amount: int) -> RecoveryClaim:
    return RecoveryClaim(
        identity, reference, "SYN-CARRIER", "SYN-CUSTOMER", "USD", amount,
        "2026-09-01T12:00:00Z", digest("synthetic finding:" + identity),
    )


def event(identity: str, reference: str, amount: int) -> SettlementEventRecord:
    return SettlementEventRecord(
        identity, reference, "SYN-CARRIER", "SYN-CUSTOMER", "USD", amount,
        "2026-09-02T10:00:00Z", digest("synthetic credit:" + identity),
        "SYNTHETIC_SOURCE_NOT_BANK_CLEARED",
    )


def ledger(tmp_path) -> SettlementStore:
    return SettlementStore(
        tmp_path / "rt05-backdated.sqlite3",
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
    )


def hold(s: SettlementStore, identity: str) -> None:
    assert s.place_claim_dispute_hold(
        claim_id=identity, kind="CARRIER_DENIAL",
        source_hash=digest("synthetic denial:" + identity),
        observed_at="2026-09-03T12:00:00Z",
        expected_claim_source_sha256=digest("synthetic finding:" + identity),
    ) is True


def test_backdated_auto_attempt_on_held_claim_returns_review_not_sql_exception(tmp_path):
    s = ledger(tmp_path)
    s.create_claim(claim("SYN-HELD", "SYN-INV", 10000))
    s.ingest_event(event("SYN-CREDIT", "SYN-INV", 10000))
    hold(s, "SYN-HELD")
    # Created-after-credit but earlier than the already-recorded denial.
    result = s.auto_allocate(
        "SYN-CREDIT", created_at="2026-09-02T11:00:00Z",
    )
    assert result.status == REVIEW
    assert "dispute" in result.reason.lower()
    assert s.count("allocations") == 0
    assert s.dispute_hold_active("SYN-HELD")
    assert s.fee_eligible_cents() == 0


def test_same_invoice_unheld_claim_cannot_launder_held_credit_by_backdating(tmp_path):
    s = ledger(tmp_path)
    # Same invoice, customer, carrier and currency. Only the smaller unheld
    # claim matches the credit exactly; the disputed larger claim is competing
    # source evidence and must force REVIEW for the entire invoice match.
    s.create_claim(claim("SYN-HELD", "SYN-INV", 10000))
    s.create_claim(claim("SYN-OTHER", "SYN-INV", 4000))
    s.ingest_event(event("SYN-CREDIT", "SYN-INV", 4000))
    hold(s, "SYN-HELD")
    result = s.auto_allocate(
        "SYN-CREDIT", created_at="2026-09-02T11:00:00Z",
    )
    assert result.status == REVIEW
    assert "dispute" in result.reason.lower()
    assert s.count("allocations") == 0
    assert s.realized_cents() == 0
    assert s.fee_eligible_cents() == 0


def test_unrelated_invoice_credit_remains_available_while_another_claim_held(tmp_path):
    s = ledger(tmp_path)
    s.create_claim(claim("SYN-HELD", "SYN-INV-A", 10000))
    s.create_claim(claim("SYN-OTHER", "SYN-INV-B", 4000))
    s.ingest_event(event("SYN-CREDIT-B", "SYN-INV-B", 4000))
    hold(s, "SYN-HELD")
    result = s.auto_allocate(
        "SYN-CREDIT-B", created_at="2026-09-02T11:00:00Z",
    )
    assert result.status == ALLOCATED
    assert s.realized_cents("SYN-HELD") == 0
    assert s.fee_eligible_cents("SYN-HELD") == 0
    assert s.realized_cents("SYN-OTHER") == 4000
