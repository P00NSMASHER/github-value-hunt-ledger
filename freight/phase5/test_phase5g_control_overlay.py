"""Owner-facing evidence status must not become a false production release flag."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from freight.phase5.phase5g_control_overlay import phase5g_snapshot,render_phase5g,export


class Phase5GOperatorAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=phase5g_snapshot()

    def test_disposable_separate_principal_evidence(self):
        proof=self.data["phase5g"]
        self.assertEqual(proof["ci_verifier_tests_passed"],11)
        self.assertEqual(proof["principal_app"],"retally_p5g_app_login")
        self.assertEqual(proof["principal_verifier"],"retally_p5g_verifier_login")
        self.assertFalse(proof["production_database_used"])
        self.assertFalse(proof["qa_hosted_database_used"])

    def test_historical_and_actual_cash_certification_remain_blocked(self):
        p=self.data["phase5g"]
        self.assertEqual(p["real_customer_revenue_cents"],0)
        self.assertEqual(p["historical_findings_closed"],0)
        self.assertFalse(p["db_owner_signature_bypass_fixed_in_hosted_floot"])
        self.assertFalse(p["verifier_db_credential_direct_sql_bypass_closed"])
        self.assertEqual(p["supported_signed_document_kinds"],["CONTRACT"])

    def test_existing_customer_dashboard_and_open_exposure_visible(self):
        html=render_phase5g(self.data)
        for required in ('id="signed-reconciliation"',
                         'id="phase5d-original-defect-and-bc"',
                         'id="phase5e-admission-trust"',
                         'id="phase5g-independent-admission"',
                         'OPEN SECURITY EXPOSURE','BLOCKED / NOT DEPLOYED',
                         "fictional CONTRACT documents only"):
            self.assertIn(required,html)
        self.assertEqual(html.count("</html>"),1)
        self.assertNotIn("PRODUCTION_FINANCIAL_CERTIFIED",html)

    def test_export(self):
        with tempfile.TemporaryDirectory() as temp:
            result=export(Path(temp))
            self.assertTrue((Path(temp)/"index.html").is_file())
            self.assertTrue((Path(temp)/"phase5g_executive.json").is_file())
            self.assertFalse(result["phase5g"]["restricted_financial_admission_hosted_in_floot"])


if __name__=="__main__":
    unittest.main()
