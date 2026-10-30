"""GAO-02-635 historical RecoveryOS accounting controls, never freight truth."""
import copy
import json
import unittest
from pathlib import Path

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures"
    / "recoveryos_gao_02_635_ap_reconciliation_candidate_v0.json"
)



# Strict v0 claim-field inventory from independently reviewed GAO-02-635 fixture.
# An unmodeled nested key could otherwise embed unsupported bank, recovery,
# commercial-rights, or independent-ground-truth assertions inside a valid pack.
APPROVED_GAO_V0_FIELDS = {
    "root": frozenset(["admission_state","cohort","engine","evaluation_family","handoff","historical_cases","pack_id","quality","schema_version","source","synthetic_negative_controls","truth_boundaries"]),
    "source": frozenset(["commercial_customer_engine_admission","contract_effective_date","government_endorsement_claimed","landing_url","original_publisher_accessible_text_url","original_publisher_response_bytes_acquired","original_publisher_response_sha256","original_underlying_invoices_payment_ledgers_bank_statements_acquired","publisher","report_id","report_public_release_date","report_published_date","reviewed_date","rights_state","rights_url","source_paragraph_line_ranges","title"]),
    "truth_boundaries": frozenset(["admission_to_commercial_customer_scoring","do_not_treat_publisher_reported_refund_as_user_cash","freight_error_accuracy_labels","holdout_leakage_warning","independent_heldout_original_customer_invoice_labels","independent_modern_general_accounting_accuracy_labels","independent_original_bank_settlement_receipts","modern_engine_accuracy","publisher_reported_historical_cases","verified_retally_recovered_cash_cents"]),
    "quality": frozenset(["case_label_completeness","original_publisher_arithmetic_disagreement_preserved","original_publisher_text_visually_confirmed_in_web_reader","private_customer_medical_student_records_included","publisher_report_explicitly_disclaims_full_underlying_DFAS_data_reliability_assessment","source_body_hash_verified","source_does_not_provide_original_invoice_or_bank_receipt_images"]),
    "historical_cases": tuple(
        frozenset(fields) for fields in [["case_id","computed_overpayment_cents","contract_delivery_price_cents","dfas_payment_cents","error_type","independent_bank_receipt_acquired","invoice_month","kind","label","liquidation_should_cents","net_invoice_cents","publisher_amount_disagreement_cents","publisher_reported_refund_cents","refund_reported_month"],["case_id","computed_component_sum_cents","error_type","independent_bank_receipt_acquired","invoice_count_reported","kind","label","original_invoice_documents_acquired","original_invoice_identifiers","publisher_component_arithmetic_agrees","publisher_reported_refund_cents","refund_reported_month","two_invoice_overcharge_cents"],["case_id","electronic_invoice_paid","electronic_invoice_submitted","error_type","hardcopy_invoice_paid","hardcopy_invoice_submitted","independent_bank_receipt_acquired","kind","label","publisher_reported_refund_cents","refund_reported_month","source_says_same_invoice","source_says_shipment_numbers_different"],["attempted_duplicate_amount_cents","case_id","duplicate_eft_canceled_before_bank","error_type","first_payment_reported","independent_bank_receipt_acquired","kind","label","publisher_reported_refund_cents","second_duplicate_bank_payment_confirmed"],["accounting_line_corrected_month","case_id","contract_modification_month","corrective_modification_eliminated_debt","demand_canceled","demand_face_amount_cents","demand_issued_month","error_type","independent_bank_receipt_acquired","independently_verified_paid_debt_or_refund_cents","kind","label","publisher_reported_refund_cents","wrong_accounting_line_found_month","wrong_accounting_line_reported"]]
    ),
}


def reject_unmodeled_gao_claims(doc):
    if type(doc) is not dict or set(doc) != APPROVED_GAO_V0_FIELDS["root"]:
        raise AssertionError("UNREVIEWED_TOP_LEVEL_GAO_CLAIM")
    for section in ("source", "truth_boundaries", "quality"):
        if type(doc[section]) is not dict or set(doc[section]) != APPROVED_GAO_V0_FIELDS[section]:
            raise AssertionError("UNREVIEWED_GAO_" + section.upper() + "_CLAIM")
    cases = doc["historical_cases"]
    expected = APPROVED_GAO_V0_FIELDS["historical_cases"]
    if type(cases) is not list or len(cases) != len(expected):
        raise AssertionError("UNREVIEWED_GAO_CASE_COUNT")
    for index, (case, allowed) in enumerate(zip(cases, expected)):
        if type(case) is not dict or set(case) != allowed:
            raise AssertionError("UNREVIEWED_GAO_CASE_FIELDS_" + str(index))


