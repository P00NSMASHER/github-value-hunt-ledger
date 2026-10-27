"""GAO-02-635 historical RecoveryOS accounting controls, never freight truth."""
import copy
import json
import unittest
from pathlib import Path

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures"
    / "recoveryos_gao_02_635_ap_reconciliation_candidate_v0.json"
)


def verify_source_bound_candidate(doc):
    def eq(actual, expected):
        assert type(actual) is type(expected) and actual == expected

    eq(doc["schema_version"], "0.1.0")
    eq(doc["pack_id"], "RECOVERYOS_GAO_02_635_AP_RECONCILIATION_CANDIDATE_V0")
    eq(doc["engine"], "recoveryos")
    eq(doc["evaluation_family"], "GENERAL_ACCOUNTING_RECONCILIATION_ONLY")
    eq(doc["admission_state"],
       "HISTORICAL_GAO_REPORT_CANDIDATE_NOT_CUSTOMER_EVALUATION_ADMITTED")
    source = doc["source"]
    eq(source["report_id"], "GAO-02-635")
    eq(source["original_publisher_accessible_text_url"],
       "https://www.gao.gov/assets/a234797.html")
    eq(source["landing_url"], "https://www.gao.gov/products/gao-02-635")
    eq(source["report_published_date"], "2002-05-30")
    eq(source["report_public_release_date"], "2002-07-01")
    eq(source["original_publisher_response_bytes_acquired"], False)
    eq(source["original_publisher_response_sha256"], None)
    eq(source["original_underlying_invoices_payment_ledgers_bank_statements_acquired"],
       False)
    eq(source["contract_effective_date"], "UNKNOWN")
    eq(source["rights_url"], "https://www.gao.gov/copyright")
    eq(source["commercial_customer_engine_admission"], False)
    eq(source["government_endorsement_claimed"], False)
    assert "THIRD_PARTY_RIGHTS_SEPARATE" in source["rights_state"]

    cases = doc["historical_cases"]
    eq(len(cases), 4)
    eq([c["case_id"] for c in cases], [
        "TEXTRON_2000_PROGRESS_LIQUIDATION",
        "BOEING_2001_TWO_INVOICE_LIQUIDATION",
        "EAGLE_2001_CROSS_FORMAT_DUPLICATE",
        "LUCENT_2000_2001_DUPLICATE_PREVENTED",
    ])
    assert all(c["kind"] == "PUBLISHER_REPORTED_HISTORICAL_CASE"
               and c["independent_bank_receipt_acquired"] is False
               for c in cases)
    textron, boeing, eagle, lucent = cases
    eq(textron["contract_delivery_price_cents"], 1095720500)
    eq(textron["liquidation_should_cents"], 821790400)
    eq(textron["net_invoice_cents"], 273930100)
    eq(textron["dfas_payment_cents"], 1093415800)
    eq(textron["publisher_reported_refund_cents"], 819485600)
    eq(textron["computed_overpayment_cents"], 819485700)
    eq(textron["publisher_amount_disagreement_cents"], 100)
    eq(textron["contract_delivery_price_cents"] -
       textron["liquidation_should_cents"], textron["net_invoice_cents"])
    eq(textron["dfas_payment_cents"] - textron["net_invoice_cents"],
       textron["computed_overpayment_cents"])
    eq(textron["computed_overpayment_cents"] -
       textron["publisher_reported_refund_cents"],
       textron["publisher_amount_disagreement_cents"])

    eq(boeing["error_type"], "INCORRECT_PROGRESS_LIQUIDATION_RATE_TWO_INVOICES")
    eq(boeing["invoice_count_reported"], 2)
    eq(boeing["two_invoice_overcharge_cents"], [207792200, 345000000])
    eq(boeing["computed_component_sum_cents"], 552792200)
    eq(boeing["publisher_reported_refund_cents"], 552792200)
    eq(boeing["publisher_component_arithmetic_agrees"], True)
    eq(boeing["original_invoice_identifiers"], "UNKNOWN")
    eq(boeing["original_invoice_documents_acquired"], False)
    eq(boeing["label"], "GAO_REPORTS_TWO_INVOICE_LIQUIDATION_REFUND_NO_ORIGINAL_INVOICE_CUSTODY")
    eq(sum(boeing["two_invoice_overcharge_cents"]), boeing["publisher_reported_refund_cents"])

    eq(eagle["publisher_reported_refund_cents"], 95833900)
    eq(eagle["source_says_same_invoice"], True)
    eq(eagle["source_says_shipment_numbers_different"], True)
    eq(eagle["hardcopy_invoice_submitted"], "2001-06-11")
    eq(eagle["electronic_invoice_submitted"], "2001-06-28")
    eq(eagle["electronic_invoice_paid"], "2001-07-10")
    eq(eagle["hardcopy_invoice_paid"], "2001-07-18")
    assert eagle["hardcopy_invoice_submitted"] < eagle["electronic_invoice_submitted"]
    assert eagle["electronic_invoice_paid"] < eagle["hardcopy_invoice_paid"]
    eq(lucent["attempted_duplicate_amount_cents"], 139720000)
    eq(lucent["duplicate_eft_canceled_before_bank"], True)
    eq(lucent["second_duplicate_bank_payment_confirmed"], False)
    eq(lucent["publisher_reported_refund_cents"], None)
    eq(lucent["label"], "NO_SECOND_PAID_DUPLICATE_NO_RECOVERY_CASH_LABEL")

    boundary = doc["truth_boundaries"]
    eq(boundary["publisher_reported_historical_cases"], 4)
    for key in ("independent_heldout_original_customer_invoice_labels",
                "independent_modern_general_accounting_accuracy_labels",
                "freight_error_accuracy_labels",
                "independent_original_bank_settlement_receipts",
                "verified_retally_recovered_cash_cents"):
        eq(boundary[key], 0)
    eq(boundary["modern_engine_accuracy"], "UNKNOWN")
    eq(boundary["admission_to_commercial_customer_scoring"], False)
    eq(boundary["do_not_treat_publisher_reported_refund_as_user_cash"], True)
    quality = doc["quality"]
    eq(quality["source_body_hash_verified"], False)
    eq(quality["publisher_report_explicitly_disclaims_full_underlying_DFAS_data_reliability_assessment"], True)
    eq(quality["original_publisher_arithmetic_disagreement_preserved"], True)
    eq(quality["private_customer_medical_student_records_included"], False)

    controls = doc["synthetic_negative_controls"]
    eq(len(controls), 6)
    eq(len({x["id"] for x in controls}), 6)
    assert all(x["kind"] == "SYNTHETIC"
               and x["id"].startswith("SYNTH_")
               and x["expected"].startswith("REJECT_")
               for x in controls)


class GAOAccountingReconCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_first_party_report_accounting_rights_and_limits(self):
        verify_source_bound_candidate(self.pack)

    def test_real_report_positive_negative_and_one_dollar_conflict(self):
        textron, boeing, eagle, lucent = self.pack["historical_cases"]
        self.assertEqual(textron["computed_overpayment_cents"], 819485700)
        self.assertEqual(textron["publisher_reported_refund_cents"], 819485600)
        self.assertEqual(textron["publisher_amount_disagreement_cents"], 100)
        self.assertEqual(boeing["invoice_count_reported"], 2)
        self.assertEqual(sum(boeing["two_invoice_overcharge_cents"]), 552792200)
        self.assertFalse(boeing["original_invoice_documents_acquired"])
        self.assertEqual(eagle["label"], "GAO_REPORTS_DUPLICATE_PAYMENT_AND_REFUND")
        self.assertEqual(eagle["publisher_reported_refund_cents"], 95833900)
        self.assertIsNone(lucent["publisher_reported_refund_cents"])
        self.assertTrue(lucent["duplicate_eft_canceled_before_bank"])
        self.assertFalse(lucent["second_duplicate_bank_payment_confirmed"])

    def test_synthetic_poisoned_source_money_and_truth_rejected(self):
        mutations = [
            ("source", "original_publisher_accessible_text_url",
             "https://www.gao.gov/assets/UNRELATED.html"),
            ("source", "original_publisher_response_sha256", "0" * 64),
            ("source", "original_publisher_response_bytes_acquired", True),
            ("source", "commercial_customer_engine_admission", True),
            ("source", "government_endorsement_claimed", True),
            ("source", "contract_effective_date", "2001-01-01"),
            ("truth_boundaries", "independent_heldout_original_customer_invoice_labels", 3),
            ("truth_boundaries", "freight_error_accuracy_labels", 3),
            ("truth_boundaries", "verified_retally_recovered_cash_cents", 95833900),
            ("truth_boundaries", "modern_engine_accuracy", "100_PERCENT"),
            ("historical_cases", 0, "publisher_reported_refund_cents", 819485700),
            ("historical_cases", 1, "invoice_count_reported", 1),
            ("historical_cases", 1, "two_invoice_overcharge_cents", [207792200, 344999900]),
            ("historical_cases", 1, "original_invoice_documents_acquired", True),
            ("historical_cases", 2, "source_says_shipment_numbers_different", False),
            ("historical_cases", 3, "duplicate_eft_canceled_before_bank", False),
            ("historical_cases", 3, "publisher_reported_refund_cents", 139720000),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                poisoned = copy.deepcopy(self.pack)
                if mutation[0] == "historical_cases":
                    _, index, key, fake = mutation
                    poisoned["historical_cases"][index][key] = fake
                else:
                    section, key, fake = mutation
                    poisoned[section][key] = fake
                with self.assertRaises(AssertionError):
                    verify_source_bound_candidate(poisoned)
        self.assertEqual(len(mutations), 17)


if __name__ == "__main__":
    unittest.main()
