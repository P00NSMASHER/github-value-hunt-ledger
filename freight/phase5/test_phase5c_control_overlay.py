"""Dashboard integration acceptance: source tags must not overclaim cash."""
from pathlib import Path
import tempfile
import unittest

from freight.phase5.phase5c_control_overlay import control_center_data,render_dashboard,generate


class Phase5CControlAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset=control_center_data()

    def test_controls_and_experiment_are_inconclusive(self):
        d=self.dataset["phase5c"]
        self.assertEqual(d["historic_findings_closed"] if "historic_findings_closed" in d else d["historical_finding_closures"],0)
        self.assertEqual(d["historical_original_findings_open"],26)
        self.assertEqual(d["experiment_director_entry"]["verdict"],"INCONCLUSIVE")
        self.assertEqual(d["actual_recovery_cents"],0)
        self.assertEqual(d["actual_retally_revenue_cents"],0)
        self.assertFalse(d["externally_authorized_bank_carrier_buyer_credentials"])
        self.assertEqual(len(self.dataset["phase4"]["executed_labs"]),14)

    def test_signed_recovery_visible_and_labeled_simulated(self):
        html=render_dashboard(self.dataset)
        for needle in (
            'id="signed-reconciliation"','OPEN_UNVERIFIED','INCONCLUSIVE',
            'Zero actual company revenue','Fee refunded','fictional',
            'NO genuine buyer, carrier or banking attestation',
        ):
            self.assertIn(needle,html)

    def test_renders_single_document_without_decorative_success_certification(self):
        html=render_dashboard(self.dataset)
        self.assertEqual(html.count("<html"),1)
        self.assertEqual(html.count("</html>"),1)
        self.assertNotIn("PRODUCTION_FINANCIAL_CERTIFIED",html)

    def test_output_can_be_rebuilt(self):
        with tempfile.TemporaryDirectory() as d:
            data=generate(Path(d))
            self.assertEqual(data["phase5c"]["staged_recovery"]["net_earned_fee_cents"],150)
            self.assertTrue((Path(d)/"index.html").is_file())
            self.assertTrue((Path(d)/"phase5c_executive.json").is_file())


if __name__=="__main__":
    unittest.main()
