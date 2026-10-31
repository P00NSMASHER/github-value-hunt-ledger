"""Adversarial CBCA carrier-billing decision test suite (no live network)."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight.cbca_rate_billing_controls import (
    ROOT_PINNED, load_fixture, make_receipt,
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



class CBCA1317PublicOffsetsEvidence(unittest.TestCase):
    """One source-bound CBCA cluster with 12 correlated public table rows."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(
            (Path(__file__).parent / "fixtures" /
             "cbca_1317_rate_public_bol_offsets_v1.json").read_text(encoding="utf-8"))

    @staticmethod
    def timeliness(row):
        from datetime import date
        paid, deducted = row.get("bill_paid_on"), row.get("treasury_deducted_on")
        if not paid or not deducted:
            return "UNKNOWN_NO_TIMELINESS_LABEL"
        paid_date, deducted_date = date.fromisoformat(paid), date.fromisoformat(deducted)
        try:
            deadline = paid_date.replace(year=paid_date.year + 3)
        except ValueError:  # February 29, if a source extension later contains it
            deadline = paid_date.replace(year=paid_date.year + 3, day=28)
        return ("DEDUCTION_UNTIMELY" if deducted_date > deadline
                else "NOT_UNTIMELY_ON_DATES_ALONE")

    def test_exact_public_source_identity_and_rights_hold(self):
        p, src = self.pack, self.pack["original_source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(src["docket"], "CBCA 1317-RATE")
        self.assertEqual(src["decision_date"], "2009-10-29")
        self.assertIn("www.cbca.gov/files/decisions/2009/", src["source_url"])
        self.assertEqual(src["source_pdf_pages_visually_checked"], [3, 8])
        self.assertIsNone(src["source_http_byte_sha256"])
        self.assertIsNone(src["source_http_byte_length"])
        self.assertFalse(src["original_pdf_bytes_custodied"])
        self.assertFalse(src["original_invoice_or_tariff_bytes_custodied"])
        self.assertEqual(src["third_party_contract_invoice_rights"], "UNKNOWN_NOT_CLEARED")
        self.assertEqual(src["commercial_scoring_rights"], "NOT_APPROVED")

    def test_original_reported_twelve_rows_tamper_hash_and_dedup(self):
        p, rows = self.pack, self.pack["rows"]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({r["row_id"] for r in rows}), 12)
        self.assertEqual(len({r["public_bol_sha256"] for r in rows}), 12)
        self.assertTrue(all(len(r["public_bol_sha256"]) == 64 for r in rows))
        original_hash = sha256(json.dumps(rows, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(original_hash, p["normalized_row_projection_sha256"])
        tampered = deepcopy(rows)
        tampered[0]["treasury_deducted_cents"] += 1
        self.assertNotEqual(sha256(json.dumps(tampered, sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest(),
                            p["normalized_row_projection_sha256"])
        duplicate = deepcopy(rows)
        duplicate[11]["public_bol_sha256"] = rows[0]["public_bol_sha256"]
        self.assertNotEqual(len({r["public_bol_sha256"] for r in duplicate}), 12)

    def test_each_reported_offset_late_on_bill_paid_date(self):
        for row in self.pack["rows"]:
            with self.subTest(row=row["row_id"]):
                self.assertEqual(self.timeliness(row), "DEDUCTION_UNTIMELY")
                self.assertEqual(row["board_disposition"],
                                 "DEDUCTION_UNTIMELY_REFUND_ORDERED")
                self.assertIsNone(row["actual_refund_paid_cents"])
        altered = deepcopy(self.pack["rows"][0])
        altered["treasury_deducted_on"] = "2007-01-20"
        self.assertEqual(self.timeliness(altered), "NOT_UNTIMELY_ON_DATES_ALONE")
        altered["bill_paid_on"] = None
        self.assertEqual(self.timeliness(altered), "UNKNOWN_NO_TIMELINESS_LABEL")

    def test_two_partial_deductions_do_not_inflate_cash_or_merits(self):
        p, rows = self.pack, self.pack["rows"]
        d = p["reported_decision"]
        self.assertEqual(sum(r["alleged_overcharge_cents"] for r in rows), 13761404)
        self.assertEqual(sum(r["treasury_deducted_cents"] for r in rows), 13735675)
        self.assertEqual(d["publisher_reported_total_treasury_deductions_cents"], 13735675)
        self.assertEqual(d["publisher_reported_total_alleged_overcharges_cents"], 13761404)
        self.assertEqual(d["publisher_reported_difference_cents"], 25729)
        self.assertEqual(sum(r["alleged_overcharge_cents"] !=
                             r["treasury_deducted_cents"] for r in rows), 2)
        self.assertIsNone(d["actual_board_ordered_refund_confirmed_as_paid_cents"])
        self.assertEqual(d["actual_retally_customer_recovery_cents"], 0)
        self.assertFalse(d["original_bill_overcharge_merits_adjudicated"])
        self.assertTrue(d["merits_of_car_substitution_moot"])

    def test_negative_controls_independence_and_no_label_leak(self):
        p = self.pack
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len({c["id"] for c in controls}), 8)
        for c in controls:
            with self.subTest(control=c["id"]):
                self.assertTrue(c["id"].startswith("SYN_"))
                self.assertEqual(c["kind"], "SYNTHETIC")
                self.assertIsNone(c["independent_original_truth"])
        q = p["quality_and_holdout"]
        self.assertEqual(q["distinct_historical_decision_clusters"], 1)
        self.assertEqual(q["reported_line_items"], 12)
        self.assertEqual(q["independent_customer_holdout_cases"], 0)
        self.assertEqual(q["blind_product_predictions"], 0)
        self.assertEqual(q["independent_invoice_rate_tariff_triplets"], 0)
        self.assertIsNone(q["original_invoice_level_precision"])
        self.assertIsNone(q["original_invoice_level_recall"])
        self.assertEqual(q["modern_tender_applicability"], "UNKNOWN")
        self.assertFalse(q["money_settlement_proven"])
        r = p["restrictions"]
        self.assertFalse(r["source_commercial_clearance"])
        self.assertFalse(r["product_engine_code_changed"])
        self.assertFalse(r["legacy_15_lab_consolidation_certified"])
        self.assertFalse(r["release_authorized"])
        self.assertFalse(r["synthetic_cases_promoted_to_original"])
        self.assertEqual(r["actual_customer_cash_collected_cents"], 0)


    def test_2010_original_reconsideration_is_same_case_not_new_accuracy(self):
        f = self.pack["reconsideration_followup"]
        self.assertEqual(f["docket"], self.pack["original_source"]["docket"])
        self.assertEqual(f["decision_date"], "2010-05-05")
        self.assertEqual(f["source_url"],
                         "https://www.cbca.gov/files/decisions/2010/GILMORE_05-05-10_1317-RATE__UNION_PACIFIC_RAILROAD_508.pdf")
        self.assertEqual(f["visually_checked_pdf_pages_1_based"], [1, 3])
        self.assertEqual(f["outcome"], "RECONSIDERATION_DENIED_ORIGINAL_DISPOSITION_RETAINED")
        self.assertFalse(f["previous_outcome_reversed"])
        self.assertEqual(f["relationship_key"], f["original_decision_key"])
        self.assertEqual(f["total_official_decision_documents_in_cluster"], 2)
        self.assertEqual(f["additional_distinct_bol_rows"], 0)
        self.assertEqual(f["additional_independent_decision_clusters"], 0)
        self.assertEqual(self.pack["quality_and_holdout"]["distinct_historical_decision_clusters"], 1)
        self.assertEqual(self.pack["quality_and_holdout"]["reported_line_items"], 12)
        self.assertEqual(f["independently_held_out_real_customer_cases"], 0)
        self.assertEqual(f["blind_engine_predictions"], 0)
        self.assertFalse(f["commercial_scoring_clearance"])

    def test_2010_reconsideration_missing_cash_and_rejected_argument_controls(self):
        f, controls = self.pack["reconsideration_followup"], self.pack["reconsideration_synthetic_controls"]
        self.assertIn("ten years", f["gov_argument"])
        self.assertFalse(f["establishes_actual_refund_paid"])
        self.assertIsNone(f["actual_refund_paid_cents"])
        self.assertFalse(f["original_invoice_merits_adjudicated"])
        self.assertFalse(f["raw_pdf_bytes_custodied"])
        self.assertIsNone(f["raw_pdf_sha256"])
        self.assertIsNone(f["raw_pdf_byte_length"])
        self.assertEqual(f["third_party_invoice_rights"], "UNKNOWN_NOT_CLEARED")
        self.assertEqual(len(controls), 4)
        self.assertEqual(len({c["id"] for c in controls}), 4)
        for c in controls:
            self.assertTrue(c["id"].startswith("SYN_"))
            self.assertEqual(c["kind"], "SYNTHETIC")
            self.assertIsNone(c["independent_original_truth"])
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_CORRELATED_DUPLICATE_CLUSTER",
            "REJECT_REJECTED_PARTY_ARGUMENT_AS_TRUTH",
            "UNKNOWN_REFUND_PAID_UNVERIFIED",
            "UNKNOWN_MODERN_APPLICABILITY",
        })


if __name__=="__main__":
    unittest.main()
