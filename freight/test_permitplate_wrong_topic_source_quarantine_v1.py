"""Pinned metadata-only research source quarantine; no customer/permit documents."""
import json
import unittest
from pathlib import Path
from freight.unified_research_lab import digest, permitplate_url_in_scope

PACK = Path(__file__).with_name("fixtures") / "permitplate_wrong_topic_source_quarantine_v1.json"

class PermitPlateWrongTopicQuarantineTest(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_immutable_census_denominator_and_input_hash(self):
        m = self.pack
        self.assertEqual(m["schema_version"], 1)
        self.assertEqual(m["pinned_input"]["git_blob_sha"], "49adf78e9468b739ecaae623dd6efe159d1d84e6")
        self.assertEqual(m["pinned_input"]["entries_sha256"], "6759c4919c86264c6394ef3f0f04c07acdafaf9f72e68a9efc8a5b8b5df4a7e1")
        self.assertEqual(m["pinned_input"]["entry_count"], 252)
        self.assertEqual(m["pinned_input"]["permitplate_assigned_pointers"], 42)
        self.assertEqual(m["partition"]["observed_wrong_topic_excluded"], 18)
        self.assertEqual(m["partition"]["remaining_unreviewed_permitplate_pointers"], 24)
        self.assertEqual(len(m["cases"]), 18)
        self.assertIn("UNVERIFIED", m["partition"]["remaining_status"])

    def test_all_18_original_pointer_ids_first_seen_and_rejection(self):
        rows = self.pack["cases"]
        self.assertEqual(len({r["id"] for r in rows}), 18)
        self.assertEqual(len({r["url"] for r in rows}), 18)
        for r in rows:
            with self.subTest(url=r["url"]):
                self.assertEqual(r["id"], digest(r["url"]))
                self.assertIn(r["first_seen"], ("2026-10-22", "2026-10-23"))
                self.assertFalse(permitplate_url_in_scope(r["url"]))
                self.assertEqual(r["expected_result"], "QUARANTINE_WRONG_TOPIC")
                self.assertIsNone(r["real_outcome_label"])
                self.assertIn("UNVERIFIED", r["source_rights_state"])
                self.assertIn("UNVERIFIED", r["source_truth_state"])

    def test_five_newly_verified_publisher_metadata_only_out_of_scope(self):
        newest = [r for r in self.pack["cases"] if r.get("metadata_checked_on") == "2026-10-23"]
        self.assertEqual(len(newest), 5)
        self.assertEqual(next(r for r in newest if r["url"].endswith("43nn-pn8j"))["first_seen"], "2026-10-22")
        for row in newest:
            self.assertTrue(row["metadata_only"])
            self.assertTrue(row["publisher_metadata_reference"].startswith("https://"))
            self.assertFalse(permitplate_url_in_scope(row["url"]))
            self.assertIsNone(row["real_outcome_label"])

    def test_synthetic_negative_and_official_candidate_still_unadjudicated(self):
        neg, candidate = self.pack["synthetic_negative_controls"]
        self.assertEqual(neg["kind"], "SYNTHETIC")
        self.assertFalse(permitplate_url_in_scope(neg["url"]))
        self.assertEqual(neg["expected"], "REJECT_WRONG_TOPIC")
        self.assertEqual(candidate["kind"], "SYNTHETIC")
        self.assertTrue(permitplate_url_in_scope(candidate["url"]))
        self.assertEqual(candidate["expected"], "CANDIDATE_ONLY_RIGHTS_AND_ISSUANCE_LABELS_UNVERIFIED")

    def test_never_promote_pointers_to_rights_accuracy_or_real_outcomes(self):
        m = self.pack
        self.assertEqual(m["actual_document_or_permit_rows_ingested"], 0)
        self.assertEqual(m["independent_issuance_labels"], 0)
        self.assertIsNone(m["original_document_sha256"])
        self.assertFalse(m["commercial_reuse_approved"])
        self.assertEqual(m["accuracy_reporting"]["permit_opportunity_scoring"], "UNKNOWN_NO_INDEPENDENT_HELD_OUT_OUTCOMES")
        for field in ("original_freight_invoice_extraction", "general_accounting_reconciliation",
                      "freight_error_detection", "recovery_outcomes"):
            self.assertEqual(m["accuracy_reporting"][field], "NOT_EVALUATED")

if __name__ == "__main__":
    unittest.main()
