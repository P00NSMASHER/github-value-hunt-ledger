import unittest
from freight.lab_customer_scenarios import CustomerPersona,simulate_customer_reactions
from freight.lab_operations_intelligence import JourneyEvent
from freight.lab_assurance import AssuranceRejected
from freight.test_lab_assurance import BUYER,BU,SRC
from freight.test_lab_operations_intelligence import journey

class CustomerReactionTests(unittest.TestCase):
    def setUp(self):
        self.events=journey("a"*64)
        self.persona=CustomerPersona("enterprise-controller",7,2,True)

    def test_delays_and_reversal_create_causal_reactions(self):
        result=simulate_customer_reactions(self.events,self.persona,refund_due_cents=50,
                                            as_of="2026-12-20T00:00:00Z")
        codes={x["kind"] for x in result["reactions"]}
        self.assertEqual(codes,{"REQUEST_STATUS_UPDATE","REQUEST_CREDIT_DOCUMENTATION","ESCALATE_REFUND_UNRESOLVED"})
        self.assertEqual(result["scope"],"HYPOTHETICAL_PERSONA_NOT_MEASURED")
        self.assertEqual(len(result["receipt_hash"]),64)

    def test_refund_cleared_removes_escalation(self):
        result=simulate_customer_reactions(self.events,self.persona,refund_due_cents=0,
                                            as_of="2026-12-20T00:00:00Z")
        self.assertNotIn("ESCALATE_REFUND_UNRESOLVED",{x["kind"] for x in result["reactions"]})

    def test_quick_updates_do_not_create_false_overdue(self):
        result=simulate_customer_reactions([e for e in self.events if e.occurred_at <= "2026-11-20T14:00:00Z"],
                                            CustomerPersona("SMB",10,3,False),
                                            refund_due_cents=0,as_of="2026-11-20T14:00:00Z")
        self.assertEqual(result["reactions"],[])

    def test_missing_customer_update_rejected(self):
        with self.assertRaisesRegex(AssuranceRejected,"CUSTOMER_SIMULATION_NO_COMMUNICATION_EVENT"):
            simulate_customer_reactions([e for e in self.events if e.stage!="CUSTOMER_UPDATED"],
                self.persona,refund_due_cents=0,as_of="2026-12-20T00:00:00Z")

    def test_nonrealistic_future_event_rejected(self):
        with self.assertRaisesRegex(AssuranceRejected,"CUSTOMER_SIMULATION_FUTURE_EVENT"):
            simulate_customer_reactions(self.events,self.persona,refund_due_cents=0,
                as_of="2026-10-01T00:00:00Z")

if __name__=="__main__":unittest.main()
