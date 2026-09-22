from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class LeaseRebateRunnerTests(unittest.TestCase):
    def test_lease_and_rebate_run_into_one_recovery_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            (root / "lease_rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Landlord A,CAM-2026,2026-01-01,,1000.00,0,2.50\n",
                encoding="utf-8",
            )
            (root / "lease_charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "L-1,Landlord A,SITE-1,CAM-2026,2026-08-31,1400.00\n",
                encoding="utf-8",
            )
            (root / "lease_area.csv").write_text(
                "Charge_ID,Area_SqFt\n"
                "L-1,100\n",
                encoding="utf-8",
            )

            (root / "rebate_agreements.csv").write_text(
                "Agreement_ID,Vendor,Basis,Effective_From,Effective_To,"
                "Threshold_Amount,Threshold_Units,Rate_BPS,Rate_Per_Unit,Fixed_Bonus\n"
                "AGR-1,Vendor A,spend_bps,2026-01-01,,50000,,200,,500.00\n",
                encoding="utf-8",
            )
            (root / "rebate_activity.csv").write_text(
                "Agreement_ID,Period_ID,Period_End,Eligible_Spend,Eligible_Units\n"
                "AGR-1,2026-Q3,2026-09-30,100000,\n",
                encoding="utf-8",
            )
            (root / "rebate_credits.csv").write_text(
                "Credit_ID,Agreement_ID,Period_ID,Amount\n"
                "CR-1,AGR-1,2026-Q3,1500.00\n",
                encoding="utf-8",
            )

            config = {
                "client_id": "client-1",
                "currency": "USD",
                "lease": {
                    "charges_csv": "lease_charges.csv",
                    "rates_csv": "lease_rates.csv",
                    "area_csv": "lease_area.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "area_source_verified": True,
                },
                "rebate": {
                    "agreements_csv": "rebate_agreements.csv",
                    "activity_csv": "rebate_activity.csv",
                    "credits_csv": "rebate_credits.csv",
                    "agreement_source_verified": True,
                    "activity_source_verified": True,
                    "credit_source_verified": True,
                },
            }

            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)

            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 2)
            self.assertEqual(first.report.branches["lease"]["validated_cents"], 15000)
            self.assertEqual(first.report.branches["rebate"]["validated_cents"], 100000)
            self.assertEqual(first.report.totals["validated_cents"], 115000)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.report.as_dict(), first.report.as_dict())
            self.assertEqual(second.state_head_hash, first.state_head_hash)

    def test_rebate_missing_credit_row_is_exception_not_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "agreements.csv").write_text(
                "Agreement_ID,Vendor,Basis,Effective_From,Effective_To,"
                "Threshold_Amount,Threshold_Units,Rate_BPS,Rate_Per_Unit,Fixed_Bonus\n"
                "AGR-1,Vendor A,spend_bps,2026-01-01,,0,,100,,0\n",
                encoding="utf-8",
            )
            (root / "activity.csv").write_text(
                "Agreement_ID,Period_ID,Period_End,Eligible_Spend,Eligible_Units\n"
                "AGR-1,2026-Q3,2026-09-30,100000,\n",
                encoding="utf-8",
            )
            (root / "credits.csv").write_text(
                "Credit_ID,Agreement_ID,Period_ID,Amount\n",
                encoding="utf-8",
            )
            result = run_scan360_config(
                {
                    "client_id": "client",
                    "currency": "USD",
                    "rebate": {
                        "agreements_csv": "agreements.csv",
                        "activity_csv": "activity.csv",
                        "credits_csv": "credits.csv",
                        "agreement_source_verified": True,
                        "activity_source_verified": True,
                        "credit_source_verified": True,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "rebate")
            self.assertEqual(
                result.exceptions[0]["code"],
                "MISSING_CREDIT_LEDGER_ROW",
            )


if __name__ == "__main__":
    unittest.main()
