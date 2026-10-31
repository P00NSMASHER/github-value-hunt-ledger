"""Source-metadata-only AHV/renewal evaluation; all input scenarios are synthetic."""
import datetime as dt
import json
from pathlib import Path
import unittest

PATH = Path(__file__).parent / "fixtures" / "nyc_dob_ahv_variance_scope_v1.json"

def decision(case):
    facts = case["facts"]
    kind = case["kind"]
    if kind == "variance_expiry":
        return ("AHV_EXPIRED_NOT_ACTIVE" if facts["ahv_expiry"] < facts["asof"]
                else "UNKNOWN_NOT_ADJUDICATED")
    if kind == "repeat_event":
        return ("REJECT_DUPLICATE_PROJECT_CLAIM" if facts["same_job_number"]
                else "UNKNOWN_DISTINCT_PROJECT")
    if kind == "general_dataset_nonmatch":
        return "UNKNOWN_AHV_OUTSIDE_GENERAL_SOURCE"
    if kind == "base_work_permit_inference":
        return "UNKNOWN_BASE_PERMIT_ISSUANCE"
    if kind == "missing_expiry":
        return "UNKNOWN_MISSING_AHV_EXPIRY"
    if kind == "asof_lookahead":
        return ("REJECT_FUTURE_EVENT_LOOKAHEAD"
                if facts["variance_start"] > facts["asof"] else "UNKNOWN")
    if kind == "catalog_freshness":
        return "STALE_CATALOG_SNAPSHOT_NOT_LIVE_OUTAGE"
    if kind == "bounded_window":
        if facts["variance_start"] <= facts["asof"] <= facts["ahv_expiry"]:
            return "PUBLISHER_TIME_WINDOW_ONLY_NOT_LEGAL_CLEARANCE"
        return "UNKNOWN_VARIANCE_WINDOW"
    raise ValueError("Unknown synthetic control kind")

class AHVSourceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PATH.read_text(encoding="utf8"))

    def test_original_publisher_metadata_is_distinct_from_real_rows(self):
        p = self.pack
        source = p["publisher_source"]
        self.assertEqual(source["dataset_id"], "g76y-dcqj")
        self.assertEqual(source["catalog_column_count"], 24)
        self.assertEqual(source["source_rows_acquired"], 0)
        self.assertIsNone(source["original_data_http_body_sha256"])
        self.assertIsNone(source["source_metadata_body_sha256"])
        self.assertEqual(p["benchmarks"]["independent_real_world_heldout_ahv_cases"], 0)
        self.assertIsNone(p["benchmarks"]["precision"])
        self.assertIsNone(p["benchmarks"]["recall"])
        self.assertFalse(p["rights"]["commercial_scored_leads_clearance"])
        self.assertFalse(p["controls"]["legacy_lab_consolidation_proved"])
        self.assertFalse(p["controls"]["release_approved"])
        self.assertEqual(p["controls"]["private_records_saved"], 0)
        self.assertEqual(p["controls"]["additional_provider_calls"], 0)

    def test_first_party_schema_and_separate_event_family(self):
        p = self.pack
        f = set(p["publisher_source"]["documented_api_fields"])
        self.assertTrue({"ahv_permit_number", "ahvpermitstatus", "variancetype",
                         "variance_start_date_time", "variance_end_date_time",
                         "workpermitnumber"}.issubset(f))
        self.assertNotEqual(p["publisher_source"]["dataset_id"],
                            p["publisher_scope"]["general_dob_now_permit_dataset"])
        self.assertNotEqual(p["publisher_source"]["dataset_id"],
                            p["publisher_scope"]["related_laa_dataset"])
        self.assertIn("ahv_permit_number", p["publisher_scope"]["entity_keys"])

    def test_official_catalog_freshness_is_not_equivalent_to_outage(self):
        d = self.pack["publisher_source"]
        gap = (dt.date.fromisoformat(self.pack["reviewed_on_utc"]) -
               dt.date.fromisoformat(d["last_dataset_updated_reported"])).days
        self.assertEqual(gap, 7)
        self.assertEqual(d["observed_catalog_staleness_days"], gap)
        self.assertIn("cannot prove", d["caveat"])

    def test_synthetic_red_status_only_baseline_green_time_aware_guard(self):
        cases = self.pack["synthetic_controls"]
        expected_count = self.pack["benchmarks"]["synthetic_calibration_controls"] + self.pack["benchmarks"]["synthetic_heldout_controls"]
        self.assertEqual(len(cases), expected_count)
        ids = [x["id"] for x in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(x["provenance"] ==
                            "RESEARCH_AUTHORED_SYNTHETIC_NOT_SOURCE_ROW"
                            and x["independent_real_world_label"] is None
                            for x in cases))
        self.assertEqual({x["id"]: decision(x) for x in cases},
                         {x["id"]: x["expected"] for x in cases})
        expired = next(x for x in cases if x["id"] ==
                       "SYN_AHV_EXPIRED_BUT_WORK_PERMIT_ACTIVE")
        naive_status_only = "ACTIVE" if expired["facts"]["ahv_status"] == "Issued" else "UNKNOWN"
        self.assertEqual(naive_status_only, "ACTIVE")
        self.assertEqual(decision(expired), "AHV_EXPIRED_NOT_ACTIVE")
        self.assertNotEqual(naive_status_only, decision(expired))

    def test_temporal_holdouts_and_fanout_do_not_inflate_accuracy(self):
        p = self.pack
        cases = p["synthetic_controls"]
        self.assertEqual(sum(x["split"] == "synthetic_heldout" for x in cases), 6)
        self.assertEqual(sum(x["split"] == "synthetic_calibration" for x in cases), 3)
        self.assertEqual(p["benchmarks"]["independently_adjudicated_opportunity_labels"], 0)
        self.assertFalse(p["benchmarks"]["commercial_customer_outcome_known"])
        self.assertEqual(p["publisher_source"]["personal_street_or_applicant_fields_persisted"], 0)
        self.assertFalse(p["controls"]["writer_branch_modified"])
        self.assertFalse(p["controls"]["engine_code_changed"])

if __name__ == "__main__":
    unittest.main()
