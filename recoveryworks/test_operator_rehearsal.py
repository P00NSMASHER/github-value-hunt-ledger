from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from recoveryworks.operator_rehearsal import run_simulated_operator_rehearsal
from recoveryworks.private_io import private_permissions_verified

class OperatorRehearsalTests(unittest.TestCase):
    def test_one_command_simulated_operator_flow(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_simulated_operator_rehearsal(Path(d))
            self.assertEqual(
                result.as_dict()["state"],"SIMULATED_OPERATOR_REHEARSAL_PASSED")
            self.assertFalse(result.customer_contacted)
            self.assertFalse(result.real_customer_onboarded)
            self.assertFalse(result.external_actions_performed)
            self.assertTrue(Path(result.assurance_report_path).is_file())
            self.assertTrue(Path(result.diligence_index_path).is_file())
            self.assertTrue(Path(result.runbook_path).is_file())
            self.assertTrue(private_permissions_verified(Path(result.runbook_path)))

if __name__=="__main__":
    unittest.main()
