"""First-party NYC boiler filing metadata; no independent enforcement truth."""
import hashlib
import json
import unittest
from pathlib import Path

PATH = Path(__file__).parent / "fixtures" / "nyc_dob_safety_boiler_filing_boundary_v1.json"
COLUMNS = {"report_type","report_status","pressure_type","inspection_date","defects_exist"}
FORBIDDEN = ("tracking_number","boiler_id","bin_number","owner_first_name",
             "owner_last_name","applicantfirst_name","applicant_last_name",
             "applicant_license_number","house_number","street_name","email","phone")


def assess(row, claim):
    if claim == "publisher_defects_flag":
        answer = row.get("defects_exist")
        return {"Yes": "SOURCE_REPORTS_DEFECTS",
                "No": "SOURCE_REPORTS_NO_DEFECTS"}.get(answer, "UNKNOWN_MISSING_DEFECT_FLAG")
    return {
        "defects_remediated": "UNKNOWN_NO_VERIFIED_REMEDIATION",
        "independent_no_violation": "UNKNOWN_NO_INDEPENDENT_NEGATIVE",
        "independent_penalty_or_violation": "UNKNOWN_NO_INDEPENDENT_ADJUDICATION",
        "payment_completed": "UNKNOWN_NO_PAYMENT_SOURCE",
        "historical_publication_asof": "UNKNOWN_NO_HISTORICAL_SOURCE_SNAPSHOT",
        "same_device_filing": "UNKNOWN_NO_RETAINED_IDENTIFIERS",
        "complete_high_pressure_inspection": "UNKNOWN_OTHER_INSPECTION_NOT_VERIFIED",
    }.get(claim, "UNKNOWN_UNSUPPORTED_CLAIM")


class SafetyBoilerScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PATH.read_text(encoding="utf-8"))

    def test_source_rights_publisher_and_scope(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["source"]["dataset_id"], "52dp-yji6")
        self.assertEqual(p["source"]["publisher_last_updated_observed"], "2026-10-22")
        self.assertEqual(p["source"]["catalog_created_date"], "2017-09-14")
        self.assertEqual(p["source"]["publisher_catalog_column_count"], 21)
        self.assertFalse(p["rights"]["permitplate_customer_scoring_authorized"])
        self.assertFalse(p["ownership"]["legacy_lab_consolidation_proven"])
        self.assertFalse(p["provenance"]["raw_original_source_custodied"])
        self.assertIsNone(p["provenance"]["raw_http_body_sha256"])
        self.assertIsNone(p["provenance"]["historical_publication_asof_date"])

    def test_projection_hash_and_no_identifiers(self):
        p = self.pack
        rows = p["observations"]["rows"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(set(r) == COLUMNS for r in rows))
        projection = json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        self.assertEqual(hashlib.sha256(projection).hexdigest(),
                         p["provenance"]["sanitized_projection_sha256"])
        for row in rows:
            self.assertFalse(set(row).intersection(FORBIDDEN))
        self.assertEqual(p["observations"]["calibration_indices"], [0,1,2,3])
        self.assertEqual(p["observations"]["nonblind_same_publisher_holdout_indices"], [4,5,6,7])
        self.assertEqual(p["observations"]["independent_real_heldout_cases"], 0)

    def test_real_source_reporting_not_adjudication(self):
        p = self.pack
        rows = p["observations"]["rows"]
        self.assertEqual(sum(r["defects_exist"] == "Yes" for r in rows), 2)
        self.assertEqual(sum(r["defects_exist"] == "No" for r in rows), 6)
        self.assertTrue(all(r["report_status"] == "Accepted" for r in rows))
        self.assertEqual(sum(r["report_type"] == "Subsequent" for r in rows), 1)
        self.assertEqual(assess(rows[6],"publisher_defects_flag"),"SOURCE_REPORTS_DEFECTS")
        self.assertEqual(assess(rows[0],"publisher_defects_flag"),"SOURCE_REPORTS_NO_DEFECTS")
        for field in ("independent_final_violation_labels",
                      "independent_repair_confirmation_labels",
                      "independent_nonviolation_labels",
                      "verified_customer_leads","penalty_or_fee_payment_evidence"):
            self.assertEqual(p["observations"][field], 0)

    def test_all_adversarial_controls_fail_closed(self):
        p = self.pack
        self.assertEqual(len(p["synthetic_controls"]), 9)
        seen = set()
        for control in p["synthetic_controls"]:
            self.assertNotIn(control["id"], seen)
            seen.add(control["id"])
            self.assertEqual(control["provenance"],"RESEARCH_AUTHORED_SYNTHETIC")
            row = dict(p["observations"]["rows"][control["base_observation_index"]])
            for key in control.get("remove_field", "").split():
                row.pop(key,None)
            row.update(control.get("override_fields",{}))
            self.assertEqual(assess(row,control["claim"]),control["expected"],control["id"])
        self.assertEqual(assess({}, "publisher_defects_flag"),"UNKNOWN_MISSING_DEFECT_FLAG")

    def test_mutated_source_projection_is_detectably_red(self):
        rows = self.pack["observations"]["rows"]
        altered = [dict(x) for x in rows]
        altered[6]["defects_exist"] = "No"
        digest = hashlib.sha256(json.dumps(altered,sort_keys=True,separators=(",",":"),
                                           ensure_ascii=False).encode("utf-8")).hexdigest()
        self.assertNotEqual(digest,self.pack["provenance"]["sanitized_projection_sha256"])
        self.assertEqual(self.pack["restrictions"]["new_scheduled_provider_calls"],0)


if __name__ == "__main__":
    unittest.main()
