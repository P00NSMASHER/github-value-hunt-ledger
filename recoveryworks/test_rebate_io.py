from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.rebate import audit_rebates
from recoveryworks.branches.rebate_io import (
    load_rebate_programs_json,
    load_rebate_purchases_csv,
    load_rebate_settlements_csv,
)


class RebateIoTests(unittest.TestCase):
    def test_real_files_flow_to_validated_rebate_underpayment(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "programs.json").write_text(
                """{
                  "programs": [{
                    "supplier_id": "Supplier A",
                    "program_id": "2026-Q3",
                    "period_start": "2026-07-01",
                    "period_end": "2026-09-30",
                    "tier_mode": "incremental",
                    "measurement_basis": "units",
                    "tiers": [
                      {"min_measure": 0, "max_measure": 100, "rate_pct": 0},
                      {"min_measure": 100, "max_measure": 200, "rate_pct": 5},
                      {"min_measure": 200, "max_measure": null, "rate_pct": 10}
                    ]
                  }]
                }""",
                encoding="utf-8",
            )
            (root / "purchases.csv").write_text(
                "Purchase_ID,Supplier,Program_ID,Purchase_Date,Quantity,Net_Spend\n"
                "P-1,Supplier A,2026-Q3,2026-08-01,250,2500.00\n",
                encoding="utf-8",
            )
            (root / "settlements.csv").write_text(
                "Settlement_ID,Supplier,Program_ID,Amount_Received,Settlement_Date\n"
                "S-1,Supplier A,2026-Q3,75.00,2026-10-15\n",
                encoding="utf-8",
            )
            programs = load_rebate_programs_json(root / "programs.json", verified=True)
            purchases = load_rebate_purchases_csv(root / "purchases.csv", verified=True)
            settlements = load_rebate_settlements_csv(
                root / "settlements.csv", verified=True
            )
            batch = audit_rebates(
                client_id="client",
                programs=programs,
                purchases=purchases,
                settlements=settlements,
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 2500)
            self.assertTrue(finding.rule.source_hash)
            self.assertIn("#row=2", finding.evidence[0].locator)

    def test_tier_mode_cannot_default(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "programs.json"
            path.write_text(
                """[{
                  "supplier_id":"S",
                  "program_id":"P",
                  "period_start":"2026-01-01",
                  "period_end":"2026-12-31",
                  "measurement_basis":"units",
                  "tiers":[{"min_measure":0,"max_measure":null,"rate_pct":5}]
                }]""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_rebate_programs_json(path)

    def test_rate_percent_must_resolve_exactly_to_basis_points(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "programs.json"
            path.write_text(
                """[{
                  "supplier_id":"S",
                  "program_id":"P",
                  "period_start":"2026-01-01",
                  "period_end":"2026-12-31",
                  "tier_mode":"retroactive",
                  "measurement_basis":"spend",
                  "tiers":[{"min_measure":0,"max_measure":null,"rate_pct":5.005}]
                }]""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_rebate_programs_json(path)


if __name__ == "__main__":
    unittest.main()
