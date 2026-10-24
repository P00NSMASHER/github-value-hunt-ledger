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
MANIFEST_SHA256 = "04ef581e072dfeb356bb6e914da33090a2b7eb717a2bf528ec96ebc364b64f1d"


def fixture():
    return json.loads(PATH.read_text(encoding="utf-8"))


def verify(doc):
    if digest({k: v for k, v in doc.items() if k != "manifest_sha256"}) != doc.get("manifest_sha256"):
        raise ResearchError("GAO_B189100_MANIFEST_TAMPER")
    s, f, lim, cap = doc["source"], doc["facts"], doc["limits"], doc["capacity_evidence"]
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
        and cap["source_url"] == URL
        and cap["source_section"] == "DECISION_CARRIER_RATING_AND_FINAL_GSA_ALTERNATIVE_REASON"
        and cap["charged_item"] == f["charged_nmfc_item"] == 41050
        and cap["published_item_41050_minimum_capacity_cuft"] == 135
        and cap["published_container_capacity_cuft"] == 52
        and cap["capacity_deficit_cuft"] == 83
        and cap["published_item_41050_minimum_capacity_cuft"] - cap["published_container_capacity_cuft"] == cap["capacity_deficit_cuft"]
        and cap["gao_excludes_item_41050_on_capacity_even_if_shape_disputed"] is True
        and cap["final_paragraph_item_41060_reference_conflicts_with_earlier_41050_rating"] is True
        and cap["item_41060_capacity_threshold_independently_verified"] is False
        and cap["original_tariff_pages_in_custody"] is False
        and cap["commercial_engine_use_authorized"] is False
        and cap["independent_invoice_accuracy_label_permitted"] is False
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
        and len(doc["synthetic_negative_controls"]) == 3
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

    def test_capacity_threshold_conflicted_gao_prose_is_not_modern_tariff_truth(self):
        x = verify(fixture())
        cap = x["capacity_evidence"]
        self.assertEqual(cap["charged_item"], 41050)
        self.assertEqual(cap["published_item_41050_minimum_capacity_cuft"], 135)
        self.assertEqual(cap["published_container_capacity_cuft"], 52)
        self.assertEqual(cap["capacity_deficit_cuft"], 83)
        self.assertTrue(cap["gao_excludes_item_41050_on_capacity_even_if_shape_disputed"])
        self.assertTrue(cap["final_paragraph_item_41060_reference_conflicts_with_earlier_41050_rating"])
        self.assertFalse(cap["item_41060_capacity_threshold_independently_verified"])
        self.assertFalse(cap["original_tariff_pages_in_custody"])
        self.assertFalse(cap["independent_invoice_accuracy_label_permitted"])
        self.assertFalse(x["limits"]["independent_invoice_accuracy_scoring_permitted"])
        self.assertIsNone(x["facts"]["independently_verified_original_invoice_error_cents"])

    def test_negative_controls_are_explicitly_synthetic(self):
        x = verify(fixture())
        self.assertEqual([c["expected"] for c in x["synthetic_negative_controls"]], [
            "REJECT_REQUIRE_CORROBORATING_CARGO_EVIDENCE",
            "REJECT_HISTORICAL_TARIFF_NOT_CURRENT_AUTHORITY",
            "UNKNOWN_DO_NOT_ATTRIBUTE_135_CUFT_MINIMUM_TO_41060_OR_MODERN_TARIFF",
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
            ("capacity_evidence", "published_item_41050_minimum_capacity_cuft", 52),
            ("capacity_evidence", "published_container_capacity_cuft", 135),
            ("capacity_evidence", "final_paragraph_item_41060_reference_conflicts_with_earlier_41050_rating", False),
            ("capacity_evidence", "original_tariff_pages_in_custody", True),
            ("capacity_evidence", "commercial_engine_use_authorized", True),
            ("capacity_evidence", "independent_invoice_accuracy_label_permitted", True),
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



# Companion classification control: a second pickup carrier is not, by itself,
# evidence of an interline rate. Keep this in the already scheduled nightly lane.
AGENT_URL = "https://www.gao.gov/products/b-221663-0"
AGENT_PATH = Path(__file__).with_name("fixtures") / "gao_b221663_agent_interline_v1.json"
AGENT_MANIFEST_SHA256 = "b79983f508686ba0250de0f77ef393fcef7289f6e4e9fbc47bac36c10dd38d0e"


def agent_fixture():
    return json.loads(AGENT_PATH.read_text(encoding="utf-8"))


def validate_agent_fixture(doc):
    if digest({k: v for k, v in doc.items() if k != "manifest_sha256"}) != doc.get("manifest_sha256"):
        raise ResearchError("GAO_B221663_AUTHORED_MANIFEST_HASH_MISMATCH")
    s, c, f, x, lim, quality = (doc["source"], doc["cohort"], doc["shipment"],
                              doc["source_conflict"], doc["limits"], doc["data_quality"])
    if not (
        doc["schema_version"] == "1.0.0"
        and doc["fixture_id"] == "GAO_B221663_AGENT_INTERLINE_DISPUTE_V1"
        and doc["evidence_lane"] == "freight_error_adjudication"
        and doc["status"] == "HISTORICAL_DECISION_LEVEL_AGENT_CLASSIFICATION_NOT_INVOICE_BENCHMARK"
        and s["original_record_url"] == AGENT_URL
        and s["case_number"] == "B-221663"
        and s["decision_date"] == "1986-10-10"
        and s["rights_url"] == "https://www.gao.gov/copyright"
        and s["source_bytes_acquired"] is False
        and s["original_source_bytes_sha256"] is None
        and s["commercial_engine_use_approved"] is False
        and c["independent_government_adjudication"] is True
        and c["held_out_from_engine_training_verified"] is False
        and c["original_gbl_or_carrier_invoice_bytes_available"] is False
        and c["decision_level_label_scope"] == "GAO_SUSTAINED_GSA_RATE_DEDUCTION_ONLY"
        and f["government_bill_of_lading"] == "S-5789267"
        and f["shipment_date"] == "1982-12-17"
        and f["pickup_carrier"] == "Merchants Fast Motor Lines"
        and f["billing_delivering_carrier"] == "Yellow Freight System"
        and f["historical_tender"] == "Yellow Freight Tender ICC 2094"
        and f["tender_in_effect_on_shipment_date"] is True
        and f["pickup_carrier_receipted_as_yellow_agent"] is True
        and f["contract_rate_mode_adjudicated"] == "SINGLE_LINE_YELLOW_AGENT"
        and f["joint_line_rate_claim_by_carrier"] is True
        and f["gao_disposition"] == "GSA_LOWER_SINGLE_LINE_DEDUCTION_SUSTAINED"
        and f["deduction_cents_from_original_decision"] is None
        and f["invoice_line_amounts_available"] is False
        and f["verified_retally_recovery_cents"] == 0
        and f["actual_refund_received_cents"] is None
        and f["independent_invoice_error_amount_cents"] is None
        and x["specific_fort_sam_houston_letter_date"] == "1986-04-04"
        and x["general_bay_city_letter_date"] == "1986-04-08"
        and x["later_general_letter_may_conflict_with_specific_letter"] is True
        and x["original_letters_in_custody"] is False
        and x["new_independent_fact_verification"] is False
        and lim["contemporaneous_carrier_contract_pages_available"] is False
        and lim["original_bol_or_invoice_images_verified"] is False
        and lim["commercial_engine_use_authorized"] is False
        and lim["independent_invoice_accuracy_scoring_permitted"] is False
        and lim["non_dod_shipments_same_result"] == "UNKNOWN"
        and lim["other_shipments_same_rates"] == "UNKNOWN"
        and lim["independent_customer_payment_chain_verified"] is False
        and lim["verified_retally_recovered_cash_cents"] == 0
        and quality["source_amount_absent"] is True
        and quality["decision_level_label_complete"] is True
        and quality["shipment_invoice_level_label_complete"] is False
        and quality["original_publisher_source_bytes_hashed"] is False
        and quality["private_customer_medical_student_data_used"] is False
        and len(doc["synthetic_negative_controls"]) == 3
        and all(v["synthetic"] is True and v["verified_invoice_error_cents"] is None
                for v in doc["synthetic_negative_controls"])
    ):
        raise ResearchError("GAO_B221663_CLASSIFICATION_OR_TRUTH_SCOPE_MISMATCH")
    return doc


class GAOAgentVersusInterlineEvidenceTests(unittest.TestCase):
    def test_official_source_and_exact_authored_manifest_hash(self):
        doc = validate_agent_fixture(agent_fixture())
        self.assertEqual(doc["manifest_sha256"], AGENT_MANIFEST_SHA256)
        self.assertIn(AGENT_URL, SEEDS["freightrecovery"])
        self.assertFalse(doc["source"]["commercial_engine_use_approved"])
        self.assertIsNone(doc["source"]["original_source_bytes_sha256"])

    def test_specific_shipment_evidence_controls_agent_classification_only(self):
        doc = validate_agent_fixture(agent_fixture())
        self.assertLess(doc["shipment"]["shipment_date"], doc["source"]["decision_date"])
        self.assertLess(doc["source_conflict"]["specific_fort_sam_houston_letter_date"],
                        doc["source_conflict"]["general_bay_city_letter_date"])
        self.assertEqual(doc["shipment"]["contract_rate_mode_adjudicated"], "SINGLE_LINE_YELLOW_AGENT")
        self.assertEqual(doc["shipment"]["gao_disposition"], "GSA_LOWER_SINGLE_LINE_DEDUCTION_SUSTAINED")
        self.assertIsNone(doc["shipment"]["deduction_cents_from_original_decision"])
        self.assertIsNone(doc["shipment"]["independent_invoice_error_amount_cents"])
        self.assertFalse(doc["cohort"]["held_out_from_engine_training_verified"])
        self.assertFalse(doc["limits"]["independent_invoice_accuracy_scoring_permitted"])

    def test_missing_agency_evidence_and_modern_tariff_are_synthetic_unknown_or_reject(self):
        doc = validate_agent_fixture(agent_fixture())
        self.assertEqual([v["expected"] for v in doc["synthetic_negative_controls"]], [
            "REJECT_PICKUP_CARRIER_ALONE_NOT_PROOF_OF_INTERLINE",
            "UNKNOWN_DO_NOT_INFER_SINGLE_LINE_RATE",
            "REJECT_HISTORICAL_TENDER_NOT_CURRENT_CONTRACT_AUTHORITY",
        ])
        self.assertFalse(doc["source_conflict"]["original_letters_in_custody"])

    def test_rehashed_forgery_cannot_turn_historical_decision_into_invoice_or_cash_truth(self):
        doc = validate_agent_fixture(agent_fixture())
        for section, field, forbidden in (
            ("source", "original_source_bytes_sha256", "f" * 64),
            ("source", "source_bytes_acquired", True),
            ("source", "commercial_engine_use_approved", True),
            ("cohort", "held_out_from_engine_training_verified", True),
            ("cohort", "original_gbl_or_carrier_invoice_bytes_available", True),
            ("shipment", "deduction_cents_from_original_decision", 100),
            ("shipment", "independent_invoice_error_amount_cents", 100),
            ("shipment", "verified_retally_recovery_cents", 100),
            ("shipment", "actual_refund_received_cents", 100),
            ("limits", "commercial_engine_use_authorized", True),
            ("limits", "independent_invoice_accuracy_scoring_permitted", True),
            ("limits", "verified_retally_recovered_cash_cents", 100),
            ("data_quality", "shipment_invoice_level_label_complete", True),
        ):
            changed = deepcopy(doc)
            changed[section][field] = forbidden
            changed["manifest_sha256"] = digest({
                k: v for k, v in changed.items() if k != "manifest_sha256"
            })
            with self.subTest(section=section, field=field), self.assertRaises(ResearchError):
                validate_agent_fixture(changed)

    def test_public_url_enters_existing_feed_as_unscored_candidate(self):
        validate_agent_fixture(agent_fixture())
        ledger = ledger_from([source_record(AGENT_URL, "freightrecovery", "2026-10-24")])
        evidence, candidates, manifest = legacy_evidence(), legacy_candidates(), load_manifest()
        feed = build_feed(ledger, evidence, candidates, manifest)
        self.assertEqual(feed["source_pointers_total"], 1)
        row = feed["candidate_sources"][0]
        self.assertEqual(row["source_url"], AGENT_URL)
        self.assertIsNone(row["case_id"])
        self.assertFalse(row["commercial_reuse_authorized"])
        self.assertFalse(row["independent_ground_truth"])
        self.assertFalse(row["source_document_ingested"])
        self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        validate_feed(feed, ledger, evidence, candidates, manifest)




# Companion original GAO decision: historical exclusive-use freight rating.
# This is decision-level evidence, NOT an independent modern invoice benchmark.
EXCLUSIVE_URL = "https://www.gao.gov/products/b-139340"
EXCLUSIVE_PATH = Path(__file__).with_name("fixtures") / "gao_b139340_exclusive_use_v1.json"
EXCLUSIVE_MANIFEST_SHA256 = "a2f0f9275eab53fc8a60ceeb31083d07a275d62982c15ff3734d5a0e8b93bb6a"


def exclusive_fixture():
    return json.loads(EXCLUSIVE_PATH.read_text(encoding="utf-8"))


def validate_exclusive_fixture(doc):
    try:
        if digest({k: v for k, v in doc.items() if k != "manifest_sha256"}) != doc.get("manifest_sha256"):
            raise ResearchError("GAO_B139340_AUTHORED_HASH_MISMATCH")
        s, sh, r, g, q = (doc["source"], doc["shipment"], doc["historical_rating"],
                          doc["ground_truth"], doc["data_quality"])
        checks = (
            doc["schema_version"] == "1.0.0"
            and doc["fixture_id"] == "GAO_B139340_EXCLUSIVE_USE_RATE_DISPUTE_V1"
            and doc["evidence_lane"] == "freight_error_adjudication"
            and doc["status"] == "HISTORICAL_GAO_DECISION_LEVEL_NUMERIC_LABEL_NOT_CUSTOMER_INVOICE_BENCHMARK"
            and doc["manifest_hash_contract"] == "AUTHORED_CANONICAL_JSON_SHA256_EXCLUDING_SELF_NOT_ORIGINAL_PUBLISHER_BYTES"
            and s["case_number"] == "B-139340"
            and s["original_record_url"] == EXCLUSIVE_URL
            and s["decision_date"] == "1959-07-29"
            and s["rights_url"] == "https://www.gao.gov/copyright"
            and s["original_source_bytes_sha256"] is None
            and s["original_source_bytes_acquired"] is False
            and s["commercial_engine_use_approved"] is False
            and sh["gbl_id"] == "N-30864154"
            and sh["shipment_month"] == "1956-02"
            and sh["weight_pounds"] == 17250
            and sh["tariff_original_pages_available"] is False
            and sh["tariff_effective_at_shipment_independently_verified"] is False
            and r["carrier_paid_cents"] == 52360
            and r["carrier_rate_cents_per_cwt"] == 374
            and r["carrier_minimum_weight_pounds"] == 14000
            and r["gao_allowable_cents"] == 45195
            and r["gao_rate_cents_per_cwt"] == 262
            and r["gao_applied_weight_pounds"] == 17250
            and r["gao_setoff_cents"] == 7165
            and r["carrier_rate_cents_per_cwt"] * r["carrier_minimum_weight_pounds"] == r["carrier_paid_cents"] * 100
            and r["gao_rate_cents_per_cwt"] * r["gao_applied_weight_pounds"] == r["gao_allowable_cents"] * 100
            and r["carrier_paid_cents"] - r["gao_allowable_cents"] == r["gao_setoff_cents"]
            and r["deduction_reported_collected_by_government"] is True
            and r["carrier_exclusive_use_argument"] == "SEALED_OR_AUTHORIZED_BUT_NOT_SHIPPER_ORDERED_WITH_SIGNATURE"
            and r["gao_reason"] == "TARIFF_REQUIRES_SHIPPER_ORDERED_EXCLUSIVE_USE_SIGNED_ON_GBL"
            and r["gao_disposition"] == "DISALLOWANCE_SUSTAINED"
            and r["further_litigation_outcome"] == "UNKNOWN"
            and g["independent_government_decision_published"] is True
            and g["independently_held_out_from_engine_training_verified"] is False
            and g["original_bill_of_lading_or_carrier_invoice_bytes_in_custody"] is False
            and g["contemporaneous_tariff_pages_in_custody"] is False
            and g["independent_customer_payment_or_credit_chain"] is False
            and g["current_contract_rate_applicability"] == "UNKNOWN"
            and g["independent_original_invoice_error_cents"] is None
            and g["retally_verified_cash_recovered_cents"] == 0
            and g["independent_customer_invoice_accuracy_scoring_permitted"] is False
            and q["official_html_text_manually_verified"] is True
            and q["reported_number_math_complete"] is True
            and q["original_source_bytes_hash_available"] is False
            and q["source_independent_invoice_label_complete"] is False
            and q["private_customer_medical_student_data_used"] is False
            and len(doc["synthetic_negative_controls"]) == 3
            and [v["expected"] for v in doc["synthetic_negative_controls"]] == [
                "REJECT_SEAL_OR_AUTHORIZATION_IS_NOT_ORDERED_AND_SIGNED",
                "REJECT_HISTORICAL_TARIFF_NOT_CURRENT_RATE_AUTHORITY",
                "UNKNOWN_DO_NOT_INFER_VALID_EXCLUSIVE_USE",
            ]
            and all(v["synthetic"] is True and v["customer_error_cents"] is None
                    for v in doc["synthetic_negative_controls"])
        )
        if not checks:
            raise ResearchError("GAO_B139340_SOURCE_OR_TRUTH_SCOPE_MISMATCH")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ResearchError("GAO_B139340_FIXTURE_SCHEMA_INVALID") from exc
    return doc


class GAOExclusiveUseNumericalEvidenceTests(unittest.TestCase):
    def test_official_source_and_pinned_manifest_enter_canonical_seed(self):
        record = validate_exclusive_fixture(exclusive_fixture())
        self.assertEqual(record["manifest_sha256"], EXCLUSIVE_MANIFEST_SHA256)
        self.assertIn(EXCLUSIVE_URL, SEEDS["freightrecovery"])
        self.assertIsNone(record["source"]["original_source_bytes_sha256"])
        self.assertFalse(record["source"]["commercial_engine_use_approved"])

    def test_two_actual_historical_rate_formulas_reconcile_to_setoff(self):
        record = validate_exclusive_fixture(exclusive_fixture())
        r = record["historical_rating"]
        self.assertEqual((r["carrier_paid_cents"], r["gao_allowable_cents"], r["gao_setoff_cents"]),
                         (52360, 45195, 7165))
        self.assertEqual(r["carrier_rate_cents_per_cwt"] * r["carrier_minimum_weight_pounds"] // 100, 52360)
        self.assertEqual(r["gao_rate_cents_per_cwt"] * r["gao_applied_weight_pounds"] // 100, 45195)
        self.assertEqual(r["carrier_paid_cents"] - r["gao_allowable_cents"], 7165)
        self.assertTrue(r["deduction_reported_collected_by_government"])
        self.assertIsNone(record["ground_truth"]["independent_original_invoice_error_cents"])
        self.assertEqual(record["ground_truth"]["retally_verified_cash_recovered_cents"], 0)

    def test_three_negative_controls_are_explicitly_synthetic_or_unknown(self):
        record = validate_exclusive_fixture(exclusive_fixture())
        self.assertTrue(all(v["synthetic"] is True for v in record["synthetic_negative_controls"]))
        self.assertEqual(record["ground_truth"]["current_contract_rate_applicability"], "UNKNOWN")
        self.assertEqual(record["historical_rating"]["further_litigation_outcome"], "UNKNOWN")
        self.assertFalse(record["ground_truth"]["independently_held_out_from_engine_training_verified"])

    def test_rehashed_tampering_cannot_promote_customer_truth_or_modern_rate(self):
        original = validate_exclusive_fixture(exclusive_fixture())
        for section, field, invalid in (
            ("source", "original_source_bytes_sha256", "f" * 64),
            ("source", "original_source_bytes_acquired", True),
            ("source", "commercial_engine_use_approved", True),
            ("shipment", "tariff_original_pages_available", True),
            ("shipment", "tariff_effective_at_shipment_independently_verified", True),
            ("historical_rating", "carrier_paid_cents", 52361),
            ("historical_rating", "gao_setoff_cents", 7166),
            ("historical_rating", "gao_reason", "SEAL_ALONE_PROVES_EXCLUSIVE_USE"),
            ("ground_truth", "independently_held_out_from_engine_training_verified", True),
            ("ground_truth", "independent_customer_payment_or_credit_chain", True),
            ("ground_truth", "independent_original_invoice_error_cents", 7165),
            ("ground_truth", "retally_verified_cash_recovered_cents", 7165),
            ("ground_truth", "independent_customer_invoice_accuracy_scoring_permitted", True),
            ("data_quality", "source_independent_invoice_label_complete", True),
        ):
            mutated = deepcopy(original)
            mutated[section][field] = invalid
            mutated["manifest_sha256"] = digest({
                k: v for k, v in mutated.items() if k != "manifest_sha256"
            })
            with self.subTest(section=section, field=field), self.assertRaises(ResearchError):
                validate_exclusive_fixture(mutated)

    def test_public_source_enters_existing_feed_with_no_claimed_invoice_error(self):
        validate_exclusive_fixture(exclusive_fixture())
        ledger = ledger_from([source_record(EXCLUSIVE_URL, "freightrecovery", "2026-10-24")])
        evidence, candidates, manifest = legacy_evidence(), legacy_candidates(), load_manifest()
        feed = build_feed(ledger, evidence, candidates, manifest)
        row = feed["candidate_sources"][0]
        self.assertEqual(feed["source_pointers_total"], 1)
        self.assertEqual(row["source_url"], EXCLUSIVE_URL)
        self.assertIsNone(row["case_id"])
        self.assertFalse(row["commercial_reuse_authorized"])
        self.assertFalse(row["independent_ground_truth"])
        self.assertFalse(row["independent_payment_verified"])
        self.assertFalse(row["source_document_ingested"])
        self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        validate_feed(feed, ledger, evidence, candidates, manifest)


if __name__ == "__main__":
    unittest.main()
