from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


def write_payer_sources(root: Path, *, code="99214"):
    (root / "payer_lines.csv").write_text(
        "Line_ID,Claim_Surrogate_ID,Payer,Service_Date,Billed_Procedure,"
        "Paid_Procedure,Units,Paid_Amount,Modifier,Place_Of_Service\n"
        f"L1,SUR-1,Payer A,2026-08-01,{code},99213,1,120.00,,11\n",
        encoding="utf-8",
    )
    (root / "payer_rates.csv").write_text(
        "Payer,Procedure_Code,Allowed_Amount_Per_Unit,Effective_From,"
        "Effective_To,Modifier,Place_Of_Service\n"
        "Payer A,99214,200.00,2026-01-01,,,,\n",
        encoding="utf-8",
    )


def config():
    return {
        "client_id": "provider-1",
        "currency": "USD",
        "payer": {
            "lines_csv": "payer_lines.csv",
            "rates_csv": "payer_rates.csv",
            "default_effective_from": "2026-01-01",
            "line_source_verified": True,
            "rate_source_verified": True,
            "jurisdiction": "US",
        },
    }


class Scan360PayerRunnerTests(unittest.TestCase):
    def test_payer_underpayment_flows_into_shared_scan360_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_payer_sources(root)
            state = root / "state.json"

            first = run_scan360_config(config(), state_path=state, base_dir=root)
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.totals["validated_cents"], 8000)
            self.assertEqual(first.report.branches["payer"]["validated_cents"], 8000)
            self.assertEqual(first.exceptions, ())

            second = run_scan360_config(config(), state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_missing_rate_becomes_exception_not_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_payer_sources(root, code="99999")
            result = run_scan360_config(
                config(),
                state_path=root / "state.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "payer")
            self.assertEqual(result.exceptions[0]["code"], "NO_RATE")
            self.assertEqual(result.exceptions[0]["claim_surrogate_id"], "SUR-1")

    def test_runner_preserves_phi_header_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "payer_lines.csv").write_text(
                "Line_ID,Claim_Surrogate_ID,Payer,Service_Date,Billed_Procedure,"
                "Paid_Procedure,Units,Paid_Amount,Patient_Name\n"
                "L1,SUR-1,Payer A,2026-08-01,99214,99213,1,120.00,Jane Doe\n",
                encoding="utf-8",
            )
            (root / "payer_rates.csv").write_text(
                "Payer,Procedure_Code,Allowed_Amount_Per_Unit,Effective_From\n"
                "Payer A,99214,200.00,2026-01-01\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                run_scan360_config(
                    config(),
                    state_path=root / "state.json",
                    base_dir=root,
                )


if __name__ == "__main__":
    unittest.main()
