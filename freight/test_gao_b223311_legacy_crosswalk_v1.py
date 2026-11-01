"""Source-bound, stdlib-only legacy pointer dedup for GAO B-223311. No network, engine code, or scored claims."""
import ast
import json
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "fixtures" / "gao_b223311_legacy_crosswalk_v1.json"
SOURCE = ROOT / "lab15" / "sources.json"
LEDGER = ROOT / "lab15" / "evidence_ledger.json"
DOC = ROOT / "real_document_lab.py"

def historical_reference_guard(facts):
    if facts.get("case_key") != "GAO/B-223311":
        return "UNKNOWN_OTHER_DECISION"
    if facts.get("original_gbl_class") is None:
        return "UNKNOWN_ORIGINAL_GBL_CLASS"
    if facts.get("carrier_supplement_class") is None:
        return "UNKNOWN_SUPPLEMENT_CLASS"
    if facts.get("supplier_supports_original") is not True:
        return "UNKNOWN_PRODUCER_SUPPORT"
    if facts.get("gao_decision_outcome") != "GSA_DEDUCTION_SUSTAINED":
        return "UNKNOWN_GAO_OUTCOME"
    if facts["original_gbl_class"] != 100 or facts["carrier_supplement_class"] != 400:
        return "UNKNOWN_DIFFERENT_CLASS_DISPUTE"
    if facts.get("supplemental_paid_cents") != 421763:
        return "UNKNOWN_SUPPLEMENT_AMOUNT_MISMATCH"
    return "HISTORICAL_GAO_OFFSET_ONLY"

