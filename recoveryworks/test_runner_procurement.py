from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class ProcurementRunnerTests(unittest.TestCase):
    def test_procurement_runs_into_durable_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Supplier A,SKU-1,2026-01-01,,0,0,10.00\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "PO-LINE-1,Supplier A,PO-100,SKU-1,2026-08-31,1200.00\n",
                encoding="utf-8",
            )
            (root / "quantities.csv").write_text(
                "Charge_ID,Quantity\n"
                "PO-LINE-1,100\n",
                encoding="utf-8",
            )
            config = {
                "client_id": "client",
                "currency": "USD",
                "procurement": {
                    "charges_csv": "charges.csv",
                    "rates_csv": "rates.csv",
                    "quantities_csv": "quantities.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "quantity_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.branches["procurement"]["validated_cents"], 20000)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)

    def test_missing_procurement_quantity_is_exception_not_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Supplier A,SKU-1,2026-01-01,,0,0,10.00\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "PO-LINE-1,Supplier A,PO-100,SKU-1,2026-08-31,1200.00\n",
                encoding="utf-8",
            )
            result = run_scan360_config(
                {
                    "client_id": "client",
                    "procurement": {
                        "charges_csv": "charges.csv",
                        "rates_csv": "rates.csv",
                        "charge_source_verified": True,
                        "rate_source_verified": True,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "procurement")
            self.assertEqual(result.exceptions[0]["code"], "MISSING_USAGE")


if __name__ == "__main__":
    unittest.main()
