"""Public historical GAO pickup-agent decision; research guards, not engine scoring."""
import json
from pathlib import Path
import unittest

PACK = Path(__file__).parent / "fixtures" / "gao_b221663_pickup_agent_joint_line_v1.json"


def research_evidence_gate(facts):
    """A decision-specific evidence boundary, not a general freight tariff rule."""
    if facts.get("tender_in_effect_on_shipment_date") is False:
        return "REJECT_INEFFECTIVE_TENDER"
    if facts.get("tender_in_effect_on_shipment_date") is not True:
        return "UNKNOWN_RATE_AUTHORITY"
    necessary = (
        "gbl_issued_to_billing_carrier", "pickup_signed_as_billing_carrier_agent",
        "shipment_specific_issuer_letter_corrob_agent",
    )
    if not all(facts.get(key) is True for key in necessary):
        return "UNKNOWN_AGENCY_RELATIONSHIP"
    return "SINGLE_LINE_RATE_SUPPORTED_IN_HISTORICAL_GAO_DECISION_ONLY"


class GAOB221663AgentEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_publisher_rights_provenance_and_unknown_raw_hash(self):
        p, s = self.pack, self.pack["original_source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["publisher"], "U.S. Government Accountability Office")
        self.assertEqual(s["decision_id"], "B-221663")
        self.assertEqual(s["decision_date"], "1986-10-10")
        self.assertEqual(s["official_html_url"], "https://www.gao.gov/products/b-221663-0")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", s["rights_and_commercial_reuse"])
        self.assertIsNone(s["original_http_body_sha256"])
        self.assertIsNone(s["original_http_body_byte_length"])
        self.assertFalse(s["original_http_bytes_custodied"])
        self.assertFalse(s["original_gbl_tender_invoice_bytes_custodied"])
        self.assertEqual(s["third_party_tender_rights"], "UNKNOWN_NOT_CLEARED")

    def test_official_decision_level_historical_outcome_and_date_scope(self):
        d = self.pack["adjudicated_decision"]
        self.assertEqual(d["shipment_date"], "1982-12-17")
        self.assertEqual(d["referenced_tender"], "ICC 2094")
        self.assertTrue(d["tender_in_effect_on_shipment_date_as_reported_by_GAO"])
        self.assertEqual(d["issuer_letter_date"], "1986-04-04")
        self.assertEqual(d["conflicting_general_letter_date"], "1986-04-08")
        self.assertTrue(d["contradictory_general_letter_not_shipment_specific"])
        self.assertEqual(d["GAO_outcome"], "GSA_DEDUCTION_SUSTAINED")
        self.assertEqual(d["finding"], "PICKUP_AGENT_THROUGH_SINGLE_LINE_TENDER_NOT_JOINT_LINE")
        self.assertIsNone(d["deducted_overcharge_amount_cents"])
        self.assertIsNone(d["original_invoice_paid_cents"])
        self.assertIsNone(d["tariff_rate_difference_cents"])
        self.assertEqual(d["independently_custodied_rate_invoice_triplets"], 0)
        self.assertEqual(d["actual_RETALLY_customer_recovery_cents"], 0)

    def test_adversarial_synthetic_missing_conflicting_or_future_evidence(self):
        controls = self.pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 9)
        self.assertEqual(len({c["id"] for c in controls}), 9)
        for c in controls:
            with self.subTest(case=c["id"]):
                self.assertTrue(c["id"].startswith("SYNTH_"))
                self.assertEqual(c["kind"], "SYNTHETIC_RESEARCH_ONLY")
                self.assertIsNone(c["independent_real_customer_label"])
                self.assertEqual(research_evidence_gate(c["facts"]), c["expected"])
        baseline = self.pack["reported_evidence_fields"]
        self.assertEqual(research_evidence_gate(baseline),
                         "SINGLE_LINE_RATE_SUPPORTED_IN_HISTORICAL_GAO_DECISION_ONLY")

    def test_selective_two_decision_comparison_is_not_engine_accuracy(self):
        h = self.pack["heldout_and_contrast"]
        self.assertEqual(h["decision_key"], "GAO/B-221663")
        self.assertEqual(h["contrast_key"], "GAO/B-203929.2")
        self.assertEqual(h["distinct_decision_keys"], 2)
        self.assertEqual(h["same_publisher_independent_decisions"], 2)
        self.assertEqual(h["reviewer_selected_original_decision_labels"], 2)
        self.assertEqual(h["naive_always_uphold_GSA_errors_in_selected_pair"], 1)
        self.assertEqual(h["naive_two_physical_carriers_implies_interline_errors_in_primary_decision"], 1)
        self.assertEqual(h["independent_original_invoice_tariff_payment_triplets"], 0)
        self.assertEqual(h["product_engine_predictions"], 0)
        self.assertEqual(h["modern_real_customer_heldouts"], 0)
        self.assertIsNone(h["real_world_precision"])
        self.assertIsNone(h["real_world_recall"])
        self.assertFalse(h["blind_test_set_proved"])

    def test_dedup_unknown_labels_and_no_customer_or_commercial_promotion(self):
        p = self.pack
        self.assertEqual(p["dedup"]["canonical_original_decision_key"], "GAO/B-221663")
        self.assertTrue(p["dedup"]["cross_reference_not_extra_independent_label"])
        self.assertEqual(p["source_quality"]["commercial_product_scoring"], "HOLD_UNVERIFIED")
        self.assertEqual(p["source_quality"]["historical_tender_full_validity_range"], "UNKNOWN")
        self.assertEqual(p["source_quality"]["source_bytes_sha256_state"], "UNKNOWN_UNCUSTODIED")
        self.assertFalse(p["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(p["restrictions"]["release_authorized"])
        self.assertFalse(p["restrictions"]["product_code_changed"])
        self.assertFalse(p["restrictions"]["customer_private_data_persisted"])


if __name__ == "__main__":
    unittest.main()
