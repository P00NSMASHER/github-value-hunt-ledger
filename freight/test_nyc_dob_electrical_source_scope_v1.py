"""Research-only coverage and provenance checks for official NYC electrical filings.

No external requests, person-level data, permit lookups, or source bytes.
"""
import json
from pathlib import Path
import unittest

PATH = Path(__file__).parent / "fixtures" / "nyc_dob_electrical_application_boundary_v1.json"


def classify(case):
    facts = case["facts"]
    claim = case["untrusted_claim"]
    if claim == "NO_ELECTRICAL_PERMIT_FROM_BUILD_NONMATCH":
        return ("UNKNOWN_OUT_OF_SCOPE_NOT_ABSENT"
                if facts["catalog_id"] == "rbx6-tga4"
                and facts["catalog_match"] is False
                and facts["work_type"] == "ELECTRICAL"
                else "UNKNOWN_INSUFFICIENT_EVIDENCE")
    if claim == "ISSUED_PERMIT_FROM_EL_IDENTIFIER":
        return ("UNKNOWN_SUFFIX_NOT_ISSUANCE"
                if facts["job_filing_number"].endswith("-EL")
                and facts["filing_status"] != "Permit Issued"
                else "UNKNOWN_INSUFFICIENT_EVIDENCE")
    if claim == "TWO_DISTINCT_PERMITS_FROM_TWO_FILINGS":
        return ("UNKNOWN_MULTIFILING_NOT_PERMIT_COUNT"
                if len(facts["job_filing_numbers"]) == 2
                and len(set(facts["job_numbers"])) == 1
                else "UNKNOWN_INSUFFICIENT_EVIDENCE")
    if claim == "ISSUED_ON_HISTORIC_DATE_FROM_CURRENT_STATUS":
        return ("UNKNOWN_NO_ASOF_VERSION_HISTORY"
                if facts["claimed_historic_date"] < facts["metadata_last_updated"]
                and not facts["historical_source_snapshot_exists"]
                else "UNKNOWN_INSUFFICIENT_EVIDENCE")
    raise AssertionError("Unknown untrusted claim must fail closed")


class ElectricalOriginalSourceScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_original_source_and_rights_scope_are_explicit(self):
        x = self.doc
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["evaluation_family"], "GOVERNMENT_PERMIT_SOURCE_SCOPE_NOT_SCORING")
        s = x["original_public_source"]
        self.assertEqual(s["dataset_id"], "dm9a-ab7w")
        self.assertEqual(s["catalog_kind"], "OFFICIAL_ORIGINAL_DATASET")
        self.assertEqual(s["event_type"], "ELECTRICAL_PERMIT_APPLICATION_LIFECYCLE")
        self.assertEqual(s["documented_api_field_names"],
                         ["job_filing_number", "job_number", "filing_number",
                          "filing_date", "filing_type", "filing_status", "job_status"])
        self.assertIsNone(s["original_response_sha256"])
        self.assertEqual(s["original_rows_read_into_pack"], 0)
        self.assertIsNone(s["original_response_content_length"])
        self.assertEqual(x["source_data_labels"]["real_issued_permit_holdout"], 0)
        self.assertEqual(x["source_data_labels"]["independently_adjudicated_permit_outcomes"], 0)
        self.assertFalse(x["rights"]["permitplate_commercial_product_clearance"])
        self.assertEqual(x["rights"]["dataset_specific_license"], "UNSPECIFIED_REQUIRES_CHECK")
        self.assertTrue(x["rights"]["nyc_general_open_data_use_unrestricted_faq"])
        self.assertTrue(x["rights"]["portal_and_provider_additional_terms_apply"])

    def test_derived_view_cannot_count_as_an_original_dob_dataset(self):
        x = self.doc
        self.assertEqual(x["derived_community_view"]["dataset_id"], "vh4j-4npc")
        self.assertEqual(x["derived_community_view"]["parent_dataset_id"], "dm9a-ab7w")
        self.assertFalse(x["derived_community_view"]["city_endorsed"])
        self.assertEqual(x["derived_community_view"]["source_role"],
                         "DO_NOT_USE_AS_ORIGINAL_GROUND_TRUTH")
        self.assertNotEqual(x["original_public_source"]["dataset_id"],
                            x["derived_community_view"]["dataset_id"])

    def test_four_held_out_synthetic_negative_controls_remain_unknown(self):
        controls = self.doc["synthetic_negative_controls"]
        expected = {
            "electrical_excluded_build_nonmatch": "UNKNOWN_OUT_OF_SCOPE_NOT_ABSENT",
            "el_suffix_pending_payment": "UNKNOWN_SUFFIX_NOT_ISSUANCE",
            "job_filing_multiplicity": "UNKNOWN_MULTIFILING_NOT_PERMIT_COUNT",
            "current_status_historic_lookahead": "UNKNOWN_NO_ASOF_VERSION_HISTORY",
        }
        self.assertEqual(len(controls), 4)
        self.assertEqual({c["id"]: c["expected"] for c in controls}, expected)
        self.assertEqual({c["id"]: classify(c) for c in controls}, expected)
        self.assertTrue(all(c["provenance"] == "SYNTHETIC_NOT_REAL_PERMIT"
                            and c["independent_real_world_label"] is None
                            for c in controls))
        self.assertFalse(self.doc["source_data_labels"]["real_scoring_allowed"])
        self.assertEqual(self.doc["source_data_labels"]["accuracy"], "UNKNOWN_NO_REAL_HELD_OUT_LABELS")
        self.assertEqual(self.doc["source_data_labels"]["synthetic_control_count"], 4)
        self.assertEqual(self.doc["source_data_labels"]["cross_source_verified_issuance_labels"], 0)


