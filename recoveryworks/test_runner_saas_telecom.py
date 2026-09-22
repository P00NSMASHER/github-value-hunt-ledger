from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class SaaSTelecomRunnerTests(unittest.TestCase):
    def test_saas_and_telecom_run_into_one_recovery_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            (root / "saas_rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "SaaS Vendor,pro,2026-01-01,,10.00,0,2.00\n",
                encoding="utf-8",
            )
            (root / "saas_charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "S-CHG-1,SaaS Vendor,SA-1,pro,2026-08-31,40.00\n",
                encoding="utf-8",
            )
            (root / "seats.csv").write_text(
                "Charge_ID,Seat_ID,Billable\n" +
                "".join(
                    f"S-CHG-1,USER-{i},true\n"
                    for i in range(1, 11)
                ),
                encoding="utf-8",
            )

            (root / "tel_rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Carrier A,voice,2026-01-01,,20.00,100,0.10\n",
                encoding="utf-8",
            )
            (root / "tel_charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "T-CHG-1,Carrier A,TEL-1,voice,2026-08-31,30.00\n",
                encoding="utf-8",
            )
            (root / "cdr.csv").write_text(
                "Charge_ID,CDR_ID,Usage_Units\n"
                "T-CHG-1,CDR-1,100\n"
                "T-CHG-1,CDR-2,50\n",
                encoding="utf-8",
            )

            config = {
                "client_id": "client-1",
                "currency": "USD",
                "saas": {
                    "charges_csv": "saas_charges.csv",
                    "rates_csv": "saas_rates.csv",
                    "seat_snapshot_csv": "seats.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "seat_source_verified": True,
                },
                "telecom": {
                    "charges_csv": "tel_charges.csv",
                    "rates_csv": "tel_rates.csv",
                    "cdr_csv": "cdr.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "cdr_source_verified": True,
                },
            }

            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)

            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 2)
            self.assertEqual(first.report.totals["validated_cents"], 1500)
            self.assertEqual(first.report.branches["saas"]["validated_cents"], 1000)
            self.assertEqual(first.report.branches["telecom"]["validated_cents"], 500)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.report.as_dict(), first.report.as_dict())
            self.assertEqual(second.state_head_hash, first.state_head_hash)

    def test_missing_telecom_cdr_is_exception_not_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Carrier A,voice,2026-01-01,,20.00,100,0.10\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "T-1,Carrier A,A-1,voice,2026-08-31,30.00\n",
                encoding="utf-8",
            )
            result = run_scan360_config(
                {
                    "client_id": "client",
                    "currency": "USD",
                    "telecom": {
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
            self.assertEqual(result.exceptions[0]["branch"], "telecom")
            self.assertEqual(result.exceptions[0]["code"], "MISSING_USAGE")


if __name__ == "__main__":
    unittest.main()
