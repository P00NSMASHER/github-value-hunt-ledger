"""Source-bound historical GAO freight safeguards. No network access or product engine behavior."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import unittest

PACK = Path(__file__).parent / "fixtures" / "gao_b192872_class_weight_ambiguity_v1.json"


def guard(control: dict) -> str:
    """Synthetic expected-result classifier; NOT a FreightRecovery prediction."""
    f = control["facts"]
    kind = control["kind"]
    if kind == "bol_conflict":
        return ("REJECT_GBL_CONFLICT_NEEDS_PHYSICAL_EVIDENCE"
                if f["written_description"] == "SU"
                and f["item_subnumber"] == 2
                and f["independent_physical_evidence"] == "LOWERED_BANDED"
                else "UNKNOWN_NEEDS_PHYSICAL_EVIDENCE")
    if kind == "cubage":
        return ("REJECT_KD_BULK_REDUCTION_EXCEEDS_THRESHOLD"
                if f["expanded_ft3"] > 0
                and (f["expanded_ft3"] - f["collapsed_ft3"]) / f["expanded_ft3"]
                    >= f["threshold_fraction"]
                else "UNKNOWN_CUBAGE_PRECONDITION")
    if kind == "weight":
        return ("REJECT_BOL_WEIGHT_UNDERSTATED"
                if f["agency_evidence_lbs"] > f["bol_lbs"]
                else "UNKNOWN_WEIGHT_CONFLICT")
    if kind == "settlement":
        return ("UNKNOWN_FINAL_NET_AFTER_WEIGHT_ADJUSTMENT"
                if f["final_adjusted_settlement_cents"] is None
                else "UNKNOWN_SETTLEMENT_NEEDS_INDEPENDENT_RECONCILIATION")
    if kind == "dedup":
        return ("REJECT_CORRELATED_DUPLICATE"
                if f["platforms"] > 1
                and f["gao_decisions"] == f["bill_of_lading_clusters"] == 1
                else "UNKNOWN_CASE_IDENTITY")
    if kind == "temporal":
        return ("UNKNOWN_CURRENT_RATE"
                if f["shipment_year"] < 2026 and not f["modern_rate_in_custody"]
                else "UNKNOWN_TARIFF_EFFECTIVE_DATE")
    if kind == "cash":
        return ("UNKNOWN_BANK_CASH"
                if f["gsa_setoff_occurred"] and f["actual_customer_refund_receipt"] is None
                else "UNKNOWN_BANK_VERIFICATION")
    if kind == "benchmark":
        return ("REJECT_NO_BLIND_HELDOUT"
                if f["case_selected_after_outcome_known"] and f["blind_predictions"] == 0
                else "UNKNOWN_BENCHMARK_INDEPENDENCE")
    raise ValueError("Unexpected negative-control type: " + str(kind))


def validate_pack(d: dict) -> None:
    s = d["original_source"]
    r = d["rights"]
    p = d["source_fact_projection"]
    assert d["schema_version"] == 1
    assert s["decision_id"] == p["decision_id"] == "B-192872"
    assert s["decision_date"] == p["decision_date"] == "1979-05-07"
    assert s["source_pdf_url"] == "https://www.gao.gov/assets/b-192872.pdf"
    assert s["source_bytes_custodied"] is False
    assert s["source_http_body_sha256"] is None
    assert s["source_http_body_length"] is None
    assert "UNKNOWN" in s["source_content_hash_status"]
    assert r["commercial_accuracy_scoring_approved"] is False
    assert r["third_party_bol_tariff_material"] == "UNKNOWN_NOT_CLEARED"
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert sha256(canonical).hexdigest() == d["source_fact_projection_sha256"]
    assert p["original_gsa_deduction_cents"] == 50201
    assert p["class_if_set_up"] == 300 and p["class_if_knocked_down"] == 125
    assert p["setup_cubage_ft3"] == 440 and p["knocked_down_cubage_ft3"] == 154
    assert (440 - 154) / 440 >= 1/3
    assert p["bill_of_lading_reported_weight_lbs"] == 1700
    assert p["gsa_corrected_weight_lbs"] == 2200
    assert p["final_net_settlement_cents"] is None
    assert d["benchmark_readiness"]["real_cash_recovered_cents"] is None
    assert d["benchmark_readiness"]["real_blind_heldout_cases"] == 0
    assert d["benchmark_readiness"]["real_precision"] is None
    assert d["benchmark_readiness"]["independently_verified_invoice_tariff_payment_triplets"] == 0
    assert d["independent_comparison"]["distinct_docket"] is True
    assert d["independent_comparison"]["case"] == "GAO B-195862"
    assert d["benchmark_readiness"]["real_adjudication_clusters_added"] == 1
    assert len(d["adjudicated_ground_truth"]) == 4
    controls = d["synthetic_negative_controls"]
    assert len(controls) == 8
    assert len({c["id"] for c in controls}) == len(controls)
    assert sum(c["split"] == "synthetic_calibration" for c in controls) == 2
    assert sum(c["split"] == "synthetic_heldout" for c in controls) == 6
    for c in controls:
        assert c["independent_real_label"] is None
        assert c["provenance"] == "RESEARCH_AUTHORED_SYNTHETIC_NOT_AN_ORIGINAL_SOURCE_ROW"
        assert guard(c) == c["expected_guard"]
    assert d["restrictions"]["legacy_15_lab_consolidation_certified"] is False
    assert d["restrictions"]["writer_branch_modified"] is False
    assert d["restrictions"]["product_code_modified"] is False


class GAOB192872SourceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_publisher_provenance_rights_and_asof_scope(self):
        d = self.pack
        self.assertEqual(d["ownership"]["canonical_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(d["ownership"]["existing_draft_pr"], 883)
        self.assertEqual(d["historical_scope"]["shipment_month"], "1975-07")
        self.assertEqual(d["historical_scope"]["original_tariff_effective_date"], "UNKNOWN")
        self.assertEqual(d["historical_scope"]["present_day_tariff_relevance"], "NOT_ESTABLISHED")
        self.assertEqual(d["original_source"]["source_http_body_sha256"], None)
        self.assertFalse(d["rights"]["commercial_accuracy_scoring_approved"])

    def test_real_facts_and_projection_sha256(self):
        validate_pack(self.pack)

    def test_decision_page_evidence_not_two_independent_cases(self):
        labels = self.pack["adjudicated_ground_truth"]
        self.assertEqual({x["label_id"] for x in labels},
                         {"BOL_DESCRIPTION_CONFLICT", "CLASSIFICATION",
                          "WEIGHT_CORRECTION", "SETTLEMENT"})
        self.assertTrue(all(x["source_pages"] for x in labels))
        self.assertEqual(self.pack["benchmark_readiness"]["real_adjudication_clusters_added"], 1)

    def test_heldout_controls_are_synthetic_not_product_accuracy(self):
        c = self.pack["synthetic_negative_controls"]
        self.assertEqual(len(c), 8)
        self.assertEqual(sum(x["split"] == "synthetic_heldout" for x in c), 6)
        self.assertTrue(all(x["independent_real_label"] is None for x in c))
        self.assertIsNone(self.pack["benchmark_readiness"]["real_recall"])

    def test_tampered_weight_and_projection_hash_fail_closed(self):
        damaged = deepcopy(self.pack)
        damaged["source_fact_projection"]["gsa_corrected_weight_lbs"] = 1700
        with self.assertRaises(AssertionError):
            validate_pack(damaged)

    def test_synthetic_false_claim_flip_fails_closed(self):
        damaged = deepcopy(self.pack)
        damaged["synthetic_negative_controls"][3]["expected_guard"] = "FINAL_NET_OVERCHARGE_50201"
        with self.assertRaises(AssertionError):
            validate_pack(damaged)

    def test_downstream_ownership_without_engine_code_or_cash_claim(self):
        d = self.pack
        self.assertEqual(set(d["handoffs"]),
                         {"freightrecovery_12", "recoveryos_12", "permitplate_48",
                          "capturebrief_52", "independent_qa_44"})
        self.assertIsNone(d["benchmark_readiness"]["real_cash_recovered_cents"])
        self.assertEqual(d["restrictions"]["private_customer_student_medical_data_saved"], 0)
        self.assertEqual(d["restrictions"]["provider_calls_scheduled"], 0)


if __name__ == "__main__":
    unittest.main()