class ElectricalDetailsFanoutResearchTest(unittest.TestCase):
    """Metadata-only publisher join boundary, not a production adapter or real benchmark."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(
            (PATH.parent / "nyc_dob_electrical_details_fanout_v1.json")
            .read_text(encoding="utf-8")
        )
        cls.controls = {c["id"]: c for c in cls.pack["synthetic_controls"]}

    def test_original_dob_detail_source_and_schema_have_no_fabricated_bytes(self):
        p = self.pack
        s = p["source"]
        self.assertEqual(s["dataset_id"], "xmmq-y7za")
        self.assertEqual(s["catalog_last_updated_reported"], "2026-10-20")
        self.assertEqual(s["original_schema_metadata_url"],
                         "https://data.cityofnewyork.us/api/views/xmmq-y7za/columns.json")
        self.assertEqual(s["documented_public_api_fields"],
                         ["unique_id", "work_id", "floor_id", "sign_id",
                          "job_filing_number", "work_description", "item"])
        self.assertTrue(s["publisher_describes_multiple_rows_per_job_filing"])
        self.assertEqual(s["original_source_rows_custodied"], 0)
        self.assertIsNone(s["original_http_response_bytes_sha256"])
        self.assertIsNone(s["original_schema_response_bytes_sha256"])
        self.assertIsNone(s["original_content_length_bytes"])

    def test_synthetic_naive_row_count_red_and_filing_dedup_green(self):
        c = self.controls["SYNTHETIC_DETAIL_FANOUT_3_TO_1"]
        rows = c["synthetic_detail_rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({x["unique_id"] for x in rows}), 3)
        self.assertEqual(len({x["job_filing_number"] for x in rows}), 1)
        self.assertEqual(len({x["work_id"] for x in rows}), 2)
        self.assertEqual(c["naive_detail_row_count"], len(rows))
        self.assertEqual(c["deduped_filing_group_count"], 1)
        self.assertEqual(c["deduped_work_scope_count"], 2)
        self.assertNotEqual(c["naive_detail_row_count"],
                            c["deduped_filing_group_count"])
        self.assertEqual(c["expected"], "UNKNOWN_ONE_FILING_NOT_THREE_ISSUED_PERMITS")
        self.assertIsNone(c["independently_verified_real_label"])

    def test_synthetic_holdouts_block_join_miss_and_filing_multiplicity(self):
        self.assertEqual(
            {x["id"] for x in self.pack["synthetic_controls"]
             if x["split"] == "synthetic_holdout"},
            {"SYNTHETIC_DETAILS_WITHOUT_APPLICATION_JOIN",
             "SYNTHETIC_TWO_FILINGS_ONE_JOB"}
        )
        missing = self.controls["SYNTHETIC_DETAILS_WITHOUT_APPLICATION_JOIN"]
        self.assertFalse(missing["synthetic_facts"]["application_join_found"])
        self.assertEqual(missing["expected"],
                         "UNKNOWN_JOIN_MISS_NOT_NEGATIVE_ISSUANCE_LABEL")
        multiple = self.controls["SYNTHETIC_TWO_FILINGS_ONE_JOB"]
        self.assertEqual(len(multiple["synthetic_facts"]["synthetic_filing_numbers"]), 2)
        self.assertEqual(multiple["expected"],
                         "UNKNOWN_FILING_MULTIPLICITY_NOT_PERMIT_COUNT")
        self.assertEqual(self.controls[
            "SYNTHETIC_EL_SUFFIX_WITHOUT_AWARD_TRUTH"]["expected"],
            "UNKNOWN_NO_HISTORIC_ASOF_OR_INDEPENDENT_ISSUANCE")

    def test_rights_scoring_dedup_and_noncustomer_limits_hold(self):
        p = self.pack
        self.assertEqual(p["join_contract"]["shared_field"], "job_filing_number")
        self.assertEqual(p["join_contract"]["expected_cardinality"],
                         "ONE_FILING_TO_MANY_SCOPE_DETAIL_ROWS")
        self.assertEqual(p["quality"]["dedup_key"], "dataset_id/unique_id_FOR_DETAILS_ONLY")
        self.assertEqual(p["quality"]["synthetic_heldout_cases"], 2)
        self.assertEqual(p["quality"]["real_heldout_cases"], 0)
        self.assertIsNone(p["quality"]["independent_scoring_accuracy"])
        self.assertEqual(p["rights"]["dataset_specific_license"], "UNVERIFIED")
        self.assertFalse(p["rights"]["permitplate_commercial_scoring_cleared"])
        self.assertTrue(p["rights"]["city_open_data_faq_describes_unrestricted_general_use"])
        self.assertTrue(all(c["provenance"] == "SYNTHETIC_NO_REAL_PUBLISHER_RECORD"
                            and c["independently_verified_real_label"] is None
                            for c in p["synthetic_controls"]))
        self.assertFalse(p["product_code_modified"])
        self.assertEqual(p["provider_gets_added_to_ci"], 0)
        self.assertFalse(p["legacy_15_lab_consolidation_certified"])


if __name__ == "__main__":
    unittest.main()
