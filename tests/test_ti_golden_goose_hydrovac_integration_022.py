"""PR-only research safety acceptance for synthetic Golden Goose invoice audit.

Runs existing Node/Python fixtures in the Technology Intelligence release lane.
No network, credentials, customer data, collections or monetization assertions.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "golden_goose" / "hydrovac_proof_to_invoice"


class TestSyntheticGoldenGooseHydrovac(unittest.TestCase):
    def run_js(self, filename):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for Golden Goose JS acceptance")
        env = dict(os.environ, PYTHON=sys.executable)
        process = subprocess.run(
            [node, str(RESEARCH / filename)],
            cwd=str(RESEARCH),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout + "\n" + process.stderr)
        try:
            return json.loads(process.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            self.fail(f"Expected machine-readable JS acceptance, got {process.stdout!r}: {exc}")

    def test_guard_requires_verified_posted_amounts(self):
        result = self.run_js("posted_amount_guard_018.js")
        self.assertEqual(result["passed"], 28)
        self.assertEqual(result["review"], 25)
        self.assertEqual(result["real_invoices"], 0)
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")

    def test_summary_bridge_preserves_review_state(self):
        result = self.run_js("cohort_amount_bridge_019.js")
        self.assertEqual(result["passed"], 28)
        self.assertEqual(result["review_cases"], 25)
        self.assertEqual(result["real_customer_records"], 0)
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")

    def test_real_python_to_js_100_job_cohort(self):
        result = self.run_js("test_100_job_python_to_js_021.js")
        self.assertEqual(result["cases"], 100)
        self.assertEqual(result["quantity_only_clears"], 70)
        self.assertEqual(result["hidden_posted_issues"], 10)
        self.assertEqual(result["strict_arithmetic_only"], 60)
        self.assertEqual(result["strict_needs_review"], 40)
        self.assertIsNone(result["verified_collectible_usd"])
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")
        self.assertEqual(result["real_customer_invoices"], 0)
        self.assertEqual(result["incumbent_vendor_comparison"], "NOT_RUN")


    def test_duplicate_id_review_amplification_is_not_collectible(self):
        result = self.run_js("test_blast_radius_023.js")
        self.assertEqual(result["cases"], 100)
        self.assertEqual(result["unaffected_arithmetic_before"], 100)
        self.assertEqual(result["duplicate_invoice_id_pairs"], 1)
        self.assertEqual(result["directly_touched_jobs"], 2)
        self.assertEqual(result["cohort_review_after"], 100)
        self.assertEqual(result["other_jobs_conservatively_held"], 98)
        self.assertEqual(result["review_amplification_ratio"], 50)
        self.assertEqual(result["hypothetical_other_job_review_cost_usd"], 285.83)
        self.assertEqual(result["real_customer_invoices"], 0)
        self.assertIsNone(result["verified_collectible_usd"])
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")


    def test_diagnostic_only_collision_scope_never_clears_invoices(self):
        result = self.run_js("test_collision_diagnostic_024.js")
        self.assertEqual(result["passed"], 18)
        self.assertTrue(result["bridge_checked"])
        self.assertEqual(result["global_bridge_review"], 100)
        self.assertEqual(result["diagnostic_not_flagged"], 98)
        self.assertEqual(result["hypothetical_global_review_cost_usd"], 291.67)
        self.assertEqual(result["hypothetical_two_job_triage_cost_usd"], 5.83)
        self.assertEqual(result["actual_customer_invoices_reviewed"], 0)
        self.assertIsNone(result["verified_collectible_usd"])
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")
        self.assertFalse(result["release_ready"])
        self.assertFalse(result["commercially_validated"])


if __name__ == "__main__":
    unittest.main()