def verify_source_bound_candidate(doc):
    reject_unmodeled_gao_claims(doc)
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
    eq(len(cases), 5)
    eq([c["case_id"] for c in cases], [
        "TEXTRON_2000_PROGRESS_LIQUIDATION",
        "BOEING_2001_TWO_INVOICE_LIQUIDATION",
        "EAGLE_2001_CROSS_FORMAT_DUPLICATE",
        "LUCENT_2000_2001_DUPLICATE_PREVENTED",
        "LOCKHEED_1997_2001_ACCOUNTING_LINE_DEBT_CANCELED",
    ])
    assert all(c["kind"] == "PUBLISHER_REPORTED_HISTORICAL_CASE"
               and c["independent_bank_receipt_acquired"] is False
               for c in cases)
    textron, boeing, eagle, lucent, lockheed = cases
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

    eq(lockheed["error_type"],
       "WRONG_ACCOUNTING_LINE_CONTRACT_MODIFICATION_DEBT_REVERSED")
    eq(lockheed["contract_modification_month"], "1997-09")
    eq(lockheed["wrong_accounting_line_found_month"], "1998-04")
    eq(lockheed["demand_issued_month"], "2001-04")
    eq(lockheed["accounting_line_corrected_month"], "2001-05")
    assert lockheed["contract_modification_month"] < lockheed["demand_issued_month"]
    assert lockheed["wrong_accounting_line_found_month"] < lockheed["accounting_line_corrected_month"]
    eq(lockheed["demand_face_amount_cents"], 275524400)
    eq(lockheed["wrong_accounting_line_reported"], True)
    eq(lockheed["corrective_modification_eliminated_debt"], True)
    eq(lockheed["demand_canceled"], True)
    eq(lockheed["publisher_reported_refund_cents"], None)
    eq(lockheed["independently_verified_paid_debt_or_refund_cents"], None)
    eq(lockheed["label"],
       "GAO_REPORTS_DEMAND_CANCELED_AFTER_ACCOUNTING_LINE_CORRECTION_NOT_RECOVERY_CASH")

    boundary = doc["truth_boundaries"]
    eq(boundary["publisher_reported_historical_cases"], 5)
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
    eq(len(controls), 7)
    eq(len({x["id"] for x in controls}), 7)
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
        textron, boeing, eagle, lucent, lockheed = self.pack["historical_cases"]
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
        self.assertTrue(lockheed["demand_canceled"])
        self.assertTrue(lockheed["corrective_modification_eliminated_debt"])
        self.assertEqual(lockheed["demand_face_amount_cents"], 275524400)
        self.assertIsNone(lockheed["publisher_reported_refund_cents"])
        self.assertIsNone(lockheed["independently_verified_paid_debt_or_refund_cents"])

    def test_synthetic_unmodeled_nested_provenance_claims_rejected(self):
        # All four are SYNTHETIC forgeries, not publisher observations.
        forged = [
            ("source", "bank_statement_sha256", "0" * 64),
            ("truth_boundaries", "independent_customer_recovery_verified", True),
            ("quality", "customer_precision_recall_verified", "100_PERCENT"),
            ("historical_cases", 1, "retally_received_bank_cash_cents", 552792200),
        ]
        for item in forged:
            with self.subTest(synthetic_mutation=item):
                poisoned = copy.deepcopy(self.pack)
                if item[0] == "historical_cases":
                    _, index, key, value = item
                    poisoned["historical_cases"][index][key] = value
                else:
                    section, key, value = item
                    poisoned[section][key] = value
                with self.assertRaisesRegex(AssertionError, "UNREVIEWED_GAO"):
                    verify_source_bound_candidate(poisoned)

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
            ("historical_cases", 4, "demand_face_amount_cents", 275524500),
            ("historical_cases", 4, "demand_canceled", False),
            ("historical_cases", 4, "corrective_modification_eliminated_debt", False),
            ("historical_cases", 4, "publisher_reported_refund_cents", 275524400),
            ("historical_cases", 4, "independently_verified_paid_debt_or_refund_cents", 275524400),
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
        self.assertEqual(len(mutations), 22)


if __name__ == "__main__":
    unittest.main()
