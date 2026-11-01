"""Phase 5H original-financial dashboard evidence classification gates."""
from pathlib import Path
import copy
import json
import tempfile
import unittest
from freight.phase5.phase5h_control_overlay import phase5h_snapshot,render_phase5h,export


class Phase5HOperatorAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=phase5h_snapshot()

    def test_principal_scoped_disposable_proof_is_explicit(self):
        p=self.data["phase5h"]
        self.assertEqual(p["phase5g_and_phase5h_verifier_tests_passed"],14)
        self.assertEqual(p["new_tenant_isolation_tests_passed"],3)
        self.assertTrue(p["foreign_tenant_direct_insert_denied"])
        self.assertTrue(p["verifier_cannot_update_tenant_mapping"])
        self.assertEqual(p["verifier_routing_scope_source"],
                         "POSTGRES_AUTHENTICATED_CURRENT_USER_ADMIN_CONTROLLED_MAPPING")
        self.assertFalse(p["spoofable_custom_guc_used"])

    def test_hosted_security_remains_unproven(self):
        p=self.data["phase5h"]
        self.assertFalse(p["hosted_floot_restricted_credential_proven"])
        self.assertFalse(p["stolen_verifier_credential_direct_sql_bypass_fixed"])
        self.assertEqual(p["actual_customer_revenue_cents"],0)
        self.assertEqual(p["historical_findings_closed"],0)
        self.assertEqual(self.data["phase5d"]["d07_historical_register_status"],"OPEN_UNVERIFIED")

    def test_existing_customer_experiment_and_new_rls_visible(self):
        html=render_phase5h(self.data)
        for label in ('id="signed-reconciliation"',
                      'id="phase5d-original-defect-and-bc"',
                      'id="phase5e-admission-trust"',
                      'id="phase5g-independent-admission"',
                      'id="phase5h-principal-rls"',
                      "Hosted Floot trust boundary remains BLOCKED",
                      "current_user","26 historical findings remain OPEN_UNVERIFIED"):
            self.assertIn(label,html)
        self.assertEqual(html.count("</html>"),1)

    def test_rendered_artifacts_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            d=export(Path(directory))
            self.assertTrue((Path(directory)/"index.html").is_file())
            self.assertTrue((Path(directory)/"phase5h_executive.json").is_file())
            self.assertFalse(d["phase5h"]["independent_hosted_verifier_service_proven"])


if __name__=="__main__":
    unittest.main()
