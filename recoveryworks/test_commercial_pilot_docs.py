from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.commercial_pilot import build_commercial_pilot_package
from recoveryworks.commercial_pilot_docs import (
    build_commercial_pilot_drafts,
    build_fee_scenario,
    write_commercial_pilot_drafts,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.test_commercial_pilot import CommercialPilotPackageTests


class CommercialPilotDraftTests(unittest.TestCase):
    def package(self):
        return build_commercial_pilot_package(
            CommercialPilotPackageTests().spec()
        )

    def test_fee_scenario_is_arithmetic_not_forecast(self):
        package = self.package()
        scenario = build_fee_scenario(
            package,
            assumed_recovered_cash_cents=5_000_000,
        )
        self.assertEqual(scenario.success_fee_cents, 1_000_000)
        self.assertFalse(scenario.is_forecast)
        self.assertTrue(scenario.is_pricing_hypothesis)

    def test_proposal_and_sow_are_explicitly_nonbinding_drafts(self):
        drafts = build_commercial_pilot_drafts(
            self.package(),
            assumed_recovered_cash_cents=5_000_000,
        )
        self.assertFalse(drafts.signature_ready)
        self.assertFalse(drafts.accepted)
        self.assertFalse(drafts.invoice_generated)
        self.assertFalse(drafts.external_commitment_created)
        self.assertIn("not accepted, signed, invoiced, or binding", drafts.proposal_markdown)
        self.assertIn("not an executed statement of work", drafts.sow_markdown)
        self.assertIn("not a forecast of recovery", drafts.proposal_markdown)

    def test_draft_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            drafts = build_commercial_pilot_drafts(self.package())
            paths = write_commercial_pilot_drafts(drafts, directory=Path(d) / "drafts")
            self.assertTrue(all(private_permissions_verified(path) for path in paths))


if __name__ == "__main__":
    unittest.main()
