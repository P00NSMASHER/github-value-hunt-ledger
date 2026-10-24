"""GAO B-221594: rejected historical tender is a negative recovery control."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest

from freight.real_world_eval_v1 import load_manifest
from freight.research_eval_bridge import build_feed, validate_feed
from freight.test_research_eval_bridge import legacy_candidates, legacy_evidence
from freight.unified_research_lab import ResearchError, SEEDS, digest, ledger_from, source_record

URL = "https://www.gao.gov/products/b-221594-0"
PATH = Path(__file__).with_name("fixtures") / "gao_b221594_source_v1.json"
SHA = "87da32abe9ec46640a33b8b3b3b9f940a15524732b5026ebbc580fbc45f6660c"


def fixture():
    return json.loads(PATH.read_text(encoding="utf-8"))


def verify_fixture(doc):
    computed = digest({k: v for k, v in doc.items() if k != "manifest_sha256"})
    if doc.get("manifest_sha256") != computed:
        raise ResearchError("GAO_NEGATIVE_MANIFEST_SHA_MISMATCH")
    s, f, l, second = doc["source"], doc["facts"], doc["limits"], doc["documented_second_shipment"]
    if not (
        doc["schema_version"] == "1.0.0"
        and doc["evidence_lane"] == "freight_error_adjudication_negative_control"
        and s["original_record_url"] == URL
        and s["case_number"] == "B-221594"
        and s["decision_date"] == "1986-09-29"
        and s["original_source_bytes_sha256"] is None
        and s["source_bytes_acquired"] is False
        and s["commercial_engine_use_independently_approved"] is False
        and f["carrier_reported_charges_cents"] == 94200
        and f["gsa_applied_lower_rate_cents"] == 72125
        and f["gsa_deduction_cents"] == 22075
        and f["carrier_reported_charges_cents"] - f["gsa_applied_lower_rate_cents"] == f["gsa_deduction_cents"]
        and f["gaos_final_determination"] == "GSA_DEDUCTION_INVALID_FOR_DOD_REJECTED_TENDER"
        and f["independent_per_invoice_overcharge_amount_cents"] is None
        and f["verified_actual_refund_to_carrier_cents"] is None
        and f["verified_retally_recovered_cash_cents"] == 0
        and l["independent_invoice_error_accuracy_scoring_permitted"] is False
        and l["other_non_dod_agencies_same_tender_result"] == "UNKNOWN"
        and l["payer_credits_or_refunds_received"] == "UNKNOWN"
        and doc["cohort"]["independently_held_out_from_training_verified"] is False
        and second["source_section"] == "DECISION_FOOTNOTE_1"
        and second["government_bill_of_lading"] == "S-5694340"
        and second["received_by_carrier_date"] == "1983-08-23"
        and second["synthetic"] is False
        and second["original_gbl_bytes_available"] is False
        and second["carrier_charges_cents"] is None
        and second["gsa_deduction_cents"] is None
        and second["independently_scored_invoice_error_cents"] is None
        and second["verified_actual_refund_cents"] is None
        and second["label_completeness"] == "IDENTIFIER_AND_DATE_ONLY"
        and second["ground_truth_limit"] == "PUBLISHER_DECISION_SCOPE_NOT_INDEPENDENT_SHIPMENT_AUDIT"
        and doc["data_quality"]["second_gbl_footnote_verified_on_official_GAO_page"] is True
        and len(doc["synthetic_negative_controls"]) == 3
        and all(c["synthetic"] is True and c["real_invoice_error_cents"] is None
                for c in doc["synthetic_negative_controls"])
    ):
        raise ResearchError("GAO_NEGATIVE_SCOPE_OR_TRUTH_MISMATCH")
    return doc


class GAORejectedTenderEvidenceTests(unittest.TestCase):
    def test_original_source_and_manifest_integrity(self):
        doc = verify_fixture(fixture())
        self.assertEqual(doc["manifest_sha256"], SHA)
        self.assertIn(URL, SEEDS["freightrecovery"])
        self.assertEqual(doc["source"]["rights_url"], "https://www.gao.gov/copyright")
        self.assertTrue(doc["data_quality"]["published_decision_has_OCR_L_1_ambiguity"])
        self.assertEqual(doc["facts"]["original_gbl_number"], "UNKNOWN_OCR_L_VS_1_AMBIGUITY")

    def test_second_original_gbl_footnote_stays_unlabeled(self):
        doc = verify_fixture(fixture())
        second = doc["documented_second_shipment"]
        self.assertFalse(second["synthetic"])
        self.assertEqual(second["government_bill_of_lading"], "S-5694340")
        self.assertEqual(second["received_by_carrier_date"], "1983-08-23")
        self.assertIsNone(second["carrier_charges_cents"])
        self.assertIsNone(second["gsa_deduction_cents"])
        self.assertIsNone(second["independently_scored_invoice_error_cents"])
        self.assertFalse(second["original_gbl_bytes_available"])

    def test_negative_1986_decision_does_not_transfer_to_other_agencies(self):
        doc = verify_fixture(fixture())
        f = doc["facts"]
        self.assertLess(date.fromisoformat(f["nominal_tender_effective_date"]),
                        date.fromisoformat(f["mtmc_tender_returned_date"]))
        self.assertLess(date.fromisoformat(f["mtmc_tender_returned_date"]),
                        date.fromisoformat(f["example_dod_shipment_date"]))
        self.assertLess(date.fromisoformat(f["example_dod_shipment_date"]),
                        date.fromisoformat(doc["source"]["decision_date"]))
        self.assertEqual(f["decision_level_ground_truth_label"], "NEGATIVE_GSA_OVERCHARGE_DEDUCTION")
        self.assertEqual([c["expected"] for c in doc["synthetic_negative_controls"]], [
            "DO_NOT_ASSERT_OVERCHARGE_USING_REJECTED_TENDER",
            "UNKNOWN_CANNOT_TRANSFER_DOD_REJECTION_AUTOMATICALLY",
            "UNKNOWN_REQUIRE_ACCEPTANCE_AND_EFFECTIVE_DATE",
        ])

    def test_rehashed_forgery_cannot_promote_historical_amount_into_cash_or_invoice_truth(self):
        original = verify_fixture(fixture())
        for first, field, value in (
            ("source", "commercial_engine_use_independently_approved", True),
            ("facts", "verified_retally_recovered_cash_cents", 22075),
            ("facts", "verified_actual_refund_to_carrier_cents", 22075),
            ("facts", "independent_per_invoice_overcharge_amount_cents", 22075),
            ("limits", "independent_invoice_error_accuracy_scoring_permitted", True),
            ("limits", "other_non_dod_agencies_same_tender_result", "GSA_INVALID"),
            ("documented_second_shipment", "gsa_deduction_cents", 22075),
            ("documented_second_shipment", "independently_scored_invoice_error_cents", 22075),
            ("documented_second_shipment", "original_gbl_bytes_available", True),
            ("documented_second_shipment", "synthetic", True),
        ):
            altered = deepcopy(original)
            altered[first][field] = value
            altered["manifest_sha256"] = digest({k: v for k, v in altered.items()
                                                  if k != "manifest_sha256"})
            with self.subTest(field=field), self.assertRaises(ResearchError):
                verify_fixture(altered)

    def test_source_pointer_flows_through_eval_bridge_without_claiming_accuracy(self):
        verify_fixture(fixture())
        ledger = ledger_from([source_record(URL, "freightrecovery", "2026-10-24")])
        evidence, candidates, manifest = legacy_evidence(), legacy_candidates(), load_manifest()
        feed = build_feed(ledger, evidence, candidates, manifest)
        self.assertEqual(feed["source_pointers_total"], 1)
        row = feed["candidate_sources"][0]
        self.assertEqual(row["source_url"], URL)
        self.assertIsNone(row["case_id"])
        self.assertFalse(row["commercial_reuse_authorized"])
        self.assertFalse(row["independent_ground_truth"])
        self.assertFalse(row["independent_payment_verified"])
        self.assertFalse(row["source_document_ingested"])
        self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        validate_feed(feed, ledger, evidence, candidates, manifest)
        forged = deepcopy(feed)
        forged["candidate_sources"][0]["model"]["verified_freight_error_cents"] = 22075
        forged["feed_sha256"] = digest({k: v for k, v in forged.items()
                                        if k != "feed_sha256"})
        with self.assertRaises(ResearchError):
            validate_feed(forged, ledger, evidence, candidates, manifest)


if __name__ == "__main__":
    unittest.main()
