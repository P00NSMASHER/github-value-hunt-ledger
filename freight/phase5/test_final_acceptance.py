"""Final RETALLY acceptance must never imply production financial authority.

Unit tests use the actual governed Phase 4-5H source and signed fictional
Floot QA snapshots, not manufactured new lab success counts.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from freight.phase5.final_acceptance import (
    acceptance,export,gates,InvalidReleaseEvidence,require,immutable_sources,
    original_findings,render,
)


class FinalRetallyAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=acceptance()

    def test_pinned_original_receipts_remain_unchanged(self):
        pinned=immutable_sources()
        self.assertEqual(len(pinned),5)
        self.assertEqual(original_findings()["historical_open"],26)

    def test_all_fourteen_labs_and_three_fictional_customers_preserved(self):
        r=self.report
        self.assertEqual(r["research_labs_executed"],14)
        self.assertEqual(r["synthetic_customer_A_financials"]["net_recovered_cents"],500)
        self.assertEqual(r["synthetic_customer_A_financials"]["net_earned_fee_cents"],150)
        self.assertEqual(r["synthetic_customer_A_financials"]["fee_refunded_cents"],100)
        self.assertEqual(r["synthetic_customers_BC"]["customers"],2)
        self.assertEqual(r["synthetic_customers_BC"]["simulated_customer_recovered_cents"],0)

    def test_all_release_blockers_are_explicit(self):
        r=self.report
        self.assertEqual(len(r["release_gates"]),12)
        self.assertEqual(len(r["blocked_gates"]),6)
        self.assertEqual(r["release_decision"],"DO_NOT_RELEASE_FINANCIAL_PRODUCTION")
        self.assertIn("HOSTED_RESTRICTED_DB_PRINCIPAL",r["blocked_gates"])
        self.assertIn("HOSTED_INDEPENDENT_CRYPTO_ADMISSION",r["blocked_gates"])
        self.assertIn("GENUINE_BUYER_CARRIER_BANK_AUTHORITY",r["blocked_gates"])
        self.assertIn("PRODUCTION_EQUIVALENT_AUTH_SCHEMA",r["blocked_gates"])
        self.assertIn("TWENTY_SIX_HISTORIC_FINDING_CLOSURES",r["blocked_gates"])
        self.assertIn("REAL_CLIENT_RECOVERY_AND_REVENUE",r["blocked_gates"])

    def test_database_isolation_and_owner_bypass_stated(self):
        r=self.report
        self.assertNotEqual(r["qa_postgres_system_id"],r["prod_postgres_system_id"])
        self.assertEqual(r["hosted_qa_db_principal"],"neondb_owner")
        self.assertFalse(r["live_floot_verified_during_this_ci"])
        self.assertFalse(r["original_findings"]["d07_product_certified"])
        self.assertEqual(r["actual_company_revenue_cents"],0)
        self.assertEqual(r["actual_customer_recovery_cents"],0)

    def test_broken_source_provenance_rejects_unpinned_objects(self):
        with self.assertRaisesRegex(InvalidReleaseEvidence,"ORIGINAL"):
            require(False,"ORIGINAL_EVIDENCE_NOT_PROVEN")

    def test_no_release_gate_may_be_passed_by_changing_status_text(self):
        altered=deepcopy(self.report)
        for gate in altered["release_gates"]:
            if gate["id"]=="HOSTED_RESTRICTED_DB_PRINCIPAL":
                gate["status"]="VERIFIED_PRODUCTION"
        self.assertNotEqual(altered["release_gates"],gates())
        self.assertEqual(self.report["release_decision"],"DO_NOT_RELEASE_FINANCIAL_PRODUCTION")

    def test_dashboard_does_not_erase_existing_evidence(self):
        html=render(self.report)
        for marker in (
            'id="signed-reconciliation"',
            'id="phase5d-original-defect-and-bc"',
            'id="phase5e-admission-trust"',
            'id="phase5g-independent-admission"',
            'id="phase5h-principal-rls"',
            'id="final-retally-release-acceptance"',
            "DO NOT RELEASE FINANCIAL PRODUCTION",
            "OPEN_UNVERIFIED",
        ):
            self.assertIn(marker,html)
        self.assertEqual(html.count("</html>"),1)
        self.assertEqual(html.count("</main>"),1)

    def test_final_handoff_generates_three_files(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            result=export(out)
            self.assertEqual(result["release_decision"],"DO_NOT_RELEASE_FINANCIAL_PRODUCTION")
            for file in ("index.html","final_acceptance.json","FINAL_ENGINEERING_HANDOFF.md"):
                self.assertTrue((out/file).is_file(),file)


if __name__=="__main__":
    unittest.main()
