"""Source-bound GAO dromedary service contrast. Tests research fixtures, never product scoring."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).parent
PACK = ROOT / "fixtures" / "gao_b227179_dromedary_service_v1.json"
CONTRAST = ROOT / "fixtures" / "gao_b225507_tender_chain_v1.json"

SPECIAL_REJECTIONS = {
    "AV_ALONE_PROVES_HIGHER_VAN_RATE": "REJECT_EQUIPMENT_CODE_ALONE",
    "NO_LITERAL_DROMEDARY_WORDS_INVALIDATE_TENDER": "REJECT_AUTOMATIC_LITERALISM",
    "68_SHIPMENTS_ARE_68_INDEPENDENT_ADJUDICATIONS": "REJECT_CORRELATED_LABELS",
    "337_PLUS_68_ARE_PROVEN_DISJOINT": "UNKNOWN_COHORT_OVERLAP",
    "GAO_SUPPLEMENT_DISALLOWANCE_PROVES_CUSTOMER_REFUND": "UNKNOWN_NO_BANK_CASH",
    "OCR_STYLE_GAO_TEXT_IS_EXACT_ORIGINAL_PDF": "UNKNOWN_ORIGINAL_BYTE_PROVENANCE",
}

def research_only_guard(claim, facts):
    if claim in SPECIAL_REJECTIONS:
        return SPECIAL_REJECTIONS[claim]
    if claim != "HISTORICAL_DROMEDARY_SUPPLEMENT_DISALLOWANCE":
        return "UNKNOWN_UNRECOGNIZED_CLAIM"
    if facts.get("shipper_dromedary_request") is not True:
        return "UNKNOWN_SHIPPER_REQUEST"
    if facts.get("gbl_dromedary_tender_reference") is not True:
        return "UNKNOWN_TENDER_REFERENCE"
    if facts.get("carrier_prior_lower_rate_billing") is not True:
        return "UNKNOWN_PRIOR_BILLING"
    if facts.get("substitution_for_carrier_convenience") is not True:
        return "UNKNOWN_REASON_FOR_SUBSTITUTION"
    if facts.get("carrier_timely_clarification") is not False:
        return "UNKNOWN_DIFFERENT_NOTICE_PATTERN"
    return "SUPPORTED_ONLY_IN_GAO_B227179_CASE"

class GAOB227179DromedarySourceQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(PACK.read_text(encoding="utf-8"))
        cls.contrast = json.loads(CONTRAST.read_text(encoding="utf-8"))

    def test_official_source_rights_and_original_bytes_not_invented(self):
        s, r = self.p["original_source"], self.p["rights"]
        self.assertEqual(self.p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-227179")
        self.assertEqual(s["decision_date"], "1988-03-23")
        self.assertEqual(s["official_html_url"], "https://www.gao.gov/products/b-227179-0")
        self.assertEqual(r["terms_url"], "https://www.gao.gov/copyright")
        self.assertIsNone(s["original_http_body_sha256"])
        self.assertIsNone(s["original_http_body_byte_length"])
        self.assertFalse(s["original_raw_bytes_custodied"])
        self.assertFalse(s["original_gbl_invoice_tender_bytes_custodied"])
        self.assertFalse(r["commercial_product_scoring_authorized"])
        self.assertEqual(self.p["checked_on_utc"], "2026-10-31")

    def test_actual_decision_outcome_is_one_cluster_not_68_labels(self):
        e, label = self.p["reported_evidence"], self.p["real_original_label"]
        self.assertEqual(e["disputed_supplemental_shipments_reported"], 68)
        self.assertEqual(e["prior_similar_lower_rate_billed_shipments_reported_min"], 337)
        self.assertEqual(e["overlap_between_groups"], "UNKNOWN_DO_NOT_SUM_AS_DISJOINT")
        self.assertEqual(e["gbl_equipment_annotation"], "AV")
        self.assertTrue(e["gbl_dromedary_rate_tender_reference"])
        self.assertFalse(e["gbl_express_words_dromedary_request"])
        self.assertEqual(e["official_outcome"], "GSA_DISALLOWANCE_OF_SUPPLEMENTAL_BILLS_SUSTAINED")
        self.assertEqual(label["case_key"], "GAO/B-227179")
        self.assertEqual(label["shipment_level_independent_labels"], 0)
        self.assertFalse(label["modern_freight_error_label"])
        for key in ("total_claimed_supplement_cents", "amount_disallowed_cents", "customer_recovery_cents"):
            self.assertIsNone(e[key])
        self.assertEqual(e["actual_retally_customer_cash_cents"], 0)

    def test_all_synthetic_controls_cannot_be_counted_as_original_outcomes(self):
        b = self.p["historical_reference_guard"]
        self.assertEqual(research_only_guard(b["claim"], b["facts"]), b["expected"])
        controls = self.p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 11)
        self.assertEqual(len({x["id"] for x in controls}), 11)
        for item in controls:
            with self.subTest(id=item["id"]):
                self.assertEqual(item["split"], "synthetic_holdout")
                self.assertEqual(item["kind"], "RESEARCH_AUTHORED_NOT_REAL_SHIPMENT")
                self.assertIsNone(item["independent_real_label"])
                self.assertTrue(item["id"].startswith("SYN_"))
                facts = deepcopy(b["facts"])
                facts.update(item["mutation"])
                self.assertEqual(research_only_guard(item["claim"], facts), item["expected"])

    def test_five_red_green_missing_critical_evidence_probes(self):
        baseline = self.p["historical_reference_guard"]
        supported = baseline["expected"]
        self.assertEqual(research_only_guard(baseline["claim"], baseline["facts"]), supported)
        for key, value in (
            ("shipper_dromedary_request", None),
            ("gbl_dromedary_tender_reference", False),
            ("carrier_prior_lower_rate_billing", None),
            ("substitution_for_carrier_convenience", None),
            ("carrier_timely_clarification", True),
        ):
            with self.subTest(changed_field=key):
                altered = deepcopy(baseline["facts"])
                altered[key] = value
                self.assertNotEqual(research_only_guard(baseline["claim"], altered), supported)

    def test_two_independent_adjudications_are_not_a_blind_product_benchmark(self):
        b = self.p["benchmark_readiness"]
        self.assertEqual(self.p["real_original_label"]["split"], "RESEARCH_RESERVED_CROSS_CASE_NOT_BLIND")
        self.assertEqual(self.contrast["original_source"]["decision_id"], "B-225507")
        self.assertEqual(self.contrast["decision_reported_evidence"]["official_outcome"], "GAO_SUSTAINED_GSA_AUDIT_ACTION")
        self.assertEqual(self.p["reported_evidence"]["official_outcome"], "GSA_DISALLOWANCE_OF_SUPPLEMENTAL_BILLS_SUSTAINED")
        self.assertEqual(b["compared_source_clusters"], 2)
        self.assertEqual(b["independently_adjudicated_cases"], 2)
        self.assertEqual(b["blind_model_predictions"], 0)
        self.assertEqual(b["independent_modern_invoice_triplets"], 0)
        self.assertEqual(b["real_customer_holdout_cases"], 0)
        self.assertIsNone(b["modern_precision"])
        self.assertIsNone(b["modern_recall"])
        self.assertTrue(b["holdout_not_blind"])

    def test_ocr_quality_and_lab_boundary(self):
        p = self.p
        self.assertIn("TRANSCRIBED_GAO_TEXT_HAS_OCR_STYLE_ERRORS_EG_OBL_VS_GBL_AND_OSA_VS_GSA", p["source_quality"]["limitations"])
        self.assertFalse(p["ownership"]["writer_modified"])
        self.assertFalse(p["ownership"]["engine_code_changed"])
        self.assertFalse(p["restrictions"]["legacy_lab_consolidation_verified"])
        self.assertFalse(p["restrictions"]["release_authorized"])
        self.assertEqual(p["restrictions"]["paid_provider_calls"], 0)

if __name__ == "__main__":
    unittest.main()
