"""GAO historical billing decisions: source-bound positive/negative controls."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import tempfile
import unittest
from pathlib import Path

from freight.gao_adjudicated_billing_casebook import (
    INVALID, SUSTAINED, build_receipt, load_casebook,
    validate_casebook, verify_receipt,
)
from freight.gao_motor_freight_numeric import load_fixture as numeric_fixture
from freight.test_gao_b189100_classification import (
    fixture as classification_fixture, verify as verify_classification,
)
from freight.test_gao_b221594_negative_control import (
    fixture as negative_fixture, verify_fixture as verify_negative,
)
from freight.unified_research_lab import ResearchError, SEEDS, digest


class HistoricGovernmentBillingCasebookTests(unittest.TestCase):
    def test_three_independently_adjudicated_gsa_setoffs_not_customer_revenue(self):
        doc = load_casebook()
        decisions = {x["case_id"]: x for x in doc["cases"]}
        self.assertEqual(set(decisions), {
            "B-191257", "B-189100", "B-213717", "B-221594"})
        self.assertEqual([x["reported_gsa_deducted_cents"] for x in doc["cases"]],
                         [3200, 263438, 52531, 22075])
        self.assertEqual([x["disposition"] for x in doc["cases"]],
                         [SUSTAINED, SUSTAINED, SUSTAINED, INVALID])
        self.assertEqual(sum(x["reported_gsa_deducted_cents"] for x in
                             doc["cases"] if x["disposition"] == SUSTAINED), 319169)
        self.assertEqual(decisions["B-191257"]["reported_carrier_collected_cents"]
                         - decisions["B-191257"]["reported_gsa_audited_charge_cents"], 3200)
        self.assertEqual(decisions["B-213717"]["reported_carrier_collected_cents"]
                         - decisions["B-213717"]["reported_gsa_audited_charge_cents"], 52531)
        self.assertIsNone(decisions["B-189100"]["reported_gsa_audited_charge_cents"])
        self.assertEqual(decisions["B-189100"]["reported_carrier_collected_cents"]
                         - decisions["B-189100"]["reported_gsa_deducted_cents"], 93280)
        self.assertEqual(decisions["B-213717"]["decision_date"], "1984-03-20")
        self.assertIsNone(decisions["B-213717"]["gbl_reference"])
        self.assertIn(decisions["B-213717"]["official_url"], SEEDS["freightrecovery"])
        self.assertFalse(doc["source_html_bytes_acquired"])
        self.assertIsNone(doc["source_html_bytes_sha256"])
        self.assertFalse(doc["original_invoice_and_tariff_bytes_held"])
        self.assertFalse(doc["independent_customer_rate_and_payment_chain_verified"])
        self.assertFalse(doc["commercial_customer_engine_reuse_approved"])
        self.assertEqual(doc["verified_retally_customer_cases"], 0)
        self.assertEqual(doc["verified_retally_recovered_cash_cents"], 0)

    def test_existing_primary_fixtures_match_historical_casebook_not_duplicate_cash(self):
        x = {c["case_id"]: c for c in load_casebook()["cases"]}
        older = {row["case_number"]: row for row in numeric_fixture()["cases"]}
        self.assertEqual(x["B-191257"]["reported_carrier_collected_cents"],
                         older["B-191257"]["reported_paid_cents"])
        self.assertEqual(x["B-191257"]["reported_gsa_deducted_cents"],
                         older["B-191257"]["reported_offset_deduction_cents"])
        classified = verify_classification(classification_fixture())["facts"]
        self.assertEqual(x["B-189100"]["reported_carrier_collected_cents"],
                         classified["billed_charges_cents"])
        self.assertEqual(x["B-189100"]["reported_gsa_deducted_cents"],
                         classified["gao_overcharge_deduction_cents"])
        self.assertEqual(classified["implied_allowable_derivation"],
                         "BILLED_MINUS_REPORTED_DEDUCTION_NOT_INDEPENDENT_RATE_VALIDATION")
        invalid = verify_negative(negative_fixture())["facts"]
        self.assertEqual(x["B-221594"]["reported_gsa_deducted_cents"],
                         invalid["gsa_deduction_cents"])
        self.assertEqual(invalid["gaos_final_determination"],
                         "GSA_DEDUCTION_INVALID_FOR_DOD_REJECTED_TENDER")

    def test_invalidated_gsa_recovery_must_never_be_positive_billing_label(self):
        receipt = build_receipt(as_of=date(2026, 10, 26))
        self.assertEqual(receipt["decision_count"], 4)
        self.assertEqual(receipt["upheld_gsa_setoff_cases"], 3)
        self.assertEqual(receipt["upheld_reported_setoff_cents_historical_only"], 319169)
        self.assertEqual(receipt["invalidated_gsa_setoff_cases"], 1)
        self.assertEqual(receipt["invalidated_reported_setoff_cents_not_overcharges"], 22075)
        self.assertEqual(receipt["independent_modern_customer_error_labels"], 0)
        self.assertEqual(receipt["original_invoice_tariff_and_bank_proofs_verified"], 0)
        self.assertEqual(receipt["verified_retally_recovered_cash_cents"], 0)
        self.assertFalse(receipt["commercial_use_authorized"])
        self.assertTrue(all(not row["modern_customer_scoring_allowed"]
                            for row in receipt["decision_labels"]))
        verify_receipt(receipt)

    def test_rehashed_money_outcome_custody_or_rights_forgery_still_fails(self):
        original = load_casebook()
        mutations = (
            ("cases", 0, "reported_gsa_deducted_cents", 3201),
            ("cases", 1, "reported_carrier_collected_cents", 356719),
            ("cases", 2, "reported_gsa_audited_charge_cents", 68677),
            ("cases", 3, "disposition", SUSTAINED),
            ("cases", 0, "official_url", "https://www.gao.gov/products/other"),
            ("root", None, "source_html_bytes_acquired", True),
            ("root", None, "source_html_bytes_sha256", "a"*64),
            ("root", None, "original_invoice_and_tariff_bytes_held", True),
            ("root", None, "commercial_customer_engine_reuse_approved", True),
            ("root", None, "independent_training_holdout_verified", True),
            ("root", None, "verified_retally_customer_cases", 1),
            ("root", None, "verified_retally_recovered_cash_cents", 319169),
        )
        for section, index, key, value in mutations:
            changed = deepcopy(original)
            if section == "root":
                changed[key] = value
            else:
                changed["cases"][index][key] = value
            with self.subTest(field=key), self.assertRaises(ResearchError):
                validate_casebook(changed)
        added = deepcopy(original)
        added["cases"][0]["unsupported_independent_bank_credit"] = True
        with self.assertRaises(ResearchError):
            validate_casebook(added)

    def test_self_hashed_fake_receipt_does_not_override_source_limits(self):
        original = build_receipt(as_of=date(2026, 10, 26))
        for field, val in (
            ("upheld_reported_setoff_cents_historical_only", 341244),
            ("invalidated_reported_setoff_cents_not_overcharges", 0),
            ("verified_retally_recovered_cash_cents", 319169),
            ("independent_modern_customer_error_labels", 3),
            ("commercial_use_authorized", True),
            ("publisher_html_sha256", "a"*64),
        ):
            spoof = deepcopy(original)
            spoof[field] = val
            spoof["receipt_sha256"] = digest({k: v for k, v in spoof.items()
                                              if k != "receipt_sha256"})
            with self.subTest(field=field), self.assertRaises(ResearchError):
                verify_receipt(spoof)
        spoof = deepcopy(original)
        spoof["decision_labels"][3]["historical_gao_disposition"] = SUSTAINED
        spoof["receipt_sha256"] = digest({k: v for k, v in spoof.items()
                                          if k != "receipt_sha256"})
        with self.assertRaises(ResearchError):
            verify_receipt(spoof)

    def test_representative_receipt_roundtrip_without_source_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "historical_decisions.json"
            original = build_receipt(as_of=date(2026, 10, 26))
            artifact.write_text(json.dumps(original, sort_keys=True))
            loaded = json.loads(artifact.read_text())
            self.assertEqual(verify_receipt(loaded), original)
            self.assertNotIn("bank_account", artifact.read_text())
            self.assertNotIn("customer_invoice", artifact.read_text())


if __name__ == "__main__":
    unittest.main()
