"""Read-only isolated synthetic experiments; no provider or customer calls."""
import unittest
from dataclasses import replace

from freight.lab_intelligence import (
    ExperimentCandidate, LabCase, LabEvent, ProofRejected, SourceAuthority,
    modeled_offer_value, prioritize_experiments, verify_population,
)

H = "a" * 64
T = "b" * 64


def authority(tenant="buyer-1", invoice="inv-1", receipts=None, fee=True):
    return SourceAuthority(tenant, invoice, "USD", H,
                           {"credit-1": 1000} if receipts is None else receipts,
                           2000 if fee else None, T if fee else None)


def case(ident="case-1", issue="incorrect-accessorial", events=None, **changes):
    if events is None:
        events = [LabEvent("intake-1", 1, "INTAKE", 0),
                  LabEvent("credit-event-1", 2, "CREDIT_APPLIED", 1000, "credit-1"),
                  LabEvent("earned-1", 3, "FEE_ACCRUED", 200),
                  LabEvent("cash-1", 4, "FEE_COLLECTED", 200)]
    values = dict(case_id=ident, tenant_id="buyer-1", invoice_id="inv-1",
                  issue_id=issue, currency="USD", source_sha256=H,
                  events=tuple(events),
                  reported={"net_recovered_cents": 1000, "net_earned_fee_cents": 200,
                            "net_collected_fee_cents": 200, "open_fee_receivable_cents": 0})
    values.update(changes)
    return LabCase(**values)


