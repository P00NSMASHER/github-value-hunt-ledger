"""Adversarial tests of third-party historical freight-billing adjudications."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from freight.gao_adjudicated_billing_cases import (
    EvidenceError, FIXTURE, LABEL_NEG, LABEL_POS, PINNED,
    canonical_digest, load_fixture, make_receipt, validate_fixture,
    verify_receipt,
)


class IndependentlyAdjudicatedHistoricalBillingTests(unittest.TestCase):
    def test_official_gao_decision_population_and_money(self):
        fixture = load_fixture()
        self.assertEqual(len(fixture["cases"]), 3)
        self.assertEqual([r["id"] for r in fixture["cases"]], list(PINNED))
        receipt = make_receipt()
        self.assertEqual(receipt["external_gao_adjudicated_historical_cases"], 3)
        self.assertEqual(receipt["sustained_overcharges_historical_cents"], 16788)
        self.assertEqual(receipt["invalid_government_deductions_historical_cents"], 22075)
        self.assertEqual(receipt["historical_agency_deductions_total_cents_not_retally_cash"], 38863)
        self.assertEqual([r["historical_label"] for r in receipt["case_outcomes"]],
                         [LABEL_POS, LABEL_POS, LABEL_NEG])
        self.assertEqual(receipt["retally_recovered_cash_cents"], 0)
        self.assertEqual(receipt["private_customer_benchmark_truth_cases"], 0)
        self.assertEqual(receipt["source_original_invoice_rate_bank_chain_verified_cases"], 0)
        self.assertFalse(receipt["production_rating_or_dispute_allowed"])
        self.assertFalse(receipt["commercial_reuse_approved"])
        self.assertIsNone(receipt["source_original_gao_response_sha256"])
        verify_receipt(receipt)

    def test_negative_rejected_tender_never_becomes_positive_from_arithmetic(self):
        data = load_fixture()
        bad = data["cases"][2]
        self.assertEqual(bad["reported_billed_and_paid_cents"], 94200)
        self.assertEqual(bad["reported_gsa_audited_cents"], 72125)
        self.assertEqual(bad["reported_gsa_deducted_cents"], 22075)
        self.assertEqual(bad["adjudicated_historical_label"], LABEL_NEG)
        self.assertEqual(bad["money_calculation"], "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION")
        self.assertIn("OCR", bad["source_money_note"])
        self.assertIsNone(bad["reported_gbl"])

    def test_positive_agency_collections_are_not_retally_revenue(self):
        for row in load_fixture()["cases"][:2]:
            with self.subTest(case=row["id"]):
                self.assertEqual(row["reported_billed_and_paid_cents"]
                                 - row["reported_gsa_audited_cents"],
                                 row["reported_gsa_deducted_cents"])
                self.assertEqual(row["adjudicated_historical_label"], LABEL_POS)
        self.assertFalse(load_fixture()["historical_government_deductions_are_retally_cash"])

    def test_rehashed_changed_money_disposition_source_and_claims_fail_closed(self):
        base = load_fixture()
        replacements = [
            ("cases", 0, "reported_billed_and_paid_cents", 82801),
            ("cases", 1, "reported_gsa_audited_cents", 13928),
            ("cases", 2, "reported_gsa_deducted_cents", 22074),
            ("cases", 2, "adjudicated_historical_label", LABEL_POS),
            ("cases", 2, "ga_review_outcome", "GSA_OVERCHARGE_DEDUCTION_SUSTAINED"),
            ("cases", 2, "money_calculation", "PUBLISHER_EXPLICIT"),
            ("cases", 0, "source_url", "https://www.gao.gov/products/b-999999"),
        ]
        for _, index, key, new in replacements:
            with self.subTest(index=index, key=key):
                forged = copy.deepcopy(base)
                forged["cases"][index][key] = new
                self.assertNotEqual(canonical_digest(forged),canonical_digest(base))
                with self.assertRaises(EvidenceError):
                    validate_fixture(forged)
        for key, value in (
            ("historical_government_deductions_are_retally_cash", True),
            ("independent_original_invoice_and_bank_custody", True),
            ("independent_current_customer_invoice_accuracy_cases", 1),
            ("verified_retally_cash_cents", 3200),
            ("production_rate_or_dispute_actions_allowed", True),
            ("rights_clearance_for_current_customer_engine", True),
        ):
            with self.subTest(key=key):
                forged = copy.deepcopy(base)
                forged[key] = value
                with self.assertRaises(EvidenceError):
                    validate_fixture(forged)

    def test_original_source_sha_and_custody_cannot_be_fabricated(self):
        base=load_fixture()
        for field, value in (
            ("original_gao_response_bytes_sha256","0"*64),
            ("original_invoice_gbl_tariff_bytes_in_custody",True),
            ("source_link_is_original_transaction_document",True),
            ("commercial_customer_use_rights_verified",True),
        ):
            with self.subTest(field=field):
                altered=copy.deepcopy(base)
                altered["source_common"][field]=value
                with self.assertRaises(EvidenceError):
                    validate_fixture(altered)

    def test_extra_nested_fabricated_claims_and_amount_types_rejected(self):
        for mutation in (
            lambda d: d["cases"][0].update({"real_customer_recovered_cents":3200}),
            lambda d: d["cases"][1].update({"reported_gsa_deducted_cents":13588.0}),
            lambda d: d["cases"][1].update({"reported_gsa_deducted_cents":True}),
            lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])),
            lambda d: d["cases"].reverse(),
            lambda d: d["source_common"].update({"provider_payment_confirmed":True}),
        ):
            altered=copy.deepcopy(load_fixture())
            mutation(altered)
            with self.assertRaises(EvidenceError):
                validate_fixture(altered)

    def test_both_provenance_and_receipt_cannot_be_rehashed_into_authority(self):
        original=make_receipt()
        for key,val in (
            ("private_customer_benchmark_truth_cases",1),
            ("retally_recovered_cash_cents",3200),
            ("commercial_reuse_approved",True),
            ("external_gao_adjudicated_historical_cases",4),
            ("sustained_overcharges_historical_cents",38863),
        ):
            with self.subTest(key=key):
                forged=copy.deepcopy(original)
                forged[key]=val
                forged["receipt_sha256"]=canonical_digest({
                    k:v for k,v in forged.items() if k!="receipt_sha256"})
                with self.assertRaises(EvidenceError):
                    verify_receipt(forged)

    def test_no_unexpected_fixture_fields_or_missing_source_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            altered=copy.deepcopy(load_fixture())
            altered["cases"][0].pop("rate_authority")
            path=Path(folder)/"altered.json"
            path.write_text(json.dumps(altered))
            with self.assertRaises(EvidenceError):
                load_fixture(path)
            with self.assertRaises(EvidenceError):
                load_fixture(Path(folder)/"missing.json")

    def test_receipt_is_deterministic_and_authored_hash_is_not_source_hash(self):
        a=make_receipt()
        self.assertEqual(a,make_receipt())
        self.assertEqual(a["fixture_authored_sha256"],canonical_digest(load_fixture()))
        self.assertEqual(a["receipt_sha256"],canonical_digest({
            k:v for k,v in a.items() if k!="receipt_sha256"}))
        self.assertFalse(load_fixture()["rights_clearance_for_current_customer_engine"])


if __name__=="__main__":
    unittest.main()