class GAOB223311LegacyCrosswalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(PACK.read_text(encoding="utf-8"))
        cls.sources = json.loads(SOURCE.read_text(encoding="utf-8"))["sources"]
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["records"]
        tree = ast.parse(DOC.read_text(encoding="utf-8"))
        cls.historical = None
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "HISTORICAL_GAO"
                for t in statement.targets
            ):
                cls.historical = ast.literal_eval(statement.value)
                break
        if cls.historical is None:
            raise AssertionError("Legacy HISTORICAL_GAO mapping unavailable")

    def test_three_legacy_pointers_are_one_original_decision_not_three_labels(self):
        crosswalk = self.p["origin_and_legacy_dedup"]
        url = crosswalk["canonical_source_url"]
        sources = [r for r in self.sources if r.get("url") == url]
        ledger = [r for r in self.ledger if r.get("url") == url]
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(ledger), 1)
        self.assertEqual(self.historical["B-223311-0"], url)
        self.assertEqual(len({sources[0]["url"], ledger[0]["url"], self.historical["B-223311-0"]}), 1)
        self.assertEqual(crosswalk["duplicate_source_rows_collapsed_to_one"], 3)
        self.assertEqual(crosswalk["legacy_ledger_source_id"], ledger[0]["id"])
        self.assertEqual(crosswalk["legacy_ledger_reported_sha256"], ledger[0]["sha256"])
        self.assertEqual(crosswalk["legacy_ledger_reported_bytes_seen"], ledger[0]["bytes_seen"])
        self.assertFalse(ledger[0]["raw_document_stored"])
        self.assertFalse(crosswalk["legacy_15_labs_fully_consolidated"])

    def test_official_historical_two_billing_events_not_two_recoveries(self):
        p = self.p
        f = p["actual_case_from_first_party"]
        self.assertEqual(p["original_source"]["decision_date"], "1987-08-03")
        self.assertEqual(f["original_class100_reported_charge_cents"], 72753)
        self.assertEqual(f["subsequent_class400_supplement_paid_cents"], 421763)
        self.assertEqual(f["gao_reported_collected_total_before_offset_cents"], 72753 + 421763)
        self.assertEqual(f["gsa_reported_overcharge_offset_cents"], 421763)
        self.assertEqual(f["official_decision_outcome"], "GSA_DEDUCTION_SUSTAINED")
        self.assertFalse(f["bank_refund_independently_custodied"])
        self.assertFalse(f["independent_original_invoice_triple_verified"])
        self.assertIsNone(f["modern_customer_overcharge_cents"])
        self.assertEqual(f["retally_customer_recovery_cents"], 0)

    def test_source_rights_and_legacy_sha_do_not_fake_original_custody(self):
        s, r, d = self.p["original_source"], self.p["rights"], self.p["origin_and_legacy_dedup"]
        self.assertEqual(s["url"], "https://www.gao.gov/products/b-223311-0")
        self.assertEqual(r["gao_policy"], "https://www.gao.gov/copyright")
        self.assertIsNone(s["original_http_body_sha256"])
        self.assertIsNone(s["original_http_body_bytes"])
        self.assertFalse(s["original_source_raw_bytes_custodied"])
        self.assertFalse(s["original_signed_gbl_invoice_tariff_files_custodied"])
        self.assertFalse(d["legacy_sha256_independently_recomputed_this_run"])
        self.assertEqual(d["legacy_digest_equivalent_to_current_original_http_response_sha256"], "UNKNOWN_NOT_VERIFIED")
        self.assertFalse(r["commercial_customer_scoring_approved"])
        self.assertEqual(r["third_party_underlying_material"], "UNKNOWN_NOT_REPRODUCED")

    def test_mutated_synthetic_evidence_fails_closed_to_unknown(self):
        b = self.p["historical_reference_guard"]
        self.assertEqual(historical_reference_guard(b), b["expected"])
        controls = self.p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 7)
        self.assertEqual(len({x["id"] for x in controls}), len(controls))
        for c in controls:
            with self.subTest(control=c["id"]):
                self.assertTrue(c["id"].startswith("SYN_"))
                altered = deepcopy(b)
                altered.update(c["mutation"])
                self.assertEqual(historical_reference_guard(altered), c["expected"])
                self.assertNotEqual(historical_reference_guard(altered), b["expected"])

    def test_cross_case_comparison_not_a_blind_model_score(self):
        h = self.p["label_and_holdout"]
        self.assertIn("https://www.gao.gov/products/b-221594-0", {x["url"] for x in self.sources})
        self.assertEqual(self.historical["B-221594-0"], h["comparison_source_url"])
        self.assertEqual(h["external_original_adjudication_cases"], 1)
        self.assertEqual(h["independently_held_out_customer_invoice_cases"], 0)
        self.assertEqual(h["real_world_heldout_model_predictions"], 0)
        self.assertTrue(h["two_case_reference_contrast_not_blind"])
        self.assertIsNone(h["modern_precision"])
        self.assertIsNone(h["modern_recall"])
        self.assertIsNone(h["true_modern_error_label"])

    def test_lab15_legacy_manifest_ledger_pointer_census(self):
        """Two metadata stores are 12 shared source URLs, not 25 independent labels."""
        audit = json.loads(
            (ROOT / "fixtures" / "lab15_manifest_ledger_source_crosswalk_v1.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(audit["schema_version"], 1)
        self.assertEqual(audit["inputs"]["source_manifest_git_blob_sha1"],
                         "a905b85413f7d5b003681f45e6ed2e0b53b19ce0")
        self.assertEqual(audit["inputs"]["evidence_ledger_git_blob_sha1"],
                         "2eb9f1cbe0173bbed0049b0a88b43cc209e48b86")
        s = {entry["url"] for entry in self.sources}
        e = {entry["url"] for entry in self.ledger}
        c = audit["audit_counts"]
        self.assertEqual(len(self.sources), c["source_manifest_rows"])
        self.assertEqual(len(self.ledger), c["evidence_ledger_rows"])
        self.assertEqual(len(s & e), c["shared_exact_source_url_keys"])
        self.assertEqual(len(s - e), c["source_manifest_only_keys"])
        self.assertEqual(len(e - s), c["ledger_only_keys"])
        self.assertEqual(len(s | e), c["unique_publisher_url_keys"])
        self.assertEqual(e - s, {audit["ledger_only_unverified_lead"]["url"]})
        self.assertEqual(sum(bool(x["sha256"]) for x in self.ledger),
                         c["legacy_ledger_reported_fingerprints"])
        self.assertEqual(sum(bool(x["raw_document_stored"]) for x in self.ledger),
                         c["raw_original_documents_custodied"])
        self.assertEqual(sum(bool(x["commercial_test_approved"]) for x in self.ledger),
                         c["commercially_approved_sources"])
        self.assertEqual(sum(bool(x["independent_invoice_error_verified"]) for x in self.ledger),
                         c["independently_verified_customer_invoice_errors"])
        self.assertEqual(c["verified_legacy_lab_retirements"], 0)
        self.assertIsNone(audit["inputs"]["source_original_http_sha256_this_cycle"])
        self.assertIsNone(audit["ledger_only_unverified_lead"]["ground_truth_label"])
        self.assertFalse(audit["interpretation"]["legacy_lab_retirement_authorized"])
        controls = audit["synthetic_negative_controls"]
        self.assertEqual(len(controls), 3)
        self.assertEqual(len({x["id"] for x in controls}), len(controls))
        for control in controls:
            self.assertTrue(control["id"].startswith("SYN_"))
            self.assertIsNone(control["independent_real_label"])
            self.assertTrue(control["expected_guard"].startswith(("UNKNOWN_", "REJECT_")))

    def test_nonpromotion_controls_and_engine_boundaries(self):
        controls = self.p["forbidden_promotions"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({x["id"] for x in controls}), 5)
        for c in controls:
            with self.subTest(control=c["id"]):
                self.assertTrue(c["id"].startswith("SYN_"))
                self.assertTrue(c["expected"].startswith("REJECT_"))
        scope = self.p["scope"]
        self.assertEqual(scope["owner_review_pr"], 883)
        self.assertFalse(scope["live_research_writer_modified"])
        self.assertFalse(scope["production_code_modified"])
        self.assertFalse(scope["producer_cost_increase"])
        self.assertFalse(scope["new_schedule"])
        self.assertFalse(scope["release_authorized"])
        self.assertEqual(scope["actual_customer_cash_cents"], 0)

if __name__ == "__main__":
    unittest.main()
