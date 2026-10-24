"""GAO B-189100: real historical classification dispute, NOT a customer benchmark."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from freight.real_world_eval_v1 import load_manifest
from freight.research_eval_bridge import build_feed, validate_feed
from freight.test_research_eval_bridge import legacy_candidates, legacy_evidence
from freight.unified_research_lab import ResearchError, SEEDS, digest, ledger_from, source_record

URL = "https://www.gao.gov/products/b-189100"
PATH = Path(__file__).with_name("fixtures") / "gao_b189100_classification_v1.json"
MANIFEST_SHA256 = "e8c45f1e0a1ab632219346995adcc85c61c918ed1a3acbc4be37a255fe7ef795"


def fixture():
    return json.loads(PATH.read_text(encoding="utf-8"))


def verify(doc):
    if digest({k: v for k, v in doc.items() if k != "manifest_sha256"}) != doc.get("manifest_sha256"):
        raise ResearchError("GAO_B189100_MANIFEST_TAMPER")
    s, f, lim = doc["source"], doc["facts"], doc["limits"]
    if not (
        doc["schema_version"] == "1.0.0"
        and doc["evidence_lane"] == "freight_error_adjudication"
        and doc["status"] == "HISTORICAL_GAO_DECISION_LEVEL_LABEL_NOT_INDEPENDENT_INVOICE_BENCHMARK"
        and s["url"] == URL and s["case_number"] == "B-189100"
        and s["decision_date"] == "1977-12-27"
        and s["rights_url"] == "https://www.gao.gov/copyright"
        and s["source_bytes_sha256"] is None
        and s["source_bytes_acquired"] is False
        and s["commercial_engine_reuse_approved"] is False
        and doc["cohort"]["held_out_from_engine_training_verified"] is False
        and doc["cohort"]["original_invoice_bytes_available"] is False
        and f["gbl_id"] == "A-6018184"
        and f["charged_nmfc_item"] == 41050
        and f["adjudicated_nmfc_item"] == 41060
        and f["billed_charges_cents"] == 356718
        and f["gao_overcharge_deduction_cents"] == 263438
        and f["implied_allowable_cents"] == 93280
        and f["billed_charges_cents"] - f["gao_overcharge_deduction_cents"] == f["implied_allowable_cents"]
        and f["implied_allowable_derivation"] == "BILLED_MINUS_REPORTED_DEDUCTION_NOT_INDEPENDENT_RATE_VALIDATION"
        and f["shipper_photo_and_report_source_bytes_available"] is False
        and f["original_bol_description_contradicted_by_later_shipper_photo_report"] is True
        and f["gao_disposition"] == "GSA_DEDUCTION_SUSTAINED"
        and f["historical_gsa_deduction_reported_collected"] is True
        and f["retally_cash_recovered_cents"] == 0
        and f["independently_verified_customer_refund_cents"] is None
        and f["independently_verified_original_invoice_error_cents"] is None
        and lim["independent_invoice_accuracy_scoring_permitted"] is False
        and lim["modern_tariff_applicability_verified"] is False
        and lim["original_invoice_or_bol_image_available"] is False
        and lim["original_photographic_corroboration_available"] is False
        and lim["verified_retally_recovery_cents"] == 0
        and doc["data_quality"]["third_party_image_rights_not_verified"] is True
        and len(doc["synthetic_negative_controls"]) == 2
        and all(x["synthetic"] is True and x["real_invoice_error_cents"] is None
                for x in doc["synthetic_negative_controls"])
    ):
        raise ResearchError("GAO_B189100_TRUTH_OR_SCOPE_MISMATCH")
    return doc


class GAOCargoClassificationEvidenceTests(unittest.TestCase):
    def test_original_publisher_source_and_authored_hash(self):
        x = verify(fixture())
        self.assertEqual(x["manifest_sha256"], MANIFEST_SHA256)
        self.assertIn(URL, SEEDS["freightrecovery"])

    def test_real_adjudicated_deduction_arithmetic_not_invoice_bytes(self):
        x = verify(fixture())
        self.assertEqual(x["facts"]["billed_charges_cents"], 356718)
        self.assertEqual(x["facts"]["gao_overcharge_deduction_cents"], 263438)
        self.assertEqual(x["facts"]["implied_allowable_cents"], 93280)
        self.assertFalse(x["limits"]["original_photographic_corroboration_available"])
        self.assertFalse(x["limits"]["independent_invoice_accuracy_scoring_permitted"])

    def test_negative_controls_are_explicitly_synthetic(self):
        x = verify(fixture())
        self.assertEqual([c["expected"] for c in x["synthetic_negative_controls"]], [
            "REJECT_REQUIRE_CORROBORATING_CARGO_EVIDENCE",
            "REJECT_HISTORICAL_TARIFF_NOT_CURRENT_AUTHORITY",
        ])

    def test_rehashed_forgery_cannot_promote_deduction_to_customer_truth(self):
        original = verify(fixture())
        for section, field, wrong in (
            ("source", "commercial_engine_reuse_approved", True),
            ("source", "source_bytes_acquired", True),
            ("source", "source_bytes_sha256", "f" * 64),
            ("facts", "retally_cash_recovered_cents", 263438),
            ("facts", "independently_verified_customer_refund_cents", 263438),
            ("facts", "independently_verified_original_invoice_error_cents", 263438),
            ("facts", "historical_gsa_deduction_reported_collected", False),
            ("facts", "adjudicated_nmfc_item", 41050),
            ("facts", "gao_overcharge_deduction_cents", 263437),
            ("cohort", "held_out_from_engine_training_verified", True),
            ("limits", "independent_invoice_accuracy_scoring_permitted", True),
            ("limits", "modern_tariff_applicability_verified", True),
            ("limits", "verified_retally_recovery_cents", 263438),
            ("data_quality", "third_party_image_rights_not_verified", False),
        ):
            changed = deepcopy(original)
            changed[section][field] = wrong
            changed["manifest_sha256"] = digest({
                k: v for k, v in changed.items() if k != "manifest_sha256"
            })
            with self.subTest(field=field), self.assertRaises(ResearchError):
                verify(changed)

    def test_url_enters_existing_bridge_without_earned_accuracy(self):
        verify(fixture())
        ledger = ledger_from([source_record(URL, "freightrecovery", "2026-10-24")])
        evidence, candidates, manifest = legacy_evidence(), legacy_candidates(), load_manifest()
        feed = build_feed(ledger, evidence, candidates, manifest)
        row = feed["candidate_sources"][0]
        self.assertEqual(feed["source_pointers_total"], 1)
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
        forged["candidate_sources"][0]["model"]["verified_freight_error_cents"] = 263438
        forged["feed_sha256"] = digest({
            k: v for k, v in forged.items() if k != "feed_sha256"
        })
        with self.assertRaises(ResearchError):
            validate_feed(forged, ledger, evidence, candidates, manifest)


if __name__ == "__main__":
    unittest.main()
