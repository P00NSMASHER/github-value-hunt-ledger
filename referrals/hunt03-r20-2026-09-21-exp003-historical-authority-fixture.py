"""Synthetic EXP-003 fixture for late payout returns and historical authority.

This does not contact a provider or bank.  It tests the provider-neutral state
transition that was missing from the existing 24-case settlement matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
import threading


@dataclass(frozen=True)
class EarningSnapshot:
    earning_id: str
    rule_revision: str
    base_cents: int
    rate: Decimal
    amount_cents: int


@dataclass
class HistoricalAuthorityLedger:
    earning: EarningSnapshot
    state: str = "READY"
    payouts: dict[str, int] = field(default_factory=dict)
    returned_ids: set[str] = field(default_factory=set)
    events: list[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def claim(self, payout_id: str) -> bool:
        with self.lock:
            if self.state != "READY" or payout_id in self.payouts:
                return False
            self.payouts[payout_id] = self.earning.amount_cents
            self.state = "CLAIMED"
            self.events.append(
                {
                    "type": "PAYOUT_CLAIMED",
                    "payout_id": payout_id,
                    "earning_id": self.earning.earning_id,
                    "rule_revision": self.earning.rule_revision,
                    "amount_cents": self.earning.amount_cents,
                }
            )
            return True

    def settle(self, payout_id: str) -> None:
        with self.lock:
            assert self.state == "CLAIMED"
            assert payout_id in self.payouts
            self.state = "SETTLED"
            self.events.append(
                {
                    "type": "SETTLEMENT_OBSERVED",
                    "payout_id": payout_id,
                    "amount_cents": self.payouts[payout_id],
                }
            )

    def observe_return(
        self,
        *,
        payout_id: str,
        return_id: str,
        match: str,
        coverage: str,
        economic_reason: str,
        source: str = "independent_readback",
    ) -> str:
        """Apply only an exact, independently covered, one-use counter-event."""
        with self.lock:
            if source != "independent_readback":
                return "REVIEW_NONINDEPENDENT_SOURCE"
            if coverage != "VERIFIED_WINDOW":
                return "HOLD_COVERAGE_UNVERIFIED"
            if match != "EXACT_UNIQUE":
                return "REVIEW_RETURN_MATCH"
            if payout_id not in self.payouts:
                return "REVIEW_UNKNOWN_PAYOUT"
            if return_id in self.returned_ids:
                return "DUPLICATE_SUPPRESSED"
            if self.state != "SETTLED":
                return "REVIEW_NONSETTLED_PAYOUT"

            self.returned_ids.add(return_id)
            self.events.append(
                {
                    "type": "PAYOUT_RETURN_OBSERVED",
                    "payout_id": payout_id,
                    "return_id": return_id,
                    "amount_cents": -self.payouts[payout_id],
                    "economic_reason": economic_reason,
                    "source": source,
                }
            )
            if economic_reason == "BANK_RETURN_STILL_OWED":
                self.state = "READY"
                self.events.append(
                    {
                        "type": "HISTORICAL_EARNING_REOPENED",
                        "earning_id": self.earning.earning_id,
                        "rule_revision": self.earning.rule_revision,
                        "amount_cents": self.earning.amount_cents,
                    }
                )
                return "REOPENED_ORIGINAL_AUTHORITY"
            if economic_reason == "REFUND_CLAWBACK_NOT_OWED":
                self.state = "REVOKED_NOT_OWED"
                return "REVOKED_NO_REPAYMENT"
            self.state = "REVIEW"
            return "REVIEW_ECONOMIC_REASON"


def settled_ledger() -> HistoricalAuthorityLedger:
    earning = EarningSnapshot(
        earning_id="earn-1",
        rule_revision="plan-A@2026-01-01",
        base_cents=100_000,
        rate=Decimal("0.10"),
        amount_cents=10_000,
    )
    ledger = HistoricalAuthorityLedger(earning)
    assert ledger.claim("payout-1")
    ledger.settle("payout-1")
    return ledger


def run_fixture() -> dict:
    checks: list[str] = []

    # The current policy has changed to 13%, but it is not settlement authority
    # for the already-earned 10% obligation.
    current_policy_rate = Decimal("0.13")
    assert current_policy_rate != settled_ledger().earning.rate
    checks.append("current_policy_differs_from_event_time_authority")

    ledger = settled_ledger()
    original_events = tuple(ledger.events)
    outcome = ledger.observe_return(
        payout_id="payout-1",
        return_id="return-1",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
    )
    assert outcome == "REOPENED_ORIGINAL_AUTHORITY"
    assert ledger.state == "READY"
    assert tuple(ledger.events[: len(original_events)]) == original_events
    checks.append("late_return_preserves_original_history_and_reopens")

    assert ledger.claim("payout-2")
    assert ledger.payouts["payout-2"] == 10_000
    assert ledger.events[-1]["rule_revision"] == "plan-A@2026-01-01"
    assert ledger.payouts["payout-2"] != 13_000
    assert not ledger.claim("payout-3")
    checks.append("repayment_uses_original_amount_once_not_current_rate")

    duplicate = settled_ledger()
    first = duplicate.observe_return(
        payout_id="payout-1",
        return_id="return-1",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
    )
    replay = duplicate.observe_return(
        payout_id="payout-1",
        return_id="return-1",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
    )
    assert first == "REOPENED_ORIGINAL_AUTHORITY"
    assert replay == "DUPLICATE_SUPPRESSED"
    assert sum(e["type"] == "HISTORICAL_EARNING_REOPENED" for e in duplicate.events) == 1
    checks.append("duplicate_semantic_return_cannot_double_reopen")

    for match, coverage, expected in (
        ("AMBIGUOUS", "VERIFIED_WINDOW", "REVIEW_RETURN_MATCH"),
        ("NOT_FOUND", "VERIFIED_WINDOW", "REVIEW_RETURN_MATCH"),
        ("EXACT_UNIQUE", "PARTIAL", "HOLD_COVERAGE_UNVERIFIED"),
        ("EXACT_UNIQUE", "UNAVAILABLE", "HOLD_COVERAGE_UNVERIFIED"),
    ):
        blocked = settled_ledger()
        before = tuple(blocked.events)
        got = blocked.observe_return(
            payout_id="payout-1",
            return_id=f"return-{match}-{coverage}",
            match=match,
            coverage=coverage,
            economic_reason="BANK_RETURN_STILL_OWED",
        )
        assert got == expected
        assert blocked.state == "SETTLED"
        assert tuple(blocked.events) == before
    checks.append("ambiguous_absent_partial_and_unavailable_evidence_do_not_mutate_money")

    wrong = settled_ledger()
    before = tuple(wrong.events)
    assert wrong.observe_return(
        payout_id="different-payout",
        return_id="return-wrong",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
    ) == "REVIEW_UNKNOWN_PAYOUT"
    assert tuple(wrong.events) == before
    checks.append("exact_return_must_reference_known_payout")

    clawback = settled_ledger()
    assert clawback.observe_return(
        payout_id="payout-1",
        return_id="return-clawback",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="REFUND_CLAWBACK_NOT_OWED",
    ) == "REVOKED_NO_REPAYMENT"
    assert clawback.state == "REVOKED_NOT_OWED"
    assert not clawback.claim("payout-2")
    checks.append("clawback_does_not_mint_repayment")

    source = settled_ledger()
    before = tuple(source.events)
    assert source.observe_return(
        payout_id="payout-1",
        return_id="return-webhook",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
        source="webhook_only",
    ) == "REVIEW_NONINDEPENDENT_SOURCE"
    assert tuple(source.events) == before
    assert source.observe_return(
        payout_id="payout-1",
        return_id="return-readback",
        match="EXACT_UNIQUE",
        coverage="VERIFIED_WINDOW",
        economic_reason="BANK_RETURN_STILL_OWED",
        source="independent_readback",
    ) == "REOPENED_ORIGINAL_AUTHORITY"
    checks.append("lost_webhook_can_be_recovered_only_by_independent_readback")

    race = settled_ledger()
    outcomes: list[str] = []

    def apply() -> None:
        outcomes.append(
            race.observe_return(
                payout_id="payout-1",
                return_id="return-race",
                match="EXACT_UNIQUE",
                coverage="VERIFIED_WINDOW",
                economic_reason="BANK_RETURN_STILL_OWED",
            )
        )

    threads = [threading.Thread(target=apply) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("REOPENED_ORIGINAL_AUTHORITY") == 1
    assert outcomes.count("DUPLICATE_SUPPRESSED") == 7
    assert sum(e["type"] == "HISTORICAL_EARNING_REOPENED" for e in race.events) == 1
    checks.append("concurrent_duplicate_return_has_one_winner")

    result = {
        "checks": checks,
        "checks_passed": len(checks),
        "event_time_amount_cents": ledger.earning.amount_cents,
        "current_policy_amount_if_rerated_cents": 13_000,
        "repayment_amount_cents": ledger.payouts["payout-2"],
        "race_one_winner": True,
    }
    result["result_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


if __name__ == "__main__":
    print(json.dumps(run_fixture(), sort_keys=True))
