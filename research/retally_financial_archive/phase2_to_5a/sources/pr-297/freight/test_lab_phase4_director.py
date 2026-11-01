"""Exact-head integration of 14 actual Python module callsites (synthetic only)."""
from __future__ import annotations

import tempfile
import unittest

from freight.lab_phase4_director import LAB_LABELS, execute_all_labs, priority_actions
from freight.test_lab_phase3_real_chain import rating_fixture, funded_store, scenario
from freight.test_lab_assurance import assertions_and_fees, verifier


class Phase4ExecutionTests(unittest.TestCase):
    def _run(self, maximum=14):
        with tempfile.TemporaryDirectory(prefix="retally-phase4-research-") as root:
            record,book=rating_fixture()
            store=funded_store(root)
            assertions,fees=assertions_and_fees()
            return execute_all_labs(record=record,authority_book=book,store=store,
                                    assertions=assertions,fee_events=fees,
                                    verifier=verifier(),contingency=scenario(),max_labs=maximum)

    def test_full_execution_has_real_results_or_specific_failures(self):
        receipt=self._run()
        self.assertEqual(len(receipt["lab_runs"]),14)
        self.assertEqual(sorted(LAB_LABELS),list(range(1,15)))
        self.assertEqual(receipt["actual_revenue_cents"],0)
        self.assertFalse(receipt["hosted_staging_certified"])
        self.assertFalse(receipt["customer_bank_carrier_authority_proven"])
        self.assertEqual(receipt["historical_findings_open"],26)
        self.assertEqual(len(receipt["receipt_sha256"]),64)
        self.assertEqual(receipt["failed_or_blocked_labs"],[],
                         "Each missing adapter must be repaired or explicitly reported as blocked")
        self.assertEqual(receipt["executed_labs"],list(range(1,15)))
        for row in receipt["lab_runs"]:
            self.assertTrue(row["status"].startswith("EXECUTED"),row)
            self.assertNotEqual(row["negative_probe"],"NOT_VERIFIED")
            self.assertIsInstance(row["elapsed_ms"],int)
        self.assertEqual(receipt["three_customer_pilot"]["simulated_customer_count"],3)
        self.assertEqual(receipt["three_customer_pilot"]["actual_company_revenue_cents"],0)

    def test_budget_marks_unexecuted_work_instead_of_success(self):
        receipt=self._run(maximum=5)
        self.assertEqual(len(receipt["executed_labs"]),5)
        self.assertEqual(len(receipt["failed_or_blocked_labs"]),9)
        self.assertTrue(all(x["status"]=="NOT_EXECUTED_BUDGET"
                            for x in receipt["lab_runs"] if x["lab"] in receipt["failed_or_blocked_labs"]))

    def test_bad_budget_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            rec,book=rating_fixture()
            store=funded_store(root)
            assertions,fees=assertions_and_fees()
            with self.assertRaisesRegex(ValueError,"INVALID_EXECUTION_BUDGET"):
                execute_all_labs(record=rec,authority_book=book,store=store,
                                 assertions=assertions,fee_events=fees,
                                 verifier=verifier(),contingency=scenario(),max_labs=True)

    def test_action_list_prioritizes_failed_execution(self):
        output=priority_actions({"failed_or_blocked_labs":[2,9]})
        self.assertEqual(output[0]["priority"],1)
        self.assertEqual(output[0]["labs"],[2,9])
        self.assertTrue(any("staging" in x["action"].lower() for x in output))


if __name__=="__main__":
    unittest.main()
