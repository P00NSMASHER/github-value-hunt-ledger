from pathlib import Path
import tempfile
import unittest

from recoveryworks.cletrics_aws_rehearsal import run_aws_cletrics_rehearsal


class AwsCletricsRehearsalTests(unittest.TestCase):
    def test_three_recovery_theories_and_signal_plane_pass_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_aws_cletrics_rehearsal(Path(d))
            self.assertTrue(result.accepted)
            self.assertEqual(result.base_rate_validated_cents, 1000)
            self.assertEqual(result.discount_validated_cents, 1200)
            self.assertEqual(result.commitment_validated_cents, 1600)
            self.assertEqual(result.savings_opportunity_cents, 35000)
            self.assertEqual(result.anomaly_exposure_cents, 620000)
            self.assertEqual(result.reconciliation_drift_cents, 1000)
            self.assertEqual(result.base_exception_codes, ("NO_CONTRACT_RATE",))


if __name__ == "__main__":
    unittest.main()
