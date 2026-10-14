import unittest
from freight.brain_review_measurement import measure

class MeasurementAcceptance(unittest.TestCase):
    def test_synthetic_tradeoff_is_not_reported_as_money_or_time_saved(self):
        report = measure()
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
