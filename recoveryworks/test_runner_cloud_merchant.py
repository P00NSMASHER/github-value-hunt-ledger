from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class CloudMerchantRunnerTests(unittest.TestCase):
    def test_cloud_and_merchant_fee_run_into_one_durable_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            (root / "cloud_rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "CloudCo,compute,2026-01-01,,10.00,0,2.00\n",
                encoding="utf-8",
            )
            (root / "cloud_charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "C-1,CloudCo,acct,compute,2026-08-31,40.00\n",
                encoding="utf-8",
            )
            (root / "cloud_meter.csv").write_text(
                "Charge_ID,Meter_Record_ID,Usage_Units\n"
                "C-1,M-1,4\n"
                "C-1,M-2,6\n",
                encoding="utf-8",
            )

            (root / "merchant_agreements.csv").write_text(
                "Processor,Fee_Plan_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Markup_BPS,Per_Transaction_Fee\n"
                "Processor A,PLAN-1,2026-01-01,,10.00,20,0.10\n",
                encoding="utf-8",
            )
            (root / "merchant_statements.csv").write_text(
                "Statement_ID,Processor,Account_ID,Fee_Plan_ID,Statement_Date,"
                "Processor_Controlled_Fees,Scope_Reviewer_ID\n"
                "S-1,Processor A,merchant-1,PLAN-1,2026-08-31,250.00,fee-reviewer-1\n",
                encoding="utf-8",
            )
            (root / "merchant_transactions.csv").write_text(
                "Statement_ID,Gross_Sales,Transaction_Count\n"
                "S-1,100000.00,100\n",
                encoding="utf-8",
            )

            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "charges_csv": "cloud_charges.csv",
                    "rates_csv": "cloud_rates.csv",
                    "meter_csv": "cloud_meter.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "meter_source_verified": True,
                },
                "merchant_fee": {
                    "statements_csv": "merchant_statements.csv",
                    "agreements_csv": "merchant_agreements.csv",
                    "transactions_csv": "merchant_transactions.csv",
                    "statement_source_verified": True,
                    "agreement_source_verified": True,
                    "transaction_source_verified": True,
                },
            }

            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 2)
            self.assertEqual(first.report.totals["validated_cents"], 4000)
            self.assertEqual(first.report.branches["cloud"]["validated_cents"], 1000)
            self.assertEqual(
                first.report.branches["merchant_fee"]["validated_cents"], 3000
            )

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_missing_merchant_transaction_evidence_is_exception(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "agreements.csv").write_text(
                "Processor,Fee_Plan_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Markup_BPS,Per_Transaction_Fee\n"
                "Processor A,PLAN-1,2026-01-01,,10.00,20,0.10\n",
                encoding="utf-8",
            )
            (root / "statements.csv").write_text(
                "Statement_ID,Processor,Account_ID,Fee_Plan_ID,Statement_Date,"
                "Processor_Controlled_Fees,Scope_Reviewer_ID\n"
                "S-1,Processor A,merchant-1,PLAN-1,2026-08-31,250.00,fee-reviewer-1\n",
                encoding="utf-8",
            )
            result = run_scan360_config(
                {
                    "client_id": "client",
                    "merchant_fee": {
                        "statements_csv": "statements.csv",
                        "agreements_csv": "agreements.csv",
                        "statement_source_verified": True,
                        "agreement_source_verified": True,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "merchant_fee")
            self.assertEqual(
                result.exceptions[0]["code"], "MISSING_TRANSACTION_SUMMARY"
            )


if __name__ == "__main__":
    unittest.main()
