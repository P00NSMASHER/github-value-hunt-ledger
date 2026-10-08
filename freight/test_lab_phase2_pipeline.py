"""Read-only 14-lab integration packet and owner report tests."""
from contextlib import closing
from dataclasses import replace
import sqlite3
import tempfile
import unittest
from pathlib import Path
from freight.test_lab_assurance import (
    BUYER, BU, populate, assertions_and_fees, verifier,
)
from freight.test_lab_operations_intelligence import journey
from freight.lab_assurance import verify_settlement, AssuranceRejected
from freight.lab_operations_intelligence import CostAssumptions
from freight.lab_phase2_pipeline import evaluate_read_only_phase2, render_owner_report


class StoreAdapter:
    def __init__(self,path):
        self.path=path;self.buyer_id=BUYER;self.business_unit=BU
    def count(self, table):
        if table!="recovery_claims":raise ValueError("not allowed")
        with closing(sqlite3.connect(self.path)) as c:
            return c.execute("SELECT COUNT(*) FROM recovery_claims WHERE buyer_id=? AND business_unit=?",(BUYER,BU)).fetchone()[0]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"simulated.sqlite3"
        populate(self.db)
        self.proofs,self.fees=assertions_and_fees()
        self.verifier=verifier()
        self.assumptions=CostAssumptions("USD",150,70,15,1000,4000,2000,120,40)
        self.reference=verify_settlement(self.db,buyer_id=BUYER,business_unit=BU,
               assertions=self.proofs,fee_events=self.fees,verifier=self.verifier)

    def test_complete_packet_and_readable_owner_report(self):
        packet=evaluate_read_only_phase2(StoreAdapter(self.db),assertions=self.proofs,
           fee_events=self.fees,verifier=self.verifier,assumptions=self.assumptions,
           journey=journey(self.reference.receipt_hash))
        self.assertEqual(packet.status,"RESEARCH_REVIEW_ONLY")
        self.assertFalse(packet.true_customer_recovery_proven)
        self.assertFalse(packet.product_integration_passed)
        self.assertTrue(packet.human_review_required)
        self.assertEqual(packet.business_decision["modeled_current_margin_cents"],-90)
        text=render_owner_report(packet)
        self.assertIn("not authentic buyer, bank, or carrier",text)
        self.assertIn("Modeled current operating margin: -90 cents",text)
        self.assertIn("Work items:",text)

    def test_packet_does_not_mutate_financial_database(self):
        before=self.db.read_bytes()
        evaluate_read_only_phase2(StoreAdapter(self.db),assertions=self.proofs,
            fee_events=self.fees,verifier=self.verifier,assumptions=self.assumptions,
            journey=journey(self.reference.receipt_hash))
        self.assertEqual(before,self.db.read_bytes())

    def test_packet_cannot_be_built_on_forged_source(self):
        altered=[replace(p,payload={**p.payload,"source_hash":"f"*64})
                 if p.kind=="SOURCE_OWNER" else p for p in self.proofs]
        with self.assertRaises(AssuranceRejected):
            evaluate_read_only_phase2(StoreAdapter(self.db),assertions=altered,
                fee_events=self.fees,verifier=self.verifier,assumptions=self.assumptions,
                journey=journey(self.reference.receipt_hash))

    def test_packet_cannot_be_built_on_fake_routing_evidence(self):
        malformed=journey(self.reference.receipt_hash)
        malformed[-1]=replace(malformed[-1],evidence_ids=("unverified-finance",))
        with self.assertRaisesRegex(AssuranceRejected,"JOURNEY_MISSING_FINANCIAL_PROOF"):
            evaluate_read_only_phase2(StoreAdapter(self.db),assertions=self.proofs,
                fee_events=self.fees,verifier=self.verifier,assumptions=self.assumptions,
                journey=malformed)

if __name__=="__main__":unittest.main()
