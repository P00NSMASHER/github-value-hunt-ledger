"""GAO B-253541 original-vs-shipping-order valuation conflict: historical evaluation only.

No network, customer, or production-engine access; original signed GBL not custodied.
"""
import copy
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b253541_released_valuation_conflict_v1.json"
ORIGINAL = "GOVERNMENT_BILL_OF_LADING_ORIGINAL_SF1103"
SHIPPING_ORDER = "GOVERNMENT_BILL_OF_LADING_SHIPPING_ORDER_SF1104"


def governing_released_valuation_cents(documents):
    """Only an unambiguous original-labeled GBL value; otherwise explicit UNKNOWN."""
    originals = [
        d["released_value_cents_per_pound_per_article"]
        for d in documents
        if d.get("document_type") == ORIGINAL
        and isinstance(d.get("released_value_cents_per_pound_per_article"), int)
    ]
    return originals[0] if len(originals) == 1 else None


class GAOB253541ReleasedValuationEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_publisher_rights_scope_and_original_byte_unknowns(self):
        p = self.pack
        s = p["source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-253541")
        self.assertEqual(s["effective_decision_date"], "1993-10-18")
        self.assertEqual(s["original_public_decision_url"], "https://www.gao.gov/products/b-253541")
        self.assertIn("NO_ENDORSEMENT", s["rights"])
        self.assertEqual(s["embedded_third_party_source_document_rights"], "UNKNOWN_NOT_CLEARED")
        self.assertIsNone(s["original_publisher_response_sha256"])
        self.assertIsNone(s["original_publisher_response_byte_length"])
        self.assertFalse(s["original_publisher_response_bytes_custodied"])
        self.assertFalse(s["original_signed_GBL_SF1103_bytes_custodied"])
        self.assertFalse(s["original_shipping_order_SF1104_bytes_custodied"])

    def test_real_historical_conflict_and_authoritative_document(self):
        case = self.pack["original_adjudicated_case"]
        docs = case["documents"]
        self.assertEqual(case["government_bill_of_lading"], "D-0,521,277")
        self.assertEqual(len(docs), 2)
        self.assertEqual({d["document_type"] for d in docs}, {ORIGINAL, SHIPPING_ORDER})
        self.assertEqual(governing_released_valuation_cents(docs), 250)
        wrong = next(d for d in docs if d["document_type"] == SHIPPING_ORDER)
        self.assertEqual(wrong["released_value_cents_per_pound_per_article"], 215000)
        self.assertEqual(215000 // 250, 860)
        self.assertEqual(case["gao_final_holding"],
                         "GSA_SETTLEMENT_AFFIRMED_BILLING_BASED_ON_ORIGINAL_GBL_VALUE")

    def test_adversarial_naive_reader_is_red_and_fail_closed_reader_green(self):
        docs = self.pack["original_adjudicated_case"]["documents"]
        # A naive shipping-order-first extraction would select the wrong 860x field.
        naive = next(d["released_value_cents_per_pound_per_article"]
                     for d in docs if d["document_type"] == SHIPPING_ORDER)
        self.assertNotEqual(naive, 250)
        self.assertEqual(governing_released_valuation_cents(docs), 250)
        missing = [d for d in docs if d["document_type"] != ORIGINAL]
        self.assertIsNone(governing_released_valuation_cents(missing))
        duplicated = copy.deepcopy(docs)
        invented_original = copy.deepcopy(next(d for d in docs if d["document_type"] == ORIGINAL))
        invented_original["released_value_cents_per_pound_per_article"] = 215000
        duplicated.append(invented_original)
        self.assertIsNone(governing_released_valuation_cents(duplicated))
        # Document order does not determine authority.
        self.assertEqual(governing_released_valuation_cents(list(reversed(docs))), 250)

    def test_released_valuation_never_becomes_freight_charge_or_cash(self):
        case = self.pack["original_adjudicated_case"]
        q = self.pack["heldout_quality"]
        self.assertIn("NOT_FREIGHT_RATE", case["field_name"])
        for key in ("original_freight_charge_cents", "extra_charges_requested_cents",
                    "overcharge_cents", "actual_setoff_cents",
                    "actual_bank_cleared_recovery_cents"):
            self.assertIsNone(case[key], key)
        self.assertTrue(q["released_value_is_not_a_freight_charge"])
        self.assertEqual(q["comparison_wrong_to_governing_field_magnitude_factor"], 860)
        self.assertEqual(q["customer_retally_recovered_cash_cents"], 0)
        self.assertEqual(q["historic_decision_total_money_recovery"],
                         "UNKNOWN_NO_AMOUNT_STATED")

    def test_holdout_independence_control_provenance_dedup_and_handoffs(self):
        p = self.pack
        q = p["heldout_quality"]
        self.assertEqual(q["adjudicated_GAO_decisions"], 1)
        self.assertEqual(q["adjudicated_document_conflicts"], 1)
        self.assertTrue(q["independent_from_other_decision_ids"])
        self.assertFalse(q["independent_from_GAO_publisher"])
        self.assertEqual(q["original_signed_GBL_pairs_custodied"], 0)
        self.assertEqual(q["product_engine_predictions_compared_to_this_case"], 0)
        self.assertEqual(q["modern_buyer_authorized_invoice_payment_rate_and_appeal_triplets"], 0)
        self.assertIsNone(q["freight_overcharge_precision"])
        self.assertIsNone(q["freight_overcharge_recall"])
        self.assertEqual(p["original_adjudicated_case"]["dedup_key"],
                         "GAO/B-253541/GBL/D-0,521,277")
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["id"].startswith("SYNTH_")
                            and c["kind"] == "SYNTHETIC_NOT_REAL_SHIPMENT"
                            and c["real_customer_label"] is None for c in controls))
        self.assertIn("REJECT_FIELD_SEMANTIC_CONFUSION",
                      {c["expected"] for c in controls})
        self.assertIn("UNKNOWN_NO_FREIGHT_CHARGE_OR_RECOVERY_AMOUNT",
                      {c["expected"] for c in controls})
        self.assertFalse(p["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(p["restrictions"]["product_release_authorized"])
        self.assertIn("freightrecovery_12", p["consumers"])
        self.assertIn("recoveryos_12", p["consumers"])
        self.assertIn("independent_qa_44", p["consumers"])


if __name__ == "__main__":
    unittest.main()
