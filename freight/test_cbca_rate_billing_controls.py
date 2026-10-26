"""Adversarial CBCA carrier-billing decision test suite (no live network)."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight.cbca_rate_billing_controls import (
    FIXTURE, PINNED, ROOT_PINNED, load_fixture, make_receipt,
    validate_fixture, verify_receipt,
)
from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.unified_research_lab import ResearchError, SEEDS, digest


class CBCARealGovernmentBillingDecisionTests(unittest.TestCase):
    def test_two_original_adjudications_are_source_scoped_not_retally_cases(self):
        d=load_fixture()
        self.assertEqual(d["schema_version"],1)
        self.assertEqual(len(d["cases"]),2)
        self.assertEqual(set(d),set(ROOT_PINNED)|{"cases"})
        self.assertEqual([x["case_id"] for x in d["cases"]],
                         ["CBCA-6578-RATE","CBCA-8051-RATE"])
        for case in d["cases"]:
            self.assertIn(case["official_decision_url"],SEEDS["freightrecovery"])
            self.assertTrue(case["official_decision_url"].startswith(
                "https://www.cbca.gov/files/decisions/"))
            self.assertIsNone(case["modern_customer_overcharge_amount_cents"])
            self.assertEqual(case["actual_retally_recovered_cash_cents"],0)
        self.assertFalse(d["source_decision_pdf_bytes_acquired"])
        self.assertIsNone(d["source_decision_pdf_sha256"])
        self.assertFalse(d["official_decision_page_images_independently_verified"])
        self.assertFalse(d["original_carrier_invoices_weight_tickets_tenders_and_bank_records_held"])
        self.assertFalse(d["commercial_reuse_approved_for_retally_customers"])
        self.assertFalse(d["customer_accuracy_scoring_permitted"])
        self.assertEqual(d["retally_real_customer_cases_verified"],0)

    def test_2020_board_rejected_only_seven_of_115_assessments(self):
        case=load_fixture()["cases"][0]
        self.assertEqual(case["decision_date"],"2020-08-06")
        self.assertEqual(case["gsa_notices_under_actual_adjudication"],7)
        self.assertEqual(case["gsa_total_notices_described"],115)
        self.assertEqual(case["additional_108_notice_outcomes"],
                         "NOT_ADJUDICATED_BY_THIS_DECISION")
        self.assertEqual(case["appealed_carrier_repayment_to_gsa_cents_reported"],1554908)
        self.assertEqual(case["decision_label"],
                         "NEGATIVE_GSA_OVERCHARGE_ASSERTION_SEVEN_SHIPMENTS_ONLY")
        self.assertIn("CLAIM_GRANTED",case["board_disposition"])
        self.assertIsNone(case["actual_carrier_refund_or_credit_received_cents"])
        self.assertFalse(case["original_governing_tender_pages_in_custody"])

    def test_2024_unpaid_invoice_is_denied_not_an_overcharge(self):
        case=load_fixture()["cases"][1]
        self.assertEqual(case["decision_date"],"2024-08-08")
        self.assertEqual(case["original_invoice_date"],"2018-09-26")
        self.assertEqual(case["prepayment_denial_date"],"2018-10-02")
        self.assertEqual(case["shipment_year"],2018)
        self.assertEqual(case["disputed_unpaid_invoice_cents_reported"],1459569)
        self.assertTrue(case["missing_weight_ticket_on_initial_payment_review"])
        self.assertEqual(case["earliest_documented_claim_response_year"],2023)
        self.assertEqual(case["board_disposition"],
                         "UNPAID_CARRIER_CLAIM_DENIED_UNTIMELY_WITHOUT_PROVEN_NOTICE_PREJUDICE")
        self.assertIsNone(case["independently_verified_customer_payment_cents"])
        self.assertFalse(case["original_invoice_weight_ticket_or_bank_record_bytes_in_custody"])

    def test_receipt_separates_invalid_government_audit_from_unpaid_claim(self):
        r=make_receipt()
        self.assertEqual(r["case_count"],2)
        self.assertEqual(r["gsa_overcharge_notices_invalidated_count"],7)
        self.assertEqual(r["other_gsa_notices_not_adjudicated_here"],108)
        self.assertEqual(r["government_notice_assessment_cents_rejected_by_board_not_retally_cash"],
                         1554908)
        self.assertEqual(r["unpaid_original_invoices_denied_by_board_case_count"],1)
        self.assertEqual(r["time_barred_carrier_claim_cents_not_recoverable"],1459569)
        self.assertEqual(r["private_customer_invoice_truth_cases"],0)
        self.assertIsNone(r["verified_carrier_refund_received_cents"])
        self.assertEqual(r["verified_retally_cash_recovery_cents"],0)
        self.assertFalse(r["commercial_reuse_approved"])
        self.assertIsNone(r["source_original_pdf_sha256"])
        self.assertEqual(r["receipt_sha256"],digest({k:v for k,v in r.items()
                                                    if k!="receipt_sha256"}))
        self.assertEqual(verify_receipt(r),r)

    def test_even_rehashed_fake_customer_or_carrier_refunds_are_rejected(self):
        base=load_fixture()
        root_cases=[
            ("source_decision_pdf_bytes_acquired",True),
            ("source_decision_pdf_sha256","f"*64),
            ("official_decision_page_images_independently_verified",True),
            ("original_carrier_invoices_weight_tickets_tenders_and_bank_records_held",True),
            ("independent_private_customer_invoice_rate_and_bank_chain_verified",True),
            ("commercial_reuse_approved_for_retally_customers",True),
            ("customer_accuracy_scoring_permitted",True),
            ("retally_real_customer_cases_verified",1),
            ("retally_verified_cash_recovered_cents",1554908),
        ]
        for key,value in root_cases:
            with self.subTest(root=key):
                d=deepcopy(base)
                d[key]=value
                with self.assertRaises(ResearchError):
                    validate_fixture(d)
        case_mutations=[
            (0,"gsa_notices_under_actual_adjudication",115),
            (0,"appealed_carrier_repayment_to_gsa_cents_reported",1554909),
            (0,"board_disposition","GSA_OVERCHARGE_SUSTAINED"),
            (0,"additional_108_notice_outcomes","BOARD_GRANTED_ALL_115"),
            (0,"actual_carrier_refund_or_credit_received_cents",1554908),
            (0,"modern_customer_overcharge_amount_cents",1554908),
            (1,"disputed_unpaid_invoice_cents_reported",1459568),
            (1,"board_disposition","CARRIER_CLAIM_GRANTED"),
            (1,"earliest_documented_claim_response_year",2019),
            (1,"independently_verified_customer_payment_cents",1459569),
        ]
        for index,key,value in case_mutations:
            with self.subTest(case=index,field=key):
                d=deepcopy(base)
                d["cases"][index][key]=value
                with self.assertRaises(ResearchError):
                    validate_fixture(d)
        fabricated=deepcopy(base)
        fabricated["cases"][0]["independent_invoice_signature"]=True
        with self.assertRaises(ResearchError):
            validate_fixture(fabricated)

    def test_unknown_population_and_forged_source_receipts_fail_closed(self):
        base=make_receipt()
        tamper=[
            ("gsa_overcharge_notices_invalidated_count",115),
            ("government_notice_assessment_cents_rejected_by_board_not_retally_cash",0),
            ("other_gsa_notices_not_adjudicated_here",0),
            ("time_barred_carrier_claim_cents_not_recoverable",0),
            ("verified_carrier_refund_received_cents",1554908),
            ("private_customer_invoice_truth_cases",7),
            ("verified_retally_cash_recovery_cents",1554908),
            ("commercial_reuse_approved",True),
            ("source_original_pdf_sha256","e"*64),
        ]
        for key,value in tamper:
            with self.subTest(key=key):
                changed=deepcopy(base)
                changed[key]=value
                changed["receipt_sha256"]=digest({k:v for k,v in changed.items()
                                                  if k!="receipt_sha256"})
                with self.assertRaises(ResearchError):
                    verify_receipt(changed)
        changed=deepcopy(base)
        changed["decision_outcomes"][0]["board_disposition"]="OVERCHARGE_CONFIRMED"
        changed["receipt_sha256"]=digest({k:v for k,v in changed.items()
                                          if k!="receipt_sha256"})
        with self.assertRaises(ResearchError):
            verify_receipt(changed)

    def test_source_bytes_and_claims_are_not_written_to_repository_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"cbca_aggregates.json"
            report=make_receipt()
            path.write_text(json.dumps(report,sort_keys=True),encoding="utf-8")
            self.assertEqual(verify_receipt(json.loads(path.read_text())),report)
            self.assertNotIn("weight_ticket_original",path.read_text())
            self.assertNotIn("original_carrier_invoice_bytes",path.read_text())

    def test_native_rating_engine_refuses_historical_decision_as_modern_tariff(self):
        # Everything in this independent regression's fabricated invoice is
        # synthetic; a $15,549.08 historical audit reversal is NOT a rate.
        for i,case in enumerate(load_fixture()["cases"]):
            with self.subTest(id=case["case_id"]):
                amount=(case.get("appealed_carrier_repayment_to_gsa_cents_reported")
                        or case.get("disputed_unpaid_invoice_cents_reported"))
                fake_sha=sha256(("SYNTHETIC-CBCA-ONLY-"+case["case_id"]).encode()).hexdigest()
                record=build_record(
                    buyer_id="SYNTHETIC-CBCA-TEST",
                    business_unit="SYNTHETIC-REVIEW-ONLY",
                    invoice_id="SYNTHETIC-CASE-"+str(i),
                    invoice_date="2026-10-26",
                    customer_id="SYNTHETIC-CBCA-TEST",
                    currency="USD",
                    shipment=ShipmentFacts(
                        shipment_id="SYNTHETIC-SHIPMENT-"+str(i),
                        carrier_id="SYNTHETIC-CARRIER",
                        mode="LTL",service_date="2026-10-26",
                        origin_postal="SYN-ORIGIN",destination_postal="SYN-DESTINATION",
                        actual_weight_grams=1000,package_count=1),
                    charges=(ChargeLine("SYN-LINEHAUL","TRANSPORTATION",amount),),
                    sources=(SourceArtifact(
                        "SYNTHETIC-NOT-ORIGINAL","NO_ORIGINAL_RATE_EVIDENCE",
                        fake_sha,"2026-10-26T00:00:00.000000Z","BATCH"),),
                )
                empty=AuthorityBook(())
                rated=rate_record(record,empty)
                strict=review_freight_rate(record,empty)
                self.assertEqual(rated.status,REVIEW_REQUIRED)
                self.assertIsNone(rated.expected_total_cents)
                self.assertIsNone(rated.variance_cents)
                self.assertFalse(rated.authority_verified)
                self.assertEqual(strict.status,"REVIEW_REQUIRED")
                self.assertFalse(strict.independent_accuracy_scored)
                self.assertIsNone(strict.externally_verified_freight_error_cents)
                self.assertEqual(strict.externally_verified_cash_recovered_cents,0)


if __name__=="__main__":
    unittest.main()
