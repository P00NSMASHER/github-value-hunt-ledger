"""Regression checks for historic rate decisions versus published settlement cash."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight.public_freight_proof_ladder import (
    ROOT, KEYS, validate_fixture,
    load_fixture, make_receipt, verify_receipt,
)
from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.unified_research_lab import ResearchError, SEEDS, digest


class PublicFreightRateAndSettlementProofTests(unittest.TestCase):
    def test_exact_original_gao_tariff_rate_reconstruction(self):
        case = load_fixture()["historical_tariff_case"]
        self.assertEqual(case["case_id"],"GAO_B_143458")
        self.assertEqual(case["carrier_bill_number_GAO_transcribed"],"NC_23166")
        self.assertEqual(case["government_bill_of_lading_GAO_transcribed"],"AF-7611030")
        self.assertEqual(case["gbl_date_GAO_reported"],"1958-03-07")
        self.assertEqual(case["actual_weight_lb_GAO_reported"],5744)
        self.assertEqual(case["applicable_minimum_weight_lb_GAO_reported"],6000)
        self.assertEqual(max(5744,6000)//100*251,15060)
        self.assertEqual(30590-15060,15530)
        self.assertEqual(case["GAO_allowable_charge_cents_GAO_reported"],15060)
        self.assertEqual(case["GAO_overcharge_cents_adjudicated"],15530)
        self.assertTrue(case["carrier_excluded_from_rule_62_2_capacity_load_roster_GAO_adjudicated"])
        self.assertEqual(
            case["overcharge_disposition"],
            "CERTIFICATE_OF_INDEBTEDNESS_PROPER_GAO_REFUND_DEMANDED_WITHIN_30_DAYS")
        self.assertIn(case["official_url"],SEEDS["freightrecovery"])

    def test_capacity_load_assertion_cannot_override_carrier_specific_tariff(self):
        case=load_fixture()["historical_tariff_case"]
        # Full visible capacity does not trigger an exception for a carrier
        # which the original historical exception specifically excluded.
        self.assertTrue(case["carrier_excluded_from_rule_62_2_capacity_load_roster_GAO_adjudicated"])
        self.assertNotEqual(case["carrier_original_billed_and_government_paid_cents_GAO_reported"],
                            case["GAO_allowable_charge_cents_GAO_reported"])
        self.assertFalse(case["present_day_rate_authority"])
        self.assertFalse(case["original_governing_tariff_pages_in_RETALLY"])
        self.assertFalse(case["GAO_original_paid_voucher_custody_in_RETALLY"])
        self.assertFalse(case["subsequent_refund_or_Treasury_offset_cleared_independently_verified"])
        self.assertFalse(case["overpayment_refunded_as_of_decision"])

    def test_2016_doj_explicitly_reports_paid_government_settlement(self):
        case=load_fixture()["doj_settlement_paid"]
        self.assertEqual(case["published_date"],"2016-05-03")
        self.assertTrue(case["doj_reports_already_paid"])
        self.assertEqual(case["menlo_settlement_paid_cents_GOV_REPORT"],1_000_000_000)
        self.assertEqual(case["estes_settlement_paid_cents_GOV_REPORT"],300_000_000)
        self.assertEqual(case["total_settlement_paid_cents_GOV_REPORT"],1_300_000_000)
        self.assertFalse(case["liability_adjudicated"])
        self.assertIsNone(case["precise_individual_invoice_damages_in_this_release"])
        self.assertFalse(case["raw_treasury_bank_remittance_in_custody"])
        self.assertEqual(case["retally_customer_refund_or_revenue_cents"],0)
        self.assertIn(case["official_url"],SEEDS["freightrecovery"])

    def test_2022_yrc_approximate_agreement_cannot_be_cleared_payment(self):
        case=load_fixture()["doj_settlement_agreed"]
        self.assertEqual(case["published_date"],"2022-03-14")
        self.assertEqual(case["doj_statement"],
                         "DEFENDANTS_AGREED_TO_PAY_APPROXIMATELY")
        self.assertEqual(case["settlement_agreed_amount_cents_APPROXIMATE"],685_000_000)
        self.assertFalse(case["doj_reports_current_completed_payment"])
        self.assertIsNone(case["actual_cash_cleared_verified_amount_cents"])
        self.assertFalse(case["liability_adjudicated"])
        self.assertEqual(case["independently_verified_per_shipment_reweigh_error_labels"],0)
        self.assertIn("LOWER_REWEIGHS",case["alleged_billing_mechanism"])
        self.assertIn(case["official_url"],SEEDS["freightrecovery"])

    def test_public_historical_money_never_transfers_to_private_customer_cash(self):
        d=load_fixture()
        self.assertEqual(set(d),set(ROOT) | {
            "historical_tariff_case","doj_settlement_paid","doj_settlement_agreed"})
        self.assertFalse(d["original_invoice_bol_and_tariff_pages_in_custody"])
        self.assertFalse(d["original_publisher_response_bytes_held"])
        self.assertFalse(d["independent_customer_shipment_rate_payment_chain_verified"])
        self.assertFalse(d["commercial_reuse_authorized_for_customer_rating"])
        self.assertEqual(d["modern_customer_invoice_ground_truth_labels"],0)
        self.assertEqual(d["retally_recovered_cash_cents"],0)
        r=make_receipt()
        self.assertEqual(len(r["public_records"]),3)
        self.assertEqual(r["GAO_historical_billable_weight_lb"],6000)
        self.assertEqual(r["GAO_historical_overcharge_cents"],15530)
        self.assertEqual(r["DOJ_settlement_paid_public_report_cents"],1300000000)
        self.assertIsNone(r["DOJ_agreed_settlement_actual_paid_cents"])
        self.assertTrue(r["DOJ_settlement_paid_NOT_customer_refund_or_overcharge_amount"])
        self.assertTrue(r["DOJ_settlement_liability_findings_cannot_be_inferred"])
        self.assertEqual(r["modern_customer_independent_overcharge_labels"],0)
        self.assertEqual(r["verified_RETALLY_cash_recovered_cents"],0)
        self.assertIsNone(r["original_publisher_SHA256"])
        self.assertEqual(set(r),KEYS)
        self.assertEqual(verify_receipt(r),r)

    def test_mutated_money_weight_tariff_or_status_rejected_even_if_self_consistent(self):
        base=load_fixture()
        cases=(
            ("historical_tariff_case","actual_weight_lb_GAO_reported",6000),
            ("historical_tariff_case","applicable_minimum_weight_lb_GAO_reported",5744),
            ("historical_tariff_case","applicable_ltl_rate_cents_per_100_lb_GAO_reported",250),
            ("historical_tariff_case","GAO_allowable_charge_cents_GAO_reported",15061),
            ("historical_tariff_case","GAO_overcharge_cents_adjudicated",15531),
            ("historical_tariff_case","carrier_excluded_from_rule_62_2_capacity_load_roster_GAO_adjudicated",False),
            ("historical_tariff_case","overpayment_refunded_as_of_decision",True),
            ("historical_tariff_case","original_governing_tariff_pages_in_RETALLY",True),
            ("doj_settlement_paid","total_settlement_paid_cents_GOV_REPORT",1_300_000_001),
            ("doj_settlement_paid","liability_adjudicated",True),
            ("doj_settlement_agreed","settlement_agreed_amount_cents_APPROXIMATE",685_000_001),
            ("doj_settlement_agreed","actual_cash_cleared_verified_amount_cents",685_000_000),
            ("doj_settlement_agreed","doj_reports_current_completed_payment",True),
            ("doj_settlement_agreed","independently_verified_per_shipment_reweigh_error_labels",1),
        )
        for scope,key,value in cases:
            changed=deepcopy(base)
            changed[scope][key]=value
            with self.subTest(scope=scope,key=key),self.assertRaises(ResearchError):
                validate_fixture(changed)
        changed=deepcopy(base)
        changed["doj_settlement_agreed"]["new_unverified_customer_recovery"]=685000000
        with self.assertRaises(ResearchError):
            validate_fixture(changed)

    def test_forged_independent_custody_commercial_use_or_retally_cash_rejected(self):
        base=load_fixture()
        for key,value in (
            ("original_publisher_response_bytes_held",True),
            ("original_invoice_bol_and_tariff_pages_in_custody",True),
            ("independent_customer_shipment_rate_payment_chain_verified",True),
            ("commercial_reuse_authorized_for_customer_rating",True),
            ("modern_customer_invoice_ground_truth_labels",3),
            ("retally_recovered_cash_cents",1_300_000_000),
        ):
            bad=deepcopy(base)
            bad[key]=value
            with self.subTest(key=key),self.assertRaises(ResearchError):
                validate_fixture(bad)

    def test_self_rehashed_receipt_cannot_override_source_state(self):
        report=make_receipt()
        values=(
            ("GAO_historical_overcharge_cents",15531),
            ("GAO_later_refund_bank_cleared_verified",True),
            ("DOJ_settlement_paid_public_report_cents",1_985_000_000),
            ("DOJ_settlement_paid_original_bank_record_in_custody",True),
            ("DOJ_agreed_settlement_actual_paid_cents",685_000_000),
            ("DOJ_settlement_liability_findings_cannot_be_inferred",False),
            ("modern_customer_independent_overcharge_labels",3),
            ("modern_tariff_rights_verified",True),
            ("verified_RETALLY_cash_recovered_cents",1),
            ("original_publisher_SHA256","a"*64),
        )
        for key,value in values:
            forged=deepcopy(report)
            forged[key]=value
            forged["receipt_SHA256"]=digest({
                k:v for k,v in forged.items() if k!="receipt_SHA256"})
            with self.subTest(key=key),self.assertRaises(ResearchError):
                verify_receipt(forged)

    def test_receipt_does_not_serialize_public_government_shipment_or_bill_ids(self):
        report=make_receipt()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"public_evidence_receipt.json"
            p.write_text(json.dumps(report,sort_keys=True),encoding="utf-8")
            raw=p.read_text(encoding="utf-8")
            for disallowed in ("NC_23166","AF-7611030","RAW_BANK_ACCOUNT","CUSTOMER_RECOVERY_ID"):
                self.assertNotIn(disallowed,raw)
            self.assertEqual(verify_receipt(json.loads(raw)),report)

    def test_native_rate_and_evidence_engines_abstain_on_historical_gao_amount(self):
        # The entire native-engine record is SYNTHETIC, never a real invoice.
        synthetic_sha=sha256(b"SYNTHETIC_PUBLIC_GAO_B143458_ONLY").hexdigest()
        record=build_record(
            buyer_id="SYNTHETIC_BUYER",business_unit="SYNTHETIC_BILLING",
            invoice_id="SYNTHETIC_GAO_CASE",invoice_date="2026-10-26",
            customer_id="SYNTHETIC_BUYER",currency="USD",
            shipment=ShipmentFacts(shipment_id="SYNTHETIC_SHIPMENT",
                                  carrier_id="SYNTHETIC_CARRIER",mode="LTL",
                                  service_date="2026-10-26",origin_postal="SYN_ORIGIN",
                                  destination_postal="SYN_DEST",
                                  actual_weight_grams=1000,package_count=1),
            charges=(ChargeLine("SYN_LINEHAUL","TRANSPORTATION",30590),),
            sources=(SourceArtifact("SYNTHETIC_NOT_ORIGINAL","NOT_AN_ORIGINAL_INVOICE",
                                    synthetic_sha,"2026-10-26T00:00:00.000000Z",
                                    "BATCH"),),
        )
        book=AuthorityBook(())
        rated=rate_record(record,book)
        evidence=review_freight_rate(record,book)
        self.assertEqual(rated.status,REVIEW_REQUIRED)
        self.assertFalse(rated.authority_verified)
        self.assertIsNone(rated.expected_total_cents)
        self.assertIsNone(rated.variance_cents)
        self.assertEqual(evidence.status,"REVIEW_REQUIRED")
        self.assertFalse(evidence.independent_accuracy_scored)
        self.assertIsNone(evidence.externally_verified_freight_error_cents)
        self.assertEqual(evidence.externally_verified_cash_recovered_cents,0)


if __name__=="__main__":
    unittest.main()
