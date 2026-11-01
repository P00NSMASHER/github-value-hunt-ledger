"""No unsupported 5E security or finance claims may appear in the executive UI."""
from pathlib import Path
import tempfile
import unittest
from freight.phase5.phase5e_control_overlay import phase5e_snapshot,render_phase5e,export

class Phase5EDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=phase5e_snapshot()

    def test_existing_three_customer_and_signed_recovery_preserved(self):
        self.assertEqual(self.data["phase5d"]["staged_customers_bc"]["customers"],2)
        self.assertEqual(self.data["phase5c"]["staged_recovery"]["net_recovered_cents"],500)
        self.assertEqual(self.data["phase5e"]["real_customer_recovery_cents"],0)

    def test_current_revocation_repair_and_owner_bypass_both_reported(self):
        p=self.data["phase5e"]
        self.assertEqual(p["staged_backdated_revoked_signer_defect"],"REPRODUCED_AND_REPAIRED_IN_QA")
        self.assertEqual(p["direct_owner_sql_signature_bypass"],"OPEN_UNMITIGATED")
        self.assertFalse(p["production_financial_certification"])
        self.assertEqual(p["historical_findings_closed"],0)
        self.assertEqual(p["original_findings_open"],26)

    def test_render_is_a_single_html_document_and_has_unmitigated_label(self):
        html=render_phase5e(self.data)
        for term in ['id="signed-reconciliation"','id="phase5d-original-defect-and-bc"',
                     'id="phase5e-admission-trust"',"OPEN_UNMITIGATED",
                     "26 historical findings still OPEN_UNVERIFIED","actual company revenue $0"]:
            self.assertIn(term,html)
        self.assertEqual(html.count("</html>"),1)
        self.assertEqual(html.count("</main>"),1)
        self.assertNotIn("PRODUCTION_CERTIFIED",html)

    def test_export_exact_evidence(self):
        with tempfile.TemporaryDirectory() as dir:
            d=export(Path(dir))
            self.assertTrue((Path(dir)/"phase5e_executive.json").exists())
            self.assertTrue((Path(dir)/"index.html").exists())
            self.assertEqual(d["phase5e"]["direct_owner_sql_signature_bypass"],"OPEN_UNMITIGATED")

if __name__=="__main__":
    unittest.main()
