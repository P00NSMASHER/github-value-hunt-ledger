"""Real existing SettlementStore + separate Phase 1 financial oracle, fictional only.

No bank/carrier calls, no client data, no fee authorization or hosted claims.
A passing result checks these two separately written local implementations only.
"""
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from freight.settlement_store import (
    ALLOCATED, REVERSED, RecoveryClaim, SettlementEventRecord,
    CounterEventRecord, SettlementStore,
)
from freight.lab_intelligence import (
    LabCase, LabEvent, ProofRejected, SourceAuthority, modeled_offer_value,
    verify_population,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Phase2RealDomainBridge(unittest.TestCase):
    def test_partial_carrier_credits_delayed_reversal_and_negative_margin(self):
        with tempfile.TemporaryDirectory() as d:
            store = SettlementStore(
                Path(d) / "settlement.sqlite3",
                buyer_id="SIM-TEST-BUYER", business_unit="SIM-TEST-BU",
            )
            claim = RecoveryClaim(
                "claim-1", "INV-1", "SIM-CARRIER", "SIM-BUYER", "USD",
                1000, "2026-10-09T12:00:00Z", h("claim-source"), False,
            )
            self.assertTrue(store.create_claim(claim))
            a = SettlementEventRecord(
                "credit-400", "INV-1", "SIM-CARRIER", "SIM-BUYER",
                "USD", 400, "2026-10-18T12:00:00Z",
                h("provider-credit-400"), "EXTERNAL",
            )
            b = SettlementEventRecord(
                "credit-600", "INV-1", "SIM-CARRIER", "SIM-BUYER",
                "USD", 600, "2026-11-07T12:00:00Z",
                h("provider-credit-600"), "EXTERNAL",
            )
            self.assertTrue(store.ingest_event(a))
            self.assertTrue(store.ingest_event(b))
            self.assertEqual(store.review_allocate(
                allocation_id="allocation-400", claim_id="claim-1",
                event_id="credit-400", amount_cents=400,
                created_at="2026-10-18T13:00:00Z",
            ), ALLOCATED)
            self.assertEqual(store.review_allocate(
                allocation_id="allocation-600", claim_id="claim-1",
                event_id="credit-600", amount_cents=600,
                created_at="2026-11-07T13:00:00Z",
            ), ALLOCATED)
            self.assertEqual(store.realized_cents("claim-1"), 1000)
            self.assertEqual(store.claim_residual("claim-1"), 0)
            returned = CounterEventRecord(
                "return-500", "credit-600", "USD", 500,
                "2026-12-12T12:00:00Z", h("provider-credit-reversal"),
                "BANK-RETURN",
            )
            self.assertTrue(store.ingest_counter(returned))
            self.assertEqual(store.review_reverse(
                reversal_id="reverse-500", counter_id="return-500",
                allocation_id="allocation-600", amount_cents=500,
                created_at="2026-12-12T13:00:00Z",
            ), REVERSED)
            self.assertEqual(store.realized_cents("claim-1"), 500)
            self.assertEqual(store.claim_residual("claim-1"), 500)

            # This independent oracle sees a *separately supplied fictional*
            # receipt capacity, fee-rate hypothesis, and source digest.
            source = h("independent-synthetic-source-fixture")
            auth = SourceAuthority(
                "SIM-TEST-BUYER", "INV-1", "USD", source,
                {"credit-400": 400, "credit-600": 600},
                2000, h("synthetic-fee-terms-uncorroborated"),
            )
            events = [
                LabEvent("intake",1,"INTAKE",0),
                LabEvent("apply-400",2,"CREDIT_APPLIED",400,"credit-400"),
                LabEvent("apply-600",3,"CREDIT_APPLIED",600,"credit-600"),
                LabEvent("accrue-200",4,"FEE_ACCRUED",200),
                LabEvent("collect-150",5,"FEE_COLLECTED",150),
                LabEvent("reverse-500",6,"CREDIT_REVERSED",500,"credit-600"),
                LabEvent("reverse-fee-100",7,"FEE_REVERSED",100),
                LabEvent("refund-fee-50",8,"FEE_REFUNDED",50),
            ]
            statement = {
                "net_recovered_cents": 500,
                "net_earned_fee_cents": 100,
                "net_collected_fee_cents": 100,
                "open_fee_receivable_cents": 0,
            }
            case = LabCase(
                "SIM-CASE-CLAIM-1", "SIM-TEST-BUYER", "INV-1",
                "accessorial-overcharge", "USD", source,
                tuple(events), statement,
            )
            verified = verify_population([auth], [case])
            self.assertEqual(verified.status, "PASS_SYNTHETIC_ONLY")
            self.assertEqual(verified.totals["net_recovered_cents"], store.realized_cents("claim-1"))
            self.assertEqual(verified.totals["net_earned_fee_cents"], 100)

            false_statement = replace(case, reported={**statement, "net_recovered_cents": 1000})
            with self.assertRaises(ProofRejected):
                verify_population([auth], [false_statement])

            # The *modeled* fee after reversal is $1; assumed analyst effort
            # costs $1.90. Signed downside must not be suppressed.
            modeled = modeled_offer_value(
                fixed_fee_cents=100, collection_probability_bps=10_000,
                analyst_minutes=150, loaded_hourly_cost_cents=70,
                other_cost_cents=15,
            )
            self.assertEqual(modeled["scope"], "MODELED_ASSUMPTIONS_ONLY")
            self.assertEqual(modeled["expected_net_cents"], -90)


if __name__ == "__main__":
    unittest.main()
