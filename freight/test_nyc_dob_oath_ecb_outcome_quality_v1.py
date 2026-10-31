"""Original NYC OATH/DOB publisher metadata, safety-only synthetic controls."""
import hashlib
import json
import unittest
from pathlib import Path

FILE = Path(__file__).parent / "fixtures" / "nyc_dob_oath_ecb_outcome_quality_v1.json"

def guard(claim, facts):
    if claim == "BIN_ALONE_UNIQUELY_IDENTIFIES_SAFETY_NOTICE":
        return "REJECT" if facts.get("same_bin") and facts.get("distinct_violation_numbers") else "UNKNOWN"
    if claim == "MISSING_VIOLATION_NUMBER_IS_VERIFIED_DISTINCT_EVENT":
        return "UNKNOWN"
    if claim == "HEARING_STATUS_PROVES_FINAL_ADJUDICATION":
        return "UNKNOWN"
    if claim == "DISMISSED_REQUIRES_POSITIVE_PENALTY":
        return "REJECT" if str(facts.get("hearing_result", "")).upper() == "DISMISSED" else "UNKNOWN"
    if claim == "PENALTY_ASSESSMENT_IS_CLEARED_CASH":
        return "REJECT"
    if claim == "FUTURE_DATE_IS_VALID_HISTORICAL_CASE":
        try:
            return "REJECT" if int(facts["date"][:4]) > 2026 else "UNKNOWN"
        except (KeyError, ValueError, TypeError):
            return "UNKNOWN"
    if claim in ("UNREVIEWED_APPEAL_IS_FINAL_OUTCOME", "OFFICIAL_PAID_FIELD_IS_CUSTOMER_RECOVERY",
                 "CROSS_DATASET_JOIN_PROVES_SAME_CASE", "ZERO_BALANCE_PROVES_BANK_SETTLEMENT",
                 "NO_OATH_RECORD_MEANS_NO_PERMIT"):
        return "UNKNOWN"
    if claim == "UNVERIFIED_SAFETY_LEGACY_PAIR_IS_DISTINCT_EVENTS":
        return "UNKNOWN"
    if claim == "SAFETY_CIVIL_VIOLATION_IS_OATH_ADJUDICATION":
        return "REJECT" if facts.get("dataset_id") == "855j-jady" else "UNKNOWN"
    if claim == "DOB_ISSUED_CIVIL_PENALTY_IS_CUSTOMER_RECOVERY":
        return "REJECT"
    if claim == "ABSENT_SAFETY_ROW_PROVES_COMPLIANT_PERMIT":
        return "UNKNOWN"
    if claim == "REMOVED_PII_FIELDS_ARE_STILL_AUTHORIZED":
        return "REJECT"
    if claim == "CASE_VARIANTS_ARE_DIFFERENT_OUTCOMES":
        return ("REJECT" if str(facts.get("a", "")).casefold() ==
                str(facts.get("b", "")).casefold() else "UNKNOWN")
    return "UNKNOWN"

class OathOutcomeSourceQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(FILE.read_text(encoding="utf-8"))

    def test_official_three_source_provenance_and_version(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["observed_date_utc"], "2026-10-31")
        self.assertEqual({x["dataset_id"] for x in p["sources"]}, {"jz4z-kudi", "6bgk-3dad", "855j-jady"})
        self.assertEqual(p["sources"][0]["record_schema_fields_verified"],
                         ["issuing_agency", "violation_date", "hearing_status",
                          "hearing_result", "decision_date", "penalty_imposed",
                          "paid_amount", "balance_due"])
        for src in p["sources"]:
            self.assertTrue(src["landing_page"].startswith("https://data.cityofnewyork.us/d/"))
            self.assertIsNone(src["original_json_bytes_sha256"])
            self.assertEqual(src["original_case_rows_custodied"], 0)
            self.assertFalse(src["commercial_scoring_authorized"])

    def test_original_publisher_schema_quality_anomalies_are_not_rows(self):
        findings = self.pack["metadata_quality_findings"]
        self.assertEqual({x["field"] for x in findings},
                         {"violation_date", "decision_date", "hearing_result", "hearing_status"})
        self.assertTrue(all(x["field"] not in ("respondent_last_name", "ticket_number")
                            for x in findings))
        self.assertEqual(findings[0]["source_metadata_largest"][:4], "5201")
        self.assertEqual(findings[1]["source_metadata_largest"][:4], "9997")

    def test_synthetic_calibration_holdouts_and_negative_controls(self):
        cases = self.pack["synthetic_controls"]
        self.assertEqual(len(cases), 18)
        self.assertEqual([x["split"] for x in cases].count("calibration"), 4)
        self.assertEqual([x["split"] for x in cases].count("synthetic_holdout"), 14)
        self.assertEqual(len({x["id"] for x in cases}), len(cases))
        for case in cases:
            self.assertTrue(case["id"].startswith("SYNTH_"))
            self.assertEqual(case["kind"], "SYNTHETIC_NOT_ORIGINAL_CASE")
            self.assertIsNone(case["independent_real_label"])
            self.assertEqual(guard(case["claim"], case["facts"]), case["expected_guard"])

    def test_no_real_benchmark_or_customer_cash_leakage(self):
        labels = self.pack["source_labeling"]
        for key in ("real_case_rows_examined", "real_joined_dob_oath_pairs",
                    "real_independent_adjudication_labels", "real_independent_negative_labels",
                    "independent_customer_cash_events", "heldout_real_cases"):
            self.assertEqual(labels[key], 0)
        self.assertIsNone(labels["benchmark_accuracy"])
        self.assertIsNone(labels["benchmark_recall"])
        self.assertFalse(any(self.pack["privacy"].values()))
        self.assertNotIn("CONFIRMED_", self.pack["benchmark_readiness"])
        self.assertEqual(self.pack["sources"][0]["privacy_change_effective"], "2026-05-04")

    def test_safety_original_publisher_catalog_crosswalk_and_no_inferred_labels(self):
        source = next(x for x in self.pack["sources"] if x["dataset_id"] == "855j-jady")
        self.assertEqual(source["record_schema_fields_verified"],
                         ["bin", "violation_issue_date", "violation_number", "violation_type"])
        self.assertEqual(source["first_published"], "2023-11-22")
        self.assertEqual(source["publisher_page_last_updated_observed"], "2026-10-23")
        self.assertEqual(source["original_case_rows_custodied"], 0)
        self.assertIsNone(source["original_json_bytes_sha256"])
        self.assertFalse(source["commercial_scoring_authorized"])
        self.assertEqual(len(self.pack["source_crosswalk_constraints"]), 4)
        pairs = {x["id"]: x for x in self.pack["source_crosswalk_constraints"]}
        self.assertEqual(pairs["SAFETY_LEGACY_OVERLAP"]["dedup_truth"],
                         "UNKNOWN_NO_ROW_IDENTITY_VERIFIED")
        self.assertEqual(pairs["SAFETY_ECB_SEPARATION"]["independent_case_join_count"], 0)
        self.assertEqual(pairs["MUTABLE_ASOF_COHORT"]["historical_asof_snapshot"], "UNKNOWN")
        self.assertEqual(pairs["ISSUANCE_NOT_RECOVERY"]["independent_cash_label_count"], 0)

    def test_safety_synthetic_holdout_is_distinct_from_real_ground_truth(self):
        controls = [x for x in self.pack["synthetic_controls"]
                    if x["id"].startswith("SYNTH_SAFETY_")]
        self.assertEqual(len(controls), 4)
        self.assertEqual([c["expected_guard"] for c in controls],
                         ["UNKNOWN", "REJECT", "REJECT", "UNKNOWN"])
        self.assertTrue(all(c["split"] == "synthetic_holdout"
                            and c["independent_real_label"] is None for c in controls))
        self.assertEqual(self.pack["source_labeling"]["real_joined_dob_oath_pairs"], 0)
        self.assertEqual(self.pack["source_labeling"]["heldout_real_cases"], 0)
        self.assertIsNone(self.pack["source_labeling"]["benchmark_accuracy"])

    def test_no_source_outcome_promotion(self):
        handoff = self.pack["downstream_handoffs"]
        self.assertEqual(set(handoff),
                         {"permitplate", "capturebrief", "freightrecovery", "recoveryos", "qa"})
        self.assertTrue(all("NO_" in handoff[x] for x in
                            ("capturebrief", "freightrecovery", "recoveryos")))


    def test_original_safety_pair_deidentified_projection_hash_and_custody_limit(self):
        source = self.pack["original_public_api_observations"]
        self.assertEqual(len(source), 1)
        obs = source[0]
        p = obs["deidentified_projection"]
        self.assertEqual(obs["kind"], "ORIGINAL_PUBLISHER_API_ROW_PROJECTION_DEIDENTIFIED_NOT_GROUND_TRUTH")
        self.assertEqual(obs["source_url"], "https://data.cityofnewyork.us/resource/855j-jady.json")
        self.assertEqual(obs["source_page_positions_zero_based"], [15, 19])
        self.assertEqual(p["source_issue_date"], "2026-10-21")
        self.assertEqual(p["records_observed"], 2)
        self.assertTrue(p["same_bin"])
        self.assertTrue(p["distinct_violation_numbers"])
        digest = hashlib.sha256(json.dumps(
            p, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        self.assertEqual(digest, "820e568269352baba054f51f2fcd38504d3f1749d384a589906362c75b398563")
        self.assertEqual(obs["deidentified_projection_sha256"], digest)
        self.assertIsNone(obs["source_response_original_http_sha256"])
        self.assertFalse(obs["source_response_complete"])
        self.assertFalse(obs["original_raw_ids_addresses_or_coordinates_persisted"])
        self.assertEqual(self.pack["source_labeling"]["original_safety_rows_projected_nonadjudicated"], 2)
        self.assertEqual(self.pack["source_labeling"]["heldout_real_cases"], 0)

    def test_source_pair_bin_dedup_red_green_and_missing_label_guard(self):
        obs = self.pack["original_public_api_observations"][0]
        p = obs["deidentified_projection"]
        # RED baseline loses one distinct publisher *notice row* by BIN-only dedup.
        self.assertEqual(obs["naive_bin_only_unique_count"], 1)
        # GREEN source-record keying preserves two distinct publisher notice IDs.
        self.assertEqual(obs["distinct_publisher_notice_ids_observed"], 2)
        self.assertEqual(p["records_observed"], 2)
        self.assertLess(obs["naive_bin_only_unique_count"], obs["distinct_publisher_notice_ids_observed"])
        self.assertIsNone(obs["independently_validated_distinct_incidents"])
        self.assertIsNone(obs["independent_adjudicated_case_label"])
        self.assertIsNone(obs["independent_cash_label"])
        self.assertFalse(obs["commercial_scoring_approved"])
        extra = [x for x in self.pack["synthetic_controls"] if
                 x["id"] in {"SYNTH_BIN_ONLY_UNIQUE_NOTICE", "SYNTH_MISSING_VIOLATION_NUMBER"}]
        self.assertEqual(len(extra), 2)
        self.assertEqual([guard(x["claim"], x["facts"]) for x in extra], ["REJECT", "UNKNOWN"])
        self.assertTrue(all(x["independent_real_label"] is None and
                            x["split"] == "synthetic_holdout" for x in extra))

if __name__ == "__main__":
    unittest.main()
