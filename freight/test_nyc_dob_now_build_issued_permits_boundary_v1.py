"""Publisher-reported DOB NOW permits; reject inferred active permits and commercial leads."""
import hashlib
import json
import os
import unittest
from pathlib import Path

PACK_PATH = Path(os.environ.get("PACK_OVERRIDE", str(Path(__file__).parent / "fixtures" / "nyc_dob_now_build_issued_permits_boundary_v1.json")))
COLUMNS = {"filing_reason", "work_type", "permit_status", "approved_date", "issued_date", "expired_date", "work_permit_field", "estimated_job_costs_usd"}
FORBIDDEN = {"job_filing_number", "work_permit", "tracking_number", "owner_name", "owner_business_name", "applicant_first_name", "applicant_last_name", "applicant_license", "house_no", "street_name", "bin", "bbl", "latitude", "longitude", "job_description", "zip_code"}


def assess(row, claim):
    if claim == "publisher_approval_date":
        return row.get("approved_date") or "UNKNOWN_MISSING_DATE"
    if claim == "publisher_date_order":
        a, b = row.get("approved_date"), row.get("issued_date")
        if a is None or b is None:
            return "UNKNOWN_MISSING_DATE"
        return "SOURCE_DATE_ORDER_CONFLICT" if b < a else "PUBLISHER_DATE_ORDER_NONDECREASING"
    if claim == "currently_issued_permit":
        if row.get("permit_status") == "Signed-off" and row.get("work_permit_field") == "PUBLISHER_NOT_YET_ISSUED_PLACEHOLDER":
            return "UNKNOWN_CONFLICTING_PUBLISHER_FIELDS"
        return "UNKNOWN_NO_CURRENT_VALIDITY_CHECK"
    return {
        "new_work_authorized": "UNKNOWN_NO_INDEPENDENT_WORK_AUTHORIZATION",
        "fees_paid_or_no_fees": "UNKNOWN_NO_FEE_LEDGER",
        "verified_customer_opportunity": "UNKNOWN_NO_VERIFIED_LEAD",
        "no_work_occurred": "UNKNOWN_NO_WORK_OBSERVATION",
        "same_permit_as_another_row": "UNKNOWN_IDENTIFIERS_REDACTED",
    }.get(claim, "UNKNOWN_UNSUPPORTED_CLAIM")


class IssuedPermitEvidenceBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))

    def test_first_party_source_and_rights_scope(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["source"]["dataset_id"], "rbx6-tga4")
        self.assertEqual(p["source"]["publisher_last_updated_at_catalog_observed"], "2026-10-31")
        self.assertEqual(p["source"]["catalog_columns"], 46)
        self.assertEqual(p["source"]["coverage_excludes"], ["ELECTRICAL_PERMITS", "ELEVATOR_PERMITS", "LAA_PERMITS"])
        self.assertEqual(p["rights"]["faq_general_reuse"], "NO_GENERAL_USE_RESTRICTIONS")
        self.assertFalse(p["rights"]["commercial_customer_scoring_approved"])
        self.assertFalse(p["ownership"]["legacy_labs_consolidated"])
        self.assertFalse(p["provenance"]["raw_http_bytes_custodied"])
        self.assertIsNone(p["provenance"]["raw_http_body_sha256"])

    def test_sanitized_source_projection_and_digest(self):
        p = self.pack
        rows = p["observations"]["rows"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(set(row) == COLUMNS for row in rows))
        self.assertTrue(all(not set(row).intersection(FORBIDDEN) for row in rows))
        self.assertTrue(all(row["work_permit_field"] in {"PUBLISHER_NOT_YET_ISSUED_PLACEHOLDER", "FORMATTED_ID_REDACTED"} for row in rows))
        payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), p["provenance"]["projection_sha256"])
        self.assertEqual(p["observations"]["calibration_indices"], [0, 1, 2, 3])
        self.assertEqual(p["observations"]["nonblind_same_publisher_holdout_indices"], [4, 5, 6, 7])
        self.assertEqual(p["observations"]["independent_real_heldout_cases"], 0)
        self.assertFalse(p["provenance"]["deduplicate_projected_rows"])

    def test_real_excerpt_is_not_permit_validity_or_customer_outcome(self):
        p = self.pack
        rows = p["observations"]["rows"]
        counts = p["observations"]
        self.assertEqual(sum(bool(r["issued_date"]) for r in rows), 7)
        self.assertEqual(sum(r["permit_status"] == "Signed-off" for r in rows), 4)
        self.assertEqual(sum(r["permit_status"] == "Permit Issued" for r in rows), 4)
        self.assertEqual(sum(r["filing_reason"] == "Renewal Permit Without Changes" for r in rows), 3)
        self.assertEqual(sum(r["estimated_job_costs_usd"] == "0" for r in rows), 2)
        self.assertEqual(sum(r["work_permit_field"] == "PUBLISHER_NOT_YET_ISSUED_PLACEHOLDER" for r in rows), 1)
        self.assertEqual(counts["publisher_unissued_placeholder"], 1)
        self.assertEqual(assess(rows[0], "currently_issued_permit"), "UNKNOWN_CONFLICTING_PUBLISHER_FIELDS")
        for field in ("independently_verified_current_issued_permits", "independent_enforcement_or_compliance_labels", "verified_customer_leads", "cash_or_fee_settlements_verified"):
            self.assertEqual(counts[field], 0)

    def test_synthetic_adversarial_controls_fail_closed(self):
        controls = self.pack["synthetic_controls"]
        self.assertEqual(len(controls), 9)
        ids = set()
        for control in controls:
            self.assertNotIn(control["id"], ids)
            ids.add(control["id"])
            self.assertEqual(control["provenance"], "RESEARCH_AUTHORED_SYNTHETIC_NOT_REAL_CASE")
            row = dict(self.pack["observations"]["rows"][control["base_observation_index"]])
            row.update(control.get("override_fields", {}))
            self.assertEqual(assess(row, control["claim"]), control["expected"], control["id"])
        self.assertEqual(assess({}, "publisher_date_order"), "UNKNOWN_MISSING_DATE")
        self.assertEqual(assess({}, "currently_issued_permit"), "UNKNOWN_NO_CURRENT_VALIDITY_CHECK")

    def test_projection_tamper_detectable_and_no_production_changes(self):
        p = self.pack
        altered = [dict(row) for row in p["observations"]["rows"]]
        altered[0]["issued_date"] = "2026-10-01"
        raw = json.dumps(altered, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(), p["provenance"]["projection_sha256"])
        self.assertEqual(p["restrictions"]["provider_cost_increase"], 0)
        self.assertFalse(p["restrictions"]["scheduled_workflows_changed"])
        self.assertFalse(p["restrictions"]["engine_code_changed"])
        self.assertFalse(p["restrictions"]["commercial_release_authorized"])


if __name__ == "__main__":
    unittest.main()
