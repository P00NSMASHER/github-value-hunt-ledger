"""Historical first-party GAO tender-authenticity dispute: source-evidence guards only."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b225507_tender_chain_v1.json"


def historic_evidence_guard(claim, facts):
    """A research safety predicate, not FreightRecovery product code or legal advice."""
    if claim == "MTMC_STAMPS_PROVE_SIGNATORY_AUTHENTIC":
        return "REJECT_UNVERIFIED_SIGNATURE"
    if claim == "FIVE_CARRIER_AFFIDAVITS_PROVE_FORGED_TENDER":
        return "REJECT_UNADJUDICATED_FRAUD"
    if claim == "CARRIER_COST_ALONE_PROVES_TENDER_NOT_ISSUED":
        return "REJECT_COST_INFERENCE"
    if claim == "GSA_DEDUCTION_PROVES_RETALLY_CUSTOMER_RECOVERY":
        return "UNKNOWN_NO_CUSTOMER_CASH"
    if claim == "EACH_GBL_IS_INDEPENDENT_ADJUDICATED_LABEL":
        return "REJECT_CORRELATED_LABELS"
    if claim == "HISTORICAL_TENDER_IS_MODERN_RATE_AUTHORITY":
        return "UNKNOWN_MODERN_RATE_AUTHORITY"
    if claim != "HISTORICAL_GAO_DEDUCTION_SUPPORT":
        return "UNKNOWN_UNRECOGNIZED_CLAIM"
    if facts.get("official_file_tender_present") is not True:
        return "UNKNOWN_OFFICIAL_TENDER_FILE"
    if facts.get("gbl_tender_notice") is not True:
        return "UNKNOWN_GBL_NOTICE"
    if facts.get("tender_effective_on_shipment") is False:
        return "REJECT_INEFFECTIVE_TENDER_NOT_GAO_CASE"
    if facts.get("tender_effective_on_shipment") is not True:
        return "UNKNOWN_TENDER_EFFECTIVITY"
    if facts.get("timely_carrier_inquiry_before_notices") is True:
        return "UNKNOWN_DIFFERENT_FACT_PATTERN"
    if facts.get("timely_carrier_inquiry_before_notices") is not False:
        return "UNKNOWN_TIMING"
    return "SUPPORTED_IN_HISTORICAL_GAO_B225507_ONLY"


class GAOB225507TenderSourceQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_source_rights_and_original_byte_hash_remain_explicitly_unknown(self):
        p, s = self.pack, self.pack["original_source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["checked_on_utc"], "2026-10-31")
        self.assertEqual(s["publisher"], "U.S. Government Accountability Office")
        self.assertEqual(s["decision_id"], "B-225507")
        self.assertEqual(s["decision_date"], "1987-09-23")
        self.assertEqual(s["official_html_url"], "https://www.gao.gov/products/b-225507-0")
        self.assertEqual(p["rights"]["terms_url"], "https://www.gao.gov/copyright")
        self.assertFalse(p["rights"]["commercial_score_authorized"])
        self.assertEqual(p["rights"]["embedded_third_party_original_tender_rights"],
                         "UNKNOWN_UNREVIEWED_NO_TENDER_COPY_REPUBLISHED")
        self.assertIsNone(s["original_http_body_sha256"])
        self.assertIsNone(s["original_http_body_byte_length"])
        self.assertFalse(s["raw_http_bytes_custodied"])
        self.assertFalse(s["original_gbl_invoice_tender_scan_bytes_custodied"])

    def test_official_historical_chain_and_no_signature_authentication_claim(self):
        e = self.pack["decision_reported_evidence"]
        self.assertEqual(e["tender_disputed"], "ICC 1003")
        self.assertEqual(e["purported_original_issue_date"], "1984-11-06")
        self.assertEqual(e["handwritten_issue_and_effective_date"], "1985-01-06")
        self.assertEqual(e["purported_expiry_date"], "1986-12-06")
        self.assertEqual(e["mtmc_first_received_stamp"], "1984-11-29")
        self.assertEqual(e["mtmc_second_received_stamp"], "1985-01-07")
        self.assertEqual(e["mtmc_second_administrative_review"], "1985-01-09")
        self.assertEqual(e["mtmc_distribution_stamp"], "1985-01-09")
        self.assertEqual(e["sample_gbl_shipment_date"], "1986-05-15")
        self.assertEqual(e["company_official_affidavits_count"], 5)
        self.assertFalse(e["carrier_issuing_officer_signature_authenticity_verified_by_mtmc"])
        self.assertTrue(e["gsa_recovered_overcharge_deductions_as_reported"])
        self.assertEqual(e["official_outcome"], "GAO_SUSTAINED_GSA_AUDIT_ACTION")
        for absent in ("gsa_total_deduction_cents", "individual_invoice_charge_cents",
                       "independent_bank_settlement_receipt_cents"):
            self.assertIsNone(e[absent])
        self.assertEqual(e["actual_retally_customer_cash_cents"], 0)

    def test_12_synthetic_negative_controls_hold_unknowns_without_promoting_labels(self):
        controls = self.pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 12)
        self.assertEqual(len({x["id"] for x in controls}), 12)
        for x in controls:
            with self.subTest(id=x["id"]):
                self.assertTrue(x["id"].startswith("SYN_"))
                self.assertEqual(x["kind"], "SYNTHETIC_RESEARCH_AUTHORED_NOT_A_REAL_SHIPMENT")
                self.assertEqual(x["split"], "synthetic_holdout")
                self.assertIsNone(x["independent_real_label"])
                self.assertEqual(historic_evidence_guard(x["claim"], x["facts"]), x["expected"])

    def test_provenance_red_green_mutation_probe(self):
        b = self.pack["reported_historical_baseline"]
        self.assertEqual(historic_evidence_guard(b["claim"], b["facts"]),
                         "SUPPORTED_IN_HISTORICAL_GAO_B225507_ONLY")
        for field, replacement in (
            ("official_file_tender_present", None),
            ("gbl_tender_notice", False),
            ("tender_effective_on_shipment", None),
            ("timely_carrier_inquiry_before_notices", True),
        ):
            with self.subTest(mutation=field):
                changed = deepcopy(b["facts"])
                changed[field] = replacement
                self.assertNotEqual(historic_evidence_guard(b["claim"], changed),
                                    "SUPPORTED_IN_HISTORICAL_GAO_B225507_ONLY")

    def test_one_source_cluster_not_aggregate_shipment_benchmark(self):
        labels = self.pack["original_outcome_labels"]
        b = self.pack["benchmark_readiness"]
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["source_key"], "GAO/B-225507")
        self.assertEqual(labels[0]["split"], "research_selected_after_decision_publication")
        self.assertFalse(labels[0]["modern_freight_error_label"])
        self.assertEqual(b["contrast_key"], "GAO/B-203929.2")
        self.assertEqual(b["selected_source_decision_clusters"], 2)
        self.assertEqual(b["product_engine_predictions"], 0)
        self.assertEqual(b["modern_independently_labeled_invoice_triplets"], 0)
        self.assertEqual(b["independent_real_customer_holdout"], 0)
        self.assertIsNone(b["modern_precision"])
        self.assertIsNone(b["modern_recall"])
        self.assertTrue(b["simulated_controls_not_counted_as_accuracy"])

    def test_ownership_handoffs_and_release_boundaries(self):
        p, r = self.pack, self.pack["restrictions"]
        self.assertEqual(p["ownership"]["canonical_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(p["ownership"]["existing_draft_pr"], 883)
        self.assertFalse(p["ownership"]["writer_modified"])
        for name in ("freightrecovery_12", "recoveryos_12", "permitplate_48",
                     "capturebrief_52", "independent_qa_44"):
            self.assertTrue(p["handoffs"][name])
        self.assertFalse(r["private_customer_data_persisted"])
        self.assertFalse(r["product_code_changed"])
        self.assertFalse(r["writer_branch_modified"])
        self.assertFalse(r["legacy_15_lab_consolidation_certified"])
        self.assertFalse(r["release_authorized"])
        self.assertEqual(r["new_paid_provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
