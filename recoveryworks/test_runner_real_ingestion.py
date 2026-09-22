from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class RealIngestionRunnerTests(unittest.TestCase):
    def test_statement_backed_ap_and_tiered_utility_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Payments.csv").write_text(
                "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
                "P-1,Vendor A,INV-1,100.00,2026-08-01\n"
                "P-2,Vendor A,INV-1-DUP,100.00,2026-08-02\n",
                encoding="utf-8",
            )
            (root / "Vendor_Statement.csv").write_text(
                "Vendor,Invoice_Number,Balance,Statement_Date\n"
                "Vendor A,INV-1,(100.00),2026-08-31\n",
                encoding="utf-8",
            )
            (root / "Bills.csv").write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh,Billed_Demand_kW,Billed_rkVA,Days_Used\n"
                "B-1,Utility A,A-1,SC1,2026-08-31,220.00,1500,0,0,31\n",
                encoding="utf-8",
            )
            (root / "tariffs.json").write_text(
                """[{
                  "sc_code":"SC1",
                  "effective_date":"2026-01-01",
                  "logic_steps":[
                    {"step_name":"Customer","charge_type":"fixed_fee","value":5},
                    {"step_name":"Energy","charge_type":"tiered_kwh","tiers":[
                      {"up_to_kwh":1000,"rate":0.10},
                      {"up_to_kwh":null,"rate":0.20}
                    ]}
                  ]
                }]""",
                encoding="utf-8",
            )
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "ap": {
                    "payments_csv": "Payments.csv",
                    "vendor_statements_csv": "Vendor_Statement.csv",
                    "payment_source_verified": True,
                    "vendor_statement_source_verified": True,
                },
                "utility": {
                    "bills_csv": "Bills.csv",
                    "tariffs_json": "tariffs.json",
                    "utility_id": "Utility A",
                    "default_effective_from": "2026-01-01",
                    "bill_source_verified": True,
                    "tariff_source_verified": True,
                },
            }
            result = run_scan360_config(
                config,
                state_path=root / "private" / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.exceptions, ())
            self.assertEqual(len(result.added_finding_ids), 2)
            self.assertEqual(result.report.totals["validated_cents"], 11500)
            self.assertEqual(result.report.branches["ap"]["validated_cents"], 10000)
            self.assertEqual(result.report.branches["utility"]["validated_cents"], 1500)


if __name__ == "__main__":
    unittest.main()
