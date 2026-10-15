import os
import unittest
from unittest.mock import patch

from freight.brain_review_measurement import measure

SOURCE_SHA = "a" * 40

class MeasurementAcceptance(unittest.TestCase):
    @patch.dict(os.environ, {"REVIEW_SOURCE_SHA": SOURCE_SHA}, clear=False)
    def test_synthetic_tradeoff_is_not_reported_as_money_or_time_saved(self):
        report = measure()
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["source_sha"], SOURCE_SHA)
        self.assertNotIn("source_base_sha", report)
        self.assertEqual(report["summary"]["REVIEW_SCENARIO"],
                         {"cases":5,"baseline_cases_flagged":2,"candidate_cases_flagged":5})
        self.assertEqual(report["summary"]["KNOWN_BENIGN_SYNTHETIC_TRUTH"],
                         {"cases":2,"baseline_cases_flagged":0,"candidate_cases_flagged":2})
        self.assertEqual(report["summary"]["NONMATCH_CONTROL"],
                         {"cases":5,"baseline_cases_flagged":0,"candidate_cases_flagged":0})
        self.assertEqual(report["validated_recovery_cents"],0)
        self.assertIsNone(report["human_time_saved"])
        self.assertIsNone(report["verified_revenue"])
        self.assertEqual(report["real_customer_outcome"],"NOT_MEASURED")
        self.assertEqual(len(report["cases"]),12)
        self.assertTrue(all(len(value)==64 for value in report["source_sha256"].values()))


class MeasurementSourceProvenanceTests(unittest.TestCase):
    def test_missing_source_sha_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "REVIEW_SOURCE_SHA"):
                measure()

    def test_malformed_or_noncanonical_source_sha_fails_closed(self):
        for value in ("29fec8", "A" * 40, "g" * 40, "0" * 39, "0" * 41):
            with self.subTest(value=value), patch.dict(
                os.environ, {"REVIEW_SOURCE_SHA": value}, clear=False
            ):
                with self.assertRaisesRegex(ValueError, "40-character lowercase"):
                    measure()
