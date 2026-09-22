from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState
from recoveryworks.runner import run_scan360_config


def write_sources(root: Path):
    (root / "Payments.csv").write_text(
        "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
        "P-1,Vendor A,INV-1,100.00,2026-08-01\n"
        "P-2,Vendor A,INV-1-DUP,100.00,2026-08-02\n",
        encoding="utf-8",
    )
    (root / "AP_Invoices.csv").write_text(
        "Vendor,Invoice_Number,Amount,Invoice_Date\n"
        "Vendor A,INV-1,100.00,2026-07-01\n",
        encoding="utf-8",
    )
    (root / "Bills.csv").write_text(
        "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
        "Billed_kWh,Billed_Demand_kW,Billed_rkVA\n"
        "B-1,Utility A,A-1,SC1,2026-08-01,15.00,100,0,0\n",
        encoding="utf-8",
    )
    (root / "tariffs.json").write_text(
        """{
          "tariffs": [{
            "sc_code": "SC1",
            "effective_date": "2026-01-01",
            "logic_steps": [
              {"step_name": "Customer", "charge_type": "fixed_fee", "value": 5},
              {"step_name": "Energy", "charge_type": "per_kwh", "value": 0.05}
            ]
          }]
        }""",
        encoding="utf-8",
    )


def config(*, verified=True):
    return {
        "client_id": "client-1",
        "currency": "USD",
        "ap": {
            "payments_csv": "Payments.csv",
            "obligations_csv": "AP_Invoices.csv",
            "default_effective_from": "2026-01-01",
            "payment_source_verified": verified,
            "obligation_source_verified": verified,
        },
        "utility": {
            "bills_csv": "Bills.csv",
            "tariffs_json": "tariffs.json",
            "utility_id": "Utility A",
            "default_effective_from": "2026-01-01",
            "bill_source_verified": verified,
            "tariff_source_verified": verified,
            "jurisdiction": "NY",
        },
    }


class Scan360RunnerTests(unittest.TestCase):
    def test_ap_and_utility_run_into_one_persistent_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            state = root / "private" / "ledger.json"

            first = run_scan360_config(config(), state_path=state, base_dir=root)

            self.assertEqual(len(first.added_finding_ids), 2)
            self.assertEqual(first.report.totals["cases"], 2)
            self.assertEqual(first.report.totals["validated_cents"], 10500)
            self.assertEqual(first.report.branches["ap"]["validated_cents"], 10000)
            self.assertEqual(first.report.branches["utility"]["validated_cents"], 500)
            self.assertEqual(first.exceptions, ())
            self.assertTrue(state.exists())

            second = run_scan360_config(config(), state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_unverified_sources_remain_review_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            result = run_scan360_config(
                config(verified=False),
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.report.totals["validated_cents"], 0)
            self.assertEqual(result.report.totals["review_cents"], 10500)
            self.assertTrue(all(
                item["state"] == "REVIEW"
                for item in result.report.review_backlog
            ))

    def test_bad_verification_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            bad = config()
            bad["ap"]["payment_source_verified"] = "yes"
            with self.assertRaises(ValueError):
                run_scan360_config(
                    bad,
                    state_path=root / "ledger.json",
                    base_dir=root,
                )

    def test_utility_exceptions_are_reported_without_fabricating_findings(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            bad = config()
            bad["utility"]["default_effective_from"] = "2027-01-01"
            (root / "tariffs.json").write_text(
                """[{
                  "sc_code": "SC1",
                  "effective_date": "2027-01-01",
                  "logic_steps": [
                    {"step_name": "Energy", "charge_type": "per_kwh", "value": 0.05}
                  ]
                }]""",
                encoding="utf-8",
            )
            result = run_scan360_config(
                bad,
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(len(result.added_finding_ids), 1)
            self.assertEqual(result.exceptions[0]["code"], "NO_TARIFF_VERSION")
            self.assertNotIn("utility", result.report.branches)


if __name__ == "__main__":
    unittest.main()
