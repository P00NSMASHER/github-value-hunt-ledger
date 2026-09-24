from pathlib import Path
import tempfile
import unittest

from recoveryworks.cletrics_provider_rehearsal import (
    run_azure_cletrics_rehearsal,
    run_gcp_cletrics_rehearsal,
)


class AzureGcpCletricsRehearsalTests(unittest.TestCase):
    def test_realistic_focus_provider_aliases(self):
        from recoveryworks.cloud_provider import canonical_cloud_provider
        self.assertEqual(canonical_cloud_provider("Microsoft"), "azure")
        self.assertEqual(canonical_cloud_provider("Microsoft Azure"), "azure")
        self.assertEqual(canonical_cloud_provider("Google Cloud"), "gcp")
        self.assertEqual(canonical_cloud_provider("Google Cloud Platform"), "gcp")
        self.assertEqual(canonical_cloud_provider("Amazon Web Services"), "aws")

    def test_azure_shared_focus_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_azure_cletrics_rehearsal(Path(d))
            self.assertTrue(result.accepted)
            self.assertEqual(result.base_rate_validated_cents, 1000)
            self.assertEqual(result.discount_validated_cents, 1200)
            self.assertEqual(result.commitment_validated_cents, 1600)
            self.assertEqual(result.savings_opportunity_cents, 5000)
            self.assertEqual(result.base_exception_codes, ("NO_CONTRACT_RATE",))

    def test_gcp_shared_focus_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_gcp_cletrics_rehearsal(Path(d))
            self.assertTrue(result.accepted)
            self.assertEqual(result.base_rate_validated_cents, 1000)
            self.assertEqual(result.discount_validated_cents, 1200)
            self.assertEqual(result.commitment_validated_cents, 1600)
            self.assertEqual(result.savings_opportunity_cents, 5000)
            self.assertEqual(result.base_exception_codes, ("NO_CONTRACT_RATE",))


if __name__ == "__main__":
    unittest.main()