class FinancialProofTests(unittest.TestCase):
    def reject(self, error, authorities=None, cases=None):
        with self.assertRaises(ProofRejected) as caught:
            verify_population([authority()] if authorities is None else authorities,
                              [case()] if cases is None else cases)
        self.assertEqual(caught.exception.code, error)

    def test_valid_credit_and_collected_fee(self):
        result = verify_population([authority()], [case()])
        self.assertEqual(result.status, "PASS_SYNTHETIC_ONLY")
        self.assertTrue(result.independent_input_required)
        self.assertEqual(result.totals["net_recovered_cents"], 1000)
        self.assertEqual(len(result.receipt_sha256), 64)

    def test_phantom_money_on_intake_rejected(self):
        bad = case(events=[LabEvent("intake-1", 1, "INTAKE", 1)])
        self.reject("INTAKE_CANNOT_POST_MONEY", cases=[bad])

    def test_rehashed_summary_does_not_change_meaning(self):
        bad = case(reported={"net_recovered_cents": 120000000,
                             "net_earned_fee_cents": 200,
                             "net_collected_fee_cents": 200,
                             "open_fee_receivable_cents": 0})
        self.reject("SUMMARY_MISMATCH_NET_RECOVERED_CENTS", cases=[bad])

    def test_incorrect_source_rejected(self):
        self.reject("SOURCE_BINDING_MISMATCH", cases=[case(source_sha256="c" * 64)])

    def test_unknown_tenant_is_not_authorized(self):
        self.reject("SOURCE_OWNERSHIP_UNKNOWN", cases=[case(tenant_id="buyer-2")])

    def test_same_issue_cannot_be_recovered_twice(self):
        bad = replace(case("case-2"), events=tuple(replace(e, event_id="second-"+e.event_id)
                                                     for e in case().events))
        self.reject("DUPLICATE_ECONOMIC_ISSUE", cases=[case(), bad])

    def test_different_issues_exceeding_one_receipt_rejected(self):
        first = case(events=[LabEvent("i-1", 1, "INTAKE", 0),
                             LabEvent("c-1", 2, "CREDIT_APPLIED", 600, "credit-1")],
                     reported={"net_recovered_cents": 600, "net_earned_fee_cents": 0,
                               "net_collected_fee_cents": 0, "open_fee_receivable_cents": 0})
        second = case(ident="case-2", issue="fuel", events=[LabEvent("i-2", 1, "INTAKE", 0),
                        LabEvent("c-2", 2, "CREDIT_APPLIED", 500, "credit-1")],
                      reported={"net_recovered_cents": 500, "net_earned_fee_cents": 0,
                                "net_collected_fee_cents": 0, "open_fee_receivable_cents": 0})
        self.reject("DUPLICATE_OR_EXCESS_CREDIT", cases=[first, second])

    def test_legal_split_allocation_across_distinct_issues(self):
        events1=[LabEvent("i-1",1,"INTAKE",0),LabEvent("c-1",2,"CREDIT_APPLIED",600,"credit-1")]
        events2=[LabEvent("i-2",1,"INTAKE",0),LabEvent("c-2",2,"CREDIT_APPLIED",400,"credit-1")]
        s1=case(ident="case-1",events=events1,reported={"net_recovered_cents":600,"net_earned_fee_cents":0,"net_collected_fee_cents":0,"open_fee_receivable_cents":0})
        s2=case(ident="case-2",issue="fuel",events=events2,reported={"net_recovered_cents":400,"net_earned_fee_cents":0,"net_collected_fee_cents":0,"open_fee_receivable_cents":0})
        result=verify_population([authority()], [s1,s2])
        self.assertEqual(result.totals["net_recovered_cents"],1000)

    def test_reversal_without_original_rejected(self):
        bad=case(events=[LabEvent("i",1,"INTAKE",0),LabEvent("r",2,"CREDIT_REVERSED",100,"credit-1")])
        self.reject("REVERSAL_WITHOUT_ORIGINAL_CREDIT",cases=[bad])

    def test_fee_without_signed_authority_rejected(self):
        self.reject("FEE_TERMS_NOT_AUTHORIZED",authorities=[authority(fee=False)])

    def test_reversed_credit_must_reduce_fee_and_refund_cash(self):
        ev=list(case().events)+[LabEvent("r",5,"CREDIT_REVERSED",1000,"credit-1")]
        self.reject("FEE_NOT_SUPPORTED_BY_REALIZED_CREDIT",cases=[case(events=ev)])
        ev.extend([LabEvent("fr",6,"FEE_REVERSED",200),LabEvent("refund",7,"FEE_REFUNDED",200)])
        summary={"net_recovered_cents":0,"net_earned_fee_cents":0,
                 "net_collected_fee_cents":0,"open_fee_receivable_cents":0}
        receipt=verify_population([authority()], [case(events=ev,reported=summary)])
        self.assertEqual(receipt.totals["net_collected_fee_cents"],0)

    def test_outstanding_fee_cannot_be_hidden_on_close(self):
        ev=list(case().events)[:-1]
        self.reject("SUMMARY_MISMATCH_NET_COLLECTED_FEE_CENTS",cases=[case(events=ev)])

    def test_unknown_receipt_rejected(self):
        ev=list(case().events)
        ev[1]=replace(ev[1],reference="invented-bank-credit")
        self.reject("RECEIPT_NOT_IN_INDEPENDENT_MANIFEST",cases=[case(events=ev)])

    def test_duplicate_event_id_rejected(self):
        ev=list(case().events)
        ev[2]=replace(ev[2],event_id=ev[1].event_id)
        self.reject("DUPLICATE_EVENT_ID",cases=[case(events=ev)])

    def test_bool_cents_rejected(self):
        self.reject("INVALID_EVENT_AMOUNT",cases=[case(events=[LabEvent("i",1,"INTAKE",False)])])

    def test_true_fee_terms_required_if_rate_exists(self):
        with self.assertRaises(ProofRejected):
            SourceAuthority("buyer-1","inv-1","USD",H,{},2000,None)


class DecisionTests(unittest.TestCase):
    def test_negative_profit_preserved(self):
        result=modeled_offer_value(fixed_fee_cents=10000, collection_probability_bps=5000,
                                   analyst_minutes=120, loaded_hourly_cost_cents=7000,
                                   other_cost_cents=2000)
        self.assertEqual(result["expected_net_cents"], -11000)
        self.assertEqual(result["scope"], "MODELED_ASSUMPTIONS_ONLY")

    def test_invalid_probability(self):
        with self.assertRaises(ValueError):
            modeled_offer_value(fixed_fee_cents=1000,collection_probability_bps=10001,
                                analyst_minutes=0,loaded_hourly_cost_cents=0,other_cost_cents=0)

    def test_prioritize_verified_severity_not_count(self):
        candidates=[ExperimentCandidate("visual-low","LOW","HYPOTHESIS",(9,),1,False),
                    ExperimentCandidate("phantom-cash","CRITICAL","REPRODUCED_OFFLINE",(2,5,8),8,True)]
        ranking=prioritize_experiments(candidates)
        self.assertEqual(ranking[0][0],"phantom-cash")

    def test_duplicate_candidate_identifiers(self):
        entry=ExperimentCandidate("id","HIGH","HYPOTHESIS",(1,),1,False)
        with self.assertRaises(ValueError):
            prioritize_experiments([entry,entry])


if __name__=="__main__":
    unittest.main()
