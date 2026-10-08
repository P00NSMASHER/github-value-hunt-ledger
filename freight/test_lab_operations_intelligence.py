"""Regression tests for routed work and loss-preserving modeled decisions."""
import unittest
from dataclasses import replace
from freight.lab_assurance import AssuranceRejected
from freight.test_lab_assurance import BUYER, BU, SRC
import freight.test_lab_assurance as finance_fixtures
from freight.lab_operations_intelligence import (
    CostAssumptions, JourneyEvent, build_lab_routing, evaluate_operating_case,
)

STAGES=[
("INVOICE_INGESTED","2026-10-08T10:00:00Z"),
("CONTRACT_AUTHORIZED","2026-10-08T11:00:00Z"),
("BLIND_RATING","2026-10-08T12:00:00Z"),
("DISCREPANCY_REVIEWED","2026-10-08T13:00:00Z"),
("BUYER_APPROVED","2026-10-09T09:00:00Z"),
("CLAIM_SUBMITTED","2026-10-09T13:00:00Z"),
("CARRIER_ACKNOWLEDGED","2026-10-12T13:00:00Z"),
("CREDIT_ALLOCATED","2026-10-18T13:00:00Z"),
("CREDIT_RECONCILED","2026-10-18T14:00:00Z"),
("FEE_ACCOUNTED","2026-10-19T13:00:00Z"),
("CUSTOMER_UPDATED","2026-11-20T13:00:00Z"),
("CREDIT_REVERSED","2026-12-12T13:00:00Z"),
("FEE_ACCOUNTED","2026-12-14T10:00:00Z"),
("FINANCIAL_RECONCILED","2026-12-14T13:00:00Z"),
("ECONOMICS_ANALYZED","2026-12-15T09:00:00Z")]


def journey(receipt_hash):
    return [JourneyEvent(f"journey-{i}",stage,at,BUYER,BU,"INV-100",SRC,"case-1",
            (receipt_hash,) if stage in ("FINANCIAL_RECONCILED","ECONOMICS_ANALYZED") else (f"test-evidence-{i}",))
            for i,(stage,at) in enumerate(STAGES,1)]


class OperationsTests(unittest.TestCase):
    def setUp(self):
        finance_fixtures.AssuranceProofTests.setUp(self)

    def verify(self, *args, **kwargs):
        return finance_fixtures.AssuranceProofTests.verify(self, *args, **kwargs)
    def test_complete_cross_lab_routing_is_a_plan_not_execution(self):
        verified=self.verify()
        routed=build_lab_routing(journey(verified.receipt_hash),assurance=verified)
        self.assertEqual(routed.status,"PASS_ROUTING_CONTRACT")
        self.assertIn("NOT_WORKER_EXECUTION",routed.scope)
        self.assertEqual(routed.stage_count,len(STAGES))
        self.assertEqual(set(x["lab"] for x in routed.lab_work_items),set(range(1,15)))
        self.assertTrue(all(x["status"]=="ROUTED_NOT_EXECUTED" for x in routed.lab_work_items))

    def test_cannot_forge_financial_certification_as_work_item(self):
        verified=self.verify()
        bad=journey(verified.receipt_hash)
        bad[-2]=replace(bad[-2],evidence_ids=("self-hash-not-financial-proof",))
        with self.assertRaisesRegex(AssuranceRejected,"JOURNEY_MISSING_FINANCIAL_PROOF"):
            build_lab_routing(bad,assurance=verified)

    def test_cross_tenant_journey_is_rejected(self):
        verified=self.verify()
        bad=journey(verified.receipt_hash)
        bad[8]=replace(bad[8],buyer_id="other-tenant")
        with self.assertRaisesRegex(AssuranceRejected,"LAB_SOURCE_SCOPE_CHANGED"):
            build_lab_routing(bad,assurance=verified)

    def test_wrong_order_is_rejected(self):
        verified=self.verify()
        bad=journey(verified.receipt_hash)
        bad[5]=replace(bad[5],occurred_at="2026-10-08T01:00:00Z")
        with self.assertRaisesRegex(AssuranceRejected,"JOURNEY_OUT_OF_ORDER"):
            build_lab_routing(bad,assurance=verified)

    def test_skipping_buyer_authorization_is_rejected(self):
        verified=self.verify()
        bad=[x for x in journey(verified.receipt_hash) if x.stage!="BUYER_APPROVED"]
        with self.assertRaisesRegex(AssuranceRejected,"JOURNEY_MISSING_PREREQUISITE"):
            build_lab_routing(bad,assurance=verified)

    def test_operating_cost_preserves_negative_margin(self):
        verified=self.verify()
        result=evaluate_operating_case(verified,CostAssumptions(
            "USD",150,70,15,1000,4000,2000,120,40))
        self.assertEqual(result["modeled_current_margin_cents"],-90)
        self.assertEqual(result["modeled_incremental_margin_cents"],-100)
        self.assertEqual(result["recommended_next_action"],"DO_NOT_ESCALATE_ON_MODELED_ECONOMICS")
        self.assertEqual(result["scope"],"ASSUMPTION_ONLY_BUSINESS_DECISION")

    def test_unresolved_customer_refund_has_priority(self):
        verified=self.verify(events=self.events[:-1])
        result=evaluate_operating_case(verified,CostAssumptions(
            "USD",150,70,15,1000,4000,2000,120,40))
        self.assertEqual(result["simulated_refund_liability_cents"],50)
        self.assertEqual(result["recommended_next_action"],"REMEDIATE_FEE_REFUND")

    def test_cross_currency_is_rejected_not_summed(self):
        verified=self.verify()
        with self.assertRaisesRegex(AssuranceRejected,"OPERATING_CURRENCY_NOT_IN_ASSURANCE"):
            evaluate_operating_case(verified,CostAssumptions("EUR",0,0,0,0,0,0,0,0))

    def test_invalid_collections_and_probabilities_rejected(self):
        verified=self.verify()
        with self.assertRaises(ValueError):
            evaluate_operating_case(verified,CostAssumptions("USD",150,70,15,1000,10001,2000,120,40))


if __name__=="__main__":
    unittest.main()
