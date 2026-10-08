"""Phase 5D owner-facing evidence classification checks."""
import tempfile
import unittest
from pathlib import Path
from freight.phase5.phase5d_control_overlay import phase5d_snapshot,render_phase5d,export


class Phase5DDashboardEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=phase5d_snapshot()

    def test_all_three_fictional_customers_are_separate_and_scoped(self):
        data=self.data
        self.assertEqual(data["phase5d"]["staged_customers_bc"]["customers"],2)
        self.assertEqual(data["phase5d"]["customer_B"]["fee_earned_cents"],0)
        self.assertEqual(data["phase5d"]["customer_C"]["fee_earned_cents"],0)
        self.assertEqual(data["phase5c"]["staged_recovery"]["net_recovered_cents"],500)
        self.assertEqual(data["phase5d"]["actual_retally_revenue_cents"],0)
        self.assertEqual(data["phase5d"]["accepted_real_customer_count"],0)

    def test_original_d07_is_research_only_and_not_closed(self):
        d=self.data["phase5d"]
        self.assertEqual(d["d07_repair_scope"],"REPAIRED_IN_OFFLINE_RESEARCH_ONLY")
        self.assertEqual(d["d07_historical_register_status"],"OPEN_UNVERIFIED")
        self.assertFalse(d["production_actor_identity_certified"])
        self.assertEqual(self.data["phase5c"]["historical_original_findings_open"],26)

    def test_html_preserves_phase5c_and_sets_correct_new_boundaries(self):
        html=render_phase5d(self.data)
        self.assertIn('id="signed-reconciliation"',html)
        self.assertIn('id="phase5d-original-defect-and-bc"',html)
        self.assertIn("NO_RECOVERY_NO_FEE",html)
        self.assertIn("ZERO_POSTINGS_STOP_RECOMMENDED",html)
        self.assertIn("OPEN_UNVERIFIED",html)
        self.assertNotIn("PRODUCTION_FINANCIAL_CERTIFIED",html)

    def test_export(self):
        with tempfile.TemporaryDirectory() as root:
            data=export(Path(root))
            self.assertTrue((Path(root)/"index.html").is_file())
            self.assertTrue((Path(root)/"phase5d_executive.json").is_file())
            self.assertEqual(data["phase5d"]["staged_customers_bc"]["rejected_unsupported_credit_and_fee_attempts"],4)


if __name__=="__main__":
    unittest.main()
