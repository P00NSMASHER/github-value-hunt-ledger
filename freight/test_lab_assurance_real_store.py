"""Use actual existing settlement domain with *independent* research verifier.

This module must execute in GitHub CI against the full RecoveryOS repository.
Tests only temporary SQLite files and fictional documents; no provider calls.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

from freight.lab_assurance import verify_settlement, AssuranceRejected
from freight.settlement_store import (
    ALLOCATED, REVERSED, RecoveryClaim, SettlementEventRecord,
    CounterEventRecord, SettlementStore,
)
from freight.lab_phase2_pipeline import evaluate_read_only_phase2, render_owner_report
from freight.lab_operations_intelligence import CostAssumptions
from freight.test_lab_operations_intelligence import journey
from freight.test_lab_assurance import (
    BUYER, BU, CLAIM, SRC, assertions_and_fees, verifier,
)


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


class ActualDomainAssuranceTests(unittest.TestCase):
    def test_actual_settlement_store_two_credits_one_reversal_and_fee_refund(self):
        with tempfile.TemporaryDirectory() as d:
            store=SettlementStore(Path(d)/"ledger.sqlite3",buyer_id=BUYER,business_unit=BU)
            claim=RecoveryClaim("case-1","INV-100","SIM-CARRIER","SIM-BUYER",
                                "USD",1000,CLAIM,SRC,False)
            self.assertTrue(store.create_claim(claim))
            for eid,cents,booked in (("credit-400",400,"2026-10-18T12:00:00Z"),
                                     ("credit-600",600,"2026-11-07T12:00:00Z")):
                event=SettlementEventRecord(eid,"INV-100","SIM-CARRIER","SIM-BUYER","USD",
                                            cents,booked,h(eid),"EXTERNAL")
                self.assertTrue(store.ingest_event(event))
            for edge,eid,cents,at in (("allocation-400","credit-400",400,"2026-10-18T13:00:00Z"),
                                      ("allocation-600","credit-600",600,"2026-11-07T13:00:00Z")):
                self.assertEqual(store.review_allocate(allocation_id=edge,
                     claim_id="case-1",event_id=eid,amount_cents=cents,created_at=at),ALLOCATED)
            self.assertEqual(store.realized_cents("case-1"),1000)
            self.assertTrue(store.ingest_counter(CounterEventRecord(
                "return-500","credit-600","USD",500,"2026-12-12T12:00:00Z",
                h("return-500"),"BANK-RETURN")))
            self.assertEqual(store.review_reverse(
                reversal_id="reversal-500",counter_id="return-500",
                allocation_id="allocation-600",amount_cents=500,
                created_at="2026-12-12T13:00:00Z"),REVERSED)
            proofs, fees=assertions_and_fees()
            receipt=verify_settlement(store.path,buyer_id=BUYER,business_unit=BU,
                                      assertions=proofs,fee_events=fees,verifier=verifier())
            self.assertEqual(store.realized_cents("case-1"),receipt.currency_totals["USD"]["recovered_cents"])
            self.assertEqual(receipt.currency_totals["USD"]["earned_fee_cents"],100)
            self.assertEqual(receipt.currency_totals["USD"]["collected_fee_cents"],100)
            self.assertEqual(receipt.status,"PASS_SYNTHETIC_ONLY")
            packet=evaluate_read_only_phase2(
                store, assertions=proofs, fee_events=fees, verifier=verifier(),
                assumptions=CostAssumptions("USD",150,70,15,1000,4000,2000,120,40),
                journey=journey(receipt.receipt_hash))
            self.assertFalse(packet.product_integration_passed)
            self.assertFalse(packet.true_customer_recovery_proven)
            self.assertEqual(packet.business_decision["modeled_incremental_margin_cents"],-100)
            self.assertIn("No historical findings are closed",render_owner_report(packet))
            # Actual domain cannot independently authenticate signed bank/buyer proof.
            with self.assertRaisesRegex(AssuranceRejected,"MISSING_FEE_REFUND"):
                verify_settlement(store.path,buyer_id=BUYER,business_unit=BU,
                                  assertions=[p for p in proofs if p.kind!="FEE_REFUND"],
                                  fee_events=fees,verifier=verifier())


if __name__=="__main__":
    unittest.main()
