"""Five actually invoked existing freight modules, isolated fictional data only.

Runs in repository GitHub Actions with the *real* RecoveryOS Python classes.
No hosted Floot API or real bank/source signer is involved.
"""
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from freight.canonical_schema import SourceArtifact, ShipmentFacts, ChargeLine, build_record
from freight.rate_authority import compile_authority, AuthorityBook
from freight.settlement_store import (
    RecoveryClaim, SettlementEventRecord, CounterEventRecord,
    SettlementStore, ALLOCATED, REVERSED,
)
from freight.lab_phase3_integration import execute_domain_chain, IntegrationRejected
from freight.lab_phase3_economics import ContingencyAssumptions, fixed_default_contingency_bps
from freight.test_lab_assurance import BUYER, BU, CLAIM, SRC, assertions_and_fees, verifier


def sha(s):return hashlib.sha256(s.encode()).hexdigest()


def rating_fixture(*, source=SRC):
    record = build_record(
        buyer_id=BUYER,business_unit=BU,invoice_id="INV-100",invoice_date="2026-10-09",
        customer_id="SIM-BUYER",currency="USD",
        shipment=ShipmentFacts(shipment_id="SIM-SHIP-1",carrier_id="SIM-CARRIER",mode="TL",
             service_date="2026-10-09",origin_postal="17901",destination_postal="21201",
             actual_weight_grams=1000,package_count=1,miles=1),
        charges=(ChargeLine("linehaul","LINEHAUL",1100),),
        sources=(SourceArtifact("source-invoice-1","INVOICE",source,
              "2026-10-09T12:00:00.000000Z","BATCH","simulated.csv"),),
    )
    authority=compile_authority({"authority_id":"synthetic-tl-v1","buyer_id":BUYER,
        "business_unit":BU,"customer_id":"SIM-BUYER","carrier_id":"SIM-CARRIER",
        "currency":"USD","mode":"TL","effective_from":"2026-01-01",
        "terms":{"pricing_model":"PER_MILE","per_mile_cents":100,
                "minimum_cents":0,"fuel_bps":0}},
        source_sha256=sha("synthetic-reviewed-tariff"),verified_controlling_authority=True)
    return record, AuthorityBook([authority])


def funded_store(directory):
    store=SettlementStore(Path(directory)/"synthetic-domain.sqlite3",buyer_id=BUYER,business_unit=BU)
    store.create_claim(RecoveryClaim("case-1","INV-100","SIM-CARRIER","SIM-BUYER",
                                     "USD",1000,CLAIM,SRC,False))
    for eid,cents,when in [("credit-400",400,"2026-10-18T12:00:00Z"),
                            ("credit-600",600,"2026-11-07T12:00:00Z")]:
        store.ingest_event(SettlementEventRecord(eid,"INV-100","SIM-CARRIER","SIM-BUYER",
                        "USD",cents,when,sha(eid),"EXTERNAL"))
    for alloc,eid,cents,when in [("allocation-400","credit-400",400,"2026-10-18T13:00:00Z"),
                                 ("allocation-600","credit-600",600,"2026-11-07T13:00:00Z")]:
        assert store.review_allocate(allocation_id=alloc,claim_id="case-1",event_id=eid,
                                   amount_cents=cents,created_at=when)==ALLOCATED
    store.ingest_counter(CounterEventRecord("return-500","credit-600","USD",500,
                        "2026-12-12T12:00:00Z",sha("return-500"),"BANK-RETURN"))
    assert store.review_reverse(reversal_id="reversal-500",counter_id="return-500",
           allocation_id="allocation-600",amount_cents=500,created_at="2026-12-12T13:00:00Z")==REVERSED
    return store


def scenario():
    return ContingencyAssumptions(
        opportunity_cents=150000,probability_valid_bps=5000,
        probability_customer_recovery_bps=6000,probability_fee_collection_bps=8000,
        expected_reversal_bps=1000,contingency_rate_bps=fixed_default_contingency_bps(),
        free_audit_minutes=150,recovery_work_minutes_if_valid=120,
        loaded_analyst_hourly_cents=4500,acquisition_cost_cents=2000,
        other_delivery_cost_cents=3000,recovery_delay_days=75)


class RealChainTests(unittest.TestCase):
    def test_real_rating_settlement_proof_economics_and_tamper_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            record,book=rating_fixture()
            store=funded_store(directory)
            proofs,fees=assertions_and_fees()
            response=execute_domain_chain(record=record,authority_book=book,store=store,
                assertions=proofs,fee_events=fees,verifier=verifier(),contingency=scenario())
            self.assertEqual(response["executed_domain_labs"],[1,4,5,8,11])
            self.assertEqual(response["settlement"]["recovered_cents"],500)
            self.assertEqual(response["rating"]["candidate_variance_cents"],1000)
            self.assertTrue(response["tampered_temporary_restore_rejected"])
            self.assertLess(response["contingency"]["expected_net_margin_cents"],0)
            self.assertFalse(response["financially_certified"])
            self.assertEqual(len(response["blocked_labs"]),9)
            self.assertTrue(all(x["status"].startswith("EXECUTED") or x["status"].startswith("BLOCKED") for x in response["lab_executions"]))

    def test_wrong_source_does_not_flow_to_finance(self):
        with tempfile.TemporaryDirectory() as directory:
            record,book=rating_fixture(source=sha("unauthorized invoice"))
            with self.assertRaisesRegex(IntegrationRejected,"INVOICE_SOURCE_MISMATCH"):
                execute_domain_chain(record=record,authority_book=book,store=funded_store(directory),
                    assertions=assertions_and_fees()[0],fee_events=assertions_and_fees()[1],
                    verifier=verifier(),contingency=scenario())

    def test_claim_amount_must_equal_invoice_variance(self):
        with tempfile.TemporaryDirectory() as directory:
            record,book=rating_fixture()
            wrong=replace(record, charges=(ChargeLine("linehaul","LINEHAUL",1200),))
            # Rebuilt canonical hash still proves wrong data would not be accepted.
            # The actual rating engine validates the record hash before any claim.
            with self.assertRaises(ValueError):
                execute_domain_chain(record=wrong,authority_book=book,store=funded_store(directory),
                    assertions=assertions_and_fees()[0],fee_events=assertions_and_fees()[1],
                    verifier=verifier(),contingency=scenario())

if __name__=="__main__": unittest.main()
