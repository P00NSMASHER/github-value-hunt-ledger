"""Offline adversarial verification of CBCA 1317/3467 freight timelines."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight.cbca_rail_detention_timeline import (
    UP_ROWS, TQL_FACTS, UP_FACTS, RECEIPT_KEYS, ROOT_PINNED, ROW_FIELDS,
    make_receipt, load_fixture, validate_fixture, verify_receipt,
)
from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.unified_research_lab import ResearchError, SEEDS, digest


class CBCAIndependentCarrierPaymentChronologyTests(unittest.TestCase):
    def test_official_board_sources_are_distinct_and_rights_held(self):
        doc = load_fixture()
        self.assertEqual(set(doc),set(ROOT_PINNED) |
                         {"union_pacific_2009","total_quality_logistics_2014"})
        self.assertEqual(doc["publisher"],"U.S. Civilian Board of Contract Appeals")
        for key in ("union_pacific_2009","total_quality_logistics_2014"):
            case=doc[key]
            self.assertIn(case["official_url"],SEEDS["freightrecovery"])
            self.assertTrue(case["official_url"].startswith(
                "https://www.cbca.gov/files/decisions/"))
        self.assertFalse(doc["original_official_pdf_bytes_acquired"])
        self.assertIsNone(doc["original_official_pdf_sha256"])
        self.assertFalse(doc["original_bol_invoice_contract_or_tender_bytes_held"])
        self.assertFalse(doc["independent_bank_or_repayment_statement_held"])
        self.assertFalse(doc["commercial_customer_engine_use_approved"])
        self.assertEqual(doc["retally_recovered_cash_cents"],0)
        self.assertEqual(doc["independent_modern_customer_invoice_ground_truth_cases"],0)

    def test_all_twelve_original_board_table_bol_date_amount_pairs(self):
        data=load_fixture()["union_pacific_2009"]
        rows=data["rows"]
        self.assertEqual(len(rows),12)
        self.assertEqual(
            [tuple(row[f] for f in ROW_FIELDS) for row in rows],list(UP_ROWS))
        self.assertEqual(len({row["public_gbl_id_from_board_table"] for row in rows}),12)
        self.assertEqual(rows[0]["public_gbl_id_from_board_table"],"W45QQ90009822")
        self.assertEqual(rows[-1]["public_gbl_id_from_board_table"],"W45QQ90006013")
        self.assertEqual(data["source_table_zero_based_pdf_page"],2)
        self.assertEqual(data["initial_74_bol_notices_reported"],74)
        self.assertEqual(data["initial_claims_settled_by_parties_reported"],67)
        self.assertEqual(data["added_claims_during_proceedings"],5)
        self.assertEqual(74-67+5,len(rows))
        self.assertFalse(data["underlying_tariff_overcharge_merits_adjudicated"])

    def test_treasury_real_offset_amount_is_not_original_billed_invoice_amount(self):
        rows=load_fixture()["union_pacific_2009"]["rows"]
        self.assertEqual(
            sum(r["government_alleged_overcharge_cents"] for r in rows),
            13761404)
        self.assertEqual(
            sum(r["treasury_offset_collected_cents"] for r in rows),
            13735675)
        self.assertEqual(
            sum(r["government_alleged_overcharge_cents"]
                - r["treasury_offset_collected_cents"] for r in rows),
            25729)
        self.assertEqual(
            sum(r["government_alleged_overcharge_cents"] !=
                r["treasury_offset_collected_cents"] for r in rows), 2)
        r=make_receipt()
        self.assertEqual(
            r["up_board_reported_alleged_overcharge_total_cents_NOT_invoice_total"],
            13761404)
        self.assertEqual(
            r["up_board_reported_treasury_offsets_taken_cents_NOT_retally_refund"],
            13735675)
        self.assertTrue(r["up_board_ordered_refund_but_no_bank_receipt"])
        self.assertEqual(r["retally_cash_recovered_cents"],0)
        self.assertEqual(r["independent_carrier_refunds_bank_verified_cases"],0)

    def test_each_offset_is_outside_three_year_payment_window(self):
        rows=load_fixture()["union_pacific_2009"]["rows"]
        for row in rows:
            with self.subTest(bol=row["public_gbl_id_from_board_table"]):
                paid=date.fromisoformat(row["carrier_bill_paid_date_board_reported"])
                offset=date.fromisoformat(row["treasury_offset_date_board_reported"])
                self.assertGreater(offset,paid.replace(year=paid.year+3))
        self.assertEqual(make_receipt()["up_late_offset_rows"],12)
        self.assertEqual(
            load_fixture()["union_pacific_2009"]["board_conclusion"],
            "TWELVE_TREASURY_DEDUCTIONS_TOO_LATE_MUST_BE_REFUNDED")

    def test_tql_historical_approved_detention_dispute_and_amount_conflict(self):
        case=load_fixture()["total_quality_logistics_2014"]
        self.assertEqual(case["decision_date"],"2014-05-14")
        self.assertEqual(case["historical_gsa_tender_reference"],
                         "GSA_STOS_100_D_ITEM_325")
        self.assertEqual(case["shipment_count_2010"],4)
        self.assertEqual(case["shipment_count_2011"],75)
        self.assertEqual(case["government_initially_accepted_paid_invoice_count"],9)
        self.assertEqual(case["government_later_challenged_paid_invoice_count"],70)
        self.assertEqual(case["reported_gsa_demand_variants_cents"],
                         [33989573,33989575])
        self.assertEqual(case["amount_discrepancy_cents"],2)
        self.assertFalse(case["gsa_recoupment_actually_received_from_carrier_verified"])
        self.assertFalse(case["later_carrier_refund_or_credit_verified"])
        self.assertFalse(case["original_signed_bol_and_itemized_invoice_bytes_in_retally_custody"])
        report=make_receipt()
        self.assertEqual(report["tql_paid_transport_invoice_shipments_reported"],79)
        self.assertEqual(report["tql_challenged_invoice_count"],70)
        self.assertEqual(report["tql_amount_variance_cents"],2)
        self.assertEqual(report["tql_contradictory_notice_amounts_cents_NOT_normalized"],
                         [33989573,33989575])
        self.assertTrue(report["tql_gsa_notices_invalidated"])
        self.assertTrue(report["tql_government_recoupment_received_not_verified"])

    def test_decision_merits_and_customer_tariffs_never_promoted(self):
        report=make_receipt()
        self.assertTrue(report["up_merits_of_underlying_tariff_dispute_not_decided"])
        self.assertFalse(report["original_invoice_bol_tender_bytes_held"])
        self.assertFalse(report["commercial_use_approved"])
        self.assertEqual(report["modern_customer_truth_cases"],0)
        self.assertEqual(report["independent_carrier_refunds_bank_verified_cases"],0)
        self.assertEqual(report["retally_cash_recovered_cents"],0)
        self.assertIsNone(report["original_official_pdf_source_sha256"])
        self.assertEqual(set(report),RECEIPT_KEYS)
        self.assertEqual(verify_receipt(report),report)

    def test_date_money_bol_and_historical_narrative_mutation_fail_closed(self):
        base=load_fixture()
        changes=(
            (0,"treasury_offset_collected_cents",1793655),
            (10,"government_alleged_overcharge_cents",1207384),
            (11,"treasury_offset_date_board_reported","2008-10-30"),
            (0,"carrier_bill_paid_date_board_reported","2006-01-20"),
            (0,"public_gbl_id_from_board_table","FAKE_PUBLIC_BOL"),
            (0,"source_money_promoted",1),
        )
        for i,key,value in changes:
            altered=deepcopy(base)
            altered["union_pacific_2009"]["rows"][i][key]=value
            with self.subTest(field=key,which=i),self.assertRaises(ResearchError):
                validate_fixture(altered)
        for key,value in (
            ("reported_gsa_demand_variants_cents",[33989575]),
            ("amount_discrepancy_cents",0),
            ("government_later_challenged_paid_invoice_count",79),
            ("gsa_recoupment_actually_received_from_carrier_verified",True),
            ("later_carrier_refund_or_credit_verified",True),
            ("board_conclusion","GSA_PAID_RECOUPMENT"),
        ):
            altered=deepcopy(base)
            altered["total_quality_logistics_2014"][key]=value
            with self.subTest(tql=key),self.assertRaises(ResearchError):
                validate_fixture(altered)

    def test_original_source_rights_or_bank_recovery_cannot_be_faked(self):
        base=load_fixture()
        for key,value in (
            ("original_official_pdf_bytes_acquired",True),
            ("original_official_pdf_sha256","a"*64),
            ("original_bol_invoice_contract_or_tender_bytes_held",True),
            ("independent_bank_or_repayment_statement_held",True),
            ("independent_modern_customer_invoice_ground_truth_cases",12),
            ("commercial_customer_engine_use_approved",True),
            ("retally_recovered_cash_cents",13735675),
        ):
            altered=deepcopy(base)
            altered[key]=value
            with self.subTest(key=key),self.assertRaises(ResearchError):
                validate_fixture(altered)

    def test_rehashed_receipt_cannot_claim_paid_refunds_or_invent_lawful_rate(self):
        expected=make_receipt()
        forged_values=(
            ("up_board_reported_treasury_offsets_taken_cents_NOT_retally_refund",0),
            ("up_late_offset_rows",0),
            ("up_board_ordered_refund_but_no_bank_receipt",False),
            ("up_merits_of_underlying_tariff_dispute_not_decided",False),
            ("tql_contradictory_notice_amounts_cents_NOT_normalized",[33989575]),
            ("tql_gsa_notices_invalidated",False),
            ("tql_government_recoupment_received_not_verified",False),
            ("commercial_use_approved",True),
            ("original_official_pdf_source_sha256","b"*64),
            ("independent_carrier_refunds_bank_verified_cases",12),
            ("retally_cash_recovered_cents",13735675),
        )
        for key,value in forged_values:
            tampered=deepcopy(expected)
            tampered[key]=value
            tampered["receipt_sha256"]=digest({
                k:v for k,v in tampered.items() if k!="receipt_sha256"})
            with self.subTest(key=key),self.assertRaises(ResearchError):
                verify_receipt(tampered)

    def test_public_bol_id_and_original_transaction_rows_not_exported_in_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"review_only_receipt.json"
            report=make_receipt()
            p.write_text(json.dumps(report,sort_keys=True),encoding="utf-8")
            content=p.read_text(encoding="utf-8")
            for row in UP_ROWS:
                self.assertNotIn(row[0],content)
            self.assertNotIn("W45QQ90009822",content)
            self.assertNotIn("original_customer_invoice_id",content)
            self.assertIn("up_original_bol_identifiers_authored_sha256_NOT_pdf_source_hash",content)
            self.assertEqual(verify_receipt(json.loads(content)),report)

    def test_synthetic_record_cannot_reprice_from_historical_board_table(self):
        row=load_fixture()["union_pacific_2009"]["rows"][0]
        synthetic_digest=sha256(b"SYNTHETIC-UP-CBCA-NO-PRIVATE-CUSTOMER").hexdigest()
        record=build_record(
            buyer_id="SYNTHETIC-REVIEW",business_unit="SYNTHETIC-UNIT",
            invoice_id="SYNTHETIC-UP-TEST",invoice_date="2026-10-26",
            customer_id="SYNTHETIC-REVIEW",currency="USD",
            shipment=ShipmentFacts(
                shipment_id="SYNTHETIC-UP-SHIPMENT",
                carrier_id="SYNTHETIC-RAIL",
                mode="LTL",service_date="2026-10-26",
                origin_postal="SYN-ORIGIN",destination_postal="SYN-DEST",
                actual_weight_grams=1000,package_count=1),
            charges=(ChargeLine("SYN-LINEHAUL","TRANSPORTATION",
                                row["government_alleged_overcharge_cents"]),),
            sources=(SourceArtifact(
                "SYNTHETIC-NOT-ORIGINAL","NO_BUYER_RATE_AUTHORITY",
                synthetic_digest,"2026-10-26T00:00:00.000000Z","BATCH"),),
        )
        empty=AuthorityBook(())
        rated=rate_record(record,empty)
        evidence=review_freight_rate(record,empty)
        self.assertEqual(rated.status,REVIEW_REQUIRED)
        self.assertIsNone(rated.expected_total_cents)
        self.assertIsNone(rated.variance_cents)
        self.assertFalse(rated.authority_verified)
        self.assertEqual(evidence.status,"REVIEW_REQUIRED")
        self.assertFalse(evidence.independent_accuracy_scored)
        self.assertIsNone(evidence.externally_verified_freight_error_cents)
        self.assertEqual(evidence.externally_verified_cash_recovered_cents,0)


if __name__ == "__main__":
    unittest.main()
