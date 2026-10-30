"""GAO B-174692 historical accounting reconciliation, not customer-cash accuracy.

No network, private records, mutable engine code, or source download.
The official decision is a historical adjudication; original voucher and
bank collection are not independently held here. A within-decision holdout
is NOT a separate independent publisher test cohort.
"""
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b174692_recoveryos_reconciliation_v1.json"


class GAOB174692AccountingReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_first_party_source_and_rights_are_explicitly_bounded(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["evaluation_family"], "GENERAL_ACCOUNTING_RECONCILIATION_NOT_FREIGHT_RATE_ACCURACY")
        self.assertEqual(p["source"]["original_public_decision_url"], "https://www.gao.gov/products/b-174692")
        self.assertEqual(p["source"]["decision_effective_date"], "1972-02-14")
        self.assertEqual(p["source"]["underlying_voucher_payment_date"], "1969-09-11")
        self.assertEqual(p["source"]["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", p["source"]["rights"])
        self.assertIsNone(p["source"]["publisher_response_bytes_sha256"])
        self.assertFalse(p["source"]["publisher_bytes_independently_custodied"])
        self.assertFalse(p["source"]["original_voucher_and_bank_statement_custodied"])
        self.assertIsNone(p["voucher"]["bank_cleared_actual_recovery_cents"])
        self.assertFalse(p["commercial_scoring_or_customer_delivery_approved"])

    def test_original_gov_decision_seven_line_items_are_not_seven_recoverable_errors(self):
        p = self.pack
        items = p["original_adjudicated_items"]
        self.assertEqual(len(items), 7)
        # Fixed source transcription independent from fixture's own totals.
        self.assertEqual([(x["item_number"], x["amount_cents"]) for x in items],
                         [(1, 11945), (2, 7755), (3, 22450), (4, 19627),
                          (5, 46830), (6, 12636), (7, 1736)])
        self.assertEqual(sum(x["amount_cents"] for x in items), 122979)
        self.assertEqual(p["voucher"]["voucher_paid_cents"], 265148)
        self.assertEqual(p["voucher"]["questioned_item_cents"], 122979)
        adjudicated_recoverable = sum(x["amount_cents"] for x in items
                                     if x["decision_on_present_record"].startswith("RECOVERABLE"))
        adjudicated_nonrecoverable = sum(x["amount_cents"] for x in items
                                        if x["decision_on_present_record"].startswith("NOT_RECOVERABLE"))
        self.assertEqual((adjudicated_recoverable, adjudicated_nonrecoverable), (100529, 22450))
        self.assertEqual(adjudicated_recoverable + adjudicated_nonrecoverable, 122979)
        self.assertEqual(p["voucher"]["gaos_final_recoverable_on_present_record_cents"],
                         adjudicated_recoverable)
        self.assertEqual(p["voucher"]["gaos_nonrecoverable_item_on_present_record_cents"],
                         adjudicated_nonrecoverable)
        # Explicit rejection of an attractive but unadjudicated naive total.
        self.assertNotEqual(adjudicated_recoverable, sum(x["amount_cents"] for x in items))
        self.assertEqual(items[2]["accounting_flag"], "FALSE_POSITIVE_NEGATIVE_LABEL")
        self.assertIn("FUTURE_PROOF", items[5]["decision_on_present_record"])
        self.assertEqual(sum(x["accounting_flag"] == "DUPLICATE_PAYMENT" for x in items), 1)

    def test_within_decision_holdout_and_unrelated_claim_dedup(self):
        p = self.pack
        items = p["original_adjudicated_items"]
        self.assertEqual(len({(p["source"]["original_decision_id"], i["item_number"]) for i in items}), 7)
        self.assertEqual([x["item_number"] for x in items
                          if x["split"] == "holdout_within_single_decision"], [3])
        self.assertEqual(p["held_out_quality"]["calibration_cases"], 6)
        self.assertEqual(p["held_out_quality"]["heldout_cases_within_same_decision"], 1)
        self.assertEqual(p["held_out_quality"]["independent_publisher_holdout_count"], 0)
        self.assertIsNone(p["held_out_quality"]["true_out_of_sample_reconciliation_accuracy"])
        self.assertEqual(p["out_of_group_control"]["other_claim_cents"], 72413)
        self.assertFalse(p["out_of_group_control"]["separate_original_source"])
        self.assertEqual(p["held_out_quality"]["freight_rate_error_labels"], 0)

    def test_synthetic_negatives_stay_unknown_or_rejected_not_promoted_to_labels(self):
        p = self.pack
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({x["id"] for x in controls}), 6)
        self.assertTrue(all(x["id"].startswith("SYNTHETIC_")
                            and x["independently_verified_real_label"] is None
                            and x["kind"] == "SYNTHETIC_NOT_REAL_TRANSACTION"
                            for x in controls))
        expected = {x["expected"] for x in controls}
        self.assertTrue({"REJECT_FALSE_POSITIVE_ITEM_3", "UNKNOWN_NO_BANK_SETTLEMENT",
                         "UNKNOWN_SUBSEQUENT_AUTHORIZATION_AND_AMOUNT",
                         "REJECT_CROSS_CLAIM_SCOPE", "DEDUP_BY_DECISION_GROUP_AND_ITEM"}.issubset(expected))
        self.assertEqual(p["held_out_quality"]["independent_2026_customer_cash_recovery_events"], 0)
        self.assertEqual(p["customer_records_downloaded"], 0)
        self.assertEqual(p["additional_provider_requests_by_ci"], 0)
        self.assertFalse(p["historical_15_labs_fully_consolidated"])


if __name__ == "__main__":
    unittest.main()
