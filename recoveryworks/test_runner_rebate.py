from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class RebateRunnerTests(unittest.TestCase):
    def test_rebate_branch_runs_into_durable_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "programs.json").write_text(
                """[{
                  "supplier_id":"Supplier A",
                  "program_id":"2026-Q3",
                  "period_start":"2026-07-01",
                  "period_end":"2026-09-30",
                  "tier_mode":"incremental",
                  "measurement_basis":"units",
                  "tiers":[
                    {"min_measure":0,"max_measure":100,"rate_pct":0},
                    {"min_measure":100,"max_measure":200,"rate_pct":5},
                    {"min_measure":200,"max_measure":null,"rate_pct":10}
                  ]
                }]""",
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
            config = {
                "client_id": "client",
                "currency": "USD",
                "rebate": {
                    "programs_json": "programs.json",
                    "purchases_csv": "purchases.csv",
                    "settlements_csv": "settlements.csv",
                    "program_source_verified": True,
                    "purchase_source_verified": True,
                    "settlement_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.branches["rebate"]["validated_cents"], 2500)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_missing_settlement_becomes_exception_not_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "programs.json").write_text(
                """[{
                  "supplier_id":"Supplier A",
                  "program_id":"P",
                  "period_start":"2026-01-01",
                  "period_end":"2026-12-31",
                  "tier_mode":"retroactive",
                  "measurement_basis":"spend",
                  "tiers":[{"min_measure":0,"max_measure":null,"rate_pct":5}]
                }]""",
                encoding="utf-8",
            )
            (root / "purchases.csv").write_text(
                "Purchase_ID,Supplier,Program_ID,Purchase_Date,Quantity,Net_Spend\n"
                "P-1,Supplier A,P,2026-08-01,1,1000.00\n",
                encoding="utf-8",
            )
            (root / "settlements.csv").write_text(
                "Settlement_ID,Supplier,Program_ID,Amount_Received,Settlement_Date\n",
                encoding="utf-8",
            )
            result = run_scan360_config(
                {
                    "client_id": "client",
                    "rebate": {
                        "programs_json": "programs.json",
                        "purchases_csv": "purchases.csv",
                        "settlements_csv": "settlements.csv",
                        "program_source_verified": True,
                        "purchase_source_verified": True,
                        "settlement_source_verified": True,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "rebate")
            self.assertEqual(result.exceptions[0]["code"], "NO_SETTLEMENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
